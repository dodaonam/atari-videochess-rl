"""Validated RAM fields exposed by the bundled Atari VideoChess ROM.

The operational decoder is enabled only for the ROM with the pinned SHA-256.
It verifies the exact board layout and Atari interaction state, including
source/target selection and target-FIRE acknowledgement. Normal shadow-board
advancement still requires the RGB board contract. A genuine ALE terminal
event may resolve the final player/reply pair from the exact RAM board only
when it uniquely matches legal chess transitions, checkmate, and ALE reward.
"""

from __future__ import annotations

from dataclasses import dataclass

import chess
import numpy as np


VIDEO_CHESS_ROM_SHA256 = "d44f2a115393b0a6cbcd5398d62369e652f3670a9ee585883d183e740edad0f7"
VIDEO_CHESS_RAM_BYTES = 128

# Atari RAM $80-$BF stores ranks 8 to 1, files a to h. The lower nibble
# contains a piece code; bit 3 marks White, and bits 2-0 identify the kind.
_PIECE_TYPES = {
    1: chess.KING,
    2: chess.QUEEN,
    3: chess.BISHOP,
    4: chess.KNIGHT,
    5: chess.ROOK,
    6: chess.PAWN,
}
_ROM_PIECE_CODES = {
    chess.KING: 1,
    chess.QUEEN: 2,
    chess.BISHOP: 3,
    chess.KNIGHT: 4,
    chess.ROOK: 5,
    chess.PAWN: 6,
}


def _piece_code(piece: chess.Piece) -> int:
    return _ROM_PIECE_CODES[piece.piece_type] | (0x08 if piece.color else 0)


def ram_square_index(square: str | chess.Square) -> int:
    """Return VideoChess' $80-$BF board-array index for a chess square."""
    if isinstance(square, str):
        try:
            square = chess.parse_square(square)
        except ValueError as exc:
            raise ValueError(f"Invalid chess square: {square!r}") from exc
    if not 0 <= square < 64:
        raise ValueError(f"Invalid chess square index: {square!r}")
    return (7 - chess.square_rank(square)) * 8 + chess.square_file(square)


def ram_index_square(index: int) -> str:
    """Return the chess square represented by an index in $80-$BF."""
    if not 0 <= index < 64:
        raise ValueError(f"Invalid VideoChess board index: {index!r}")
    return chess.square_name(chess.square(index % 8, 7 - index // 8))


@dataclass(frozen=True)
class VideoChessRAMState:
    """A read-only interpretation of the validated VideoChess RAM fields."""

    piece_codes: tuple[int, ...]
    source_index: int
    target_index: int
    interaction_state: int
    move_valid_flag: int
    half_move_count: int

    @classmethod
    def from_ram(cls, ram: np.ndarray | bytes | bytearray) -> "VideoChessRAMState":
        values = np.asarray(ram, dtype=np.uint8)
        if values.shape != (VIDEO_CHESS_RAM_BYTES,):
            raise ValueError(
                f"Expected {VIDEO_CHESS_RAM_BYTES} ALE RAM bytes, got {values.shape}"
            )
        # The upper nibble carries flags that vary during rendering/search.
        # The low nibble is the ROM's piece identity and color encoding.
        return cls(
            piece_codes=tuple(int(value) & 0x0F for value in values[:64]),
            source_index=int(values[0x59]),  # $D9: current/previous source square
            target_index=int(values[0x5A]),  # $DA: current/previous target square
            interaction_state=int(values[0x73]),  # $F3: cursor/selection/search state
            move_valid_flag=int(values[0x75]),  # $F5: invalid movement is $FF
            half_move_count=int(values[0x64]),  # $E4: completed half-move counter
        )

    @property
    def source_square(self) -> str | None:
        return ram_index_square(self.source_index) if self.source_index < 64 else None

    @property
    def target_square(self) -> str | None:
        return ram_index_square(self.target_index) if self.target_index < 64 else None

    @property
    def piece_selected(self) -> bool:
        return self.interaction_state == 0x01

    @property
    def target_accepted(self) -> bool:
        # A valid human move enters the ROM's computer-search state.
        return self.interaction_state == 0xC0

    @property
    def move_is_valid(self) -> bool:
        return self.move_valid_flag == 0

    def board_matches(self, board: chess.Board) -> bool:
        """Compare all 64 RAM piece identities with a chess board."""
        for square in chess.SQUARES:
            code = self.piece_codes[ram_square_index(square)]
            actual = None
            if code:
                piece_type = _PIECE_TYPES.get(code & 0x07)
                if piece_type is None:
                    return False
                actual = chess.Piece(piece_type, bool(code & 0x08))
            if actual != board.piece_at(square):
                return False
        return True

    def board_matches_selected_preview(
        self,
        board: chess.Board,
        source: str | chess.Square,
        target: str | chess.Square,
    ) -> bool:
        """Match all unrelated squares during VideoChess' selected-move preview.

        The ROM temporarily draws the selected piece on the target square while
        leaving it on its source square. That duplicate is a UI preview, not a
        committed move. Only those two squares are allowed to differ from the
        verified board, and the source identity must remain present.
        """
        source_square = chess.parse_square(source) if isinstance(source, str) else source
        target_square = chess.parse_square(target) if isinstance(target, str) else target
        if source_square == target_square:
            return False
        source_piece = board.piece_at(source_square)
        if source_piece is None:
            return False
        source_code = _piece_code(source_piece)
        if self.piece_codes[ram_square_index(source_square)] != source_code:
            return False
        target_piece = board.piece_at(target_square)
        target_code = (
            0
            if target_piece is None
            else _piece_code(target_piece)
        )
        actual_target_code = self.piece_codes[ram_square_index(target_square)]
        if actual_target_code not in (target_code, source_code):
            return False
        for square in chess.SQUARES:
            if square in (source_square, target_square):
                continue
            code = self.piece_codes[ram_square_index(square)]
            piece = None
            if code:
                piece_type = _PIECE_TYPES.get(code & 0x07)
                if piece_type is None:
                    return False
                piece = chess.Piece(piece_type, bool(code & 0x08))
            if piece != board.piece_at(square):
                return False
        return True


def acknowledges_target_fire(
    state: VideoChessRAMState,
    source: str | chess.Square,
    target: str | chess.Square,
) -> bool:
    """Require Atari's search-state acknowledgement for the selected move.

    A changed state byte alone is insufficient: source and target registers
    must still identify the input that was just issued, and the ROM must mark
    that destination legal. This function deliberately does not claim that
    the chess board was committed or authorize shadow advancement.
    """
    source_index = ram_square_index(source)
    target_index = ram_square_index(target)
    return (
        state.target_accepted
        and state.source_index == source_index
        and state.target_index == target_index
        and state.move_is_valid
    )
