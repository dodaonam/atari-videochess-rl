from __future__ import annotations

import unittest

from scripts.analyze_m7_campaign import m7_seed_grid_svg, outcome_svg


class M7ReportTests(unittest.TestCase):
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
