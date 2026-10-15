"""Observable Atari action planning tests."""

from __future__ import annotations

import unittest

import chess

from videochess_rl.controller import ControllerTiming, plan_cursor_route, plan_move


class AtariControlPlanTests(unittest.TestCase):
    def test_e2e3_plan_uses_measured_cursor_and_button_timing(self) -> None:
        actions = plan_move(cursor_origin="d4", uci="e2e3")

        self.assertEqual(
            [(action.index, action.frames) for action in actions],
            [
                (8, 33),
                (0, 1),
                (5, 33),
                (0, 33),
                (1, 1),
                (0, 1),
                (2, 33),
                (0, 33),
                (1, 1),
                (0, 1),
            ],
        )

    def test_plan_rejects_illegal_or_malformed_moves(self) -> None:
        with self.assertRaises(ValueError):
            plan_move(cursor_origin="d4", uci="e2e5")
        with self.assertRaises(ValueError):
            plan_move(cursor_origin="z9", uci="e2e3")

    def test_plan_move_uses_current_board_cursor_and_timing_profile(self) -> None:
        board = chess.Board()
        board.push_uci("e2e3")
        board.push_uci("c7c5")
        timing = ControllerTiming(direction_frames=12, fire_settle_frames=14, fire_press_frames=2)

        actions = plan_move(cursor_origin="c7", uci="e3e4", board=board, timing=timing)

        self.assertEqual((actions[0].index, actions[0].frames, actions[0].cursor_after), (8, 12, "d6"))
        self.assertEqual((actions[2].index, actions[2].frames, actions[2].cursor_after), (8, 12, "e5"))
        self.assertIn((1, 2), [(action.index, action.frames) for action in actions])
        self.assertIn((0, 14), [(action.index, action.frames) for action in actions])
        target_navigation = [action for action in actions if action.phase == "selected_target_navigation"]
        self.assertTrue(target_navigation)
        self.assertTrue(all(action.cursor_after is None for action in target_navigation))

    def test_cursor_route_uses_observed_and_calibrated_diagonal_actions(self) -> None:
        actions = plan_cursor_route("d4", "e5")

        self.assertEqual([(action.index, action.frames, action.cursor_after) for action in actions], [(6, 33, "e5")])

    def test_plan_move_rejects_move_legal_only_in_the_start_position(self) -> None:
        board = chess.Board()
        board.push_uci("e2e3")
        board.push_uci("c7c5")

        with self.assertRaisesRegex(ValueError, "current position"):
            plan_move(cursor_origin="c7", uci="e2e4", board=board)


if __name__ == "__main__":
    unittest.main()
