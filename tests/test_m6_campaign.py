"""Frozen M6 configuration and seed/order regression tests."""

from __future__ import annotations

import json
import os
from pathlib import Path
import hashlib
import tempfile
import unittest
from unittest.mock import patch

from videochess_rl.environment import ALEConfig, VideoChessEnv
from videochess_rl.m6.campaign import (
    CONFIG_PATH,
    CONFIG_PATH_V2,
    M6Campaign,
    canonical_schedule_bytes,
    profile_config,
    stage3_schedule,
    stage3_v2_schedule,
    summarize_run,
    validate_stage3_v2_config,
    verify_runtime_matches_lock,
    load_policy_roster,
)
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
        self.assertEqual(config["controller_timing"]["target_fire_settle_windows"], 3)
        self.assertEqual(config["campaign_limits"]["maximum_game_attempts"], 35)
        self.assertEqual(config["campaign_limits"]["maximum_gameplay_wall_seconds"], 36000)
        self.assertEqual(config["campaign_limits"]["gameplay_wall_budget_scope"], "all M6 ALE diagnostics plus Stage 3 evaluation attempts")
        self.assertEqual(config["campaign_limits"]["maximum_artifact_bytes"], 2 * 1024 * 1024 * 1024)
        self.assertEqual(config["episode_limits"]["maximum_wall_seconds"], 900)
        self.assertEqual(config["episode_limits"]["maximum_ale_frames"], 54000)
        self.assertFalse(config["outcome_semantics"]["truncation_is_draw"])

    def test_v1_and_v2_frame_and_wall_limits_are_versioned_separately(self) -> None:
        v1 = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        v2 = json.loads(CONFIG_PATH_V2.read_text(encoding="utf-8"))
        validate_stage3_v2_config(v2)
        self.assertEqual(hashlib.sha256(CONFIG_PATH.read_bytes()).hexdigest(),
                         "05aedeb30efb8b6b97667c44f9d606b58d4da8ae20800d4ef143e629420cebac")
        self.assertEqual(v1["episode_limits"]["maximum_ale_frames"], 54_000)
        self.assertEqual(v1["episode_limits"]["maximum_wall_seconds"], 900)
        self.assertEqual(v1["campaign_limits"]["maximum_gameplay_wall_seconds"], 36_000)
        self.assertEqual(v2["episode_limits"]["maximum_ale_frames"], 432_000)
        self.assertEqual(v2["episode_limits"]["maximum_wall_seconds"], 1_800)
        self.assertEqual(v2["campaign_limits"]["maximum_gameplay_wall_seconds"], 43_200)
        self.assertEqual(v2["ale_horizon"]["max_num_frames_per_episode"], 500_000)
        self.assertNotEqual(v1["schema"], v2["schema"])

    def test_stage3_v2_schedule_is_exactly_paired_and_preordered(self) -> None:
        schedule = stage3_v2_schedule()
        self.assertEqual(len(schedule), 20)
        self.assertEqual(len({row["game_id"] for row in schedule}), 20)
        self.assertEqual({row["policy_id"] for row in schedule}, {
            "m5-warm-seed-20261104-post-rl", "m5-scratch-seed-20261104-post-rl",
        })
        for seed in range(20261130, 20261140):
            pair = [row["policy_id"] for row in schedule if row["ale_seed"] == seed]
            expected = ["m5-warm-seed-20261104-post-rl", "m5-scratch-seed-20261104-post-rl"]
            if seed % 2:
                expected.reverse()
            self.assertEqual(pair, expected)
        self.assertEqual(hashlib.sha256(canonical_schedule_bytes(schedule)).hexdigest(),
                         "be4e6548e6fd3e3db4605e6b55fbe860848dccb2df87d8a7122145bdabe22ffc")
        self.assertEqual(hashlib.sha256(CONFIG_PATH_V2.read_bytes()).hexdigest(),
                         "663651050db80ab027b452241c7d39837ec7986927c0aefc7c7be631f459a49b")

    def test_stage3_v2_rejects_roster_and_underlying_horizon_drift(self) -> None:
        config = json.loads(CONFIG_PATH_V2.read_text(encoding="utf-8"))
        bad_roster = json.loads(json.dumps(config))
        bad_roster["policy_roster"][0]["checkpoint_sha256"] = "0" * 64
        with self.assertRaisesRegex(RuntimeError, "roster"):
            validate_stage3_v2_config(bad_roster)
        bad_horizon = json.loads(json.dumps(config))
        bad_horizon["ale_horizon"]["max_num_frames_per_episode"] = 108_000
        with self.assertRaisesRegex(RuntimeError, "horizon"):
            validate_stage3_v2_config(bad_horizon)

    def test_installed_ale_honors_explicit_v2_horizon_without_reset_or_step(self) -> None:
        with VideoChessEnv(ALEConfig.default_v5(mode=4)) as default_env:
            default_info = default_env.runtime_info()
            self.assertEqual(default_info["ale_episode_frame_limit"], 108_000)
        extended = ALEConfig(
            env_id="ALE/VideoChess-v5", obs_type="rgb", frameskip=4,
            repeat_action_probability=0.25, mode=4, difficulty=0,
            max_num_frames_per_episode=500_000,
        )
        with VideoChessEnv(extended) as extended_env:
            info = extended_env.runtime_info()
            self.assertEqual(info["registered_defaults"]["max_num_frames_per_episode"], 108_000)
            self.assertEqual(info["ale_episode_frame_limit"], 500_000)
            self.assertEqual(info["instance_runtime"]["max_num_frames_per_episode"], 500_000)
            self.assertEqual(info["instance_runtime"]["mode"], 4)
            self.assertEqual(info["instance_runtime"]["difficulty"], 0)
            self.assertEqual(info["instance_runtime"]["observation_shape"], [210, 160, 3])
            self.assertEqual(info["rom_sha256"], "d44f2a115393b0a6cbcd5398d62369e652f3670a9ee585883d183e740edad0f7")
            self.assertEqual(info["instance_runtime"]["action_set"], list(range(10)))
            self.assertEqual(info["instance_runtime"]["frameskip"], 4)
            self.assertEqual(info["instance_runtime"]["repeat_action_probability"], 0.25)
            self.assertEqual(info["available_modes"], [0, 1, 2, 3, 4])
            self.assertEqual(info["available_difficulties"], [0])

    def test_v2_policy_roster_loader_returns_only_the_two_frozen_m5_policies(self) -> None:
        warm = PolicyIdentity(
            "m5-warm-seed-20261104-post-rl", "frozen_m5_double_dqn_q_policy",
            checkpoint_sha256="0b2405017a8e1d539851f0cd278883d3fd23936fb5c2f7962c813590a6fd1767",
        )
        scratch = PolicyIdentity(
            "m5-scratch-seed-20261104-post-rl", "frozen_m5_double_dqn_q_policy",
            checkpoint_sha256="3749b0c0b6ae44d3ad5d6bf0863b60937a59fbe881e0bdf4932bdce6033ca400",
        )
        with patch("videochess_rl.m6.campaign.verify_selected_m5_root", return_value={
            "schema": "videochess-m5-artifact-manifest/1.0",
        }), patch("videochess_rl.m6.campaign._load_m5_path", side_effect=(Path("warm.pt"), Path("scratch.pt"))), \
                patch("videochess_rl.m6.campaign.load_m5_policy", side_effect=(
                    (object(), warm), (object(), scratch),
                )) as loader, patch("videochess_rl.m6.campaign.load_m4_policy") as m4_loader, \
                patch("videochess_rl.m6.campaign.load_baseline") as baseline_loader:
            roster = load_policy_roster("/unused/m5", None, m5_only=True)
        self.assertEqual(set(roster), {warm.policy_id, scratch.policy_id})
        self.assertEqual(loader.call_count, 2)
        m4_loader.assert_not_called()
        baseline_loader.assert_not_called()

    def test_installed_runtime_matches_committed_dependency_lock(self) -> None:
        identity = verify_runtime_matches_lock(Path(__file__).resolve().parents[1])
        self.assertEqual(identity["installed_packages"]["gymnasium"], "1.4.0")
        self.assertEqual(identity["installed_packages"]["ale-py"], "0.11.2")
        self.assertIn(identity["installed_packages"]["torch"], identity["locked_package_versions"]["torch"])

    def test_stage3_roster_pins_exact_accepted_checkpoint_identities(self) -> None:
        config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        identities = {
            row["policy_id"]: (row.get("checkpoint_sha256"), row.get("sidecar_sha256"))
            for row in config["policy_roster"]
        }
        self.assertEqual(identities, {
            "m5-warm-seed-20261104-post-rl": (
                "0b2405017a8e1d539851f0cd278883d3fd23936fb5c2f7962c813590a6fd1767",
                "80d8689e4b349576c5708bb4dce3451e5a8c64d81470cd6f4273a4746844b682",
            ),
            "m5-scratch-seed-20261104-post-rl": (
                "3749b0c0b6ae44d3ad5d6bf0863b60937a59fbe881e0bdf4932bdce6033ca400",
                "1c15e5bc4ba2437df113671dc316accbdfe6d8b59069ed29ed187daebf4fff1e",
            ),
            "m4-behavior-only-seed-20261024": (
                "724ac730f3c5f2d01b48b26eb7670a3c764978a3dd4d6702b3057a99ab1a90a4",
                "cc0af4694e45fc23acb740c652dd9a62e1bcaf7851815d179693d09539f0f606",
            ),
            "simple-material-heuristic": (None, None),
            "random-legal": (None, None),
        })

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

    def test_v2_campaign_uses_isolated_artifact_namespace_and_its_own_limits(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "artifacts/m6"
            with patch("videochess_rl.m6.campaign.load_policy_roster", return_value={}) as loader:
                campaign = M6Campaign(
                    artifact_root=root,
                    m5_root="/unused/private-m5",
                    m4_root=None,
                    config_path=CONFIG_PATH_V2,
                )
            loader.assert_called_once()
            self.assertTrue(loader.call_args.kwargs["m5_only"])
            self.assertEqual(campaign.artifact_root, root / "v2")
            self.assertEqual(campaign.episode_limits["maximum_ale_frames"], 432_000)
            self.assertEqual(campaign.episode_limits["maximum_wall_seconds"], 1_800)
            self.assertEqual(campaign.campaign_limits["maximum_artifact_bytes"], 8 * 1024**3)

    def test_global_gameplay_budget_counts_all_stage_attempt_records(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            campaign = M6Campaign.__new__(M6Campaign)
            campaign.artifact_root = root / "artifacts/m6"
            for run_id, attempt_id, wall in (("stage1-run", "a", 7.5), ("stage2-run", "b", 12.0), ("stage3-run", "c", None)):
                path = campaign.artifact_root / run_id / "attempts" / attempt_id / "attempt.json"
                path.parent.mkdir(parents=True)
                record = {"wall_seconds": wall}
                if wall is None:
                    record.update({"start_timestamp_utc": "2026-10-30T00:00:00Z", "end_timestamp_utc": "2026-10-30T00:00:10Z"})
                path.write_text(json.dumps(record), encoding="utf-8")
            self.assertEqual(campaign._cumulative_gameplay_wall_seconds(), 29.5)
            self.assertEqual(campaign._cumulative_gameplay_wall_seconds(exclude_run_id="stage3-run"), 19.5)

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
