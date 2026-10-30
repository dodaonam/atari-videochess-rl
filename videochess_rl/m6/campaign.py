"""Serialized, resource-bounded M6 ALE diagnostics and evaluation runner."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import re
import resource
import subprocess
import sys
import time
from typing import Any, Callable

import chess

from videochess_rl.episode import run_episode
from videochess_rl.environment import ALEConfig, VideoChessEnv
from videochess_rl.m6.adapter import (
    M4_CHECKPOINT_SHA256,
    M4_ROOT_MANIFEST_SHA256,
    M4_SIDECAR_SHA256,
    M5_ROOT_MANIFEST_SHA256,
    M5_SCRATCH_CHECKPOINT_SHA256,
    M5_SCRATCH_SIDECAR_SHA256,
    M5_WARM_CHECKPOINT_SHA256,
    M5_WARM_SIDECAR_SHA256,
    M6PolicyAdapter,
    PolicyIdentity,
    load_baseline,
    load_m4_policy,
    load_m5_policy,
    sha256_file,
    verify_selected_m5_root,
)
from videochess_rl.m6.ledger import (
    HashChainLedger,
    TRACE_SCHEMA,
    build_artifact_manifest,
    classify_attempt,
    sha256_file as ledger_sha256,
    summarize_attempts,
    seal_episode_trace,
    verify_artifact_manifest,
    verify_episode_trace,
    verify_hash_chain,
    write_json_atomic,
)


CONFIG_PATH = Path(__file__).resolve().parents[2] / "configs/m6/m6-stage3-v1.json"
ROM_SHA256 = "d44f2a115393b0a6cbcd5398d62369e652f3670a9ee585883d183e740edad0f7"
M5_RUN_IDS = {
    ("warm", 20261104): "m5-e072011a58411f4ff26040013ba2e8c71212e6c83acf755337c2d7e1e01378d7__warm__attempt-0001",
    ("scratch", 20261104): "m5-e072011a58411f4ff26040013ba2e8c71212e6c83acf755337c2d7e1e01378d7__scratch__attempt-0000",
}


class ExperimentIdentityError(RuntimeError):
    """A frozen Stage 3 source, config, roster, or artifact changed."""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


def git_identity(root: Path) -> dict[str, str]:
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
    tree = subprocess.check_output(["git", "rev-parse", "HEAD^{tree}"], cwd=root, text=True).strip()
    status = subprocess.check_output(["git", "status", "--porcelain=v1", "--untracked-files=all"], cwd=root, text=True)
    if status.strip():
        raise ExperimentIdentityError("source freeze requires a clean tracked/untracked worktree")
    archive = subprocess.run(
        ["git", "archive", "--format=tar", commit], cwd=root, stdout=subprocess.PIPE, check=True
    ).stdout
    return {"git_commit": commit, "git_tree": tree, "source_bundle_sha256": hashlib.sha256(archive).hexdigest()}


def dependency_identity(root: Path) -> dict[str, Any]:
    lock = root / "uv.lock"
    packages = {}
    for name in ("gymnasium", "ale-py", "torch", "chess"):
        try:
            packages[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            packages[name] = None
    return {
        "dependency_lock_path": "uv.lock",
        "dependency_lock_sha256": sha256_file(lock),
        "python_version": sys.version.split()[0],
        "packages": packages,
    }


def profile_config(profile: str, *, mode: int = 4) -> ALEConfig:
    if profile == "development-debug":
        return ALEConfig.deterministic_dev(mode=mode)
    if profile == "ale-v5-default":
        return ALEConfig.default_v5(mode=mode)
    raise ValueError(f"unsupported M6 ALE profile: {profile}")


def stage3_schedule() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for seed in range(20261130, 20261140):
        pair = ["m5-warm-seed-20261104-post-rl", "m5-scratch-seed-20261104-post-rl"]
        if seed % 2:
            pair.reverse()
        for policy_id in pair:
            rows.append({"policy_id": policy_id, "ale_seed": seed, "game_id": f"{policy_id}-ale-seed-{seed}"})
    for policy_id in (
        "m4-behavior-only-seed-20261024",
        "simple-material-heuristic",
        "random-legal",
    ):
        for seed in range(20261130, 20261135):
            rows.append({"policy_id": policy_id, "ale_seed": seed, "game_id": f"{policy_id}-ale-seed-{seed}"})
    if len(rows) != 35 or len({row["game_id"] for row in rows}) != 35:
        raise AssertionError("frozen M6 Stage 3 schedule must contain 35 unique attempts")
    return [{**row, "slot": index} for index, row in enumerate(rows)]


def _slug(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_.-]+", "-", value).strip("-_")[:120]


def _load_m5_path(root: Path, arm: str) -> Path:
    run_id = M5_RUN_IDS[(arm, 20261104)]
    manifest = json.loads((root / "artifact-manifest.json").read_text(encoding="utf-8"))
    prefix = f"runs/{run_id}/"
    candidates = [
        row["path"] for row in manifest["files"]
        if row["path"].startswith(prefix)
        and row["path"].endswith("__stage-post_rl__decisions-050000__eval-snapshot-v2.pt")
    ]
    if len(candidates) != 1:
        raise ValueError(f"expected one selected {arm} M5 post_rl snapshot in verified manifest")
    return root / candidates[0]


def load_policy_roster(m5_root: str | Path, m4_root: str | Path) -> dict[str, tuple[Any, PolicyIdentity]]:
    m5_root_path = Path(m5_root).expanduser()
    root_manifest = verify_selected_m5_root(m5_root_path)
    if root_manifest.get("schema") != "videochess-m5-artifact-manifest/1.0":
        raise ValueError("unsupported M5 root artifact manifest")
    warm_path = _load_m5_path(m5_root_path, "warm")
    scratch_path = _load_m5_path(m5_root_path, "scratch")
    warm_policy, warm_identity = load_m5_policy(
        warm_path,
        policy_id="m5-warm-seed-20261104-post-rl",
        arm="warm",
        training_seed=20261104,
        expected_checkpoint_sha256=M5_WARM_CHECKPOINT_SHA256,
        expected_sidecar_sha256=M5_WARM_SIDECAR_SHA256,
        artifact_root=m5_root_path,
    )
    scratch_policy, scratch_identity = load_m5_policy(
        scratch_path,
        policy_id="m5-scratch-seed-20261104-post-rl",
        arm="scratch",
        training_seed=20261104,
        expected_checkpoint_sha256=M5_SCRATCH_CHECKPOINT_SHA256,
        expected_sidecar_sha256=M5_SCRATCH_SIDECAR_SHA256,
        artifact_root=m5_root_path,
    )
    m4_policy, m4_identity = load_m4_policy(m4_root)
    roster = {
        warm_identity.policy_id: (warm_policy, warm_identity),
        scratch_identity.policy_id: (scratch_policy, scratch_identity),
        m4_identity.policy_id: (m4_policy, m4_identity),
    }
    for policy_id in ("simple-material-heuristic", "random-legal"):
        roster[policy_id] = load_baseline(policy_id)
    return roster


def _runtime_snapshot(config: ALEConfig) -> dict[str, Any]:
    with VideoChessEnv(config) as env:
        return env.runtime_info()


def _run_manifest(
    root: Path,
    *,
    run_id: str,
    stage: str,
    config: ALEConfig,
    roster: dict[str, tuple[Any, PolicyIdentity]],
    seed_schedule: list[dict[str, Any]],
) -> dict[str, Any]:
    git = git_identity(root)
    dependencies = dependency_identity(root)
    runtime = _runtime_snapshot(config)
    if runtime.get("rom_sha256") != ROM_SHA256:
        raise ExperimentIdentityError("installed VideoChess ROM differs from the verified M1/M6 identity")
    if runtime.get("config") != config.as_dict():
        raise ExperimentIdentityError("constructed ALE configuration differs from the frozen profile")
    return {
        "schema": "videochess-m6-run-manifest/1.0",
        "run_id": run_id,
        "stage": stage,
        "frozen_at_utc": utc_now(),
        **git,
        **dependencies,
        "configuration_path": "configs/m6/m6-stage3-v1.json",
        "configuration_sha256": sha256_file(CONFIG_PATH),
        "runtime_construction": runtime,
        "rom_sha256": runtime["rom_sha256"],
        "environment_id": config.env_id,
        "agent_color": "white",
        "policy_roster": [identity.__dict__ if hasattr(identity, "__dict__") else {
            key: getattr(identity, key) for key in identity.__slots__
        } for _, identity in sorted(roster.values(), key=lambda row: row[1].policy_id)],
        "seed_schedule": seed_schedule,
        "attempt_limit": 35 if stage == "stage3" else len(seed_schedule),
        "budget": {
            "wall_seconds_per_game": 900 if stage == "stage3" else 900,
            "ale_frames_per_game": 54000,
            "gameplay_wall_seconds_total": 36000 if stage == "stage3" else None,
            "artifact_bytes_total": 2147483648,
            "serialized_ale_processes": 1,
            "pre_action_startup_retries": 1 if stage == "stage3" else 0,
        },
        "controller_timing": {
            "direction_hold_frames": 33,
            "source_fire_press_frames": 1,
            "target_fire_press_frames": 16,
            "release_frames": 1,
            "observation_window_frames": 66 if config.frameskip > 1 else 33,
        },
        "ale_config": config.as_dict(),
        "stockfish_in_inference": False,
        "training_or_finetuning": False,
    }


def _manifest_policy_row(identity: PolicyIdentity) -> dict[str, Any]:
    return {key: getattr(identity, key) for key in identity.__slots__}


class _TrackedEnvironment:
    """Tracks whether reset or an ALE action occurred before an exception."""

    def __init__(
        self,
        config: ALEConfig,
        state: dict[str, Any],
        on_reset: Callable[[Any], None],
        on_action: Callable[[int, Any | None, BaseException | None], None],
    ) -> None:
        state["stage"] = "constructing"
        self.inner = VideoChessEnv(config)
        self.state = state
        self.on_reset = on_reset
        self.on_action = on_action
        state["stage"] = "constructed"

    def reset(self, *, seed: int | None = None):
        self.state["stage"] = "resetting"
        frame = self.inner.reset(seed=seed)
        self.state["reset_observed"] = True
        self.state["stage"] = "reset_complete"
        self.on_reset(frame)
        return frame

    def step(self, action: int):
        self.state["action_attempted"] = True
        self.state["stage"] = "gameplay"
        self.on_action(action, None, None)
        try:
            frame = self.inner.step(action)
        except BaseException as exc:
            self.on_action(action, None, exc)
            raise
        self.on_action(action, frame, None)
        return frame

    def runtime_info(self):
        return self.inner.runtime_info()

    def diagnostic_ram(self, addresses: tuple[int, ...]):
        return self.inner.diagnostic_ram(addresses)

    def close(self):
        self.inner.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()


def _attempt_record(
    *,
    trace: dict[str, Any] | None,
    identity: PolicyIdentity,
    policy_id: str,
    game_id: str,
    attempt_id: str,
    seed: int,
    profile: str,
    trace_path: str | None,
    trace_sha256: str | None,
    attempt_manifest_path: str | None,
    attempt_manifest_sha256: str | None,
    started_at_utc: str,
    ended_at_utc: str,
    startup_state: dict[str, Any],
    startup_failure: str | None = None,
) -> dict[str, Any]:
    terminal = trace.get("terminal", {}) if trace else {}
    result = classify_attempt(trace) if trace else "incomplete"
    runtime = trace.get("runtime", {}) if trace else {}
    return {
        "schema": "videochess-m6-attempt-record/1.0",
        "run_id": trace.get("run_id") if trace else None,
        "game_id": game_id,
        "attempt_id": attempt_id,
        "policy_id": policy_id,
        "policy_type": identity.policy_type,
        "arm": identity.arm,
        "training_seed": identity.training_seed,
        "snapshot_stage": identity.snapshot_stage,
        "checkpoint_sha256": identity.checkpoint_sha256,
        "checkpoint_sidecar_sha256": identity.sidecar_sha256,
        "policy_root_artifact_manifest_sha256": identity.artifact_manifest_sha256,
        "git_commit": trace.get("git", {}).get("head") if trace else None,
        "source_bundle_sha256": trace.get("source_bundle_sha256") if trace else None,
        "dependency_lock_sha256": trace.get("dependency_lock_sha256") if trace else None,
        "python_version": runtime.get("python"),
        "gymnasium_version": runtime.get("gymnasium"),
        "ale_py_version": runtime.get("ale_py"),
        "pytorch_version": runtime.get("pytorch"),
        "python_chess_version": runtime.get("python_chess"),
        "rom_sha256": runtime.get("rom_sha256"),
        "ale_environment_id": runtime.get("config", {}).get("env_id"),
        "mode": runtime.get("config", {}).get("mode"),
        "difficulty": runtime.get("config", {}).get("difficulty"),
        "observation_type": runtime.get("config", {}).get("obs_type"),
        "action_space": runtime.get("action_space"),
        "frameskip": runtime.get("config", {}).get("frameskip"),
        "repeat_action_probability": runtime.get("config", {}).get("repeat_action_probability"),
        "controller_timing": trace.get("controller_timing") if trace else None,
        "ale_seed": seed,
        "agent_color": "white",
        "profile_id": profile,
        "start_timestamp_utc": started_at_utc,
        "end_timestamp_utc": ended_at_utc,
        "terminal_or_stop_reason": terminal.get("runner_stop_category") or startup_failure,
        "ale_reward": terminal.get("ale_reward_total"),
        "agent_reward": terminal.get("agent_reward_total"),
        "ale_terminated": terminal.get("ale_terminated", False),
        "ale_truncated": terminal.get("ale_truncated", False),
        "outcome": result,
        "verified_move_history": [move for turn in (trace or {}).get("turns", [])
                                  for move in (turn.get("player_move", {}).get("uci"), turn.get("opponent_reply", {}).get("uci"))
                                  if move and (turn.get("player_move", {}).get("verified_from_rgb") if move == turn.get("player_move", {}).get("uci") else turn.get("opponent_reply", {}).get("verified_from_rgb"))],
        "last_verified_fen": terminal.get("last_verified_fen"),
        "player_moves_attempted": _optional_int(terminal.get("player_moves_attempted", 0)),
        "rgb_verified_player_moves": _optional_int(terminal.get("verified_player_moves", 0)),
        "verified_atari_replies": _optional_int(terminal.get("verified_atari_replies", 0)),
        "desynchronization_count": (
            0 if terminal.get("unexpected_directional_displacements") is None and not startup_state.get("action_attempted")
            else None if terminal.get("unexpected_directional_displacements") is None
            else int(terminal.get("unexpected_directional_displacements", 0))
            + int(terminal.get("runner_stop_category") == "CONTROLLER_BOARD_DESYNCHRONIZED")
        ),
        "ale_frames": _optional_int(terminal.get("ale_frames", 0)),
        "environment_steps": _optional_int(terminal.get("environment_steps", 0)),
        "wall_seconds": None if terminal.get("wall_seconds") is None else float(terminal.get("wall_seconds", 0.0)),
        "peak_rss_bytes": int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024),
        "startup_state": {key: value for key, value in startup_state.items() if key in {"stage", "reset_observed", "action_attempted"}},
        "startup_failure": startup_failure,
        "trace_path": trace_path,
        "trace_sha256": trace_sha256,
        "artifact_manifest_path": attempt_manifest_path,
        "artifact_manifest_sha256": attempt_manifest_sha256,
        "retries": 0,
    }


def _optional_int(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"expected an integer or unknown value, got {value!r}")
    return value


def _exception_episode(state: dict[str, Any], *, seed: int, config: ALEConfig, reason: str) -> dict[str, Any]:
    """Retain a hashable incomplete record if run_episode unexpectedly escapes."""
    action_count = int(state.get("ale_action_attempts", 0))
    action_results = int(state.get("ale_action_results", 0))
    action_failures = int(state.get("ale_action_failures", 0))
    reset_verified = bool(state.get("reset_position_verified"))
    unknown_moves = action_count > 0
    action_result_unknown = action_count > action_results + action_failures or action_failures > 0
    return seal_episode_trace({
        "schema": "videochess-m6-episode-trace/1.0",
        "created_at_utc": utc_now(),
        "seed": seed,
        "config": config.as_dict(),
        "runtime": {},
        "reset": {
            "frame_number": state.get("reset_frame_number"),
            "rgb_shape": state.get("reset_rgb_shape"),
            "rgb_sha256": state.get("reset_rgb_sha256"),
            "rgb_artifact_path": state.get("reset_rgb_path"),
            "stable_window": reset_verified,
            "initial_position_verified_from_rgb": reset_verified,
        },
        "initial_position": {"verified_from_rgb": reset_verified, "cursor_squares": []},
        "actions": [],
        "observations": [],
        "turns": [],
        "terminal_observation": None,
        "terminal": {
            "observed": False,
            "ale_terminated": False,
            "ale_truncated": False,
            "ale_reward_total": None if action_result_unknown else 0.0,
            "agent_reward_total": None if action_result_unknown else 0.0,
            "runner_stopped": True,
            "runner_stop_category": "EXCEPTION_OR_EXTERNAL_INTERRUPTION",
            "runner_stop_reason": reason,
            "terminal_or_stop_reason": "EXCEPTION_OR_EXTERNAL_INTERRUPTION",
            "player_moves_attempted": None if unknown_moves else 0,
            "verified_player_moves": None if unknown_moves else 0,
            "verified_atari_replies": None if unknown_moves else 0,
            "unexpected_directional_displacements": None if unknown_moves else 0,
            "ale_frames": None if action_result_unknown else int(state.get("reset_frame_number") or 0),
            "environment_steps": None if action_result_unknown else action_results,
            "wall_seconds": None,
            "last_verified_fen": chess.Board().fen() if reset_verified else None,
        },
        "interruption_evidence": {
            "reason": reason,
            "ale_action_attempts": action_count,
            "ale_action_results": action_results,
            "ale_action_failures": action_failures,
            "ale_action_result_unknown": action_result_unknown,
            "move_accounting_unknown_after_action": unknown_moves,
        },
        "status": "partial",
        "failure": reason,
    })


def _trace_latency_rows(trace: dict[str, Any]) -> tuple[list[float], list[float]]:
    inference = []
    decisions = []
    for turn in trace.get("turns", []):
        policy = turn.get("policy_decision") or {}
        if isinstance(policy.get("inference_latency_seconds"), (int, float)):
            inference.append(float(policy["inference_latency_seconds"]))
        if isinstance(turn.get("decision_latency_seconds"), (int, float)):
            decisions.append(float(turn["decision_latency_seconds"]))
    return inference, decisions


def _distribution(values: list[float]) -> dict[str, float | None]:
    if not values:
        return {"count": 0, "mean": None, "median": None, "iqr": None, "p95": None, "max": None}
    ordered = sorted(values)
    def quantile(probability: float) -> float:
        index = (len(ordered) - 1) * probability
        lower = int(index)
        upper = min(lower + 1, len(ordered) - 1)
        fraction = index - lower
        return ordered[lower] * (1 - fraction) + ordered[upper] * fraction
    return {
        "count": len(ordered),
        "mean": sum(ordered) / len(ordered),
        "median": quantile(0.5),
        "iqr": quantile(0.75) - quantile(0.25),
        "p95": quantile(0.95),
        "max": max(ordered),
    }


def _records_from_events(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    started: dict[str, dict[str, Any]] = {}
    reset_ids: set[str] = set()
    finished: dict[str, dict[str, Any]] = {}
    for event in events:
        payload = event["payload"]
        attempt_id = payload.get("attempt_id")
        if event["event_type"] == "attempt_started" and isinstance(attempt_id, str):
            if attempt_id in started:
                raise ValueError(f"duplicate attempt ID in M6 ledger: {attempt_id}")
            started[attempt_id] = payload
        elif event["event_type"] == "ale_reset_observed" and isinstance(attempt_id, str):
            reset_ids.add(attempt_id)
        elif event["event_type"] == "attempt_finished" and isinstance(attempt_id, str):
            if attempt_id in finished:
                raise ValueError(f"duplicate completion event for M6 attempt {attempt_id}")
            finished[attempt_id] = payload["attempt_record"]
    rows = []
    for attempt_id, payload in started.items():
        if attempt_id in finished:
            row = finished[attempt_id]
        elif attempt_id in reset_ids:
            row = {
                "attempt_id": attempt_id,
                "game_id": payload.get("game_id"),
                "policy_id": payload.get("policy_id"),
                "outcome": "incomplete",
                "reset_observed": True,
                "player_moves_attempted": 0,
                "rgb_verified_player_moves": 0,
                "verified_atari_replies": 0,
                "desynchronization_count": 0,
                "ale_frames": 0,
                "environment_steps": 0,
                "wall_seconds": 0.0,
                "terminal_or_stop_reason": "PROCESS_INTERRUPTED_AFTER_RESET",
            }
        else:
            # Process-start failures are retained in the hash chain but do not
            # count as game attempts because ALE never completed reset.
            continue
        row["attempt_id"] = attempt_id
        row.setdefault("reset_observed", attempt_id in reset_ids)
        rows.append(row)
    return rows


def summarize_run(ledger_path: str | Path, *, run_id: str, repo_root: str | Path) -> dict[str, Any]:
    events = verify_hash_chain(ledger_path, expected_run_id=run_id)
    records = _records_from_events(events)
    root = Path(repo_root).resolve()
    reset_records = []
    for row in records:
        if not row.get("reset_observed"):
            continue
        trace_rel = row.get("trace_path")
        trace_path = root / trace_rel if isinstance(trace_rel, str) else None
        if trace_path is None or trace_path.is_symlink() or not trace_path.is_file():
            raise ValueError(f"attempt trace is missing or unsafe: {trace_rel!r}")
        if sha256_file(trace_path) != row.get("trace_sha256"):
            raise ValueError(f"attempt trace hash differs from ledger: {trace_rel}")
        trace_document = json.loads(trace_path.read_text(encoding="utf-8"))
        if trace_document.get("schema") != TRACE_SCHEMA:
            raise ValueError(f"unsupported attempt trace schema: {trace_rel}")
        trace = trace_document.get("episode")
        if not isinstance(trace, dict) or classify_attempt(trace) != row.get("outcome"):
            raise ValueError(f"ledger outcome differs from raw trace: {trace_rel}")
        verify_episode_trace(trace)
        terminal = trace.get("terminal", {})
        if terminal.get("player_moves_attempted", 0) != row.get("player_moves_attempted", 0):
            raise ValueError(f"attempted-move denominator differs from raw trace: {trace_rel}")
        if terminal.get("verified_player_moves", 0) != row.get("rgb_verified_player_moves", 0):
            raise ValueError(f"verified-move numerator differs from raw trace: {trace_rel}")
        manifest_rel = row.get("artifact_manifest_path")
        manifest_path = root / manifest_rel if isinstance(manifest_rel, str) else None
        if manifest_path is None or manifest_path.is_symlink() or not manifest_path.is_file():
            raise ValueError(f"attempt artifact manifest is missing or unsafe: {manifest_rel!r}")
        if sha256_file(manifest_path) != row.get("artifact_manifest_sha256"):
            raise ValueError(f"attempt artifact manifest hash differs from ledger: {manifest_rel}")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        actual_manifest = build_artifact_manifest(manifest_path.parent, exclude=("attempt.json", "attempt-manifest.json"))
        if actual_manifest != manifest:
            raise ValueError(f"attempt files do not match their manifest: {manifest_rel}")
        reset_records.append(row)
    by_policy = {}
    for policy_id in sorted({row["policy_id"] for row in reset_records}):
        subset = [row for row in reset_records if row["policy_id"] == policy_id]
        summary = summarize_attempts(subset)
        inference = []
        decisions = []
        for row in subset:
            path = row.get("trace_path")
            if path:
                trace_path = root / path
                if trace_path.is_file():
                    trace = json.loads(trace_path.read_text(encoding="utf-8"))["episode"]
                    inf, dec = _trace_latency_rows(trace)
                    inference.extend(inf)
                    decisions.extend(dec)
        summary["inference_latency_seconds"] = _distribution(inference)
        summary["decision_latency_seconds"] = _distribution(decisions)
        summary["per_game_records"] = subset
        by_policy[policy_id] = summary
    return {
        "schema": "videochess-m6-summary/1.0",
        "run_id": run_id,
        "ledger_path": Path(ledger_path).as_posix(),
        "ledger_sha256": sha256_file(ledger_path),
        "attempt_process_count": len(records),
        "attempted_reset_count": len(reset_records),
        "process_start_failures": sum(1 for row in records if not row.get("reset_observed")),
        "process_start_failures_by_policy": {
            policy_id: sum(1 for row in records if row.get("policy_id") == policy_id and not row.get("reset_observed"))
            for policy_id in sorted({row.get("policy_id") for row in records})
        },
        "resource_limit_stop_events": sum(1 for event in events if event["event_type"] == "resource_stop"),
        "startup_retry_events": sum(1 for event in events if event["event_type"] == "process_start_retry"),
        "by_policy": by_policy,
        "all_attempts": reset_records,
    }


class M6Campaign:
    def __init__(self, *, artifact_root: str | Path, m5_root: str | Path, m4_root: str | Path) -> None:
        self.repo_root = Path(__file__).resolve().parents[2]
        self.artifact_root = Path(artifact_root)
        self.m5_root = Path(m5_root)
        self.m4_root = Path(m4_root)
        self.artifact_root.mkdir(parents=True, exist_ok=True)
        self.roster = load_policy_roster(self.m5_root, self.m4_root)
        self.startup_retries_used = 0

    def _write_frozen_manifest(
        self, run_dir: Path, *, run_id: str, stage: str, profile: str, schedule: list[dict[str, Any]]
    ) -> tuple[dict[str, Any], ALEConfig]:
        config = profile_config(profile, mode=4)
        manifest = _run_manifest(
            self.repo_root,
            run_id=run_id,
            stage=stage,
            config=config,
            roster=self.roster,
            seed_schedule=schedule,
        )
        manifest["profile_id"] = profile
        manifest["m5_root_manifest_sha256"] = M5_ROOT_MANIFEST_SHA256
        manifest["m4_root_manifest_sha256"] = M4_ROOT_MANIFEST_SHA256
        manifest["m5_policy_selection_rule"] = "lowest predeclared paired training seed 20261104; not selected by M6 or final evaluation result"
        manifest["run_plan_sha256"] = sha256_file(CONFIG_PATH)
        write_json_atomic(run_dir / "run-manifest.json", manifest)
        return manifest, config

    def _run_one(
        self,
        *,
        ledger: HashChainLedger,
        run_id: str,
        stage: str,
        profile: str,
        config: ALEConfig,
        schedule: dict[str, Any],
        max_player_moves: int,
        max_episode_seconds: float = 900,
        attempt_id_override: str | None = None,
    ) -> dict[str, Any]:
        policy_id = schedule["policy_id"]
        game_id = schedule["game_id"]
        seed = int(schedule["ale_seed"])
        slot = int(schedule["slot"])
        attempt_id = attempt_id_override or f"{_slug(policy_id)}-seed-{seed}-slot-{slot:03d}-attempt-0000"
        game_dir = self.artifact_root / run_id / "attempts" / _slug(attempt_id)
        if game_dir.exists() or game_dir.is_symlink():
            raise FileExistsError(f"M6 game attempt path already exists: {game_dir}")
        game_dir.mkdir(parents=True, exist_ok=False)
        frames_dir = game_dir / "frames"
        state: dict[str, Any] = {"stage": "not_started", "reset_observed": False, "action_attempted": False,
                                 "ale_action_attempts": 0, "ale_action_results": 0, "ale_action_failures": 0}
        started_at = utc_now()
        identity = self.roster[policy_id][1]
        adapter = M6PolicyAdapter(self.roster[policy_id][0], identity, rng_seed=seed, agent_color=chess.WHITE)
        ledger.append("attempt_started", {
            "run_id": run_id,
            "stage": stage,
            "profile_id": profile,
            "game_id": game_id,
            "attempt_id": attempt_id,
            "policy_id": policy_id,
            "ale_seed": seed,
            "agent_color": "white",
            "attempt_index": slot,
            "gameplay_resource_ceiling_seconds": max_episode_seconds,
            "episode_wall_cap_seconds": max_episode_seconds,
            "start_timestamp_utc": started_at,
        })

        def on_reset(frame: Any) -> None:
            reset_path = game_dir / "reset.rgb"
            with reset_path.open("xb") as stream:
                stream.write(frame.rgb.tobytes())
                stream.flush()
                os.fsync(stream.fileno())
            state.update({
                "reset_rgb_path": reset_path.relative_to(self.repo_root).as_posix(),
                "reset_rgb_sha256": hashlib.sha256(frame.rgb.tobytes()).hexdigest(),
                "reset_frame_number": int(frame.frame_number),
                "reset_rgb_shape": list(frame.rgb.shape),
                "reset_position_verified": False,
            })
            try:
                from videochess_rl.vision import VideoChessVision

                observation = VideoChessVision().observe(frame.rgb)
                window = VideoChessVision().window((frame.rgb, frame.rgb, frame.rgb))
                state["reset_position_verified"] = bool(observation.matches_start_position() and window.is_stable)
            except Exception:
                # The raw reset RGB and hash remain the primary evidence.
                state["reset_position_verified"] = False
            ledger.append("ale_reset_observed", {
                "attempt_id": attempt_id,
                "game_id": game_id,
                "frame_number": int(frame.frame_number),
                "rgb_sha256": hashlib.sha256(frame.rgb.tobytes()).hexdigest(),
                "ale_seed": seed,
                "reset_confirmed": True,
                "rgb_path": state["reset_rgb_path"],
                "rgb_shape": state["reset_rgb_shape"],
                "initial_position_rgb_verified": state["reset_position_verified"],
            })

        def on_action(action: int, frame: Any | None, error: BaseException | None) -> None:
            if frame is None and error is None:
                state["ale_action_attempts"] += 1
                ledger.append("ale_action_started", {
                    "attempt_id": attempt_id,
                    "game_id": game_id,
                    "action_index": int(action),
                    "action_sequence": state["ale_action_attempts"],
                    "before_or_after_policy_decision": True,
                })
            elif error is not None:
                state["ale_action_failures"] += 1
                ledger.append("ale_action_failed", {
                    "attempt_id": attempt_id,
                    "game_id": game_id,
                    "action_index": int(action),
                    "action_sequence": state["ale_action_attempts"],
                    "error_type": type(error).__name__,
                    "error": str(error),
                })
            else:
                state["ale_action_results"] += 1
                ledger.append("ale_action_observed", {
                    "attempt_id": attempt_id,
                    "game_id": game_id,
                    "action_index": int(action),
                    "action_sequence": state["ale_action_results"],
                    "frame_number": int(frame.frame_number),
                    "rgb_sha256": hashlib.sha256(frame.rgb.tobytes()).hexdigest(),
                    "reward": float(frame.reward),
                    "terminated": bool(frame.terminated),
                    "truncated": bool(frame.truncated),
                })

        def factory(ale_config: ALEConfig) -> _TrackedEnvironment:
            return _TrackedEnvironment(ale_config, state, on_reset, on_action)

        trace: dict[str, Any] | None = None
        startup_failure: str | None = None
        try:
            trace = run_episode(
                    config=config,
                    seed=seed,
                    expected_rom_sha256=ROM_SHA256,
                    decision_selector=adapter,
                    max_player_moves=max_player_moves,
                    max_opponent_wait_frames=20_000,
                    max_episode_frames=54_000,
                    max_episode_seconds=max_episode_seconds,
                    max_artifact_bytes=max(0, 2 * 1024 * 1024 * 1024 - self._artifact_bytes() - 16 * 1024 * 1024),
                    target_fire_press_frames=16,
                    artifact_dir=str(frames_dir),
                    env_factory=factory,
            )
        except Exception as exc:
            startup_failure = f"{type(exc).__name__}: {exc}"
            if state.get("reset_observed"):
                trace = _exception_episode(state, seed=seed, config=config, reason=startup_failure)

        ended_at = utc_now()
        if trace is not None:
            trace["m6_trace_schema"] = "videochess-m6-episode-trace/1.0"
            trace["run_id"] = run_id
            trace["game_id"] = game_id
            trace["attempt_id"] = attempt_id
            trace["policy_identity"] = _manifest_policy_row(identity)
            trace["profile_id"] = profile
            source_identity = git_identity(self.repo_root)
            trace["git"] = {"head": source_identity["git_commit"], "tree": source_identity["git_tree"]}
            trace["source_commit"] = source_identity["git_commit"]
            trace["source_bundle_sha256"] = source_identity["source_bundle_sha256"]
            trace["dependency_lock_sha256"] = sha256_file(self.repo_root / "uv.lock")
            trace["runtime"]["pytorch"] = importlib.metadata.version("torch")
            trace["runtime"]["python_chess"] = importlib.metadata.version("chess")
            trace = seal_episode_trace(trace)
            trace_path = game_dir / "trace.json"
            trace_sha = write_json_atomic(trace_path, {"schema": TRACE_SCHEMA, "episode": trace})
            per_attempt_manifest = build_artifact_manifest(game_dir, exclude=("attempt.json", "attempt-manifest.json"))
            per_attempt_manifest_path = game_dir / "attempt-manifest.json"
            per_attempt_manifest_sha = write_json_atomic(per_attempt_manifest_path, per_attempt_manifest)
            relative_trace_path = trace_path.relative_to(self.repo_root).as_posix()
            relative_manifest_path = per_attempt_manifest_path.relative_to(self.repo_root).as_posix()
            record = _attempt_record(
                trace=trace,
                identity=identity,
                policy_id=policy_id,
                game_id=game_id,
                attempt_id=attempt_id,
                seed=seed,
                profile=profile,
                trace_path=relative_trace_path,
                trace_sha256=trace_sha,
                attempt_manifest_path=relative_manifest_path,
                attempt_manifest_sha256=per_attempt_manifest_sha,
                started_at_utc=started_at,
                ended_at_utc=ended_at,
                startup_state=state,
                startup_failure=startup_failure,
            )
            record.update({
                "run_id": run_id,
                "reset_observed": bool(trace.get("reset")),
                "retries": 0,
                "policy_inference_latencies_seconds": [
                    turn["policy_decision"]["inference_latency_seconds"]
                    for turn in trace.get("turns", [])
                    if isinstance(turn.get("policy_decision"), dict)
                    and isinstance(turn["policy_decision"].get("inference_latency_seconds"), (int, float))
                ],
                "decision_latencies_seconds": [
                    turn["decision_latency_seconds"] for turn in trace.get("turns", [])
                    if isinstance(turn.get("decision_latency_seconds"), (int, float))
                ],
                "stop_reason": trace.get("terminal", {}).get("runner_stop_reason"),
                "runner_stop_category": trace.get("terminal", {}).get("runner_stop_category"),
            })
        else:
            trace_path = None
            trace_sha = None
            relative_manifest_path = None
            per_attempt_manifest_sha = None
            record = _attempt_record(
                trace=None,
                identity=identity,
                policy_id=policy_id,
                game_id=game_id,
                attempt_id=attempt_id,
                seed=seed,
                profile=profile,
                trace_path=None,
                trace_sha256=None,
                attempt_manifest_path=None,
                attempt_manifest_sha256=None,
                started_at_utc=started_at,
                ended_at_utc=ended_at,
                startup_state=state,
                startup_failure=startup_failure,
            )
            record["run_id"] = run_id
            record["reset_observed"] = bool(state.get("reset_observed"))
            record["retries"] = 0
            record["runner_stop_category"] = "PROCESS_START_FAILURE"
            record["stop_reason"] = startup_failure
        write_json_atomic(game_dir / "attempt.json", record)
        ledger.append("attempt_finished", {"attempt_id": attempt_id, "game_id": game_id, "attempt_record": record})
        if trace is not None:
            reset_diagnostics = trace.get("ram_diagnostics_only", [])
            if reset_diagnostics and int(reset_diagnostics[0].get("0xEA", -1)) != int(config.mode):
                raise ExperimentIdentityError("actual reset mode byte differs from frozen numeric mode")
        return record

    def _artifact_bytes(self) -> int:
        total = 0
        for path in self.artifact_root.rglob("*"):
            if path.is_file() and not path.is_symlink():
                total += path.stat().st_size
        return total

    def _finish_pre_reset_failure(
        self, *, ledger: HashChainLedger, run_id: str, game_id: str, attempt_id: str,
        policy_id: str, seed: int, reason: str,
    ) -> None:
        record = {
            "schema": "videochess-m6-attempt-record/1.0",
            "run_id": run_id,
            "game_id": game_id,
            "attempt_id": attempt_id,
            "policy_id": policy_id,
            "profile_id": "ale-v5-default",
            "ale_seed": seed,
            "agent_color": "white",
            "reset_observed": False,
            "outcome": "incomplete",
            "terminal_or_stop_reason": "PROCESS_START_FAILURE",
            "stop_reason": reason,
            "player_moves_attempted": 0,
            "rgb_verified_player_moves": 0,
            "verified_atari_replies": 0,
            "desynchronization_count": 0,
            "ale_frames": 0,
            "environment_steps": 0,
            "wall_seconds": 0.0,
            "trace_path": None,
            "trace_sha256": None,
            "artifact_manifest_path": None,
            "artifact_manifest_sha256": None,
            "retries": 0,
        }
        attempt_dir = self.artifact_root / run_id / "attempts" / _slug(attempt_id)
        attempt_dir.mkdir(parents=True, exist_ok=True)
        attempt_path = attempt_dir / "attempt.json"
        if not attempt_path.exists():
            write_json_atomic(attempt_path, record)
        ledger.append("attempt_finished", {"attempt_id": attempt_id, "game_id": game_id, "attempt_record": record})

    def _recover_interrupted_reset(
        self,
        *,
        run_id: str,
        schedule: dict[str, Any],
        attempt_id: str,
        events: list[dict[str, Any]],
        ledger: HashChainLedger,
    ) -> dict[str, Any]:
        """Seal an explicitly incomplete trace after a process died mid-attempt."""
        started = next(
            event["payload"] for event in events
            if event["event_type"] == "attempt_started" and event["payload"].get("attempt_id") == attempt_id
        )
        reset_event = next(
            event["payload"] for event in events
            if event["event_type"] == "ale_reset_observed" and event["payload"].get("attempt_id") == attempt_id
        )
        action_events = [
            event for event in events
            if event["event_type"] in {"ale_action_started", "ale_action_observed", "ale_action_failed"}
            and event["payload"].get("attempt_id") == attempt_id
        ]
        reset_rel = reset_event.get("rgb_path")
        reset_path = self.repo_root / reset_rel if isinstance(reset_rel, str) else None
        if reset_path is None or reset_path.is_symlink() or not reset_path.is_file():
            raise ValueError(f"interrupted M6 attempt has no safe reset RGB evidence: {reset_rel!r}")
        reset_hash = sha256_file(reset_path)
        if reset_hash != reset_event.get("rgb_sha256"):
            raise ValueError("interrupted M6 attempt reset RGB hash differs from its ledger event")
        action_count = sum(event["event_type"] == "ale_action_started" for event in action_events)
        observed_count = sum(event["event_type"] == "ale_action_observed" for event in action_events)
        failed_count = sum(event["event_type"] == "ale_action_failed" for event in action_events)
        last_observed = next((event["payload"] for event in reversed(action_events)
                              if event["event_type"] == "ale_action_observed"), {})
        action_outcome_unknown = action_count > observed_count + failed_count or failed_count > 0
        unknown_moves = action_count > 0
        identity = self.roster[schedule["policy_id"]][1]
        now = utc_now()
        reward_total = sum(
            float(event["payload"].get("reward", 0.0))
            for event in action_events if event["event_type"] == "ale_action_observed"
        )
        ale_terminated = bool(last_observed.get("terminated", False)) and not action_outcome_unknown
        ale_truncated = bool(last_observed.get("truncated", False)) and not action_outcome_unknown
        terminal_reason = "ALE_TERMINATED" if ale_terminated else "ALE_TRUNCATED" if ale_truncated else "PROCESS_INTERRUPTED_AFTER_RESET"
        terminal = {
            "observed": ale_terminated or ale_truncated,
            "ale_terminated": ale_terminated,
            "ale_truncated": ale_truncated,
            "ale_reward_total": reward_total,
            "agent_reward_total": reward_total,
            "runner_stopped": not (ale_terminated or ale_truncated),
            "runner_stop_category": terminal_reason,
            "runner_stop_reason": "process exited before its full episode trace was flushed",
            "last_verified_fen": chess.Board().fen() if reset_event.get("initial_position_rgb_verified") and not unknown_moves else None,
            "player_moves_attempted": None if unknown_moves else 0,
            "verified_player_moves": None if unknown_moves else 0,
            "verified_atari_replies": None if unknown_moves else 0,
            "unexpected_directional_displacements": None if unknown_moves else 0,
            "ale_frames": None if action_outcome_unknown else int(last_observed.get("frame_number", reset_event.get("frame_number", 0))),
            "environment_steps": None if action_outcome_unknown else observed_count,
            "wall_seconds": None,
        }
        outcome = classify_attempt({"terminal": terminal})
        trace = {
            "schema": "videochess-m6-episode-trace/1.0",
            "run_id": run_id,
            "game_id": schedule["game_id"],
            "attempt_id": attempt_id,
            "policy_identity": _manifest_policy_row(identity),
            "profile_id": "ale-v5-default",
            "seed": int(schedule["ale_seed"]),
            "created_at_utc": now,
            "reset": {
                "frame_number": reset_event.get("frame_number"),
                "rgb_sha256": reset_hash,
                "rgb_artifact_path": reset_rel,
                "rgb_shape": reset_event.get("rgb_shape"),
                "stable_window": reset_event.get("initial_position_rgb_verified", False),
            },
            "initial_position": {
                "verified_from_rgb": reset_event.get("initial_position_rgb_verified", False),
                "cursor_squares": [],
            },
            "actions": [],
            "observations": [],
            "turns": [],
            "interruption_evidence": {
                "reason": "PROCESS_INTERRUPTED_AFTER_RESET",
                "attempt_started_event_sha256": next(
                    event["event_sha256"] for event in events
                    if event["event_type"] == "attempt_started" and event["payload"].get("attempt_id") == attempt_id
                ),
                "reset_event_sha256": next(
                    event["event_sha256"] for event in events
                    if event["event_type"] == "ale_reset_observed" and event["payload"].get("attempt_id") == attempt_id
                ),
                "action_event_sha256s": [event["event_sha256"] for event in action_events],
                "action_attempt_count": action_count,
                "action_observed_count": observed_count,
                "action_failed_count": failed_count,
                "action_result_unknown": action_outcome_unknown,
                "move_accounting_unknown_after_action": unknown_moves,
                "full_episode_trace_was_not_flushed": True,
            },
            "terminal": terminal,
            "status": "partial",
        }
        sealed = seal_episode_trace(trace)
        attempt_dir = self.artifact_root / run_id / "attempts" / _slug(attempt_id)
        trace_path = attempt_dir / "trace.json"
        trace_sha = write_json_atomic(trace_path, {"schema": TRACE_SCHEMA, "episode": sealed})
        manifest = build_artifact_manifest(attempt_dir, exclude=("attempt.json", "attempt-manifest.json"))
        manifest_path = attempt_dir / "attempt-manifest.json"
        manifest_sha = write_json_atomic(manifest_path, manifest)
        record = {
            "schema": "videochess-m6-attempt-record/1.0",
            "run_id": run_id,
            "game_id": schedule["game_id"],
            "attempt_id": attempt_id,
            "policy_id": identity.policy_id,
            "policy_type": identity.policy_type,
            "arm": identity.arm,
            "training_seed": identity.training_seed,
            "snapshot_stage": identity.snapshot_stage,
            "checkpoint_sha256": identity.checkpoint_sha256,
            "checkpoint_sidecar_sha256": identity.sidecar_sha256,
            "policy_root_artifact_manifest_sha256": identity.artifact_manifest_sha256,
            "ale_seed": int(schedule["ale_seed"]),
            "agent_color": "white",
            "profile_id": "ale-v5-default",
            "start_timestamp_utc": started.get("start_timestamp_utc"),
            "end_timestamp_utc": now,
            "reset_observed": True,
            "outcome": outcome,
            "terminal_or_stop_reason": terminal_reason,
            "player_moves_attempted": None if unknown_moves else 0,
            "rgb_verified_player_moves": None if unknown_moves else 0,
            "verified_atari_replies": None if unknown_moves else 0,
            "desynchronization_count": None if unknown_moves else 0,
            "ale_frames": None if action_outcome_unknown else int(last_observed.get("frame_number", reset_event.get("frame_number", 0))),
            "environment_steps": None if action_outcome_unknown else observed_count,
            "wall_seconds": None,
            "retries": 0,
            "trace_path": trace_path.relative_to(self.repo_root).as_posix(),
            "trace_sha256": trace_sha,
            "trace_integrity_status": "sealed_recovery_trace_with_explicit_missing_episode_detail",
            "artifact_manifest_path": manifest_path.relative_to(self.repo_root).as_posix(),
            "artifact_manifest_sha256": manifest_sha,
            "peak_rss_bytes": None,
        }
        attempt_path = attempt_dir / "attempt.json"
        write_json_atomic(attempt_path, record)
        ledger.append("attempt_interrupted", {
            "attempt_id": attempt_id,
            "game_id": schedule["game_id"],
            "reason": "process exited after ALE reset before completion record",
            "action_attempt_count": action_count,
            "recovery_trace_sha256": trace_sha,
        })
        ledger.append("attempt_finished", {"attempt_id": attempt_id, "game_id": schedule["game_id"], "attempt_record": record})
        return record

    def _finalize(self, run_dir: Path, *, run_id: str, ledger: HashChainLedger) -> dict[str, Any]:
        summary = summarize_run(run_dir / "events.jsonl", run_id=run_id, repo_root=self.repo_root)
        summary_path = run_dir / "summary.json"
        write_json_atomic(summary_path, summary, refuse_existing=False)
        manifest = build_artifact_manifest(run_dir)
        write_json_atomic(run_dir / "artifact-manifest.json", manifest, refuse_existing=False)
        verify_artifact_manifest(run_dir)
        return summary

    def run_diagnostics(self, *, stage: str, profile: str = "development-debug") -> dict[str, Any]:
        if stage not in {"stage1", "stage2-debug", "stage2-default"}:
            raise ValueError("diagnostic stage must be stage1, stage2-debug, or stage2-default")
        if stage == "stage1":
            policies = ["m5-warm-seed-20261104-post-rl"]
            seeds = [20261129]
            moves = 1
        elif stage == "stage2-default":
            policies = ["m5-warm-seed-20261104-post-rl", "m5-scratch-seed-20261104-post-rl"]
            seeds = [20261220, 20261221]
            moves = 1
            profile = "ale-v5-default"
        else:
            policies = [
                "m5-warm-seed-20261104-post-rl",
                "m5-scratch-seed-20261104-post-rl",
                "m4-behavior-only-seed-20261024",
                "simple-material-heuristic",
                "random-legal",
            ]
            seeds = [20261210, 20261211, 20261212, 20261213, 20261214]
            moves = 10
        schedule = []
        for index, policy_id in enumerate(policies):
            seed = seeds[index] if len(seeds) > 1 else seeds[0]
            schedule.append({"slot": index, "policy_id": policy_id, "ale_seed": seed,
                             "game_id": f"{stage}-{policy_id}-seed-{seed}"})
        run_id = f"m6-{stage}-{profile}-{git_identity(self.repo_root)['git_commit'][:12]}"
        run_dir = self.artifact_root / run_id
        run_dir.mkdir(parents=True, exist_ok=False)
        manifest, config = self._write_frozen_manifest(run_dir, run_id=run_id, stage=stage, profile=profile, schedule=schedule)
        ledger = HashChainLedger(run_dir / "events.jsonl", run_id=run_id)
        ledger.append("run_started", {"run_manifest_sha256": sha256_file(run_dir / "run-manifest.json"), "schedule": schedule})
        for item in schedule:
            self._run_one(ledger=ledger, run_id=run_id, stage=stage, profile=profile, config=config,
                          schedule=item, max_player_moves=moves)
        ledger.append("run_finished", {"stage": stage, "profile_id": profile})
        return self._finalize(run_dir, run_id=run_id, ledger=ledger)

    def run_stage3(self, *, resume: bool = False) -> dict[str, Any]:
        config_data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        if config_data.get("schema") != "videochess-m6-stage3-config/1.0":
            raise ExperimentIdentityError("Stage 3 config schema is unsupported")
        if config_data.get("paired_m5_seeds") != list(range(20261130, 20261140)):
            raise ExperimentIdentityError("paired M5 Stage 3 seed roster was changed")
        if config_data.get("baseline_seeds") != list(range(20261130, 20261135)):
            raise ExperimentIdentityError("Stage 3 baseline seed roster was changed")
        roster_counts = {row.get("policy_id"): row.get("attempts") for row in config_data.get("policy_roster", [])}
        if roster_counts != {
            "m5-warm-seed-20261104-post-rl": 10,
            "m5-scratch-seed-20261104-post-rl": 10,
            "m4-behavior-only-seed-20261024": 5,
            "simple-material-heuristic": 5,
            "random-legal": 5,
        }:
            raise ExperimentIdentityError("Stage 3 policy roster or attempt counts were changed")
        if (config_data.get("environment") != "ALE/VideoChess-v5" or config_data.get("agent_color") != "white"
                or config_data.get("mode") != 4 or config_data.get("difficulty") != 0
                or config_data.get("frameskip") != 4 or config_data.get("repeat_action_probability") != 0.25):
            raise ExperimentIdentityError("Stage 3 ALE evaluation profile was changed")
        expected_checkpoints = {
            "m5-warm-seed-20261104-post-rl": (M5_WARM_CHECKPOINT_SHA256, M5_WARM_SIDECAR_SHA256),
            "m5-scratch-seed-20261104-post-rl": (M5_SCRATCH_CHECKPOINT_SHA256, M5_SCRATCH_SIDECAR_SHA256),
            "m4-behavior-only-seed-20261024": (M4_CHECKPOINT_SHA256, M4_SIDECAR_SHA256),
        }
        for row in config_data.get("policy_roster", []):
            expected = expected_checkpoints.get(row.get("policy_id"))
            if expected is not None and (row.get("checkpoint_sha256"), row.get("sidecar_sha256")) != expected:
                raise ExperimentIdentityError(f"frozen checkpoint identity changed for {row.get('policy_id')}")
        limits = config_data.get("campaign_limits", {})
        episode_limits = config_data.get("episode_limits", {})
        if (limits.get("maximum_game_attempts") != 35
                or limits.get("maximum_gameplay_wall_seconds") != 36_000
                or limits.get("maximum_artifact_bytes") != 2 * 1024 * 1024 * 1024
                or limits.get("serialized_ale_processes") != 1
                or limits.get("maximum_pre_action_process_start_retries") != 1
                or episode_limits.get("maximum_wall_seconds") != 900
                or episode_limits.get("maximum_ale_frames") != 54_000):
            raise ExperimentIdentityError("Stage 3 resource envelope differs from the owner authorization")
        if config_data.get("m5_root_artifact_manifest_sha256") != M5_ROOT_MANIFEST_SHA256:
            raise ExperimentIdentityError("M5 root artifact manifest identity changed in the frozen config")
        if config_data.get("m4_root_artifact_manifest_sha256") != M4_ROOT_MANIFEST_SHA256:
            raise ExperimentIdentityError("M4 root artifact manifest identity changed in the frozen config")
        if config_data.get("rom_sha256") != ROM_SHA256:
            raise ExperimentIdentityError("VideoChess ROM identity changed in the frozen config")
        schedule = stage3_schedule()
        schedule_id = hashlib.sha256(canonical_schedule_bytes(schedule)).hexdigest()[:12]
        run_id = f"m6-stage3-{git_identity(self.repo_root)['git_commit'][:12]}-{schedule_id}"
        run_dir = self.artifact_root / run_id
        if not resume:
            run_dir.mkdir(parents=True, exist_ok=False)
            manifest, config = self._write_frozen_manifest(
                run_dir, run_id=run_id, stage="stage3", profile="ale-v5-default", schedule=schedule
            )
            manifest["frozen_schedule_sha256"] = hashlib.sha256(canonical_schedule_bytes(schedule)).hexdigest()
            # The schedule digest is included before the run manifest's final write;
            # this same manifest is never replaced after the first result.
            manifest_path = run_dir / "run-manifest.json"
            write_json_atomic(manifest_path, manifest, refuse_existing=False)
            ledger = HashChainLedger(run_dir / "events.jsonl", run_id=run_id)
            ledger.append("run_started", {"run_manifest_sha256": sha256_file(manifest_path), "schedule": schedule})
            completed_ids: set[str] = set()
            reset_ids: set[str] = set()
            started_ids: set[str] = set()
            finished_records: dict[str, dict[str, Any]] = {}
        else:
            if run_dir.is_symlink() or not run_dir.is_dir():
                raise FileNotFoundError("frozen Stage 3 run directory is unavailable")
            manifest_path = run_dir / "run-manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            expected_identity = git_identity(self.repo_root)
            for key, value in expected_identity.items():
                if manifest.get(key) != value:
                    raise ExperimentIdentityError(f"Stage 3 resume source identity differs for {key}")
            if manifest.get("frozen_schedule_sha256") != hashlib.sha256(canonical_schedule_bytes(schedule)).hexdigest():
                raise ExperimentIdentityError("Stage 3 resume schedule differs from the frozen manifest")
            config = profile_config("ale-v5-default", mode=4)
            ledger = HashChainLedger(run_dir / "events.jsonl", run_id=run_id, create=False)
            events = verify_hash_chain(run_dir / "events.jsonl", expected_run_id=run_id)
            started_ids = {event["payload"].get("attempt_id") for event in events if event["event_type"] == "attempt_started"}
            completed_ids = {event["payload"].get("attempt_id") for event in events if event["event_type"] == "attempt_finished"}
            reset_ids = {event["payload"].get("attempt_id") for event in events if event["event_type"] == "ale_reset_observed"}
            finished_records = {
                event["payload"].get("attempt_id"): event["payload"].get("attempt_record", {})
                for event in events if event["event_type"] == "attempt_finished"
            }
            self.startup_retries_used = sum(1 for event in events if event["event_type"] == "process_start_retry")

        gameplay_start = time.monotonic()
        finished_before = _records_from_events(verify_hash_chain(run_dir / "events.jsonl", expected_run_id=run_id))
        consumed_before = sum(
            float(row["wall_seconds"]) for row in finished_before if row.get("wall_seconds") is not None
        )

        def run_slot(
            item: dict[str, Any],
            attempt_id_override: str | None = None,
            max_episode_seconds: float = 900,
        ) -> dict[str, Any]:
            record = self._run_one(
                ledger=ledger,
                run_id=run_id,
                stage="stage3",
                profile="ale-v5-default",
                config=config,
                schedule={**item, "slot": item["slot"]},
                max_player_moves=200,
                max_episode_seconds=max_episode_seconds,
                attempt_id_override=attempt_id_override,
            )
            finished_id = record["attempt_id"]
            started_ids.add(finished_id)
            completed_ids.add(finished_id)
            finished_records[finished_id] = record
            if record.get("reset_observed"):
                reset_ids.add(finished_id)
            return record

        for item in schedule:
            policy_id = item["policy_id"]
            seed = item["ale_seed"]
            slot = item["slot"]
            attempt_id = f"{_slug(policy_id)}-seed-{seed}-slot-{slot:03d}-attempt-0000"
            retry_id = f"{attempt_id}-startup-retry-0001"
            related_ids = (attempt_id, retry_id)
            handled = False
            for candidate_id in related_ids:
                if candidate_id in reset_ids and candidate_id not in completed_ids:
                    current_events = verify_hash_chain(run_dir / "events.jsonl", expected_run_id=run_id)
                    record = self._recover_interrupted_reset(
                        run_id=run_id,
                        schedule=item,
                        attempt_id=candidate_id,
                        events=current_events,
                        ledger=ledger,
                    )
                    completed_ids.add(candidate_id)
                    finished_records[candidate_id] = record
                    handled = True
                    break
            if handled:
                continue

            if attempt_id in completed_ids:
                original = finished_records.get(attempt_id, {})
                if original.get("reset_observed"):
                    continue
                # The scheduled process failed before an ALE reset. It is
                # retained as a startup failure; the one pre-action retry, if
                # available, gets a distinct attempt identity.
                if retry_id in completed_ids or retry_id in started_ids:
                    continue
                if self.startup_retries_used >= 1:
                    continue
                remaining_seconds = 36_000 - consumed_before - (time.monotonic() - gameplay_start)
                remaining_artifact_bytes = 2 * 1024 * 1024 * 1024 - self._artifact_bytes() - 16 * 1024 * 1024
                if remaining_seconds <= 0 or remaining_artifact_bytes <= 0:
                    ledger.append("resource_stop", {
                        "reason": "10-hour gameplay or 2-GiB artifact ceiling reached before startup retry",
                        "retry_attempt_id": retry_id,
                    })
                    break
                self.startup_retries_used += 1
                ledger.append("process_start_retry", {
                    "attempt_id": attempt_id,
                    "retry_attempt_id": retry_id,
                    "game_id": item["game_id"],
                    "action_attempted": False,
                    "reason": "recovered process ended before an ALE reset",
                })
                run_slot(item, retry_id, max_episode_seconds=min(900.0, remaining_seconds))
                continue

            if attempt_id in started_ids and attempt_id not in completed_ids:
                if attempt_id in reset_ids:
                    continue
                self._finish_pre_reset_failure(
                    ledger=ledger,
                    run_id=run_id,
                    game_id=item["game_id"],
                    attempt_id=attempt_id,
                    policy_id=policy_id,
                    seed=seed,
                    reason="previous process ended before an ALE reset was recorded",
                )
                completed_ids.add(attempt_id)
                finished_records[attempt_id] = {"attempt_id": attempt_id, "reset_observed": False, "outcome": "incomplete"}
                if retry_id not in started_ids and self.startup_retries_used < 1:
                    remaining_seconds = 36_000 - consumed_before - (time.monotonic() - gameplay_start)
                    remaining_artifact_bytes = 2 * 1024 * 1024 * 1024 - self._artifact_bytes() - 16 * 1024 * 1024
                    if remaining_seconds <= 0 or remaining_artifact_bytes <= 0:
                        ledger.append("resource_stop", {
                            "reason": "10-hour gameplay or 2-GiB artifact ceiling reached before startup retry",
                            "retry_attempt_id": retry_id,
                        })
                        break
                    self.startup_retries_used += 1
                    ledger.append("process_start_retry", {
                        "attempt_id": attempt_id,
                        "retry_attempt_id": retry_id,
                        "game_id": item["game_id"],
                        "action_attempted": False,
                        "reason": "recovered process ended before an ALE reset was recorded",
                    })
                    run_slot(item, retry_id, max_episode_seconds=min(900.0, remaining_seconds))
                continue

            if consumed_before + (time.monotonic() - gameplay_start) >= 36_000:
                ledger.append("resource_stop", {"reason": "10-hour cumulative gameplay wall-time ceiling reached", "next_attempt_id": attempt_id})
                break
            remaining_seconds = 36_000 - consumed_before - (time.monotonic() - gameplay_start)
            remaining_artifact_bytes = 2 * 1024 * 1024 * 1024 - self._artifact_bytes() - 16 * 1024 * 1024
            if remaining_artifact_bytes <= 0:
                ledger.append("resource_stop", {"reason": "2-GiB M6 artifact ceiling reached before attempt reset", "next_attempt_id": attempt_id})
                break
            record = run_slot(item, max_episode_seconds=min(900.0, remaining_seconds))
            startup_state = record.get("startup_state", {})
            if (not record.get("reset_observed")
                    and record.get("runner_stop_category") == "PROCESS_START_FAILURE"
                    and not startup_state.get("action_attempted")
                    and self.startup_retries_used < 1):
                retry_remaining_seconds = 36_000 - consumed_before - (time.monotonic() - gameplay_start)
                retry_remaining_artifacts = 2 * 1024 * 1024 * 1024 - self._artifact_bytes() - 16 * 1024 * 1024
                if retry_remaining_seconds <= 0 or retry_remaining_artifacts <= 0:
                    ledger.append("resource_stop", {
                        "reason": "10-hour gameplay or 2-GiB artifact ceiling reached before startup retry",
                        "retry_attempt_id": retry_id,
                    })
                    break
                self.startup_retries_used += 1
                ledger.append("process_start_retry", {
                    "attempt_id": record["attempt_id"],
                    "retry_attempt_id": retry_id,
                    "game_id": item["game_id"],
                    "action_attempted": False,
                    "reason": record.get("stop_reason"),
                })
                run_slot(item, retry_id, max_episode_seconds=min(900.0, retry_remaining_seconds))
            if self._artifact_bytes() > 2 * 1024 * 1024 * 1024:
                ledger.append("resource_stop", {"reason": "2-GiB M6 artifact ceiling reached", "completed_attempt_id": record["attempt_id"]})
                break
        ledger.append("run_progress_checkpoint", {
            "completed_attempt_ids": sorted(completed_ids),
            "completed_reset_game_ids": sorted({
                record.get("game_id") for record in finished_records.values() if record.get("reset_observed")
            }),
            "remaining_schedule_count": 35 - len({
                record.get("game_id") for record in finished_records.values() if record.get("reset_observed")
            }),
            "run_manifest_sha256": sha256_file(run_dir / "run-manifest.json"),
        })
        return self._finalize(run_dir, run_id=run_id, ledger=ledger)


def canonical_schedule_bytes(schedule: list[dict[str, Any]]) -> bytes:
    return json.dumps(schedule, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
