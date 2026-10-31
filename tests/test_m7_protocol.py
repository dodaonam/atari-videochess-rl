from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from videochess_rl.m7.protocol import (
    ALE_SEEDS,
    CONFIG_SCHEMA,
    POLICY_BASE_ORDER,
    build_config,
    build_schedule,
    counterbalanced_policy_order,
    load_frozen_config,
    schedule_sha256,
    validate_config,
    write_frozen_config,
)


class M7ProtocolTests(unittest.TestCase):
    def test_exact_policy_roster_and_post_rl_mapping(self) -> None:
        config = build_config()
        roster = config["accepted_inputs"]["m5"]["policies"]
        self.assertEqual(len(roster), 6)
        self.assertEqual({row["arm"] for row in roster}, {"warm", "scratch"})
        self.assertEqual({row["training_seed"] for row in roster}, {20261104, 20261105, 20261106})
        self.assertTrue(all(row["snapshot_stage"] == "post_rl" for row in roster))
        self.assertEqual(len(POLICY_BASE_ORDER), 9)
        self.assertEqual(len(set(POLICY_BASE_ORDER)), 9)
        self.assertEqual(config["accepted_inputs"]["m4"]["metadata_sha256"], "63615d8d0ed27900fdf86d3f3084ca95cd562f9ec2f9a7e94bca4b0f6301e0c8")
        self.assertEqual(config["accepted_inputs"]["m4"]["sidecar_manifest_file_sha256"], "cc0af4694e45fc23acb740c652dd9a62e1bcaf7851815d179693d09539f0f606")

    def test_schedule_is_exact_unique_complete_and_counterbalanced(self) -> None:
        schedule = build_schedule()
        self.assertEqual(len(schedule), 90)
        self.assertEqual([row["slot"] for row in schedule], list(range(90)))
        self.assertEqual(len({row["game_id"] for row in schedule}), 90)
        self.assertEqual(len({(row["policy_id"], row["ale_seed"]) for row in schedule}), 90)
        for policy in POLICY_BASE_ORDER:
            self.assertEqual(sum(row["policy_id"] == policy for row in schedule), 10)
        for seed in ALE_SEEDS:
            self.assertEqual({row["policy_id"] for row in schedule if row["ale_seed"] == seed}, set(POLICY_BASE_ORDER))
        digest = schedule_sha256(schedule)
        self.assertEqual(len(digest), 64)
        self.assertLessEqual(set(digest), set("0123456789abcdef"))
        self.assertEqual(set(counterbalanced_policy_order(i)[0] for i in range(9)), set(POLICY_BASE_ORDER))
        self.assertTrue(set(ALE_SEEDS).isdisjoint(range(20261130, 20261140)))
        self.assertEqual(schedule, build_config()["research_design"]["schedule"])

    def test_config_freezes_exact_profile_limits_and_analysis_seed(self) -> None:
        config = build_config()
        validate_config(config)
        self.assertEqual(config["schema"], CONFIG_SCHEMA)
        self.assertEqual(config["ale_profile"]["registered_default_max_num_frames_per_episode"], 108000)
        self.assertEqual(config["ale_profile"]["effective_max_num_frames_per_episode"], 500000)
        self.assertEqual(config["ale_profile"]["runner_maximum_post_reset_action_frames"], 432000)
        self.assertEqual(config["resource_limits"]["scheduled_attempts"], 90)
        self.assertEqual(config["resource_limits"]["maximum_wall_seconds_per_attempt"], 1800)
        self.assertEqual(config["resource_limits"]["maximum_campaign_artifact_bytes"], 8 * 1024**3)
        self.assertEqual(config["resource_limits"]["minimum_free_bytes_before_first_attempt"], 12 * 1024**3)
        self.assertEqual(config["resource_limits"]["maximum_process_rss_bytes"], None)
        self.assertEqual(config["resource_limits"]["expected_gameplay_time"]["hours"], 4.4)
        self.assertFalse(config["resource_limits"]["expected_gameplay_time"]["guaranteed"])
        self.assertEqual(config["analysis_freeze"]["bootstrap_resamples"], 10000)
        self.assertEqual(config["analysis_freeze"]["bootstrap_seed"], 20261290)

    def test_config_rejects_seed_or_horizon_mutation_and_refuses_overwrite(self) -> None:
        config = build_config()
        config["research_design"]["ale_evaluation_seeds"][0] += 1
        with self.assertRaises(ValueError):
            validate_config(config)
        config = build_config()
        config["ale_profile"]["effective_max_num_frames_per_episode"] = 108000
        with self.assertRaises(ValueError):
            validate_config(config)
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "frozen.json"
            write_frozen_config(target)
            self.assertEqual(load_frozen_config(target)["schema"], CONFIG_SCHEMA)
            before = target.read_bytes()
            with self.assertRaises(FileExistsError):
                write_frozen_config(target)
            self.assertEqual(target.read_bytes(), before)

    def test_frozen_config_refuses_symbolic_link_inputs(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "frozen.json"
            write_frozen_config(target)
            link = root / "config-link.json"
            link.symlink_to(target)
            with self.assertRaises(ValueError):
                load_frozen_config(link)

    def test_privacy_and_gate_boundaries_are_explicit(self) -> None:
        config = build_config()
        encoded = json.dumps(config)
        self.assertNotIn("/home/", encoded)
        self.assertNotIn("/tmp/", encoded)
        self.assertFalse(config["privacy"]["public_release_authorized"])
        self.assertEqual(config["historical_status"]["g4_status"], "HOLD_NOT_APPROVED")
        self.assertIn("M7-004 and M7-005 require verified independent G4 approval", config["historical_status"]["phase_ii_gate"])
        self.assertEqual(config["elo_disposition"], "Elo not reported: calibrated pool/design not approved or unavailable.")


if __name__ == "__main__":
    unittest.main()
