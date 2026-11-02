#!/usr/bin/env python3
"""Bounded M5 recurrent-update probe at the observed M4 history range.

This is a CPU feasibility measurement only. It performs a handful of synthetic
Double DQN updates with a batch of 32 history lengths spanning zero through the
maximum history observed in a separately verified 40-game M4 workload profile.
It neither reconstructs semantic chess transitions nor trains a policy.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import platform
import random
import resource
import signal
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import torch
import torch.nn.functional as F

from videochess_rl.model.checkpoint import load_checkpoint, verify_artifact_manifest
from videochess_rl.model.network import initialize_q_head

EXPECTED_CHECKPOINT_SHA256 = "724ac730f3c5f2d01b48b26eb7670a3c764978a3dd4d6702b3057a99ab1a90a4"
EXPECTED_RELEASE_ID = "f10a679deddf06f3e1e3c39cf58db4e21176629c26c09034a271bf278189e890"
EXPECTED_SPLIT_SHA256 = "84efed824e57de45c0058b73818bb7a9d740201ead38e9171308cee43bc0934e"
RSS_CAP_BYTES = 2 * 1024**3
MAX_PROFILE_SECONDS = 120.0
TRAINING_DECISIONS = 10_000
UPDATES_AFTER_WARMUP = ((TRAINING_DECISIONS - 512) // 4) + 1


class ProfileLimit(RuntimeError):
    pass


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def deadline_handler(signum: int, frame: Any) -> None:
    del signum, frame
    raise ProfileLimit("history budget profile reached the 120-second hard cap")


def make_synthetic_batch(max_history_plies: int, candidate_count: int) -> tuple[dict[str, Any], tuple[int, ...]]:
    lengths = tuple(round(i * max_history_plies / 31) for i in range(32))
    board_planes = torch.zeros((32, 13, 8, 8), dtype=torch.float32)
    state_scalars = torch.zeros((32, 6), dtype=torch.float32)
    history_moves = torch.zeros((32, max_history_plies, 4), dtype=torch.int64)
    history_mask = torch.zeros((32, max_history_plies), dtype=torch.bool)
    for index, length in enumerate(lengths):
        if length:
            history_moves[index, :length, 0] = 0
            history_moves[index, :length, 1] = 1
            history_mask[index, :length] = True
    candidate_squares = torch.zeros((32, candidate_count, 2), dtype=torch.int64)
    candidate_squares[:, :, 1] = 1
    candidate_promotion = torch.zeros((32, candidate_count), dtype=torch.int64)
    candidate_flags = torch.zeros((32, candidate_count, 4), dtype=torch.float32)
    candidate_mask = torch.ones((32, candidate_count), dtype=torch.bool)
    return {
        "board_planes": board_planes,
        "state_scalars": state_scalars,
        "history_moves": history_moves,
        "history_mask": history_mask,
        "candidate_squares": candidate_squares,
        "candidate_promotion": candidate_promotion,
        "candidate_flags": candidate_flags,
        "candidate_mask": candidate_mask,
    }, lengths


def run(checkpoint: Path, reference_profile: Path, max_seconds: float) -> dict[str, Any]:
    started_wall = datetime.now(timezone.utc).isoformat()
    started = time.monotonic()
    deadline = started + max_seconds
    signal.signal(signal.SIGALRM, deadline_handler)
    signal.setitimer(signal.ITIMER_REAL, max_seconds)

    checkpoint = checkpoint.expanduser().resolve(strict=True)
    reference_profile = reference_profile.expanduser().resolve(strict=True)
    checkpoint_hash = sha256(checkpoint)
    if checkpoint_hash != EXPECTED_CHECKPOINT_SHA256:
        raise ValueError("accepted M4 checkpoint SHA-256 differs")
    artifact_manifest = verify_artifact_manifest(checkpoint.parent)
    if len(artifact_manifest["files"]) != 19:
        raise ValueError("accepted M4 bundle does not contain the expected 19 verified files")
    reference_bytes = reference_profile.read_bytes()
    reference = json.loads(reference_bytes)
    if reference.get("schema") != "videochess-pre-m5-feasibility-profile/2.1":
        raise ValueError("reference profile schema must be v2.1")
    if reference.get("m3_release", {}).get("release_id") != EXPECTED_RELEASE_ID:
        raise ValueError("reference profile does not identify the accepted M3 release")
    if reference.get("m4_checkpoint", {}).get("sha256") != EXPECTED_CHECKPOINT_SHA256:
        raise ValueError("reference profile does not identify the accepted M4 checkpoint")
    reference_workload = reference["m4_policy_workload_only"]
    observed_max = int(reference_workload["history_plies_per_policy_decision"]["max"])
    if observed_max <= 0 or observed_max > 801:
        raise ValueError("reference profile has an unsupported maximum observed history")

    torch.set_num_threads(1)
    try:
        torch.set_num_interop_threads(1)
    except RuntimeError:
        if torch.get_num_interop_threads() != 1:
            raise
    random.seed(20261028)
    np.random.seed(20261028)
    torch.manual_seed(20261028)
    behavior, _ = load_checkpoint(
        checkpoint, expected_release_id=EXPECTED_RELEASE_ID,
        expected_split_sha256=EXPECTED_SPLIT_SHA256,
    )
    online = initialize_q_head(behavior, seed=20261028).cpu()
    target = copy.deepcopy(online).eval()
    online.train()
    batch, lengths = make_synthetic_batch(observed_max, candidate_count=46)
    optimizer = torch.optim.AdamW(online.parameters(), lr=1e-4, weight_decay=1e-4)
    rewards = torch.zeros((32,), dtype=torch.float32)
    bootstrap = torch.ones((32,), dtype=torch.float32)
    chosen = torch.zeros((32,), dtype=torch.long)

    elapsed_updates: list[float] = []
    losses: list[float] = []
    grad_norms: list[float] = []
    for update_index in range(7):
        if time.monotonic() >= deadline:
            raise ProfileLimit("history budget profile reached its 120-second hard cap")
        tick = time.perf_counter()
        with torch.no_grad():
            next_online = online.eval()(**batch)
            next_target = target(**batch)
            selected = next_online.masked_fill(~batch["candidate_mask"], -torch.inf).argmax(dim=1)
            target_values = next_target.gather(1, selected[:, None]).squeeze(1)
            targets = rewards + 0.99 * bootstrap * target_values
        online.train()
        optimizer.zero_grad(set_to_none=True)
        predictions = online(**batch).gather(1, chosen[:, None]).squeeze(1)
        loss = F.smooth_l1_loss(predictions, targets.detach())
        if not torch.isfinite(loss):
            raise FloatingPointError("synthetic TD loss is nonfinite")
        loss.backward()
        grad_norm = torch.nn.utils.clip_grad_norm_(online.parameters(), 1.0, error_if_nonfinite=True)
        if not torch.isfinite(grad_norm) or any(
            parameter.grad is not None and not torch.isfinite(parameter.grad).all()
            for parameter in online.parameters()
        ):
            raise FloatingPointError("synthetic gradients are nonfinite")
        optimizer.step()
        if any(not torch.isfinite(parameter).all() for parameter in online.parameters()):
            raise FloatingPointError("synthetic updated parameters are nonfinite")
        elapsed = time.perf_counter() - tick
        if update_index >= 2:
            elapsed_updates.append(elapsed)
            losses.append(float(loss.detach()))
            grad_norms.append(float(grad_norm.detach()))

    if sha256(checkpoint) != checkpoint_hash:
        raise RuntimeError("accepted M4 checkpoint changed during profile")
    manifest_after = verify_artifact_manifest(checkpoint.parent)
    if manifest_after != artifact_manifest:
        raise RuntimeError("accepted M4 artifact bundle changed during profile")

    decision_seconds = float(reference["training_run_feasibility_projection"]["p95_decision_time_seconds_for_10000"])
    update_median = float(np.median(elapsed_updates))
    update_p95 = float(np.quantile(elapsed_updates, 0.95))
    allowed_update = (45 * 60 - decision_seconds) / UPDATES_AFTER_WARMUP
    peak_rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024
    elapsed_total = time.monotonic() - started
    if peak_rss > RSS_CAP_BYTES or elapsed_total > max_seconds:
        raise ProfileLimit(f"profile resource cap exceeded (elapsed={elapsed_total:.3f}, rss={peak_rss})")
    source_sha = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    source_dirty = bool(subprocess.check_output(["git", "status", "--porcelain"], text=True).strip())
    return {
        "schema": "videochess-pre-m5-history-budget-profile/1.0",
        "source_revision": source_sha,
        "source_worktree_clean": not source_dirty,
        "started_at_utc": started_wall,
        "elapsed_seconds": elapsed_total,
        "software": {
            "python": platform.python_version(),
            "torch": str(torch.__version__),
            "numpy": np.__version__,
            "platform": platform.platform(),
            "logical_cpu_count": os.cpu_count(),
            "device": "cpu",
            "torch_threads": {"intra_op": torch.get_num_threads(), "inter_op": torch.get_num_interop_threads()},
        },
        "artifact": {
            "checkpoint_path": str(checkpoint),
            "checkpoint_sha256": checkpoint_hash,
            "bundle_files_verified": len(artifact_manifest["files"]),
            "reference_profile_sha256": hashlib.sha256(reference_bytes).hexdigest(),
            "reference_profile_source_revision": reference["source_revision"],
            "reference_workload_history_plies": reference_workload["history_plies_per_policy_decision"],
        },
        "workload": {
            "batch_size": 32,
            "candidate_slots_per_row": 46,
            "max_history_plies": observed_max,
            "history_lengths": list(lengths),
            "history_length_quantiles": {
                "min": min(lengths), "p50": int(np.quantile(lengths, 0.50)),
                "p95": int(np.quantile(lengths, 0.95)), "max": max(lengths),
            },
            "total_history_tokens": sum(lengths),
            "update_repeats_total": 7,
            "warmup_updates_excluded": 2,
            "measured_update_seconds": elapsed_updates,
            "update_median_seconds": update_median,
            "update_p95_seconds": update_p95,
            "finite_losses": losses,
            "gradient_norms_before_clip": grad_norms,
            "synthetic_nonsemantic_chess_batch": True,
            "trained_policy_claimed": False,
        },
        "budget_projection": {
            "updates_per_10000_decision_run": UPDATES_AFTER_WARMUP,
            "observed_m4_decision_time_projection_seconds": decision_seconds,
            "per_run_cap_seconds": 2700,
            "max_average_update_seconds_for_cap": allowed_update,
            "run_projection_seconds_at_median_update": update_median * UPDATES_AFTER_WARMUP + decision_seconds,
            "run_projection_seconds_at_p95_update": update_p95 * UPDATES_AFTER_WARMUP + decision_seconds,
            "median_projection_within_cap": update_median <= allowed_update,
            "p95_projection_within_cap": update_p95 <= allowed_update,
            "excludes_replay_sampling_checkpoint_and_validation_overhead": True,
            "does_not_guarantee_m5_convergence_or_runtime": True,
        },
        "resource": {"peak_rss_bytes": peak_rss, "rss_cap_bytes": RSS_CAP_BYTES,
                     "wall_cap_seconds": max_seconds},
        "limitations": [
            "History lengths are synthetic evenly spaced shapes capped at the observed M4 workload maximum; board, candidates, and move histories are not semantically valid chess transitions.",
            "The M4 workload is a cost proxy, not an M5 policy or replay-history distribution.",
            "The projection excludes replay sampling, transition validation, checkpoint I/O, and validation overhead.",
            "No M5 learner, training campaign, or policy-quality result was produced.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--reference-profile", type=Path, required=True)
    parser.add_argument("--max-seconds", type=float, default=60.0)
    args = parser.parse_args()
    if not 0 < args.max_seconds <= MAX_PROFILE_SECONDS:
        parser.error("max-seconds must be in (0, 120]")
    print(json.dumps(run(args.checkpoint, args.reference_profile, args.max_seconds), sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ProfileLimit as exc:
        print(json.dumps({"schema": "videochess-pre-m5-history-budget-profile/1.0", "status": "INCOMPLETE", "reason": str(exc)}, sort_keys=True))
        raise SystemExit(2)
