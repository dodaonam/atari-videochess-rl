"""Small transparent legal-move policies for M2 simulator checks."""

from __future__ import annotations

import random
from typing import Sequence

import chess

from .simulator import Observation


class RandomLegalAgent:
    """Uniformly sample legal UCI-sorted moves using a caller-owned RNG."""

    policy_id = "random_legal"

    @property
    def config(self) -> dict[str, object]:
        return {"selection": "uniform over legal moves sorted by UCI"}

    def choose_move(
        self,
        observation: Observation,
        legal_moves: Sequence[chess.Move],
        rng: random.Random,
    ) -> chess.Move:
        del observation
        if not legal_moves:
            raise ValueError("no legal move is available")
        ordered = sorted(legal_moves, key=lambda move: move.uci())
        return chess.Move.from_uci(rng.choice(ordered).uci())


class SimpleHeuristicAgent:
    """Prefer mate, material gain, promotions, captures, then checks.

    This is a one-ply evaluation, not an engine or search policy. It rebuilds
    only the current position from the immutable observation FEN; the
    simulator itself retains the authoritative history for rules outcomes.
    """

    policy_id = "simple_material_heuristic"
    _MATERIAL = {
        chess.PAWN: 100,
        chess.KNIGHT: 320,
        chess.BISHOP: 330,
        chess.ROOK: 500,
        chess.QUEEN: 900,
        chess.KING: 0,
    }
    _MATE_SCORE = 1_000_000
    _CHECK_BONUS = 20

    @property
    def config(self) -> dict[str, object]:
        return {
            "evaluation": "immediate mate, material, promotion, capture, check",
            "material_values_cp": {chess.piece_name(piece): value for piece, value in self._MATERIAL.items()},
            "check_bonus_cp": self._CHECK_BONUS,
            "search_plies": 1,
        }

    def choose_move(
        self,
        observation: Observation,
        legal_moves: Sequence[chess.Move],
        rng: random.Random,
    ) -> chess.Move:
        if not legal_moves:
            raise ValueError("no legal move is available")
        board = chess.Board(observation.fen)
        if board.turn != observation.turn:
            raise ValueError("observation FEN and turn disagree")

        scored: list[tuple[int, str]] = []
        for offered_move in legal_moves:
            uci = offered_move.uci()
            move = chess.Move.from_uci(uci)
            if move not in board.legal_moves:
                raise ValueError("supplied move is not legal for the observation")
            before_material = self._material_balance(board, observation.turn)
            is_capture = board.is_capture(move)
            captured_piece = board.piece_at(move.to_square)
            if board.is_en_passant(move):
                captured_piece = chess.Piece(chess.PAWN, not board.turn)
            promotion_bonus = (
                self._MATERIAL[move.promotion] - self._MATERIAL[chess.PAWN]
                if move.promotion is not None
                else 0
            )

            successor = board.copy(stack=False)
            successor.push(move)
            outcome = successor.outcome(claim_draw=False)
            if outcome is not None and outcome.winner == observation.turn:
                score = self._MATE_SCORE
            elif outcome is not None and outcome.winner == (not observation.turn):
                score = -self._MATE_SCORE
            else:
                score = self._material_balance(successor, observation.turn) - before_material
                score += promotion_bonus
                if is_capture and captured_piece is not None:
                    score += self._MATERIAL[captured_piece.piece_type] // 20
                if successor.is_check():
                    score += self._CHECK_BONUS
            scored.append((score, uci))

        best_score = max(score for score, _ in scored)
        best_moves = sorted(uci for score, uci in scored if score == best_score)
        return chess.Move.from_uci(rng.choice(best_moves))

    @classmethod
    def _material_balance(cls, board: chess.Board, perspective: chess.Color) -> int:
        total = 0
        for piece_type, value in cls._MATERIAL.items():
            total += value * len(board.pieces(piece_type, perspective))
            total -= value * len(board.pieces(piece_type, not perspective))
        return total
