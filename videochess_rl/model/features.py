"""Versioned board, history, and legal-candidate features for M4/M5."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import chess
import numpy as np

from videochess_rl.action_contract import canonical_model_fen, legal_action_candidates

INPUT_SCHEMA = "videochess-model-input/1.0"
PROMOTION_TO_ID = {
    None: 0,
    chess.KNIGHT: 1,
    chess.BISHOP: 2,
    chess.ROOK: 3,
    chess.QUEEN: 4,
}
ID_TO_PROMOTION = {value: key for key, value in PROMOTION_TO_ID.items()}


@dataclass(frozen=True, slots=True)
class PositionFeatures:
    """One position's compact CPU representation; UCI remains the action ID."""

    sample_id: str
    split: str
    board_planes: np.ndarray
    state_scalars: np.ndarray
    history_moves: np.ndarray
    candidate_squares: np.ndarray
    candidate_promotion: np.ndarray
    candidate_flags: np.ndarray
    candidate_uci: tuple[str, ...]
    target_index: int | None
    target_uci: str | None
    ply_index: int | None = None

    @property
    def candidate_count(self) -> int:
        return len(self.candidate_uci)

    @property
    def history_length(self) -> int:
        return int(self.history_moves.shape[0])


def _move_token(move: chess.Move, mover: chess.Color) -> tuple[int, int, int, int]:
    try:
        promotion = PROMOTION_TO_ID[move.promotion]
    except KeyError as exc:
        raise ValueError(f"unsupported promotion piece in history: {move.promotion}") from exc
    return (move.from_square, move.to_square, promotion, int(mover))


def _board_planes(board: chess.Board) -> np.ndarray:
    planes = np.zeros((13, 8, 8), dtype=np.uint8)
    for square, piece in board.piece_map().items():
        row = chess.square_rank(square)
        if board.turn == chess.BLACK:
            row = 7 - row
        channel = piece.piece_type - 1
        if piece.color != board.turn:
            channel += 6
        planes[channel, row, chess.square_file(square)] = 1
    if board.ep_square is not None and board.has_legal_en_passant():
        row = chess.square_rank(board.ep_square)
        if board.turn == chess.BLACK:
            row = 7 - row
        planes[12, row, chess.square_file(board.ep_square)] = 1
    return planes


def encode_board(
    board: chess.Board,
    *,
    sample_id: str = "",
    split: str = "inference",
    target_uci: str | None = None,
    ply_index: int | None = None,
) -> PositionFeatures:
    """Encode an authoritative Board and its complete move stack.

    Version 1 requires a standard-start root. The caller must reconstruct the
    Board from observed/released move history; FEN is never treated as the full
    rules state.
    """
    if not isinstance(board, chess.Board):
        raise TypeError("board must be a python-chess Board")
    if board.chess960 or not board.is_valid():
        raise ValueError("model input v1 supports only valid standard chess")
    if canonical_model_fen(board.root()) != chess.STARTING_FEN:
        raise ValueError("model input v1 rejects nonstandard initial positions")

    scalars = np.asarray(
        [
            float(board.turn == chess.WHITE),
            float(board.has_kingside_castling_rights(board.turn)),
            float(board.has_queenside_castling_rights(board.turn)),
            float(board.has_kingside_castling_rights(not board.turn)),
            float(board.has_queenside_castling_rights(not board.turn)),
            min(board.halfmove_clock, 150) / 150.0,
        ],
        dtype=np.float32,
    )

    history: list[tuple[int, int, int, int]] = []
    mover = chess.WHITE
    for move in board.move_stack:
        history.append(_move_token(move, mover))
        mover = not mover
    history_array = np.asarray(history, dtype=np.uint8).reshape((-1, 4))

    candidates = legal_action_candidates(board)
    candidate_squares = np.asarray(
        [(item.from_square, item.to_square) for item in candidates], dtype=np.uint8
    ).reshape((-1, 2))
    candidate_promotion = np.asarray(
        [PROMOTION_TO_ID[item.promotion] for item in candidates], dtype=np.uint8
    )
    candidate_flags = np.asarray(
        [
            (item.is_capture, item.is_castling, item.is_en_passant, item.gives_check)
            for item in candidates
        ],
        dtype=np.uint8,
    ).reshape((-1, 4))
    candidate_uci = tuple(item.uci for item in candidates)

    target_index: int | None = None
    if target_uci is not None:
        if not isinstance(target_uci, str):
            raise TypeError("target_uci must be a string")
        matches = [index for index, uci in enumerate(candidate_uci) if uci == target_uci]
        if len(matches) != 1:
            raise ValueError("played_move_uci must occur exactly once in legal candidates")
        target_index = matches[0]

    return PositionFeatures(
        sample_id=sample_id,
        split=split,
        board_planes=_board_planes(board),
        state_scalars=scalars,
        history_moves=history_array,
        candidate_squares=candidate_squares,
        candidate_promotion=candidate_promotion,
        candidate_flags=candidate_flags,
        candidate_uci=candidate_uci,
        target_index=target_index,
        target_uci=target_uci,
        ply_index=ply_index,
    )


def replay_observation_history(history_uci: Sequence[str]) -> chess.Board:
    """Reconstruct an M2 standard-start observation from complete UCI history."""
    if isinstance(history_uci, (str, bytes)):
        raise TypeError("history_uci must be a sequence of UCI strings")
    board = chess.Board()
    for index, uci in enumerate(history_uci):
        if not isinstance(uci, str):
            raise ValueError(f"history move {index} is not a UCI string")
        try:
            move = chess.Move.from_uci(uci)
        except ValueError as exc:
            raise ValueError(f"history move {index} is malformed") from exc
        if move not in board.legal_moves or board.outcome(claim_draw=False) is not None:
            raise ValueError(f"history move {index} is illegal or follows a terminal state")
        board.push(move)
    return board
