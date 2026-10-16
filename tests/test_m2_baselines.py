"""Seeded and legal-move checks for M2 baseline policies."""

from __future__ import annotations

import random
import unittest

import chess

from videochess_rl.baselines import RandomLegalAgent, SimpleHeuristicAgent
from videochess_rl.simulator import ChessSimulator


class FirstLegalPolicy:
    policy_id = "test_first"

    @property
    def config(self) -> dict[str, object]:
        return {}

    def choose_move(self, observation, legal_moves, rng):
        del observation, rng
        return chess.Move.from_uci(sorted(move.uci() for move in legal_moves)[0])


class BaselineAgentTests(unittest.TestCase):
    def test_random_agent_is_seeded_and_independent_of_candidate_order(self) -> None:
        simulator = ChessSimulator(FirstLegalPolicy())
        observation = simulator.reset(seed=1)
        moves = simulator.legal_moves
        policy = RandomLegalAgent()

        first = policy.choose_move(observation, moves, random.Random(2026))
        second = policy.choose_move(observation, tuple(reversed(moves)), random.Random(2026))
        third = policy.choose_move(observation, moves, random.Random(2027))

        self.assertEqual(first, second)
        self.assertIn(first, moves)
        self.assertIn(third, moves)
        self.assertEqual(policy.policy_id, "random_legal")

    def test_random_agent_rejects_empty_action_set(self) -> None:
        simulator = ChessSimulator(FirstLegalPolicy())
        observation = simulator.reset(seed=2)
        with self.assertRaises(ValueError):
            RandomLegalAgent().choose_move(observation, (), random.Random(1))

    def test_heuristic_agent_selects_immediate_white_checkmate(self) -> None:
        board = chess.Board("7k/8/5KQ1/8/8/8/8/8 w - - 0 1")
        simulator = ChessSimulator(FirstLegalPolicy())
        observation = simulator.reset(seed=3, initial_board=board)

        move = SimpleHeuristicAgent().choose_move(observation, simulator.legal_moves, random.Random(5))

        self.assertEqual(move.uci(), "g6g7")
        after = board.copy()
        after.push(move)
        self.assertTrue(after.is_checkmate())

    def test_heuristic_agent_selects_immediate_black_checkmate(self) -> None:
        board = chess.Board("8/8/8/8/8/5kq1/8/7K b - - 0 1")
        simulator = ChessSimulator(FirstLegalPolicy())
        observation = simulator.reset(seed=4, agent_color=chess.BLACK, initial_board=board)

        move = SimpleHeuristicAgent().choose_move(observation, simulator.legal_moves, random.Random(6))

        self.assertEqual(move.uci(), "g3g2")
        after = board.copy()
        after.push(move)
        self.assertTrue(after.is_checkmate())

    def test_heuristic_prefers_a_safe_material_capture_to_quiet_moves(self) -> None:
        board = chess.Board("7k/8/8/3p4/4P3/8/8/7K w - - 0 1")
        simulator = ChessSimulator(FirstLegalPolicy())
        observation = simulator.reset(seed=7, initial_board=board)

        move = SimpleHeuristicAgent().choose_move(observation, simulator.legal_moves, random.Random(8))

        self.assertEqual(move.uci(), "e4d5")
        self.assertIn(move, board.legal_moves)

    def test_heuristic_is_seeded_when_multiple_moves_have_equal_score(self) -> None:
        simulator = ChessSimulator(FirstLegalPolicy())
        observation = simulator.reset(seed=9)
        agent = SimpleHeuristicAgent()

        first = agent.choose_move(observation, simulator.legal_moves, random.Random(10))
        second = agent.choose_move(observation, simulator.legal_moves, random.Random(10))
        self.assertEqual(first, second)
        self.assertIn(first.uci(), observation.legal_moves_uci)

    def test_policy_configs_are_explicit_and_engine_free(self) -> None:
        random_config = RandomLegalAgent().config
        heuristic_config = SimpleHeuristicAgent().config

        self.assertIn("uniform", random_config["selection"])
        self.assertEqual(heuristic_config["search_plies"], 1)
        self.assertNotIn("stockfish", str(heuristic_config).lower())
        self.assertNotIn("engine", str(heuristic_config).lower())


if __name__ == "__main__":
    unittest.main()
