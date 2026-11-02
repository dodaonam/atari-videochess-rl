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


class RepetitionPolicy:
    policy_id = "test_repetition_policy"

    @property
    def config(self) -> dict[str, object]:
        return {"moves": ["g8f6", "f6g8"]}

    def __init__(self) -> None:
        self.index = 0

    def reset_episode(self, *, seed: int) -> None:
        del seed
        self.index = 0

    def choose_move(self, observation, legal_moves, rng):
        del observation, rng
        moves = ("g8f6", "f6g8")
        move = chess.Move.from_uci(moves[self.index % len(moves)])
        self.index += 1
        if move not in legal_moves:
            raise AssertionError(f"fixture move {move.uci()} is not legal")
        return move


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

    def test_promotion_material_gain_is_counted_once(self) -> None:
        board = chess.Board("8/P6k/8/8/8/8/8/7K w - - 0 1")
        expected_gain = {
            chess.QUEEN: 800,
            chess.ROOK: 400,
            chess.BISHOP: 230,
            chess.KNIGHT: 220,
        }
        for piece_type, score in expected_gain.items():
            move = chess.Move(chess.A7, chess.A8, promotion=piece_type)
            with self.subTest(promotion=chess.piece_name(piece_type)):
                self.assertEqual(SimpleHeuristicAgent._score_move(board, move, chess.WHITE), score)

    def test_capturing_a_queen_outranks_double_counted_quiet_promotion(self) -> None:
        board = chess.Board("8/P6k/8/4q3/4R3/8/8/7K w - - 0 1")
        simulator = ChessSimulator(FirstLegalPolicy())
        observation = simulator.reset(seed=11, initial_board=board)

        move = SimpleHeuristicAgent().choose_move(observation, simulator.legal_moves, random.Random(12))

        self.assertEqual(move.uci(), "e4e5")
        self.assertEqual(SimpleHeuristicAgent._score_move(board, chess.Move.from_uci("a7a8q"), chess.WHITE), 800)
        self.assertEqual(SimpleHeuristicAgent._score_move(board, chess.Move.from_uci("e4e5"), chess.WHITE), 945)

    def test_capture_promotion_counts_promoted_material_and_capture_preference_once(self) -> None:
        board = chess.Board("2r5/1P6/7k/8/8/8/8/7K w - - 0 1")
        score = SimpleHeuristicAgent._score_move(board, chess.Move.from_uci("b7c8q"), chess.WHITE)
        self.assertEqual(score, 1325)

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
        self.assertIn("capture preference", heuristic_config["evaluation"])
        self.assertNotIn("promotion", heuristic_config["evaluation"])

    def test_fen_only_heuristic_observation_does_not_override_history_authority(self) -> None:
        cycle = ("g1f3", "g8f6", "f3g1", "f6g8")
        board = chess.Board()
        for uci in cycle * 3:
            board.push_uci(uci)
        opponent = RepetitionPolicy()
        simulator = ChessSimulator(opponent)
        observation = simulator.reset(seed=13, initial_board=board)
        position_only = chess.Board(observation.fen)

        self.assertTrue(board.is_repetition(4))
        self.assertFalse(position_only.is_repetition(4))
        heuristic_move = SimpleHeuristicAgent().choose_move(
            observation, simulator.legal_moves, random.Random(14)
        )
        self.assertIn(heuristic_move.uci(), observation.legal_moves_uci)

        simulator.step_uci("g1f3")
        result = simulator.step_uci("f3g1")
        self.assertTrue(result.terminated)
        self.assertEqual(result.outcome_reason, "fivefold_repetition")


if __name__ == "__main__":
    unittest.main()
