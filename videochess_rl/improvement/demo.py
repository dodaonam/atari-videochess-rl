"""Run a real, bounded Atari VideoChess session in a resizable local Tk viewer."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path
import torch

from videochess_rl.episode import run_episode
from videochess_rl.environment import ALEConfig
from .common import ARTIFACTS, write
from .live import LiveDemoWindow, LiveEnvironment
from .policies import load_demo_policy

ROM_SHA256 = "d44f2a115393b0a6cbcd5398d62369e652f3670a9ee585883d183e740edad0f7"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--policy", choices=("double-dqn", "m4-a"), default="m4-a")
    parser.add_argument("--checkpoint", help="Required Q-only snapshot for --policy double-dqn")
    parser.add_argument("--checkpoint-sha256")
    parser.add_argument("--seed", type=int, default=20261103)
    parser.add_argument("--max-player-moves", type=int, default=24)
    parser.add_argument("--max-seconds", type=float, default=900.0)
    parser.add_argument("--auto-smoke", action="store_true",
                        help="Use a two-move live ALE smoke, test resize/replay keys, and close automatically")
    args = parser.parse_args(argv)
    if args.auto_smoke:
        args.max_player_moves = 2
        args.max_seconds = min(args.max_seconds, 180.0)
    if args.max_player_moves < 1 or args.max_seconds <= 0:
        parser.error("move and wall-clock bounds must be positive")
    torch.set_num_threads(1)
    policy, identity = load_demo_policy(args.policy, checkpoint=args.checkpoint,
                                        expected_sha256=args.checkpoint_sha256, seed=args.seed)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    artifact_dir = ARTIFACTS / "live-demo" / f"{stamp}-{args.policy}"
    artifact_dir.mkdir(parents=True, exist_ok=False)
    window = None

    def worker(viewer):
        def publish_frame(frame):
            viewer.publish({"event": "frame", "frame_number": frame.frame_number,
                            "rgb": frame.rgb})
        try:
            trace = run_episode(config=ALEConfig.deterministic_dev(mode=4), seed=args.seed,
                expected_rom_sha256=ROM_SHA256, decision_selector=policy,
                max_player_moves=args.max_player_moves, max_opponent_wait_frames=30000,
                max_episode_frames=150000, max_episode_env_steps=150000,
                max_episode_seconds=args.max_seconds, max_artifact_bytes=1024*1024*1024,
                artifact_dir=str(artifact_dir / "frames"), stop_event=viewer.stop_event,
                progress_callback=viewer.publish,
                env_factory=lambda config: LiveEnvironment(config, frame_callback=publish_frame))
            trace_path = artifact_dir / "trace.json"
            write(trace_path, trace)
            viewer.publish({"event": "trace_saved", "path": trace_path.name})
        except Exception as exc:
            viewer.publish({"event": "worker_error", "error": f"{type(exc).__name__}: {exc}"})

    window = LiveDemoWindow(policy_name=identity.policy_id, identity=identity,
                            artifact_dir=artifact_dir, max_player_moves=args.max_player_moves,
                            run_worker=worker, auto_smoke=args.auto_smoke)
    window.start()
    if args.auto_smoke:
        result = __import__("json").loads((artifact_dir / "demo-verification.json").read_text())
        trace = __import__("json").loads((artifact_dir / "trace.json").read_text())
        print(__import__("json").dumps(result, sort_keys=True))
        terminal = trace.get("terminal", {})
        return 0 if (result.get("window_created") and result.get("resized_900x560")
            and result.get("replay_test", {}).get("left_moved_backward")
            and result.get("replay_test", {}).get("right_moved_forward")
            and result.get("verified_atari_turns_displayed", 0) >= 1
            and terminal.get("verified_atari_replies", 0) >= 1) else 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
