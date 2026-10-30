"""Hash-chain, outcome, denominator, and artifact integrity tests for M6."""

from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from videochess_rl.m6.ledger import (
    HashChainLedger,
    build_artifact_manifest,
    classify_attempt,
    seal_episode_trace,
    summarize_attempts,
    verify_artifact_manifest,
    verify_episode_trace,
    verify_hash_chain,
    wilson_interval,
    write_json_atomic,
)


class M6LedgerTests(unittest.TestCase):
    def test_append_only_attempt_chain_verifies_and_detects_tampering(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "events.jsonl"
            ledger = HashChainLedger(path, run_id="m6-test-run")
            ledger.append("attempt_started", {"attempt_id": "game-001", "ale_seed": 7})
            ledger.append("attempt_finished", {"attempt_id": "game-001", "result": "incomplete"})
            self.assertEqual(len(verify_hash_chain(path, expected_run_id="m6-test-run")), 2)
            records = path.read_text(encoding="utf-8").splitlines()
            changed = json.loads(records[0])
            changed["payload"]["ale_seed"] = 8
            records[0] = json.dumps(changed, sort_keys=True, separators=(",", ":"))
            path.write_text("\n".join(records) + "\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "hash mismatch"):
                verify_hash_chain(path, expected_run_id="m6-test-run")

    def test_partial_ledger_tail_is_preserved_and_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "events.jsonl"
            ledger = HashChainLedger(path, run_id="run")
            ledger.append("attempt_started", {"attempt_id": "game-1"})
            with path.open("ab") as stream:
                stream.write(b'{"schema":"partial')
            original = path.read_bytes()
            with self.assertRaisesRegex(ValueError, "partial final record"):
                verify_hash_chain(path)
            self.assertEqual(path.read_bytes(), original)

    def test_trace_hash_chain_detects_nested_decision_or_rgb_tampering(self) -> None:
        trace = seal_episode_trace({
            "reset": {"frame_number": 0, "rgb_sha256": "a" * 64},
            "initial_position": {"verified_from_rgb": True},
            "turns": [{
                "decision_input": {"history_uci": [], "legal_candidates_uci": ["e2e4"]},
                "policy_decision": {"policy_id": "frozen", "selected_uci": "e2e4"},
                "input_phases": [{"phase": "select_source", "frame_number": 10}],
                "evidence_windows": [{"frame_number": 20, "rgb_sha256": "b" * 64}],
                "player_move": {"uci": "e2e4", "verified_from_rgb": True},
                "opponent_reply": {"uci": "e7e5", "verified_from_rgb": True},
            }],
            "terminal": {"ale_terminated": False, "ale_truncated": False},
        })
        self.assertEqual(verify_episode_trace(trace)["event_count"], 11)
        trace["turns"][0]["decision_input"]["history_uci"].append("e2e4")
        with self.assertRaisesRegex(ValueError, "payload hash"):
            verify_episode_trace(trace)

    def test_artifact_manifest_binds_frames_and_trace_and_detects_tampering(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "frames").mkdir()
            (root / "frames/reset.rgb").write_bytes(b"frame-a")
            (root / "trace.json").write_text('{"status":"runner_stopped"}\n', encoding="utf-8")
            manifest = build_artifact_manifest(root)
            write_json_atomic(root / "artifact-manifest.json", manifest)
            verified = verify_artifact_manifest(root)
            self.assertEqual(verified["total_bytes"], len(b"frame-a") + len('{"status":"runner_stopped"}\n'))
            (root / "frames/reset.rgb").write_bytes(b"tampered")
            with self.assertRaisesRegex(ValueError, "does not match"):
                verify_artifact_manifest(root)

    def test_aggregate_rebuilds_from_sealed_trace_and_attempt_manifest(self) -> None:
        from videochess_rl.m6.campaign import summarize_run

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            run_id = "m6-summary-test"
            attempt_id = "game-000"
            attempt_dir = root / "artifacts/m6" / run_id / "attempts" / attempt_id
            attempt_dir.mkdir(parents=True)
            (attempt_dir / "reset.rgb").write_bytes(b"rgb-reset")
            trace = seal_episode_trace({
                "terminal": {
                    "ale_terminated": True,
                    "ale_truncated": False,
                    "ale_reward_total": 0.0,
                    "runner_stop_category": "ALE_TERMINATED",
                    "player_moves_attempted": 1,
                    "verified_player_moves": 1,
                    "verified_atari_replies": 1,
                    "unexpected_directional_displacements": 4,
                    "ale_frames": 25,
                    "environment_steps": 8,
                    "wall_seconds": 2.0,
                },
                "turns": [],
            })
            trace_path = attempt_dir / "trace.json"
            trace_sha = write_json_atomic(trace_path, {"schema": "videochess-m6-episode-trace/1.0", "episode": trace})
            attempt_manifest = build_artifact_manifest(attempt_dir, exclude=("attempt.json", "attempt-manifest.json"))
            manifest_path = attempt_dir / "attempt-manifest.json"
            manifest_sha = write_json_atomic(manifest_path, attempt_manifest)
            record = {
                "attempt_id": attempt_id,
                "game_id": attempt_id,
                "policy_id": "test-policy",
                "outcome": "terminal_unknown",
                "reset_observed": True,
                "trace_path": trace_path.relative_to(root).as_posix(),
                "trace_sha256": trace_sha,
                "artifact_manifest_path": manifest_path.relative_to(root).as_posix(),
                "artifact_manifest_sha256": manifest_sha,
                "player_moves_attempted": 1,
                "rgb_verified_player_moves": 1,
                "verified_atari_replies": 1,
                # Legacy development rows counted recoverable cursor movement
                # corrections as board desynchronizations; summaries rederive
                # the board metric from the trace and preserve this source value.
                "desynchronization_count": 4,
                "ale_frames": 25,
                "environment_steps": 8,
                "wall_seconds": 2.0,
            }
            events_path = root / "events.jsonl"
            ledger = HashChainLedger(events_path, run_id=run_id)
            ledger.append("attempt_started", {"attempt_id": attempt_id, "game_id": attempt_id})
            ledger.append("ale_reset_observed", {"attempt_id": attempt_id})
            ledger.append("attempt_finished", {"attempt_id": attempt_id, "game_id": attempt_id, "attempt_record": record})

            summary = summarize_run(events_path, run_id=run_id, repo_root=root)
            policy = summary["by_policy"]["test-policy"]
            self.assertEqual(summary["attempted_reset_count"], 1)
            self.assertEqual(policy["completed_games"], 0)
            self.assertEqual(policy["ale_terminated_games"], 1)
            self.assertEqual(policy["terminal_unknown"], 1)
            self.assertEqual(policy["incomplete_games"], 0)
            self.assertIsNone(policy["match_score"])
            self.assertEqual(policy["rgb_verified_player_moves"], 1)
            self.assertEqual(policy["desynchronization_count"], 0)
            self.assertEqual(policy["unexpected_cursor_displacements"], 4)
            self.assertEqual(policy["per_game_records"][0]["recorded_desynchronization_count"], 4)

    def test_outcome_classification_never_converts_incomplete_to_draw(self) -> None:
        self.assertEqual(classify_attempt({"terminal": {"ale_terminated": True, "ale_truncated": False, "ale_reward_total": 1.0}}), "win")
        self.assertEqual(classify_attempt({"terminal": {"ale_terminated": True, "ale_truncated": False, "ale_reward_total": -1.0}}), "loss")
        self.assertEqual(classify_attempt({"terminal": {"ale_terminated": True, "ale_truncated": False, "ale_reward_total": 0.0}}), "terminal_unknown")
        self.assertEqual(classify_attempt({"terminal": {"ale_terminated": False, "ale_truncated": True}}), "ale_truncated")
        self.assertEqual(classify_attempt({"terminal": {"ale_terminated": False, "runner_stop_category": "RUNNER_MAX_WALL_CLOCK"}}), "runner_truncated")
        self.assertEqual(classify_attempt({"terminal": {"ale_terminated": False, "runner_stopped": True}}), "incomplete")

    def test_metrics_keep_wdl_incomplete_and_move_denominators_separate(self) -> None:
        rows = [
            {"attempt_id": "win", "outcome": "win", "player_moves_attempted": 3, "rgb_verified_player_moves": 2, "verified_atari_replies": 2, "desynchronization_count": 0, "ale_frames": 40, "environment_steps": 10, "wall_seconds": 1.5},
            {"attempt_id": "loss", "outcome": "loss", "player_moves_attempted": 2, "rgb_verified_player_moves": 2, "verified_atari_replies": 1, "desynchronization_count": 1, "unexpected_cursor_displacements": 4, "ale_frames": 30, "environment_steps": 8, "wall_seconds": 2.0},
            {"attempt_id": "unknown", "outcome": "terminal_unknown", "player_moves_attempted": 1, "rgb_verified_player_moves": 0, "verified_atari_replies": 0, "desynchronization_count": 0, "ale_frames": 7, "environment_steps": 2, "wall_seconds": 0.4},
            {"attempt_id": "runner-stop", "outcome": "runner_truncated", "player_moves_attempted": 0, "rgb_verified_player_moves": 0, "verified_atari_replies": 0, "desynchronization_count": 0, "ale_frames": 5, "environment_steps": 1, "wall_seconds": 0.1},
        ]
        summary = summarize_attempts(rows)
        self.assertEqual(summary["attempted_games"], 4)
        self.assertEqual(summary["completed_games"], 2)
        self.assertEqual(summary["ale_terminated_games"], 3)
        self.assertEqual((summary["win"], summary["draw"], summary["loss"]), (1, 0, 1))
        self.assertEqual(summary["terminal_unknown"], 1)
        self.assertEqual(summary["runner_truncated"], 1)
        self.assertEqual(summary["incomplete_games"], 1)
        self.assertEqual(summary["incomplete_fraction"], 0.25)
        self.assertEqual(summary["match_score"], 0.5)
        self.assertEqual(summary["match_score_denominator"], 2)
        self.assertEqual(summary["attempted_player_moves"], 6)
        self.assertEqual(summary["rgb_verified_player_moves"], 4)
        self.assertAlmostEqual(summary["move_success_rate"], 4 / 6)
        self.assertAlmostEqual(summary["desynchronization_rate_per_attempted_move"], 1 / 6)
        self.assertEqual(summary["unexpected_cursor_displacements"], 4)
        self.assertEqual(summary["verified_atari_replies"], 3)
        self.assertEqual(summary["ale_frames"], 82)

    def test_zero_denominators_are_undefined_and_duplicate_attempt_ids_fail(self) -> None:
        empty = summarize_attempts([])
        self.assertIsNone(empty["move_success_rate"])
        self.assertIsNone(empty["move_success_wilson_95"])
        self.assertIsNone(empty["match_score"])
        self.assertIsNone(wilson_interval(0, 0))
        row = {"attempt_id": "same", "outcome": "incomplete"}
        with self.assertRaisesRegex(ValueError, "duplicate"):
            summarize_attempts([row, row])

    def test_interrupted_attempt_does_not_fabricate_move_denominators(self) -> None:
        summary = summarize_attempts([{
            "attempt_id": "interrupted",
            "outcome": "incomplete",
            "player_moves_attempted": None,
            "rgb_verified_player_moves": None,
            "desynchronization_count": None,
            "unexpected_cursor_displacements": None,
            "wall_seconds": None,
            "peak_rss_bytes": None,
        }])
        self.assertEqual(summary["attempted_games"], 1)
        self.assertEqual(summary["incomplete_games"], 1)
        self.assertEqual(summary["attempted_player_moves"], 0)
        self.assertEqual(summary["attempts_with_unknown_move_accounting"], 1)
        self.assertEqual(summary["attempts_with_unknown_desynchronization_accounting"], 1)
        self.assertEqual(summary["attempts_with_unknown_cursor_displacement_accounting"], 1)
        self.assertIsNone(summary["move_success_rate"])
        self.assertEqual(summary["attempts_with_unknown_wall_seconds"], 1)
        self.assertEqual(summary["attempts_with_unknown_peak_rss"], 1)


if __name__ == "__main__":
    unittest.main()
