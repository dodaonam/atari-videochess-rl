"""Small RGB parser for the observed ALE VideoChess screen layout."""

from __future__ import annotations

from dataclasses import dataclass

import chess
import numpy as np


SCREEN_SHAPE = (210, 160, 3)
BOARD_LEFT = 44
BOARD_TOP = 36
SQUARE_WIDTH = 8
SQUARE_HEIGHT = 17
GOLD_RGB = (180, 122, 48)
BLUE_RGB = (132, 144, 252)
CURSOR_GOLD_PIXELS = 19
START_MAJOR_SPRITE_COUNTS = (26, 25, 20, 28, 26, 20, 25, 26)


def _square_indices(square: str) -> tuple[int, int]:
    if len(square) != 2 or square[0] not in "abcdefgh" or square[1] not in "12345678":
        raise ValueError(f"Invalid chess square: {square!r}")
    return 8 - int(square[1]), ord(square[0]) - ord("a")


@dataclass(frozen=True)
class CellPixels:
    gold: int
    blue: int


@dataclass(frozen=True)
class WindowCell:
    gold_piece_seen: bool
    blue_piece_seen: bool
    cursor_seen: bool

    @property
    def side(self) -> str:
        if self.cursor_seen:
            return "cursor"
        if self.gold_piece_seen and not self.blue_piece_seen:
            return "black"
        if self.blue_piece_seen and not self.gold_piece_seen:
            return "white"
        if not self.gold_piece_seen and not self.blue_piece_seen:
            return "empty"
        return "unknown"


@dataclass(frozen=True)
class BoardObservation:
    cells: tuple[tuple[CellPixels, ...], ...]

    def cell(self, square: str) -> CellPixels:
        row, col = _square_indices(square)
        return self.cells[row][col]

    @property
    def cursor_squares(self) -> frozenset[str]:
        return frozenset(
            chess.square_name(chess.square(col, 7 - row))
            for row, line in enumerate(self.cells)
            for col, pixels in enumerate(line)
            if pixels.gold == CURSOR_GOLD_PIXELS
        )

    def side(self, square: str) -> str:
        pixels = self.cell(square)
        if pixels.gold == CURSOR_GOLD_PIXELS:
            return "cursor"
        if pixels.gold and pixels.blue:
            return "unknown"
        if pixels.gold:
            return "black"
        if pixels.blue:
            return "white"
        return "empty"

    def piece_kind(self, square: str) -> str | None:
        """Classify visible sprite counts; ambiguous major sprites stay explicit."""
        side = self.side(square)
        if side not in ("white", "black"):
            return None
        pixels = self.cell(square)
        count = pixels.blue if side == "white" else pixels.gold
        return {
            8: "pawn",
            20: "bishop",
            25: "knight",
            26: "rook_or_king",
            28: "queen",
        }.get(count, "unknown")

    def matches_board(self, board: chess.Board) -> bool:
        cursor_squares = self.cursor_squares
        for square in chess.SQUARES:
            name = chess.square_name(square)
            if name in cursor_squares:
                continue
            piece = board.piece_at(square)
            expected = "empty" if piece is None else ("white" if piece.color else "black")
            if self.side(name) != expected:
                return False
        return True

    def matches_start_position(self) -> bool:
        if not self.matches_board(chess.Board()):
            return False
        for col, file_name in enumerate("abcdefgh"):
            if self.cell(f"{file_name}8").gold != START_MAJOR_SPRITE_COUNTS[col]:
                return False
            if self.cell(f"{file_name}1").blue != START_MAJOR_SPRITE_COUNTS[col]:
                return False
            if self.cell(f"{file_name}7").gold != 8 or self.cell(f"{file_name}2").blue != 8:
                return False
        return True


@dataclass(frozen=True)
class BoardWindow:
    observations: tuple[BoardObservation, ...]

    def cell(self, square: str) -> WindowCell:
        pixels = [observation.cell(square) for observation in self.observations]
        return WindowCell(
            gold_piece_seen=any(p.gold > 0 and p.gold != CURSOR_GOLD_PIXELS for p in pixels),
            blue_piece_seen=any(p.blue > 0 for p in pixels),
            cursor_seen=any(p.gold == CURSOR_GOLD_PIXELS for p in pixels),
        )

    @property
    def cursor_squares(self) -> frozenset[str]:
        return frozenset().union(*(observation.cursor_squares for observation in self.observations))

    def matches_board(self, board: chess.Board) -> bool:
        if len(self.cursor_squares) > 1:
            return False
        for square in chess.SQUARES:
            name = chess.square_name(square)
            cell = self.cell(name)
            if cell.side == "cursor":
                continue
            piece = board.piece_at(square)
            expected = "empty" if piece is None else ("white" if piece.color else "black")
            if cell.side != expected:
                return False
        return True


class VideoChessVision:
    """Extract per-square color evidence from genuine RGB observations."""

    def observe(self, rgb: np.ndarray) -> BoardObservation:
        if not isinstance(rgb, np.ndarray) or rgb.shape != SCREEN_SHAPE or rgb.dtype != np.uint8:
            raise ValueError(f"Expected a uint8 RGB observation with shape {SCREEN_SHAPE}")
        cells: list[tuple[CellPixels, ...]] = []
        for row in range(8):
            line: list[CellPixels] = []
            y0 = BOARD_TOP + row * SQUARE_HEIGHT
            for col in range(8):
                x0 = BOARD_LEFT + col * SQUARE_WIDTH
                square = rgb[y0 : y0 + SQUARE_HEIGHT, x0 : x0 + SQUARE_WIDTH]
                line.append(
                    CellPixels(
                        gold=int(np.all(square == GOLD_RGB, axis=2).sum()),
                        blue=int(np.all(square == BLUE_RGB, axis=2).sum()),
                    )
                )
            cells.append(tuple(line))
        return BoardObservation(tuple(cells))

    def window(self, rgb_frames: list[np.ndarray] | tuple[np.ndarray, ...]) -> BoardWindow:
        if not rgb_frames:
            raise ValueError("At least one RGB frame is required")
        return BoardWindow(tuple(self.observe(frame) for frame in rgb_frames))
