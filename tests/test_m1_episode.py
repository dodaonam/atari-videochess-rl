"""Tests for the transparent, non-engine M1 experiment move selector."""

from __future__ import annotations

import unittest

import chess
import numpy as np

from tests.test_m1_vision import BACKGROUND, BLUE, GOLD, paint, start_frame
from videochess_rl.episode import agent_reward_from_ale, choose_diagnostic_move, run_episode
from videochess_rl.environment import ALEConfig, ALEFrame


PIECE_PIXELS = {
    chess.PAWN: 8,
    chess.BISHOP: 20,
    chess.KNIGHT: 25,
    chess.ROOK: 26,
    chess.QUEEN: 28,
    chess.KING: 26,
}


def render_fake_board(board: chess.Board, cursor: str) -> np.ndarray:
    rgb = np.empty((210, 160, 3), dtype=np.uint8)
    rgb[:] = BACKGROUND
    for square, piece in board.piece_map().items():
        name = chess.square_name(square)
        if name == cursor:
            continue
        color = BLUE if piece.color == chess.WHITE else GOLD
        paint(rgb, name, color, PIECE_PIXELS[piece.piece_type])
    paint(rgb, cursor, GOLD, 19)
    return rgb


class FakeALE:
    """Small action-driven ALE double for failure-boundary tests only."""

    def __init__(
        self,
        *,
        fail_target_fire: bool = False,
        stop_kind: str | None = None,
        stop_reward: float = 0.0,
        overshoot_first_cursor_action: bool = False,
    ):
        self.config = None
        self.board = chess.Board()
        self.cursor = "d4"
        self.selected_source: str | None = None
        self.selected_target: str | None = None
        self.held_action: int | None = None
        self.held_frames = 0
        self.frame_number = 0
        self.fail_target_fire = fail_target_fire
        self.overshoot_first_cursor_action = overshoot_first_cursor_action
        self.overshot = False
        self.stop_kind = stop_kind
        self.stop_reward = stop_reward
        self.stopped = False
        self.steps_after_terminal = 0
        self.last_frame = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return None

    def _frame(self, reward=0.0, terminated=False, truncated=False):
        self.last_frame = ALEFrame(
            rgb=render_fake_board(self.board, self.cursor),
            reward=reward,
            terminated=terminated,
            truncated=truncated,
            info={},
            frame_number=self.frame_number,
        )
        return self.last_frame

    def reset(self, *, seed=None):
        self.frame_number = 0
        self.board = chess.Board()
        self.cursor = "d4"
        self.selected_source = None
        self.selected_target = None
        return self._frame()

    def runtime_info(self):
        return {"test_double": True}

    def diagnostic_ram(self, addresses):
        return {f"0x{address:02X}": 0 for address in addresses}

    def step(self, action):
        self.frame_number += 1
        if self.stopped:
            self.steps_after_terminal += 1
            return self._frame(self.stop_reward, self.stop_kind == "terminated", self.stop_kind == "truncated")
        if self.stop_kind and action in (1, 2, 3, 4, 5, 6, 7, 8, 9):
            self.stopped = True
            return self._frame(
                self.stop_reward,
                self.stop_kind == "terminated",
                self.stop_kind == "truncated",
            )
        if action in (2, 3, 4, 5, 6, 7, 8, 9):
            if self.held_action != action:
                self.held_action = action
                self.held_frames = 0
            self.held_frames += 1
            if self.held_frames >= 33:
                self.held_frames = 0
                step = 2 if self.overshoot_first_cursor_action and not self.overshot else 1
                if step == 2:
                    self.overshot = True
                if self.selected_source is None:
                    row = 8 - int(self.cursor[1])
                    col = ord(self.cursor[0]) - ord("a")
                    if action == 2:
                        row -= step
                    elif action == 3:
                        col += step
                    elif action == 4:
                        col -= step
                    elif action == 5:
                        row += step
                    elif action == 6:
                        row -= step; col += step
                    elif action == 7:
                        row -= step; col -= step
                    elif action == 8:
                        row += step; col += step
                    else:
                        row += step; col -= step
                    if 0 <= row < 8 and 0 <= col < 8:
                        self.cursor = chr(ord("a") + col) + str(8 - row)
                else:
                    square = self.selected_target
                    row = 8 - int(square[1])
                    col = ord(square[0]) - ord("a")
                    if action == 2:
                        row -= 1
                    elif action == 3:
                        col += 1
                    elif action == 4:
                        col -= 1
                    elif action == 5:
                        row += 1
                    elif action == 6:
                        row -= 1; col += 1
                    elif action == 7:
                        row -= 1; col -= 1
                    elif action == 8:
                        row += 1; col += 1
                    else:
                        row += 1; col -= 1
                    if 0 <= row < 8 and 0 <= col < 8:
                        self.selected_target = chr(ord("a") + col) + str(8 - row)
        elif action == 0:
            self.held_action = None
            self.held_frames = 0
        elif action == 1:
            self.held_action = None
            self.held_frames = 0
            if self.selected_source is None:
                piece = self.board.piece_at(chess.parse_square(self.cursor))
                if piece is not None and piece.color == chess.WHITE:
                    self.selected_source = self.cursor
                    self.selected_target = self.cursor
            elif not self.fail_target_fire:
                move = chess.Move.from_uci(self.selected_source + self.selected_target)
                if move in self.board.legal_moves:
                    self.board.push(move)
                    self.cursor = self.selected_source
                self.selected_source = None
                self.selected_target = None
        return self._frame()


class DiagnosticMoveSelectorTests(unittest.TestCase):
    def test_selector_is_deterministic_and_returns_a_current_legal_move(self) -> None:
        board = chess.Board()
        board.push_uci("e2e3")
        board.push_uci("c7c5")

        first = choose_diagnostic_move(board)
        second = choose_diagnostic_move(board)

        self.assertEqual(first, second)
        self.assertIn(chess.Move.from_uci(first), board.legal_moves)

    def test_initial_move_is_the_disclosed_one_ply_feasibility_choice(self) -> None:
        self.assertEqual(choose_diagnostic_move(chess.Board()), "e2e3")

    def test_selector_takes_an_immediate_checkmate(self) -> None:
        board = chess.Board()
        for move in ("e2e4", "e7e5", "d1h5", "b8c6", "f1c4", "g8f6"):
            board.push_uci(move)

        move = choose_diagnostic_move(board)

        candidate = board.copy()
        candidate.push_uci(move)
        self.assertTrue(candidate.is_checkmate())

    def test_selector_prefers_a_one_square_atari_input_when_capture_needs_long_route(self) -> None:
        board = chess.Board()
        for move in ("e2e3", "c7c5", "e3e4", "b8c6", "d2d3", "e7e5", "d3d4", "c5d4"):
            board.push_uci(move)

        move = choose_diagnostic_move(board)

        self.assertEqual(move, "a2a3")

    def test_selector_does_not_repeat_a_failed_h_file_route(self) -> None:
        board = chess.Board()
        for move in (
            "e2e3", "c7c5", "e3e4", "b8c6", "d2d3", "e7e5", "d3d4", "c5d4",
            "a2a3", "d7d5",
        ):
            board.push_uci(move)

        self.assertEqual(choose_diagnostic_move(board), "b2b3")


class EpisodeSafetyTests(unittest.TestCase):
    def run_fake(self, fake: FakeALE, **kwargs):
        parameters = {
            "config": ALEConfig.deterministic_dev(),
            "seed": 7,
            "move_selector": lambda board: "e2e3",
            "max_player_moves": 1,
            "max_opponent_wait_frames": 33,
            "max_episode_frames": 10000,
            "max_episode_seconds": 30,
            "env_factory": lambda config: fake,
        }
        parameters.update(kwargs)
        return run_episode(**parameters)

    def test_failed_target_fire_stops_without_advancing_shadow(self) -> None:
        result = self.run_fake(FakeALE(fail_target_fire=True))

        self.assertEqual(result["status"], "partial")
        self.assertIn("FIRE selection or target input may have failed", result["failure"])
        self.assertFalse(result["turns"][0]["player_move"]["verified_from_rgb"])
        self.assertEqual(result["terminal"]["last_verified_fen"], chess.Board().fen())

    def test_missing_atari_reply_leaves_the_shadow_at_last_verified_state(self) -> None:
        result = self.run_fake(FakeALE())

        self.assertEqual(result["status"], "partial")
        self.assertIn("No stable unique legal Atari reply", result["failure"])
        self.assertEqual(result["terminal"]["last_verified_fen"], chess.Board().fen())

    def test_opponent_wait_does_not_exceed_its_frame_cap(self) -> None:
        result = self.run_fake(FakeALE(), max_opponent_wait_frames=40)

        self.assertEqual(result["status"], "partial")
        self.assertLessEqual(result["turns"][0]["opponent_reply"]["frames_waited"], 40)

    def test_unexpected_cursor_displacement_is_observed_and_replanned(self) -> None:
        result = self.run_fake(FakeALE(overshoot_first_cursor_action=True))

        self.assertTrue(any(event["unexpected_displacement"] for event in result["cursor_observations"]))
        self.assertTrue(any(event["from_square"] == "f2" and event["observed_square"] == "e3" for event in result["cursor_observations"]))

    def test_episode_frame_budget_is_not_reported_as_ale_truncation(self) -> None:
        result = self.run_fake(FakeALE(), max_episode_frames=40)

        self.assertEqual(result["status"], "partial")
        self.assertFalse(result["terminal"]["terminated"])
        self.assertFalse(result["terminal"]["truncated"])
        self.assertIn("frame budget", result["failure"])

    def test_termination_during_input_records_reward_and_stops_stepping(self) -> None:
        fake = FakeALE(stop_kind="terminated", stop_reward=1.0)
        result = self.run_fake(fake)

        self.assertTrue(result["terminal"]["terminated"])
        self.assertFalse(result["terminal"]["truncated"])
        self.assertEqual(result["terminal"]["ale_reward_total"], 1.0)
        self.assertEqual(result["terminal"]["agent_reward_total"], 1.0)
        self.assertEqual(fake.steps_after_terminal, 0)
        self.assertIn("episode_finished", [event["state"] for event in result["turn_events"]])

    def test_truncation_is_distinct_from_termination(self) -> None:
        fake = FakeALE(stop_kind="truncated")
        result = self.run_fake(fake)

        self.assertFalse(result["terminal"]["terminated"])
        self.assertTrue(result["terminal"]["truncated"])
        self.assertEqual(result["terminal"]["ale_reward_total"], 0.0)
        self.assertIn("episode_truncated", [event["state"] for event in result["turn_events"]])

    def test_white_perspective_reward_conversion_is_explicit(self) -> None:
        self.assertEqual(agent_reward_from_ale(1.0, chess.WHITE), 1.0)
        self.assertEqual(agent_reward_from_ale(-1.0, chess.WHITE), -1.0)
        self.assertEqual(agent_reward_from_ale(1.0, chess.BLACK), -1.0)


if __name__ == "__main__":
    unittest.main()
