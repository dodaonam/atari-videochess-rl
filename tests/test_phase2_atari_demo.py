"""Outcome categories for bounded real-ALE evaluation and selected-policy loading."""
import unittest

from videochess_rl.improvement.atari_eval import classify


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


if __name__ == "__main__":
    unittest.main()
