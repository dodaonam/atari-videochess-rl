"""Lifecycle wrapper around the real Gymnasium ALE/VideoChess-v5 environment."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import hashlib
import platform
import sys

import numpy as np


@dataclass(frozen=True)
class ALEConfig:
    env_id: str = "ALE/VideoChess-v5"
    obs_type: str = "rgb"
    frameskip: int = 1
    repeat_action_probability: float = 0.0
    mode: int = 0
    difficulty: int = 0

    def __post_init__(self) -> None:
        if self.env_id != "ALE/VideoChess-v5" or self.obs_type != "rgb":
            raise ValueError("VideoChess experiments require ALE/VideoChess-v5 with RGB observations")
        if self.frameskip < 1:
            raise ValueError("frameskip must be a positive integer")
        if not 0.0 <= self.repeat_action_probability <= 1.0:
            raise ValueError("repeat_action_probability must be between 0 and 1")
        if self.mode not in range(5) or self.difficulty != 0:
            raise ValueError("VideoChess supports modes 0-4 and difficulty 0 in ALE-Py 0.11.2")

    @classmethod
    def deterministic_dev(cls, *, mode: int = 0) -> "ALEConfig":
        return cls(frameskip=1, repeat_action_probability=0.0, mode=mode)

    @classmethod
    def default_v5(cls, *, mode: int = 0) -> "ALEConfig":
        return cls(frameskip=4, repeat_action_probability=0.25, mode=mode)

    def as_dict(self) -> dict[str, object]:
        return {
            "env_id": self.env_id,
            "obs_type": self.obs_type,
            "frameskip": self.frameskip,
            "repeat_action_probability": self.repeat_action_probability,
            "mode": self.mode,
            "difficulty": self.difficulty,
        }


@dataclass(frozen=True)
class ALEFrame:
    rgb: np.ndarray
    reward: float
    terminated: bool
    truncated: bool
    info: dict[str, object]
    frame_number: int


class VideoChessEnv:
    """Keep ALE lifecycle and optional RAM diagnostics separate from RGB policy."""

    def __init__(self, config: ALEConfig | None = None) -> None:
        import ale_py
        import gymnasium as gym

        self.config = config or ALEConfig.deterministic_dev()
        gym.register_envs(ale_py)
        self.env = gym.make(
            self.config.env_id,
            obs_type=self.config.obs_type,
            frameskip=self.config.frameskip,
            repeat_action_probability=self.config.repeat_action_probability,
            mode=self.config.mode,
            difficulty=self.config.difficulty,
        )
        self._ale_py = ale_py
        self._gymnasium = gym
        self._closed = False

    def _frame(
        self,
        rgb: np.ndarray,
        reward: float,
        terminated: bool,
        truncated: bool,
        info: dict[str, object],
    ) -> ALEFrame:
        return ALEFrame(
            rgb=np.array(rgb, copy=True),
            reward=float(reward),
            terminated=bool(terminated),
            truncated=bool(truncated),
            info=dict(info),
            frame_number=int(self.env.unwrapped.ale.getEpisodeFrameNumber()),
        )

    def reset(self, *, seed: int | None = None) -> ALEFrame:
        rgb, info = self.env.reset(seed=seed)
        return self._frame(rgb, 0.0, False, False, info)

    def step(self, action: int) -> ALEFrame:
        rgb, reward, terminated, truncated, info = self.env.step(action)
        return self._frame(rgb, reward, terminated, truncated, info)

    def diagnostic_ram(self, addresses: tuple[int, ...]) -> dict[str, int]:
        """Read selected Atari memory-mapped bytes for diagnostics only."""
        ram = self.env.unwrapped.ale.getRAM()
        values: dict[str, int] = {}
        for address in addresses:
            if not 0x80 <= address <= 0xFF:
                raise ValueError("Atari RAM diagnostics require addresses in 0x80-0xFF")
            values[f"0x{address:02X}"] = int(ram[address - 0x80])
        return values

    def runtime_info(self) -> dict[str, object]:
        from ale_py.roms import get_rom_path

        rom_path = get_rom_path("video_chess")
        digest = hashlib.sha256(Path(rom_path).read_bytes()).hexdigest()
        ale = self.env.unwrapped.ale
        instance = self.env.unwrapped
        registered_defaults = dict(self._gymnasium.spec(self.config.env_id).kwargs)
        return {
            "python": sys.version.split()[0],
            "platform": platform.platform(),
            "machine": platform.machine(),
            "ale_py": self._ale_py.__version__,
            "gymnasium": self._gymnasium.__version__,
            "rom_name": "video_chess.bin",
            "rom_sha256": digest,
            "action_space": str(self.env.action_space),
            "action_meanings": [
                "NOOP",
                "FIRE",
                "UP",
                "RIGHT",
                "LEFT",
                "DOWN",
                "UPRIGHT",
                "UPLEFT",
                "DOWNRIGHT",
                "DOWNLEFT",
            ],
            "observation_space": str(self.env.observation_space),
            "ram_observation_shape": list(ale.getRAM().shape),
            "available_modes": [int(mode) for mode in ale.getAvailableModes()],
            "available_difficulties": [int(level) for level in ale.getAvailableDifficulties()],
            "registered_defaults": registered_defaults,
            "instance_runtime": {
                "mode": int(instance._game_mode),
                "difficulty": int(instance._game_difficulty),
                "frameskip": instance._frameskip,
                "repeat_action_probability": float(ale.getFloat("repeat_action_probability")),
                "obs_type": instance._obs_type,
                "action_set": [int(action) for action in instance._action_set],
                "observation_shape": list(self.env.observation_space.shape),
                "action_count": int(self.env.action_space.n),
            },
            "config": self.config.as_dict(),
        }

    def close(self) -> None:
        if not self._closed:
            self.env.close()
            self._closed = True

    def __enter__(self) -> "VideoChessEnv":
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        self.close()
