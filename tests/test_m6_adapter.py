"""Focused contracts for the RGB-verified M6 policy boundary."""

from __future__ import annotations

from dataclasses import replace
import hashlib
import json
import random
import tempfile
import unittest
from pathlib import Path

import chess
import numpy as np
import torch
from torch import nn

from tests.test_m1_vision import BACKGROUND, BLUE, GOLD, start_frame
from videochess_rl.episode import AtariDecisionContext, DecisionResult
from videochess_rl.m6.adapter import (
    M6PolicyAdapter,
    PolicyIdentity,
    PolicyInputError,
    validate_decision_context,
)
from videochess_rl.rl.checkpoint import SNAPSHOT_SCHEMA, load_evaluation_snapshot
from videochess_rl.vision import BoardEvidenceSet, BoardWindow, VideoChessVision


class FixedPolicy:
    def __init__(self, action: str = "e2e4", model: nn.Module | None = None) -> None:
        self.action = action
        self.model = model
        if self.model is not None:
            self.model.eval()
        self.calls = 0

    def choose_move(self, observation, legal_moves, rng: random.Random):
        self.calls += 1
        return self.action


def _paint_square(frame: np.ndarray, square: chess.Square, color: tuple[int, int, int]) -> None:
    row = 7 - chess.square_rank(square)
    col = chess.square_file(square)
    y0 = 36 + row * 17
    x0 = 44 + col * 8
    for index in range(8):
        frame[y0 + index // 8, x0 + index % 8] = color


def _frame_for_board(board: chess.Board) -> np.ndarray:
    frame = np.empty((210, 160, 3), dtype=np.uint8)
    frame[:] = BACKGROUND
    for square, piece in board.piece_map().items():
        _paint_square(frame, square, BLUE if piece.color else GOLD)
    return frame


def _context(board: chess.Board | None = None, *, frame_number: int = 10) -> AtariDecisionContext:
    board = board or chess.Board()
    initial = not board.move_stack
    frame = start_frame(cursor=None) if initial else _frame_for_board(board)
    vision = VideoChessVision()
    observation = vision.observe(frame)
    window = vision.window((frame, frame, frame))
    evidence = window if initial else BoardEvidenceSet((window,))
    frame.setflags(write=False)
    return AtariDecisionContext(
        board=board.copy(stack=True),
        fen=board.fen(en_passant="fen"),
        side_to_move=board.turn,
        history_uci=tuple(move.uci() for move in board.move_stack),
        legal_moves_uci=tuple(sorted(move.uci() for move in board.legal_moves)),
        frame_number=frame_number,
        rgb_sha256=hashlib.sha256(frame.tobytes()).hexdigest(),
        rgb_frame=frame,
        rgb_observation=observation,
        rgb_evidence=evidence,
        standard_reset_verified=initial and observation.matches_start_position(),
    )


def _adapter(policy: FixedPolicy | None = None, *, action: str = "e2e4", seed: int = 1) -> M6PolicyAdapter:
    policy = policy or FixedPolicy(action)
    identity = PolicyIdentity("test-policy", "test-frozen-policy", checkpoint_sha256="a" * 64)
    return M6PolicyAdapter(policy, identity, rng_seed=seed)


class M6PolicyAdapterTests(unittest.TestCase):
    def test_valid_rgb_confirmed_standard_reset_is_a_policy_input(self) -> None:
        context = _context()
        board, observation = validate_decision_context(context)
        self.assertEqual(board.fen(en_passant="fen"), chess.Board().fen(en_passant="fen"))
        self.assertEqual(observation.history_uci, ())
        self.assertEqual(observation.agent_color, chess.WHITE)
        self.assertTrue(context.rgb_observation.matches_start_position())

    def test_complete_legal_history_preserves_castling_en_passant_promotion_and_repetition(self) -> None:
        histories = (
            ("e2e4", "e7e5", "g1f3", "b8c6", "f1e2", "g8f6", "e1g1", "f8e7"),
            ("e2e4", "a7a6", "e4e5", "d7d5", "e5d6", "c7d6"),
            ("a2a4", "b7b5", "a4b5", "c7c6", "b5b6", "c6c5", "b6b7", "d7d6", "b7a8n", "g8f6"),
            ("g1f3", "g8f6", "f3g1", "f6g8", "g1f3", "g8f6", "f3g1", "f6g8"),
        )
        for history in histories:
            with self.subTest(history=history):
                board = chess.Board()
                for uci in history:
                    move = chess.Move.from_uci(uci)
                    self.assertIn(move, board.legal_moves)
                    board.push(move)
                if board.turn != chess.WHITE:
                    self.fail("fixture history must end on White's M6 decision turn")
                context = _context(board)
                rebuilt, observation = validate_decision_context(context)
                self.assertEqual(tuple(move.uci() for move in rebuilt.move_stack), history)
                self.assertEqual(observation.history_uci, history)
                self.assertEqual(observation.fen, board.fen(en_passant="fen"))
                self.assertEqual(observation.legal_moves_uci, tuple(sorted(move.uci() for move in board.legal_moves)))
                if "e1g1" in history:
                    self.assertFalse(rebuilt.has_kingside_castling_rights(chess.WHITE))
                if "e5d6" in history:
                    self.assertEqual(rebuilt.peek().uci(), "g8f6" if history[-1] == "g8f6" else "c7d6")
                if "b7a8n" in history:
                    self.assertIn("b7a8n", observation.history_uci)
                    self.assertEqual(rebuilt.piece_at(chess.A8), chess.Piece(chess.KNIGHT, chess.WHITE))
                if rebuilt.is_repetition(3):
                    self.assertTrue(rebuilt.can_claim_threefold_repetition())

    def test_missing_history_is_rejected_for_noninitial_rgb(self) -> None:
        board = chess.Board()
        board.push_uci("e2e3")
        context = _context(board)
        with self.assertRaisesRegex(PolicyInputError, "history"):
            validate_decision_context(replace(context, history_uci=()))

    def test_empty_history_is_rejected_without_standard_reset_confirmation(self) -> None:
        context = _context()
        with self.assertRaisesRegex(PolicyInputError, "empty history"):
            validate_decision_context(replace(context, standard_reset_verified=False))

    def test_malformed_or_illegal_history_is_rejected(self) -> None:
        context = _context()
        with self.assertRaisesRegex(PolicyInputError, "malformed or illegal"):
            validate_decision_context(replace(context, history_uci=("not-a-move",)))

    def test_fen_history_mismatch_is_rejected(self) -> None:
        board = chess.Board()
        board.push_uci("e2e3")
        with self.assertRaisesRegex(PolicyInputError, "FEN/history/shadow mismatch"):
            validate_decision_context(replace(_context(board), fen=chess.STARTING_FEN))

    def test_side_to_move_mismatch_is_rejected(self) -> None:
        with self.assertRaisesRegex(PolicyInputError, "side-to-move mismatch"):
            validate_decision_context(replace(_context(), side_to_move=chess.BLACK))

    def test_missing_mismatched_duplicate_and_malformed_candidates_fail_closed(self) -> None:
        context = _context()
        cases = (
            (),
            ("e2e4",),
            tuple(sorted((*context.legal_moves_uci, context.legal_moves_uci[0]))),
            tuple(sorted((*context.legal_moves_uci[:-1], "bad"))),
        )
        for candidates in cases:
            with self.subTest(candidates=candidates[:2]):
                with self.assertRaises(PolicyInputError):
                    validate_decision_context(replace(context, legal_moves_uci=candidates))

    def test_shadow_board_stack_must_match_observed_history(self) -> None:
        context = _context()
        desynced = chess.Board()
        desynced.push_uci("e2e3")
        with self.assertRaises(PolicyInputError):
            validate_decision_context(replace(context, board=desynced))

    def test_rgb_hash_frame_identity_and_stale_observation_are_checked(self) -> None:
        context = _context(frame_number=10)
        with self.assertRaisesRegex(PolicyInputError, "frame hash"):
            validate_decision_context(replace(context, rgb_sha256="0" * 64))
        policy = FixedPolicy("e2e4")
        adapter = _adapter(policy)
        self.assertEqual(adapter(context).uci, "e2e4")
        with self.assertRaisesRegex(PolicyInputError, "stale"):
            adapter(replace(context, frame_number=9))
        with self.assertRaisesRegex(PolicyInputError, "same ALE frame"):
            altered = start_frame(cursor=None)
            altered[0, 0] = (25, 26, 167)
            altered.setflags(write=False)
            observation = VideoChessVision().observe(altered)
            window = VideoChessVision().window((altered, altered, altered))
            repeated_frame = replace(context, rgb_frame=altered, rgb_sha256=hashlib.sha256(altered.tobytes()).hexdigest(),
                                     rgb_observation=observation, rgb_evidence=window)
            adapter(repeated_frame)

    def test_ambiguous_rgb_evidence_is_rejected(self) -> None:
        context = _context()
        moved = chess.Board()
        moved.push_uci("e2e3")
        bad_window = VideoChessVision().window((start_frame(cursor=None), _frame_for_board(moved), start_frame(cursor=None)))
        with self.assertRaises(PolicyInputError):
            validate_decision_context(replace(context, rgb_evidence=bad_window))

    def test_illegal_or_malformed_policy_outputs_are_rejected(self) -> None:
        with self.assertRaisesRegex(PolicyInputError, "illegal or outside"):
            _adapter(action="e2e5")(_context())
        with self.assertRaisesRegex(PolicyInputError, "malformed UCI"):
            _adapter(action="bad")(_context())

    def test_policy_decision_is_bound_to_policy_and_rgb_identity(self) -> None:
        result = _adapter(action="e2e4")(_context())
        self.assertIsInstance(result, DecisionResult)
        self.assertEqual(result.metadata["policy_id"], "test-policy")
        self.assertEqual(result.metadata["selected_uci"], "e2e4")
        self.assertEqual(result.metadata["rgb_sha256"], _context().rgb_sha256)
        self.assertFalse(result.metadata["training"])
        self.assertFalse(result.metadata["optimizer"])
        self.assertFalse(result.metadata["replay_insertion"])
        self.assertFalse(result.metadata["stockfish"])

    def test_model_weights_and_gradients_remain_frozen(self) -> None:
        model = nn.Linear(4, 3).eval()
        before = {name: value.detach().clone() for name, value in model.state_dict().items()}
        policy = FixedPolicy("e2e4", model=model)
        result = _adapter(policy)(_context())
        self.assertEqual(result.uci, "e2e4")
        self.assertFalse(model.training)
        self.assertTrue(all(parameter.grad is None for parameter in model.parameters()))
        self.assertTrue(all(torch.equal(model.state_dict()[key], value) for key, value in before.items()))


class M6CheckpointValidationTests(unittest.TestCase):
    def test_missing_or_corrupt_private_checkpoint_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            missing = Path(directory) / "missing.pt"
            with self.assertRaisesRegex(ValueError, "missing/unsafe"):
                load_evaluation_snapshot(missing)
            corrupt = Path(directory) / "corrupt.pt"
            corrupt.write_bytes(b"not-a-torch-checkpoint")
            corrupt.with_suffix(".pt.manifest.json").write_text(json.dumps({
                "schema": SNAPSHOT_SCHEMA,
                "file": corrupt.name,
                "sha256": "0" * 64,
                "size_bytes": corrupt.stat().st_size,
                "resumable": False,
            }), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "invalid non-resumable"):
                load_evaluation_snapshot(corrupt)

    def test_incompatible_evaluation_snapshot_schema_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            checkpoint = Path(directory) / "wrong-schema.pt"
            torch.save({"schema": "videochess-ddqn-checkpoint/2.0", "resumable": True}, checkpoint)
            import hashlib
            digest = hashlib.sha256(checkpoint.read_bytes()).hexdigest()
            checkpoint.with_suffix(".pt.manifest.json").write_text(json.dumps({
                "schema": SNAPSHOT_SCHEMA,
                "file": checkpoint.name,
                "sha256": digest,
                "size_bytes": checkpoint.stat().st_size,
                "resumable": False,
            }), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "schema/role mismatch"):
                load_evaluation_snapshot(checkpoint)


if __name__ == "__main__":
    unittest.main()
