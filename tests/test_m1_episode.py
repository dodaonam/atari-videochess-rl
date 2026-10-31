"""Tests for the transparent, non-engine M1 experiment move selector."""

from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import patch
from pathlib import Path
import tempfile

import chess
import numpy as np

from tests.test_m1_vision import BACKGROUND, BLUE, GOLD, paint, start_frame
from videochess_rl.episode import (
    StopCategory,
    agent_reward_from_ale,
    choose_cooperative_loss_move,
    choose_diagnostic_move,
    run_episode,
)
from videochess_rl.environment import ALEConfig, ALEFrame


PIECE_PIXELS = {
    chess.PAWN: 8,
    chess.BISHOP: 20,
    chess.KNIGHT: 25,
    chess.ROOK: 26,
    chess.QUEEN: 28,
    chess.KING: 26,
}


def render_fake_board(
    board: chess.Board,
    cursor: str,
    *,
    selected_source: str | None = None,
    selected_target: str | None = None,
    frame_number: int = 0,
) -> np.ndarray:
    rgb = np.empty((210, 160, 3), dtype=np.uint8)
    rgb[:] = BACKGROUND
    for square, piece in board.piece_map().items():
        name = chess.square_name(square)
        if name == cursor or name == selected_source:
            continue
        color = BLUE if piece.color == chess.WHITE else GOLD
        paint(rgb, name, color, PIECE_PIXELS[piece.piece_type])
    if selected_source is None:
        paint(rgb, cursor, GOLD, 19)
    else:
        piece = board.piece_at(chess.parse_square(selected_source))
        color = BLUE if piece.color == chess.WHITE else GOLD
        if selected_target in (None, selected_source):
            if frame_number % 2 == 0:
                paint(rgb, selected_source, color, PIECE_PIXELS[piece.piece_type])
        elif frame_number % 2 == 0:
            paint(rgb, selected_source, color, PIECE_PIXELS[piece.piece_type])
        else:
            paint(rgb, selected_target, color, PIECE_PIXELS[piece.piece_type])
    return rgb


class FakeALE:
    """Small action-driven ALE double for failure-boundary tests only."""

    def __init__(
        self,
        *,
        fail_target_fire: bool = False,
        fail_source_selection: bool = False,
        fail_selected_target_navigation: bool = False,
        stop_kind: str | None = None,
        stop_reward: float = 0.0,
        stop_after_fire_presses: int | None = None,
        stop_on_opponent_thinking: bool = False,
        opponent_thinking_noops: int = 35,
        overshoot_first_cursor_action: bool = False,
        target_fire_delay_noops: int = 0,
        desync_after_first_cursor_action: bool = False,
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
        self.target_fire_delay_noops = target_fire_delay_noops
        self.desync_after_first_cursor_action = desync_after_first_cursor_action
        self.target_fire_pending = False
        self.target_fire_noops = 0
        self.fail_source_selection = fail_source_selection
        self.fail_selected_target_navigation = fail_selected_target_navigation
        self.overshoot_first_cursor_action = overshoot_first_cursor_action
        self.overshot = False
        self.did_desync = False
        self.stop_kind = stop_kind
        self.stop_reward = stop_reward
        self.stop_after_fire_presses = stop_after_fire_presses
        self.stop_on_opponent_thinking = stop_on_opponent_thinking
        self.opponent_thinking_noops = opponent_thinking_noops
        self.fire_presses = 0
        self.opponent_noops = 0
        self.stopped = False
        self.steps_after_terminal = 0
        self.last_frame = None
        self.actions_seen: list[int] = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return None

    def _frame(self, reward=0.0, terminated=False, truncated=False):
        self.last_frame = ALEFrame(
            rgb=render_fake_board(
                self.board,
                self.cursor,
                selected_source=self.selected_source,
                selected_target=self.selected_target,
                frame_number=self.frame_number,
            ),
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
        self.target_fire_pending = False
        self.target_fire_noops = 0
        return self._frame()

    def runtime_info(self):
        return {"test_double": True}

    def diagnostic_ram(self, addresses):
        return {f"0x{address:02X}": 0 for address in addresses}

    def step(self, action):
        self.actions_seen.append(action)
        self.frame_number += 1
        if self.stopped:
            self.steps_after_terminal += 1
            return self._frame(self.stop_reward, self.stop_kind == "terminated", self.stop_kind == "truncated")
        if (
            self.stop_kind
            and self.stop_after_fire_presses is None
            and not self.stop_on_opponent_thinking
            and action in (1, 2, 3, 4, 5, 6, 7, 8, 9)
        ):
            self.stopped = True
            return self._frame(
                self.stop_reward,
                self.stop_kind == "terminated",
                self.stop_kind == "truncated",
            )
        if action == 1 and self.held_action != 1:
            self.fire_presses += 1
            if self.stop_kind and self.stop_after_fire_presses == self.fire_presses:
                self.stopped = True
                return self._frame(
                    self.stop_reward,
                    self.stop_kind == "terminated",
                    self.stop_kind == "truncated",
                )
        if action == 0 and self.stop_kind and self.stop_on_opponent_thinking:
            if self.fire_presses >= 2:
                self.opponent_noops += 1
                if self.opponent_noops >= self.opponent_thinking_noops:
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
                        if self.desync_after_first_cursor_action and not self.did_desync:
                            self.board.push_uci("g1f3")
                            self.did_desync = True
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
                    if 0 <= row < 8 and 0 <= col < 8 and not self.fail_selected_target_navigation:
                        self.selected_target = chr(ord("a") + col) + str(8 - row)
        elif action == 0:
            self.held_action = None
            self.held_frames = 0
            if self.target_fire_pending:
                self.target_fire_noops += 1
                if self.target_fire_noops >= self.target_fire_delay_noops:
                    move = chess.Move.from_uci(self.selected_source + self.selected_target)
                    if move in self.board.legal_moves:
                        self.board.push(move)
                        self.cursor = self.selected_source
                    self.selected_source = None
                    self.selected_target = None
                    self.target_fire_pending = False
        elif action == 1:
            if self.held_action == 1:
                return self._frame()
            self.held_action = 1
            self.held_frames = 0
            if self.selected_source is None:
                piece = self.board.piece_at(chess.parse_square(self.cursor))
                if piece is not None and piece.color == chess.WHITE and not self.fail_source_selection:
                    self.selected_source = self.cursor
                    self.selected_target = self.cursor
            elif not self.fail_target_fire:
                if self.target_fire_delay_noops:
                    self.target_fire_pending = True
                else:
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

    def test_cooperative_loss_policy_uses_legal_fools_mate_blunders(self) -> None:
        board = chess.Board()
        self.assertEqual(choose_cooperative_loss_move(board), "f2f3")
        board.push_uci("f2f3")
        board.push_uci("c7c5")
        self.assertEqual(choose_cooperative_loss_move(board), "g2g4")
        board.push_uci("g2g4")
        board.push_uci("b8c6")
        self.assertEqual(choose_cooperative_loss_move(board), "a2a3")
        board.push_uci("a2a3")
        board.push_uci("e7e5")
        self.assertEqual(choose_cooperative_loss_move(board), "b2b3")
        board.push_uci("b2b3")
        self.assertIn(chess.Move.from_uci("d8h4"), board.legal_moves)
        mate = board.copy()
        mate.push_uci("d8h4")
        self.assertTrue(mate.is_checkmate())

    def test_cooperative_loss_policy_does_not_immediately_undo_its_last_move(self) -> None:
        board = chess.Board()
        for move in ("a2a3", "c7c5", "a1a2", "b8c6"):
            board.push_uci(move)

        self.assertNotEqual(choose_cooperative_loss_move(board), "a2a1")

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
        self.assertIn("selected-piece preview remained visible", result["failure"])
        self.assertIn(
            "target_confirmation_uncertain",
            [event["phase"] for event in result["turns"][0]["input_phases"]],
        )
        self.assertFalse(result["turns"][0]["player_move"]["verified_from_rgb"])
        self.assertEqual(result["terminal"]["last_verified_fen"], chess.Board().fen())

    def test_target_fire_settling_wait_accepts_a_delayed_rgb_transition_without_retry(self) -> None:
        fake = FakeALE(target_fire_delay_noops=55)
        result = self.run_fake(fake)

        phases = [event["phase"] for event in result["turns"][0]["input_phases"]]
        self.assertIn("target_confirmation_settle_wait", phases)
        self.assertNotIn("target_confirmation_uncertain", phases)
        self.assertEqual(result["turns"][0]["player_move"]["uci"], "e2e3")
        self.assertEqual(result["turns"][0]["player_move"]["candidate_fen"], "rnbqkbnr/pppppppp/8/8/8/4P3/PPPP1PPP/RNBQKBNR b KQkq - 0 1")
        self.assertFalse(result["turns"][0]["player_move"]["verified_from_rgb"], "without an Atari reply, full-board shadow advancement remains blocked")
        self.assertIn("No stable unique legal Atari reply", result["failure"])
        self.assertEqual(fake.fire_presses, 2, "the source and target each receive exactly one FIRE press")

    def test_unverified_source_selection_stops_before_target_navigation(self) -> None:
        fake = FakeALE(fail_source_selection=True)
        result = self.run_fake(fake)

        self.assertEqual(result["status"], "partial")
        phases = [event["phase"] for event in result["turns"][0]["input_phases"]]
        self.assertIn("source_selection_uncertain", phases)
        self.assertNotIn("selected_target_navigation_requested", phases)
        self.assertEqual(result["terminal"]["last_verified_fen"], chess.Board().fen())

    def test_unverified_selected_target_stops_without_retry_or_target_fire(self) -> None:
        fake = FakeALE(fail_selected_target_navigation=True)
        result = self.run_fake(fake)

        self.assertEqual(result["status"], "partial")
        phases = [event["phase"] for event in result["turns"][0]["input_phases"]]
        self.assertIn("selected_target_uncertain", phases)
        self.assertNotIn("target_confirmation_requested", phases)
        self.assertEqual(fake.actions_seen.count(1), 1, "only the source-selection FIRE should be issued")
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
        diagnostics = result["terminal"]["cursor_diagnostics"]
        self.assertGreaterEqual(diagnostics["unexpected_displacements"], 1)
        self.assertGreaterEqual(diagnostics["unexpected_displacements_corrected"], 1)
        self.assertEqual(diagnostics["stable_board_disagreements"], 0)

    def test_stable_rgb_board_disagreement_stops_and_is_not_cursor_correction(self) -> None:
        result = self.run_fake(FakeALE(desync_after_first_cursor_action=True))
        self.assertEqual(result["terminal"]["runner_stop_category"], StopCategory.CONTROLLER_BOARD_DESYNCHRONIZED.value)
        diagnostics = result["terminal"]["cursor_diagnostics"]
        self.assertEqual(diagnostics["stable_board_disagreements"], 1)
        self.assertEqual(diagnostics["unexpected_displacements_corrected"], 0)

    def test_recorded_post_reset_frame_budget_subtracts_reset_counter_origin(self) -> None:
        result = self.run_fake(FakeALE(stop_kind="terminated", stop_reward=-1.0))
        terminal = result["terminal"]
        self.assertEqual(terminal["post_reset_action_frames"], terminal["ale_frames"] - terminal["reset_frame_number"])
        self.assertEqual(terminal["reset_frame_number"], result["reset"]["frame_number"])

    def test_process_rss_limit_stops_before_another_ale_action(self) -> None:
        fake = FakeALE()
        with patch("videochess_rl.episode.resource.getrusage", return_value=SimpleNamespace(ru_maxrss=1)):
            result = self.run_fake(fake, max_process_rss_bytes=1)
        self.assertEqual(result["terminal"]["runner_stop_category"], StopCategory.RUNNER_RESOURCE_LIMIT.value)
        self.assertEqual(fake.actions_seen, [])

    def test_artifact_limit_at_reset_is_recorded_without_gameplay(self) -> None:
        fake = FakeALE()
        with tempfile.TemporaryDirectory() as directory:
            result = self.run_fake(fake, artifact_dir=str(Path(directory) / "frames"), max_artifact_bytes=1)
        self.assertEqual(result["status"], "runner_stopped")
        self.assertEqual(result["terminal"]["runner_stop_category"], StopCategory.RUNNER_ARTIFACT_LIMIT.value)
        self.assertEqual(result["terminal"]["player_moves_attempted"], 0)
        self.assertEqual(fake.actions_seen, [])

    def test_wall_clock_limit_is_not_reported_as_ale_termination(self) -> None:
        fake = FakeALE()
        result = self.run_fake(fake, max_episode_seconds=1e-9)
        self.assertEqual(result["status"], "runner_stopped")
        self.assertEqual(result["terminal"]["runner_stop_category"], StopCategory.RUNNER_MAX_WALL_CLOCK.value)
        self.assertFalse(result["terminal"]["ale_terminated"])
        self.assertEqual(fake.actions_seen, [])

    def test_episode_frame_budget_is_not_reported_as_ale_truncation(self) -> None:
        result = self.run_fake(FakeALE(), max_episode_frames=40)

        self.assertEqual(result["status"], "runner_stopped")
        self.assertFalse(result["terminal"]["terminated"])
        self.assertFalse(result["terminal"]["truncated"])
        self.assertEqual(result["terminal"]["runner_stop_category"], StopCategory.RUNNER_MAX_ALE_FRAMES.value)
        self.assertIn("frame budget", result["failure"])

    def test_termination_during_input_records_reward_and_stops_stepping(self) -> None:
        fake = FakeALE(stop_kind="terminated", stop_reward=1.0)
        result = self.run_fake(fake)

        self.assertTrue(result["terminal"]["terminated"])
        self.assertFalse(result["terminal"]["truncated"])
        self.assertEqual(result["terminal"]["ale_reward_total"], 1.0)
        self.assertEqual(result["terminal"]["agent_reward_total"], 1.0)
        self.assertEqual(result["status"], "ale_terminated")
        self.assertEqual(result["terminal"]["runner_stop_category"], StopCategory.ALE_TERMINATED.value)
        terminal_visual = result["terminal_observation"]
        self.assertLess(
            terminal_visual["pre_terminal_frame"]["frame_number"],
            terminal_visual["frame_number"],
        )
        self.assertEqual(len(terminal_visual["pre_terminal_frame"]["rgb_sha256"]), 64)
        self.assertEqual(fake.steps_after_terminal, 0)
        self.assertIn("episode_finished", [event["state"] for event in result["turn_events"]])

    def test_terminal_at_target_fire_is_not_overwritten_by_rgb_confirmation_failure(self) -> None:
        fake = FakeALE(stop_kind="terminated", stop_reward=-1.0, stop_after_fire_presses=2)
        result = self.run_fake(fake)

        self.assertEqual(result["status"], "ale_terminated")
        self.assertEqual(result["terminal"]["runner_stop_category"], StopCategory.ALE_TERMINATED.value)
        self.assertEqual(result["terminal"]["ale_reward_total"], -1.0)
        self.assertEqual(result["terminal_observation"]["phase"], "select_target")
        self.assertEqual(fake.steps_after_terminal, 0)

    def test_terminal_during_opponent_thinking_stops_without_requesting_another_turn(self) -> None:
        fake = FakeALE(stop_kind="terminated", stop_reward=-1.0, stop_on_opponent_thinking=True)
        result = self.run_fake(fake)

        self.assertEqual(result["status"], "ale_terminated")
        self.assertEqual(result["terminal"]["ale_reward_total"], -1.0)
        self.assertEqual(result["terminal_observation"]["phase"], "Atari thinking/reply observation")
        self.assertEqual(fake.steps_after_terminal, 0)

    def test_environment_step_budget_has_a_distinct_runner_stop_category(self) -> None:
        result = self.run_fake(FakeALE(), max_episode_env_steps=1)

        self.assertEqual(result["status"], "runner_stopped")
        self.assertEqual(result["terminal"]["runner_stop_category"], StopCategory.RUNNER_MAX_ENV_STEPS.value)
        self.assertFalse(result["terminal"]["ale_terminated"])
        self.assertFalse(result["terminal"]["ale_truncated"])

    def test_truncation_is_distinct_from_termination(self) -> None:
        fake = FakeALE(stop_kind="truncated")
        result = self.run_fake(fake)

        self.assertFalse(result["terminal"]["terminated"])
        self.assertTrue(result["terminal"]["truncated"])
        self.assertEqual(result["terminal"]["ale_reward_total"], 0.0)
        self.assertEqual(result["status"], "ale_truncated")
        self.assertEqual(result["terminal"]["runner_stop_category"], StopCategory.ALE_TRUNCATED.value)
        self.assertIn("episode_truncated", [event["state"] for event in result["turn_events"]])

    def test_white_perspective_reward_conversion_is_explicit(self) -> None:
        self.assertEqual(agent_reward_from_ale(1.0, chess.WHITE), 1.0)
        self.assertEqual(agent_reward_from_ale(-1.0, chess.WHITE), -1.0)
        self.assertEqual(agent_reward_from_ale(1.0, chess.BLACK), -1.0)


if __name__ == "__main__":
    unittest.main()
