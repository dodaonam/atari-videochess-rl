"""ALE lifecycle and configuration checks for the real VideoChess environment."""

from __future__ import annotations

import unittest

from videochess_rl.environment import ALEConfig, VideoChessEnv


class ALEConfigTests(unittest.TestCase):
    def test_profiles_keep_development_and_v5_defaults_distinct(self) -> None:
        development = ALEConfig.deterministic_dev()
        evaluation = ALEConfig.default_v5()

        self.assertEqual((development.frameskip, development.repeat_action_probability), (1, 0.0))
        self.assertEqual((evaluation.frameskip, evaluation.repeat_action_probability), (4, 0.25))
        self.assertEqual(development.env_id, "ALE/VideoChess-v5")


class ALEEnvironmentTests(unittest.TestCase):
    def test_real_ale_reset_and_step_return_rgb_and_gymnasium_flags(self) -> None:
        with VideoChessEnv(ALEConfig.deterministic_dev()) as env:
            initial = env.reset(seed=20261015)
            after_noop = env.step(0)
            runtime = env.runtime_info()

        self.assertEqual(initial.rgb.shape, (210, 160, 3))
        self.assertEqual(str(initial.rgb.dtype), "uint8")
        self.assertEqual(after_noop.frame_number - initial.frame_number, 1)
        self.assertEqual(after_noop.reward, 0.0)
        self.assertFalse(after_noop.terminated)
        self.assertFalse(after_noop.truncated)
        self.assertEqual(runtime["available_modes"], [0, 1, 2, 3, 4])
        self.assertEqual(runtime["available_difficulties"], [0])
        self.assertEqual(runtime["ram_observation_shape"], [128])
        self.assertEqual(runtime["registered_defaults"]["frameskip"], 4)
        self.assertEqual(runtime["registered_defaults"]["repeat_action_probability"], 0.25)
        self.assertEqual(runtime["instance_runtime"]["frameskip"], 1)
        self.assertEqual(runtime["instance_runtime"]["repeat_action_probability"], 0.0)
        self.assertEqual(runtime["instance_runtime"]["mode"], 0)
        self.assertEqual(runtime["instance_runtime"]["difficulty"], 0)
        self.assertEqual(runtime["instance_runtime"]["obs_type"], "rgb")
        self.assertEqual(runtime["instance_runtime"]["action_set"], list(range(10)))

    def test_supported_modes_reset_to_rgb_and_report_the_selected_mode(self) -> None:
        for mode in range(5):
            with self.subTest(mode=mode), VideoChessEnv(ALEConfig.deterministic_dev(mode=mode)) as env:
                reset = env.reset(seed=20261015 + mode)

                self.assertEqual(reset.rgb.shape, (210, 160, 3))
                self.assertEqual(env.diagnostic_ram((0xEA,))["0xEA"], mode)
                self.assertEqual(env.runtime_info()["available_difficulties"], [0])


if __name__ == "__main__":
    unittest.main()
