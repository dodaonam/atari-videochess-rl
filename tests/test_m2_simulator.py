"""Focused rule, lifecycle, and transition-contract checks for M2."""

from __future__ import annotations

import random
import unittest
from dataclasses import FrozenInstanceError

import chess

from videochess_rl.simulator import (
    ChessSimulator,
    EpisodeStateError,
    InvalidActionError,
    Observation,
    OpponentPolicyError,
)


class FirstLegalPolicy:
    policy_id = "test_first_legal"

    @property
    def config(self) -> dict[str, object]:
        return {"selection": "first legal UCI"}

    def choose_move(self, observation, legal_moves, rng):
        del observation, rng
        if not legal_moves:
            raise AssertionError("policy should not be called without legal moves")
        return chess.Move.from_uci(sorted(move.uci() for move in legal_moves)[0])


class ScriptedPolicy:
    policy_id = "test_scripted"

    def __init__(self, *ucis: str) -> None:
        self.ucis = list(ucis)
        self.index = 0

    @property
    def config(self) -> dict[str, object]:
        return {"moves": list(self.ucis)}

    def reset_episode(self, *, seed: int) -> None:
        del seed
        self.index = 0

    def choose_move(self, observation, legal_moves, rng):
        del observation, rng
        if self.index >= len(self.ucis):
            raise AssertionError("scripted policy ran out of moves")
        uci = self.ucis[self.index]
        self.index += 1
        move = chess.Move.from_uci(uci)
        if move not in legal_moves:
            raise AssertionError(f"test fixture move is illegal: {uci}")
        return move


class ResettablePolicy:
    policy_id = "test_resettable"

    def __init__(self, *ucis: str, fail_at: int | None = None) -> None:
        self.ucis = tuple(ucis)
        self.fail_at = fail_at
        self.index = 0
        self.reset_seeds: list[int] = []

    @property
    def config(self) -> dict[str, object]:
        return {"moves": list(self.ucis), "fail_at": self.fail_at}

    def reset_episode(self, *, seed: int) -> None:
        self.index = 0
        self.reset_seeds.append(seed)

    def choose_move(self, observation, legal_moves, rng):
        del observation, rng
        self.index += 1
        if self.index == self.fail_at:
            raise RuntimeError("configured stateful policy failure")
        if not self.ucis:
            raise AssertionError("no scripted moves configured")
        uci = self.ucis[(self.index - 1) % len(self.ucis)]
        move = chess.Move.from_uci(uci)
        if move not in legal_moves:
            raise AssertionError(f"test fixture move is illegal: {uci}")
        return move


class MutableConfigPolicy(FirstLegalPolicy):
    policy_id = "test_mutable_config"

    def __init__(self) -> None:
        self.version = 1

    @property
    def config(self) -> dict[str, object]:
        return {"version": self.version}


class RaisingPolicy:
    policy_id = "test_raising"

    @property
    def config(self) -> dict[str, object]:
        return {"failure": "intentional test exception"}

    def choose_move(self, observation, legal_moves, rng):
        del observation, legal_moves, rng
        raise RuntimeError("expected test failure")


class InvalidPolicy:
    policy_id = "test_invalid"

    @property
    def config(self) -> dict[str, object]:
        return {}

    def choose_move(self, observation, legal_moves, rng):
        del observation, legal_moves, rng
        return chess.Move.from_uci("e2e5")


def board_after(*ucis: str) -> chess.Board:
    board = chess.Board()
    for uci in ucis:
        board.push_uci(uci)
    return board


class ChessSimulatorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.simulator = ChessSimulator(ScriptedPolicy("e7e5"))
        self.initial_observation = self.simulator.reset(seed=7)

    def test_observation_is_immutable_and_board_copy_cannot_mutate_rules_state(self) -> None:
        self.assertIsInstance(self.initial_observation, Observation)
        with self.assertRaises(FrozenInstanceError):
            self.initial_observation.fen = "corrupted"  # type: ignore[misc]
        with self.assertRaises(AttributeError):
            self.initial_observation.legal_moves_uci.append("e2e5")  # type: ignore[attr-defined]

        external_board = self.simulator.board
        external_board.push_uci("e2e4")
        self.assertEqual(self.simulator.board.ply(), 0)
        self.assertEqual(self.simulator.observation.fen, self.initial_observation.fen)
        self.assertEqual(self.initial_observation.opponent_id, "test_scripted")
        self.assertEqual(self.initial_observation.opponent_config_json, '{"moves":["e7e5"]}')

    def test_reset_copies_custom_initial_board_with_its_history(self) -> None:
        external_board = board_after("e2e4", "e7e5")
        simulator = ChessSimulator(FirstLegalPolicy())
        observation = simulator.reset(seed=1, initial_board=external_board)
        external_board.push_uci("g1f3")

        self.assertEqual(observation.history_uci, ("e2e4", "e7e5"))
        self.assertEqual(simulator.observation.history_uci, ("e2e4", "e7e5"))
        self.assertEqual(simulator.board.ply(), 2)

    def test_observation_and_move_identity_match_board_legal_moves(self) -> None:
        board = self.simulator.board
        self.assertEqual(self.initial_observation.legal_moves_uci, tuple(sorted(m.uci() for m in board.legal_moves)))
        self.assertEqual(
            {chess.Move.from_uci(uci) for uci in self.initial_observation.legal_moves_uci},
            set(board.legal_moves),
        )
        self.assertEqual(self.initial_observation.side_to_move, "white")
        self.assertEqual(self.initial_observation.agent_side, "white")

    def test_normal_transition_applies_one_agent_move_then_one_reply(self) -> None:
        result = self.simulator.step(chess.Move.from_uci("e2e4"))

        self.assertEqual(result.agent_move_uci, "e2e4")
        self.assertEqual(result.opponent_move_uci, "e7e5")
        self.assertEqual(result.history_uci, ("e2e4", "e7e5"))
        self.assertEqual(result.episode_decisions, 1)
        self.assertEqual(result.episode_plies, 2)
        self.assertFalse(result.terminated)
        self.assertFalse(result.truncated)
        self.assertEqual(result.reward, 0.0)
        self.assertEqual(result.metric_source, "chess_simulator")
        self.assertEqual(result.observation.turn, chess.WHITE)

    def test_black_agent_receives_opponent_white_opening_during_reset(self) -> None:
        simulator = ChessSimulator(ScriptedPolicy("e2e4"))
        observation = simulator.reset(seed=11, agent_color=chess.BLACK)

        self.assertEqual(observation.agent_color, chess.BLACK)
        self.assertEqual(observation.turn, chess.BLACK)
        self.assertEqual(observation.history_uci, ("e2e4",))
        self.assertEqual(simulator.episode_decisions, 0)
        self.assertEqual(simulator.episode_plies, 1)

    def test_opponent_failure_during_black_opening_leaves_no_partial_episode(self) -> None:
        simulator = ChessSimulator(RaisingPolicy())
        with self.assertRaises(OpponentPolicyError):
            simulator.reset(seed=14, agent_color=chess.BLACK)
        self.assertEqual(simulator.board.fen(), chess.Board().fen())
        self.assertEqual(simulator.episode_decisions, 0)
        with self.assertRaises(EpisodeStateError):
            _ = simulator.observation

    def test_illegal_uci_action_is_rejected_without_any_state_change(self) -> None:
        before = self.simulator.board
        observation_before = self.simulator.observation

        with self.assertRaises(InvalidActionError):
            self.simulator.step_uci("e2e5")

        self.assertEqual(self.simulator.board.fen(en_passant="fen"), before.fen(en_passant="fen"))
        self.assertEqual(tuple(self.simulator.board.move_stack), tuple(before.move_stack))
        self.assertEqual(self.simulator.episode_decisions, 0)
        self.assertEqual(self.simulator.observation, observation_before)

    def test_action_made_stale_by_previous_transition_is_rejected_atomically(self) -> None:
        stale = chess.Move.from_uci("e2e4")
        simulator = ChessSimulator(FirstLegalPolicy())
        simulator.reset(seed=1)
        simulator.step(chess.Move.from_uci("e2e4"))
        before = simulator.board
        count = simulator.episode_decisions

        with self.assertRaises(InvalidActionError):
            simulator.step(stale)

        self.assertEqual(simulator.board.fen(en_passant="fen"), before.fen(en_passant="fen"))
        self.assertEqual(tuple(simulator.board.move_stack), tuple(before.move_stack))
        self.assertEqual(simulator.episode_decisions, count)

    def test_only_move_objects_are_accepted_by_step(self) -> None:
        with self.assertRaises(InvalidActionError):
            self.simulator.step("e2e4")  # type: ignore[arg-type]
        self.assertEqual(self.simulator.episode_decisions, 0)
        self.assertEqual(self.simulator.step_uci("e2e4").agent_move_uci, "e2e4")

    def test_malformed_move_object_is_rejected_without_corrupting_state(self) -> None:
        before = self.simulator.board
        malformed = chess.Move(64, 0)
        with self.assertRaises(InvalidActionError):
            self.simulator.step(malformed)
        self.assertEqual(self.simulator.board.fen(), before.fen())
        self.assertEqual(self.simulator.episode_decisions, 0)

    def test_special_move_uci_identities_are_available_and_round_trip(self) -> None:
        positions = {
            "capture": chess.Board("7k/8/8/3p4/4P3/8/8/7K w - - 0 1"),
            "castling": chess.Board("r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1"),
            "en_passant": chess.Board("7k/8/8/3pP3/8/8/8/7K w - d6 0 1"),
            "promotion": chess.Board("7k/P7/8/8/8/8/8/7K w - - 0 1"),
        }
        expected = {
            "capture": "e4d5",
            "castling": "e1g1",
            "en_passant": "e5d6",
            "promotion": "a7a8q",
        }
        for name, board in positions.items():
            with self.subTest(position=name):
                simulator = ChessSimulator(FirstLegalPolicy())
                observation = simulator.reset(seed=19, initial_board=board)
                legal = set(observation.legal_moves_uci)
                self.assertEqual(legal, {move.uci() for move in board.legal_moves})
                self.assertIn(expected[name], legal)
                self.assertEqual(
                    {chess.Move.from_uci(uci).uci() for uci in observation.legal_moves_uci}, legal
                )
        promotion_legal = set(
            ChessSimulator(FirstLegalPolicy())
            .reset(seed=1, initial_board=positions["promotion"])
            .legal_moves_uci
        )
        self.assertTrue({"a7a8q", "a7a8r", "a7a8b", "a7a8n"}.issubset(promotion_legal))

    def test_castling_en_passant_and_each_promotion_update_the_board(self) -> None:
        cases = (
            ("castling", "r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1", "e1g1", chess.KING, chess.G1),
            ("en_passant", "7k/8/8/3pP3/8/8/8/7K w - d6 0 1", "e5d6", chess.PAWN, chess.D6),
        )
        for name, fen, uci, piece_type, square in cases:
            with self.subTest(move_type=name):
                simulator = ChessSimulator(FirstLegalPolicy())
                simulator.reset(seed=22, initial_board=chess.Board(fen))
                result = simulator.step_uci(uci)
                self.assertEqual(simulator.board.piece_type_at(square), piece_type)
                self.assertEqual(result.agent_move_uci, uci)
                if name == "en_passant":
                    self.assertIsNone(simulator.board.piece_at(chess.D5))
                else:
                    self.assertFalse(simulator.board.has_castling_rights(chess.WHITE))
                    self.assertEqual(simulator.board.piece_type_at(chess.F1), chess.ROOK)

        promotion_types = {"q": chess.QUEEN, "r": chess.ROOK, "b": chess.BISHOP, "n": chess.KNIGHT}
        for suffix, piece_type in promotion_types.items():
            with self.subTest(promotion=suffix):
                simulator = ChessSimulator(FirstLegalPolicy())
                simulator.reset(
                    seed=23,
                    initial_board=chess.Board("7k/P7/8/8/8/8/8/7K w - - 0 1"),
                )
                result = simulator.step_uci(f"a7a8{suffix}")
                self.assertEqual(simulator.board.piece_type_at(chess.A8), piece_type)
                self.assertEqual(result.agent_move_uci, f"a7a8{suffix}")
                self.assertEqual(result.history_uci[0], f"a7a8{suffix}")

    def test_agent_checkmate_ends_before_opponent_is_requested(self) -> None:
        opponent = FirstLegalPolicy()
        board = chess.Board("7k/8/5KQ1/8/8/8/8/8 w - - 0 1")
        simulator = ChessSimulator(opponent, max_decisions=1)
        simulator.reset(seed=1, initial_board=board)

        result = simulator.step_uci("g6g7")

        self.assertTrue(result.terminated)
        self.assertFalse(result.truncated)
        self.assertEqual(result.reward, 1.0)
        self.assertEqual(result.outcome_result, "1-0")
        self.assertEqual(result.outcome_reason, "checkmate")
        self.assertIsNone(result.opponent_move_uci)

    def test_opponent_checkmate_ends_transition_without_another_agent_action(self) -> None:
        board = board_after("f2f3", "e7e5")
        simulator = ChessSimulator(ScriptedPolicy("d8h4"))
        simulator.reset(seed=2, initial_board=board)

        result = simulator.step_uci("g2g4")

        self.assertTrue(result.terminated)
        self.assertFalse(result.truncated)
        self.assertEqual(result.agent_move_uci, "g2g4")
        self.assertEqual(result.opponent_move_uci, "d8h4")
        self.assertEqual(result.outcome_reason, "checkmate")
        self.assertEqual(result.reward, -1.0)
        self.assertEqual(result.observation.legal_moves_uci, ())
        with self.assertRaises(EpisodeStateError):
            simulator.step(chess.Move.from_uci("a2a3"))

    def test_agent_reward_is_from_black_perspective_for_black_win_and_loss(self) -> None:
        black_mates = board_after("f2f3", "e7e5", "g2g4")
        winning_simulator = ChessSimulator(FirstLegalPolicy())
        winning_simulator.reset(seed=24, agent_color=chess.BLACK, initial_board=black_mates)
        black_win = winning_simulator.step_uci("d8h4")
        self.assertTrue(black_win.terminated)
        self.assertEqual(black_win.outcome_result, "0-1")
        self.assertEqual(black_win.reward, 1.0)

        white_mates = board_after("e2e4", "f7f6", "d2d4")
        losing_simulator = ChessSimulator(ScriptedPolicy("d1h5"))
        losing_simulator.reset(seed=25, agent_color=chess.BLACK, initial_board=white_mates)
        black_loss = losing_simulator.step_uci("g7g5")
        self.assertTrue(black_loss.terminated)
        self.assertEqual(black_loss.outcome_result, "1-0")
        self.assertEqual(black_loss.outcome_reason, "checkmate")
        self.assertEqual(black_loss.reward, -1.0)

    def test_stalemate_created_by_agent_is_an_automatic_draw(self) -> None:
        board = chess.Board("7k/8/5K2/6Q1/8/8/8/8 w - - 0 1")
        simulator = ChessSimulator(FirstLegalPolicy())
        simulator.reset(seed=3, initial_board=board)

        result = simulator.step_uci("g5g6")

        self.assertTrue(result.terminated)
        self.assertEqual(result.reward, 0.0)
        self.assertEqual(result.outcome_result, "1/2-1/2")
        self.assertEqual(result.outcome_reason, "stalemate")
        self.assertIsNone(result.opponent_move_uci)

    def test_insufficient_material_after_capture_is_an_automatic_draw(self) -> None:
        board = chess.Board("7k/8/4n3/8/2B5/8/8/4K3 w - - 0 1")
        simulator = ChessSimulator(FirstLegalPolicy())
        simulator.reset(seed=5, initial_board=board)

        result = simulator.step_uci("c4e6")

        self.assertTrue(result.terminated)
        self.assertEqual(result.reward, 0.0)
        self.assertEqual(result.outcome_reason, "insufficient_material")
        self.assertIsNone(result.opponent_move_uci)

    def test_fivefold_repetition_uses_preserved_board_history(self) -> None:
        board = board_after(*(tuple(["g1f3", "g8f6", "f3g1", "f6g8"]) * 3))
        scripted = ScriptedPolicy("g8f6", "f6g8")
        simulator = ChessSimulator(scripted)
        observation = simulator.reset(seed=6, initial_board=board)
        self.assertEqual(len(observation.history_uci), 12)
        self.assertIsNone(simulator.board.outcome(claim_draw=False))

        simulator.step_uci("g1f3")
        result = simulator.step_uci("f3g1")

        self.assertTrue(result.terminated)
        self.assertEqual(result.outcome_reason, "fivefold_repetition")
        self.assertEqual(result.reward, 0.0)
        self.assertEqual(len(result.history_uci), 16)

    def test_threefold_claim_is_not_an_automatic_draw_action_or_termination(self) -> None:
        board = board_after(*(tuple(["g1f3", "g8f6", "f3g1", "f6g8"]) * 2))
        self.assertTrue(board.is_repetition(3))
        self.assertIsNone(board.outcome(claim_draw=False))
        simulator = ChessSimulator(ScriptedPolicy("g8f6"))
        simulator.reset(seed=26, initial_board=board)

        result = simulator.step_uci("g1f3")

        self.assertFalse(result.terminated)
        self.assertFalse(result.truncated)
        self.assertEqual(result.reward, 0.0)

    def test_seventyfive_move_rule_is_automatic_after_full_transition(self) -> None:
        board = chess.Board("7k/8/6K1/8/8/8/8/R7 w - - 148 75")
        simulator = ChessSimulator(ScriptedPolicy("h8g8"))
        simulator.reset(seed=8, initial_board=board)

        result = simulator.step_uci("a1a2")

        self.assertTrue(result.terminated)
        self.assertFalse(result.truncated)
        self.assertEqual(result.outcome_reason, "seventyfive_moves")
        self.assertEqual(result.reward, 0.0)
        self.assertEqual(result.observation.halfmove_clock, 150)

    def test_terminal_outcome_takes_precedence_over_decision_limit(self) -> None:
        board = chess.Board("7k/8/5KQ1/8/8/8/8/8 w - - 0 1")
        simulator = ChessSimulator(FirstLegalPolicy(), max_decisions=1)
        simulator.reset(seed=9, initial_board=board)

        result = simulator.step_uci("g6g7")

        self.assertTrue(result.terminated)
        self.assertFalse(result.truncated)
        self.assertIsNone(result.truncation_reason)

    def test_decision_limit_truncates_with_a_valid_next_agent_state(self) -> None:
        simulator = ChessSimulator(ScriptedPolicy("e7e5"), max_decisions=1)
        simulator.reset(seed=10)

        result = simulator.step_uci("e2e4")

        self.assertFalse(result.terminated)
        self.assertTrue(result.truncated)
        self.assertEqual(result.truncation_reason, "max_agent_decisions")
        self.assertEqual(result.reward, 0.0)
        self.assertEqual(result.observation.turn, chess.WHITE)
        self.assertGreater(len(result.observation.legal_moves_uci), 0)
        self.assertTrue(result.observation.legal_moves_uci)

    def test_opponent_exception_rolls_back_the_whole_attempted_transition(self) -> None:
        simulator = ChessSimulator(RaisingPolicy())
        simulator.reset(seed=12)
        before = simulator.board

        with self.assertRaises(OpponentPolicyError):
            simulator.step_uci("e2e4")

        self.assertEqual(simulator.board.fen(en_passant="fen"), before.fen(en_passant="fen"))
        self.assertEqual(tuple(simulator.board.move_stack), tuple(before.move_stack))
        self.assertEqual(simulator.episode_decisions, 0)
        self.assertEqual(simulator.observation.turn, chess.WHITE)
        with self.assertRaises(EpisodeStateError):
            simulator.step(chess.Move.from_uci("e2e4"))

    def test_illegal_opponent_move_rolls_back_the_whole_transition(self) -> None:
        simulator = ChessSimulator(InvalidPolicy())
        simulator.reset(seed=13)
        before = simulator.board

        with self.assertRaises(OpponentPolicyError):
            simulator.step_uci("e2e4")

        self.assertEqual(simulator.board.fen(en_passant="fen"), before.fen(en_passant="fen"))
        self.assertEqual(simulator.episode_decisions, 0)
        with self.assertRaises(EpisodeStateError):
            simulator.step(chess.Move.from_uci("e2e4"))

    def test_seeded_random_opponent_and_reset_reproduce_move_history(self) -> None:
        first = ChessSimulator(FirstLegalPolicy())
        second = ChessSimulator(FirstLegalPolicy())
        obs1 = first.reset(seed=17, agent_color=chess.BLACK)
        obs2 = second.reset(seed=17, agent_color=chess.BLACK)
        self.assertEqual(obs1.history_uci, obs2.history_uci)

        rng1, rng2 = random.Random(33), random.Random(33)
        for _ in range(4):
            m1 = rng1.choice(first.legal_moves)
            m2 = rng2.choice(second.legal_moves)
            self.assertEqual(m1.uci(), m2.uci())
            r1, r2 = first.step(m1), second.step(m2)
            self.assertEqual(r1.history_uci, r2.history_uci)
            if r1.terminated or r1.truncated:
                break

    def test_stateful_opponent_reset_reproduces_reused_and_fresh_simulators(self) -> None:
        policy = ResettablePolicy("e7e5", "b8c6")
        reused = ChessSimulator(policy)

        def episode(simulator: ChessSimulator) -> tuple[tuple[str, ...], ...]:
            histories = [simulator.reset(seed=190, agent_color=chess.WHITE).history_uci]
            histories.append(simulator.step_uci("e2e4").history_uci)
            histories.append(simulator.step_uci("g1f3").history_uci)
            return tuple(histories)

        first = episode(reused)
        repeated = episode(reused)
        fresh = episode(ChessSimulator(ResettablePolicy("e7e5", "b8c6")))

        self.assertEqual(first, repeated)
        self.assertEqual(first, fresh)
        self.assertEqual(policy.reset_seeds, [190, 190])

    def test_reset_after_opponent_failure_resets_policy_local_state(self) -> None:
        policy = ResettablePolicy("e7e5", "b8c6", fail_at=2)
        simulator = ChessSimulator(policy)
        first = simulator.reset(seed=191)
        result = simulator.step_uci("e2e4")
        self.assertEqual(result.history_uci, ("e2e4", "e7e5"))
        with self.assertRaises(OpponentPolicyError):
            simulator.step_uci("g1f3")

        reset_observation = simulator.reset(seed=191)
        replayed = simulator.step_uci("e2e4")

        self.assertEqual(reset_observation.history_uci, first.history_uci)
        self.assertEqual(replayed.history_uci, result.history_uci)
        self.assertEqual(policy.reset_seeds, [191, 191])

    def test_mutated_policy_configuration_is_rejected_before_reset(self) -> None:
        policy = MutableConfigPolicy()
        simulator = ChessSimulator(policy)
        initial = simulator.reset(seed=192)
        policy.version = 2

        with self.assertRaisesRegex(OpponentPolicyError, "configuration changed"):
            simulator.reset(seed=193)

        with self.assertRaises(EpisodeStateError):
            _ = simulator.observation
        self.assertEqual(simulator.board.fen(en_passant="fen"), initial.fen)
        self.assertEqual(simulator.episode_decisions, 0)

    def test_mutated_policy_configuration_is_rejected_before_transition(self) -> None:
        policy = MutableConfigPolicy()
        simulator = ChessSimulator(policy)
        initial = simulator.reset(seed=199)
        policy.version = 2

        with self.assertRaisesRegex(OpponentPolicyError, "configuration changed"):
            simulator.step_uci("e2e4")

        self.assertEqual(simulator.observation, initial)
        self.assertEqual(simulator.episode_decisions, 0)
        self.assertEqual(simulator.board.fen(en_passant="fen"), initial.fen)

    def test_reset_starts_new_episode_and_clears_prior_termination(self) -> None:
        board = chess.Board("7k/8/5KQ1/8/8/8/8/8 w - - 0 1")
        simulator = ChessSimulator(FirstLegalPolicy())
        simulator.reset(seed=1, initial_board=board)
        terminal = simulator.step_uci("g6g7")
        self.assertTrue(terminal.terminated)
        with self.assertRaises(EpisodeStateError):
            simulator.step(chess.Move.null())

        observation = simulator.reset(seed=2)

        self.assertEqual(observation.history_uci, ())
        self.assertEqual(simulator.episode_decisions, 0)
        self.assertEqual(simulator.episode_plies, 0)
        self.assertEqual(simulator.board.fen(), chess.Board().fen())

    def test_custom_initial_board_requires_live_agent_turn(self) -> None:
        with self.assertRaises(ValueError):
            self.simulator.reset(seed=20, agent_color=chess.BLACK, initial_board=chess.Board())
        terminal = chess.Board("7k/8/5KQ1/8/8/8/8/8 b - - 0 1")
        with self.assertRaises(ValueError):
            self.simulator.reset(seed=21, agent_color=chess.BLACK, initial_board=terminal)
        with self.assertRaises(ValueError):
            self.simulator.reset(seed=22, initial_board=chess.Board.from_chess960_pos(0))

    def test_invalid_custom_positions_are_rejected_without_changing_live_episode(self) -> None:
        invalid_fens = {
            "missing king": "8/8/8/8/8/8/8/4K3 w - - 0 1",
            "multiple kings": "4k3/8/8/8/8/8/4K3/4K3 w - - 0 1",
            "pawn on back rank": "P3k3/8/8/8/8/8/8/4K3 w - - 0 1",
            "invalid castling rights": "4k3/8/8/8/8/8/8/4K3 w K - 0 1",
            "opposite king in check": "4k3/8/8/8/8/8/8/K3R3 w - - 0 1",
        }
        before = self.simulator.observation
        before_board = self.simulator.board

        for label, fen in invalid_fens.items():
            with self.subTest(position=label):
                invalid = chess.Board(fen)
                self.assertFalse(invalid.is_valid())
                with self.assertRaisesRegex(ValueError, "not a valid standard chess position"):
                    self.simulator.reset(seed=194, initial_board=invalid)
                self.assertEqual(self.simulator.observation, before)
                self.assertEqual(self.simulator.board.fen(en_passant="fen"), before_board.fen(en_passant="fen"))
                self.assertEqual(tuple(self.simulator.board.move_stack), tuple(before_board.move_stack))

    def test_fen_round_trip_preserves_position_fields_and_legal_uci_moves(self) -> None:
        board = chess.Board("r3k2r/8/8/3pP3/8/8/8/R3K2R w KQkq d6 0 22")
        self.assertTrue(board.is_valid())
        simulator = ChessSimulator(FirstLegalPolicy())
        observation = simulator.reset(seed=195, initial_board=board)
        restored = chess.Board(observation.fen)

        self.assertEqual(restored.board_fen(), board.board_fen())
        self.assertEqual(restored.turn, board.turn)
        self.assertEqual(restored.castling_xfen(), board.castling_xfen())
        self.assertEqual(restored.ep_square, board.ep_square)
        self.assertEqual(restored.halfmove_clock, board.halfmove_clock)
        self.assertEqual(restored.fullmove_number, board.fullmove_number)
        self.assertEqual(
            {move.uci() for move in restored.legal_moves},
            set(observation.legal_moves_uci),
        )
        self.assertEqual(restored.fen(en_passant="fen"), observation.fen)

    def test_fen_serialization_preserves_en_passant_target_by_fen_convention(self) -> None:
        board = board_after("e2e4")
        simulator = ChessSimulator(FirstLegalPolicy())
        observation = simulator.reset(seed=196, agent_color=chess.BLACK, initial_board=board)
        restored = chess.Board(observation.fen)

        self.assertEqual(observation.ep_square, "e3")
        self.assertEqual(restored.ep_square, chess.E3)
        self.assertEqual(restored.fen(en_passant="fen"), observation.fen)

    def test_uci_history_replay_preserves_standard_and_custom_initial_games(self) -> None:
        standard = board_after("e2e4", "e7e5", "g1f3", "b8c6")
        simulator = ChessSimulator(FirstLegalPolicy())
        standard_observation = simulator.reset(seed=197, initial_board=standard)
        replayed_standard = chess.Board()
        for uci in standard_observation.history_uci:
            replayed_standard.push_uci(uci)
        self.assertEqual(replayed_standard.fen(en_passant="fen"), standard_observation.fen)
        self.assertEqual(
            tuple(move.uci() for move in replayed_standard.move_stack),
            standard_observation.history_uci,
        )

        custom_start = chess.Board("r3k2r/pp3ppp/8/8/8/8/PP3PPP/R3K2R w KQkq - 0 1")
        custom = custom_start.copy()
        custom.push_uci("a2a3")
        custom.push_uci("a7a6")
        custom_observation = simulator.reset(seed=198, initial_board=custom)
        replayed_custom = custom_start.copy()
        for uci in custom_observation.history_uci:
            replayed_custom.push_uci(uci)
        self.assertEqual(replayed_custom.fen(en_passant="fen"), custom_observation.fen)
        self.assertEqual(replayed_custom.castling_xfen(), custom_observation.castling_rights)

    def test_fen_alone_does_not_restore_repetition_history(self) -> None:
        cycle = ("g1f3", "g8f6", "f3g1", "f6g8")
        historical = board_after(*(cycle * 3))
        self.assertTrue(historical.is_repetition(4))
        self.assertIsNone(historical.outcome(claim_draw=False))
        restored_from_fen = chess.Board(historical.fen(en_passant="fen"))
        self.assertFalse(restored_from_fen.is_repetition(4))

        replayed = chess.Board()
        for move in historical.move_stack:
            replayed.push(move)
        self.assertTrue(replayed.is_repetition(4))
        for uci in cycle:
            historical.push_uci(uci)
            replayed.push_uci(uci)
            restored_from_fen.push_uci(uci)

        self.assertEqual(historical.outcome(claim_draw=False).termination, chess.Termination.FIVEFOLD_REPETITION)
        self.assertEqual(replayed.outcome(claim_draw=False), historical.outcome(claim_draw=False))
        self.assertIsNone(restored_from_fen.outcome(claim_draw=False))

    def test_simulator_requires_a_positive_integer_decision_limit(self) -> None:
        for invalid in (0, -1, True, 1.5):
            with self.subTest(max_decisions=invalid):
                with self.assertRaises(ValueError):
                    ChessSimulator(FirstLegalPolicy(), max_decisions=invalid)  # type: ignore[arg-type]


if __name__ == "__main__":
    unittest.main()
