"""Low-cost M0 environment smoke checks; these do not play or reset ALE games."""

from __future__ import annotations

import shutil
import unittest


class M0EnvironmentSmokeTests(unittest.TestCase):
    def test_python_chess_generates_a_legal_opening_move(self) -> None:
        import chess

        board = chess.Board()
        move = chess.Move.from_uci("e2e4")
        self.assertIn(move, board.legal_moves)
        board.push(move)
        self.assertEqual(board.fen().split()[1], "b")

    def test_pytorch_runs_a_cpu_tensor_operation(self) -> None:
        import torch

        result = torch.tensor([2, 3], device="cpu").square().sum().item()
        self.assertEqual(result, 13)

    def test_ale_registers_videochess_v5(self) -> None:
        import ale_py
        import gymnasium as gym

        gym.register_envs(ale_py)
        spec = gym.spec("ALE/VideoChess-v5")
        self.assertEqual(spec.id, "ALE/VideoChess-v5")

    def test_ale_bundles_videochess_rom_under_snake_case_name(self) -> None:
        from ale_py.roms import get_all_rom_ids, get_rom_path

        self.assertIn("video_chess", get_all_rom_ids())
        rom_path = get_rom_path("video_chess")
        self.assertIsNotNone(rom_path)
        self.assertTrue(rom_path.is_file())

    def test_videochess_environment_constructs_without_reset(self) -> None:
        import ale_py
        import gymnasium as gym

        gym.register_envs(ale_py)
        env = gym.make("ALE/VideoChess-v5")
        try:
            self.assertEqual(env.action_space.n, 10)
            self.assertEqual(env.observation_space.shape, (210, 160, 3))
        finally:
            env.close()

    def test_stockfish_answers_uci_readiness_without_searching(self) -> None:
        import chess.engine

        executable = shutil.which("stockfish")
        self.assertIsNotNone(executable, "Stockfish must be available in the project environment PATH.")
        with chess.engine.SimpleEngine.popen_uci(executable) as engine:
            self.assertIn("Stockfish", engine.id.get("name", ""))
            engine.ping()


if __name__ == "__main__":
    unittest.main()
