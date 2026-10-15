"""Bounded real-ALE closed-loop check; RGB frames, not mocks, decide the result."""

from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from videochess_rl.demo import run_closed_loop
from videochess_rl.environment import ALEConfig, VideoChessEnv
from videochess_rl.shadow import DesynchronizationError, ShadowBoard
from videochess_rl.vision import VideoChessVision


class RealALEClosedLoopTests(unittest.TestCase):
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
        self.assertEqual(result["opponent_reply"]["uci"], "c7c5")
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
        self.assertEqual(result["opponent_reply"]["uci"], "c7c5")
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
