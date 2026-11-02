#!/usr/bin/env python3
"""Bounded CPU-only M5 workload profile; this is not DDQN training.

Uses the accepted local M3 release and M4 checkpoint read-only. It profiles a
real batch of 32 M3 features, a synthetic 801-ply shape stress (M2's maximum
400 agent decisions can contain one Black opening ply plus two plies per
decision), one synthetic TD/Huber optimizer step, bounded serialized replay-
like storage, and one 40-game M4 policy workload sample. No M5 learner or
persistent replay/checkpoint is created.
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
import statistics
import subprocess
import sys
import tempfile
import time
import tracemalloc
from pathlib import Path
from typing import Any

import chess
import numpy as np
import torch
import torch.nn.functional as F

from videochess_rl.baselines import RandomLegalAgent, SimpleHeuristicAgent
from videochess_rl.model.checkpoint import load_checkpoint, verify_artifact_manifest
from videochess_rl.model.dataset import M4Dataset, collate_examples, load_m3_release, model_inputs
from videochess_rl.model.features import PositionFeatures
from videochess_rl.model.inference import BehaviorPolicy
from videochess_rl.model.network import initialize_q_head
from videochess_rl.simulator import ChessSimulator

EXPECTED_CHECKPOINT_SHA256 = "724ac730f3c5f2d01b48b26eb7670a3c764978a3dd4d6702b3057a99ab1a90a4"
EXPECTED_RELEASE_ID = "f10a679deddf06f3e1e3c39cf58db4e21176629c26c09034a271bf278189e890"
EXPECTED_MANIFEST_SHA256 = "be1e1f9316fac01be893774cfe09a313de193fbd1a12ab2d219ff5c041104a12"
EXPECTED_SPLIT_SHA256 = "84efed824e57de45c0058b73818bb7a9d740201ead38e9171308cee43bc0934e"
MAX_PROFILE_SECONDS = 840.0
RSS_CAP_BYTES = 2 * 1024**3
HISTORY_STRESS_PLIES = 801
REPLAY_CAPACITY = 4096


class ProfileDeadline(RuntimeError):
    """The profile reached its hard wall-clock bound."""


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def release_inventory(release: Path, names: tuple[str, ...]) -> dict[str, dict[str, int | str]]:
    inventory: dict[str, dict[str, int | str]] = {}
    for name in names:
        path = release / name
        inventory[name] = {"sha256": sha256(path), "size_bytes": path.stat().st_size}
    return inventory


def quantiles(values: list[float]) -> dict[str, float]:
    ordered = sorted(values)
    if not ordered:
        return {"p50": 0.0, "p95": 0.0, "max": 0.0}

    def at(fraction: float) -> float:
        return ordered[min(len(ordered) - 1, round((len(ordered) - 1) * fraction))]

    return {"p50": at(0.50), "p95": at(0.95), "max": ordered[-1]}


def select_profile_batch(dataset: M4Dataset, count: int = 32) -> tuple[PositionFeatures, ...]:
    """Deterministically span history and candidate-count distributions."""
    if count != 32 or len(dataset.train) < count:
        raise ValueError("the versioned profile requires exactly 32 training features")
    selected: dict[str, PositionFeatures] = {}

    def add_quantiles(key) -> None:
        ordered = sorted(dataset.train, key=lambda row: (key(row), row.sample_id))
        for index in range(16):
            selected[ordered[round(index * (len(ordered) - 1) / 15)].sample_id] = ordered[
                round(index * (len(ordered) - 1) / 15)
            ]

    add_quantiles(lambda row: row.history_length)
    add_quantiles(lambda row: row.candidate_count)
    if len(selected) < count:
        for row in dataset.train:
            selected.setdefault(row.sample_id, row)
            if len(selected) == count:
                break
    return tuple(selected[sample_id] for sample_id in sorted(selected)[:count])


def make_max_history_stress(batch: dict[str, Any], *, plies: int = HISTORY_STRESS_PLIES) -> dict[str, Any]:
    """Return a synthetic tensor-shape stress; it is not a valid chess state."""
    if batch["history_moves"].shape[0] != 32 or not 0 < plies <= 801:
        raise ValueError("unexpected stress batch size or history length")
    output = dict(batch)
    base = batch["history_moves"]
    extended = torch.zeros((32, plies, 4), dtype=base.dtype)
    if base.shape[1]:
        copies = min(base.shape[1], plies)
        extended[:, :copies] = base[:, :copies]
        fill = base[:, copies - 1, :] if copies else torch.tensor([0, 1, 0, 0], dtype=base.dtype)
    else:
        fill = torch.tensor([0, 1, 0, 0], dtype=base.dtype).expand(32, -1)
    if base.shape[1] < plies:
        extended[:, base.shape[1]:] = fill[:, None, :].expand(-1, plies - base.shape[1], -1)
    output["history_moves"] = extended
    output["history_mask"] = torch.ones((32, plies), dtype=torch.bool)
    return output


def make_variable_history_stress(
    batch: dict[str, Any], *, max_plies: int = HISTORY_STRESS_PLIES,
) -> tuple[dict[str, Any], tuple[int, ...]]:
    """Build an evenly spread shape stress; it does not represent chess states."""
    if batch["history_moves"].shape[0] != 32 or not 0 < max_plies <= HISTORY_STRESS_PLIES:
        raise ValueError("unexpected stress batch size or maximum history length")
    lengths = tuple(round(index * max_plies / 31) for index in range(32))
    source = batch["history_moves"]
    extended = torch.zeros((32, max_plies, 4), dtype=source.dtype)
    mask = torch.zeros((32, max_plies), dtype=torch.bool)
    for index, length in enumerate(lengths):
        source_length = int(batch["history_mask"][index].sum())
        copied = min(source_length, length)
        if copied:
            extended[index, :copied] = source[index, :copied]
        if length > copied:
            fill = source[index, source_length - 1] if source_length else torch.tensor([0, 1, 0, 0], dtype=source.dtype)
            extended[index, copied:length] = fill.expand(length - copied, -1)
        mask[index, :length] = True
    output = dict(batch)
    output["history_moves"] = extended
    output["history_mask"] = mask
    return output, lengths


def build_replay_wire_probe(
    rows: tuple[PositionFeatures, ...], *, history_plies: int | None = None,
) -> dict[str, Any]:
    """Measure a bounded compact serialized-record ring, not a learner replay."""
    tracemalloc.start()
    before_current, _ = tracemalloc.get_traced_memory()
    ring = []
    for index in range(REPLAY_CAPACITY):
        if index % 128 == 0:
            peak_rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024
            if peak_rss > RSS_CAP_BYTES:
                tracemalloc.stop()
                raise ProfileDeadline("replay-like profile reached its 2 GiB RSS bound")
        row = rows[index % len(rows)]
        history_tokens = row.history_moves.tolist()
        if history_plies is not None:
            if history_plies < len(history_tokens):
                raise ValueError("stress history cannot be shorter than its sampled source")
            fill = history_tokens[-1] if history_tokens else [0, 1, 0, 0]
            history_tokens.extend([list(fill) for _ in range(history_plies - len(history_tokens))])
        record = {
            "transition_id": f"profile-transition-{index:05d}",
            "seed": 20261028,
            "agent_color": "profile-only",
            "opponent_id": "profile-only",
            "current_history_tokens": history_tokens,
            "legal_uci": list(row.candidate_uci),
            "selected_uci": row.candidate_uci[0],
            "reward_agent": 0.0,
            "terminated": False,
            "truncated": False,
            "next_history_tokens": history_tokens,
            "next_legal_uci": list(row.candidate_uci),
        }
        ring.append(json.dumps(record, sort_keys=True, separators=(",", ":")).encode("utf-8"))
    current_bytes, peak_bytes = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    stored_wire_bytes = sum(len(record) for record in ring)
    object_bytes = sys.getsizeof(ring) + sum(sys.getsizeof(record) for record in ring)
    return {
        "capacity": len(ring),
        "record_schema": "synthetic_profile_wire_only",
        "history_plies_per_state": history_plies,
        "unique_record_count": len(set(ring)),
        "record_wire_bytes": {"p50": statistics.median(map(len, ring)), "max": max(map(len, ring))},
        "stored_wire_bytes": stored_wire_bytes,
        "measured_container_and_bytes_object_bytes": object_bytes,
        "tracemalloc_incremental_current_bytes": current_bytes - before_current,
        "tracemalloc_incremental_peak_bytes": peak_bytes - before_current,
        "persistent_file_written": False,
        "semantically_valid_transitions_claimed": False,
    }


def check_deadline(deadline: float, phase: str) -> None:
    if time.monotonic() >= deadline:
        raise ProfileDeadline(f"profile reached the 840-second bound during {phase}")
    peak_rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024
    if peak_rss > RSS_CAP_BYTES:
        raise ProfileDeadline(f"profile reached the 2 GiB RSS bound during {phase}")


def _profile_timeout(signum: int, frame: Any) -> None:
    del signum, frame
    raise ProfileDeadline("profile reached its configured hard wall-clock bound")


def run_m4_evaluation_workload(policy: BehaviorPolicy, *, deadline: float) -> dict[str, Any]:
    """Time 40 predeclared scenarios; discard outcomes and report workload only."""
    seeds = tuple(range(20261130, 20261140))
    opponents = (
        ("random_legal", RandomLegalAgent),
        ("simple_heuristic", SimpleHeuristicAgent),
    )
    games: list[dict[str, Any]] = []
    inference_seconds: list[float] = []
    step_seconds: list[float] = []
    history_plies: list[int] = []
    total_started = time.perf_counter()
    for seed in seeds:
        for opponent_id, opponent_type in opponents:
            for color_name, color in (("white", chess.WHITE), ("black", chess.BLACK)):
                check_deadline(deadline, "40-game M4 workload")
                simulator = ChessSimulator(opponent_type(), max_decisions=400)
                observation = simulator.reset(seed=seed, agent_color=color)
                decisions = 0
                outcome = None
                stop_reason = None
                game_started = time.perf_counter()
                while True:
                    check_deadline(deadline, "40-game M4 workload decision")
                    tick = time.perf_counter()
                    action = policy.choose_move(observation, simulator.legal_moves, random.Random(seed + decisions))
                    inference_seconds.append(time.perf_counter() - tick)
                    history_plies.append(len(observation.history_uci))
                    tick = time.perf_counter()
                    result = simulator.step(action)
                    step_seconds.append(time.perf_counter() - tick)
                    decisions += 1
                    observation = result.observation
                    if result.terminated:
                        outcome = "terminal"
                        stop_reason = result.outcome_reason
                        break
                    if result.truncated:
                        outcome = "truncated"
                        stop_reason = result.truncation_reason
                        break
                games.append({
                    "seed": seed,
                    "opponent": opponent_id,
                    "agent_color": color_name,
                    "decisions": decisions,
                    "elapsed_seconds": time.perf_counter() - game_started,
                    "stop_kind": outcome,
                    "stop_reason": stop_reason,
                })
    return {
        "policy": "accepted_frozen_m4_behavior_only_workload_probe",
        "scenarios_planned": 40,
        "scenarios_completed": len(games),
        "scenario_key": ["seed", "opponent", "agent_color"],
        "game_decisions": {"total": sum(game["decisions"] for game in games),
                            "p50": statistics.median(game["decisions"] for game in games),
                            "p95": sorted(game["decisions"] for game in games)[round(.95 * (len(games) - 1))],
                            "max": max(game["decisions"] for game in games)},
        "history_plies_per_policy_decision": quantiles(history_plies),
        "per_game_wall_seconds": quantiles([game["elapsed_seconds"] for game in games]),
        "per_decision_inference_seconds": quantiles(inference_seconds),
        "per_decision_simulator_step_seconds": quantiles(step_seconds),
        "simulator_steps_per_second": len(step_seconds) / max(sum(step_seconds), 1e-12),
        "agent_decisions_per_second_including_policy_inference": len(inference_seconds) / max(
            sum(inference_seconds) + sum(step_seconds), 1e-12
        ),
        "snapshot_wall_seconds": time.perf_counter() - total_started,
        "games": games,
        "outcomes_intentionally_not_aggregated": True,
        "not_an_m5_or_policy_strength_evaluation": True,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--release", type=Path, required=True)
    parser.add_argument("--max-seconds", type=float, default=840.0)
    args = parser.parse_args()
    if not 0 < args.max_seconds <= MAX_PROFILE_SECONDS:
        parser.error("max-seconds must be in (0, 840]; Pre-M5 CPU profile allowance is 14 minutes")

    started = time.monotonic()
    deadline = started + args.max_seconds
    signal.signal(signal.SIGALRM, _profile_timeout)
    signal.setitimer(signal.ITIMER_REAL, args.max_seconds)
    checkpoint = args.checkpoint.expanduser().resolve(strict=True)
    release = args.release.expanduser().resolve(strict=True)
    checkpoint_before = sha256(checkpoint)
    if checkpoint_before != EXPECTED_CHECKPOINT_SHA256:
        raise RuntimeError("accepted M4 checkpoint SHA-256 differs")
    m4_manifest_before = verify_artifact_manifest(checkpoint.parent)
    if len(m4_manifest_before["files"]) != 19:
        raise RuntimeError("accepted M4 bundle must contain 19 verified files")

    torch.set_num_threads(1)
    try:
        torch.set_num_interop_threads(1)
    except RuntimeError:
        if torch.get_num_interop_threads() != 1:
            raise
    random.seed(20261028)
    np.random.seed(20261028)
    torch.manual_seed(20261028)

    dataset_started = time.perf_counter()
    dataset = load_m3_release(release)
    dataset_seconds = time.perf_counter() - dataset_started
    if dataset.release_id != EXPECTED_RELEASE_ID or dataset.manifest_sha256 != EXPECTED_MANIFEST_SHA256:
        raise RuntimeError("accepted M3 data identity differs")
    row_selection_started = time.perf_counter()
    rows = select_profile_batch(dataset)
    selection_seconds = time.perf_counter() - row_selection_started
    collate_started = time.perf_counter()
    batch = collate_examples(rows, require_targets=False)
    collate_seconds = time.perf_counter() - collate_started
    inputs = model_inputs(batch)
    if len(rows) != 32 or any(row.split != "train" for row in rows):
        raise RuntimeError("profile batch must contain exactly 32 accepted train examples")

    behavior, bundle = load_checkpoint(
        checkpoint, expected_release_id=EXPECTED_RELEASE_ID,
        expected_split_sha256=EXPECTED_SPLIT_SHA256,
    )
    online = initialize_q_head(behavior, seed=20261028).cpu()
    target = copy.deepcopy(online).eval()
    online.eval()
    for key, value in behavior.m5_transfer_state().items():
        if not torch.equal(value, online.state_dict()[key]):
            raise RuntimeError(f"shared M4 representation differs after Q-head initialization: {key}")
    if hasattr(online, "behavior_head") or not hasattr(online, "q_head"):
        raise RuntimeError("M4 behavior head was not replaced by an M5 Q head")
    if not all(torch.equal(value, target.state_dict()[key]) for key, value in online.state_dict().items()):
        raise RuntimeError("target initialization differs from the post-transfer online model")

    check_deadline(deadline, "batch32 profile")
    forward_latencies: list[float] = []
    with torch.inference_mode():
        for _ in range(12):
            tick = time.perf_counter()
            online_scores = online(**inputs)
            target_scores = target(**inputs)
            forward_latencies.append(time.perf_counter() - tick)
            legal = batch["candidate_mask"]
            if not torch.isfinite(online_scores[legal]).all() or not torch.isfinite(target_scores[legal]).all():
                raise FloatingPointError("legal batch32 profile outputs must be finite")
            if not torch.isfinite(online_scores.masked_fill(~legal, 0.0)).all():
                raise FloatingPointError("masked online output contains nonfinite values")

    stress_batch = make_max_history_stress(batch)
    stress_inputs = model_inputs(stress_batch)
    check_deadline(deadline, "801-ply shape stress")
    stress_forward_times: list[float] = []
    with torch.inference_mode():
        for _ in range(3):
            tick = time.perf_counter()
            stress_online = online(**stress_inputs)
            stress_target = target(**stress_inputs)
            stress_forward_times.append(time.perf_counter() - tick)
            stress_legal = stress_batch["candidate_mask"]
            if not torch.isfinite(stress_online[stress_legal]).all() or not torch.isfinite(stress_target[stress_legal]).all():
                raise FloatingPointError("long-history stress output is nonfinite")

    check_deadline(deadline, "synthetic TD/Huber update")
    online.train()
    optimizer = torch.optim.AdamW(online.parameters(), lr=1e-4, weight_decay=1e-4)
    legal = batch["candidate_mask"]
    rewards = torch.zeros((32,), dtype=torch.float32)
    rewards[0::3] = 1.0
    rewards[1::3] = -1.0
    bootstrap = torch.tensor([0.0 if index % 7 == 0 else 1.0 for index in range(32)])
    with torch.no_grad():
        next_online = online.eval()(**inputs)
        next_target = target(**inputs)
        selected_indices = next_online.masked_fill(~legal, -torch.inf).argmax(dim=1)
        target_selected = next_target.gather(1, selected_indices[:, None]).squeeze(1)
        targets = rewards + 0.99 * bootstrap * target_selected
    online.train()
    chosen_indices = torch.tensor([
        int(row.target_index) if row.target_index is not None else 0 for row in rows
    ], dtype=torch.long)
    if not torch.all(legal.gather(1, chosen_indices[:, None])):
        raise RuntimeError("profile selected action must be inside the real legal candidate mask")
    tick = time.perf_counter()
    optimizer.zero_grad(set_to_none=True)
    predictions = online(**inputs).gather(1, chosen_indices[:, None]).squeeze(1)
    td_loss = F.smooth_l1_loss(predictions, targets.detach())
    if not torch.isfinite(td_loss):
        raise FloatingPointError("synthetic TD Huber loss is nonfinite")
    td_loss.backward()
    grad_norm = torch.nn.utils.clip_grad_norm_(online.parameters(), 1.0, error_if_nonfinite=True)
    if not torch.isfinite(grad_norm) or any(p.grad is not None and not torch.isfinite(p.grad).all() for p in online.parameters()):
        raise FloatingPointError("synthetic gradient profile produced nonfinite gradients")
    optimizer.step()
    if any(not torch.isfinite(p).all() for p in online.parameters()):
        raise FloatingPointError("synthetic optimizer step produced nonfinite parameters")
    update_seconds = time.perf_counter() - tick

    check_deadline(deadline, "801-ply synthetic TD/Huber update")
    stress_legal = stress_batch["candidate_mask"]
    with torch.no_grad():
        tick = time.perf_counter()
        long_next_online = online.eval()(**stress_inputs)
        long_next_target = target(**stress_inputs)
        long_indices = long_next_online.masked_fill(~stress_legal, -torch.inf).argmax(dim=1)
        long_target_values = long_next_target.gather(1, long_indices[:, None]).squeeze(1)
        long_targets = rewards + 0.99 * bootstrap * long_target_values
    online.train()
    tick = time.perf_counter()
    optimizer.zero_grad(set_to_none=True)
    long_predictions = online(**stress_inputs).gather(1, chosen_indices[:, None]).squeeze(1)
    long_loss = F.smooth_l1_loss(long_predictions, long_targets.detach())
    if not torch.isfinite(long_loss):
        raise FloatingPointError("long-history synthetic TD Huber loss is nonfinite")
    long_loss.backward()
    long_grad_norm = torch.nn.utils.clip_grad_norm_(online.parameters(), 1.0, error_if_nonfinite=True)
    if not torch.isfinite(long_grad_norm) or any(
        parameter.grad is not None and not torch.isfinite(parameter.grad).all()
        for parameter in online.parameters()
    ):
        raise FloatingPointError("long-history synthetic gradient profile is nonfinite")
    optimizer.step()
    stress_update_seconds = time.perf_counter() - tick

    variable_batch, variable_history_lengths = make_variable_history_stress(batch)
    variable_inputs = model_inputs(variable_batch)
    check_deadline(deadline, "variable-history shape stress")
    variable_forward_times: list[float] = []
    with torch.inference_mode():
        for _ in range(3):
            tick = time.perf_counter()
            variable_online = online(**variable_inputs)
            variable_target = target(**variable_inputs)
            variable_forward_times.append(time.perf_counter() - tick)
            variable_legal = variable_batch["candidate_mask"]
            if not torch.isfinite(variable_online[variable_legal]).all() or not torch.isfinite(variable_target[variable_legal]).all():
                raise FloatingPointError("variable-history stress output is nonfinite")

    with torch.no_grad():
        variable_next_online = online.eval()(**variable_inputs)
        variable_next_target = target(**variable_inputs)
        variable_indices = variable_next_online.masked_fill(~variable_legal, -torch.inf).argmax(dim=1)
        variable_target_values = variable_next_target.gather(1, variable_indices[:, None]).squeeze(1)
        variable_targets = rewards + 0.99 * bootstrap * variable_target_values
    online.train()
    tick = time.perf_counter()
    optimizer.zero_grad(set_to_none=True)
    variable_predictions = online(**variable_inputs).gather(1, chosen_indices[:, None]).squeeze(1)
    variable_loss = F.smooth_l1_loss(variable_predictions, variable_targets.detach())
    if not torch.isfinite(variable_loss):
        raise FloatingPointError("variable-history synthetic TD Huber loss is nonfinite")
    variable_loss.backward()
    variable_grad_norm = torch.nn.utils.clip_grad_norm_(online.parameters(), 1.0, error_if_nonfinite=True)
    if not torch.isfinite(variable_grad_norm) or any(
        parameter.grad is not None and not torch.isfinite(parameter.grad).all()
        for parameter in online.parameters()
    ):
        raise FloatingPointError("variable-history synthetic gradients are nonfinite")
    optimizer.step()
    variable_update_seconds = time.perf_counter() - tick

    with tempfile.TemporaryDirectory(prefix="m5-profile-checkpoint-") as directory:
        temporary_checkpoint = Path(directory) / "state.pt"
        serialization_started = time.perf_counter()
        torch.save({
            "online": online.state_dict(),
            "target": target.state_dict(),
            "optimizer": optimizer.state_dict(),
            "counters": {"profile_only": True, "committed_decisions": 0, "gradient_updates": 1},
        }, temporary_checkpoint)
        checkpoint_serialize_seconds = time.perf_counter() - serialization_started
        temporary_checkpoint_bytes = temporary_checkpoint.stat().st_size

    check_deadline(deadline, "replay-like storage probe")
    replay_observed = build_replay_wire_probe(rows)
    replay_max_history = build_replay_wire_probe(rows, history_plies=HISTORY_STRESS_PLIES)
    check_deadline(deadline, "40-game workload")
    behavior.eval()
    policy = BehaviorPolicy(behavior, checkpoint_sha256=checkpoint_before)
    evaluation_workload = run_m4_evaluation_workload(policy, deadline=deadline)

    if sha256(checkpoint) != checkpoint_before:
        raise RuntimeError("accepted M4 checkpoint changed during profile")
    m4_manifest_after = verify_artifact_manifest(checkpoint.parent)
    if m4_manifest_after != m4_manifest_before:
        raise RuntimeError("accepted M4 artifact bundle changed during profile")
    if dataset.file_inventory != release_inventory(release, tuple(dataset.file_inventory)):
        raise RuntimeError("accepted M3 release inventory changed during profile")

    elapsed = time.monotonic() - started
    peak_rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024
    if elapsed > args.max_seconds or peak_rss > RSS_CAP_BYTES:
        raise RuntimeError(f"profile resource cap exceeded (wall={elapsed:.3f}s, rss={peak_rss})")

    observed_snapshot_seconds = evaluation_workload["snapshot_wall_seconds"]
    estimated_full_schedule_seconds = observed_snapshot_seconds * 15
    combined_p95_step_seconds = (
        evaluation_workload["per_decision_inference_seconds"]["p95"]
        + evaluation_workload["per_decision_simulator_step_seconds"]["p95"]
    )
    worst_case_per_checkpoint_seconds = 40 * 400 * combined_p95_step_seconds
    full_schedule_upper_estimate_seconds = 15 * worst_case_per_checkpoint_seconds
    estimated_updates = ((10000 - 512) // 4) + 1
    decision_projection_seconds = combined_p95_step_seconds * 10000
    maximum_update_seconds_for_cap = (45 * 60 - decision_projection_seconds) / estimated_updates
    source_revision = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    source_status = subprocess.check_output(["git", "status", "--porcelain"], text=True)
    profile_config = {
        "schema": "videochess-pre-m5-profile-config/2.1",
        "real_batch_size": 32,
        "synthetic_max_history_plies": HISTORY_STRESS_PLIES,
        "forward_repeats": 12,
        "long_history_forward_repeats": 3,
        "replay_probe_capacity": REPLAY_CAPACITY,
        "evaluation_workload_games": 40,
        "evaluation_max_agent_decisions_per_game": 400,
        "profile_max_seconds": args.max_seconds,
        "peak_rss_hard_cap_bytes": RSS_CAP_BYTES,
        "device": "cpu",
        "threads": {"intra_op": torch.get_num_threads(), "inter_op": torch.get_num_interop_threads()},
    }
    output = {
        "schema": "videochess-pre-m5-feasibility-profile/2.1",
        "profile_config": profile_config,
        "profile_config_sha256": hashlib.sha256(json.dumps(profile_config, sort_keys=True, separators=(",", ":")).encode()).hexdigest(),
        "source_revision": source_revision,
        "source_worktree_clean_at_profile": not bool(source_status.strip()),
        "python": platform.python_version(),
        "platform": platform.platform(),
        "processor": platform.processor(),
        "logical_cpu_count": os.cpu_count(),
        "torch": str(torch.__version__),
        "numpy": np.__version__,
        "python_chess": chess.__version__,
        "m3_release": {"path": str(release), "release_id": dataset.release_id,
                       "manifest_sha256": dataset.manifest_sha256,
                       "split_assignment_sha256": dataset.split_assignment_sha256,
                       "nine_file_inventory_sha256": hashlib.sha256(json.dumps(dataset.file_inventory, sort_keys=True, separators=(",", ":")).encode()).hexdigest(),
                       "counts": dataset.counts, "game_counts": dataset.game_counts,
                       "verification_seconds": dataset.verification_seconds,
                       "replay_seconds": dataset.replay_seconds,
                       "total_load_seconds": dataset.total_load_seconds,
                       "sampled_train_ids": [row.sample_id for row in rows],
                       "sampled_id_sha256": hashlib.sha256("\n".join(row.sample_id for row in rows).encode()).hexdigest(),
                       "train_history_plies": quantiles([row.history_length for row in dataset.train]),
                       "train_legal_candidate_count": quantiles([row.candidate_count for row in dataset.train]),
                       "files_unchanged_after_profile": True},
        "m4_checkpoint": {"path": str(checkpoint), "sha256": checkpoint_before,
                          "file_size_bytes": checkpoint.stat().st_size,
                          "bundle_files_verified": len(m4_manifest_before["files"]),
                          "bundle_manifest_inventory_sha256": hashlib.sha256(json.dumps(m4_manifest_before, sort_keys=True, separators=(",", ":")).encode()).hexdigest(),
                          "bundle_unchanged_after_profile": True,
                          "bundle_metadata": bundle["metadata"],
                          "trainable_parameter_count": online.trainable_parameter_count,
                          "online_state_tensor_bytes": sum(t.numel() * t.element_size() for t in online.state_dict().values()),
                          "online_plus_target_state_tensor_bytes": 2 * sum(t.numel() * t.element_size() for t in online.state_dict().values()),
                          "behavior_head_excluded_from_q": True,
                          "target_copied_after_initialization": True},
        "real_batch32": {"selected_rows": len(rows), "split_counts": {"train": 32},
                         "selection_seconds": selection_seconds,
                         "collation_seconds": collate_seconds,
                         "history_plies": quantiles([row.history_length for row in rows]),
                         "history_plies_by_row": [row.history_length for row in rows],
                         "history_plies_total": sum(row.history_length for row in rows),
                         "legal_candidate_count": quantiles([row.candidate_count for row in rows]),
                         "candidate_mask_padding_slots": int(batch["candidate_mask"].numel() - batch["candidate_mask"].sum()),
                         "forward_pair_repeats": 12,
                         "online_plus_target_forward_pair_seconds": quantiles(forward_latencies),
                         "legal_candidate_scores_per_second": sum(row.candidate_count for row in rows) * 24 / max(sum(forward_latencies), 1e-12)},
        "max_history_shape_stress": {"plies": HISTORY_STRESS_PLIES,
                                     "batch_size": 32,
                                     "padded_history_tokens": 32 * HISTORY_STRESS_PLIES,
                                     "synthetic_not_semantic_chess_history": True,
                                     "online_plus_target_forward_pair_seconds": quantiles(stress_forward_times)},
        "variable_history_shape_stress": {"plies": HISTORY_STRESS_PLIES,
                                          "batch_size": 32,
                                          "history_lengths": list(variable_history_lengths),
                                          "total_history_tokens": sum(variable_history_lengths),
                                          "history_length_quantiles": quantiles(list(variable_history_lengths)),
                                          "synthetic_not_semantic_chess_history": True,
                                          "online_plus_target_forward_pair_seconds": quantiles(variable_forward_times),
                                          "synthetic_huber_loss": float(variable_loss.detach()),
                                          "gradient_norm_before_clip": float(variable_grad_norm.detach()),
                                          "full_td_backward_update_seconds": variable_update_seconds},
        "synthetic_ddqn_computation": {"online_next_action_masked_selection": True,
                                       "target_evaluates_same_batch_candidate_index": True,
                                       "reward_and_bootstrap_shapes": [32],
                                       "huber_loss": float(td_loss.detach()),
                                       "gradient_norm_before_clip": float(grad_norm.detach()),
                                       "adamw_update_seconds": update_seconds,
                                       "801_ply_synthetic_huber_loss": float(long_loss.detach()),
                                       "801_ply_gradient_norm_before_clip": float(long_grad_norm.detach()),
                                       "801_ply_full_td_backward_update_seconds": stress_update_seconds,
                                       "m3_real_batch32_full_td_backward_update_seconds": update_seconds,
                                       "variable_history_full_td_backward_update_seconds": variable_update_seconds,
                                       "finite_targets_loss_gradients_and_parameters": all(torch.isfinite(p).all() for p in online.parameters()),
                                       "trained_policy_claimed": False},
        "replay_like_storage_probe": {
            "observed_m3_feature_lengths": replay_observed,
            "synthetic_801_ply_upper_shape": replay_max_history,
        },
        "temporary_checkpoint_serialization": {"seconds": checkpoint_serialize_seconds,
                                                "size_bytes": temporary_checkpoint_bytes,
                                                "includes_online_target_and_one_adamw_state": True,
                                                "persistent_file_written": False},
        "m4_policy_workload_only": evaluation_workload,
        "evaluation_schedule_feasibility": {
            "policy_snapshots": 15,
            "games_per_snapshot": 40,
            "planned_games": 600,
            "per_snapshot_cap_seconds": 1200,
            "sum_of_snapshot_caps_seconds": 18000,
            "aggregate_cap_seconds": 10800,
            "aggregate_average_seconds_per_game": 18,
            "observed_one_snapshot_40_game_seconds": observed_snapshot_seconds,
            "simple_projection_15_snapshots_seconds": estimated_full_schedule_seconds,
            "simple_projection_is_within_aggregate_cap": estimated_full_schedule_seconds <= 10800,
            "conservative_400_decision_p95_projection_seconds": full_schedule_upper_estimate_seconds,
            "p95_projection_is_within_aggregate_cap": full_schedule_upper_estimate_seconds <= 10800,
            "per_snapshot_conservative_projection_seconds": worst_case_per_checkpoint_seconds,
            "combined_inference_plus_simulator_step_p95_seconds": combined_p95_step_seconds,
            "per_snapshot_p95_projection_within_20_minutes": worst_case_per_checkpoint_seconds <= 1200,
            "projection_caveat": "M4 behavior inference is a same-architecture cost proxy; policy trajectory/game length varies, p95 extrapolation is not a hard guarantee, and all future 15 schedules share one cumulative three-hour cap.",
        },
        "training_run_feasibility_projection": {
            "configured_decisions_per_arm_seed": 10000,
            "configured_updates_per_decisions": 0.25,
            "estimated_updates_after_512_warmup": estimated_updates,
            "p95_decision_time_seconds_for_10000": decision_projection_seconds,
            "max_average_update_seconds_allowed_by_45_min_after_decisions": maximum_update_seconds_for_cap,
            "estimated_run_seconds_using_m3_real_batch32_update_and_p95_decisions": update_seconds * estimated_updates + decision_projection_seconds,
            "estimated_run_seconds_using_variable_history_stress_update_and_p95_decisions": variable_update_seconds * estimated_updates + decision_projection_seconds,
            "profiled_801_ply_update_seconds": stress_update_seconds,
            "profiled_variable_history_update_seconds": variable_update_seconds,
            "profiled_m3_real_batch32_update_seconds": update_seconds,
            "p95_policy_plus_simulator_seconds_per_decision": combined_p95_step_seconds,
            "estimated_run_seconds_using_801_ply_update_and_p95_decisions": stress_update_seconds * estimated_updates + decision_projection_seconds,
            "run_wall_cap_seconds": 45 * 60,
            "six_run_aggregate_cap_seconds": 6 * 60 * 60,
            "projection_caveat": "Projections bracket a real M3 batch, an evenly spread synthetic 0-to-801-ply batch, and an all-801-ply upper stress. The true M5 replay-history distribution is unmeasured; estimates exclude replay sampling/validation overhead and do not guarantee training convergence or fit on another CPU.",
        },
        "resource": {"elapsed_seconds": elapsed, "peak_rss_bytes": peak_rss,
                     "active_profile_cap_seconds": args.max_seconds, "rss_cap_bytes": RSS_CAP_BYTES},
        "limitations": [
            "No M5 learner, replay training, or DDQN policy was implemented or trained.",
            "The 801-ply tensor stress repeats valid categorical token values but is not a semantically valid chess history.",
            "Replay bytes measure compact synthetic JSON records and Python bytes/list overhead, not a future replay implementation's heap or allocator fragmentation.",
            "The 801-ply replay shape is an upper-bound tensor/history stress with sampled candidate sets; it is not a complete legal-state replay dataset.",
            "The variable-history shape stress spreads 32 synthetic history lengths uniformly from zero to 801 plies; it is a workload bracket, not an observed M5 replay-length distribution or legal chess history.",
            "The 45-minute run projection is bracketed using a real M3 batch update, a synthetic variable-history update, and the all-801-ply bound; the true M5 replay workload must be measured before relying on a projection.",
            "The 40-game workload uses the frozen M4 behavior scorer only for timing; outcomes are deliberately not summarized as a new performance result.",
            "The 400-decision p95 schedule estimate is conservative arithmetic from a finite sample, not an execution-time guarantee.",
            "Training convergence, policy quality, paired trajectory equivalence, and ALE performance were not measured.",
        ],
    }
    print(json.dumps(output, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ProfileDeadline as exc:
        print(json.dumps({"schema": "videochess-pre-m5-feasibility-profile/2.1", "status": "INCOMPLETE", "reason": str(exc)}, sort_keys=True))
        raise SystemExit(2)
