"""Small, deterministic state/action boundary helpers for future chess models.

These helpers do not implement a neural model or alter simulator/data
contracts. They provide a shared FEN and legal-candidate identity contract.
"""

from __future__ import annotations

from dataclasses import dataclass

import chess


@dataclass(frozen=True, slots=True)
class ActionCandidate:
    """One legal semantic move and its side-to-move-oriented features.

    ``uci`` remains the action identity used to apply a move to the original
    Board. Square indexes use python-chess's 0..63 encoding; for Black to move,
    the rank is flipped so the mover's home rank is always at the bottom.
    """

    uci: str
    from_square: int
    to_square: int
    promotion: chess.PieceType | None
    is_capture: bool
    is_castling: bool
    is_en_passant: bool
    gives_check: bool


def canonical_model_fen(board: chess.Board) -> str:
    """Serialize a standard-chess model position with only legal EP targets.

    M2 observations intentionally preserve the raw FEN en-passant target;
    M3 data identities include it only when an en-passant capture is legal.
    This model boundary uses the latter rule without changing either source
    contract. The full move history remains separate from this FEN.
    """
    if not isinstance(board, chess.Board):
        raise TypeError("board must be a python-chess Board")
    if board.chess960:
        raise ValueError("model contract supports standard chess, not Chess960")
    return board.fen(en_passant="legal")


def legal_action_candidates(board: chess.Board) -> tuple[ActionCandidate, ...]:
    """Return all and only legal moves in stable UCI order.

    The ordered list is a per-position batch layout, never a persistent action
    ID. Callers must retain each candidate's UCI key when selecting a move.
    A terminal Board returns an empty tuple.
    """
    if not isinstance(board, chess.Board):
        raise TypeError("board must be a python-chess Board")
    if board.chess960:
        raise ValueError("model contract supports standard chess, not Chess960")

    rank_flip = 56 if board.turn == chess.BLACK else 0
    candidates = []
    for move in sorted(board.legal_moves, key=lambda item: item.uci()):
        candidates.append(ActionCandidate(
            uci=move.uci(),
            from_square=move.from_square ^ rank_flip,
            to_square=move.to_square ^ rank_flip,
            promotion=move.promotion,
            is_capture=board.is_capture(move),
            is_castling=board.is_castling(move),
            is_en_passant=board.is_en_passant(move),
            gives_check=board.gives_check(move),
        ))
    return tuple(candidates)
