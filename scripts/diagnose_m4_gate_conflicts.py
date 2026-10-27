#!/usr/bin/env python3
"""Verify whether fixed M4 sanity samples contain indistinguishable labels."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import subprocess
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import chess
import numpy as np
import torch

from videochess_rl.model.dataset import (
    EXPECTED_COUNTS,
    EXPECTED_GAME_COUNTS,
    EXPECTED_MANIFEST_SHA256,
    EXPECTED_RELEASE_ID,
    EXPECTED_SPLIT_SHA256,
    load_m3_release,
    smallest_training_sample_ids,
)
from videochess_rl.model.features import INPUT_SCHEMA, PositionFeatures
from videochess_rl.model.network import MODEL_SCHEMA


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


def _revision() -> tuple[str | None, bool | None]:
    root = Path(__file__).resolve().parents[1]
    revision = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=root, capture_output=True, text=True, check=False,
    )
    status = subprocess.run(
        ["git", "status", "--porcelain=v1"], cwd=root, capture_output=True, text=True, check=False,
    )
    return (
        revision.stdout.strip() if revision.returncode == 0 else None,
        bool(status.stdout.strip()) if status.returncode == 0 else None,
    )


def _input_identity(row: PositionFeatures) -> tuple[str, dict[str, Any]]:
    digest = hashlib.sha256()
    arrays: dict[str, np.ndarray] = {}
    for name in (
        "board_planes",
        "state_scalars",
        "history_moves",
        "candidate_squares",
        "candidate_promotion",
        "candidate_flags",
    ):
        array = np.ascontiguousarray(getattr(row, name))
        arrays[name] = array
        digest.update(name.encode("ascii") + b"\0")
        digest.update(array.dtype.str.encode("ascii") + b"\0")
        digest.update(json.dumps(list(array.shape), separators=(",", ":")).encode("ascii") + b"\0")
        digest.update(array.tobytes())
    digest.update(json.dumps(row.candidate_uci, separators=(",", ":")).encode("ascii"))
    return digest.hexdigest(), arrays


def diagnose(gate_run: Path, release_dir: Path) -> dict[str, Any]:
    started_at = _utc_now()
    started = time.perf_counter()
    revision, dirty = _revision()
    gate_path = gate_run / "sanity_gate.json"
    run_path = gate_run / "run_manifest.json"
    gate = json.loads(gate_path.read_text(encoding="utf-8"))
    run = json.loads(run_path.read_text(encoding="utf-8"))
    if run.get("schema") != "videochess-m4-run/1.0":
        raise ValueError("gate run has an unsupported M4 run schema")
    if run.get("status") != "sanity_gate_failed" or gate.get("status") != "FAIL":
        raise ValueError("diagnostic requires the preserved failed fixed-gate run")
    if gate.get("sample_id_count") != 128 or len(gate.get("sample_ids", [])) != 128:
        raise ValueError("failed gate does not preserve exactly 128 sample IDs")

    data = load_m3_release(release_dir)
    if (
        data.release_id != EXPECTED_RELEASE_ID
        or data.manifest_sha256 != EXPECTED_MANIFEST_SHA256
        or data.split_assignment_sha256 != EXPECTED_SPLIT_SHA256
        or data.counts != EXPECTED_COUNTS
        or data.game_counts != EXPECTED_GAME_COUNTS
        or data.file_inventory.keys() != {
            "config.json", "games.jsonl", "manifest.json", "manifest.sha256",
            "positions.jsonl", "rejections.jsonl", "source_manifest.json", "split.json", "stats.json",
        }
    ):
        raise ValueError("fresh M4 loader verification did not identify the exact accepted release")
    if data.file_inventory["manifest.json"]["sha256"] != EXPECTED_MANIFEST_SHA256:
        raise ValueError("fresh M4 loader inventory has a mismatched release manifest")

    sample_ids = smallest_training_sample_ids(data.train, 128)
    if tuple(gate["sample_ids"]) != sample_ids:
        raise ValueError("preserved gate sample IDs differ from the fixed lexical 128-row selection")
    selected = {row.sample_id: row for row in data.train if row.sample_id in set(sample_ids)}
    if len(selected) != 128:
        raise ValueError("fresh release replay did not reconstruct every selected training sample")

    groups: dict[str, list[PositionFeatures]] = defaultdict(list)
    input_arrays: dict[str, dict[str, np.ndarray]] = {}
    for sample_id in sample_ids:
        row = selected[sample_id]
        identity, arrays = _input_identity(row)
        groups[identity].append(row)
        input_arrays[identity] = arrays

    conflicting: list[dict[str, Any]] = []
    maximum_correct = 0
    for identity, rows in sorted(groups.items()):
        target_counts = Counter(row.target_uci for row in rows)
        maximum_correct += max(target_counts.values())
        if len(target_counts) > 1:
            arrays = input_arrays[identity]
            # Confirm identity using exact equality as well as the digest.
            for row in rows[1:]:
                for name, reference in arrays.items():
                    if not np.array_equal(reference, getattr(row, name)):
                        raise RuntimeError("input digest collision or inconsistent feature grouping")
                if row.candidate_uci != rows[0].candidate_uci:
                    raise RuntimeError("candidate UCI identity differs inside a duplicate-input group")
            conflicting.append({
                "model_input_sha256": identity,
                "sample_count": len(rows),
                "distinct_target_count": len(target_counts),
                "targets": dict(sorted(target_counts.items())),
                "samples": [
                    {
                        "sample_id": row.sample_id,
                        "played_move_uci": row.target_uci,
                        "ply_index": row.ply_index,
                        "history_length": row.history_length,
                        "legal_candidate_count": row.candidate_count,
                        "history_moves_sha256": hashlib.sha256(
                            np.ascontiguousarray(row.history_moves).tobytes()
                        ).hexdigest(),
                    }
                    for row in sorted(rows, key=lambda item: item.sample_id)
                ],
            })

    ceiling = maximum_correct / len(sample_ids)
    final_metrics = gate.get("final") or {}
    reported = float(final_metrics.get("legal_top1_accuracy", -1.0))
    if conflicting and maximum_correct < 127 and reported > ceiling + 1e-12:
        raise ValueError("recorded gate accuracy exceeds the exact-input upper bound")
    status = "structural_conflict_blocks_threshold" if ceiling < 0.99 else "conflict_does_not_prove_blocker"

    return {
        "schema": "videochess-m4-sanity-input-conflict-diagnostic/1.0",
        "status": status,
        "result": (
            "The fixed 128-sample gate contains identical complete model inputs with contradictory played_move_uci labels; "
            "a deterministic legal top-1 policy cannot reach 99% on this sample set."
            if status == "structural_conflict_blocks_threshold"
            else "The verified conflict analysis does not establish an accuracy ceiling below the required 99%."
        ),
        "started_at_utc": started_at,
        "ended_at_utc": _utc_now(),
        "duration_seconds": time.perf_counter() - started,
        "diagnostic_git_revision": revision,
        "diagnostic_worktree_dirty_at_start": dirty,
        "source_run": {
            "run_id": run.get("run_id"),
            "source_revision": run.get("source_revision"),
            "source_worktree_dirty": run.get("source_worktree_dirty"),
            "artifact_directory": str(gate_run.resolve()),
            "gate_status": gate.get("status"),
            "gate_seed": gate.get("seed"),
            "gate_updates": gate.get("updates"),
            "gate_duration_seconds": gate.get("duration_seconds"),
            "gate_final_metrics": final_metrics,
            "gate_thresholds": gate.get("thresholds"),
            "selected_sample_id_sha256": gate.get("sample_ids_sha256"),
        },
        "dataset": {
            "release_path": str(release_dir.resolve()),
            "release_id": data.release_id,
            "manifest_sha256": data.manifest_sha256,
            "split_assignment_sha256": data.split_assignment_sha256,
            "position_counts": data.counts,
            "game_counts": data.game_counts,
            "file_inventory": data.file_inventory,
            "post_load_release_files_unchanged": True,
            "verification_seconds": data.verification_seconds,
            "replay_tensorization_seconds": data.replay_seconds,
            "loader_total_seconds": data.total_load_seconds,
        },
        "model_contract": {
            "input_schema": INPUT_SCHEMA,
            "model_schema": MODEL_SCHEMA,
            "identity_fields": [
                "board_planes", "state_scalars", "history_moves", "candidate_squares",
                "candidate_promotion", "candidate_flags", "candidate_uci",
            ],
            "target_excluded_from_identity": True,
        },
        "fixed_sample": {
            "count": len(sample_ids),
            "lexically_smallest_training_ids": list(sample_ids),
            "same_ids_as_failed_gate": True,
            "conflicting_identical_input_groups": conflicting,
            "group_count_with_conflicting_targets": len(conflicting),
            "maximum_deterministic_top1_correct_count": maximum_correct,
            "maximum_deterministic_top1_accuracy": ceiling,
            "minimum_error_count_from_input_collisions": len(sample_ids) - maximum_correct,
            "required_top1_accuracy": 0.99,
            "required_correct_count": 127,
            "recorded_gate_top1_accuracy": reported,
        },
        "environment": {
            "python": sys.version,
            "python_executable": sys.executable,
            "torch": torch.__version__,
            "python_chess": chess.__version__,
            "numpy": np.__version__,
            "platform": platform.platform(),
            "stockfish_on_path": shutil_which_stockfish(),
        },
        "resource_measurements": {
            "peak_rss_bytes": _peak_rss_bytes(),
        },
        "scope": "read-only data/feature diagnosis; no model training or data mutation performed",
    }


def _peak_rss_bytes() -> int:
    import resource

    value = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return int(value if sys.platform == "darwin" else value * 1024)


def shutil_which_stockfish() -> str | None:
    import shutil

    return shutil.which("stockfish")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--gate-run", type=Path, required=True)
    parser.add_argument("--release-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = diagnose(args.gate_run, args.release_dir)
    report["command"] = [sys.executable, str(Path(__file__).resolve()), *sys.argv[1:]]
    encoded = json.dumps(report, sort_keys=True, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded, encoding="utf-8")
    print(encoded, end="")
    return 0 if report["status"] == "structural_conflict_blocks_threshold" else 1


if __name__ == "__main__":
    raise SystemExit(main())
