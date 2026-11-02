#!/usr/bin/env python3
"""Verify and restore the latest compatible M5 episode-boundary checkpoint."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import resource
import sys
import time
from pathlib import Path

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from videochess_rl.m5_seeding import EXPERIMENT_ID, pair_identity, run_identity, paired_seed_schedule
from videochess_rl.rl.checkpoint import load_evaluation_snapshot, restore_training_checkpoint
from videochess_rl.rl.cli import ARTIFACT_ROOT, config_hash, load_config, source_hash, _latest_verified_resume
from videochess_rl.rl.training import DoubleDqnLearner


def _same(left, right) -> bool:
    if isinstance(left, torch.Tensor) and isinstance(right, torch.Tensor):
        return torch.equal(left, right)
    if isinstance(left, np.ndarray) and isinstance(right, np.ndarray):
        return np.array_equal(left, right)
    if isinstance(left, dict) and isinstance(right, dict):
        return left.keys() == right.keys() and all(_same(left[key], right[key]) for key in left)
    if isinstance(left, (list, tuple)) and isinstance(right, (list, tuple)):
        return len(left) == len(right) and all(_same(a, b) for a, b in zip(left, right))
    return left == right


def verify(training_seed: int, arm: str) -> dict[str, object]:
    config = load_config()
    if training_seed not in config["training"]["paired_seeds"] or arm not in {"warm", "scratch"}:
        raise ValueError("seed or arm is outside the authorized M5 paired design")
    pair_id = pair_identity(EXPERIMENT_ID, training_seed)
    checkpoint, bundle = _latest_verified_resume(pair_id, arm, training_seed)
    if checkpoint is None or bundle is None:
        raise FileNotFoundError("no verified episode-boundary checkpoint exists for this pair/arm")
    initial_run = run_identity(pair_id, arm, 0)
    initial_dir = ARTIFACT_ROOT / "runs" / initial_run
    snapshot = next(initial_dir.glob("*stage-pre_rl*eval-snapshot-v2.pt"))
    model, metadata = load_evaluation_snapshot(snapshot)
    schedule = paired_seed_schedule(EXPERIMENT_ID, training_seed, 0)
    ddqn = config["double_dqn"]
    learner = DoubleDqnLearner(model, seed=int(schedule["replay_sampling_rng_seed"]),
        exploration_seed=int(schedule["exploration_rng_seed"]), device="cpu", config={
            "replay_capacity":ddqn["replay_capacity"],"replay_warmup_transitions":ddqn["replay_warmup_transitions"],
            "batch_size":ddqn["batch_size"],"learning_rate":ddqn["learning_rate"],
            "weight_decay":ddqn["weight_decay"],"update_interval_decisions":4,"gamma":ddqn["gamma"],
            "target_sync_interval_gradient_updates":ddqn["target_sync_interval_gradient_updates"],
            "gradient_clip_norm":ddqn["gradient_clip_norm"]})
    restored = restore_training_checkpoint(checkpoint, learner, expected_identity={
        "experiment_id":EXPERIMENT_ID,"pair_id":pair_id,"arm":arm,"training_seed":training_seed,
        "config_sha256":config_hash()})
    counters = restored["counters"]
    if learner.valid_decisions != learner.transitions or len(learner.replay) > learner.replay.capacity:
        raise ValueError("restored transition, decision, or replay counters are inconsistent")
    if counters != bundle["counters"]:
        raise ValueError("restored counters differ from the immutable checkpoint payload")
    if not _same(learner.online.state_dict(), bundle["online"]):
        raise ValueError("restored online network differs from the immutable checkpoint payload")
    if not _same(learner.target.state_dict(), bundle["target"]):
        raise ValueError("restored target network differs from the immutable checkpoint payload")
    if not _same(learner.optimizer.state_dict(), bundle["optimizer"]):
        raise ValueError("restored optimizer differs from the immutable checkpoint payload")
    replay_control = bundle["replay_control"]
    replay_rng = random.Random()
    from videochess_rl.rl.checkpoint import _nested_tuple
    replay_rng.setstate(_nested_tuple(replay_control["rng_state"]))
    if learner.replay.rng.getstate() != replay_rng.getstate():
        raise ValueError("restored replay RNG differs from the immutable checkpoint payload")
    exploration_rng = random.Random()
    exploration_rng.setstate(_nested_tuple(bundle["exploration_rng_state"]))
    if learner.exploration_rng.getstate() != exploration_rng.getstate():
        raise ValueError("restored exploration RNG differs from the immutable checkpoint payload")
    if random.getstate() != _nested_tuple(bundle["python_rng_state"]):
        raise ValueError("restored Python RNG differs from the immutable checkpoint payload")
    expected_numpy = bundle["numpy_rng_state"]
    actual_numpy = np.random.get_state()
    if (actual_numpy[0] != expected_numpy["bit_generator"]
            or not np.array_equal(actual_numpy[1], np.asarray(expected_numpy["keys"], dtype=np.uint32))
            or actual_numpy[2:] != (int(expected_numpy["position"]), int(expected_numpy["has_gauss"]),
                                    float(expected_numpy["cached_gaussian"]))):
        raise ValueError("restored NumPy RNG differs from the immutable checkpoint payload")
    if not torch.equal(torch.get_rng_state(), bundle["torch_rng_state"].cpu()):
        raise ValueError("restored PyTorch CPU RNG differs from the immutable checkpoint payload")
    replay_ids = "\n".join(row.transition_id for row in learner.replay.transitions).encode("ascii")
    replay_identity = restored["restored_replay"]
    if (replay_identity["transition_ids_sha256"] != hashlib.sha256(replay_ids).hexdigest()
            or replay_identity["rows"] != len(learner.replay)
            or learner.replay.inserted_count != replay_control["inserted_count"]
            or learner.replay.evicted_count != replay_control["evicted_count"]):
        raise ValueError("restored bounded replay rows or counters differ from verified recovery state")
    manifest_path = checkpoint.with_suffix(checkpoint.suffix + ".manifest.json")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    return {"result":"PASS","checkpoint_path":str(checkpoint),"checkpoint_sha256":manifest["sha256"],
        "checkpoint_code_sha256":bundle["identity"].get("code_sha256"),"current_source_sha256":source_hash(),
        "configuration_sha256":config_hash(),"initialization_snapshot_sha256":hashlib.sha256(snapshot.read_bytes()).hexdigest(),
        "pair_id":pair_id,"arm":arm,"training_seed":training_seed,
        "valid_decisions":learner.valid_decisions,"transitions":learner.transitions,
        "completed_episodes":learner.completed_episodes,"optimizer_updates":learner.optimizer_updates,
        "target_syncs":learner.target_syncs,"replay_rows":len(learner.replay),
        "replay_identity":replay_identity,
        "restoration_checks":{"online_network":"exact_tensor_match","target_network":"exact_tensor_match",
            "optimizer":"exact_state_match","replay":"verified_full_journal_chain_and_exact_bounded_tail",
            "counters":"exact_match","exploration_rng":"exact_match","replay_rng":"exact_match",
            "python_numpy_torch_rng":"exact_match"},
        "journal_prefix":bundle["journal"],"counters":counters}


def main() -> int:
    started=time.monotonic()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--training-seed", type=int, required=True)
    parser.add_argument("--arm", choices=("warm", "scratch"), required=True)
    args = parser.parse_args()
    result=verify(args.training_seed, args.arm)
    result["verification_elapsed_seconds"]=time.monotonic()-started
    result["verification_peak_rss_bytes"]=int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024)
    print(json.dumps(result, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
