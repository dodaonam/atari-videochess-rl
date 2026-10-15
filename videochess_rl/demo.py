"""Bounded observation-driven M1 closed-loop demonstration."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import struct
import subprocess
import zlib

import numpy as np

from .environment import ALEConfig


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _git_revision() -> str | None:
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
            cwd=Path(__file__).resolve().parents[1],
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def _git_state() -> dict[str, object]:
    repo = Path(__file__).resolve().parents[1]
    try:
        branch = subprocess.run(
            ["git", "branch", "--show-current"],
            check=True,
            capture_output=True,
            text=True,
            cwd=repo,
        ).stdout.strip()
        status = subprocess.run(
            ["git", "status", "--porcelain=v1", "--untracked-files=all"],
            check=True,
            capture_output=True,
            text=True,
            cwd=repo,
        ).stdout.splitlines()
        return {"branch": branch, "head": _git_revision(), "dirty_paths": status}
    except (OSError, subprocess.CalledProcessError):
        return {"branch": None, "head": None, "dirty_paths": []}


def _write_png(path: Path, rgb: np.ndarray) -> None:
    height, width, _ = rgb.shape

    def chunk(tag: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    rows = b"".join(b"\0" + row.tobytes() for row in rgb)
    png = (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(rows, 9))
        + chunk(b"IEND", b"")
    )
    path.write_bytes(png)


def run_closed_loop(
    *,
    config: ALEConfig | None = None,
    seed: int = 20261015,
    player_move: str = "e2e3",
    cursor_origin: str = "d4",
    max_opponent_wait_frames: int = 10000,
    artifact_dir: Path | None = None,
) -> dict[str, object]:
    """Preserve the one-cycle CLI contract using the multi-turn observer."""
    from .episode import run_episode

    config = config or ALEConfig.deterministic_dev()
    return run_episode(
        config=config,
        seed=seed,
        expected_reset_cursor=cursor_origin,
        move_selector=lambda board: player_move,
        max_player_moves=1,
        max_opponent_wait_frames=max_opponent_wait_frames,
        max_episode_frames=max(54000, max_opponent_wait_frames + 5000),
        max_episode_seconds=900.0,
        artifact_dir=artifact_dir.as_posix() if artifact_dir is not None else None,
    )


def write_trace(path: Path, trace: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(trace, indent=2, sort_keys=True) + "\n", encoding="utf-8")
