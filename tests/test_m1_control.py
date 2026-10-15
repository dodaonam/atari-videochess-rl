"""Observable Atari action planning tests."""

from __future__ import annotations

import unittest

from videochess_rl.controller import plan_move


class AtariControlPlanTests(unittest.TestCase):
    def test_e2e3_plan_uses_measured_cursor_and_button_timing(self) -> None:
        actions = plan_move(cursor_origin="d4", uci="e2e3")

        self.assertEqual(
            [(action.index, action.frames) for action in actions],
            [
                (3, 33),
                (0, 1),
                (5, 33),
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


if __name__ == "__main__":
    unittest.main()
