"""Synthetic M2/M3/model-boundary contracts for the pending M4 design."""

from __future__ import annotations

import unittest

import chess

from videochess_rl.action_contract import canonical_model_fen, legal_action_candidates
from videochess_rl.baselines import RandomLegalAgent
from videochess_rl.data.contracts import canonical_fen, candidate_identity
from videochess_rl.simulator import ChessSimulator


class PreM4ChessContractTests(unittest.TestCase):
    def test_model_fen_normalizes_unavailable_en_passant_target(self) -> None:
        raw_ep = chess.Board("4k3/8/8/8/4P3/8/8/4K3 b - e3 0 1")
        no_ep = chess.Board("4k3/8/8/8/4P3/8/8/4K3 b - - 0 1")
        observation = ChessSimulator(RandomLegalAgent()).reset(
            seed=11, agent_color=chess.BLACK, initial_board=raw_ep,
        )

        self.assertEqual(observation.fen, raw_ep.fen(en_passant="fen"))
        self.assertEqual(raw_ep.fen(en_passant="fen").split()[3], "e3")
        self.assertEqual(raw_ep.fen(en_passant="legal").split()[3], "-")
        self.assertNotEqual(raw_ep.fen(en_passant="fen"), no_ep.fen(en_passant="fen"))
        self.assertEqual(canonical_model_fen(raw_ep), canonical_model_fen(no_ep))
        self.assertEqual(canonical_model_fen(raw_ep), canonical_fen(raw_ep))

    def test_pinned_en_passant_is_not_encoded_as_a_legal_capture(self) -> None:
        pinned = chess.Board("k3r3/8/8/3pP3/8/8/8/4K3 w - d6 0 1")
        self.assertNotIn(chess.Move.from_uci("e5d6"), pinned.legal_moves)
        self.assertEqual(pinned.fen(en_passant="fen").split()[3], "d6")
        self.assertEqual(canonical_model_fen(pinned).split()[3], "-")

    def test_legal_en_passant_survives_normalization_and_has_stable_identity(self) -> None:
        board = chess.Board("4k3/8/8/3pP3/8/8/8/4K3 w - d6 0 1")
        candidates = legal_action_candidates(board)
        ep = next(item for item in candidates if item.uci == "e5d6")

        self.assertEqual(canonical_model_fen(board).split()[3], "d6")
        self.assertTrue(ep.is_capture)
        self.assertTrue(ep.is_en_passant)
        self.assertIsNone(ep.promotion)
        self.assertEqual(ep.uci, chess.Move.from_uci(ep.uci).uci())

    def test_candidate_order_and_identity_match_m2_and_m3_contracts(self) -> None:
        board = chess.Board()
        simulator = ChessSimulator(RandomLegalAgent())
        observation = simulator.reset(seed=31, initial_board=board)
        candidates = legal_action_candidates(simulator.board)
        candidate_ucis = tuple(candidate.uci for candidate in candidates)

        self.assertEqual(candidate_ucis, tuple(sorted(candidate_ucis)))
        self.assertEqual(candidate_ucis, observation.legal_moves_uci)
        self.assertEqual(canonical_model_fen(simulator.board), canonical_fen(simulator.board))
        target_uci = "e2e4"
        target = next(candidate for candidate in candidates if candidate.uci == target_uci)
        self.assertIn(target_uci, candidate_ucis)
        self.assertEqual(
            candidate_identity("a" * 64, target_uci),
            candidate_identity("a" * 64, target.uci),
        )
        self.assertNotEqual(candidate_identity("a" * 64, target_uci), candidate_identity("a" * 64, "e2e5"))
        self.assertNotIn("e2e5", candidate_ucis)

    def test_black_to_move_uses_mover_oriented_square_features(self) -> None:
        board = chess.Board()
        board.push_uci("e2e4")
        candidates = legal_action_candidates(board)
        move = next(candidate for candidate in candidates if candidate.uci == "e7e5")

        self.assertEqual(move.from_square, chess.E2)
        self.assertEqual(move.to_square, chess.E4)
        self.assertEqual(move.uci, "e7e5")

    def test_all_promotion_pieces_are_distinct_legal_candidates(self) -> None:
        board = chess.Board("4k3/P7/8/8/8/8/8/4K3 w - - 0 1")
        candidates = {item.uci: item for item in legal_action_candidates(board)}
        expected = {"a7a8b", "a7a8n", "a7a8q", "a7a8r"}

        self.assertTrue(expected.issubset(candidates))
        self.assertEqual({candidates[uci].promotion for uci in expected}, {
            chess.BISHOP, chess.KNIGHT, chess.QUEEN, chess.ROOK,
        })

    def test_castling_captures_and_check_flags_come_from_the_authoritative_board(self) -> None:
        castle_board = chess.Board("r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1")
        castle_candidates = {item.uci: item for item in legal_action_candidates(castle_board)}
        self.assertTrue(castle_candidates["e1c1"].is_castling)
        self.assertTrue(castle_candidates["e1g1"].is_castling)

        capture_board = chess.Board("4k3/8/8/3p4/4P3/8/8/4K3 w - - 0 1")
        capture = next(item for item in legal_action_candidates(capture_board) if item.uci == "e4d5")
        self.assertTrue(capture.is_capture)

        check_board = chess.Board("4k3/8/8/8/8/8/8/K3R3 w - - 0 1")
        check = next(item for item in legal_action_candidates(check_board) if item.uci == "e1e7")
        self.assertTrue(check.gives_check)

    def test_terminal_mate_and_stalemate_have_empty_candidate_sets(self) -> None:
        mate = chess.Board("7k/6Q1/6K1/8/8/8/8/8 b - - 0 1")
        stale = chess.Board("7k/5K2/6Q1/8/8/8/8/8 b - - 0 1")

        self.assertTrue(mate.is_checkmate())
        self.assertEqual(legal_action_candidates(mate), ())
        self.assertTrue(stale.is_stalemate())
        self.assertFalse(stale.is_check())
        self.assertEqual(legal_action_candidates(stale), ())

    def test_automatic_repetition_and_seventy_five_move_terminals_have_no_candidates(self) -> None:
        fivefold = chess.Board()
        cycle = ("g1f3", "g8f6", "f3g1", "f6g8")
        for _ in range(4):
            for uci in cycle:
                fivefold.push_uci(uci)
        self.assertTrue(fivefold.is_fivefold_repetition())
        self.assertTrue(any(fivefold.legal_moves))
        self.assertEqual(legal_action_candidates(fivefold), ())

        seventy_five = chess.Board("4k3/8/8/8/8/8/4R3/4K3 w - - 150 76")
        self.assertTrue(seventy_five.is_seventyfive_moves())
        self.assertTrue(any(seventy_five.legal_moves))
        self.assertEqual(legal_action_candidates(seventy_five), ())

    def test_fen_does_not_replace_history_for_repetition_sensitive_state(self) -> None:
        with_history = chess.Board()
        cycle = ("g1f3", "g8f6", "f3g1", "f6g8")
        for _ in range(3):
            for uci in cycle:
                with_history.push_uci(uci)
        fen_only = chess.Board(with_history.fen())

        self.assertEqual(canonical_model_fen(with_history), canonical_model_fen(fen_only))
        self.assertTrue(with_history.can_claim_threefold_repetition())
        self.assertFalse(fen_only.can_claim_threefold_repetition())
        self.assertEqual(tuple(move.uci() for move in with_history.move_stack), cycle * 3)


if __name__ == "__main__":
    unittest.main()
