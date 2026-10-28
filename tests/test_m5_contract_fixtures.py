"""Validate preparatory M5 oracle data; this is not a DDQN learner test."""

from __future__ import annotations

import json
import math
import unittest
from pathlib import Path


FIXTURE = Path(__file__).parent / "fixtures" / "m5_double_dqn_targets.json"
REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


class M5DoubleDqnFixtureTests(unittest.TestCase):
    def test_proposed_evaluation_schedule_matches_config_and_protocol(self) -> None:
        config = json.loads((REPOSITORY_ROOT / "configs/rl/m5-double-dqn-v1.json").read_text(encoding="utf-8"))
        protocol = (REPOSITORY_ROOT / "docs/04-research/M5_EXPERIMENT_PROTOCOL.md").read_text(encoding="utf-8")
        evaluation = config["evaluation"]
        checkpoints = evaluation["policy_checkpoints"]
        checkpoint_count = sum(value for key, value in checkpoints.items() if key != "total")
        games_per_checkpoint = (
            len(evaluation["seeds"])
            * len(config["environment"]["opponents"])
            * len(config["environment"]["agent_colors"])
            * evaluation["games_per_opponent_per_color_per_seed"]
        )

        self.assertTrue(evaluation["both_agent_colors"])
        self.assertEqual(checkpoint_count, checkpoints["total"])
        self.assertEqual(games_per_checkpoint, evaluation["games_per_policy_checkpoint"])
        self.assertEqual(games_per_checkpoint * checkpoint_count, evaluation["planned_total_games"])
        self.assertEqual(evaluation["games_per_policy_checkpoint"], 40)
        self.assertEqual(evaluation["planned_total_games"], 360)
        self.assertEqual(evaluation["max_wall_minutes_per_checkpoint"], 20)
        self.assertEqual(evaluation["aggregate_wall_hours_hard_cap"], 3)
        self.assertIn("40 games per policy checkpoint", protocol)
        self.assertIn("complete schedule is **360 games**", protocol)

    def test_online_target_disagreement_uses_online_action_in_target_value(self) -> None:
        document = json.loads(FIXTURE.read_text(encoding="utf-8"))
        self.assertEqual(document["schema"], "videochess-m5-double-dqn-target-fixture/1.0")
        case = next(row for row in document["cases"] if row["id"] == "online_target_disagree_nonterminal")
        online_action = max(case["legal_uci"], key=lambda uci: (case["q_online_by_uci"][uci], tuple(-ord(c) for c in uci)))
        self.assertEqual(online_action, case["expected_online_action_uci"])
        target_preferred = max(case["legal_uci"], key=lambda uci: case["q_target_by_uci"][uci])
        self.assertNotEqual(online_action, target_preferred)
        target_value = case["q_target_by_uci"][online_action]
        calculated = case["reward_agent"] + document["gamma"] * case["bootstrap_mask"] * target_value
        self.assertAlmostEqual(calculated, case["expected_bellman_target"], places=12)

    def test_terminal_and_valid_truncation_masks_are_distinct(self) -> None:
        document = json.loads(FIXTURE.read_text(encoding="utf-8"))
        cases = {row["id"]: row for row in document["cases"]}
        terminal = cases["true_terminal_no_bootstrap"]
        self.assertEqual(terminal["legal_uci"], [])
        self.assertEqual(terminal["bootstrap_mask"], 0)
        self.assertIsNone(terminal["expected_online_action_uci"])
        self.assertEqual(terminal["expected_bellman_target"], terminal["reward_agent"])

        automatic_draw = cases["automatic_draw_terminal_has_raw_board_moves_but_no_bootstrap_candidates"]
        self.assertEqual(automatic_draw["termination"], "seventyfive_moves")
        self.assertIn("test_seventyfive_move_rule_is_automatic_after_full_transition", automatic_draw["source_test"])
        self.assertTrue(automatic_draw["terminal_fen"])
        self.assertGreater(automatic_draw["raw_board_legal_uci_count"], 0)
        self.assertEqual(automatic_draw["legal_uci"], [])
        self.assertEqual(automatic_draw["bootstrap_mask"], 0)
        self.assertEqual(automatic_draw["expected_bellman_target"], 0.0)

        truncated = cases["valid_time_limit_truncation_bootstraps"]
        self.assertTrue(truncated["legal_uci"])
        self.assertEqual(truncated["bootstrap_mask"], 1)
        target = truncated["reward_agent"] + document["gamma"] * truncated["q_target_by_uci"][truncated["expected_online_action_uci"]]
        self.assertAlmostEqual(target, truncated["expected_bellman_target"], places=12)
        self.assertTrue(math.isfinite(target))


if __name__ == "__main__":
    unittest.main()
