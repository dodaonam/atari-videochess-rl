from __future__ import annotations

import unittest

from scripts.analyze_m7_campaign import _track_table, m7_seed_grid_svg, outcome_svg


class M7ReportTests(unittest.TestCase):
    def test_outcome_table_reports_scheduled_started_and_not_started_denominators(self) -> None:
        table = "\n".join(_track_table("M7 policy outcomes", {
            "policy-a": {"scheduled": 10, "started_after_ale_reset": 8, "not_started": 2,
                         "wins": 1, "draws": 0, "losses": 3, "incomplete": 4,
                         "terminal_wdl_denominator": 4, "terminal_only_game_score": 0.25},
        }))
        self.assertIn("| Policy | Scheduled | Started | W / D / L |", table)
        self.assertIn("| `policy-a` | 10 | 8 | 1 / 0 / 3 |", table)
        self.assertIn("| `policy-a` | 10 | 8 | 1 / 0 / 3 | 0 | 0 | 4 | 2 | 0.250 (4) |", table)

    def _rows(self):
        outcomes = ("win", "draw", "loss", "terminal_unknown", "truncated", "incomplete", "not_started", "win", "loss", "incomplete")
        return {
            "policy <unsafe>": {
                "scheduled": 10,
                "wins": 2,
                "draws": 1,
                "losses": 2,
                "terminal_unknown": 1,
                "truncated": 1,
                "incomplete": 2,
                "not_started": 1,
                "per_seed_cells": [
                    {"ale_seed": 20261201 + i, "outcome": outcome}
                    for i, outcome in enumerate(outcomes)
                ],
            }
        }

    def test_outcome_chart_retains_all_scheduled_categories_and_escapes_labels(self) -> None:
        svg = outcome_svg(self._rows())
        self.assertIn("scheduled outcome categories", svg)
        self.assertIn("&lt;unsafe&gt;", svg)
        for category in ("wins", "draws", "losses", "terminal unknown", "truncated", "incomplete", "not started"):
            self.assertIn(category, svg)

    def test_shared_seed_grid_has_one_cell_for_each_frozen_policy_seed(self) -> None:
        svg = m7_seed_grid_svg(self._rows())
        self.assertIn("20261201–20261210", svg)
        self.assertEqual(svg.count("<rect x="), 10)
        self.assertIn("Each column is a shared seed block", svg)


if __name__ == "__main__":
    unittest.main()
