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
import shutil
import subprocess
import sys
import time
import tomllib
from typing import Any, Callable

import chess

from videochess_rl.episode import TARGET_FIRE_SETTLE_WINDOWS, run_episode
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
    iter_verified_hash_chain,
    write_json_atomic,
)


CONFIG_PATH = Path(__file__).resolve().parents[2] / "configs/m6/m6-stage3-v1.json"
CONFIG_PATH_V2 = Path(__file__).resolve().parents[2] / "configs/m6/m6-stage3-v2.json"
STAGE3_V2_CONFIG_SHA256 = "663651050db80ab027b452241c7d39837ec7986927c0aefc7c7be631f459a49b"
STAGE3_V2_SCHEDULE_SHA256 = "be4e6548e6fd3e3db4605e6b55fbe860848dccb2df87d8a7122145bdabe22ffc"
ROM_SHA256 = "d44f2a115393b0a6cbcd5398d62369e652f3670a9ee585883d183e740edad0f7"
MAX_GAMEPLAY_WALL_SECONDS = 36_000
MAX_EPISODE_WALL_SECONDS = 900
MAX_M6_ARTIFACT_BYTES = 2 * 1024 * 1024 * 1024
ARTIFACT_METADATA_RESERVE_BYTES = 64 * 1024 * 1024
V2_POLICY_IDS = (
    "m5-warm-seed-20261104-post-rl",
    "m5-scratch-seed-20261104-post-rl",
)
V2_MIN_FREE_BYTES = 12 * 1024 * 1024 * 1024
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


def verify_runtime_matches_lock(root: Path) -> dict[str, Any]:
    lock_path = root / "uv.lock"
    lock_document = tomllib.loads(lock_path.read_text(encoding="utf-8"))
    installed = {
        name: importlib.metadata.version(name)
        for name in ("gymnasium", "ale-py", "torch", "chess")
    }
    locked: dict[str, set[str]] = {}
    for package in lock_document.get("package", []):
        name = package.get("name")
        version = package.get("version")
        if name in installed and isinstance(version, str):
            locked.setdefault(name, set()).add(version)
    for name, version in installed.items():
        if version not in locked.get(name, set()):
            raise ExperimentIdentityError(
                f"installed {name} version {version!r} is absent from the committed uv.lock package set"
            )
    if sys.version_info[:2] != (3, 12):
        raise ExperimentIdentityError("M6 v2 is frozen for the repository's Python 3.12 environment")
    return {
        "python": sys.version.split()[0],
        "installed_packages": installed,
        "locked_package_versions": {name: sorted(versions) for name, versions in sorted(locked.items())},
        "dependency_lock_sha256": sha256_file(lock_path),
    }


def profile_config(
    profile: str,
    *,
    mode: int = 4,
    max_num_frames_per_episode: int | None = None,
) -> ALEConfig:
    if profile == "development-debug":
        return ALEConfig.deterministic_dev(mode=mode)
    if profile in {"ale-v5-default", "ale-v5-extended-horizon"}:
        return ALEConfig(
            env_id="ALE/VideoChess-v5",
            obs_type="rgb",
            frameskip=4,
            repeat_action_probability=0.25,
            mode=mode,
            difficulty=0,
            max_num_frames_per_episode=max_num_frames_per_episode,
        )
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


def stage3_v2_schedule() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    warm = "m5-warm-seed-20261104-post-rl"
    scratch = "m5-scratch-seed-20261104-post-rl"
    for seed in range(20261130, 20261140):
        pair = [warm, scratch] if seed % 2 == 0 else [scratch, warm]
        for policy_id in pair:
            rows.append({
                "policy_id": policy_id,
                "ale_seed": seed,
                "game_id": f"{policy_id}-ale-seed-{seed}-stage3-v2",
            })
    if len(rows) != 20 or len({row["game_id"] for row in rows}) != 20:
        raise AssertionError("M6 Stage 3 v2 must contain 20 unique paired M5 attempts")
    return [{**row, "slot": index} for index, row in enumerate(rows)]


def validate_stage3_v2_config(config_data: dict[str, Any]) -> None:
    """Reject any v2 config that differs from the direct owner amendment."""
    if config_data.get("schema") != "videochess-m6-stage3-config/2.0":
        raise ExperimentIdentityError("Stage 3 v2 config schema is unsupported")
    if config_data.get("protocol_id") != "M6-Stage3-v2-extended-horizon-frozen-m5":
        raise ExperimentIdentityError("Stage 3 v2 protocol identity changed")
    expected_environment = {
        "profile_id": "ale-v5-extended-horizon",
        "environment": "ALE/VideoChess-v5",
        "rom_sha256": ROM_SHA256,
        "agent_color": "white",
        "mode": 4,
        "difficulty": 0,
        "observation_type": "rgb",
        "frameskip": 4,
        "repeat_action_probability": 0.25,
    }
    if any(config_data.get(key) != value for key, value in expected_environment.items()):
        raise ExperimentIdentityError("Stage 3 v2 ALE profile differs from the authorized profile")
    if config_data.get("m5_root_artifact_manifest_sha256") != M5_ROOT_MANIFEST_SHA256:
        raise ExperimentIdentityError("Stage 3 v2 M5 root manifest identity changed")
    if config_data.get("ale_horizon") != {
        "registered_default_max_num_frames_per_episode": 108_000,
        "max_num_frames_per_episode": 500_000,
        "runner_maximum_post_reset_action_frames": 432_000,
        "frame_counter_reset_offset_expected": 4,
    }:
        raise ExperimentIdentityError("Stage 3 v2 extended ALE horizon changed")
    roster = config_data.get("policy_roster")
    expected_roster = {
        V2_POLICY_IDS[0]: (
            "warm", 20261104, "post_rl", 50_000,
            M5_WARM_CHECKPOINT_SHA256, M5_WARM_SIDECAR_SHA256,
        ),
        V2_POLICY_IDS[1]: (
            "scratch", 20261104, "post_rl", 50_000,
            M5_SCRATCH_CHECKPOINT_SHA256, M5_SCRATCH_SIDECAR_SHA256,
        ),
    }
    actual = {
        row.get("policy_id"): (
            row.get("arm"), row.get("training_seed"), row.get("snapshot_stage"), row.get("valid_decisions"),
            row.get("checkpoint_sha256"), row.get("sidecar_sha256"), row.get("attempts"),
        )
        for row in roster if isinstance(row, dict)
    } if isinstance(roster, list) else {}
    if actual != {key: (*value, 10) for key, value in expected_roster.items()}:
        raise ExperimentIdentityError("Stage 3 v2 frozen roster or attempt counts changed")
    if config_data.get("paired_m5_seeds") != list(range(20261130, 20261140)):
        raise ExperimentIdentityError("Stage 3 v2 paired seed schedule changed")
    if config_data.get("schedule_order") != {
        "paired_policy_order": "warm first for even ALE seeds; scratch first for odd ALE seeds",
        "same_seed_use": "extended-horizon re-evaluation of the v1 paired seeds; not independent held-out evidence",
        "intermediate_outcome_selection": "none",
    }:
        raise ExperimentIdentityError("Stage 3 v2 schedule-order rule changed")
    expected_episode = {
        "maximum_player_moves": 200,
        "maximum_opponent_wait_frames": 40_000,
        "maximum_ale_frames": 432_000,
        "maximum_wall_seconds": 1_800,
    }
    if config_data.get("episode_limits") != expected_episode:
        raise ExperimentIdentityError("Stage 3 v2 per-attempt limits changed")
    expected_campaign = {
        "maximum_game_attempts": 20,
        "maximum_gameplay_wall_seconds": 43_200,
        "gameplay_wall_budget_scope": "Stage 3 v2 only; excludes historical v1 and completed M6 diagnostics",
        "maximum_artifact_bytes": 8 * 1024 * 1024 * 1024,
        "artifact_metadata_reserve_bytes": 128 * 1024 * 1024,
        "minimum_free_bytes_before_campaign": V2_MIN_FREE_BYTES,
        "maximum_process_rss_bytes": 6 * 1024 * 1024 * 1024,
        "serialized_ale_processes": 1,
        "maximum_pre_action_process_start_retries": 1,
        "retry_scope": "one global retry only for process-start failure before any ALE action; no reset attempt replacement",
    }
    if config_data.get("campaign_limits") != expected_campaign:
        raise ExperimentIdentityError("Stage 3 v2 campaign resource envelope changed")
    if config_data.get("controller_timing") != {
        "direction_hold_frames": 33,
        "source_fire_press_frames": 1,
        "target_fire_press_frames": 16,
        "release_frames": 1,
        "observation_window_frames": 66,
        "target_fire_settle_windows": TARGET_FIRE_SETTLE_WINDOWS,
    }:
        raise ExperimentIdentityError("Stage 3 v2 controller timing differs from the verified contract")
    if config_data.get("outcome_semantics") != {
        "ale_reward_perspective": "white",
        "positive_finite_terminal_reward": "white_win",
        "negative_finite_terminal_reward": "white_loss",
        "zero_terminal_reward": "terminal_unknown",
        "unsupported_or_nonfinite_reward": "terminal_unknown",
        "incomplete_or_runner_truncated_is_draw": False,
        "shadow_board_alone_can_establish_result": False,
    }:
        raise ExperimentIdentityError("Stage 3 v2 outcome rules changed")


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


def load_policy_roster(
    m5_root: str | Path,
    m4_root: str | Path | None,
    *,
    m5_only: bool = False,
) -> dict[str, tuple[Any, PolicyIdentity]]:
    if not m5_only and m4_root is None:
        raise ValueError("the Stage 3 v1 and diagnostic rosters require the accepted M4 artifact root")
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
    if m5_only:
        return {
            warm_identity.policy_id: (warm_policy, warm_identity),
            scratch_identity.policy_id: (scratch_policy, scratch_identity),
        }
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


def _campaign_budget_scope_metadata(config_data: dict[str, Any]) -> tuple[str, bool]:
    """Return the schema-bound campaign scope without inheriting another version's default."""
    schema = config_data.get("schema")
    limits = config_data.get("campaign_limits", {})
    if not isinstance(limits, dict):
        raise ExperimentIdentityError("campaign_limits must be an object")
    recorded = limits.get("gameplay_wall_budget_includes_diagnostics")

    if schema == "videochess-m6-stage3-config/2.0":
        scope = limits.get("gameplay_wall_budget_scope")
        expected = "Stage 3 v2 only; excludes historical v1 and completed M6 diagnostics"
        if scope != expected:
            raise ExperimentIdentityError("v2 campaign wall-budget scope differs from its frozen protocol")
        if recorded is not None and (not isinstance(recorded, bool) or recorded is not False):
            raise ExperimentIdentityError("v2 campaign metadata cannot include diagnostic gameplay")
        return scope, False

    if schema == "videochess-m6-stage3-config/1.0":
        scope = limits.get("gameplay_wall_budget_scope")
        expected = "all M6 ALE diagnostics plus Stage 3 evaluation attempts"
        if scope != expected:
            raise ExperimentIdentityError("v1 campaign wall-budget scope differs from its legacy protocol")
        includes_diagnostics = True if recorded is None else recorded
        if not isinstance(includes_diagnostics, bool) or includes_diagnostics is not True:
            raise ExperimentIdentityError("legacy v1 campaign budget must continue to include diagnostics")
        return scope, True

    raise ExperimentIdentityError(f"unsupported M6 campaign budget schema: {schema!r}")


def _run_manifest(
    root: Path,
    *,
    run_id: str,
    stage: str,
    config: ALEConfig,
    roster: dict[str, tuple[Any, PolicyIdentity]],
    seed_schedule: list[dict[str, Any]],
    config_path: Path = CONFIG_PATH,
) -> dict[str, Any]:
    git = git_identity(root)
    dependencies = dependency_identity(root)
    config_data = json.loads(config_path.read_text(encoding="utf-8"))
    campaign_wall_scope, campaign_wall_includes_diagnostics = _campaign_budget_scope_metadata(config_data)
    ale_horizon = config_data.get("ale_horizon", {})
    expected_ale_limit = ale_horizon.get("max_num_frames_per_episode")
    runtime_config = ALEConfig(
        env_id=config.env_id,
        obs_type=config.obs_type,
        frameskip=config.frameskip,
        repeat_action_probability=config.repeat_action_probability,
        mode=config.mode,
        difficulty=config.difficulty,
        max_num_frames_per_episode=expected_ale_limit,
    )
    runtime = _runtime_snapshot(runtime_config)
    if runtime.get("rom_sha256") != ROM_SHA256:
        raise ExperimentIdentityError("installed VideoChess ROM differs from the verified M1/M6 identity")
    if runtime.get("config") != config.as_dict():
        raise ExperimentIdentityError("constructed ALE configuration differs from the frozen profile")
    if expected_ale_limit is not None and runtime.get("ale_episode_frame_limit") != expected_ale_limit:
        raise ExperimentIdentityError("ALE emulator did not honor the frozen per-episode frame ceiling")
    return {
        "schema": "videochess-m6-run-manifest/2.0" if config_data.get("schema") == "videochess-m6-stage3-config/2.0" else "videochess-m6-run-manifest/1.0",
        "run_id": run_id,
        "stage": stage,
        "frozen_at_utc": utc_now(),
        **git,
        **dependencies,
        "configuration_path": config_path.relative_to(root).as_posix(),
        "configuration_sha256": sha256_file(config_path),
        "runtime_construction": runtime,
        "rom_sha256": runtime["rom_sha256"],
        "environment_id": config.env_id,
        "agent_color": "white",
        "policy_roster": [identity.__dict__ if hasattr(identity, "__dict__") else {
            key: getattr(identity, key) for key in identity.__slots__
        } for _, identity in sorted(roster.values(), key=lambda row: row[1].policy_id)],
        "seed_schedule": seed_schedule,
        "protocol_schema": config_data.get("schema"),
        "campaign_wall_budget_scope": campaign_wall_scope,
        "campaign_wall_budget_includes_diagnostics": campaign_wall_includes_diagnostics,
        "attempt_limit": len(seed_schedule),
        "budget": {
            "wall_seconds_per_game": config_data.get("episode_limits", {}).get("maximum_wall_seconds", MAX_EPISODE_WALL_SECONDS),
            "ale_post_reset_action_frames_per_game": config_data.get("episode_limits", {}).get("maximum_ale_frames", 54000),
            "underlying_ale_frames_per_episode": expected_ale_limit or runtime.get("ale_episode_frame_limit"),
            "opponent_response_wait_frames": config_data.get("episode_limits", {}).get("maximum_opponent_wait_frames", 20_000),
            "maximum_player_moves": config_data.get("episode_limits", {}).get("maximum_player_moves", 200),
            "gameplay_wall_seconds_total": config_data.get("campaign_limits", {}).get("maximum_gameplay_wall_seconds", MAX_GAMEPLAY_WALL_SECONDS),
            "gameplay_wall_budget_includes_diagnostics": campaign_wall_includes_diagnostics,
            "artifact_bytes_total": config_data.get("campaign_limits", {}).get("maximum_artifact_bytes", MAX_M6_ARTIFACT_BYTES),
            "artifact_metadata_reserve_bytes": config_data.get("campaign_limits", {}).get("artifact_metadata_reserve_bytes", ARTIFACT_METADATA_RESERVE_BYTES),
            "minimum_free_bytes_before_campaign": config_data.get("campaign_limits", {}).get("minimum_free_bytes_before_campaign"),
            "maximum_process_rss_bytes": config_data.get("campaign_limits", {}).get("maximum_process_rss_bytes"),
            "serialized_ale_processes": config_data.get("campaign_limits", {}).get("serialized_ale_processes", 1),
            "pre_action_startup_retries": config_data.get("campaign_limits", {}).get("maximum_pre_action_process_start_retries", 1 if stage == "stage3" else 0),
        },
        "controller_timing": {
            "direction_hold_frames": 33,
            "source_fire_press_frames": 1,
            "target_fire_press_frames": 16,
            "release_frames": 1,
            "observation_window_frames": 66 if config.frameskip > 1 else 33,
            "target_fire_settle_windows": TARGET_FIRE_SETTLE_WINDOWS,
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
    episode_budget = trace.get("episode_budget", {}) if trace else {}
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
        "ale_episode_frame_limit": runtime.get("ale_episode_frame_limit"),
        "frameskip": runtime.get("config", {}).get("frameskip"),
        "repeat_action_probability": runtime.get("config", {}).get("repeat_action_probability"),
        "runner_post_reset_action_frame_limit": episode_budget.get("max_episode_frames"),
        "episode_wall_time_limit_seconds": episode_budget.get("max_episode_seconds"),
        "maximum_player_moves": episode_budget.get("max_player_moves"),
        "maximum_opponent_wait_frames": episode_budget.get("max_opponent_wait_frames"),
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
            None if terminal.get("unexpected_directional_displacements") is None and startup_state.get("action_attempted")
            else int(terminal.get("runner_stop_category") == "CONTROLLER_BOARD_DESYNCHRONIZED")
        ),
        "unexpected_cursor_displacements": _optional_int(terminal.get("unexpected_directional_displacements", 0)),
        "cursor_diagnostics": terminal.get("cursor_diagnostics"),
        "incomplete_final_move_count": _optional_int(terminal.get("incomplete_final_move_count", 0)),
        "incomplete_final_move_category": terminal.get("incomplete_final_move_category"),
        "post_reset_action_frames": _optional_int(terminal.get("post_reset_action_frames")),
        "reset_frame_number": _optional_int(terminal.get("reset_frame_number")),
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


def _trace_latency_rows(trace: dict[str, Any]) -> tuple[list[float], list[float], list[float], list[float], list[float]]:
    choose_move = []
    validation = []
    adapter_total = []
    legacy_unclassified = []
    decisions = []
    for turn in trace.get("turns", []):
        policy = turn.get("policy_decision") or {}
        if isinstance(policy.get("policy_choose_move_latency_seconds"), (int, float)):
            choose_move.append(float(policy["policy_choose_move_latency_seconds"]))
        if isinstance(policy.get("input_validation_latency_seconds"), (int, float)):
            validation.append(float(policy["input_validation_latency_seconds"]))
        if isinstance(policy.get("adapter_total_latency_seconds"), (int, float)):
            adapter_total.append(float(policy["adapter_total_latency_seconds"]))
        if isinstance(policy.get("inference_latency_seconds"), (int, float)):
            # Preserve the historical field without claiming it measured only
            # the neural forward pass; it included context validation.
            legacy_unclassified.append(float(policy["inference_latency_seconds"]))
        if isinstance(turn.get("decision_latency_seconds"), (int, float)):
            decisions.append(float(turn["decision_latency_seconds"]))
    return choose_move, validation, adapter_total, legacy_unclassified, decisions


def _cursor_diagnostics_from_trace(trace: dict[str, Any]) -> dict[str, int | None]:
    terminal = trace.get("terminal", {})
    recorded = terminal.get("cursor_diagnostics")
    if isinstance(recorded, dict):
        return recorded
    events = trace.get("cursor_observations", [])
    unexpected_events = [event for event in events if event.get("unexpected_displacement") is True]
    return {
        "unexpected_displacements": len(unexpected_events),
        # Legacy v1 traces do not bind each displacement to a completed cursor
        # route, so correction status cannot be reconstructed safely.
        "unexpected_displacements_corrected": None,
        "unexpected_displacements_unresolved": None,
        "repeated_movement_without_progress": sum(
            event.get("movement_confirmed") is False for event in events
        ),
        # The historical trace schema did not retain these observation states.
        "ambiguous_or_unlocated_observations": None,
        "stable_board_disagreements": None,
    }


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


def _records_from_events(
    events: Any,
    *,
    event_counts: dict[str, int] | None = None,
) -> list[dict[str, Any]]:
    started: dict[str, dict[str, Any]] = {}
    reset_ids: set[str] = set()
    finished: dict[str, dict[str, Any]] = {}
    for event in events:
        if event_counts is not None:
            event_counts[event["event_type"]] = event_counts.get(event["event_type"], 0) + 1
            event_counts["event_count"] = event["sequence"]
            event_counts["last_event_sha256"] = event["event_sha256"]
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
                "unexpected_cursor_displacements": 0,
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
    event_counts: dict[str, int] = {}
    records = _records_from_events(
        iter_verified_hash_chain(ledger_path, expected_run_id=run_id),
        event_counts=event_counts,
    )
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
        # Derive board desynchronization from the raw trace outcome. Older M6
        # development summaries grouped corrected cursor-route displacements
        # into desynchronizations; preserve that ledger value alongside the
        # trace-derived board mismatch count during reanalysis.
        row["recorded_desynchronization_count"] = row.get("desynchronization_count")
        raw_cursor_displacements = terminal.get("unexpected_directional_displacements")
        row["desynchronization_count"] = (
            None if raw_cursor_displacements is None
            else int(terminal.get("runner_stop_category") == "CONTROLLER_BOARD_DESYNCHRONIZED")
        )
        row["unexpected_cursor_displacements"] = _optional_int(raw_cursor_displacements)
        row["cursor_diagnostics"] = _cursor_diagnostics_from_trace(trace)
        row["incomplete_final_move_count"] = _optional_int(terminal.get("incomplete_final_move_count"))
        row["incomplete_final_move_category"] = terminal.get("incomplete_final_move_category")
        if row["incomplete_final_move_count"] is None:
            attempted = row.get("player_moves_attempted")
            verified = row.get("rgb_verified_player_moves")
            if attempted is not None and verified is not None:
                row["incomplete_final_move_count"] = int(attempted) - int(verified)
        if row["incomplete_final_move_count"] and row["incomplete_final_move_category"] is None:
            row["incomplete_final_move_category"] = {
                "RUNNER_MAX_ALE_FRAMES": "frame_cap",
                "RUNNER_MAX_ENV_STEPS": "frame_cap",
                "RUNNER_MAX_WALL_CLOCK": "wall_clock_cap",
                "RUNNER_ARTIFACT_LIMIT": "artifact_cap",
                "RUNNER_RESOURCE_LIMIT": "other_interrupted_or_unknown",
                "ALE_TERMINATED": "ale_terminal",
                "ALE_TRUNCATED": "ale_truncation",
                "CONTROLLER_SOURCE_SELECTION_UNCERTAIN": "source_selection_uncertainty",
                "CONTROLLER_TARGET_NAVIGATION_UNCERTAIN": "target_navigation_uncertainty",
                "CONTROLLER_TARGET_CONFIRMATION_UNCERTAIN": "target_confirmation_uncertainty",
                "OPPONENT_RESPONSE_TIMEOUT": "opponent_response_timeout",
                "CONTROLLER_BOARD_DESYNCHRONIZED": "board_desynchronization",
            }.get(terminal.get("runner_stop_category"), "other_interrupted_or_unknown")
        row["post_reset_action_frames"] = _optional_int(terminal.get("post_reset_action_frames"))
        row["reset_frame_number"] = _optional_int(terminal.get("reset_frame_number"))
        if row["post_reset_action_frames"] is None:
            reset_frame = trace.get("reset", {}).get("frame_number")
            final_frame = terminal.get("ale_frames")
            if (isinstance(reset_frame, int) and not isinstance(reset_frame, bool)
                    and isinstance(final_frame, int) and not isinstance(final_frame, bool)
                    and final_frame >= reset_frame):
                row["post_reset_action_frames"] = final_frame - reset_frame
                row["reset_frame_number"] = reset_frame
                row["post_reset_action_frames_derived_from_v1_trace"] = True
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
    reset_game_ids = [row.get("game_id") for row in reset_records]
    if len(reset_game_ids) != len(set(reset_game_ids)):
        raise ValueError("duplicate M6 reset/game IDs cannot be summarized")
    by_policy = {}
    for policy_id in sorted({row["policy_id"] for row in reset_records}):
        subset = [row for row in reset_records if row["policy_id"] == policy_id]
        summary = summarize_attempts(subset)
        choose_move = []
        validation = []
        adapter_total = []
        legacy_unclassified = []
        decisions = []
        for row in subset:
            path = row.get("trace_path")
            if path:
                trace_path = root / path
                if trace_path.is_file():
                    trace = json.loads(trace_path.read_text(encoding="utf-8"))["episode"]
                    choice, valid, total, legacy, dec = _trace_latency_rows(trace)
                    choose_move.extend(choice)
                    validation.extend(valid)
                    adapter_total.extend(total)
                    legacy_unclassified.extend(legacy)
                    decisions.extend(dec)
        summary["policy_choose_move_latency_seconds"] = _distribution(choose_move)
        summary["input_validation_latency_seconds"] = _distribution(validation)
        summary["adapter_total_latency_seconds"] = _distribution(adapter_total)
        summary["legacy_unclassified_adapter_latency_seconds"] = _distribution(legacy_unclassified)
        summary["decision_latency_seconds"] = _distribution(decisions)
        summary["ale_frames_per_attempt"] = _distribution([
            float(row["ale_frames"]) for row in subset if isinstance(row.get("ale_frames"), int)
        ])
        summary["post_reset_action_frames_per_attempt"] = _distribution([
            float(row["post_reset_action_frames"])
            for row in subset if isinstance(row.get("post_reset_action_frames"), int)
        ])
        summary["environment_steps_per_attempt"] = _distribution([
            float(row["environment_steps"]) for row in subset if isinstance(row.get("environment_steps"), int)
        ])
        summary["wall_seconds_per_attempt"] = _distribution([
            float(row["wall_seconds"]) for row in subset if isinstance(row.get("wall_seconds"), (int, float))
        ])
        summary["peak_rss_bytes_per_attempt"] = _distribution([
            float(row["peak_rss_bytes"]) for row in subset if isinstance(row.get("peak_rss_bytes"), int)
        ])
        summary["per_game_records"] = subset
        by_policy[policy_id] = summary
    return {
        "schema": "videochess-m6-summary/2.0",
        "run_id": run_id,
        "ledger_path": Path(ledger_path).as_posix(),
        "ledger_sha256": sha256_file(ledger_path),
        "ledger_event_count": event_counts.get("event_count", 0),
        "ledger_head_sha256": event_counts.get("last_event_sha256"),
        "attempt_process_count": len(records),
        "attempted_reset_count": len(reset_records),
        "process_start_failures": sum(1 for row in records if not row.get("reset_observed")),
        "process_start_failures_by_policy": {
            policy_id: sum(1 for row in records if row.get("policy_id") == policy_id and not row.get("reset_observed"))
            for policy_id in sorted({row.get("policy_id") for row in records})
        },
        "resource_limit_stop_events": event_counts.get("resource_stop", 0),
        "startup_retry_events": event_counts.get("process_start_retry", 0),
        "by_policy": by_policy,
        "all_attempts": reset_records,
    }


class M6Campaign:
    def __init__(
        self,
        *,
        artifact_root: str | Path,
        m5_root: str | Path,
        m4_root: str | Path | None,
        config_path: str | Path = CONFIG_PATH,
    ) -> None:
        self.repo_root = Path(__file__).resolve().parents[2]
        requested_artifact_root = Path(artifact_root).expanduser().resolve()
        self.config_path = Path(config_path).expanduser().resolve()
        self.config_data = json.loads(self.config_path.read_text(encoding="utf-8"))
        if self.config_data.get("schema") not in {
            "videochess-m6-stage3-config/1.0", "videochess-m6-stage3-config/2.0"
        }:
            raise ExperimentIdentityError("M6 campaign configuration schema is unsupported")
        self.protocol_v2 = self.config_data.get("schema") == "videochess-m6-stage3-config/2.0"
        self.artifact_root = requested_artifact_root / "v2" if self.protocol_v2 else requested_artifact_root
        self.m5_root = Path(m5_root)
        self.m4_root = Path(m4_root) if m4_root is not None else None
        self.artifact_root.mkdir(parents=True, exist_ok=True)
        self.episode_limits = self.config_data.get("episode_limits", {})
        self.campaign_limits = self.config_data.get("campaign_limits", {})
        self.ale_horizon = self.config_data.get("ale_horizon", {}).get("max_num_frames_per_episode")
        self.roster = load_policy_roster(self.m5_root, self.m4_root, m5_only=self.protocol_v2)
        self.startup_retries_used = 0

    def _write_frozen_manifest(
        self, run_dir: Path, *, run_id: str, stage: str, profile: str, schedule: list[dict[str, Any]]
    ) -> tuple[dict[str, Any], ALEConfig]:
        config = profile_config(
            profile,
            mode=int(self.config_data.get("mode", 4)),
            max_num_frames_per_episode=self.ale_horizon,
        )
        manifest = _run_manifest(
            self.repo_root,
            run_id=run_id,
            stage=stage,
            config=config,
            roster=self.roster,
            seed_schedule=schedule,
            config_path=self.config_path,
        )
        manifest["profile_id"] = profile
        manifest["m5_root_manifest_sha256"] = M5_ROOT_MANIFEST_SHA256
        manifest["m4_root_manifest_sha256"] = None if self.protocol_v2 else M4_ROOT_MANIFEST_SHA256
        manifest["m5_policy_selection_rule"] = "lowest predeclared paired training seed 20261104; not selected by M6 or final evaluation result"
        manifest["run_plan_sha256"] = sha256_file(self.config_path)
        manifest["protocol_version"] = "v2" if self.protocol_v2 else "v1"
        manifest["max_num_frames_per_episode"] = self.ale_horizon or manifest["runtime_construction"]["ale_episode_frame_limit"]
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
                    max_opponent_wait_frames=int(self.episode_limits.get("maximum_opponent_wait_frames", 20_000)),
                    max_episode_frames=int(self.episode_limits.get("maximum_ale_frames", 54_000)),
                    max_episode_seconds=max_episode_seconds,
                    max_artifact_bytes=max(
                        1,
                        int(self.campaign_limits.get("maximum_artifact_bytes", MAX_M6_ARTIFACT_BYTES))
                        - self._artifact_bytes()
                        - int(self.campaign_limits.get("artifact_metadata_reserve_bytes", ARTIFACT_METADATA_RESERVE_BYTES)),
                    ),
                    max_process_rss_bytes=self.campaign_limits.get("maximum_process_rss_bytes"),
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
                "policy_choose_move_latencies_seconds": [
                    turn["policy_decision"]["policy_choose_move_latency_seconds"]
                    for turn in trace.get("turns", [])
                    if isinstance(turn.get("policy_decision"), dict)
                    and isinstance(turn["policy_decision"].get("policy_choose_move_latency_seconds"), (int, float))
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

    def _artifact_bytes(self, root: str | Path | None = None) -> int:
        total = 0
        search_root = Path(root) if root is not None else self.artifact_root
        if not search_root.exists():
            return 0
        for path in search_root.rglob("*"):
            if path.is_file() and not path.is_symlink():
                total += path.stat().st_size
        return total

    def _cumulative_gameplay_wall_seconds(self, *, exclude_run_id: str | None = None) -> float:
        """Sum recorded gameplay wall time; use timestamp upper bounds if a process died."""
        total = 0.0
        if not self.artifact_root.exists():
            return total
        for attempt_path in self.artifact_root.rglob("attempt.json"):
            if attempt_path.is_symlink():
                raise ValueError(f"symlink in M6 attempt records: {attempt_path}")
            if exclude_run_id is not None and attempt_path.parents[2].name == exclude_run_id:
                continue
            try:
                record = json.loads(attempt_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                raise ValueError(f"cannot account for M6 gameplay budget from {attempt_path}") from exc
            total += self._record_wall_bound_seconds(record)
        return total

    @staticmethod
    def _record_wall_bound_seconds(record: dict[str, Any]) -> float:
        wall = record.get("wall_seconds")
        if isinstance(wall, (int, float)) and not isinstance(wall, bool) and wall >= 0:
            return float(wall)
        started = record.get("start_timestamp_utc")
        ended = record.get("end_timestamp_utc")
        if isinstance(started, str) and isinstance(ended, str):
            try:
                start_dt = datetime.fromisoformat(started.replace("Z", "+00:00"))
                end_dt = datetime.fromisoformat(ended.replace("Z", "+00:00"))
            except ValueError:
                return 0.0
            if end_dt >= start_dt:
                return (end_dt - start_dt).total_seconds()
        return 0.0

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
            "profile_id": self.config_data.get("profile_id", "ale-v5-default"),
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
            "unexpected_cursor_displacements": 0,
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
        run_manifest_path = self.artifact_root / run_id / "run-manifest.json"
        if run_manifest_path.is_symlink() or not run_manifest_path.is_file():
            raise ValueError("interrupted M6 recovery requires the frozen run manifest")
        run_manifest = json.loads(run_manifest_path.read_text(encoding="utf-8"))
        runtime = dict(run_manifest.get("runtime_construction", {}))
        dependencies = dependency_identity(self.repo_root)
        runtime["pytorch"] = dependencies.get("packages", {}).get("torch")
        runtime["python_chess"] = dependencies.get("packages", {}).get("chess")
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
            "profile_id": run_manifest.get("profile_id", "ale-v5-default"),
            "seed": int(schedule["ale_seed"]),
            "created_at_utc": now,
            "git": {"head": run_manifest.get("git_commit"), "tree": run_manifest.get("git_tree")},
            "source_commit": run_manifest.get("git_commit"),
            "source_bundle_sha256": run_manifest.get("source_bundle_sha256"),
            "dependency_lock_sha256": run_manifest.get("dependency_lock_sha256"),
            "run_manifest_sha256": sha256_file(run_manifest_path),
            "rom_sha256": run_manifest.get("rom_sha256"),
            "config": run_manifest.get("ale_config"),
            "controller_timing": run_manifest.get("controller_timing"),
            "episode_budget": {
                "max_player_moves": run_manifest.get("budget", {}).get("maximum_player_moves"),
                "max_opponent_wait_frames": run_manifest.get("budget", {}).get("opponent_response_wait_frames"),
                "max_episode_frames": run_manifest.get("budget", {}).get("ale_post_reset_action_frames_per_game"),
                "max_episode_seconds": run_manifest.get("budget", {}).get("wall_seconds_per_game"),
            },
            "runtime": runtime,
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
            "git_commit": run_manifest.get("git_commit"),
            "source_bundle_sha256": run_manifest.get("source_bundle_sha256"),
            "dependency_lock_sha256": run_manifest.get("dependency_lock_sha256"),
            "python_version": runtime.get("python"),
            "gymnasium_version": runtime.get("gymnasium"),
            "ale_py_version": runtime.get("ale_py"),
            "pytorch_version": runtime.get("pytorch"),
            "python_chess_version": runtime.get("python_chess"),
            "rom_sha256": run_manifest.get("rom_sha256"),
            "ale_environment_id": run_manifest.get("environment_id"),
            "mode": run_manifest.get("ale_config", {}).get("mode"),
            "difficulty": run_manifest.get("ale_config", {}).get("difficulty"),
            "observation_type": run_manifest.get("ale_config", {}).get("obs_type"),
            "ale_episode_frame_limit": runtime.get("ale_episode_frame_limit"),
            "frameskip": run_manifest.get("ale_config", {}).get("frameskip"),
            "repeat_action_probability": run_manifest.get("ale_config", {}).get("repeat_action_probability"),
            "runner_post_reset_action_frame_limit": run_manifest.get("budget", {}).get("ale_post_reset_action_frames_per_game"),
            "episode_wall_time_limit_seconds": run_manifest.get("budget", {}).get("wall_seconds_per_game"),
            "maximum_player_moves": run_manifest.get("budget", {}).get("maximum_player_moves"),
            "maximum_opponent_wait_frames": run_manifest.get("budget", {}).get("opponent_response_wait_frames"),
            "controller_timing": run_manifest.get("controller_timing"),
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
            "unexpected_cursor_displacements": None if unknown_moves else 0,
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
        run_manifest = json.loads((run_dir / "run-manifest.json").read_text(encoding="utf-8"))
        if run_manifest.get("stage") == "stage3-v2":
            scheduled = run_manifest.get("seed_schedule", [])
            scheduled_ids = [row.get("game_id") for row in scheduled]
            if len(scheduled_ids) != 20 or len(set(scheduled_ids)) != 20:
                raise ExperimentIdentityError("frozen v2 run manifest does not contain 20 unique scheduled game IDs")
            completed_ids = {row.get("game_id") for row in summary["all_attempts"]}
            summary.update({
                "scheduled_game_count": len(scheduled_ids),
                "reset_game_count": len(completed_ids),
                "unexecuted_game_ids": [game_id for game_id in scheduled_ids if game_id not in completed_ids],
                "schedule_accounting_complete": len(completed_ids) == len(scheduled_ids),
            })
        summary_path = run_dir / "summary.json"
        write_json_atomic(summary_path, summary, refuse_existing=False)
        manifest = build_artifact_manifest(run_dir)
        write_json_atomic(run_dir / "artifact-manifest.json", manifest, refuse_existing=False)
        verify_artifact_manifest(run_dir)
        return summary

    def run_diagnostics(self, *, stage: str, profile: str = "development-debug") -> dict[str, Any]:
        if self.protocol_v2:
            raise ValueError("the Stage 3 v2 campaign does not authorize additional diagnostic runs")
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
        campaign_wall_used_before = self._cumulative_gameplay_wall_seconds(exclude_run_id=run_id)
        manifest["campaign_wall_seconds_used_before"] = campaign_wall_used_before
        manifest["campaign_wall_budget_includes_diagnostics"] = True
        manifest["artifact_bytes_used_before"] = self._artifact_bytes()
        write_json_atomic(run_dir / "run-manifest.json", manifest, refuse_existing=False)
        ledger = HashChainLedger(run_dir / "events.jsonl", run_id=run_id)
        ledger.append("run_started", {"run_manifest_sha256": sha256_file(run_dir / "run-manifest.json"), "schedule": schedule})
        gameplay_start = time.monotonic()
        for item in schedule:
            remaining_seconds = MAX_GAMEPLAY_WALL_SECONDS - campaign_wall_used_before - (time.monotonic() - gameplay_start)
            remaining_artifacts = MAX_M6_ARTIFACT_BYTES - self._artifact_bytes() - ARTIFACT_METADATA_RESERVE_BYTES
            if remaining_seconds <= 0 or remaining_artifacts <= 0:
                ledger.append("resource_stop", {
                    "reason": "10-hour cumulative gameplay or 2-GiB M6 artifact ceiling reached before diagnostic attempt",
                    "next_attempt_id": item["game_id"],
                })
                break
            self._run_one(
                ledger=ledger,
                run_id=run_id,
                stage=stage,
                profile=profile,
                config=config,
                schedule=item,
                max_player_moves=moves,
                max_episode_seconds=min(MAX_EPISODE_WALL_SECONDS, remaining_seconds),
            )
        ledger.append("run_finished", {"stage": stage, "profile_id": profile})
        return self._finalize(run_dir, run_id=run_id, ledger=ledger)

    def _run_stage3_v1(self, *, resume: bool = False) -> dict[str, Any]:
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
        if config_data.get("controller_timing", {}).get("target_fire_settle_windows") != TARGET_FIRE_SETTLE_WINDOWS:
            raise ExperimentIdentityError("target FIRE passive-settling rule differs from the frozen M6 config")
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
                or limits.get("maximum_gameplay_wall_seconds") != MAX_GAMEPLAY_WALL_SECONDS
                or limits.get("gameplay_wall_budget_scope") != "all M6 ALE diagnostics plus Stage 3 evaluation attempts"
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
            manifest["campaign_wall_seconds_used_before"] = self._cumulative_gameplay_wall_seconds(exclude_run_id=run_id)
            manifest["campaign_wall_budget_includes_diagnostics"] = True
            manifest["artifact_bytes_used_before"] = self._artifact_bytes()
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

        campaign_wall_used_before = self._cumulative_gameplay_wall_seconds(exclude_run_id=run_id)
        gameplay_start = time.monotonic()
        finished_before = _records_from_events(verify_hash_chain(run_dir / "events.jsonl", expected_run_id=run_id))
        consumed_before = sum(self._record_wall_bound_seconds(row) for row in finished_before)

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
                remaining_seconds = MAX_GAMEPLAY_WALL_SECONDS - campaign_wall_used_before - consumed_before - (time.monotonic() - gameplay_start)
                remaining_artifact_bytes = MAX_M6_ARTIFACT_BYTES - self._artifact_bytes() - ARTIFACT_METADATA_RESERVE_BYTES
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
                run_slot(item, retry_id, max_episode_seconds=min(MAX_EPISODE_WALL_SECONDS, remaining_seconds))
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
                    remaining_seconds = MAX_GAMEPLAY_WALL_SECONDS - campaign_wall_used_before - consumed_before - (time.monotonic() - gameplay_start)
                    remaining_artifact_bytes = MAX_M6_ARTIFACT_BYTES - self._artifact_bytes() - ARTIFACT_METADATA_RESERVE_BYTES
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
                    run_slot(item, retry_id, max_episode_seconds=min(MAX_EPISODE_WALL_SECONDS, remaining_seconds))
                continue

            if campaign_wall_used_before + consumed_before + (time.monotonic() - gameplay_start) >= MAX_GAMEPLAY_WALL_SECONDS:
                ledger.append("resource_stop", {"reason": "10-hour cumulative gameplay wall-time ceiling reached", "next_attempt_id": attempt_id})
                break
            remaining_seconds = MAX_GAMEPLAY_WALL_SECONDS - campaign_wall_used_before - consumed_before - (time.monotonic() - gameplay_start)
            remaining_artifact_bytes = MAX_M6_ARTIFACT_BYTES - self._artifact_bytes() - ARTIFACT_METADATA_RESERVE_BYTES
            if remaining_artifact_bytes <= 0:
                ledger.append("resource_stop", {"reason": "2-GiB M6 artifact ceiling reached before attempt reset", "next_attempt_id": attempt_id})
                break
            record = run_slot(item, max_episode_seconds=min(MAX_EPISODE_WALL_SECONDS, remaining_seconds))
            startup_state = record.get("startup_state", {})
            if (not record.get("reset_observed")
                    and record.get("runner_stop_category") == "PROCESS_START_FAILURE"
                    and not startup_state.get("action_attempted")
                    and self.startup_retries_used < 1):
                retry_remaining_seconds = MAX_GAMEPLAY_WALL_SECONDS - campaign_wall_used_before - consumed_before - (time.monotonic() - gameplay_start)
                retry_remaining_artifacts = MAX_M6_ARTIFACT_BYTES - self._artifact_bytes() - ARTIFACT_METADATA_RESERVE_BYTES
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
                run_slot(item, retry_id, max_episode_seconds=min(MAX_EPISODE_WALL_SECONDS, retry_remaining_seconds))
            if self._artifact_bytes() > MAX_M6_ARTIFACT_BYTES:
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

    def run_stage3(self, *, resume: bool = False) -> dict[str, Any]:
        if self.protocol_v2:
            return self._run_stage3_v2(resume=resume)
        return self._run_stage3_v1(resume=resume)

    def _run_stage3_v2(self, *, resume: bool = False) -> dict[str, Any]:
        config_data = self.config_data
        validate_stage3_v2_config(config_data)
        if self.config_path != CONFIG_PATH_V2:
            raise ExperimentIdentityError("v2 execution requires the canonical versioned v2 configuration path")
        schedule = stage3_v2_schedule()
        expected_schedule_sha = hashlib.sha256(canonical_schedule_bytes(schedule)).hexdigest()
        config_sha = sha256_file(self.config_path)
        if config_sha != STAGE3_V2_CONFIG_SHA256 or expected_schedule_sha != STAGE3_V2_SCHEDULE_SHA256:
            raise ExperimentIdentityError("Stage 3 v2 config or schedule hash differs from the owner-authorized freeze")
        source = git_identity(self.repo_root)
        identity_bytes = json.dumps(
            {
                "source_commit": source["git_commit"],
                "source_tree": source["git_tree"],
                "configuration_sha256": config_sha,
                "schedule_sha256": expected_schedule_sha,
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        run_digest = hashlib.sha256(identity_bytes).hexdigest()
        run_id = f"m6-stage3-v2-{source['git_commit'][:12]}-{run_digest[:12]}"
        run_dir = self.artifact_root / run_id
        expected_runtime_config = profile_config(
            "ale-v5-extended-horizon",
            mode=4,
            max_num_frames_per_episode=500_000,
        )
        locked_runtime_identity = verify_runtime_matches_lock(self.repo_root)

        free_bytes = shutil.disk_usage(self.artifact_root).free
        minimum_free = int(self.campaign_limits["minimum_free_bytes_before_campaign"])
        if free_bytes < minimum_free:
            raise ExperimentIdentityError(
                f"v2 campaign requires {minimum_free} free bytes before starting; observed {free_bytes}"
            )

        if not resume:
            if run_dir.exists() or run_dir.is_symlink():
                raise FileExistsError(f"refusing to reuse the deterministic v2 run identity: {run_dir}")
            artifact_bytes_before = self._artifact_bytes()
            wall_seconds_before = self._cumulative_gameplay_wall_seconds()
            run_dir.mkdir(parents=True, exist_ok=False)
            manifest, config = self._write_frozen_manifest(
                run_dir,
                run_id=run_id,
                stage="stage3-v2",
                profile="ale-v5-extended-horizon",
                schedule=schedule,
            )
            if config != expected_runtime_config:
                raise ExperimentIdentityError("v2 runner profile differs from the frozen extended-horizon config")
            runtime = manifest["runtime_construction"]
            if runtime.get("ale_episode_frame_limit") != 500_000:
                raise ExperimentIdentityError("constructed ALE did not retain the requested 500,000-frame horizon")
            manifest.update({
                "protocol_id": config_data["protocol_id"],
                "protocol_version": "v2",
                "run_id_derivation": "SHA-256 of canonical source commit/tree, config SHA-256, and schedule SHA-256",
                "frozen_schedule_sha256": expected_schedule_sha,
                "schedule_sha256": expected_schedule_sha,
                "campaign_wall_seconds_used_before": wall_seconds_before,
                "campaign_wall_budget_scope": config_data["campaign_limits"]["gameplay_wall_budget_scope"],
                "artifact_bytes_used_before": artifact_bytes_before,
                "v1_run_id_excluded_from_this_run": "m6-stage3-ad3998200e31-c5ff389dc4fe",
                "protocol_interpretation": config_data["scientific_interpretation"],
                "runtime_lock_verification": locked_runtime_identity,
                "policy_roster": [
                    _manifest_policy_row(self.roster[policy_id][1]) for policy_id in V2_POLICY_IDS
                ],
                "run_identity_inputs": {
                    "source_commit": source["git_commit"],
                    "source_tree": source["git_tree"],
                    "configuration_sha256": config_sha,
                    "schedule_sha256": expected_schedule_sha,
                },
            })
            manifest_path = run_dir / "run-manifest.json"
            write_json_atomic(manifest_path, manifest, refuse_existing=False)
            # The immutable manifest is durable before the first reset/outcome.
            ledger = HashChainLedger(run_dir / "events.jsonl", run_id=run_id)
            ledger.append("run_started", {
                "run_manifest_sha256": sha256_file(manifest_path),
                "schedule_sha256": expected_schedule_sha,
                "schedule": schedule,
                "protocol_id": config_data["protocol_id"],
            })
            started_payloads: dict[str, dict[str, Any]] = {}
            started_ids: set[str] = set()
            reset_ids: set[str] = set()
            completed_ids: set[str] = set()
            finished_records: dict[str, dict[str, Any]] = {}
            self.startup_retries_used = 0
        else:
            if run_dir.is_symlink() or not run_dir.is_dir():
                raise FileNotFoundError("the frozen Stage 3 v2 run directory is unavailable")
            manifest_path = run_dir / "run-manifest.json"
            if manifest_path.is_symlink() or not manifest_path.is_file():
                raise ExperimentIdentityError("the frozen v2 run manifest is missing or unsafe")
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            for key, value in source.items():
                if manifest.get(key) != value:
                    raise ExperimentIdentityError(f"v2 resume source identity differs for {key}")
            if (manifest.get("configuration_sha256") != config_sha
                    or manifest.get("schedule_sha256") != expected_schedule_sha
                    or manifest.get("runtime_construction", {}).get("ale_episode_frame_limit") != 500_000
                    or manifest.get("protocol_id") != config_data["protocol_id"]
                    or manifest.get("seed_schedule") != schedule
                    or manifest.get("frozen_schedule_sha256") != expected_schedule_sha
                    or manifest.get("attempt_limit") != 20):
                raise ExperimentIdentityError("v2 resume configuration, schedule, protocol, or ALE horizon changed")
            ledger = HashChainLedger(run_dir / "events.jsonl", run_id=run_id, create=False)
            started_payloads = {}
            started_ids = set()
            reset_ids = set()
            completed_ids = set()
            finished_records = {}
            reset_game_ids: set[str] = set()
            self.startup_retries_used = 0
            run_started_manifest_hash: str | None = None
            for event in iter_verified_hash_chain(run_dir / "events.jsonl", expected_run_id=run_id):
                payload = event["payload"]
                attempt_id = payload.get("attempt_id")
                if event["event_type"] == "run_started":
                    if run_started_manifest_hash is not None:
                        raise ExperimentIdentityError("v2 ledger has multiple run_started events")
                    run_started_manifest_hash = payload.get("run_manifest_sha256")
                elif event["event_type"] == "attempt_started" and isinstance(attempt_id, str):
                    if attempt_id in started_ids:
                        raise ExperimentIdentityError(f"duplicate v2 attempt ID in ledger: {attempt_id}")
                    started_ids.add(attempt_id)
                    started_payloads[attempt_id] = payload
                elif event["event_type"] == "ale_reset_observed" and isinstance(attempt_id, str):
                    game_id = payload.get("game_id")
                    if game_id in reset_game_ids:
                        raise ExperimentIdentityError(f"duplicate v2 reset/game identity: {game_id}")
                    reset_game_ids.add(game_id)
                    reset_ids.add(attempt_id)
                elif event["event_type"] == "attempt_finished" and isinstance(attempt_id, str):
                    if attempt_id in completed_ids:
                        raise ExperimentIdentityError(f"duplicate v2 attempt completion: {attempt_id}")
                    completed_ids.add(attempt_id)
                    finished_records[attempt_id] = payload["attempt_record"]
                elif event["event_type"] == "process_start_retry":
                    self.startup_retries_used += 1
            if self.startup_retries_used > 1:
                raise ExperimentIdentityError("v2 ledger exceeds the one global pre-action retry allowance")
            if run_started_manifest_hash != sha256_file(manifest_path):
                raise ExperimentIdentityError("v2 frozen run manifest does not match its run_started ledger identity")
            config = expected_runtime_config

        campaign_wall_used_before = self._cumulative_gameplay_wall_seconds(exclude_run_id=run_id)
        gameplay_start = time.monotonic()
        consumed_before = sum(self._record_wall_bound_seconds(row) for row in finished_records.values())
        campaign_wall_limit = int(self.campaign_limits["maximum_gameplay_wall_seconds"])
        artifact_limit = int(self.campaign_limits["maximum_artifact_bytes"])
        artifact_reserve = int(self.campaign_limits["artifact_metadata_reserve_bytes"])
        max_rss = int(self.campaign_limits["maximum_process_rss_bytes"])

        def run_slot(item: dict[str, Any], attempt_id: str, max_seconds: float) -> dict[str, Any]:
            record = self._run_one(
                ledger=ledger,
                run_id=run_id,
                stage="stage3-v2",
                profile="ale-v5-extended-horizon",
                config=config,
                schedule=item,
                max_player_moves=int(self.episode_limits["maximum_player_moves"]),
                max_episode_seconds=max_seconds,
                attempt_id_override=attempt_id,
            )
            started_ids.add(attempt_id)
            completed_ids.add(attempt_id)
            finished_records[attempt_id] = record
            if record.get("reset_observed"):
                reset_ids.add(attempt_id)
            return record

        resource_stop_reason: str | None = None
        for item in schedule:
            base_attempt_id = (
                f"{_slug(item['policy_id'])}-seed-{item['ale_seed']}-slot-{item['slot']:03d}-attempt-0000-v2"
            )
            retry_attempt_id = f"{base_attempt_id}-startup-retry-0001"
            related_ids = (base_attempt_id, retry_attempt_id)
            recovered = False
            for attempt_id in related_ids:
                if attempt_id in reset_ids and attempt_id not in completed_ids:
                    attempt_events = [
                        event for event in iter_verified_hash_chain(run_dir / "events.jsonl", expected_run_id=run_id)
                        if event["payload"].get("attempt_id") == attempt_id
                    ]
                    record = self._recover_interrupted_reset(
                        run_id=run_id,
                        schedule=item,
                        attempt_id=attempt_id,
                        events=attempt_events,
                        ledger=ledger,
                    )
                    completed_ids.add(attempt_id)
                    finished_records[attempt_id] = record
                    recovered = True
                    break
            if recovered:
                continue
            if retry_attempt_id in started_ids and retry_attempt_id not in completed_ids:
                self._finish_pre_reset_failure(
                    ledger=ledger,
                    run_id=run_id,
                    game_id=item["game_id"],
                    attempt_id=retry_attempt_id,
                    policy_id=item["policy_id"],
                    seed=int(item["ale_seed"]),
                    reason="the single v2 pre-action retry was interrupted before reset/action evidence",
                )
                completed_ids.add(retry_attempt_id)
                finished_records[retry_attempt_id] = {
                    "attempt_id": retry_attempt_id,
                    "reset_observed": False,
                    "outcome": "incomplete",
                    "start_timestamp_utc": started_payloads.get(retry_attempt_id, {}).get("start_timestamp_utc"),
                    "end_timestamp_utc": utc_now(),
                    "wall_seconds": None,
                }
                continue

            if base_attempt_id in completed_ids:
                existing = finished_records[base_attempt_id]
                if existing.get("reset_observed") or retry_attempt_id in started_ids:
                    continue
                if self.startup_retries_used >= 1:
                    continue
                pre_action_failure = True
            elif base_attempt_id in started_ids:
                if base_attempt_id in reset_ids:
                    continue
                self._finish_pre_reset_failure(
                    ledger=ledger,
                    run_id=run_id,
                    game_id=item["game_id"],
                    attempt_id=base_attempt_id,
                    policy_id=item["policy_id"],
                    seed=int(item["ale_seed"]),
                    reason="resumed process ended before reset or action evidence was durable",
                )
                completed_ids.add(base_attempt_id)
                finished_records[base_attempt_id] = {
                    "attempt_id": base_attempt_id,
                    "reset_observed": False,
                    "outcome": "incomplete",
                    "start_timestamp_utc": started_payloads.get(base_attempt_id, {}).get("start_timestamp_utc"),
                    "end_timestamp_utc": utc_now(),
                    "wall_seconds": None,
                }
                pre_action_failure = True
            else:
                pre_action_failure = False

            total_used = campaign_wall_used_before + consumed_before + (time.monotonic() - gameplay_start)
            remaining_seconds = campaign_wall_limit - total_used
            current_rss = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024)
            current_artifacts = self._artifact_bytes()
            available_disk = shutil.disk_usage(self.artifact_root).free
            if remaining_seconds <= 0:
                resource_stop_reason = "12-hour v2 cumulative gameplay wall-time ceiling reached"
            elif current_artifacts + artifact_reserve >= artifact_limit:
                resource_stop_reason = "8-GiB v2 retained-artifact ceiling reached with finalization reserve"
            elif available_disk <= artifact_reserve:
                resource_stop_reason = "free disk space reached the v2 artifact-finalization reserve"
            elif current_rss >= max_rss:
                resource_stop_reason = "process RSS reached the 6-GiB v2 memory ceiling"
            if resource_stop_reason:
                ledger.append("resource_stop", {
                    "reason": resource_stop_reason,
                    "next_game_id": item["game_id"],
                    "remaining_schedule_count": len(schedule) - int(item["slot"]),
                    "rss_bytes": current_rss,
                    "artifact_bytes": current_artifacts,
                    "free_disk_bytes": available_disk,
                })
                break

            max_seconds = min(float(self.episode_limits["maximum_wall_seconds"]), remaining_seconds)
            attempt_id = retry_attempt_id if pre_action_failure else base_attempt_id
            if pre_action_failure:
                if self.startup_retries_used >= 1:
                    continue
                self.startup_retries_used += 1
                ledger.append("process_start_retry", {
                    "attempt_id": base_attempt_id,
                    "retry_attempt_id": retry_attempt_id,
                    "game_id": item["game_id"],
                    "action_attempted": False,
                    "reason": finished_records.get(base_attempt_id, {}).get("stop_reason", "recovered pre-reset process failure"),
                })
            record = run_slot(item, attempt_id, max_seconds)
            resource_records = [record]
            state = record.get("startup_state", {})
            if (not record.get("reset_observed")
                    and record.get("runner_stop_category") == "PROCESS_START_FAILURE"
                    and not state.get("action_attempted")
                    and self.startup_retries_used < 1):
                remaining_after = campaign_wall_limit - campaign_wall_used_before - consumed_before - (time.monotonic() - gameplay_start)
                if remaining_after > 0 and self._artifact_bytes() + artifact_reserve < artifact_limit:
                    self.startup_retries_used += 1
                    ledger.append("process_start_retry", {
                        "attempt_id": record["attempt_id"],
                        "retry_attempt_id": retry_attempt_id,
                        "game_id": item["game_id"],
                        "action_attempted": False,
                        "reason": record.get("stop_reason"),
                    })
                    retry_record = run_slot(
                        item,
                        retry_attempt_id,
                        min(float(self.episode_limits["maximum_wall_seconds"]), remaining_after),
                    )
                    resource_records.append(retry_record)
            if any(
                item_record.get("runner_stop_category") == "RUNNER_RESOURCE_LIMIT"
                or (isinstance(item_record.get("peak_rss_bytes"), int) and item_record["peak_rss_bytes"] >= max_rss)
                for item_record in resource_records
            ):
                resource_stop_reason = "process RSS reached the 6-GiB v2 memory ceiling during an attempt"
                ledger.append("resource_stop", {
                    "reason": resource_stop_reason,
                    "completed_attempt_ids": [item_record["attempt_id"] for item_record in resource_records],
                    "rss_bytes": max((item_record.get("peak_rss_bytes", 0) or 0 for item_record in resource_records), default=None),
                })
                break
            if self._artifact_bytes() > artifact_limit:
                ledger.append("resource_stop", {
                    "reason": "v2 retained-artifact size exceeded its hard ceiling",
                    "completed_attempt_id": record["attempt_id"],
                })
                resource_stop_reason = "8-GiB v2 retained-artifact hard ceiling exceeded"
                break

        reset_game_ids = sorted({
            record.get("game_id") for record in finished_records.values() if record.get("reset_observed")
        })
        ledger.append("run_progress_checkpoint", {
            "completed_attempt_ids": sorted(completed_ids),
            "completed_reset_game_ids": reset_game_ids,
            "scheduled_game_ids": [row["game_id"] for row in schedule],
            "unexecuted_game_ids": [row["game_id"] for row in schedule if row["game_id"] not in reset_game_ids],
            "remaining_schedule_count": 20 - len(reset_game_ids),
            "resource_stop_reason": resource_stop_reason,
            "run_manifest_sha256": sha256_file(run_dir / "run-manifest.json"),
        })
        return self._finalize(run_dir, run_id=run_id, ledger=ledger)


def canonical_schedule_bytes(schedule: list[dict[str, Any]]) -> bytes:
    return json.dumps(schedule, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
