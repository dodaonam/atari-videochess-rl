"""Legal-move shadow state that only advances on matching RGB evidence."""

from __future__ import annotations

from dataclasses import dataclass, field

import chess

from .atari_ram import VideoChessRAMState
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
        self.apply_observed_sequence((uci,), evidence)

    def apply_observed_sequence(
        self,
        ucis: tuple[str, ...],
        evidence: BoardEvidence,
    ) -> tuple[str, ...]:
        """Advance atomically only when RGB confirms the sequence's final board."""
        if not ucis:
            raise ValueError("At least one observed move is required")
        candidate = self.board.copy()
        parsed: list[str] = []
        for uci in ucis:
            try:
                move = chess.Move.from_uci(uci)
            except ValueError as exc:
                raise ValueError(f"Invalid UCI move: {uci!r}") from exc
            if move not in candidate.legal_moves:
                raise ValueError(f"Move is not legal in the current shadow position: {uci}")
            candidate.push(move)
            parsed.append(uci)

        if not evidence.matches_board(candidate):
            moves = ", ".join(parsed)
            raise DesynchronizationError(
                f"RGB evidence does not show the requested move sequence {moves}; shadow state was not advanced"
            )
        self.board = candidate
        return tuple(parsed)

    def apply_terminal_ram_verified_sequence(
        self,
        ucis: tuple[str, ...],
        ram_state: VideoChessRAMState,
        *,
        ale_terminated: bool,
        ale_reward: float,
    ) -> tuple[str, ...]:
        """Advance at a terminal only when exact ROM RAM proves a legal mate.

        This path is reserved for the final transition when ALE terminates
        during the Atari reply and no full RGB board frame exists. It requires
        a legal sequence from the current shadow, exact full-board ROM RAM
        agreement, checkmate in the resulting position, and a matching ALE
        reward. It never treats policy intent or a preview as a move.
        """
        if not ale_terminated:
            raise DesynchronizationError("Terminal RAM verification requires ALE terminated=True")
        if not ucis:
            raise ValueError("At least one move is required for terminal RAM verification")
        candidate = self.board.copy()
        parsed: list[str] = []
        for uci in ucis:
            try:
                move = chess.Move.from_uci(uci)
            except ValueError as exc:
                raise ValueError(f"Invalid UCI move: {uci!r}") from exc
            if move not in candidate.legal_moves:
                raise ValueError(f"Move is not legal in the current shadow position: {uci}")
            candidate.push(move)
            parsed.append(uci)
        if not candidate.is_checkmate():
            raise DesynchronizationError("ALE terminal RAM sequence did not produce checkmate")
        expected_reward = -1.0 if candidate.turn == chess.WHITE else 1.0
        if float(ale_reward) != expected_reward:
            raise DesynchronizationError("ALE terminal reward disagreed with the terminal checkmate winner")
        if not ram_state.board_matches(candidate):
            raise DesynchronizationError("ALE terminal RAM board did not match the legal terminal sequence")
        self.board = candidate
        return tuple(parsed)

    def apply_observed_reply(self, evidence: BoardEvidence) -> str | None:
        """Infer one legal opponent move from RGB, or return None while it is thinking."""
        uci = self.infer_observed_reply(evidence)
        if uci is not None:
            move = chess.Move.from_uci(uci)
            self.board.push(move)
        return uci

    def infer_observed_reply(
        self,
        evidence: BoardEvidence,
        *,
        allow_cursor_masked_square: bool = False,
    ) -> str | None:
        """Return a candidate reply without changing shadow state.

        Cursor-masked inference is only a staging check; callers must later
        confirm the complete board with strict RGB evidence before advancing.
        """
        def matches_evidence(board: chess.Board) -> bool:
            if allow_cursor_masked_square and isinstance(evidence, BoardWindow):
                return evidence.matches_board_except_cursor(board)
            return evidence.matches_board(board)

        if matches_evidence(self.board):
            return None

        candidate_matches: list[tuple[chess.Move, chess.Board]] = []
        for move in self.board.legal_moves:
            candidate = self.board.copy()
            candidate.push(move)
            if matches_evidence(candidate):
                candidate_matches.append((move, candidate))

        if not candidate_matches:
            raise DesynchronizationError("RGB board matches no legal shadow-board transition")
        if len(candidate_matches) != 1:
            moves = ", ".join(move.uci() for move, _ in candidate_matches)
            raise AmbiguousObservedMoveError(f"RGB board matches multiple legal moves: {moves}")

        move, _ = candidate_matches[0]
        return move.uci()
