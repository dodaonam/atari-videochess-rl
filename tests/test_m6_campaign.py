"""Frozen M6 configuration and seed/order regression tests."""

from __future__ import annotations

import json
import os
from pathlib import Path
import hashlib
import tempfile
import unittest
from unittest.mock import patch

from videochess_rl.environment import ALEConfig
from videochess_rl.m6.campaign import CONFIG_PATH, M6Campaign, profile_config, stage3_schedule, summarize_run
from videochess_rl.m6.adapter import PolicyIdentity
from videochess_rl.m6.ledger import HashChainLedger, verify_hash_chain


class M6CampaignPlanTests(unittest.TestCase):
    def test_debug_and_default_profiles_are_separate(self) -> None:
        debug = profile_config("development-debug", mode=4)
        official = profile_config("ale-v5-default", mode=4)
        self.assertEqual(debug, ALEConfig(env_id="ALE/VideoChess-v5", obs_type="rgb", frameskip=1,
                                          repeat_action_probability=0.0, mode=4, difficulty=0))
        self.assertEqual(official, ALEConfig(env_id="ALE/VideoChess-v5", obs_type="rgb", frameskip=4,
                                             repeat_action_probability=0.25, mode=4, difficulty=0))
        self.assertNotEqual(debug, official)

    def test_frozen_stage3_seed_roster_counts_and_paired_order(self) -> None:
        schedule = stage3_schedule()
        self.assertEqual(len(schedule), 35)
        self.assertEqual(len({row["game_id"] for row in schedule}), 35)
        counts = {}
        for row in schedule:
            counts[row["policy_id"]] = counts.get(row["policy_id"], 0) + 1
        self.assertEqual(counts, {
            "m5-warm-seed-20261104-post-rl": 10,
            "m5-scratch-seed-20261104-post-rl": 10,
            "m4-behavior-only-seed-20261024": 5,
            "simple-material-heuristic": 5,
            "random-legal": 5,
        })
        for seed in range(20261130, 20261140):
            pair = [row["policy_id"] for row in schedule if row["ale_seed"] == seed and row["policy_id"].startswith("m5-")]
            self.assertEqual(pair[0], "m5-warm-seed-20261104-post-rl" if seed % 2 == 0 else "m5-scratch-seed-20261104-post-rl")
        self.assertEqual({row["ale_seed"] for row in schedule if row["policy_id"] == "random-legal"}, set(range(20261130, 20261135)))

    def test_versioned_stage3_configuration_matches_authorized_limits(self) -> None:
        config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        self.assertEqual(config["environment"], "ALE/VideoChess-v5")
        self.assertEqual(config["rom_sha256"], "d44f2a115393b0a6cbcd5398d62369e652f3670a9ee585883d183e740edad0f7")
        self.assertEqual(config["m5_root_artifact_manifest_sha256"], "a201a254671ad59ae1fecb402abf994d5bf523097f1c3010b5c7fa237ae6dd4c")
        self.assertEqual(config["m4_root_artifact_manifest_sha256"], "f00fde1c59325105e0ffd45bb45eb269dfa303416010c9a0b6c6be47bd9a9921")
        self.assertEqual((config["mode"], config["difficulty"], config["agent_color"]), (4, 0, "white"))
        self.assertEqual((config["frameskip"], config["repeat_action_probability"]), (4, 0.25))
        self.assertEqual(config["campaign_limits"]["maximum_game_attempts"], 35)
        self.assertEqual(config["campaign_limits"]["maximum_gameplay_wall_seconds"], 36000)
        self.assertEqual(config["campaign_limits"]["maximum_artifact_bytes"], 2 * 1024 * 1024 * 1024)
        self.assertEqual(config["episode_limits"]["maximum_wall_seconds"], 900)
        self.assertEqual(config["episode_limits"]["maximum_ale_frames"], 54000)
        self.assertFalse(config["outcome_semantics"]["truncation_is_draw"])

    def test_relative_artifact_root_is_normalized_before_trace_paths_are_built(self) -> None:
        original_cwd = Path.cwd()
        with tempfile.TemporaryDirectory() as temporary:
            os.chdir(temporary)
            try:
                with patch("videochess_rl.m6.campaign.load_policy_roster", return_value={}):
                    campaign = M6Campaign(
                        artifact_root="relative/m6-artifacts",
                        m5_root="/unused/private-m5",
                        m4_root="/unused/private-m4",
                    )
            finally:
                os.chdir(original_cwd)
            self.assertTrue(campaign.artifact_root.is_absolute())
            self.assertEqual(campaign.artifact_root, (Path(temporary) / "relative/m6-artifacts").resolve())

    def test_interrupted_after_reset_is_sealed_without_guessing_or_replaying(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "uv.lock").write_text("version = 1\n", encoding="utf-8")
            run_id = "m6-interruption-test"
            attempt_id = "test-policy-seed-7-slot-000-attempt-0000"
            attempt_dir = root / "artifacts/m6" / run_id / "attempts" / attempt_id
            attempt_dir.mkdir(parents=True)
            run_dir = root / "artifacts/m6" / run_id
            (run_dir / "run-manifest.json").write_text(json.dumps({
                "git_commit": "test-commit",
                "git_tree": "test-tree",
                "source_bundle_sha256": "a" * 64,
                "dependency_lock_sha256": "b" * 64,
                "rom_sha256": "c" * 64,
                "environment_id": "ALE/VideoChess-v5",
                "ale_config": {"mode": 4, "difficulty": 0, "obs_type": "rgb", "frameskip": 4,
                                "repeat_action_probability": 0.25},
                "controller_timing": {"direction_hold_frames": 33},
                "runtime_construction": {"python": "3.12", "gymnasium": "1.4.0", "ale_py": "0.11.2"},
            }), encoding="utf-8")
            reset = b"rgb-reset-fixture"
            (attempt_dir / "reset.rgb").write_bytes(reset)
            reset_rel = (attempt_dir / "reset.rgb").relative_to(root).as_posix()
            events_path = root / "events.jsonl"
            ledger = HashChainLedger(events_path, run_id=run_id)
            ledger.append("attempt_started", {
                "attempt_id": attempt_id,
                "game_id": "game-7",
                "policy_id": "test-policy",
                "ale_seed": 7,
                "start_timestamp_utc": "2026-10-30T00:00:00Z",
            })
            ledger.append("ale_reset_observed", {
                "attempt_id": attempt_id,
                "game_id": "game-7",
                "frame_number": 0,
                "rgb_sha256": hashlib.sha256(reset).hexdigest(),
                "rgb_path": reset_rel,
                "rgb_shape": [210, 160, 3],
                "initial_position_rgb_verified": True,
            })
            ledger.append("ale_action_started", {
                "attempt_id": attempt_id,
                "game_id": "game-7",
                "action_index": 2,
                "action_sequence": 1,
            })

            campaign = M6Campaign.__new__(M6Campaign)
            campaign.repo_root = root
            campaign.artifact_root = root / "artifacts/m6"
            campaign.roster = {"test-policy": (None, PolicyIdentity("test-policy", "test-frozen"))}
            schedule = {"game_id": "game-7", "policy_id": "test-policy", "ale_seed": 7, "slot": 0}
            events = verify_hash_chain(events_path, expected_run_id=run_id)
            record = campaign._recover_interrupted_reset(
                run_id=run_id,
                schedule=schedule,
                attempt_id=attempt_id,
                events=events,
                ledger=ledger,
            )
            self.assertEqual(record["outcome"], "incomplete")
            self.assertIsNone(record["player_moves_attempted"])
            self.assertIsNone(record["rgb_verified_player_moves"])
            self.assertEqual(record["trace_integrity_status"], "sealed_recovery_trace_with_explicit_missing_episode_detail")
            summary = summarize_run(events_path, run_id=run_id, repo_root=root)
            metrics = summary["by_policy"]["test-policy"]
            self.assertEqual(metrics["attempted_games"], 1)
            self.assertEqual(metrics["incomplete_games"], 1)
            self.assertEqual(metrics["attempts_with_unknown_move_accounting"], 1)
            self.assertEqual(metrics["attempts_with_unknown_desynchronization_accounting"], 1)


if __name__ == "__main__":
    unittest.main()
