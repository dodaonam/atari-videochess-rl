#!/usr/bin/env python3
"""Run one bounded M1 real-ALE terminal-feasibility episode."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from videochess_rl.demo import write_trace  # noqa: E402
from videochess_rl.environment import ALEConfig  # noqa: E402
from videochess_rl.episode import choose_diagnostic_move, run_episode  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", choices=("deterministic-dev", "v5-default"), default="deterministic-dev")
    parser.add_argument("--seed", type=int, default=20261015)
    parser.add_argument("--max-player-moves", type=int, default=40)
    parser.add_argument("--max-opponent-wait-frames", type=int, default=10000)
    parser.add_argument("--max-episode-frames", type=int, default=54000)
    parser.add_argument("--max-episode-seconds", type=float, default=900.0)
    parser.add_argument("--max-artifact-bytes", type=int, default=250 * 1024 * 1024)
    parser.add_argument(
        "--trace",
        type=Path,
        default=Path("artifacts/m1/m1-04/attempt.json"),
        help="Write the trace and selected RGB frames under the ignored artifacts directory.",
    )
    args = parser.parse_args()
    config = (
        ALEConfig.deterministic_dev()
        if args.profile == "deterministic-dev"
        else ALEConfig.default_v5()
    )
    trace_path = args.trace if args.trace.is_absolute() else REPO_ROOT / args.trace
    result = run_episode(
        config=config,
        seed=args.seed,
        move_selector=choose_diagnostic_move,
        max_player_moves=args.max_player_moves,
        max_opponent_wait_frames=args.max_opponent_wait_frames,
        max_episode_frames=args.max_episode_frames,
        max_episode_seconds=args.max_episode_seconds,
        max_artifact_bytes=args.max_artifact_bytes,
        artifact_dir=str(trace_path.parent / "frames"),
    )
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
        "failure": result.get("failure"),
    }
    print(json.dumps(summary, indent=2))
    return 0 if result.get("status") == "complete" else 2


if __name__ == "__main__":
    raise SystemExit(main())
