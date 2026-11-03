"""Run a preflighted, bounded Atari VideoChess session in the local Tk viewer."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path
import json
import sys
import uuid

from .common import ARTIFACTS, write

ROM_SHA256 = "d44f2a115393b0a6cbcd5398d62369e652f3670a9ee585883d183e740edad0f7"


def allocate_session_artifact_dir(root: Path, policy: str, *, now=None, token_factory=None) -> Path:
    """Atomically allocate a unique, auditable session directory; never overwrite."""
    now = now or datetime.now(timezone.utc)
    token_factory = token_factory or (lambda: uuid.uuid4().hex[:10])
    root = Path(root)
    if any(parent.is_symlink() for parent in (root, *root.parents)):
        raise ValueError("refusing to allocate demo artifacts through a symlinked root")
    root.mkdir(parents=True, exist_ok=True)
    base = f"{now.strftime('%Y%m%dT%H%M%S.%fZ')}-{policy}"
    for collision in range(1000):
        token = token_factory()
        suffix = f"-{token}" if collision == 0 else f"-{token}-{collision:03d}"
        candidate = root / f"{base}{suffix}"
        try:
            candidate.mkdir(exist_ok=False)
            return candidate
        except FileExistsError:
            continue
    raise FileExistsError("could not allocate a unique demo artifact directory after 1000 attempts")


def run_demo_worker(viewer, *, episode_runner, episode_kwargs: dict, trace_path: Path,
                    trace_writer=write) -> None:
    """Execute one demo worker and always publish a terminal worker event."""
    worker_status = "failed"
    try:
        trace = episode_runner(**episode_kwargs)
        try:
            trace_writer(trace_path, trace)
        except Exception as exc:
            viewer.publish({"event": "trace_save_error", "error_type": type(exc).__name__,
                            "error": str(exc)})
            raise
        viewer.publish({"event": "trace_saved", "path": trace_path.name})
        worker_status = "completed"
    except Exception as exc:
        import traceback
        viewer.publish({"event": "worker_error", "error_type": type(exc).__name__,
            "error": str(exc), "traceback": traceback.format_exc()})
    finally:
        viewer.publish({"event": "worker_finished", "status": worker_status,
            "reason": None if worker_status == "completed" else "episode or trace persistence did not complete",
            "replay_available": bool(getattr(viewer, "frames", []))})


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--policy", choices=("double-dqn", "m4-a"), default="m4-a")
    parser.add_argument("--checkpoint", help="Required Q-only snapshot for --policy double-dqn")
    parser.add_argument("--checkpoint-sha256")
    parser.add_argument("--seed", "--reset-seed", dest="reset_seed", type=int, default=20261103,
                        help="Atari emulator reset seed, independent of immutable model training seed")
    parser.add_argument("--max-player-moves", type=int, default=24)
    parser.add_argument("--max-seconds", type=float, default=900.0)
    parser.add_argument("--auto-smoke", action="store_true",
                        help="Run a bounded two-move live ALE smoke, test resize/replay, and close")
    parser.add_argument("--preflight-only", action="store_true",
                        help="Check readiness without resetting or stepping Atari")
    args = parser.parse_args(argv)
    if args.auto_smoke:
        args.max_player_moves = 2
        args.max_seconds = min(args.max_seconds, 180.0)
    if args.max_player_moves < 1 or args.max_seconds <= 0:
        parser.error("move and wall-clock bounds must be positive")
    from .preflight import run_demo_preflight
    report = run_demo_preflight(policy=args.policy, checkpoint=args.checkpoint,
        expected_sha256=args.checkpoint_sha256, reset_seed=args.reset_seed,
        output_root=ARTIFACTS / "live-demo")
    print(json.dumps(report, sort_keys=True), flush=True)
    if not report["ok"]:
        return 3
    if args.preflight_only:
        return 0

    import torch
    torch.set_num_threads(1)
    from videochess_rl.episode import run_episode
    from videochess_rl.environment import ALEConfig
    from .live import LiveDemoWindow, LiveEnvironment
    from .policies import load_demo_policy
    policy, identity = load_demo_policy(args.policy, checkpoint=args.checkpoint,
        expected_sha256=args.checkpoint_sha256, policy_rng_seed=args.reset_seed)
    artifact_dir = allocate_session_artifact_dir(ARTIFACTS / "live-demo", args.policy)
    run_limits = {
        "max_player_moves": args.max_player_moves,
        "max_wall_seconds": args.max_seconds,
        "runner_frame_cap": 150000,
        "runner_environment_step_cap": 150000,
        "ale_episode_frame_cap": next((item["observed"].get("ale_episode_frame_limit")
            for item in report["checks"] if item["name"] == "videochess_environment" and item["ok"]), None),
        "opponent_response_frame_cap": 30000,
        "artifact_byte_cap": 128 * 1024 * 1024,
        "ale_truncation_is_game_terminal": False,
    }

    def worker(viewer):
        def publish_frame(frame):
            viewer.publish({"event": "frame", "frame_number": frame.frame_number,
                            "rgb": frame.rgb})
        episode_kwargs = dict(config=ALEConfig.deterministic_dev(mode=4), seed=args.reset_seed,
                expected_rom_sha256=ROM_SHA256, decision_selector=policy,
                max_player_moves=args.max_player_moves, max_opponent_wait_frames=30000,
                max_episode_frames=150000, max_episode_env_steps=150000,
                max_episode_seconds=args.max_seconds, max_artifact_bytes=128 * 1024 * 1024,
                artifact_dir=str(artifact_dir / "frames"), stop_event=viewer.stop_event,
                progress_callback=viewer.publish,
                env_factory=lambda config: LiveEnvironment(config, frame_callback=publish_frame))
        run_demo_worker(viewer, episode_runner=run_episode, episode_kwargs=episode_kwargs,
                        trace_path=artifact_dir / "trace.json")

    try:
        window = LiveDemoWindow(policy_name=identity.policy_id, identity=identity,
            artifact_dir=artifact_dir, max_player_moves=args.max_player_moves,
            run_worker=worker, demo_seed=args.reset_seed, auto_smoke=args.auto_smoke,
            session_limits=run_limits)
    except Exception as exc:
        print(f"could not initialize the live Tk window: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 5
    exit_code = window.start()
    if args.auto_smoke:
        result_path = artifact_dir / "demo-verification.json"
        if not result_path.is_file():
            print("automated smoke failed: verification record was not written", file=sys.stderr)
            return 4
        result = json.loads(result_path.read_text())
        print(json.dumps(result, sort_keys=True))
        trace_path = artifact_dir / "trace.json"
        trace = json.loads(trace_path.read_text()) if trace_path.is_file() else {}
        terminal = trace.get("terminal", {})
        smoke_valid = (result.get("window_created") and result.get("resized_1100x680")
            and result.get("layout_check", {}).get("ok")
            and result.get("replay_test", {}).get("left_moved_backward")
            and result.get("replay_test", {}).get("right_moved_forward")
            and result.get("verified_atari_turns_displayed", 0) >= 1
            and terminal.get("verified_atari_replies", 0) >= 1
            and result.get("session_state", {}).get("worker_status") == "completed")
        return 0 if smoke_valid and exit_code == 0 else (exit_code or 2)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
