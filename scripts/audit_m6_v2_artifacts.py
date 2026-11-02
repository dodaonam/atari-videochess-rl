#!/usr/bin/env python3
"""Independent, read-only audit of the retained M6 Stage 3 v2 raw evidence.

This verifier intentionally uses only the Python standard library and does not
import the campaign, ledger, or summary implementation that created the run.
It hashes the complete artifact tree, validates both hash-chain layers, and
reconstructs schedule, outcome, move, reply, cursor, frame, and resource counts
from the retained records and episode traces.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path, PurePosixPath
import platform
import stat
import subprocess
import sys
from typing import Any


RUN_ID = "m6-stage3-v2-91f51b14690e-d05d42400cfc"
V2_MANIFEST_SHA256 = "e5870bdc4c1aa05108ed58eacc6ec95123ab2b4bc9436d43c9c9640113eabd83"
V2_ARTIFACT_MANIFEST_SHA256 = "bc0068aa2254e4c15165247ee299f48940cca9b7c21f6a288fd13812631ea2b2"
V2_LEDGER_SHA256 = "c8364fa194a65c8de6d90bf9165743a411d0a63eba2459f3023821f3d0d838cb"
V2_CONFIG_SHA256 = "663651050db80ab027b452241c7d39837ec7986927c0aefc7c7be631f459a49b"
V2_SCHEDULE_SHA256 = "be4e6548e6fd3e3db4605e6b55fbe860848dccb2df87d8a7122145bdabe22ffc"
M5_ROOT_MANIFEST_SHA256 = "a201a254671ad59ae1fecb402abf994d5bf523097f1c3010b5c7fa237ae6dd4c"
ROM_SHA256 = "d44f2a115393b0a6cbcd5398d62369e652f3670a9ee585883d183e740edad0f7"
WARM_ID = "m5-warm-seed-20261104-post-rl"
SCRATCH_ID = "m5-scratch-seed-20261104-post-rl"
CHECKPOINTS = {
    WARM_ID: (
        "0b2405017a8e1d539851f0cd278883d3fd23936fb5c2f7962c813590a6fd1767",
        "80d8689e4b349576c5708bb4dce3451e5a8c64d81470cd6f4273a4746844b682",
    ),
    SCRATCH_ID: (
        "3749b0c0b6ae44d3ad5d6bf0863b60937a59fbe881e0bdf4932bdce6033ca400",
        "1c15e5bc4ba2437df113671dc316accbdfe6d8b59069ed29ed187daebf4fff1e",
    ),
}
GENESIS = "0" * 64
LEDGER_SCHEMA = "videochess-m6-attempt-ledger/1.0"
MANIFEST_SCHEMA = "videochess-m6-artifact-manifest/1.0"
TRACE_CHAIN_SCHEMA = "videochess-m6-trace-event-chain/1.0"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def safe_relative(value: Any) -> str:
    if not isinstance(value, str) or not value or "\\" in value:
        raise ValueError(f"unsafe or missing relative artifact path: {value!r}")
    path = PurePosixPath(value)
    if (path.is_absolute() or not path.parts or any(part in {"", ".", ".."} for part in path.parts)
            or ":" in path.parts[0]):
        raise ValueError(f"unsafe artifact path traversal: {value!r}")
    return path.as_posix()


def checked_root(value: str | Path) -> Path:
    path = Path(value).expanduser()
    if path.is_symlink() or not path.is_dir():
        raise ValueError(f"artifact root must be an existing non-symlink directory: {path}")
    return path.resolve(strict=True)


def portable_artifact_root(root: str | Path) -> str:
    """Return a project-relative artifact identity without host-specific roots."""
    resolved = Path(root).resolve(strict=True)
    artifacts_ancestors = [parent for parent in resolved.parents if parent.name == "artifacts"]
    if artifacts_ancestors:
        # The nearest artifacts directory is the logical root, regardless of
        # which worktree mounted or preserved the bytes.
        artifacts = artifacts_ancestors[0]
        return (Path("artifacts") / resolved.relative_to(artifacts)).as_posix()
    return (Path("external-artifact-root") / resolved.name).as_posix()


def tree_files(root: Path) -> dict[str, Path]:
    """Enumerate only regular files; reject symlinks and special nodes anywhere."""
    found: dict[str, Path] = {}
    for directory, dirnames, filenames in os.walk(root, topdown=True, followlinks=False):
        base = Path(directory)
        for name in list(dirnames):
            child = base / name
            if child.is_symlink():
                raise ValueError(f"symlink directory in artifact tree: {child.relative_to(root)}")
            if not child.is_dir():
                raise ValueError(f"non-directory entry in artifact tree: {child.relative_to(root)}")
        for name in filenames:
            child = base / name
            mode = child.lstat().st_mode
            if stat.S_ISLNK(mode):
                raise ValueError(f"symlink in artifact tree: {child.relative_to(root)}")
            if not stat.S_ISREG(mode):
                raise ValueError(f"non-regular file in artifact tree: {child.relative_to(root)}")
            relative = child.relative_to(root).as_posix()
            if relative == "artifact-manifest.json":
                continue
            found[relative] = child
    return found


def verify_tree(root: Path, *, expected_manifest_sha256: str | None = None) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    manifest_path = root / "artifact-manifest.json"
    if manifest_path.is_symlink() or not manifest_path.is_file():
        raise ValueError(f"artifact manifest missing or unsafe under {root}")
    manifest_sha = sha256_file(manifest_path)
    if expected_manifest_sha256 is not None and manifest_sha != expected_manifest_sha256:
        raise ValueError(f"artifact-manifest.json SHA-256 mismatch: {manifest_sha}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("schema") != MANIFEST_SCHEMA or not isinstance(manifest.get("files"), list):
        raise ValueError("unsupported artifact manifest schema")
    expected: dict[str, dict[str, Any]] = {}
    for row in manifest["files"]:
        if not isinstance(row, dict):
            raise ValueError("artifact manifest contains a non-object row")
        relative = safe_relative(row.get("path"))
        if relative == "artifact-manifest.json" or relative in expected:
            raise ValueError(f"duplicate or self-referential artifact row: {relative}")
        size = row.get("size_bytes")
        digest = row.get("sha256")
        if isinstance(size, bool) or not isinstance(size, int) or size < 0:
            raise ValueError(f"invalid manifest size for {relative}")
        if not isinstance(digest, str) or len(digest) != 64:
            raise ValueError(f"invalid manifest hash for {relative}")
        expected[relative] = row

    actual_paths = tree_files(root)
    if set(actual_paths) != set(expected):
        missing = sorted(set(expected) - set(actual_paths))
        unexpected = sorted(set(actual_paths) - set(expected))
        raise ValueError(f"artifact path set differs; missing={missing[:8]} unexpected={unexpected[:8]}")

    actual: dict[str, dict[str, Any]] = {}
    for relative in sorted(actual_paths):
        path = actual_paths[relative]
        row = {"path": relative, "size_bytes": path.stat().st_size, "sha256": sha256_file(path)}
        if row != expected[relative]:
            raise ValueError(f"artifact size/hash mismatch for {relative}")
        actual[relative] = row
    total = sum(row["size_bytes"] for row in actual.values())
    if manifest.get("total_bytes") != total:
        raise ValueError("artifact manifest total_bytes differs from independently measured bytes")
    return {"sha256": manifest_sha, "file_count": len(actual), "total_bytes": total}, actual


def verify_ledger(path: Path, run_id: str) -> tuple[dict[str, Any], dict[str, Any]]:
    if path.is_symlink() or not path.is_file():
        raise ValueError("ledger is missing or unsafe")
    digest = sha256_file(path)
    previous = GENESIS
    counts: Counter[str] = Counter()
    started: dict[str, dict[str, Any]] = {}
    resets: dict[str, dict[str, Any]] = {}
    finished: dict[str, dict[str, Any]] = {}
    action_counts: dict[str, Counter[str]] = defaultdict(Counter)
    last_observed: dict[str, dict[str, Any]] = {}
    terminal_action_sequence: dict[str, int] = {}
    run_started: list[dict[str, Any]] = []
    run_finished: list[dict[str, Any]] = []
    with path.open("rb") as stream:
        for sequence, line in enumerate(stream, 1):
            if not line.endswith(b"\n"):
                raise ValueError(f"ledger ends with a partial record at sequence {sequence}")
            try:
                event = json.loads(line[:-1])
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise ValueError(f"invalid JSON ledger record at sequence {sequence}") from exc
            if not isinstance(event, dict) or event.get("schema") != LEDGER_SCHEMA:
                raise ValueError(f"unsupported ledger event at sequence {sequence}")
            if event.get("run_id") != run_id or event.get("sequence") != sequence:
                raise ValueError(f"ledger identity/sequence mismatch at sequence {sequence}")
            if event.get("previous_event_sha256") != previous:
                raise ValueError(f"ledger predecessor mismatch at sequence {sequence}")
            required = ("schema", "run_id", "sequence", "previous_event_sha256", "event_type", "payload")
            try:
                core = {key: event[key] for key in required}
                calculated = hashlib.sha256(previous.encode("ascii") + canonical_bytes(core)).hexdigest()
            except (KeyError, TypeError, ValueError) as exc:
                raise ValueError(f"malformed ledger event at sequence {sequence}") from exc
            if event.get("event_sha256") != calculated:
                raise ValueError(f"ledger event digest mismatch at sequence {sequence}")
            payload = event.get("payload")
            if not isinstance(payload, dict):
                raise ValueError(f"ledger payload is not an object at sequence {sequence}")
            kind = event["event_type"]
            counts[kind] += 1
            attempt_id = payload.get("attempt_id")
            if kind == "run_started":
                run_started.append(payload)
            elif kind == "run_finished":
                run_finished.append(payload)
            elif kind == "attempt_started":
                if not isinstance(attempt_id, str) or attempt_id in started:
                    raise ValueError(f"missing/duplicate attempt_started identity at sequence {sequence}")
                started[attempt_id] = payload
            elif kind == "ale_reset_observed":
                if not isinstance(attempt_id, str) or attempt_id in resets:
                    raise ValueError(f"missing/duplicate reset identity at sequence {sequence}")
                resets[attempt_id] = payload
            elif kind == "attempt_finished":
                if not isinstance(attempt_id, str) or attempt_id in finished:
                    raise ValueError(f"missing/duplicate attempt_finished identity at sequence {sequence}")
                record = payload.get("attempt_record")
                if not isinstance(record, dict):
                    raise ValueError(f"attempt_finished record is malformed at sequence {sequence}")
                finished[attempt_id] = record
            if kind in {"ale_action_started", "ale_action_observed", "ale_action_failed"} and isinstance(attempt_id, str):
                if attempt_id in terminal_action_sequence:
                    raise ValueError(f"ALE action recorded after terminal for {attempt_id}")
                action_counts[attempt_id][kind] += 1
                if kind == "ale_action_observed":
                    last_observed[attempt_id] = {**payload, "sequence": sequence}
                    if payload.get("terminated") is True or payload.get("truncated") is True:
                        terminal_action_sequence[attempt_id] = sequence
            previous = calculated
    if len(run_started) != 1 or len(run_finished) > 1:
        raise ValueError("ledger must contain exactly one run_started and at most one run_finished")
    if set(started) != set(resets) or set(started) != set(finished):
        raise ValueError("attempt starts, resets, and finishes do not have identical identities")
    return (
        {"sha256": digest, "event_count": sequence, "head_sha256": previous, "event_counts": dict(sorted(counts.items()))},
        {
            "run_started": run_started[0], "started": started, "resets": resets,
            "finished": finished, "action_counts": action_counts,
            "last_observed": last_observed, "terminal_sequences": terminal_action_sequence,
        },
    )


def trace_rows(trace: dict[str, Any]) -> list[tuple[str, Any]]:
    rows: list[tuple[str, Any]] = [("reset", trace.get("reset")), ("initial_position", trace.get("initial_position"))]
    for turn in trace.get("turns", []):
        rows.append(("decision_input", turn.get("decision_input")))
        rows.append(("policy_decision", turn.get("policy_decision")))
        rows.extend(("controller_phase", phase) for phase in turn.get("input_phases", []))
        rows.extend(("rgb_evidence_window", evidence) for evidence in turn.get("evidence_windows", []))
        rows.append(("player_move", turn.get("player_move")))
        rows.append(("atari_reply", turn.get("opponent_reply")))
    rows.extend((("terminal", trace.get("terminal")), ("terminal_observation", trace.get("terminal_observation"))))
    return rows


def verify_trace_chain(trace: dict[str, Any]) -> dict[str, Any]:
    chain = trace.get("event_hash_chain")
    if not isinstance(chain, dict) or chain.get("schema") != TRACE_CHAIN_SCHEMA:
        raise ValueError("episode trace event chain is missing or unsupported")
    payload = {key: value for key, value in trace.items() if key != "event_hash_chain"}
    payload_sha = hashlib.sha256(canonical_bytes(payload)).hexdigest()
    if chain.get("payload_sha256") != payload_sha:
        raise ValueError("episode payload SHA-256 differs from its chained digest")
    rows = trace_rows(payload)
    rows.append(("complete_trace_payload_sha256", {"sha256": payload_sha}))
    previous = GENESIS
    expected_events = []
    for sequence, (kind, event_payload) in enumerate(rows, 1):
        core = {
            "sequence": sequence,
            "previous_event_sha256": previous,
            "event_type": kind,
            "payload": event_payload,
        }
        calculated = hashlib.sha256(previous.encode("ascii") + canonical_bytes(core)).hexdigest()
        expected_events.append({**core, "event_sha256": calculated})
        previous = calculated
    if chain.get("event_count") != len(expected_events) or chain.get("head_sha256") != previous:
        raise ValueError("episode trace event-chain head or count mismatch")
    if chain.get("events") != expected_events:
        raise ValueError("episode trace event-chain records are inconsistent")
    return {"event_count": len(expected_events), "head_sha256": previous, "payload_sha256": payload_sha}


def outcome_from_trace(terminal: dict[str, Any]) -> str:
    if terminal.get("ale_terminated") is True and terminal.get("ale_truncated") is not True:
        reward = terminal.get("ale_reward_total")
        if not finite_number(reward):
            return "terminal_unknown"
        if reward > 0:
            return "win"
        if reward < 0:
            return "loss"
        return "terminal_unknown"
    if terminal.get("ale_truncated") is True:
        return "ale_truncated"
    if terminal.get("runner_stop_category") in {
        "RUNNER_MAX_ALE_FRAMES", "RUNNER_MAX_ENV_STEPS", "RUNNER_MAX_WALL_CLOCK",
        "RUNNER_MAX_PLAYER_MOVES", "RUNNER_ARTIFACT_LIMIT", "RUNNER_RESOURCE_LIMIT",
    }:
        return "runner_truncated"
    return "incomplete"


def repo_relative_artifact(root: Path, run_id: str, value: Any) -> tuple[Path, str]:
    relative = safe_relative(value)
    prefix = f"artifacts/m6/v2/{run_id}/"
    if not relative.startswith(prefix):
        raise ValueError(f"trace/manifest path does not name this v2 run: {relative}")
    suffix = safe_relative(relative[len(prefix):])
    path = root / suffix
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"trace/manifest artifact is missing or unsafe: {suffix}")
    return path, suffix


def expected_schedule(config: dict[str, Any]) -> list[dict[str, Any]]:
    warm, scratch = WARM_ID, SCRATCH_ID
    result = []
    slot = 0
    for seed in config["paired_m5_seeds"]:
        order = [warm, scratch] if int(seed) % 2 == 0 else [scratch, warm]
        for policy_id in order:
            result.append({
                "ale_seed": int(seed),
                "game_id": f"{policy_id}-ale-seed-{int(seed)}-stage3-v2",
                "policy_id": policy_id,
                "slot": slot,
            })
            slot += 1
    return result


def finite_number(value: Any) -> bool:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    try:
        return math.isfinite(float(value))
    except (OverflowError, ValueError):
        return False


def latency_summary(values: list[float]) -> dict[str, float | None]:
    if not values:
        return {"count": 0, "median": None, "iqr": None, "p95": None, "max": None}
    ordered = sorted(values)

    def quantile(probability: float) -> float:
        position = (len(ordered) - 1) * probability
        lower = math.floor(position)
        upper = math.ceil(position)
        if lower == upper:
            return ordered[lower]
        return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)

    return {
        "count": len(ordered),
        "median": quantile(0.50),
        "iqr": quantile(0.75) - quantile(0.25),
        "p95": quantile(0.95),
        "max": ordered[-1],
    }


def audit_v1(root_value: str | Path, repo_root: Path) -> dict[str, Any]:
    root = checked_root(root_value)
    expected_run = "m6-stage3-ad3998200e31-c5ff389dc4fe"
    expected_manifest = "22ac6ec7e0f4a48f52b2452654d4adecaf111f38ea37f5d9517f173c838716d7"
    expected_ledger = "c8ad5b26c28bb8f934a8541c4b69846afedd3ad4a3eb8c302ac835b20fdf27d3"
    expected_run_manifest = "17491f1a82eacffda9189179cc63b2ebff422136d07925de1fb39a2bcff897e8"
    tree, _ = verify_tree(root, expected_manifest_sha256=expected_manifest)
    ledger, ledger_records = verify_ledger(root / "events.jsonl", expected_run)
    run_manifest_sha = sha256_file(root / "run-manifest.json")
    if run_manifest_sha != expected_run_manifest or ledger["sha256"] != expected_ledger:
        raise ValueError("historical v1 run-manifest or ledger identity mismatch")
    run_manifest = json.loads((root / "run-manifest.json").read_text(encoding="utf-8"))
    config_sha = sha256_file(repo_root / "configs/m6/m6-stage3-v1.json")
    if run_manifest.get("git_commit") != "ad3998200e31e77b292ffc1138d02354f188bf5f":
        raise ValueError("v1 source commit identity mismatch")
    if config_sha != "05aedeb30efb8b6b97667c44f9d606b58d4da8ae20800d4ef143e629420cebac":
        raise ValueError("v1 frozen config digest changed")
    if len(ledger_records["resets"]) != 35 or len(ledger_records["finished"]) != 35:
        raise ValueError("v1 raw ledger no longer records all 35 original attempts")
    return {
        "run_id": expected_run,
        "raw_root": portable_artifact_root(root),
        "run_manifest_sha256": run_manifest_sha,
        "artifact_manifest": tree,
        "ledger": ledger,
        "reset_attempts": len(ledger_records["resets"]),
        "finished_attempts": len(ledger_records["finished"]),
        "protocol_config_sha256": config_sha,
        "budget_metadata": {
            "gameplay_wall_budget_includes_diagnostics": run_manifest.get("budget", {}).get("gameplay_wall_budget_includes_diagnostics"),
            "campaign_wall_budget_includes_diagnostics": run_manifest.get("campaign_wall_budget_includes_diagnostics"),
        },
    }


def audit_v2(root_value: str | Path, repo_root_value: str | Path) -> dict[str, Any]:
    root = checked_root(root_value)
    repo_root = Path(repo_root_value).resolve(strict=True)
    run_manifest_path = root / "run-manifest.json"
    manifest_sha = sha256_file(run_manifest_path)
    if manifest_sha != V2_MANIFEST_SHA256:
        raise ValueError(f"v2 original run-manifest SHA-256 mismatch: {manifest_sha}")
    manifest = json.loads(run_manifest_path.read_text(encoding="utf-8"))
    if manifest.get("run_id") != RUN_ID or manifest.get("stage") != "stage3-v2":
        raise ValueError("raw run-manifest identity mismatch")
    if manifest.get("git_commit") != "91f51b14690eba12e9e4fd25a4fc1671801fac0d" or manifest.get("git_tree") != "4d6ed616971c8f5606a0a7250fe68fa2eea40949":
        raise ValueError("frozen v2 execution source identity mismatch")
    source_tree = subprocess.check_output(
        ["git", "rev-parse", "91f51b14690eba12e9e4fd25a4fc1671801fac0d^{tree}"], cwd=repo_root, text=True
    ).strip()
    if source_tree != manifest["git_tree"]:
        raise ValueError("frozen source commit tree differs from the raw run manifest")
    config_path = repo_root / "configs/m6/m6-stage3-v2.json"
    config_sha = sha256_file(config_path)
    if config_sha != V2_CONFIG_SHA256 or manifest.get("configuration_sha256") != config_sha:
        raise ValueError("v2 frozen configuration identity mismatch")
    if manifest.get("m5_root_manifest_sha256") != M5_ROOT_MANIFEST_SHA256:
        raise ValueError("v2 M5 root artifact-manifest identity mismatch")
    if manifest.get("rom_sha256") != ROM_SHA256:
        raise ValueError("v2 recorded ROM identity mismatch")
    config = json.loads(config_path.read_text(encoding="utf-8"))
    expected_ale_config = {
        "difficulty": 0,
        "env_id": "ALE/VideoChess-v5",
        "frameskip": 4,
        "max_num_frames_per_episode": 500_000,
        "mode": 4,
        "obs_type": "rgb",
        "repeat_action_probability": 0.25,
    }
    runtime = manifest.get("runtime_construction", {})
    if manifest.get("ale_config") != expected_ale_config or runtime.get("config") != expected_ale_config:
        raise ValueError("v2 frozen ALE config differs from the recorded runtime configuration")
    if (runtime.get("ale_episode_frame_limit") != config["ale_horizon"]["max_num_frames_per_episode"]
            or runtime.get("instance_runtime", {}).get("max_num_frames_per_episode") != 500_000
            or runtime.get("registered_defaults", {}).get("max_num_frames_per_episode") != 108_000):
        raise ValueError("v2 explicit ALE horizon is not distinguishable from the registered default")
    if manifest.get("stockfish_in_inference") is not False or manifest.get("training_or_finetuning") is not False:
        raise ValueError("v2 runtime manifest does not exclude training and Stockfish")
    if manifest.get("budget", {}).get("ale_post_reset_action_frames_per_game") != 432_000:
        raise ValueError("v2 runner frame cap differs from its frozen profile")
    if manifest.get("budget", {}).get("wall_seconds_per_game") != 1_800:
        raise ValueError("v2 per-attempt wall limit differs from its frozen profile")
    if manifest.get("budget", {}).get("gameplay_wall_seconds_total") != 43_200:
        raise ValueError("v2 campaign wall limit differs from its frozen profile")
    if (manifest.get("campaign_wall_budget_scope") != config["campaign_limits"]["gameplay_wall_budget_scope"]
            or manifest.get("campaign_wall_seconds_used_before") != 0.0
            or manifest.get("budget", {}).get("gameplay_wall_budget_includes_diagnostics") is not True):
        raise ValueError("v2 historical budget metadata does not reproduce the documented PM6-F06 discrepancy")
    schedule = expected_schedule(config)
    schedule_sha = hashlib.sha256(canonical_bytes(schedule)).hexdigest()
    if schedule_sha != V2_SCHEDULE_SHA256 or manifest.get("seed_schedule") != schedule:
        raise ValueError("v2 schedule differs from independently reconstructed frozen order")
    if manifest.get("frozen_schedule_sha256") != schedule_sha or manifest.get("schedule_sha256") != schedule_sha:
        raise ValueError("v2 schedule digest differs from its frozen identity")
    roster = {row.get("policy_id"): row for row in manifest.get("policy_roster", [])}
    if set(roster) != set(CHECKPOINTS):
        raise ValueError("v2 frozen roster is not exactly the accepted Warm/Scratch pair")
    for policy_id, hashes in CHECKPOINTS.items():
        row = roster[policy_id]
        if (row.get("checkpoint_sha256"), row.get("sidecar_sha256")) != hashes:
            raise ValueError(f"frozen checkpoint/sidecar identity mismatch for {policy_id}")
        if row.get("artifact_manifest_sha256") != M5_ROOT_MANIFEST_SHA256:
            raise ValueError(f"M5 root manifest identity mismatch for {policy_id}")

    artifact_tree, file_rows = verify_tree(root, expected_manifest_sha256=V2_ARTIFACT_MANIFEST_SHA256)
    if artifact_tree["file_count"] != 4159 or artifact_tree["total_bytes"] != 728_148_524:
        raise ValueError("v2 artifact count/byte total differs from the frozen reference")
    ledger, raw = verify_ledger(root / "events.jsonl", RUN_ID)
    if ledger["sha256"] != V2_LEDGER_SHA256:
        raise ValueError("v2 ledger SHA-256 differs from its frozen reference")
    summary = json.loads((root / "summary.json").read_text(encoding="utf-8"))
    if summary.get("run_id") != RUN_ID or summary.get("scheduled_game_count") != 20:
        raise ValueError("v2 generated summary has an unexpected run or schedule identity")
    if raw["run_started"].get("run_manifest_sha256") != manifest_sha:
        raise ValueError("run_started ledger event does not bind the immutable run manifest")
    if raw["run_started"].get("schedule") != schedule or raw["run_started"].get("schedule_sha256") != schedule_sha:
        raise ValueError("run_started ledger schedule differs from the frozen schedule")
    if set(raw["action_counts"]) - set(raw["started"]):
        raise ValueError("ledger contains ALE action events without a declared attempt")
    if ledger["event_count"] != 968_132:
        raise ValueError("unexpected v2 ledger event count")

    expected_by_game = {row["game_id"]: row for row in schedule}
    started_game_ids = [started.get("game_id") for started in raw["started"].values()]
    if len(started_game_ids) != len(set(started_game_ids)) or set(started_game_ids) != set(expected_by_game):
        raise ValueError("attempt starts do not cover the frozen 20 game IDs exactly once")
    if len(raw["resets"]) != 20 or len(raw["finished"]) != 20:
        raise ValueError("v2 does not contain exactly 20 reset and finish identities")
    if ledger["event_counts"].get("process_start_retry", 0) != 0:
        raise ValueError("v2 unexpectedly used a process-start retry")
    if ledger["event_counts"].get("resource_stop", 0) != 0:
        raise ValueError("v2 contains an unexpected campaign resource stop")

    attempts: list[dict[str, Any]] = []
    totals: dict[str, Counter[str]] = {policy_id: Counter() for policy_id in CHECKPOINTS}
    policy_latencies: dict[str, dict[str, list[float]]] = {
        policy_id: {
            name: [] for name in (
                "input_validation_latency_seconds",
                "policy_choose_move_latency_seconds",
                "adapter_total_latency_seconds",
            )
        } for policy_id in CHECKPOINTS
    }
    all_totals: Counter[str] = Counter()
    stop_counts: Counter[str] = Counter()
    censor_counts: Counter[str] = Counter()
    expected_prefix = f"artifacts/m6/v2/{RUN_ID}/"
    ordered_started = sorted(raw["started"].items(), key=lambda pair: int(pair[1]["attempt_index"]))
    if len(ordered_started) != len(schedule):
        raise ValueError("attempt start count differs from the frozen schedule")
    seen_reset_games: set[str] = set()

    for expected, (attempt_id, started) in zip(schedule, ordered_started, strict=True):
        slot = int(started.get("attempt_index", -1))
        game_id = started.get("game_id")
        if slot != expected["slot"] or game_id != expected["game_id"]:
            raise ValueError(f"schedule slot/order mismatch at slot {expected['slot']}")
        if started.get("policy_id") != expected["policy_id"] or started.get("ale_seed") != expected["ale_seed"]:
            raise ValueError(f"policy/seed mismatch at frozen slot {slot}")
        expected_attempt_id = f"{expected['policy_id']}-seed-{expected['ale_seed']}-slot-{slot:03d}-attempt-0000-v2"
        if attempt_id != expected_attempt_id:
            raise ValueError(f"unexpected or substituted attempt ID at slot {slot}")
        reset = raw["resets"][attempt_id]
        record = raw["finished"][attempt_id]
        if reset.get("game_id") != game_id or reset.get("ale_seed") != expected["ale_seed"] or reset.get("reset_confirmed") is not True:
            raise ValueError(f"reset event does not match frozen slot {slot}")
        reset_rgb_path, reset_rgb_rel = repo_relative_artifact(root, RUN_ID, reset.get("rgb_path"))
        reset_rgb_row = file_rows.get(reset_rgb_rel)
        if (reset_rgb_rel != f"attempts/{attempt_id}/reset.rgb"
                or reset_rgb_row is None or reset_rgb_row["sha256"] != reset.get("rgb_sha256")
                or reset.get("rgb_shape") != [210, 160, 3]
                or reset_rgb_path.stat().st_size != 210 * 160 * 3):
            raise ValueError(f"reset RGB bytes/hash/shape do not match the raw reset event at slot {slot}")
        if game_id in seen_reset_games:
            raise ValueError(f"duplicate reset/game ID: {game_id}")
        seen_reset_games.add(game_id)
        if record.get("attempt_id") != attempt_id or record.get("game_id") != game_id or record.get("policy_id") != expected["policy_id"]:
            raise ValueError(f"finished record identity mismatch at slot {slot}")
        if record.get("run_id") != RUN_ID or record.get("ale_seed") != expected["ale_seed"]:
            raise ValueError(f"finished record run/seed mismatch at slot {slot}")
        if (record.get("git_commit") != manifest["git_commit"]
                or record.get("dependency_lock_sha256") != manifest.get("dependency_lock_sha256")
                or record.get("source_bundle_sha256") != manifest.get("source_bundle_sha256")):
            raise ValueError(f"attempt source/lock identity differs from the frozen run manifest at slot {slot}")
        if (record.get("ale_environment_id") != "ALE/VideoChess-v5"
                or record.get("agent_color") != "white"
                or record.get("profile_id") != "ale-v5-extended-horizon"
                or record.get("mode") != 4 or record.get("difficulty") != 0
                or record.get("observation_type") != "rgb"
                or record.get("frameskip") != 4 or record.get("repeat_action_probability") != 0.25
                or record.get("ale_episode_frame_limit") != 500_000
                or record.get("runner_post_reset_action_frame_limit") != 432_000
                or record.get("episode_wall_time_limit_seconds") != 1_800
                or record.get("maximum_opponent_wait_frames") != 40_000):
            raise ValueError(f"attempt runtime profile differs from the frozen extended-horizon profile at slot {slot}")
        if record.get("checkpoint_sha256") != CHECKPOINTS[expected["policy_id"]][0] or record.get("checkpoint_sidecar_sha256") != CHECKPOINTS[expected["policy_id"]][1]:
            raise ValueError(f"attempt checkpoint identity mismatch at slot {slot}")
        if record.get("policy_root_artifact_manifest_sha256") != M5_ROOT_MANIFEST_SHA256:
            raise ValueError(f"attempt M5 root manifest identity mismatch at slot {slot}")

        attempt_path, attempt_rel = repo_relative_artifact(root, RUN_ID, record.get("artifact_manifest_path"))
        if attempt_rel != f"attempts/{attempt_id}/attempt-manifest.json":
            raise ValueError(f"attempt-manifest path does not match attempt ID at slot {slot}")
        if sha256_file(attempt_path) != record.get("artifact_manifest_sha256"):
            raise ValueError(f"attempt-manifest hash mismatch at slot {slot}")
        attempt_manifest = json.loads(attempt_path.read_text(encoding="utf-8"))
        attempt_dir = attempt_path.parent
        expected_attempt_files = {
            name.removeprefix(f"attempts/{attempt_id}/"): {
                "path": name.removeprefix(f"attempts/{attempt_id}/"),
                "size_bytes": row["size_bytes"],
                "sha256": row["sha256"],
            }
            for name, row in file_rows.items()
            if name.startswith(f"attempts/{attempt_id}/") and name not in {
                f"attempts/{attempt_id}/attempt.json", f"attempts/{attempt_id}/attempt-manifest.json"
            }
        }
        listed_attempt_files = {}
        for row in attempt_manifest.get("files", []):
            relative = safe_relative(row.get("path"))
            if relative in listed_attempt_files:
                raise ValueError(f"duplicate attempt-manifest path at slot {slot}")
            listed_attempt_files[relative] = row
        if attempt_manifest.get("schema") != MANIFEST_SCHEMA or listed_attempt_files != expected_attempt_files:
            raise ValueError(f"per-attempt manifest does not bind its complete artifact set at slot {slot}")
        if attempt_manifest.get("total_bytes") != sum(row["size_bytes"] for row in listed_attempt_files.values()):
            raise ValueError(f"per-attempt manifest byte count mismatch at slot {slot}")

        attempt_json = attempt_dir / "attempt.json"
        if attempt_json.is_symlink() or json.loads(attempt_json.read_text(encoding="utf-8")) != record:
            raise ValueError(f"attempt.json differs from the hash-chained attempt_finished record at slot {slot}")
        trace_path, trace_rel = repo_relative_artifact(root, RUN_ID, record.get("trace_path"))
        if trace_rel != f"attempts/{attempt_id}/trace.json" or sha256_file(trace_path) != record.get("trace_sha256"):
            raise ValueError(f"trace path/hash mismatch at slot {slot}")
        trace_doc = json.loads(trace_path.read_text(encoding="utf-8"))
        if trace_doc.get("schema") != "videochess-m6-episode-trace/1.0" or not isinstance(trace_doc.get("episode"), dict):
            raise ValueError(f"episode trace schema invalid at slot {slot}")
        trace = trace_doc["episode"]
        trace_chain = verify_trace_chain(trace)
        terminal = trace.get("terminal")
        if not isinstance(terminal, dict):
            raise ValueError(f"episode terminal record missing at slot {slot}")
        outcome = outcome_from_trace(terminal)
        if outcome != record.get("outcome"):
            raise ValueError(f"raw terminal flags/reward disagree with recorded outcome at slot {slot}")
        if record.get("ale_terminated") is not terminal.get("ale_terminated") or record.get("ale_truncated") is not terminal.get("ale_truncated"):
            raise ValueError(f"attempt termination flags disagree with raw trace at slot {slot}")

        turns = trace.get("turns")
        if not isinstance(turns, list):
            raise ValueError(f"trace turns are missing at slot {slot}")
        attempted = verified = replies = 0
        decision_count = 0
        choose_latencies: list[float] = []
        reconstructed_history: list[str] = []
        for turn in turns:
            if not isinstance(turn, dict):
                raise ValueError(f"malformed turn record at slot {slot}")
            decision_input = turn.get("decision_input")
            if not isinstance(decision_input, dict) or decision_input.get("history_uci") != reconstructed_history:
                raise ValueError(f"policy observation history advanced beyond verified RGB moves at slot {slot}")
            decision = turn.get("policy_decision")
            if not isinstance(decision, dict):
                raise ValueError(f"turn lacks a frozen-policy decision record at slot {slot}")
            candidates = decision.get("legal_candidates_uci")
            selected = decision.get("selected_uci")
            if (not isinstance(candidates, list) or not candidates
                    or any(not isinstance(candidate, str) for candidate in candidates)
                    or len(candidates) != len(set(candidates)) or candidates != sorted(candidates)
                    or candidates != decision_input.get("legal_candidates_uci")
                    or selected not in candidates):
                raise ValueError(f"policy decision is not a unique legal candidate at slot {slot}")
            if (decision.get("policy_id") != expected["policy_id"]
                    or decision.get("checkpoint_sha256") != CHECKPOINTS[expected["policy_id"]][0]
                    or decision.get("sidecar_sha256") != CHECKPOINTS[expected["policy_id"]][1]
                    or decision.get("artifact_manifest_sha256") != M5_ROOT_MANIFEST_SHA256
                    or decision.get("training") is not False or decision.get("optimizer") is not False
                    or decision.get("replay_insertion") is not False or decision.get("stockfish") is not False):
                raise ValueError(f"policy decision identity or frozen-inference flags mismatch at slot {slot}")
            if (decision.get("history_uci") != reconstructed_history
                    or decision.get("frame_number") != decision_input.get("frame_number")
                    or decision.get("rgb_sha256") != decision_input.get("rgb_sha256")
                    or decision.get("fen") != decision_input.get("fen")
                    or decision.get("side_to_move") != decision_input.get("side_to_move")
                    or decision.get("decision_index") != decision_count + 1):
                raise ValueError(f"policy decision does not bind the verified input context at slot {slot}")
            for metric in (
                "input_validation_latency_seconds",
                "policy_choose_move_latency_seconds",
                "adapter_total_latency_seconds",
            ):
                value = decision.get(metric)
                if not finite_number(value) or value < 0:
                    raise ValueError(f"policy timing {metric} is missing or invalid at slot {slot}")
                policy_latencies[expected["policy_id"]][metric].append(float(value))
                if metric == "policy_choose_move_latency_seconds":
                    choose_latencies.append(float(value))
            decision_count += 1
            move = turn.get("player_move") or {}
            reply = turn.get("opponent_reply") or {}
            initiated = move.get("input_initiated") is True
            rgb_verified = move.get("verified_from_rgb") is True
            if rgb_verified and not initiated:
                raise ValueError(f"RGB-verified move lacks initiated input at slot {slot}")
            attempted += int(initiated)
            verified += int(rgb_verified)
            replies += int(reply.get("verified_from_rgb") is True)
            if rgb_verified:
                uci = move.get("uci")
                if not isinstance(uci, str) or not uci:
                    raise ValueError(f"RGB-verified player move lacks semantic UCI identity at slot {slot}")
                reconstructed_history.append(uci)
            if reply.get("verified_from_rgb") is True:
                uci = reply.get("uci")
                if not isinstance(uci, str) or not uci:
                    raise ValueError(f"RGB-verified Atari reply lacks semantic UCI identity at slot {slot}")
                reconstructed_history.append(uci)
        if attempted != terminal.get("player_moves_attempted") or verified != terminal.get("verified_player_moves"):
            raise ValueError(f"move numerator/denominator does not reconstruct from turn evidence at slot {slot}")
        if replies != terminal.get("verified_atari_replies"):
            raise ValueError(f"verified reply count does not reconstruct from turns at slot {slot}")
        if reconstructed_history != record.get("verified_move_history"):
            raise ValueError(f"verified move history differs from independently reconstructed RGB turns at slot {slot}")
        if trace.get("final_position", {}).get("shadow_fen") != terminal.get("last_verified_fen"):
            raise ValueError(f"last verified FEN differs from the trace's retained shadow position at slot {slot}")
        if (attempted, verified, replies) != (
            record.get("player_moves_attempted"), record.get("rgb_verified_player_moves"), record.get("verified_atari_replies")
        ):
            raise ValueError(f"recorded move/reply totals differ from raw turn evidence at slot {slot}")
        if decision_count != attempted or record.get("policy_choose_move_latencies_seconds") != choose_latencies:
            raise ValueError(f"policy inference count or chooser latencies differ from raw decisions at slot {slot}")

        pending = attempted - verified
        pending_category = terminal.get("incomplete_final_move_category")
        if pending != terminal.get("incomplete_final_move_count") or pending != record.get("incomplete_final_move_count"):
            raise ValueError(f"pending final-move count disagrees with raw trace at slot {slot}")
        if pending_category != record.get("incomplete_final_move_category"):
            raise ValueError(f"pending final-move category differs between trace and record at slot {slot}")
        if pending not in {0, 1} or (pending == 1 and not isinstance(pending_category, str)):
            raise ValueError(f"invalid pending final-move accounting at slot {slot}")
        if pending == 1:
            censor_counts[pending_category] += 1
        elif pending_category is not None:
            raise ValueError(f"completed move unexpectedly has a censor category at slot {slot}")

        diag = terminal.get("cursor_diagnostics")
        if not isinstance(diag, dict) or record.get("cursor_diagnostics") != diag:
            raise ValueError(f"cursor diagnostics differ between trace and record at slot {slot}")
        if record.get("unexpected_cursor_displacements") != diag.get("unexpected_displacements"):
            raise ValueError(f"cursor displacement count mismatch at slot {slot}")
        raw_displacements = terminal.get("unexpected_directional_displacements")
        derived_desynchronizations = (
            None if raw_displacements is None
            else int(terminal.get("runner_stop_category") == "CONTROLLER_BOARD_DESYNCHRONIZED")
        )
        if record.get("desynchronization_count") != derived_desynchronizations:
            raise ValueError(f"board desynchronization count mismatch at slot {slot}")
        if (int(diag.get("unexpected_displacements_corrected", -1))
                + int(diag.get("unexpected_displacements_unresolved", -1))
                != int(diag.get("unexpected_displacements", -2))):
            raise ValueError(f"cursor correction counts do not partition unexpected displacements at slot {slot}")

        action_count = raw["action_counts"][attempt_id]
        observed_count = action_count.get("ale_action_observed", 0)
        started_count = action_count.get("ale_action_started", 0)
        if started_count != observed_count or action_count.get("ale_action_failed", 0) != 0:
            raise ValueError(f"ALE action start/result accounting is incomplete at slot {slot}")
        if observed_count != terminal.get("environment_steps") or observed_count != record.get("environment_steps"):
            raise ValueError(f"environment step count differs from raw ALE action events at slot {slot}")
        last_action = raw["last_observed"].get(attempt_id)
        if not isinstance(last_action, dict) or last_action.get("frame_number") != terminal.get("frame_number"):
            raise ValueError(f"last raw ALE action frame does not match trace terminal frame at slot {slot}")
        if last_action.get("terminated") is not terminal.get("ale_terminated") or last_action.get("truncated") is not terminal.get("ale_truncated"):
            raise ValueError(f"last raw ALE action flags differ from trace at slot {slot}")
        reset_origin = reset.get("frame_number")
        if (reset_origin != trace.get("reset", {}).get("frame_number")
                or reset_origin != record.get("reset_frame_number")
                or reset_origin != config["ale_horizon"]["frame_counter_reset_offset_expected"]):
            raise ValueError(f"reset frame counter origin differs across evidence at slot {slot}")
        if (trace.get("reset", {}).get("rgb_sha256") != reset.get("rgb_sha256")
                or trace.get("reset", {}).get("rgb_shape") != reset.get("rgb_shape")):
            raise ValueError(f"episode trace reset RGB identity differs from the raw reset event at slot {slot}")
        post_reset_frames = int(terminal.get("frame_number")) - int(reset_origin)
        if post_reset_frames != record.get("post_reset_action_frames") or post_reset_frames != terminal.get("post_reset_action_frames"):
            raise ValueError(f"post-reset frame accounting differs at slot {slot}")
        if post_reset_frames > config["episode_limits"]["maximum_ale_frames"]:
            raise ValueError(f"post-reset frames exceeded v2 runner cap at slot {slot}")
        if terminal.get("ale_frames") != terminal.get("frame_number") or terminal.get("ale_frames") != record.get("ale_frames"):
            raise ValueError(f"ALE frame counter differs from attempt record at slot {slot}")
        if int(record.get("maximum_player_moves", 0)) != config["episode_limits"]["maximum_player_moves"]:
            raise ValueError(f"player move cap mismatch at slot {slot}")
        if attempted > config["episode_limits"]["maximum_player_moves"]:
            raise ValueError(f"attempted player moves exceeded the frozen cap at slot {slot}")
        wall = record.get("wall_seconds")
        if not finite_number(wall) or wall < 0 or wall > config["episode_limits"]["maximum_wall_seconds"]:
            raise ValueError(f"per-attempt wall budget violated at slot {slot}")
        if record.get("retries") != 0:
            raise ValueError(f"attempt was retried or replaced at slot {slot}")
        for turn in turns:
            reply = turn.get("opponent_reply") or {}
            waited = reply.get("frames_waited")
            if waited is not None and (isinstance(waited, bool) or not isinstance(waited, int) or waited > config["episode_limits"]["maximum_opponent_wait_frames"]):
                raise ValueError(f"opponent reply wait exceeded the frozen cap at slot {slot}")

        if pending and pending_category in {"source_selection_uncertainty", "target_navigation_uncertainty"}:
            final_turn = turns[-1]
            phases = final_turn.get("input_phases", [])
            phase_names = [phase.get("phase") for phase in phases if isinstance(phase, dict)]
            turn_start = next((phase.get("frame_number") for phase in phases
                               if phase.get("phase") == "player_turn_verified"), None)
            if not isinstance(turn_start, int):
                raise ValueError(f"uncertain controller stop lacks a verified-turn boundary at slot {slot}")
            final_actions = [action for action in trace.get("actions", [])
                             if int(action.get("frame_number_start", -1)) >= turn_start]
            fire_actions = [action for action in final_actions if action.get("action") == "FIRE"]
            source_fires = [action for action in fire_actions if action.get("name") == "select_source"]
            target_fires = [action for action in fire_actions if action.get("name") == "select_target"]
            if len(source_fires) != 1 or target_fires:
                raise ValueError(f"uncertain controller action was repeated or target FIRE was not withheld at slot {slot}")
            if pending_category == "source_selection_uncertainty":
                if phase_names.count("source_selection_requested") != 1 or "source_selection_uncertain" not in phase_names:
                    raise ValueError(f"source uncertainty evidence is incomplete at slot {slot}")
                if any(name in phase_names for name in ("selected_target_navigation", "target_selection_requested")):
                    raise ValueError(f"controller proceeded beyond an uncertain source selection at slot {slot}")
            else:
                if "selected_target_uncertain" not in phase_names or "target_selection_requested" in phase_names:
                    raise ValueError(f"target-navigation uncertainty did not stop before target FIRE at slot {slot}")

        # The ledger stores every observed ALE step, including the terminal reward.
        # The event-derived aggregate below is computed while streaming in a second
        # compact pass to avoid retaining the 968k event records.
        # terminal reward identity is corroborated by terminal_observation and record.
        reward_value = terminal.get("ale_reward_total")
        if outcome in {"win", "loss"} and not finite_number(reward_value):
            raise ValueError(f"supported terminal outcome has nonfinite reward at slot {slot}")
        if outcome == "loss" and not float(reward_value) < 0:
            raise ValueError(f"loss classification lacks a negative reward at slot {slot}")
        if outcome == "win" and not float(reward_value) > 0:
            raise ValueError(f"win classification lacks a positive reward at slot {slot}")
        if record.get("agent_reward") != terminal.get("agent_reward_total"):
            raise ValueError(f"agent reward total differs from raw terminal trace at slot {slot}")
        if manifest.get("agent_color") != "white" or trace.get("player_color") != "white" or record.get("agent_color") != "white":
            raise ValueError(f"reward perspective/player color differs from frozen White profile at slot {slot}")
        reward_result = terminal.get("white_result_from_reward")
        if outcome == "loss" and reward_result != "white_loss":
            raise ValueError(f"terminal loss is not independently identified from White-perspective reward at slot {slot}")
        if outcome == "win" and reward_result != "white_win":
            raise ValueError(f"terminal win is not independently identified from White-perspective reward at slot {slot}")

        terminal_observation = trace.get("terminal_observation") or {}
        frame_artifact = terminal_observation.get("frame_artifact")
        terminal_frame_path = None
        terminal_frame_sha256 = None
        terminal_rgb_sha256 = terminal_observation.get("rgb_sha256")
        if isinstance(frame_artifact, dict):
            terminal_frame_path, terminal_frame_rel = repo_relative_artifact(root, RUN_ID, frame_artifact.get("path"))
            frame_row = file_rows.get(terminal_frame_rel)
            if frame_row is None or not isinstance(frame_artifact.get("rgb_sha256"), str):
                raise ValueError(f"terminal RGB frame artifact is not present in the verified file manifest at slot {slot}")
            terminal_frame_sha256 = frame_row["sha256"]
            if (frame_artifact.get("rgb_sha256") != terminal_observation.get("rgb_sha256")
                    or frame_artifact.get("frame_number") != terminal_observation.get("frame_number")):
                raise ValueError(f"terminal PNG reference is not bound to the ALE observation RGB hash at slot {slot}")
            pre_terminal = terminal_observation.get("pre_terminal_frame")
            if isinstance(pre_terminal, dict) and isinstance(pre_terminal.get("frame_artifact"), dict):
                _, pre_terminal_rel = repo_relative_artifact(
                    root, RUN_ID, pre_terminal["frame_artifact"].get("path")
                )
                pre_terminal_row = file_rows.get(pre_terminal_rel)
                if (pre_terminal_row is None
                        or pre_terminal["frame_artifact"].get("rgb_sha256") != pre_terminal.get("rgb_sha256")
                        or pre_terminal["frame_artifact"].get("frame_number") != pre_terminal.get("frame_number")):
                    raise ValueError(f"pre-terminal PNG reference is not bound to the ALE observation RGB hash at slot {slot}")
        if terminal.get("ale_terminated") is True:
            if terminal.get("ale_truncated") is not False or not isinstance(frame_artifact, dict):
                raise ValueError(f"ALE terminal lacks a terminal RGB artifact or has truncation at slot {slot}")
            if terminal_observation.get("terminated") is not True or terminal_observation.get("truncated") is not False:
                raise ValueError(f"terminal observation flags unsupported at slot {slot}")
            if (terminal_observation.get("reward") != reward_value
                    or terminal_observation.get("rgb_sha256") != last_action.get("rgb_sha256")
                    or frame_artifact.get("rgb_sha256") != terminal_observation.get("rgb_sha256")):
                raise ValueError(f"terminal observation reward/RGB differs from ALE event at slot {slot}")
            if pending_category != "ale_terminal" or pending != 1:
                raise ValueError(f"terminal final move censor category invalid at slot {slot}")
        elif pending and pending_category not in {
            "opponent_response_timeout", "source_selection_uncertainty", "target_navigation_uncertainty",
            "target_confirmation_uncertainty", "board_desynchronization", "frame_cap", "wall_clock_cap",
            "artifact_cap", "ale_truncation", "other_interrupted_or_unknown",
        }:
            raise ValueError(f"unsupported incomplete final-move censor category at slot {slot}")

        policy = expected["policy_id"]
        policy_totals = totals[policy]
        policy_totals["attempts"] += 1
        policy_totals[outcome] += 1
        policy_totals["policy_decisions"] += decision_count
        policy_totals["initiated_moves"] += attempted
        policy_totals["verified_moves"] += verified
        policy_totals["verified_replies"] += replies
        policy_totals["cursor_displacements"] += int(diag["unexpected_displacements"])
        policy_totals["cursor_displacements_corrected"] += int(diag["unexpected_displacements_corrected"])
        policy_totals["desynchronizations"] += int(record["desynchronization_count"])
        policy_totals["environment_steps"] += observed_count
        policy_totals["ale_counter_frames"] += int(record["ale_frames"])
        policy_totals["post_reset_action_frames"] += post_reset_frames
        policy_totals["wall_seconds_millis"] += round(float(wall) * 1000)
        policy_totals["peak_rss_bytes_max"] = max(policy_totals["peak_rss_bytes_max"], int(record["peak_rss_bytes"]))
        all_totals["initiated_moves"] += attempted
        all_totals["verified_moves"] += verified
        all_totals["verified_replies"] += replies
        all_totals["cursor_displacements"] += int(diag["unexpected_displacements"])
        all_totals["cursor_displacements_corrected"] += int(diag["unexpected_displacements_corrected"])
        all_totals["cursor_displacements_unresolved"] += int(diag["unexpected_displacements_unresolved"])
        all_totals["ambiguous_or_unlocated_observations"] += int(diag["ambiguous_or_unlocated_observations"])
        all_totals["repeated_movement_without_progress"] += int(diag["repeated_movement_without_progress"])
        all_totals["stable_board_disagreements"] += int(diag["stable_board_disagreements"])
        all_totals["desynchronizations"] += int(record["desynchronization_count"])
        all_totals["environment_steps"] += observed_count
        all_totals["ale_counter_frames"] += int(record["ale_frames"])
        all_totals["post_reset_action_frames"] += post_reset_frames
        all_totals["wall_seconds_millis"] += round(float(wall) * 1000)
        all_totals["peak_rss_bytes_max"] = max(all_totals["peak_rss_bytes_max"], int(record["peak_rss_bytes"]))
        all_totals["attempts"] += 1
        all_totals["policy_decisions"] += decision_count
        all_totals[outcome] += 1
        stop = record.get("terminal_or_stop_reason", record.get("runner_stop_category"))
        stop_counts[str(stop)] += 1
        if pending_category in {"source_selection_uncertainty", "target_navigation_uncertainty"}:
            safe_stop_check = "one source FIRE; target FIRE withheld; no retry"
        elif pending_category == "opponent_response_timeout":
            safe_stop_check = "last player move RGB-verified; no reply retry or attempt replacement"
        elif terminal.get("ale_terminated") is True:
            safe_stop_check = "ALE terminal stopped action loop; no post-terminal ALE action"
        else:
            safe_stop_check = "no action retry or attempt replacement recorded"
        attempts.append({
            "slot": slot,
            "attempt_id": attempt_id,
            "game_id": game_id,
            "policy_id": policy,
            "ale_seed": expected["ale_seed"],
            "reset_observed": True,
            "outcome": outcome,
            "ale_terminated": terminal.get("ale_terminated"),
            "ale_truncated": terminal.get("ale_truncated"),
            "raw_terminal_reward_white": reward_value,
            "stop_category": record.get("runner_stop_category"),
            "stop_reason": record.get("stop_reason"),
            "last_verified_fen": terminal.get("last_verified_fen"),
            "verified_move_history": list(record.get("verified_move_history", [])),
            "initiated_moves": attempted,
            "policy_decision_count": decision_count,
            "rgb_verified_moves": verified,
            "verified_atari_replies": replies,
            "pending_final_move_count": pending,
            "pending_final_move_category": pending_category,
            "cursor_displacements": diag["unexpected_displacements"],
            "cursor_displacements_corrected": diag["unexpected_displacements_corrected"],
            "cursor_displacements_unresolved": diag["unexpected_displacements_unresolved"],
            "ambiguous_or_unlocated_observations": diag["ambiguous_or_unlocated_observations"],
            "board_desynchronizations": record["desynchronization_count"],
            "reset_frame_counter_origin": reset_origin,
            "final_ale_frame_counter": terminal.get("frame_number"),
            "post_reset_action_frames": post_reset_frames,
            "environment_steps": observed_count,
            "wall_seconds": wall,
            "peak_rss_bytes": record.get("peak_rss_bytes"),
            "ale_action_start_events": started_count,
            "ale_action_observed_events": observed_count,
            "terminal_frame_path": terminal_frame_rel if terminal_frame_path else None,
            "terminal_frame_file_sha256": terminal_frame_sha256,
            "terminal_rgb_bytes_sha256": terminal_rgb_sha256,
            "trace_path": record.get("trace_path"),
            "attempt_manifest_sha256": record["artifact_manifest_sha256"],
            "attempt_manifest_path": record.get("artifact_manifest_path"),
            "trace_sha256": record["trace_sha256"],
            "trace_chain_head_sha256": trace_chain["head_sha256"],
            "controller_safe_stop_check": safe_stop_check,
        })

    # Independently sum ALE reward observations directly from the raw ledger.
    rewards_by_attempt: dict[str, float] = defaultdict(float)
    with (root / "events.jsonl").open("rb") as stream:
        for line in stream:
            event = json.loads(line)
            if event.get("event_type") != "ale_action_observed":
                continue
            payload = event["payload"]
            attempt_id = payload["attempt_id"]
            reward = payload.get("reward")
            if not finite_number(reward):
                raise ValueError(f"nonfinite or unsupported per-step reward in raw ledger: {attempt_id}")
            rewards_by_attempt[attempt_id] += float(reward)
    for row in attempts:
        record = raw["finished"][row["attempt_id"]]
        trace_path, _ = repo_relative_artifact(root, RUN_ID, record["trace_path"])
        episode = json.loads(trace_path.read_text(encoding="utf-8"))["episode"]
        expected_reward = episode["terminal"].get("ale_reward_total")
        if not finite_number(expected_reward) or not math.isclose(rewards_by_attempt[row["attempt_id"]], float(expected_reward), abs_tol=1e-9):
            raise ValueError(f"per-step ALE reward sum differs from terminal trace for {row['attempt_id']}")

    if seen_reset_games != set(expected_by_game):
        raise ValueError("not every schedule slot has exactly one distinct reset")
    if len(attempts) != 20 or len({row["attempt_id"] for row in attempts}) != 20:
        raise ValueError("v2 attempt identities are incomplete or duplicated")
    if all_totals["attempts"] != 20 or all_totals["loss"] != 11 or all_totals["incomplete"] != 9:
        raise ValueError("independently reconstructed high-level outcomes differ from the expected historical record")
    if all_totals["initiated_moves"] != 405 or all_totals["verified_moves"] != 385 or all_totals["verified_replies"] != 385:
        raise ValueError("independently reconstructed move/reply counts differ from the retained traces")
    if all_totals["cursor_displacements"] != 1_871 or all_totals["desynchronizations"] != 0:
        raise ValueError("independently reconstructed cursor/desynchronization counts differ from raw traces")
    if sum(row["pending_final_move_count"] for row in attempts) != 20:
        raise ValueError("each scheduled attempt must account for its pending final move exactly once")

    # The historical value is an explicit discrepancy, not a reason to mutate or
    # reject otherwise intact immutable experiment bytes.
    budget = manifest.get("budget", {})
    review_manifest_path = repo_root / ".agents/evidence/M6-stage3-v2-run-manifest-review-20261031.json"
    review_manifest_sha = sha256_file(review_manifest_path)
    review_manifest = json.loads(review_manifest_path.read_text(encoding="utf-8"))
    if review_manifest.get("raw_run_manifest_sha256") != manifest_sha:
        raise ValueError("sanitized review manifest does not bind the original raw manifest identity")
    review_budget = review_manifest.get("budget", {})
    if review_budget.get("gameplay_wall_budget_includes_diagnostics") is not True:
        raise ValueError("sanitized review copy does not reproduce the PM6-F06 field")
    if review_manifest.get("campaign_wall_budget_scope") != config["campaign_limits"]["gameplay_wall_budget_scope"]:
        raise ValueError("sanitized review copy scope differs from the frozen v2 configuration")
    execution_record_path = repo_root / ".agents/evidence/M6-stage3-v2-execution-record-20261031.json"
    execution_record_sha = sha256_file(execution_record_path)
    execution_record = json.loads(execution_record_path.read_text(encoding="utf-8"))
    if (execution_record.get("integrity", {}).get("raw_run_manifest_sha256") != manifest_sha
            or execution_record.get("resource_limits", {}).get("gameplay_wall_budget_includes_diagnostics") is not True):
        raise ValueError("sanitized execution record does not reproduce the PM6-F06 discrepancy")
    historical_scope_issue = {
        "finding_id": "PM6-F06",
        "historical_field": "budget.gameplay_wall_budget_includes_diagnostics",
        "historical_value": budget.get("gameplay_wall_budget_includes_diagnostics"),
        "authoritative_scope": config["campaign_limits"]["gameplay_wall_budget_scope"],
        "expected_boolean": False,
        "status": "historical_manifest_inconsistency_preserved_and_erratum_required",
        "raw_manifest_sha256": manifest_sha,
        "sanitized_review_copy_path": ".agents/evidence/M6-stage3-v2-run-manifest-review-20261031.json",
        "sanitized_review_copy_sha256": review_manifest_sha,
        "sanitized_review_copy_value": review_budget.get("gameplay_wall_budget_includes_diagnostics"),
        "execution_record_path": ".agents/evidence/M6-stage3-v2-execution-record-20261031.json",
        "execution_record_sha256": execution_record_sha,
        "execution_record_value": execution_record["resource_limits"]["gameplay_wall_budget_includes_diagnostics"],
    }
    if budget.get("gameplay_wall_budget_includes_diagnostics") is not True:
        raise ValueError("expected PM6-F06 historical metadata discrepancy was not reproduced")
    if manifest.get("campaign_wall_budget_scope") != historical_scope_issue["authoritative_scope"]:
        raise ValueError("v2 run-manifest textual budget scope differs from frozen config")

    expected_summary = {
        "attempted_reset_count": 20,
        "reset_game_count": 20,
        "scheduled_game_count": 20,
        "unexecuted_game_ids": [],
        "schedule_accounting_complete": True,
        "ledger_event_count": ledger["event_count"],
        "ledger_head_sha256": ledger["head_sha256"],
        "ledger_sha256": ledger["sha256"],
    }
    for key, value in expected_summary.items():
        if summary.get(key) != value:
            raise ValueError(f"generated summary disagrees with raw evidence for {key}")
    summary_by_id = {row.get("attempt_id"): row for row in summary.get("all_attempts", [])}
    if len(summary_by_id) != 20:
        raise ValueError("summary does not contain all 20 reset attempts")
    for row in attempts:
        old = summary_by_id.get(row["attempt_id"])
        if not old or any(old.get(key) != value for key, value in {
            "outcome": row["outcome"],
            "ale_terminated": row["ale_terminated"],
            "ale_truncated": row["ale_truncated"],
            "player_moves_attempted": row["initiated_moves"],
            "rgb_verified_player_moves": row["rgb_verified_moves"],
            "verified_atari_replies": row["verified_atari_replies"],
            "incomplete_final_move_count": row["pending_final_move_count"],
            "incomplete_final_move_category": row["pending_final_move_category"],
            "unexpected_cursor_displacements": row["cursor_displacements"],
            "desynchronization_count": row["board_desynchronizations"],
        }.items()):
            raise ValueError(f"summary differs from independently reconstructed trace: {row['attempt_id']}")

    policy_report = {}
    for policy_id, counts in totals.items():
        attempts_for_policy = [row for row in attempts if row["policy_id"] == policy_id]
        if counts["attempts"] != 10:
            raise ValueError(f"policy schedule count is not ten for {policy_id}")
        if sum(row["initiated_moves"] for row in attempts_for_policy) != counts["initiated_moves"]:
            raise ValueError(f"per-policy move subtotal mismatch for {policy_id}")
        policy_report[policy_id] = {
            **dict(counts),
            "wall_seconds": counts["wall_seconds_millis"] / 1000,
            "rgb_verified_move_rate": counts["verified_moves"] / counts["initiated_moves"] if counts["initiated_moves"] else None,
            "stop_reasons": dict(sorted(Counter(row["stop_reason"] or row["stop_category"] for row in attempts_for_policy).items())),
            "policy_decision_latency_seconds": {
                metric: latency_summary(values)
                for metric, values in policy_latencies[policy_id].items()
            },
        }
        policy_report[policy_id].pop("wall_seconds_millis", None)

    campaign_seconds = all_totals["wall_seconds_millis"] / 1000
    if campaign_seconds > config["campaign_limits"]["maximum_gameplay_wall_seconds"]:
        raise ValueError("v2 cumulative gameplay wall budget exceeded")
    if artifact_tree["total_bytes"] > config["campaign_limits"]["maximum_artifact_bytes"]:
        raise ValueError("v2 retained artifact ceiling exceeded")
    if all_totals["peak_rss_bytes_max"] > config["campaign_limits"]["maximum_process_rss_bytes"]:
        raise ValueError("v2 peak process RSS ceiling exceeded")

    return {
        "schema": "videochess-m6-independent-raw-audit/1.0",
        "run_id": RUN_ID,
        "raw_root": portable_artifact_root(root),
        "identities": {
            "execution_source_commit": manifest["git_commit"],
            "execution_source_tree": manifest["git_tree"],
            "configuration_sha256": config_sha,
            "schedule_sha256": schedule_sha,
            "m5_root_artifact_manifest_sha256": manifest["m5_root_manifest_sha256"],
            "warm_checkpoint_sha256": CHECKPOINTS[WARM_ID][0],
            "warm_sidecar_sha256": CHECKPOINTS[WARM_ID][1],
            "scratch_checkpoint_sha256": CHECKPOINTS[SCRATCH_ID][0],
            "scratch_sidecar_sha256": CHECKPOINTS[SCRATCH_ID][1],
            "rom_sha256_recorded_by_runtime": manifest["rom_sha256"],
            "dependency_lock_sha256": manifest.get("dependency_lock_sha256"),
            "source_bundle_sha256": manifest.get("source_bundle_sha256"),
        },
        "integrity": {
            "raw_run_manifest_sha256": manifest_sha,
            "artifact_manifest": artifact_tree,
            "ledger": ledger,
            "per_attempt_manifests_validated": len(attempts),
            "episode_traces_validated": len(attempts),
            "trace_hash_chains_validated": len(attempts),
            "attempt_json_matches_ledger": len(attempts),
            "symlinks_or_unsafe_paths": 0,
            "missing_or_unexpected_artifacts": 0,
        },
        "protocol": {
            "environment_id": manifest.get("environment_id"),
            "agent_color": manifest.get("agent_color"),
            "mode": manifest.get("ale_config", {}).get("mode"),
            "difficulty": manifest.get("ale_config", {}).get("difficulty"),
            "observation_type": manifest.get("ale_config", {}).get("obs_type"),
            "frameskip": manifest.get("ale_config", {}).get("frameskip"),
            "repeat_action_probability": manifest.get("ale_config", {}).get("repeat_action_probability"),
            "underlying_ale_frame_limit": manifest.get("runtime_construction", {}).get("ale_episode_frame_limit"),
            "runner_max_post_reset_frames": config["episode_limits"]["maximum_ale_frames"],
            "per_attempt_wall_limit_seconds": config["episode_limits"]["maximum_wall_seconds"],
            "campaign_wall_limit_seconds": config["campaign_limits"]["maximum_gameplay_wall_seconds"],
            "maximum_player_moves": config["episode_limits"]["maximum_player_moves"],
            "maximum_opponent_wait_frames": config["episode_limits"]["maximum_opponent_wait_frames"],
        },
        "reconstructed": {
            "scheduled_attempts": len(schedule),
            "recorded_resets": len(raw["resets"]),
            "attempts_by_policy": policy_report,
            "outcomes": {
                "ale_terminated_wins": all_totals["win"],
                "ale_terminated_draws": all_totals["draw"],
                "ale_terminated_losses": all_totals["loss"],
                "terminal_unknown": all_totals["terminal_unknown"],
                "ale_truncated": all_totals["ale_truncated"],
                "runner_truncated": all_totals["runner_truncated"],
                "incomplete": all_totals["incomplete"],
                "incomplete_not_draws": True,
            },
            "initiated_player_moves": all_totals["initiated_moves"],
            "policy_decisions": all_totals["policy_decisions"],
            "rgb_verified_player_moves": all_totals["verified_moves"],
            "verified_atari_replies": all_totals["verified_replies"],
            "primary_move_rate": all_totals["verified_moves"] / all_totals["initiated_moves"],
            "pending_final_moves": sum(row["pending_final_move_count"] for row in attempts),
            "pending_final_moves_by_category": dict(sorted(censor_counts.items())),
            "stop_reason_counts": dict(sorted(stop_counts.items())),
            "cursor_displacements": all_totals["cursor_displacements"],
            "cursor_displacements_corrected": all_totals["cursor_displacements_corrected"],
            "cursor_displacements_unresolved": all_totals["cursor_displacements_unresolved"],
            "ambiguous_or_unlocated_observations": all_totals["ambiguous_or_unlocated_observations"],
            "repeated_movement_without_progress": all_totals["repeated_movement_without_progress"],
            "stable_board_disagreements": all_totals["stable_board_disagreements"],
            "board_desynchronizations": all_totals["desynchronizations"],
            "ale_counter_frames": all_totals["ale_counter_frames"],
            "post_reset_action_frames": all_totals["post_reset_action_frames"],
            "environment_steps": all_totals["environment_steps"],
            "gameplay_wall_seconds": campaign_seconds,
            "maximum_attempt_peak_rss_bytes": all_totals["peak_rss_bytes_max"],
            "resource_stops": ledger["event_counts"].get("resource_stop", 0),
            "startup_retries": ledger["event_counts"].get("process_start_retry", 0),
        },
        "per_attempt": attempts,
        "known_historical_discrepancy": historical_scope_issue,
        "budget_enforcement_cross_check": {
            "configured_wall_limit_seconds": config["campaign_limits"]["maximum_gameplay_wall_seconds"],
            "recorded_wall_limit_seconds": budget.get("gameplay_wall_seconds_total"),
            "recorded_wall_used_before_campaign_seconds": manifest.get("campaign_wall_seconds_used_before"),
            "observed_v2_gameplay_seconds": campaign_seconds,
            "diagnostics_excluded_by_frozen_scope": True,
            "original_manifest_metadata_flag_is_incorrect": True,
            "resource_stop_events": ledger["event_counts"].get("resource_stop", 0),
        },
        "limitations": [
            "ROM identity is verified from the immutable run-time record; this audit does not launch or reset ALE.",
            "Raw artifacts are local-only; the report contains hashes and summaries, not private RGB or checkpoint bytes.",
            "Wilson intervals are descriptive because moves within each game are correlated.",
        ],
        "discrepancies": [historical_scope_issue],
        "disposition": "PASS_WITH_IMMUTABLE_PM6_F06_ERRATUM_REQUIRED",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True, help="original local v2 raw artifact run directory")
    parser.add_argument("--repo-root", default=Path(__file__).resolve().parents[1], type=Path)
    parser.add_argument("--v1-root", type=Path, help="optional original v1 raw run directory to verify read-only")
    parser.add_argument("--output", type=Path, help="new JSON report path; existing output is never overwritten")
    args = parser.parse_args(argv)
    started = utc_now()
    repo_root = Path(args.repo_root).resolve(strict=True)
    source_revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo_root, text=True).strip()
    try:
        report = audit_v2(args.root, repo_root)
        v1 = audit_v1(args.v1_root, repo_root) if args.v1_root else None
        report["audit"] = {
            "command": "python3 scripts/audit_m6_v2_artifacts.py --root <v2-raw-root> --repo-root <repo-root> [--v1-root <v1-raw-root>]",
            "audit_source_revision": source_revision,
            "audit_source_sha256": sha256_file(Path(__file__).resolve()),
            "python_version": platform.python_version(),
            "started_at_utc": started,
            "completed_at_utc": utc_now(),
            "read_only": True,
            "v1_integrity_check": v1,
        }
        encoded = json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n"
        if args.output:
            output = args.output.expanduser()
            resolved_root = checked_root(args.root)
            resolved_output = output.resolve(strict=False)
            if resolved_output == resolved_root or resolved_root in resolved_output.parents:
                raise ValueError("audit report output must be outside the immutable raw artifact root")
            if output.exists() or output.is_symlink():
                raise FileExistsError(f"refusing to overwrite audit output: {output}")
            output.parent.mkdir(parents=True, exist_ok=True)
            with output.open("x", encoding="utf-8") as stream:
                stream.write(encoded)
                stream.flush()
                os.fsync(stream.fileno())
            print(f"audit_report={output}")
            print(f"audit_report_sha256={sha256_file(output)}")
        else:
            print(encoded, end="")
        return 0
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError, subprocess.CalledProcessError) as exc:
        print(f"AUDIT_FAILED: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
