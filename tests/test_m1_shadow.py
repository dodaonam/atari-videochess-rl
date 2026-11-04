"""Shadow-board checks never replace a missing or contradictory RGB move."""

from __future__ import annotations

import unittest

import chess
import numpy as np

from tests.test_m1_vision import after_c7c5, after_e2e3, start_frame
from videochess_rl.atari_ram import VideoChessRAMState, ram_square_index
from videochess_rl.shadow import DesynchronizationError, ShadowBoard
from videochess_rl.vision import VideoChessVision


class ShadowBoardTests(unittest.TestCase):
    def setUp(self) -> None:
        self.vision = VideoChessVision()
        self.shadow = ShadowBoard()

    def test_player_move_is_applied_only_after_rgb_confirms_it(self) -> None:
        window = self.vision.window([after_e2e3(), after_e2e3(cursor=None), after_e2e3(cursor=None)])

        self.shadow.apply_observed_move("e2e3", window)

        self.assertEqual(self.shadow.board.peek(), chess.Move.from_uci("e2e3"))
        self.assertEqual(self.shadow.board.turn, chess.BLACK)

    def test_legal_opponent_reply_is_inferred_from_rgb(self) -> None:
        player_window = self.vision.window([after_e2e3(), after_e2e3(cursor=None), after_e2e3(cursor=None)])
        self.shadow.apply_observed_move("e2e3", player_window)
        reply_window = self.vision.window(
            [after_c7c5(cursor="c7"), after_c7c5(cursor=None), after_c7c5(cursor=None), after_c7c5(cursor="c7")]
        )

        reply = self.shadow.apply_observed_reply(reply_window)

        self.assertEqual(reply, "c7c5")
        self.assertEqual(self.shadow.board.peek(), chess.Move.from_uci("c7c5"))

    def test_opponent_wait_is_not_misreported_as_a_move(self) -> None:
        before = self.shadow.board.fen()
        window = self.vision.window([start_frame(), start_frame(cursor=None), start_frame(cursor=None)])

        self.assertIsNone(self.shadow.infer_observed_reply(window))
        self.assertEqual(self.shadow.board.fen(), before)

    def test_illegal_player_move_does_not_change_shadow_position(self) -> None:
        before = self.shadow.board.fen()
        window = self.vision.window([after_e2e3()])

        with self.assertRaises(ValueError):
            self.shadow.apply_observed_move("e2e5", window)

        self.assertEqual(self.shadow.board.fen(), before)

    def test_rgb_mismatch_raises_without_repairing_shadow_position(self) -> None:
        before = self.shadow.board.fen()
        wrong_window = self.vision.window([after_e2e3()])

        with self.assertRaises(DesynchronizationError):
            self.shadow.apply_observed_move("e2e4", wrong_window)

        self.assertEqual(self.shadow.board.fen(), before)

    def test_observed_sequence_advances_only_after_full_rgb_position_matches(self) -> None:
        window = self.vision.window([after_c7c5(cursor=None)] * 3)

        moves = self.shadow.apply_observed_sequence(("e2e3", "c7c5"), window)

        self.assertEqual(moves, ("e2e3", "c7c5"))
        self.assertEqual(self.shadow.board.fen(), "rnbqkbnr/pp1ppppp/8/2p5/8/4P3/PPPP1PPP/RNBQKBNR w KQkq - 0 2")

    def test_cursor_masked_partial_board_cannot_advance_the_shadow(self) -> None:
        board = chess.Board()
        board.push_uci("e2e3")
        visible = after_e2e3(cursor="e2")
        hidden = visible.copy()
        hidden[36 + 5 * 17 : 36 + 6 * 17, 44 + 4 * 8 : 44 + 5 * 8] = (24, 26, 167)
        window = self.vision.window([visible if i % 4 == 0 else hidden for i in range(32)])
        before = self.shadow.board.fen()

        self.assertTrue(window.matches_board_except_cursor(board))
        with self.assertRaises(DesynchronizationError):
            self.shadow.apply_observed_sequence(("e2e3",), window)
        self.assertEqual(self.shadow.board.fen(), before)

    def test_partial_reply_inference_does_not_advance_shadow(self) -> None:
        self.shadow.board.push_uci("e2e3")
        window = self.vision.window([after_c7c5(cursor="c7")] * 32)
        before = self.shadow.board.fen()

        reply = self.shadow.infer_observed_reply(window, allow_cursor_masked_square=True)

        self.assertEqual(reply, "c7c5")
        self.assertEqual(self.shadow.board.fen(), before)

    def test_terminal_ram_sequence_requires_termination_reward_mate_and_exact_board(self) -> None:
        moves = ("f2f3", "e7e5", "g2g4", "d8h4")
        terminal = chess.Board()
        for move in moves:
            terminal.push_uci(move)
        self.assertTrue(terminal.is_checkmate())
        ram = np.zeros(128, dtype=np.uint8)
        rom_codes = {
            chess.KING: 1,
            chess.QUEEN: 2,
            chess.BISHOP: 3,
            chess.KNIGHT: 4,
            chess.ROOK: 5,
            chess.PAWN: 6,
        }
        for square, piece in terminal.piece_map().items():
            code = rom_codes[piece.piece_type] | (0x08 if piece.color else 0)
            ram[ram_square_index(square)] = code
        evidence = VideoChessRAMState.from_ram(ram)

        applied = self.shadow.apply_terminal_ram_verified_sequence(
            moves, evidence, ale_terminated=True, ale_reward=-1.0
        )

        self.assertEqual(applied, moves)
        self.assertEqual(self.shadow.board.fen(), terminal.fen())

    def test_terminal_ram_mismatch_or_nonterminal_cannot_advance_shadow(self) -> None:
        before = self.shadow.board.fen()
        terminal = chess.Board()
        for move in ("f2f3", "e7e5", "g2g4", "d8h4"):
            terminal.push_uci(move)
        ram = np.zeros(128, dtype=np.uint8)
        evidence = VideoChessRAMState.from_ram(ram)
        with self.assertRaises(DesynchronizationError):
            self.shadow.apply_terminal_ram_verified_sequence(
                ("f2f3", "e7e5", "g2g4", "d8h4"),
                evidence,
                ale_terminated=True,
                ale_reward=-1.0,
            )
        with self.assertRaises(DesynchronizationError):
            self.shadow.apply_terminal_ram_verified_sequence(
                ("f2f3", "e7e5", "g2g4", "d8h4"),
                evidence,
                ale_terminated=False,
                ale_reward=-1.0,
            )
        self.assertEqual(self.shadow.board.fen(), before)


if __name__ == "__main__":
    unittest.main()
