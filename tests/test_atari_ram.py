"""Tests for the documented VideoChess RAM interaction contract."""

from __future__ import annotations

import unittest

import chess
import numpy as np

from videochess_rl.atari_ram import (
    VideoChessRAMState,
    acknowledges_target_fire,
    ram_index_square,
    ram_square_index,
)


class VideoChessRamStateTests(unittest.TestCase):
    def test_square_indices_follow_the_roms_rank_eight_to_rank_one_layout(self) -> None:
        self.assertEqual(ram_square_index("a8"), 0)
        self.assertEqual(ram_square_index("h8"), 7)
        self.assertEqual(ram_square_index("e2"), 52)
        self.assertEqual(ram_square_index("h1"), 63)
        self.assertEqual(ram_index_square(39), "h4")

    def test_piece_decoder_matches_the_standard_position_and_exact_piece_kinds(self) -> None:
        ram = np.zeros(128, dtype=np.uint8)
        for square, piece in chess.Board().piece_map().items():
            piece_code = {
                chess.KING: 1,
                chess.QUEEN: 2,
                chess.BISHOP: 3,
                chess.KNIGHT: 4,
                chess.ROOK: 5,
                chess.PAWN: 6,
            }[piece.piece_type]
            if piece.color:
                piece_code |= 0x08
            # High bits are ROM rendering/move flags; the low nibble is the
            # documented exact kind/color identity.
            ram[ram_square_index(square)] = piece_code | 0xC0

        state = VideoChessRAMState.from_ram(ram)

        self.assertTrue(state.board_matches(chess.Board()))
        ram[ram_square_index("h4")] = 0xC3
        self.assertFalse(VideoChessRAMState.from_ram(ram).board_matches(chess.Board()))

    def test_selection_acknowledgement_and_target_square_are_independent(self) -> None:
        ram = np.zeros(128, dtype=np.uint8)
        ram[0x59] = ram_square_index("h1")
        ram[0x5A] = ram_square_index("h4")
        ram[0x73] = 0x01
        ram[0x75] = 0
        selected = VideoChessRAMState.from_ram(ram)
        self.assertTrue(selected.piece_selected)
        self.assertFalse(selected.target_accepted)
        self.assertEqual((selected.source_square, selected.target_square), ("h1", "h4"))
        self.assertTrue(selected.move_is_valid)

        ram[0x73] = 0xC0
        accepted = VideoChessRAMState.from_ram(ram)
        self.assertTrue(accepted.target_accepted)
        self.assertFalse(accepted.piece_selected)

    def test_delayed_target_fire_ack_is_not_claimed_until_matching_atari_state(self) -> None:
        ram = np.zeros(128, dtype=np.uint8)
        ram[0x59] = ram_square_index("h1")
        ram[0x5A] = ram_square_index("h4")
        ram[0x75] = 0

        # The target remains selected through early frames; an ignored FIRE
        # has the same state. Neither condition permits a retry or shadow move.
        ram[0x73] = 0x01
        self.assertFalse(
            acknowledges_target_fire(VideoChessRAMState.from_ram(ram), "h1", "h4")
        )
        ram[0x73] = 0x01
        self.assertFalse(
            acknowledges_target_fire(VideoChessRAMState.from_ram(ram), "h1", "h4")
        )

        # Only the later, matching ROM search-state transition acknowledges
        # the single pending FIRE operation.
        ram[0x73] = 0xC0
        self.assertTrue(
            acknowledges_target_fire(VideoChessRAMState.from_ram(ram), "h1", "h4")
        )

    def test_target_fire_state_change_with_wrong_target_is_not_acknowledged(self) -> None:
        ram = np.zeros(128, dtype=np.uint8)
        ram[0x59] = ram_square_index("h1")
        ram[0x5A] = ram_square_index("h3")
        ram[0x73] = 0xC0
        ram[0x75] = 0

        self.assertFalse(
            acknowledges_target_fire(VideoChessRAMState.from_ram(ram), "h1", "h4")
        )

    def test_target_fire_with_invalid_rom_move_flag_is_not_acknowledged(self) -> None:
        ram = np.zeros(128, dtype=np.uint8)
        ram[0x59] = ram_square_index("h1")
        ram[0x5A] = ram_square_index("h4")
        ram[0x73] = 0xC0
        ram[0x75] = 0xFF

        self.assertFalse(
            acknowledges_target_fire(VideoChessRAMState.from_ram(ram), "h1", "h4")
        )

    def test_selected_piece_target_preview_is_not_treated_as_a_committed_move(self) -> None:
        board = chess.Board()
        ram = np.zeros(128, dtype=np.uint8)
        rom_codes = {
            chess.KING: 1,
            chess.QUEEN: 2,
            chess.BISHOP: 3,
            chess.KNIGHT: 4,
            chess.ROOK: 5,
            chess.PAWN: 6,
        }
        for square, piece in board.piece_map().items():
            code = rom_codes[piece.piece_type] | (0x08 if piece.color else 0)
            ram[ram_square_index(square)] = code
        ram[ram_square_index("d1")] = 0x09  # White king preview; e1 remains occupied.
        state = VideoChessRAMState.from_ram(ram)

        self.assertFalse(state.board_matches(board))
        self.assertTrue(state.board_matches_selected_preview(board, "e1", "d1"))
        ram[ram_square_index("a1")] = 0  # Unrelated-square corruption is never preview evidence.
        self.assertFalse(
            VideoChessRAMState.from_ram(ram).board_matches_selected_preview(board, "e1", "d1")
        )

    def test_malformed_ram_size_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "128 ALE RAM bytes"):
            VideoChessRAMState.from_ram(np.zeros(64, dtype=np.uint8))


if __name__ == "__main__":
    unittest.main()
