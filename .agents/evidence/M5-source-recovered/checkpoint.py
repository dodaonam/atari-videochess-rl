"""Atomic, hash-verified M5 training checkpoint and frozen policy snapshots."""

from __future__ import annotations

import hashlib
import json
import os
import random
import tempfile
from pathlib import Path
from typing import Any

import numpy as np
import torch

from .network import QScorer, clone_target
from .replay import ReplayBuffer, ReplayJournal

CHECKPOINT_SCHEMA = "videochess-ddqn-checkpoint/2.0"
SNAPSHOT_SCHEMA = "videochess-ddqn-evaluation-snapshot/2.0"


def _sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _load_checkpoint_payload(path: Path, *, map_location: str | torch.device = "cpu") -> dict[str, Any]:
    """Load this program's hash-verified checkpoint using the restricted unpickler.

    PyTorch versions that expose ``TorchVersion`` serialize it as a string
    subclass. Older locally-created M5 bundles may contain that value in the
    environment identity. Allowlisting that inert string subclass keeps
    ``weights_only=True`` enabled while preserving recovery compatibility.
    """
    version_type = type(torch.__version__)
    safe_globals = getattr(torch.serialization, "safe_globals", None)
    if version_type.__name__ == "TorchVersion" and safe_globals is not None:
        with safe_globals([version_type]):
            return torch.load(path, map_location=map_location, weights_only=True)
    return torch.load(path, map_location=map_location, weights_only=True)


def _atomic(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data); f.flush(); os.fsync(f.fileno())
        os.replace(name, path)
        dir_fd = os.open(path.parent, os.O_DIRECTORY)
        try: os.fsync(dir_fd)
        finally: os.close(dir_fd)
    finally:
        try: os.unlink(name)
        except FileNotFoundError: pass
        dir_fd=os.open(path.parent,os.O_DIRECTORY)
        try: os.fsync(dir_fd)
        finally: os.close(dir_fd)


def save_training_checkpoint(path: str | Path, learner: Any, *, identity: dict[str, Any],
                             journal: ReplayJournal, journal_head: dict[str, Any],
                             episode_complete: bool, resource_accounting: dict[str, Any]) -> dict[str, Any]:
    if not episode_complete:
        raise ValueError("resumable checkpoints are allowed only at completed episode boundaries")
    target = Path(path)
    sidecar = target.with_suffix(target.suffix + ".manifest.json")
    if target.is_symlink() or sidecar.is_symlink() or target.exists() or sidecar.exists():
        raise FileExistsError("refusing to overwrite an existing checkpoint identity")
    target.parent.mkdir(parents=True,exist_ok=True)
    replay_state = learner.replay.state_dict()
    replay_state.pop("rows")
    bundle = {
        "schema": CHECKPOINT_SCHEMA,
        "identity": identity,
        "online": {k: v.detach().cpu() for k, v in learner.online.state_dict().items()},
        "target": {k: v.detach().cpu() for k, v in learner.target.state_dict().items()},
        "optimizer": learner.optimizer.state_dict(),
        "replay_control": replay_state,
        "journal": {"path": str(journal.path), **journal_head},
        "counters": {k: int(getattr(learner, k)) for k in (
            "valid_decisions", "transitions", "optimizer_updates", "completed_episodes", "target_syncs", "invalid_transitions")},
        "exploration_rng_state": learner.exploration_rng.getstate(),
        "python_rng_state": random.getstate(),
        "numpy_rng_state": {"bit_generator":np.random.get_state()[0],"keys":np.random.get_state()[1].tolist(),
                             "position":int(np.random.get_state()[2]),"has_gauss":int(np.random.get_state()[3]),
                             "cached_gaussian":float(np.random.get_state()[4])},
        "torch_rng_state": torch.get_rng_state().cpu(),
        "torch_cuda_rng_states":torch.cuda.get_rng_state_all() if torch.cuda.is_available() else [],
        "resource_accounting": resource_accounting,
    }
    fd,name=tempfile.mkstemp(prefix=f".{target.name}.",suffix=".tmp",dir=target.parent)
    os.close(fd); temp=Path(name)
    try:
        torch.save(bundle,temp)
        with temp.open("rb") as f: os.fsync(f.fileno())
        os.replace(temp,target)
    finally:
        try: temp.unlink()
        except FileNotFoundError: pass
    dirfd = os.open(target.parent, os.O_DIRECTORY)
    try: os.fsync(dirfd)
    finally: os.close(dirfd)
    manifest = {"schema": CHECKPOINT_SCHEMA, "file": target.name, "sha256": _sha(target),
                "size_bytes": target.stat().st_size, "journal_prefix": journal_head}
    data = (json.dumps(manifest, sort_keys=True, indent=2) + "\n").encode()
    _atomic(sidecar, data)
    verify_training_checkpoint(target,verify_journal=False)
    return manifest


def verify_training_checkpoint(path: str | Path, *, expected_code_sha256: str | None = None,
                               verify_journal: bool = True) -> dict[str, Any]:
    target = Path(path); sidecar = target.with_suffix(target.suffix + ".manifest.json")
    if target.is_symlink() or sidecar.is_symlink() or not target.is_file() or not sidecar.is_file():
        raise ValueError("checkpoint or integrity sidecar is missing/unsafe")
    manifest = json.loads(sidecar.read_text())
    if manifest.get("schema") != CHECKPOINT_SCHEMA or manifest.get("file") != target.name:
        raise ValueError("unsupported or mismatched checkpoint sidecar")
    if manifest.get("sha256") != _sha(target) or manifest.get("size_bytes") != target.stat().st_size:
        raise ValueError("checkpoint checksum/size mismatch")
    bundle = _load_checkpoint_payload(target, map_location="cpu")
    if bundle.get("schema") != CHECKPOINT_SCHEMA:
        raise ValueError("unsupported resumable checkpoint schema")
    journal = bundle.get("journal", {})
    expected_head = manifest.get("journal_prefix")
    if not journal or journal.get("record_count") != expected_head.get("record_count") or journal.get("chain_sha256") != expected_head.get("chain_sha256"):
        raise ValueError("checkpoint journal pointer differs from sidecar")
    if verify_journal:
        ReplayJournal(journal["path"],verify_existing=False).verify(record_count=journal["record_count"],
            chain_sha256=journal["chain_sha256"])
    if expected_code_sha256 and bundle.get("identity", {}).get("code_sha256") != expected_code_sha256:
        raise ValueError("checkpoint code revision/hash is incompatible")
    return manifest


def load_training_checkpoint_bundle(path: str | Path, *, verify_journal: bool = True) -> dict[str, Any]:
    """Return a training bundle only after validating its immutable sidecar."""
    target = Path(path)
    verify_training_checkpoint(target, verify_journal=verify_journal)
    return _load_checkpoint_payload(target, map_location="cpu")


def restore_training_checkpoint(path: str | Path, learner: Any, *, expected_identity: dict[str, Any] | None = None) -> dict[str, Any]:
    target = Path(path); verify_training_checkpoint(target,verify_journal=True)
    bundle = _load_checkpoint_payload(target, map_location=learner.device)
    if expected_identity:
        for key, value in expected_identity.items():
            if bundle["identity"].get(key) != value:
                raise ValueError(f"checkpoint identity mismatch for {key}")
    learner.online.load_state_dict(bundle["online"], strict=True)
    learner.target.load_state_dict(bundle["target"], strict=True)
    learner.optimizer.load_state_dict(bundle["optimizer"])
    j = bundle["journal"]
    rows = ReplayJournal(j["path"],verify_existing=False).verify(record_count=j["record_count"], chain_sha256=j["chain_sha256"])
    restored = ReplayBuffer(learner.replay.capacity, seed=0)
    for row in rows[-learner.replay.capacity:]: restored.insert(row)
    replay_control = bundle["replay_control"]
    restored.inserted_count = int(replay_control["inserted_count"])
    restored.evicted_count = int(replay_control["evicted_count"])
    restored.rng.setstate(_nested_tuple(replay_control["rng_state"]))
    learner.replay = restored
    for key, value in bundle["counters"].items(): setattr(learner, key, int(value))
    learner.exploration_rng.setstate(_nested_tuple(bundle["exploration_rng_state"]))
    random.setstate(_nested_tuple(bundle["python_rng_state"]))
    torch.set_rng_state(bundle["torch_rng_state"].cpu())
    ns=bundle["numpy_rng_state"]
    np.random.set_state((ns["bit_generator"],np.asarray(ns["keys"],dtype=np.uint32),int(ns["position"]),
                         int(ns["has_gauss"]),float(ns["cached_gaussian"])))
    if bundle.get("torch_cuda_rng_states") and torch.cuda.is_available():
        torch.cuda.set_rng_state_all(bundle["torch_cuda_rng_states"])
    return {"identity": bundle["identity"], "counters": bundle["counters"], "journal": j}


def _nested_tuple(value: Any) -> Any:
    return tuple(_nested_tuple(x) for x in value) if isinstance(value, list) else value


def save_evaluation_snapshot(path: str | Path, model: QScorer, *, metadata: dict[str, Any]) -> dict[str, Any]:
    """Write a non-resumable online policy artifact with explicit frozen semantics."""
    if metadata.get("schema") != SNAPSHOT_SCHEMA or metadata.get("valid_decisions") not in (0, 10000, 20000, 30000, 40000, 50000):
        raise ValueError("invalid evaluation snapshot identity or decision boundary")
    if metadata.get("resumable") is not False:
        raise ValueError("evaluation snapshots are never resumable")
    target = Path(path)
    sidecar = target.with_suffix(target.suffix + ".manifest.json")
    if target.exists() or sidecar.exists(): raise FileExistsError("refusing to overwrite policy snapshot or its manifest")
    bundle = {"schema": SNAPSHOT_SCHEMA, "resumable": False, "metadata": metadata,
              "online": {k: v.detach().cpu() for k, v in model.state_dict().items()}}
    target.parent.mkdir(parents=True, exist_ok=True)
    fd,name=tempfile.mkstemp(prefix=f".{target.name}.",suffix=".tmp",dir=target.parent)
    os.close(fd); temp=Path(name)
    try:
        torch.save(bundle,temp)
        with temp.open("rb") as f: os.fsync(f.fileno())
        os.replace(temp,target)
    finally:
        try: temp.unlink()
        except FileNotFoundError: pass
    manifest = {"schema": SNAPSHOT_SCHEMA, "file": target.name, "sha256": _sha(target),
                "size_bytes": target.stat().st_size, "resumable": False}
    _atomic(sidecar, (json.dumps(manifest, sort_keys=True, indent=2)+"\n").encode())
    return manifest


def load_evaluation_snapshot(path: str | Path, *, device: str = "cpu") -> tuple[QScorer, dict[str, Any]]:
    target = Path(path); sidecar_path=target.with_suffix(target.suffix+".manifest.json")
    if target.is_symlink() or sidecar_path.is_symlink() or not target.is_file() or not sidecar_path.is_file():
        raise ValueError("snapshot or its manifest is missing/unsafe")
    sidecar = json.loads(sidecar_path.read_text())
    if (sidecar.get("schema") != SNAPSHOT_SCHEMA or sidecar.get("file")!=target.name
            or sidecar.get("resumable") is not False or sidecar.get("sha256") != _sha(target)
            or sidecar.get("size_bytes")!=target.stat().st_size):
        raise ValueError("invalid non-resumable evaluation snapshot")
    bundle = torch.load(target, map_location=device, weights_only=True)
    if bundle.get("schema") != SNAPSHOT_SCHEMA or bundle.get("resumable") is not False:
        raise ValueError("snapshot bundle schema/role mismatch")
    metadata = bundle["metadata"]
    cfg = dict(metadata["model_config"])
    cfg["conv_widths"] = tuple(cfg["conv_widths"]); cfg["history_embedding_dims"] = tuple(cfg["history_embedding_dims"])
    model = QScorer(__import__('videochess_rl.model.network', fromlist=['ModelConfig']).ModelConfig(**cfg), seed=0).to(device)
    model.load_state_dict(bundle["online"], strict=True); model.eval()
    return model, metadata
