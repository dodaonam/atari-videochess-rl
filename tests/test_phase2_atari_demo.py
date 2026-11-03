"""Outcome categories for bounded real-ALE evaluation and selected-policy loading."""
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch

from videochess_rl.improvement.atari_eval import classify, public_attempt_metadata
from videochess_rl.improvement.live import demo_footer_text


class AtariOutcomeCategoryTests(unittest.TestCase):
    def test_terminal_reward_does_not_relabel_incomplete_attempts(self):
        base = {"reset": {"initial_position_verified_from_rgb": True}, "terminal": {"ale_terminated": True}}
        self.assertEqual(classify({**base, "terminal": {**base["terminal"], "ale_reward_total": 1.0}}),
                         "true_atari_win")
        self.assertEqual(classify({**base, "terminal": {**base["terminal"], "ale_reward_total": -1.0}}),
                         "true_atari_loss")
        self.assertEqual(classify({**base, "terminal": {**base["terminal"], "ale_reward_total": 0.0}}),
                         "ale_terminal_zero_reward_outcome_unresolved")

    def test_reset_failure_desync_truncation_and_limit_are_distinct(self):
        self.assertEqual(classify({"reset": {}, "terminal": {}}), "reset_or_startup_failure")
        self.assertEqual(classify({"reset": {"initial_position_verified_from_rgb": True},
                                   "terminal": {"ale_truncated": True}}), "incomplete_ale_truncation")
        self.assertEqual(classify({"reset": {"initial_position_verified_from_rgb": True},
                                   "terminal": {"runner_stop_category": "CONTROLLER_BOARD_DESYNCHRONIZED"}}),
                         "board_desynchronization")
        self.assertEqual(classify({"reset": {"initial_position_verified_from_rgb": True},
                                   "terminal": {"runner_stop_category": "RUNNER_MAX_PLAYER_MOVES"}}),
                         "incomplete_bounded_attempt")

    def test_public_attempt_metadata_keeps_aggregates_and_removes_private_detail(self):
        source = {"seed": 42, "verified_opponent_moves": 9, "private_trace_sha256": "a" * 64,
                  "raw_trace": "artifacts/private/attempt.json",
                  "verified_atari_opponent_uci": ["e7e5", "b8c6"],
                  "future_move_payload": [{"uci": "c7c5"}]}
        result = public_attempt_metadata(source)
        self.assertEqual(result["verified_opponent_moves"], 9)
        self.assertEqual(result["private_trace_sha256"], "a" * 64)
        self.assertNotIn("raw_trace", result)
        self.assertNotIn("verified_atari_opponent_uci", result)
        self.assertNotIn("future_move_payload", result)


class DemoSeedTests(unittest.TestCase):
    def test_footer_distinguishes_custom_atari_seed_from_model_seed(self):
        self.assertEqual(demo_footer_text(123456, 20261103, 24),
                         "Atari reset seed: 123456 • model training seed: 20261103 • move cap 24")

    def test_cli_passes_custom_seed_to_viewer_without_starting_atari(self):
        from videochess_rl.improvement import demo

        identity = SimpleNamespace(policy_id="M4-A_behavior_cloning", policy_type="behavior_cloning",
                                   training_seed=20261103)
        with TemporaryDirectory() as temp:
            with patch.object(demo, "ARTIFACTS", Path(temp)), \
                 patch.object(demo, "load_demo_policy", return_value=(object(), identity)), \
                 patch.object(demo, "LiveDemoWindow") as viewer:
                self.assertEqual(demo.main(["--policy", "m4-a", "--seed", "123456"]), 0)
                self.assertEqual(viewer.call_args.kwargs["demo_seed"], 123456)
                self.assertEqual(viewer.call_args.kwargs["identity"].training_seed, 20261103)

    def test_optional_external_gui_requires_an_explicit_path(self):
        import sys
        from videochess_rl.improvement import existing_demo

        with patch.object(sys, "argv", ["existing_demo"]):
            with self.assertRaises(SystemExit) as error:
                existing_demo.main()
        self.assertEqual(error.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
