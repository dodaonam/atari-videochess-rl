#!/usr/bin/env python3
"""Read-only differential restore of authentic M5 checkpoints with old/new code."""

from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import random
import resource
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from videochess_rl.m5_seeding import EXPERIMENT_ID, pair_identity, run_identity, paired_seed_schedule
from videochess_rl.rl.checkpoint import load_evaluation_snapshot, load_training_checkpoint_bundle, restore_training_checkpoint
from videochess_rl.rl.network import clone_target
from videochess_rl.rl.training import DoubleDqnLearner

ARTIFACT_ROOT = ROOT / "artifacts/m5"
SOURCE_ROOT = ROOT / ".agents/evidence/M5-source-recovered"
CONFIG = json.loads((ROOT / "configs/rl/m5-double-dqn-v1.json").read_text(encoding="utf-8"))
SOURCE_GROUPS = {20261105: "093992c50e893a7fdd92f2f95faafe28d4f1e73c7351a4a8179a3056c4e63b00",
                 20261106: "cdcc1fdc0ca0b324e49cfb8b0ff571496a554e9892dfb3620d6454a65ee16da0"}


def _load_source_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"failed to load recovered source {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _same(left: Any, right: Any) -> bool:
    if isinstance(left, torch.Tensor) and isinstance(right, torch.Tensor):
        return torch.equal(left, right)
    if isinstance(left, np.ndarray) and isinstance(right, np.ndarray):
        return np.array_equal(left, right)
    if type(left) is not type(right):
        return False
    if isinstance(left, dict):
        return left.keys() == right.keys() and all(_same(left[key], right[key]) for key in left)
    if isinstance(left, (tuple, list)):
        return len(left) == len(right) and all(_same(a, b) for a, b in zip(left, right))
    return left == right


def _numpy_rng_state() -> tuple[Any, ...]:
    state = np.random.get_state()
    return state[0], state[1].copy(), state[2], state[3], state[4]


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _latest_checkpoint(run_dir: Path) -> Path:
    candidates = []
    for path in run_dir.glob("*__resume-v2.pt"):
        name = path.name
        try:
            episode = int(name.split("__episodes-", 1)[1].split("__", 1)[0])
            decisions = int(name.split("__decisions-", 1)[1].split("__", 1)[0])
        except (IndexError, ValueError):
            raise ValueError(f"checkpoint filename lacks verified progress counters: {name}")
        candidates.append(((episode, decisions), path))
    if not candidates:
        raise FileNotFoundError(f"no resumable checkpoint exists in {run_dir}")
    return max(candidates, key=lambda item: item[0])[1]


def _learner(seed: int, arm: str, initial_snapshot: Path) -> DoubleDqnLearner:
    model, _ = load_evaluation_snapshot(initial_snapshot)
    # Separate model copies are loaded from the same immutable initialization.
    # The checkpoint restore replaces all model/optimizer/replay/RNG state.
    ddqn = CONFIG["double_dqn"]
    schedule = paired_seed_schedule(EXPERIMENT_ID, seed, 0)
    return DoubleDqnLearner(
        model,
        seed=int(schedule["replay_sampling_rng_seed"]),
        exploration_seed=int(schedule["exploration_rng_seed"]),
        device="cpu",
        config={
            "replay_capacity": ddqn["replay_capacity"],
            "replay_warmup_transitions": ddqn["replay_warmup_transitions"],
            "batch_size": ddqn["batch_size"],
            "learning_rate": ddqn["learning_rate"],
            "weight_decay": ddqn["weight_decay"],
            "update_interval_decisions": 4,
            "gamma": ddqn["gamma"],
            "target_sync_interval_gradient_updates": ddqn["target_sync_interval_gradient_updates"],
            "gradient_clip_norm": ddqn["gradient_clip_norm"],
        },
    )


def _restore_pair(seed: int, arm: str, old_checkpoint: Any, old_replay: Any) -> dict[str, Any]:
    pair = pair_identity(EXPERIMENT_ID, seed)
    run_id = run_identity(pair, arm, 0)
    run_dir = ARTIFACT_ROOT / "runs" / run_id
    summary = json.loads((run_dir / "run-summary.json").read_text(encoding="utf-8"))
    attempt = json.loads((run_dir / "attempt-record.json").read_text(encoding="utf-8"))
    if summary["code"]["source_sha256"] != SOURCE_GROUPS[seed]:
        raise ValueError(f"run source does not match its recorded training source group: {run_id}")
    if attempt.get("attempt_id") != "attempt-0000" or summary.get("resume_parent_checkpoint_sha256") is not None:
        raise ValueError(f"expected a fresh, non-resumed final-seed attempt: {run_id}")

    checkpoint = _latest_checkpoint(run_dir)
    checkpoint_bundle = load_training_checkpoint_bundle(checkpoint, verify_journal=False)
    initial_dir = ARTIFACT_ROOT / "runs" / run_identity(pair, arm, 0)
    initial_snapshot = next(initial_dir.glob("*stage-pre_rl*eval-snapshot-v2.pt"))
    old_learner = _learner(seed, arm, initial_snapshot)
    new_learner = _learner(seed, arm, initial_snapshot)
    expected = {"experiment_id": EXPERIMENT_ID, "pair_id": pair, "arm": arm, "training_seed": seed,
                "config_sha256": CONFIG["configuration_sha256"] if "configuration_sha256" in CONFIG
                else hashlib.sha256((ROOT / "configs/rl/m5-double-dqn-v1.json").read_bytes()).hexdigest()}

    started = time.monotonic()
    old_result = old_checkpoint.restore_training_checkpoint(checkpoint, old_learner, expected_identity=expected)
    old_global = (random.getstate(), _numpy_rng_state(), torch.get_rng_state().clone())
    new_result = restore_training_checkpoint(checkpoint, new_learner, expected_identity=expected)
    new_global = (random.getstate(), _numpy_rng_state(), torch.get_rng_state().clone())

    tests = {
        "online_network_exact": _same(old_learner.online.state_dict(), new_learner.online.state_dict()),
        "target_network_exact": _same(old_learner.target.state_dict(), new_learner.target.state_dict()),
        "optimizer_exact": _same(old_learner.optimizer.state_dict(), new_learner.optimizer.state_dict()),
        "counters_exact": _same(old_result["counters"], new_result["counters"]),
        "replay_order_exact": [r.transition_id for r in old_learner.replay.transitions]
            == [r.transition_id for r in new_learner.replay.transitions],
        "replay_counters_exact": (old_learner.replay.inserted_count, old_learner.replay.evicted_count)
            == (new_learner.replay.inserted_count, new_learner.replay.evicted_count),
        "replay_rng_exact": old_learner.replay.rng.getstate() == new_learner.replay.rng.getstate(),
        "exploration_rng_exact": old_learner.exploration_rng.getstate() == new_learner.exploration_rng.getstate(),
        "python_numpy_torch_rng_exact": _same(old_global, new_global),
    }
    if not all(tests.values()):
        raise AssertionError(f"historical/current restore differs for {run_id}: {tests}")
    old_batch = [row.transition_id for row in old_learner.replay.sample(CONFIG["double_dqn"]["batch_size"])]
    new_batch = [row.transition_id for row in new_learner.replay.sample(CONFIG["double_dqn"]["batch_size"])]
    if old_batch != new_batch or old_learner.replay.rng.getstate() != new_learner.replay.rng.getstate():
        raise AssertionError(f"next minibatch differs after restore for {run_id}")

    return {
        "run_id": run_id,
        "arm": arm,
        "training_seed": seed,
        "source_sha256": summary["code"]["source_sha256"],
        "checkpoint_path": checkpoint.relative_to(ROOT).as_posix(),
        "checkpoint_sha256": _sha256_file(checkpoint),
        "checkpoint_decisions": checkpoint_bundle["counters"]["valid_decisions"],
        "checkpoint_journal_prefix_records": checkpoint_bundle["journal"]["record_count"],
        "restoration_equivalence": tests,
        "next_minibatch_transition_ids": new_batch,
        "comparison_seconds": time.monotonic() - started,
    }


def verify() -> dict[str, Any]:
    old_replay = _load_source_module("videochess_rl.rl._m5_actual_recovered_replay", SOURCE_ROOT / "replay.py")
    old_checkpoint = _load_source_module("videochess_rl.rl._m5_actual_recovered_checkpoint", SOURCE_ROOT / "checkpoint.py")
    old_checkpoint.ReplayBuffer = old_replay.ReplayBuffer
    old_checkpoint.ReplayJournal = old_replay.ReplayJournal
    results = [_restore_pair(20261105, "scratch", old_checkpoint, old_replay),
               _restore_pair(20261106, "scratch", old_checkpoint, old_replay)]
    return {"schema": "videochess-m5-authentic-checkpoint-restore-equivalence/1.0",
            "read_only": True, "results": results}


def main() -> int:
    started = time.monotonic()
    report = verify()
    report["total_elapsed_seconds"] = time.monotonic() - started
    report["peak_process_rss_bytes"] = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024)
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
