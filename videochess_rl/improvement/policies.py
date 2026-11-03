"""Verified policy loaders shared by Atari evaluation and the live viewer."""
from __future__ import annotations

import hashlib
from pathlib import Path

from videochess_rl.m6.adapter import M6PolicyAdapter, PolicyIdentity
from videochess_rl.model.checkpoint import load_checkpoint
from videochess_rl.model.inference import BehaviorPolicy
from videochess_rl.rl.checkpoint import load_evaluation_snapshot
from videochess_rl.rl.evaluate import QPolicy

from .common import ROOT

EXPERIMENT = "videochess-improvement-20261103-v1"
M4_PATH = ROOT / "artifacts/improvement" / EXPERIMENT / "m4-a/epoch-22.pt"
M4_SHA256 = "cf5e437ff4e2d6a8e85739df751dec33f16b7bc4c92268f996ec4c612d62feed"
M4_TRAINING_SEED = 20261103
TRAINING_SEED = 20261103
M4_DATASET_RELEASE = "f2b3b52724958ffa845894681013cdc40915da179bbec3ae011087fe8a8ce0cc"
OFFICIAL = ROOT / "artifacts/improvement" / EXPERIMENT / "official"
ATTEMPT = OFFICIAL / "attempt-0000"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_demo_policy(name: str, *, checkpoint: str | Path | None = None,
                     expected_sha256: str | None = None,
                     policy_rng_seed: int = 20261103):
    """Load a fixed-provenance policy; seed its adapter independently of model provenance.

    ``policy_rng_seed`` is the deterministic policy-adapter RNG domain for this
    ALE session. It is deliberately not compared with checkpoint training
    metadata; an Atari reset seed may vary without changing model identity.
    """
    if name == "m4-a":
        path = Path(checkpoint) if checkpoint else M4_PATH
        digest = sha256(path)
        if digest != M4_SHA256 or expected_sha256 not in (None, M4_SHA256):
            raise ValueError("M4-A checkpoint identity mismatch")
        model, bundle = load_checkpoint(path, device="cpu")
        meta = bundle.get("metadata") if isinstance(bundle, dict) else None
        if not isinstance(meta, dict):
            raise ValueError("M4-A checkpoint metadata is missing or malformed")
        expected_m4 = {
            "checkpoint_role": "improvement_m4",
            "run_id": EXPERIMENT,
            "seed": M4_TRAINING_SEED,
            "dataset_release_id": M4_DATASET_RELEASE,
            "input_schema": "videochess-model-input/1.0",
            "model_schema": "videochess-behavior-scorer/1.0",
        }
        if any(meta.get(key) != value for key, value in expected_m4.items()):
            raise ValueError("M4-A checkpoint immutable training metadata mismatch")
        model.eval()
        policy = BehaviorPolicy(model, checkpoint_sha256=digest)
        identity = PolicyIdentity(policy_id="M4-A_behavior_cloning", policy_type="behavior_cloning",
            checkpoint_sha256=digest, training_seed=meta["seed"],
            artifact_path=path.as_posix())
    elif name == "double-dqn":
        if checkpoint is None:
            raise ValueError("Double DQN requires an explicit selected snapshot path")
        path = Path(checkpoint)
        digest = sha256(path)
        if expected_sha256 is None or digest != expected_sha256:
            raise ValueError("Double DQN snapshot SHA-256 is missing or mismatched")
        model, meta = load_evaluation_snapshot(path, device="cpu")
        run = __import__("json").loads((ATTEMPT / "run.json").read_text())
        identity_data = run["identity"]
        if (identity_data.get("experiment_id") != EXPERIMENT
                or identity_data.get("training_seed") != TRAINING_SEED
                or identity_data.get("execution_kind") != "official"):
            raise ValueError("official Double DQN run identity is missing or inconsistent")
        if (run.get("valid_decisions") != 250000 or run.get("optimizer_updates") != 62245
                or run.get("target_syncs") != 124 or run.get("completed_episodes") != 3203):
            raise ValueError("official Double DQN run completion metadata is inconsistent")
        if (meta.get("experiment_id") != EXPERIMENT or meta.get("execution_kind") != "official"
                or meta.get("training_seed") != identity_data["training_seed"] or meta.get("q_only_evaluation") is not True
                or meta.get("resumable") is not False or meta.get("code_sha256") != identity_data["code_sha256"]
                or meta.get("config_sha256") != identity_data["config_sha256"]
                or meta.get("m4_sha256") != M4_SHA256):
            raise ValueError("Double DQN snapshot metadata does not match the completed official run")
        policy = QPolicy(model, policy_id=f"double_dqn_{meta['valid_decisions']}", checkpoint_sha256=digest)
        identity = PolicyIdentity(policy_id=policy.policy_id, policy_type="double_dqn_q_only",
            checkpoint_sha256=digest, snapshot_stage="evaluation_only", valid_decisions=meta["valid_decisions"],
            training_seed=meta.get("training_seed"), artifact_path=path.as_posix())
    else:
        raise ValueError("policy must be 'double-dqn' or 'm4-a'")
    adapter = M6PolicyAdapter(policy, identity, rng_seed=policy_rng_seed)
    return adapter, identity
