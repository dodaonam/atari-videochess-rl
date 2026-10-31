"""Bounded real-ALE closed-loop check; RGB frames, not mocks, decide the result."""

from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

import chess

from videochess_rl.demo import run_closed_loop
from videochess_rl.environment import ALEConfig, VideoChessEnv
from videochess_rl.episode import DecisionResult, choose_diagnostic_move, run_episode
from videochess_rl.episode import StopCategory
from videochess_rl.shadow import DesynchronizationError, ShadowBoard
from videochess_rl.vision import VideoChessVision


class RealALEClosedLoopTests(unittest.TestCase):
    def test_real_episode_plans_second_player_move_from_verified_evolving_board(self) -> None:
        with tempfile.TemporaryDirectory(prefix="videochess-m1-multiturn-") as directory:
            result = run_episode(
                config=ALEConfig.deterministic_dev(),
                seed=20261015,
                move_selector=choose_diagnostic_move,
                max_player_moves=2,
                max_opponent_wait_frames=10000,
                max_episode_frames=20000,
                max_episode_seconds=180,
                artifact_dir=directory,
            )

        self.assertEqual(result["status"], "runner_stopped", result.get("failure"))
        self.assertEqual(result["terminal"]["runner_stop_category"], StopCategory.RUNNER_MAX_PLAYER_MOVES.value)
        self.assertFalse(result["terminal"]["ale_terminated"])
        self.assertEqual(len(result["turns"]), 2)
        self.assertNotEqual(result["turns"][1]["board_before_fen"], chess.Board().fen())
        for turn in result["turns"]:
            self.assertTrue(turn["player_move"]["verified_from_rgb"])
            self.assertTrue(turn["opponent_reply"]["verified_from_rgb"])
            before = chess.Board(turn["board_before_fen"])
            self.assertIn(chess.Move.from_uci(turn["player_move"]["uci"]), before.legal_moves)

    def test_multiturn_runner_verifies_one_real_rgb_move_cycle(self) -> None:
        with tempfile.TemporaryDirectory(prefix="videochess-m1-episode-") as directory:
            result = run_episode(
                config=ALEConfig.deterministic_dev(),
                seed=20261015,
                move_selector=lambda board: "e2e3",
                max_player_moves=1,
                max_opponent_wait_frames=10000,
                max_episode_frames=10000,
                max_episode_seconds=120,
                artifact_dir=directory,
            )

        self.assertEqual(result["status"], "runner_stopped", result.get("failure"))
        self.assertEqual(result["terminal"]["runner_stop_category"], StopCategory.RUNNER_MAX_PLAYER_MOVES.value)
        self.assertFalse(result["terminal"]["ale_terminated"])
        self.assertEqual(result["turns"][0]["player_move"]["uci"], "e2e3")
        self.assertTrue(result["turns"][0]["player_move"]["verified_from_rgb"])
        reply = result["turns"][0]["opponent_reply"]["uci"]
        after_player = chess.Board()
        after_player.push_uci("e2e3")
        self.assertIn(chess.Move.from_uci(reply), after_player.legal_moves)
        self.assertTrue(result["turns"][0]["opponent_reply"]["verified_from_rgb"])
        self.assertFalse(result["terminal"]["observed"])

    def test_verified_context_selector_receives_real_rgb_history_and_candidate_set(self) -> None:
        seen = []

        def selector(context):
            seen.append(context)
            self.assertTrue(context.standard_reset_verified)
            self.assertTrue(context.rgb_observation.matches_start_position())
            self.assertEqual(context.history_uci, ())
            self.assertEqual(context.fen, chess.Board().fen(en_passant="fen"))
            self.assertEqual(context.side_to_move, chess.WHITE)
            self.assertEqual(context.legal_moves_uci, tuple(sorted(move.uci() for move in chess.Board().legal_moves)))
            return DecisionResult("e2e3", {"policy_id": "test-frozen-policy", "checkpoint_sha256": "a" * 64})

        with tempfile.TemporaryDirectory(prefix="videochess-m6-selector-boundary-") as directory:
            result = run_episode(
                config=ALEConfig.deterministic_dev(mode=4),
                seed=20261129,
                decision_selector=selector,
                max_player_moves=1,
                max_opponent_wait_frames=10000,
                max_episode_frames=20000,
                max_episode_seconds=120,
                artifact_dir=directory,
            )

        self.assertEqual(len(seen), 1)
        self.assertEqual(result["selector_contract"], "verified_atari_context_v1")
        self.assertEqual(result["turns"][0]["policy_decision"]["policy_id"], "test-frozen-policy")
        self.assertTrue(result["turns"][0]["player_move"]["input_initiated"])
        self.assertTrue(result["turns"][0]["player_move"]["verified_from_rgb"])
        self.assertTrue(result["turns"][0]["opponent_reply"]["verified_from_rgb"])
        self.assertEqual(result["terminal"]["player_moves_attempted"], 1)
        self.assertEqual(result["terminal"]["verified_player_moves"], 1)

    def test_rgb_player_move_and_atari_opponent_reply_are_shadow_legal(self) -> None:
        with tempfile.TemporaryDirectory(prefix="videochess-m1-") as directory:
            result = run_closed_loop(
                config=ALEConfig.deterministic_dev(),
                seed=20261015,
                max_opponent_wait_frames=10000,
                artifact_dir=Path(directory),
            )

        self.assertTrue(result["initial_position"]["verified_from_rgb"])
        self.assertEqual(result["player_move"]["uci"], "e2e3")
        self.assertTrue(result["player_move"]["verified_from_rgb"])
        reply = chess.Move.from_uci(result["opponent_reply"]["uci"])
        after_player = chess.Board()
        after_player.push_uci("e2e3")
        self.assertIn(reply, after_player.legal_moves)
        self.assertTrue(result["opponent_reply"]["verified_from_rgb"])
        self.assertTrue(result["final_position"]["matches_shadow_board"])
        self.assertFalse(result["terminal"]["observed"])

    def test_registered_v5_defaults_also_support_a_closed_loop(self) -> None:
        with tempfile.TemporaryDirectory(prefix="videochess-m1-v5-") as directory:
            result = run_closed_loop(
                config=ALEConfig.default_v5(),
                seed=20261016,
                max_opponent_wait_frames=10000,
                artifact_dir=Path(directory),
            )

        self.assertEqual(result["config"]["frameskip"], 4)
        self.assertEqual(result["config"]["repeat_action_probability"], 0.25)
        self.assertTrue(result["player_move"]["verified_from_rgb"])
        self.assertTrue(result["opponent_reply"]["verified_from_rgb"])
        reply = chess.Move.from_uci(result["opponent_reply"]["uci"])
        after_player = chess.Board()
        after_player.push_uci("e2e3")
        self.assertIn(reply, after_player.legal_moves)
        self.assertTrue(result["final_position"]["matches_shadow_board"])

    def test_real_reset_rgb_rejects_an_unobserved_shadow_move(self) -> None:
        with VideoChessEnv(ALEConfig.deterministic_dev()) as env:
            frame = env.reset(seed=20261015)
            window = VideoChessVision().window([frame.rgb] * 33)
            shadow = ShadowBoard()
            before = shadow.board.fen()

            with self.assertRaises(DesynchronizationError):
                shadow.apply_observed_move("e2e3", window)

            self.assertEqual(shadow.board.fen(), before)


if __name__ == "__main__":
    unittest.main()
