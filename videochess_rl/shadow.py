"""Legal-move shadow state that only advances on matching RGB evidence."""

from __future__ import annotations

from dataclasses import dataclass, field

import chess

from .vision import BoardObservation, BoardWindow


class DesynchronizationError(RuntimeError):
    """The observed board does not support the expected chess state."""


class AmbiguousObservedMoveError(DesynchronizationError):
    """More than one legal move matches the RGB occupancy evidence."""


BoardEvidence = BoardObservation | BoardWindow


@dataclass
class ShadowBoard:
    """A python-chess board used only to validate observed Atari transitions."""

    board: chess.Board = field(default_factory=chess.Board)

    def apply_observed_move(self, uci: str, evidence: BoardEvidence) -> None:
        try:
            move = chess.Move.from_uci(uci)
        except ValueError as exc:
            raise ValueError(f"Invalid UCI move: {uci!r}") from exc
        if move not in self.board.legal_moves:
            raise ValueError(f"Move is not legal in the current shadow position: {uci}")

        candidate = self.board.copy()
        candidate.push(move)
        if not evidence.matches_board(candidate):
            raise DesynchronizationError(
                f"RGB evidence does not show the requested move {uci}; shadow state was not advanced"
            )
        self.board = candidate

    def apply_observed_reply(self, evidence: BoardEvidence) -> str | None:
        """Infer one legal opponent move from RGB, or return None while it is thinking."""
        uci = self.infer_observed_reply(evidence)
        if uci is not None:
            move = chess.Move.from_uci(uci)
            self.board.push(move)
        return uci

    def infer_observed_reply(self, evidence: BoardEvidence) -> str | None:
        """Return the unique visible legal reply without changing shadow state."""
        if evidence.matches_board(self.board):
            return None

        matches: list[tuple[chess.Move, chess.Board]] = []
        for move in self.board.legal_moves:
            candidate = self.board.copy()
            candidate.push(move)
            if evidence.matches_board(candidate):
                matches.append((move, candidate))

        if not matches:
            raise DesynchronizationError("RGB board matches no legal shadow-board transition")
        if len(matches) != 1:
            moves = ", ".join(move.uci() for move, _ in matches)
            raise AmbiguousObservedMoveError(f"RGB board matches multiple legal moves: {moves}")

        move, _ = matches[0]
        return move.uci()
