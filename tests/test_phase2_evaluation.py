"""Phase 2 simulator result accounting tests."""
import unittest

from scripts.improvement.phase2_evaluate import M5_ROOT, OFFICIAL, outcomes, rank


class Phase2EvaluationTests(unittest.TestCase):
    def test_artifact_roots_resolve_from_repository_root(self):
        self.assertEqual((OFFICIAL.name, OFFICIAL.parent.name, OFFICIAL.parent.parent.name),
                         ("official", "videochess-improvement-20261103-v1", "improvement"))
        self.assertEqual(M5_ROOT.name, "m5")
        self.assertEqual(M5_ROOT.parent.name, "artifacts")

    def test_scheduled_denominator_keeps_truncations_and_incompletes_distinct(self):
        rows = [
            {"status": "completed_game", "truncated": False, "agent_reward": 1.0,
             "opponent_id": "random_legal", "agent_color": "white", "agent_decisions": 3},
            {"status": "completed_game", "truncated": False, "agent_reward": 0.0,
             "opponent_id": "random_legal", "agent_color": "black", "agent_decisions": 4},
            {"status": "completed_game", "truncated": True, "agent_reward": 0.0,
             "opponent_id": "simple_material_heuristic", "agent_color": "white", "agent_decisions": 400},
            {"status": "incomplete_policy_deadline", "truncated": None, "agent_reward": None,
             "opponent_id": "simple_material_heuristic", "agent_color": "black", "agent_decisions": 1},
        ]
        result = outcomes(rows, 4)
        self.assertEqual((result["wins"], result["losses"], result["true_draws"]), (1, 0, 1))
        self.assertEqual((result["truncations"], result["incomplete"]), (1, 1))
        self.assertEqual(result["score"], .375)
        self.assertEqual(result["opponent_color_strata"]["simple_material_heuristic/white"]["truncations"], 1)
        self.assertEqual(result["agent_decisions"], 408)
        partial = outcomes(rows[:2], 4)
        self.assertEqual((partial["incomplete"], partial["unattempted"]), (2, 2))

    def test_selection_rank_order_matches_protocol(self):
        stronger_simple = {"outcomes": {"score": .5, "truncations": 0, "incomplete": 0,
            "opponent_color_strata": {"simple_material_heuristic/white": {"score": .4},
                "simple_material_heuristic/black": {"score": .6}}}, "training_decisions": 25000}
        earlier = {"outcomes": {"score": .5, "truncations": 0, "incomplete": 0,
            "opponent_color_strata": {"simple_material_heuristic/white": {"score": .5},
                "simple_material_heuristic/black": {"score": .5}}}, "training_decisions": 50000}
        self.assertGreater(rank(stronger_simple), rank(earlier))


if __name__ == "__main__":
    unittest.main()
