"""Hash-verified, inference-safe M4 checkpoint bundles and artifact manifests."""

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

from .features import INPUT_SCHEMA
from .network import MODEL_SCHEMA, BehaviorScorer, ModelConfig

CHECKPOINT_SCHEMA = "videochess-m4-checkpoint/1.0"
ARTIFACT_MANIFEST_SCHEMA = "videochess-m4-artifacts/1.0"


def _sha256(path: Path) -> tuple[str, int]:
    digestor = hashlib.sha256()
    size = 0
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digestor.update(chunk)
            size += len(chunk)
    return digestor.hexdigest(), size


def _json_bytes(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8")


def _atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp_name, path)
    finally:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass


def _to_plain(value: Any) -> Any:
    if isinstance(value, tuple):
        return [_to_plain(item) for item in value]
    if isinstance(value, list):
        return [_to_plain(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _to_plain(item) for key, item in value.items()}
    if isinstance(value, np.generic):
        return value.item()
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    raise TypeError(f"RNG/checkpoint metadata value is not safely serializable: {type(value).__name__}")


def capture_rng_state() -> dict[str, Any]:
    """Return primitive/tensor RNG metadata suitable for weights-only loading."""
    numpy_state = np.random.get_state()
    return {
        "python_random": _to_plain(random.getstate()),
        "numpy_random": {
            "bit_generator": numpy_state[0],
            "keys": numpy_state[1].astype(np.uint32).tolist(),
            "position": int(numpy_state[2]),
            "has_gauss": int(numpy_state[3]),
            "cached_gaussian": float(numpy_state[4]),
        },
        "torch_cpu": torch.get_rng_state().clone(),
    }


def restore_rng_state(state: dict[str, Any]) -> None:
    def nested_tuple(value: Any) -> Any:
        return tuple(nested_tuple(item) for item in value) if isinstance(value, list) else value

    random.setstate(nested_tuple(state["python_random"]))
    numpy_state = state["numpy_random"]
    np.random.set_state((
        numpy_state["bit_generator"],
        np.asarray(numpy_state["keys"], dtype=np.uint32),
        int(numpy_state["position"]),
        int(numpy_state["has_gauss"]),
        float(numpy_state["cached_gaussian"]),
    ))
    torch.set_rng_state(state["torch_cpu"].cpu())


def save_checkpoint(
    path: str | Path,
    model: BehaviorScorer,
    *,
    metadata: dict[str, Any],
    optimizer_state: dict[str, Any] | None = None,
    rng_state: dict[str, Any] | None = None,
) -> dict[str, Any]:
    requested_target = Path(path).expanduser()
    if requested_target.is_symlink():
        raise ValueError("checkpoint must not be a symlink")
    target = requested_target.resolve()
    if not isinstance(metadata, dict):
        raise TypeError("checkpoint metadata must be an object")
    try:
        metadata_bytes = _json_bytes(metadata)
    except (TypeError, ValueError) as exc:
        raise ValueError("checkpoint metadata must be finite JSON-compatible data") from exc
    if model.trainable_parameter_count >= 250_000:
        raise ValueError("M4 model exceeds the strict 250,000 trainable parameter cap")
    if metadata.get("input_schema") != INPUT_SCHEMA or metadata.get("model_schema") != MODEL_SCHEMA:
        raise ValueError("checkpoint metadata must declare the accepted input and model schemas")
    if metadata.get("parameter_count") != model.trainable_parameter_count:
        raise ValueError("checkpoint parameter count metadata differs from the actual model")
    bundle = {
        "checkpoint_schema": CHECKPOINT_SCHEMA,
        "metadata": metadata,
        "model_state": {key: tensor.detach().cpu() for key, tensor in model.state_dict().items()},
        "optimizer_state": optimizer_state or {},
        "rng_state": rng_state or capture_rng_state(),
    }
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{target.name}.", suffix=".tmp", dir=target.parent)
    os.close(fd)
    try:
        torch.save(bundle, temp_name)
        with open(temp_name, "rb") as stream:
            os.fsync(stream.fileno())
        os.replace(temp_name, target)
    finally:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass
    sha, size = _sha256(target)
    manifest_path = target.with_suffix(target.suffix + ".manifest.json")
    manifest = {
        "schema": CHECKPOINT_SCHEMA,
        "checkpoint_file": target.name,
        "checkpoint_sha256": sha,
        "checkpoint_size_bytes": size,
        "metadata_sha256": hashlib.sha256(metadata_bytes).hexdigest(),
        "input_schema": INPUT_SCHEMA,
        "model_schema": MODEL_SCHEMA,
        "parameter_count": model.trainable_parameter_count,
    }
    _atomic_write(manifest_path, _json_bytes(manifest))
    verify_checkpoint(target, manifest_path=manifest_path)
    return manifest


def verify_checkpoint(path: str | Path, *, manifest_path: str | Path | None = None) -> dict[str, Any]:
    requested_target = Path(path).expanduser()
    if requested_target.is_symlink() or not requested_target.is_file():
        raise ValueError("checkpoint must be a regular file, not a symlink")
    target = requested_target.resolve(strict=True)
    if not target.is_file():
        raise ValueError("checkpoint must be a regular file, not a symlink")
    requested_sidecar = (
        Path(manifest_path).expanduser()
        if manifest_path
        else requested_target.with_suffix(requested_target.suffix + ".manifest.json")
    )
    if requested_sidecar.is_symlink() or not requested_sidecar.is_file():
        raise ValueError("checkpoint integrity manifest is missing or unsafe")
    sidecar = requested_sidecar.resolve(strict=True)
    if not sidecar.is_file():
        raise ValueError("checkpoint integrity manifest is missing or unsafe")
    manifest = json.loads(sidecar.read_text(encoding="utf-8"))
    if manifest.get("schema") != CHECKPOINT_SCHEMA or manifest.get("checkpoint_file") != target.name:
        raise ValueError("checkpoint manifest schema or filename mismatch")
    sha, size = _sha256(target)
    if sha != manifest.get("checkpoint_sha256") or size != manifest.get("checkpoint_size_bytes"):
        raise ValueError("checkpoint checksum or size mismatch")
    if manifest.get("input_schema") != INPUT_SCHEMA or manifest.get("model_schema") != MODEL_SCHEMA:
        raise ValueError("checkpoint manifest declares an unsupported model interface")
    return manifest


def load_checkpoint(
    path: str | Path,
    *,
    device: str | torch.device = "cpu",
    expected_release_id: str | None = None,
    expected_split_sha256: str | None = None,
) -> tuple[BehaviorScorer, dict[str, Any]]:
    target = Path(path).expanduser()
    if target.is_symlink():
        raise ValueError("checkpoint must be a regular file, not a symlink")
    manifest = verify_checkpoint(target)
    # weights_only prevents arbitrary Python object construction from artifact files.
    bundle = torch.load(target, map_location=device, weights_only=True)
    if bundle.get("checkpoint_schema") != CHECKPOINT_SCHEMA:
        raise ValueError("unsupported checkpoint bundle schema")
    metadata = bundle.get("metadata")
    if not isinstance(metadata, dict):
        raise ValueError("checkpoint metadata is missing")
    metadata_hash = hashlib.sha256(_json_bytes(metadata)).hexdigest()
    if metadata_hash != manifest.get("metadata_sha256"):
        raise ValueError("checkpoint metadata checksum mismatch")
    if metadata.get("input_schema") != INPUT_SCHEMA or metadata.get("model_schema") != MODEL_SCHEMA:
        raise ValueError("checkpoint metadata declares unsupported model interfaces")
    if expected_release_id and metadata.get("dataset_release_id") != expected_release_id:
        raise ValueError("checkpoint dataset release identity mismatch")
    if expected_split_sha256 and metadata.get("split_assignment_sha256") != expected_split_sha256:
        raise ValueError("checkpoint split assignment identity mismatch")
    config_data = dict(metadata.get("model_config", {}))
    for key in ("conv_widths", "history_embedding_dims"):
        if key in config_data:
            config_data[key] = tuple(config_data[key])
    config = ModelConfig(**config_data)
    model = BehaviorScorer(config).to(device)
    model.load_state_dict(bundle["model_state"], strict=True)
    if model.trainable_parameter_count != metadata.get("parameter_count"):
        raise ValueError("checkpoint model parameter count does not match its metadata")
    if model.trainable_parameter_count != manifest.get("parameter_count"):
        raise ValueError("checkpoint model parameter count does not match its integrity manifest")
    model.eval()
    return model, bundle


def write_artifact_manifest(directory: str | Path) -> dict[str, Any]:
    requested_root = Path(directory).expanduser()
    if requested_root.is_symlink():
        raise ValueError("artifact directory must not be a symlink")
    root = requested_root.resolve(strict=True)
    files: list[dict[str, Any]] = []
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise ValueError(f"artifact directory contains a symlink: {path.relative_to(root)}")
        if path.is_file() and path.name != "artifact_manifest.json":
            sha, size = _sha256(path)
            files.append({"path": path.relative_to(root).as_posix(), "sha256": sha, "size_bytes": size})
    manifest = {"schema": ARTIFACT_MANIFEST_SCHEMA, "files": files}
    _atomic_write(root / "artifact_manifest.json", _json_bytes(manifest))
    return manifest


def verify_artifact_manifest(directory: str | Path) -> dict[str, Any]:
    requested_root = Path(directory).expanduser()
    if requested_root.is_symlink():
        raise ValueError("artifact directory must not be a symlink")
    root = requested_root.resolve(strict=True)
    manifest_path = root / "artifact_manifest.json"
    if not manifest_path.is_file() or manifest_path.is_symlink():
        raise ValueError("artifact_manifest.json is missing or unsafe")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("schema") != ARTIFACT_MANIFEST_SCHEMA or not isinstance(manifest.get("files"), list):
        raise ValueError("unsupported M4 artifact manifest")
    expected: dict[str, tuple[str, int]] = {}
    for entry in manifest["files"]:
        rel = entry.get("path")
        if not isinstance(rel, str) or Path(rel).is_absolute() or ".." in Path(rel).parts or rel in expected:
            raise ValueError("unsafe or duplicate artifact path")
        path = root / rel
        current = root
        has_symlink_component = False
        for component in Path(rel).parts:
            current = current / component
            if current.is_symlink():
                has_symlink_component = True
                break
        if has_symlink_component or not path.is_file():
            raise ValueError(f"artifact missing or unsafe: {rel}")
        sha, size = _sha256(path)
        if sha != entry.get("sha256") or size != entry.get("size_bytes"):
            raise ValueError(f"artifact checksum or size mismatch: {rel}")
        expected[rel] = (sha, size)
    actual = {
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_file() and path.name != "artifact_manifest.json"
    }
    if actual != set(expected):
        raise ValueError("artifact directory file set differs from its integrity manifest")
    return manifest
