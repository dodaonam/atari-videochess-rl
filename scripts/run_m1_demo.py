#!/usr/bin/env python3
"""Run a bounded real-ALE VideoChess observation/control demonstration."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from videochess_rl.demo import run_closed_loop, write_trace  # noqa: E402
from videochess_rl.environment import ALEConfig  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--profile",
        choices=("deterministic-dev", "v5-default"),
        default="deterministic-dev",
        help="Use frameskip=1/stickiness=0 for calibration, or registered v5 defaults.",
    )
    parser.add_argument("--seed", type=int, default=20261015)
    parser.add_argument("--max-opponent-wait-frames", type=int, default=10000)
    parser.add_argument(
        "--trace",
        type=Path,
        default=Path("artifacts/m1/closed-loop/trace.json"),
        help="Write the sanitized JSON trace under the ignored artifacts directory.",
    )
    args = parser.parse_args()
    config = (
        ALEConfig.deterministic_dev()
        if args.profile == "deterministic-dev"
        else ALEConfig.default_v5()
    )
    trace_path = args.trace if args.trace.is_absolute() else REPO_ROOT / args.trace
    result = run_closed_loop(
        config=config,
        seed=args.seed,
        max_opponent_wait_frames=args.max_opponent_wait_frames,
        artifact_dir=trace_path.parent / "frames",
    )
    write_trace(trace_path, result)
    summary = {
        "status": result.get("status"),
        "trace": trace_path.relative_to(REPO_ROOT).as_posix()
        if trace_path.is_relative_to(REPO_ROOT)
        else str(trace_path),
        "player_move": result.get("player_move"),
        "opponent_reply": result.get("opponent_reply"),
        "failure": result.get("failure"),
    }
    print(json.dumps(summary, indent=2))
    return 0 if result.get("status") == "complete" else 2


if __name__ == "__main__":
    raise SystemExit(main())
