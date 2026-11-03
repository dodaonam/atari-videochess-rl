"""Small, paired-seed reality check in the actual ALE VideoChess environment."""
from __future__ import annotations

from datetime import datetime, timezone
import argparse
import hashlib
import json
from pathlib import Path
import time

from videochess_rl.episode import run_episode
from videochess_rl.environment import ALEConfig
from .common import ARTIFACTS, ROOT, write
from .policies import ATTEMPT, EXPERIMENT, M4_SHA256, load_demo_policy

ROM_SHA256 = "d44f2a115393b0a6cbcd5398d62369e652f3670a9ee585883d183e740edad0f7"
SEEDS = (20261210, 20261211, 20261212)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def classify(trace: dict) -> str:
    term = trace.get("terminal", {})
    if not trace.get("reset", {}).get("initial_position_verified_from_rgb"):
        return "reset_or_startup_failure"
    if term.get("ale_terminated"):
        reward = float(term.get("ale_reward_total") or 0.0)
        if reward > 0: return "true_atari_win"
        if reward < 0: return "true_atari_loss"
        return "ale_terminal_zero_reward_outcome_unresolved"
    if term.get("ale_truncated"):
        return "incomplete_ale_truncation"
    cat = term.get("runner_stop_category")
    if cat == "CONTROLLER_BOARD_DESYNCHRONIZED": return "board_desynchronization"
    if cat in ("CONTROLLER_SOURCE_SELECTION_UNCERTAIN", "CONTROLLER_TARGET_NAVIGATION_UNCERTAIN",
               "CONTROLLER_TARGET_CONFIRMATION_UNCERTAIN", "POLICY_OUTPUT_ILLEGAL"):
        return "input_or_policy_control_failure"
    if cat == "ALE_TERMINATED":
        reward = float(term.get("ale_reward_total") or 0.0)
        return "true_atari_win" if reward > 0 else "true_atari_loss" if reward < 0 else "ale_terminal_zero_reward_outcome_unresolved"
    return "incomplete_bounded_attempt"


def summarize(attempts):
    by_policy = {}
    for policy in ("double-dqn", "m4-a"):
        rows = [r for r in attempts if r["policy"] == policy]
        counts = {}
        for row in rows: counts[row["category"]] = counts.get(row["category"], 0) + 1
        by_policy[policy] = {"attempts": len(rows), "categories": counts,
            "verified_player_moves": sum(r["verified_player_moves"] for r in rows),
            "verified_opponent_moves": sum(r["verified_opponent_moves"] for r in rows),
            "total_wall_seconds": sum(r["wall_seconds"] for r in rows),
            "seeds": [r["seed"] for r in rows]}
    return by_policy


PUBLIC_ATTEMPT_FIELDS = frozenset({
    "attempt_index", "policy", "policy_type", "checkpoint_sha256", "snapshot_decisions",
    "seed", "started_at_utc", "ended_at_utc", "environment", "reset_verified", "category",
    "status", "ale_terminated", "ale_truncated", "ale_reward_total", "white_result_from_reward",
    "verified_player_moves", "verified_opponent_moves", "player_moves_attempted",
    "incomplete_final_move_category", "runner_stop_category", "runner_stop_reason", "frame_number",
    "wall_seconds", "private_trace_sha256",
})


def public_attempt_metadata(attempt: dict) -> dict:
    """Allow-list aggregate fields; never serialize arbitrary trace-derived keys."""
    return {key: value for key, value in attempt.items() if key in PUBLIC_ATTEMPT_FIELDS}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--max-player-moves", type=int, default=12)
    parser.add_argument("--max-seconds-per-attempt", type=float, default=600.0)
    parser.add_argument("--output-name", default="atari-evaluation-corrected")
    args = parser.parse_args(argv)
    selection_path = ATTEMPT.parent / "simulator-development" / "selection.json"
    selection = json.loads(selection_path.read_text())
    chosen = selection["selected"]
    checkpoint = ROOT / chosen["snapshot_path"]
    checkpoint_sha = chosen["snapshot_sha256"]
    if sha256(checkpoint) != checkpoint_sha:
        raise ValueError("frozen simulator-selected Q checkpoint changed")
    plan = [("double-dqn", seed) for seed in SEEDS] + [("m4-a", seed) for seed in SEEDS]
    if not args.output_name.replace("-", "").replace("_", "").isalnum():
        parser.error("output name must contain only letters, digits, underscores, or hyphens")
    root = ARTIFACTS / "official" / args.output_name
    raw = root / "raw"
    raw.mkdir(parents=True, exist_ok=False)
    attempts = []
    started_all = datetime.now(timezone.utc).isoformat()
    for index, (name, seed) in enumerate(plan):
        # ALE resets its per-episode frame counter. The RGB adapter therefore
        # must also be fresh for each reset, while its policy weights stay fixed.
        if name == "double-dqn":
            policy, identity = load_demo_policy(name, checkpoint=checkpoint, expected_sha256=checkpoint_sha)
        else:
            policy, identity = load_demo_policy(name)
        started = datetime.now(timezone.utc).isoformat()
        tick = time.monotonic()
        trace = run_episode(config=ALEConfig.deterministic_dev(mode=4), seed=seed,
            expected_rom_sha256=ROM_SHA256, decision_selector=policy,
            max_player_moves=args.max_player_moves, max_opponent_wait_frames=30000,
            max_episode_frames=300000, max_episode_env_steps=300000,
            max_episode_seconds=args.max_seconds_per_attempt,
            max_artifact_bytes=150*1024*1024,
            artifact_dir=str(raw / f"{name}-seed{seed}-frames"))
        elapsed = time.monotonic()-tick
        raw_path = raw / f"{name}-seed{seed}.json"
        write(raw_path, trace)
        term = trace.get("terminal", {})
        attempt = {"attempt_index": index, "policy": name,
            "policy_type": identity.policy_type, "checkpoint_sha256": identity.checkpoint_sha256,
            "snapshot_decisions": identity.valid_decisions, "seed": seed,
            "started_at_utc": started, "ended_at_utc": datetime.now(timezone.utc).isoformat(),
            "environment": trace.get("runtime", {}),
            "reset_verified": trace.get("reset", {}).get("initial_position_verified_from_rgb", False),
            "category": classify(trace), "status": trace.get("status"),
            "ale_terminated": term.get("ale_terminated"), "ale_truncated": term.get("ale_truncated"),
            "ale_reward_total": term.get("ale_reward_total"), "white_result_from_reward": term.get("white_result_from_reward"),
            "verified_player_moves": term.get("verified_player_moves", 0),
            "verified_opponent_moves": term.get("verified_atari_replies", 0),
            "player_moves_attempted": term.get("player_moves_attempted", 0),
            "incomplete_final_move_category": term.get("incomplete_final_move_category"),
            "runner_stop_category": term.get("runner_stop_category"),
            "runner_stop_reason": term.get("runner_stop_reason"),
            "frame_number": term.get("frame_number"), "wall_seconds": elapsed,
            "private_trace_sha256": sha256(raw_path)}
        attempts.append(public_attempt_metadata(attempt))
        write(root / "progress.json", {"experiment_id": EXPERIMENT, "selected_q_checkpoint_sha256": checkpoint_sha,
              "selected_q_decisions": chosen["training_decisions"], "completed_attempts": attempts,
              "summary": summarize(attempts)})
    result = {"experiment_id": EXPERIMENT, "started_at_utc": started_all,
        "ended_at_utc": datetime.now(timezone.utc).isoformat(), "rom_sha256_expected": ROM_SHA256,
        "mode": 4, "frameskip": 1, "repeat_action_probability": 0.0,
        "agent_color": "white (runner contract)", "scenario_seeds": list(SEEDS),
        "attempt_cap": {"max_player_moves": args.max_player_moves,
                        "max_seconds_per_attempt": args.max_seconds_per_attempt},
        "selection_frozen_before_atari": True, "atari_results_used_for_selection": False,
        "selected_q_checkpoint": {"path": chosen["snapshot_path"], "sha256": checkpoint_sha,
                                  "training_decisions": chosen["training_decisions"]},
        "attempts": attempts, "summary": summarize(attempts),
        "limitations": ["Only White-agent runs are supported by the current Atari episode runner.",
            "The embedded ALE opponent is uncontrolled; paired seeds do not guarantee identical move sequences after policy divergence.",
            "Bounded or incomplete attempts are not wins, losses, or draws.",
            "Historical M5 Atari baseline was not included in this bounded campaign."]}
    write(root / "results.json", result)
    print(json.dumps({"attempt_count": len(attempts), "summary": result["summary"],
                      "results_path": (root / "results.json").relative_to(ROOT).as_posix()}), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
