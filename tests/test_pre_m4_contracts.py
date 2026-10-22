"""Synthetic M2/M3/model-boundary contracts for the pending M4 design."""

from __future__ import annotations

import unittest

import chess

from videochess_rl.action_contract import canonical_model_fen, legal_action_candidates
from videochess_rl.baselines import RandomLegalAgent
from videochess_rl.data.contracts import (
    GAME_SCHEMA,
    board_position_signature,
    canonical_fen,
    candidate_identity,
    digest,
    normalized_game_identity,
    reconstruct_position,
    replay_history_identity,
    sample_identity,
    validate_position_record,
)
from videochess_rl.simulator import ChessSimulator


class ScriptedReplies:
    policy_id = "pre_m4_scripted_replies"

    def __init__(self, *moves: str) -> None:
        self.moves = tuple(moves)
        self.observations = []
        self.index = 0

    @property
    def config(self) -> dict[str, object]:
        return {"moves": list(self.moves)}

    def reset_episode(self, *, seed: int) -> None:
        del seed
        self.index = 0
        self.observations.clear()

    def choose_move(self, observation, legal_moves, rng):
        del rng
        self.observations.append(observation)
        uci = self.moves[self.index]
        self.index += 1
        move = chess.Move.from_uci(uci)
        if move not in legal_moves:
            raise AssertionError(f"scripted reply is illegal in {observation.fen}: {uci}")
        return move


def synthetic_m3_game(moves: list[str]) -> dict[str, object]:
    source_id = "a" * 64
    game_id = "b" * 64
    normalized_id = normalized_game_identity(chess.STARTING_FEN, moves)
    return {
        "schema": GAME_SCHEMA,
        "schema_version": GAME_SCHEMA,
        "game_id": game_id,
        "record_id": game_id,
        "normalized_game_sha256": normalized_id,
        "variant": "standard",
        "source_id": source_id,
        "source_archive_sha256": "c" * 64,
        "source_member_name": "synthetic.pgn",
        "source_member": "synthetic.pgn",
        "source_ordinal": 1,
        "source_game_id": None,
        "source_game_ref_sha256": None,
        "pgn_result": "1/2-1/2",
        "result": "1/2-1/2",
        "white_result": "draw",
        "initial_fen": chess.STARTING_FEN,
        "moves_uci": moves,
        "board_termination": None,
        "ply_count": len(moves),
        "validation_status": "accepted",
        "diagnostics": [],
    }


def synthetic_m3_position(game: dict[str, object], ply_index: int) -> dict[str, object]:
    board = reconstruct_position(game, ply_index)
    legal = sorted(move.uci() for move in board.legal_moves)
    game_id = str(game["game_id"])
    source_id = str(game["source_id"])
    normalized_id = str(game["normalized_game_sha256"])
    played = str(game["moves_uci"][ply_index])
    sample_id = sample_identity(source_id, game_id, normalized_id, ply_index)
    return {
        "schema": "videochess-position/1.0",
        "schema_version": "videochess-position/1.0",
        "record_id": sample_id,
        "sample_id": sample_id,
        "game_id": game_id,
        "source_id": source_id,
        "normalized_game_sha256": normalized_id,
        "ply_index": ply_index,
        "reconstruction_path": {"game_id": game_id, "ply_index": ply_index},
        "fen": canonical_fen(board),
        "side_to_move": "white" if board.turn == chess.WHITE else "black",
        "legal_moves_uci": legal,
        "played_move_uci": played,
        "board_position_signature": board_position_signature(board),
        "history_state_id": replay_history_identity(
            str(game["initial_fen"]), list(game["moves_uci"][:ply_index]),
        ),
        "candidate_count": len(legal),
        "candidate_set_sha256": digest({
            "domain": "videochess-candidate-set/v1",
            "sample_id": sample_id,
            "legal_moves_uci": legal,
        }),
        "played_candidate_id": candidate_identity(sample_id, played),
        "pgn_result": "1/2-1/2",
        "white_result": "draw",
        "side_to_move_result": "draw",
        "result_white": "1/2-1/2",
        "result_to_move": 0,
        "sampling_config_sha256": "d" * 64,
        "sampling_id": "e" * 64,
        "split": "train",
        "split_id": "train",
    }


class PreM4ChessContractTests(unittest.TestCase):
    def assert_m2_observation_matches_m3_position(
        self, observation, game: dict[str, object], ply_index: int,
    ) -> None:
        position = synthetic_m3_position(game, ply_index)
        m3_board = validate_position_record(position, game)
        m2_replay = chess.Board()
        for uci in observation.history_uci:
            m2_replay.push_uci(uci)

        self.assertEqual(len(observation.history_uci), ply_index)
        self.assertEqual(observation.fen, m2_replay.fen(en_passant="fen"))
        self.assertEqual(canonical_model_fen(m2_replay), position["fen"])
        self.assertEqual(canonical_model_fen(m3_board), position["fen"])
        self.assertEqual(observation.turn, m3_board.turn)
        self.assertEqual(
            observation.legal_moves_uci,
            tuple(position["legal_moves_uci"]),
        )
        candidates = legal_action_candidates(m2_replay)
        self.assertEqual(
            tuple(candidate.uci for candidate in candidates),
            tuple(position["legal_moves_uci"]),
        )
        target = str(position["played_move_uci"])
        candidate = next(item for item in candidates if item.uci == target)
        self.assertEqual(
            position["played_candidate_id"],
            candidate_identity(str(position["sample_id"]), candidate.uci),
        )

    def test_m2_observation_history_matches_m3_positions_for_white_and_black(self) -> None:
        moves = ["e2e4", "e7e5", "g1f3"]
        game = synthetic_m3_game(moves)
        opponent = ScriptedReplies("e7e5")
        simulator = ChessSimulator(opponent)

        first = simulator.reset(seed=101, agent_color=chess.WHITE)
        self.assert_m2_observation_matches_m3_position(first, game, 0)
        step = simulator.step_uci("e2e4")

        black_observation = opponent.observations[0]
        self.assertEqual(black_observation.turn, chess.BLACK)
        self.assertEqual(black_observation.agent_color, chess.WHITE)
        self.assert_m2_observation_matches_m3_position(black_observation, game, 1)
        self.assert_m2_observation_matches_m3_position(step.observation, game, 2)

    def test_m2_and_m3_history_reconstruction_preserves_en_passant_target(self) -> None:
        moves = ["e2e4", "a7a6", "e4e5", "d7d5", "e5d6"]
        game = synthetic_m3_game(moves)
        opponent = ScriptedReplies("a7a6", "d7d5")
        simulator = ChessSimulator(opponent)

        simulator.reset(seed=202, agent_color=chess.WHITE)
        simulator.step_uci("e2e4")
        final_step = simulator.step_uci("e4e5")
        observation = final_step.observation
        self.assert_m2_observation_matches_m3_position(observation, game, 4)

        ep = next(candidate for candidate in legal_action_candidates(simulator.board) if candidate.uci == "e5d6")
        self.assertTrue(ep.is_en_passant)
        self.assertIn("e5d6", observation.legal_moves_uci)

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
