"""RGB parsing and board agreement tests for the observed VideoChess layout."""

from __future__ import annotations

import unittest

import chess
import numpy as np

from videochess_rl.vision import BoardEvidenceSet, BoardObservation, BoardWindow, VideoChessVision


BACKGROUND = (24, 26, 167)
GOLD = (180, 122, 48)
BLUE = (132, 144, 252)


def paint(rgb: np.ndarray, square: str, color: tuple[int, int, int], pixels: int) -> None:
    col = ord(square[0]) - ord("a")
    row = 8 - int(square[1])
    x0 = 44 + col * 8
    y0 = 36 + row * 17
    for index in range(pixels):
        rgb[y0 + index // 8, x0 + index % 8] = color


def start_frame(cursor: str | None = "d4") -> np.ndarray:
    rgb = np.empty((210, 160, 3), dtype=np.uint8)
    rgb[:] = BACKGROUND
    major_counts = (26, 25, 20, 28, 26, 20, 25, 26)
    for col, file_name in enumerate("abcdefgh"):
        paint(rgb, f"{file_name}8", GOLD, major_counts[col])
        paint(rgb, f"{file_name}1", BLUE, major_counts[col])
    for file_name in "abcdefgh":
        paint(rgb, f"{file_name}7", GOLD, 8)
        paint(rgb, f"{file_name}2", BLUE, 8)
    if cursor:
        paint(rgb, cursor, GOLD, 19)
    return rgb


def after_e2e3(cursor: str | None = "e2") -> np.ndarray:
    rgb = start_frame(cursor=None)
    rgb[36 + 6 * 17 : 36 + 7 * 17, 44 + 4 * 8 : 44 + 5 * 8] = BACKGROUND
    paint(rgb, "e3", BLUE, 8)
    if cursor:
        paint(rgb, cursor, GOLD, 19)
    return rgb


def after_c7c5(cursor: str | None = "c7") -> np.ndarray:
    rgb = after_e2e3(cursor=None)
    rgb[36 + 1 * 17 : 36 + 2 * 17, 44 + 2 * 8 : 44 + 3 * 8] = BACKGROUND
    paint(rgb, "c5", GOLD, 8)
    if cursor:
        paint(rgb, cursor, GOLD, 19)
    return rgb


class VideoChessVisionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.vision = VideoChessVision()

    def test_reads_pixel_counts_at_algebraic_squares(self) -> None:
        observation = self.vision.observe(start_frame())

        self.assertEqual(observation.cell("e2").blue, 8)
        self.assertEqual(observation.cell("c7").gold, 8)
        self.assertEqual(observation.cell("d4").gold, 19)
        self.assertEqual(observation.cursor_squares, frozenset({"d4"}))

    def test_rejects_non_rgb_observation_shapes(self) -> None:
        with self.assertRaises(ValueError):
            self.vision.observe(np.zeros((128,), dtype=np.uint8))

    def test_initial_rgb_layout_matches_standard_chess_start(self) -> None:
        observation = self.vision.observe(start_frame())

        self.assertTrue(observation.matches_start_position())

    def test_start_layout_rejects_wrong_major_sprite_placement(self) -> None:
        rgb = start_frame()
        rgb[36 + 7 * 17 : 36 + 8 * 17, 44 : 44 + 8] = BACKGROUND
        paint(rgb, "a1", BLUE, 20)

        self.assertFalse(self.vision.observe(rgb).matches_start_position())

    def test_observed_sprite_counts_identify_pawns_and_major_candidates(self) -> None:
        observation = self.vision.observe(start_frame())

        self.assertEqual(observation.piece_kind("e2"), "pawn")
        self.assertEqual(observation.piece_kind("c8"), "bishop")
        self.assertEqual(observation.piece_kind("b8"), "knight")
        self.assertEqual(observation.piece_kind("d8"), "queen")
        self.assertEqual(observation.piece_kind("a8"), "rook_or_king")

    def test_cursor_overlay_does_not_hide_an_observed_player_move(self) -> None:
        board = chess.Board()
        board.push_uci("e2e3")
        observation = self.vision.observe(after_e2e3())

        self.assertTrue(observation.matches_board(board))

    def test_window_recovers_blinking_player_move_and_opponent_reply(self) -> None:
        board = chess.Board()
        board.push_uci("e2e3")
        board.push_uci("c7c5")
        window = self.vision.window(
            [
                after_c7c5(cursor="c7"),
                after_c7c5(cursor=None),
                after_c7c5(cursor=None),
            ]
        )

        self.assertTrue(window.matches_board(board))
        self.assertEqual(window.cell("c5").side, "black")
        self.assertIn("c7", window.cursor_squares)

    def test_rgb_mismatch_is_not_repaired_to_match_shadow_board(self) -> None:
        board = chess.Board()
        board.push_uci("e2e4")
        observation = self.vision.observe(after_e2e3())

        self.assertFalse(observation.matches_board(board))

    def test_multiple_cursor_locations_make_window_ambiguous(self) -> None:
        board = chess.Board()
        board.push_uci("e2e3")
        board.push_uci("c7c5")
        window = self.vision.window(
            [after_c7c5(cursor="c7"), after_c7c5(cursor="b7")]
        )

        self.assertFalse(window.matches_board(board))

    def test_cursor_overlay_does_not_hide_a_missing_piece(self) -> None:
        board = chess.Board()
        board.push_uci("e2e3")
        missing_piece = after_e2e3(cursor=None)
        missing_piece[36 + 5 * 17 : 36 + 6 * 17, 44 + 4 * 8 : 44 + 5 * 8] = BACKGROUND
        paint(missing_piece, "e3", GOLD, 19)
        window = self.vision.window([missing_piece, missing_piece.copy(), missing_piece.copy()])

        self.assertFalse(window.matches_board(board))

    def test_transition_window_is_not_accepted_as_a_stable_board(self) -> None:
        after = chess.Board()
        after.push_uci("e2e3")
        window = self.vision.window([start_frame(), start_frame(cursor=None), after_e2e3(cursor=None)])

        self.assertFalse(window.is_stable)
        self.assertFalse(window.matches_board(chess.Board()))
        self.assertFalse(window.matches_board(after))
        stable = self.vision.window([after_e2e3(cursor=None)] * 3)
        self.assertTrue(stable.is_stable)
        self.assertTrue(stable.matches_board(after))

    def test_window_recovers_a_blinking_piece_but_keeps_cursor_square_masked(self) -> None:
        board = chess.Board()
        board.push_uci("e2e3")
        visible = after_e2e3(cursor="e2")
        hidden = visible.copy()
        hidden[36 + 5 * 17 : 36 + 6 * 17, 44 + 4 * 8 : 44 + 5 * 8] = BACKGROUND
        window = self.vision.window([visible if i % 4 == 0 else hidden for i in range(32)])

        self.assertEqual(window.cell("e3").side, "white")
        self.assertTrue(window.is_stable)
        self.assertFalse(window.matches_board(board))
        self.assertTrue(window.matches_board_except_cursor(board))

    def test_separate_stable_views_combine_to_verify_every_square(self) -> None:
        board = chess.Board()
        board.push_uci("e2e3")
        board.push_uci("c7c5")
        cursor_on_c7 = self.vision.window([after_c7c5(cursor="c7")] * 32)
        cursor_on_d4 = self.vision.window([after_c7c5(cursor="d4")] * 32)
        evidence = BoardEvidenceSet((cursor_on_c7, cursor_on_d4))

        self.assertTrue(evidence.matches_board(board))
        self.assertFalse(evidence.matches_board(chess.Board()))

    def test_one_cursor_masked_view_cannot_verify_a_complete_board(self) -> None:
        board = chess.Board()
        board.push_uci("e2e3")
        board.push_uci("c7c5")
        evidence = BoardEvidenceSet((self.vision.window([after_c7c5(cursor="c7")] * 32),))

        self.assertFalse(evidence.matches_board(board))


if __name__ == "__main__":
    unittest.main()
