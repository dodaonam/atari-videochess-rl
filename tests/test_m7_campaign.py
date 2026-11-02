from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from videochess_rl.m6.ledger import HashChainLedger, write_json_atomic
from videochess_rl.m7.campaign import (
    M7CampaignError,
    M7CampaignRunner,
    inspect_ale_runtime,
    run_identity,
)
from videochess_rl.m7.protocol import build_config, canonical_json_bytes, schedule_sha256


class _FakeRuntime:
    def __init__(self, size: int = 0) -> None:
        self.size = size

    def _artifact_bytes(self) -> int:
        return self.size


class M7CampaignTests(unittest.TestCase):
    def test_run_identity_binds_source_config_and_schedule(self) -> None:
        source = {"git_commit": "a" * 40, "git_tree": "b" * 40, "source_bundle_sha256": "c" * 64}
        base = run_identity(source, "d" * 64, "e" * 64, "m7-option-b-test")
        self.assertEqual(base, run_identity(source, "d" * 64, "e" * 64, "m7-option-b-test"))
        self.assertNotEqual(base, run_identity(source, "f" * 64, "e" * 64, "m7-option-b-test"))

    def test_runtime_resource_stops_enforce_only_authorized_limits(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            runner = object.__new__(M7CampaignRunner)
            runner.campaign_limits = build_config()["resource_limits"]
            runner.artifact_parent = Path(directory)
            runner.runtime = _FakeRuntime()
            self.assertIsNone(runner._stop_check("run", {"game_id": "g"}, 0))
            self.assertIsNone(runner.campaign_limits["maximum_process_rss_bytes"])
            self.assertEqual(runner._stop_check("run", {"game_id": "g"}, 162000), "authorized aggregate gameplay allowance reached")
            runner.runtime = _FakeRuntime(8 * 1024**3)
            self.assertEqual(runner._stop_check("run", {"game_id": "g"}, 0), "8-GiB M7 artifact ceiling reached with finalization reserve")

    def test_constructed_ale_matches_rom_profile_and_horizon_without_reset(self) -> None:
        runtime = inspect_ale_runtime(build_config())
        self.assertEqual(runtime["rom_sha256"], "d44f2a115393b0a6cbcd5398d62369e652f3670a9ee585883d183e740edad0f7")
        self.assertEqual(runtime["registered_defaults"]["max_num_frames_per_episode"], 108000)
        self.assertEqual(runtime["ale_episode_frame_limit"], 500000)
        self.assertEqual(runtime["instance_runtime"]["mode"], 4)
        self.assertEqual(runtime["instance_runtime"]["frameskip"], 4)
        self.assertEqual(runtime["instance_runtime"]["repeat_action_probability"], 0.25)
        self.assertEqual(runtime["instance_runtime"]["observation_shape"], [210, 160, 3])

    def _fixture_runner_and_ledger(self, root: Path):
        config = build_config()
        schedule = config["research_design"]["schedule"]
        config_path = root / "config.json"
        config_path.write_text(json.dumps(config), encoding="utf-8")
        config_sha = hashlib.sha256(config_path.read_bytes()).hexdigest()
        source = {"git_commit": "a" * 40, "git_tree": "b" * 40, "source_bundle_sha256": "c" * 64}
        run_id = "m7-resume-fixture"
        manifest = {
            "schema": "videochess-m7-run-manifest/1.0",
            "protocol_id": config["protocol_id"],
            "run_id": run_id,
            "configuration_sha256": config_sha,
            "schedule_sha256": config["research_design"]["schedule_sha256"],
            "scheduled_attempt_count": len(schedule),
            "seed_schedule": schedule,
            "effective_ale_horizon": 500000,
            **source,
        }
        run_dir = root / run_id
        run_dir.mkdir()
        manifest_path = run_dir / "run-manifest.json"
        manifest_sha = write_json_atomic(manifest_path, manifest)
        ledger = HashChainLedger(run_dir / "events.jsonl", run_id=run_id)
        ledger.append("run_started", {"run_manifest_sha256": manifest_sha,
                                       "schedule_sha256": config["research_design"]["schedule_sha256"],
                                       "schedule": schedule})
        runner = object.__new__(M7CampaignRunner)
        runner.config = config
        runner.config_path = config_path
        runner.repo_root = root
        return runner, run_dir, run_id, source, schedule, ledger

    def test_resume_recovery_streams_and_validates_hash_chained_ledger(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            runner, run_dir, run_id, source, schedule, ledger = self._fixture_runner_and_ledger(root)
            item = schedule[0]
            attempt_id = runner._attempt_id(item, retry=False)
            ledger.append("attempt_started", {"attempt_id": attempt_id, "game_id": item["game_id"],
                                               "policy_id": item["policy_id"], "ale_seed": item["ale_seed"]})
            state = runner._recover_run_state(run_dir, run_id, source, schedule)
            self.assertIn(attempt_id, state["started_ids"])
            self.assertNotIn(attempt_id, state["completed_ids"])
            self.assertNotIn(attempt_id, state["reset_ids"])

    def test_resume_rejects_duplicate_attempt_and_tampered_ledger(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            runner, run_dir, run_id, source, schedule, ledger = self._fixture_runner_and_ledger(root)
            item = schedule[0]
            attempt_id = runner._attempt_id(item, retry=False)
            start = {"attempt_id": attempt_id, "game_id": item["game_id"], "policy_id": item["policy_id"], "ale_seed": item["ale_seed"]}
            ledger.append("attempt_started", start)
            ledger.append("attempt_started", start)
            with self.assertRaises(M7CampaignError):
                runner._recover_run_state(run_dir, run_id, source, schedule)

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            runner, run_dir, run_id, source, schedule, ledger = self._fixture_runner_and_ledger(root)
            path = run_dir / "events.jsonl"
            data = path.read_bytes().replace(b"run_started", b"run_corrupt", 1)
            path.write_bytes(data)
            with self.assertRaises(ValueError):
                runner._recover_run_state(run_dir, run_id, source, schedule)


if __name__ == "__main__":
    unittest.main()
