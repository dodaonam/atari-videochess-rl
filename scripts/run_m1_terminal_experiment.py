#!/usr/bin/env python3
"""Run one bounded M1 real-ALE terminal-feasibility episode."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import time

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from videochess_rl.demo import write_trace  # noqa: E402
from videochess_rl.environment import ALEConfig  # noqa: E402
from videochess_rl.episode import (  # noqa: E402
    choose_cooperative_loss_move,
    choose_diagnostic_move,
    StopCategory,
    run_episode,
)


def validate_output_paths(trace_path: Path) -> Path:
    """Reject existing outputs so a rerun cannot replace prior user evidence."""
    frames_path = trace_path.parent / "frames"
    for path in (trace_path, frames_path):
        if path.exists() or path.is_symlink():
            raise FileExistsError(f"Refusing to overwrite existing experiment output: {path}")
    return frames_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", choices=("deterministic-dev", "v5-default"), default="deterministic-dev")
    parser.add_argument("--mode", type=int, choices=range(5), default=0, help="ALE VideoChess skill mode 0-4.")
    parser.add_argument(
        "--policy",
        choices=("diagnostic", "cooperative-loss"),
        default="diagnostic",
        help="Use a transparent one-ply move selector or a legal Fool's Mate loss-seeking diagnostic.",
    )
    parser.add_argument("--seed", type=int, default=20261015)
    parser.add_argument("--max-player-moves", type=int, default=40)
    parser.add_argument("--max-opponent-wait-frames", type=int, default=20000)
    parser.add_argument("--max-episode-frames", type=int, default=54000)
    parser.add_argument("--max-episode-env-steps", type=int)
    parser.add_argument("--max-episode-seconds", type=float, default=900.0)
    parser.add_argument("--max-artifact-bytes", type=int, default=32 * 1024 * 1024)
    parser.add_argument(
        "--target-fire-press-frames",
        type=int,
        default=16,
        help="Hold target-confirmation FIRE for this many ALE frames (source selection remains a one-frame pulse).",
    )
    parser.add_argument(
        "--trace",
        type=Path,
        default=Path("artifacts/m1/m1-04/attempt.json"),
        help="Write the trace and selected RGB frames under the ignored artifacts directory.",
    )
    args = parser.parse_args()
    profile = ALEConfig.deterministic_dev if args.profile == "deterministic-dev" else ALEConfig.default_v5
    config = profile(mode=args.mode)
    trace_path = args.trace if args.trace.is_absolute() else REPO_ROOT / args.trace
    try:
        frames_path = validate_output_paths(trace_path)
    except FileExistsError as exc:
        parser.error(str(exc))
    experiment_started = time.monotonic()
    try:
        result = run_episode(
            config=config,
            seed=args.seed,
            move_selector=(choose_cooperative_loss_move if args.policy == "cooperative-loss" else choose_diagnostic_move),
            max_player_moves=args.max_player_moves,
            max_opponent_wait_frames=args.max_opponent_wait_frames,
            max_episode_frames=args.max_episode_frames,
            max_episode_env_steps=args.max_episode_env_steps,
            max_episode_seconds=args.max_episode_seconds,
            max_artifact_bytes=args.max_artifact_bytes,
            target_fire_press_frames=args.target_fire_press_frames,
            artifact_dir=str(frames_path),
        )
    except Exception as exc:
        reason = f"{type(exc).__name__}: {exc}"
        result = {
            "status": "partial",
            "seed": args.seed,
            "config": config.as_dict(),
            "move_selector": args.policy,
            "actions": [],
            "turns": [],
            "failure": reason,
            "terminal": {
                "observed": False,
                "ale_terminated": False,
                "ale_truncated": False,
                "ale_reward_total": 0.0,
                "runner_stopped": True,
                "runner_stop_category": StopCategory.EXCEPTION_OR_EXTERNAL_INTERRUPTION.value,
                "runner_stop_reason": reason,
                "player_moves_attempted": 0,
                "verified_player_moves": 0,
                "verified_atari_replies": 0,
                "ale_frames": 0,
                "environment_steps": 0,
                "wall_seconds": round(time.monotonic() - experiment_started, 3),
            },
        }
    write_trace(trace_path, result)
    summary = {
        "status": result.get("status"),
        "trace": trace_path.resolve().relative_to(REPO_ROOT).as_posix()
        if trace_path.resolve().is_relative_to(REPO_ROOT)
        else trace_path.name,
        "turns": [
            {
                "player_move": turn["player_move"],
                "opponent_reply": turn["opponent_reply"],
                "board_after_fen": turn.get("board_after_fen"),
            }
            for turn in result.get("turns", [])
        ],
        "terminal": result.get("terminal"),
        "terminal_observation": result.get("terminal_observation"),
        "failure": result.get("failure"),
    }
    print(json.dumps(summary, indent=2))
    return 0 if result.get("terminal", {}).get("ale_terminated") else 2


if __name__ == "__main__":
    raise SystemExit(main())
