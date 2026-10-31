from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from videochess_rl.m6.campaign import _slug
from videochess_rl.m6.ledger import HashChainLedger, build_artifact_manifest, seal_episode_trace, sha256_file, write_json_atomic
from videochess_rl.m7.analysis import AnalysisIntegrityError, analyze_m7_run
from videochess_rl.m7.campaign import run_identity
from videochess_rl.m7.protocol import build_config


class M7AnalysisIntegrationTests(unittest.TestCase):
    def _make_not_started_run(self, root: Path):
        config = build_config()
        config_path = root / "config.json"
        config_path.write_text(json.dumps(config, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
        config_sha = sha256_file(config_path)
        source = {"git_commit": "a" * 40, "git_tree": "b" * 40, "source_bundle_sha256": "c" * 64}
        schedule = config["research_design"]["schedule"]
        run_id = run_identity(source, config_sha, config["research_design"]["schedule_sha256"], config["run_id_prefix"])
        run_dir = root / run_id
        attempts_root = run_dir / "attempts"
        attempts_root.mkdir(parents=True)
        manifest = {
            "schema": "videochess-m7-run-manifest/1.0",
            "protocol_id": config["protocol_id"],
            "run_id": run_id,
            "configuration_sha256": config_sha,
            "schedule_sha256": config["research_design"]["schedule_sha256"],
            "scheduled_attempt_count": 90,
            "seed_schedule": schedule,
            "effective_ale_horizon": 500000,
            **source,
        }
        manifest_sha = write_json_atomic(run_dir / "run-manifest.json", manifest)
        ledger = HashChainLedger(run_dir / "events.jsonl", run_id=run_id)
        ledger.append("run_started", {"run_manifest_sha256": manifest_sha,
                                       "schedule_sha256": config["research_design"]["schedule_sha256"],
                                       "schedule": schedule})
        resource_rows = []
        accounting_cells = []
        for item in schedule:
            attempt_id = f"fixture-{item['slot']:03d}"
            reset_observed = item["slot"] < 9
            ledger.append("attempt_started", {"attempt_id": attempt_id, "game_id": item["game_id"],
                                                "policy_id": item["policy_id"], "ale_seed": item["ale_seed"]})
            if reset_observed:
                ledger.append("ale_reset_observed", {"attempt_id": attempt_id, "game_id": item["game_id"],
                                                       "ale_seed": item["ale_seed"]})
                trace = seal_episode_trace({
                    "run_id": run_id, "game_id": item["game_id"], "attempt_id": attempt_id,
                    "seed": item["ale_seed"], "player_color": "white",
                    "config": {"env_id": "ALE/VideoChess-v5"},
                    "runtime": {"rom_sha256": "d44f2a115393b0a6cbcd5398d62369e652f3670a9ee585883d183e740edad0f7"},
                    "git": {"head": source["git_commit"], "tree": source["git_tree"]},
                    "turns": [], "reset": {"observed": True}, "initial_position": {"rgb": "synthetic"},
                    "terminal": {"ale_terminated": True, "ale_truncated": False, "ale_reward_total": -1.0,
                                 "player_moves_attempted": 0, "verified_player_moves": 0,
                                 "verified_atari_replies": 0, "runner_stop_category": None},
                    "terminal_observation": {"synthetic_fixture": True},
                })
            record = {
                "schema": "videochess-m6-attempt-record/1.0",
                "run_id": run_id,
                "game_id": item["game_id"],
                "attempt_id": attempt_id,
                "policy_id": item["policy_id"],
                "ale_seed": item["ale_seed"],
                "agent_color": "white",
                "reset_observed": reset_observed,
                "outcome": "loss" if reset_observed else "incomplete",
                "stop_reason": "synthetic terminal loss" if reset_observed else "synthetic pre-reset failure",
            }
            attempt_dir = attempts_root / _slug(attempt_id)
            attempt_dir.mkdir()
            if reset_observed:
                trace_path = attempt_dir / "trace.json"
                trace_sha = write_json_atomic(trace_path, {"schema": "videochess-m6-episode-trace/1.0", "episode": trace})
                attempt_manifest = build_artifact_manifest(attempt_dir, exclude=("attempt.json", "attempt-manifest.json"))
                attempt_manifest_sha = write_json_atomic(attempt_dir / "attempt-manifest.json", attempt_manifest)
                record.update({"trace_sha256": trace_sha, "artifact_manifest_sha256": attempt_manifest_sha})
            else:
                record.update({"trace_sha256": None, "artifact_manifest_sha256": None})
            write_json_atomic(attempt_dir / "attempt.json", record)
            ledger.append("attempt_finished", {"attempt_id": attempt_id, "game_id": item["game_id"], "attempt_record": record})
            resource = {"attempt_id": attempt_id, "game_id": item["game_id"],
                        "policy_id": item["policy_id"], "ale_seed": item["ale_seed"],
                        "observed_process_wall_seconds": 0.1, "process_cpu_seconds": 0.05,
                        "process_cpu_utilization_one_core_percent": 50.0,
                        "process_cpu_utilization_machine_percent": 6.25,
                        "logical_cpu_count": 8, "process_peak_rss_bytes": 1024,
                        "attempt_trace_peak_rss_bytes": 1024,
                        "campaign_artifact_bytes_after_attempt": 1024,
                        "free_disk_bytes_after_attempt": 1000000}
            resource_rows.append(resource)
            ledger.append("attempt_resource_observed", resource)
            accounting_cells.append({
                "slot": item["slot"], "game_id": item["game_id"], "policy_id": item["policy_id"],
                "ale_seed": item["ale_seed"], "scheduled": True, "started": reset_observed,
                "attempt_process_started": True, "reset_observed": reset_observed,
                "attempt_process_count": 1, "attempt_ids": [attempt_id],
                "selected_attempt_status": record["outcome"], "selected_stop_reason": record["stop_reason"],
            })
        ledger.append("run_finished", {"scheduled_count": 90, "schedule_reset_count": 0, "resource_stop_reason": None})
        summary = {
            "schema": "videochess-m7-campaign-summary/1.0", "run_id": run_id,
            "protocol_id": config["protocol_id"], "configuration_sha256": config_sha,
            "schedule_sha256": config["research_design"]["schedule_sha256"],
            "scheduled_attempt_count": 90,
            "schedule_accounting": {"scheduled_cells": 90, "started_cells": 9,
                                    "attempt_process_started_cells": 90, "reset_observed_cells": 9,
                                    "not_started_cells": 81, "all_cells_retained": True,
                                    "cells": accounting_cells},
            "process_resource_observations": resource_rows,
            "resource_stop_reason": None, "campaign_artifact_bytes": 1024,
            "free_disk_bytes_after_campaign": 1000000, "maximum_process_rss_bytes": 1024,
            "aggregate_process_cpu_seconds": 4.5,
            "aggregate_observed_process_wall_seconds": 9.0,
            "campaign_observed_session_wall_seconds": 12.0,
            "setup_seconds_before_first_attempt": 0.1, "resume_recovery_seconds": 0.0,
        }
        write_json_atomic(run_dir / "summary.json", summary)
        artifact_manifest = build_artifact_manifest(run_dir)
        write_json_atomic(run_dir / "artifact-manifest.json", artifact_manifest)
        return config_path, run_dir

    def test_partial_run_reconstructs_ninety_cells_and_matches_summary(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            config_path, run_dir = self._make_not_started_run(Path(directory))
            result = analyze_m7_run(run_dir, config_path=config_path)
            self.assertEqual(result["scheduled_attempt_count"], 90)
            self.assertEqual(result["attempt_processes_started"], 90)
            self.assertEqual(result["reset_observed_cells"], 9)
            self.assertEqual(result["summary_reconciliation"]["summary_matches_verified_schedule"], True)
            for policy in result["policy_summary"]["by_policy"].values():
                self.assertEqual(policy["scheduled"], 10)
                self.assertEqual(policy["losses"], 1)
                self.assertEqual(policy["not_started"], 9)
                self.assertEqual(policy["terminal_only_game_score"], 0.0)

    def test_partial_run_rejects_summary_outcome_drift(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            config_path, run_dir = self._make_not_started_run(Path(directory))
            summary_path = run_dir / "summary.json"
            summary = json.loads(summary_path.read_text(encoding="utf-8"))
            summary["schedule_accounting"]["cells"][0]["selected_attempt_status"] = "draw"
            write_json_atomic(summary_path, summary, refuse_existing=False)
            manifest = build_artifact_manifest(run_dir)
            write_json_atomic(run_dir / "artifact-manifest.json", manifest, refuse_existing=False)
            with self.assertRaises(AnalysisIntegrityError):
                analyze_m7_run(run_dir, config_path=config_path)


if __name__ == "__main__":
    unittest.main()
