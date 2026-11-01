"""Resolve and load the exact frozen M4/M5/M6-option policy population."""

from __future__ import annotations

import json
from pathlib import Path, PurePosixPath
from typing import Any

from videochess_rl.baselines import RandomLegalAgent, SimpleHeuristicAgent
from videochess_rl.m6.adapter import (
    M6PolicyAdapter,
    PolicyIdentity,
    load_m4_policy,
    load_m5_policy,
    sha256_file,
)
from videochess_rl.m7.protocol import load_frozen_config
from videochess_rl.rl.evaluate import QPolicy


class FrozenPolicyError(ValueError):
    """A frozen model, sidecar, manifest, or policy identity did not match."""


def _safe_root(root: str | Path, label: str) -> Path:
    supplied = Path(root).expanduser()
    if supplied.is_symlink():
        raise FrozenPolicyError(f"{label} artifact root must not be a symbolic link")
    resolved = supplied.resolve(strict=True)
    if not resolved.is_dir():
        raise FrozenPolicyError(f"{label} artifact root is missing or unsafe")
    return resolved


def _manifest_entries(root: Path, manifest_name: str, expected_sha256: str) -> dict[str, dict[str, Any]]:
    manifest_path = root / manifest_name
    if manifest_path.is_symlink() or not manifest_path.is_file() or sha256_file(manifest_path) != expected_sha256:
        raise FrozenPolicyError(f"accepted {manifest_name} identity differs from the frozen M7 roster")
    try:
        document = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise FrozenPolicyError(f"accepted {manifest_name} is not readable JSON") from exc
    files = document.get("files")
    if not isinstance(files, list):
        raise FrozenPolicyError(f"accepted {manifest_name} has no file inventory")
    entries: dict[str, dict[str, Any]] = {}
    for row in files:
        if not isinstance(row, dict) or not isinstance(row.get("path"), str):
            raise FrozenPolicyError(f"accepted {manifest_name} has a malformed file row")
        path = PurePosixPath(row["path"])
        if path.is_absolute() or ".." in path.parts or row["path"] in entries:
            raise FrozenPolicyError(f"accepted {manifest_name} contains an unsafe or duplicate path")
        entries[row["path"]] = row
    return entries


def _verify_m5_inputs(root: Path, config: dict[str, Any]) -> dict[str, tuple[Any, PolicyIdentity]]:
    m5 = config["accepted_inputs"]["m5"]
    root_manifest_sha = m5["root_manifest_sha256"]
    entries = _manifest_entries(root, "artifact-manifest.json", root_manifest_sha)
    from scripts.m5_artifact_manifests import verify_manifest

    manifest_path = root / "artifact-manifest.json"
    verified = verify_manifest(root, manifest_path)
    if verified.get("status") not in {"complete", "completed"}:
        raise FrozenPolicyError("accepted M5 root manifest is not a completed immutable inventory")
    roster: dict[str, tuple[Any, PolicyIdentity]] = {}
    for row in m5["policies"]:
        rel = row["artifact_relative_path"]
        posix = PurePosixPath(rel)
        if posix.is_absolute() or ".." in posix.parts:
            raise FrozenPolicyError("M5 checkpoint path escaped the accepted artifact root")
        checkpoint = root.joinpath(*posix.parts)
        sidecar = checkpoint.with_suffix(checkpoint.suffix + ".manifest.json")
        if checkpoint.is_symlink() or sidecar.is_symlink() or not checkpoint.is_file() or not sidecar.is_file():
            raise FrozenPolicyError(f"accepted M5 snapshot or sidecar is missing/unsafe: {row['policy_id']}")
        sidecar_rel = sidecar.relative_to(root).as_posix()
        checkpoint_record = entries.get(rel)
        sidecar_record = entries.get(sidecar_rel)
        if checkpoint_record is None or sidecar_record is None:
            raise FrozenPolicyError(f"accepted M5 manifest omits the snapshot or sidecar: {row['policy_id']}")
        actual_checkpoint_sha = sha256_file(checkpoint)
        actual_sidecar_sha = sha256_file(sidecar)
        if (
            actual_checkpoint_sha != row["checkpoint_file_sha256"]
            or checkpoint_record.get("sha256") != row["checkpoint_file_sha256"]
            or actual_sidecar_sha != row["sidecar_manifest_file_sha256"]
            or sidecar_record.get("sha256") != row["sidecar_manifest_file_sha256"]
        ):
            raise FrozenPolicyError(f"accepted M5 checkpoint/sidecar hash mismatch: {row['policy_id']}")
        sidecar_document = json.loads(sidecar.read_text(encoding="utf-8"))
        if (
            sidecar_document.get("sha256") != row["sidecar_embedded_checkpoint_sha256"]
            or sidecar_document.get("file") != checkpoint.name
            or sidecar_document.get("resumable") is not False
        ):
            raise FrozenPolicyError(f"accepted M5 sidecar metadata mismatch: {row['policy_id']}")
        try:
            policy, identity = load_m5_policy(
                checkpoint,
                policy_id=row["policy_id"],
                arm=row["arm"],
                training_seed=int(row["training_seed"]),
                expected_checkpoint_sha256=row["checkpoint_file_sha256"],
                expected_sidecar_sha256=row["sidecar_manifest_file_sha256"],
                root_manifest_sha256=root_manifest_sha,
                artifact_root=root,
            )
        except Exception as exc:
            raise FrozenPolicyError(f"accepted M5 checkpoint contract failed: {row['policy_id']}: {exc}") from exc
        if identity.valid_decisions != row["valid_training_decisions"] or identity.snapshot_stage != row["snapshot_stage"]:
            raise FrozenPolicyError(f"accepted M5 checkpoint metadata differs from roster: {row['policy_id']}")
        roster[row["policy_id"]] = (policy, identity)
    if len(roster) != 6:
        raise FrozenPolicyError("M7 requires exactly six unique accepted post-RL M5 policies")
    return roster


def load_frozen_policy_roster(
    config_path: str | Path,
    *,
    m4_artifact_root: str | Path,
    m5_artifact_root: str | Path,
) -> tuple[dict[str, tuple[Any, PolicyIdentity]], dict[str, Any]]:
    """Hash-verify accepted roots before constructing the nine policies."""
    config = load_frozen_config(config_path)
    m4_root = _safe_root(m4_artifact_root, "M4")
    m5_root = _safe_root(m5_artifact_root, "M5")
    roster = _verify_m5_inputs(m5_root, config)

    m4 = config["accepted_inputs"]["m4"]
    m4_entries = _manifest_entries(m4_root, "artifact_manifest.json", m4["root_manifest_sha256"])
    for rel, expected in (
        (m4["checkpoint_file"], m4["checkpoint_sha256"]),
        (m4["sidecar_file"], m4["sidecar_manifest_file_sha256"]),
    ):
        path = m4_root / rel
        item = m4_entries.get(rel)
        if path.is_symlink() or not path.is_file() or item is None:
            raise FrozenPolicyError(f"accepted M4 artifact is missing or unsafe: {rel}")
        if sha256_file(path) != expected or item.get("sha256") != expected:
            raise FrozenPolicyError(f"accepted M4 artifact hash mismatch: {rel}")
    if m4["metadata_sha256"] != m4["sidecar_metadata_sha256"]:
        raise FrozenPolicyError("M4 metadata checksum naming is inconsistent in the frozen config")
    try:
        m4_policy, m4_identity = load_m4_policy(
            m4_root,
            policy_id="m4-behavior-only-seed-20261024",
            expected_root_manifest_sha256=m4["root_manifest_sha256"],
            expected_checkpoint_sha256=m4["checkpoint_sha256"],
            expected_sidecar_sha256=m4["sidecar_manifest_file_sha256"],
        )
    except Exception as exc:
        raise FrozenPolicyError(f"accepted M4 behavior policy contract failed: {exc}") from exc
    if m4_identity.training_seed != m4["training_seed"]:
        raise FrozenPolicyError("accepted M4 training-seed metadata differs from the frozen roster")
    roster[m4_identity.policy_id] = (m4_policy, m4_identity)

    roster["random-legal"] = (
        RandomLegalAgent(),
        PolicyIdentity(policy_id="random-legal", policy_type="random_legal"),
    )
    roster["simple-heuristic"] = (
        SimpleHeuristicAgent(),
        PolicyIdentity(policy_id="simple-heuristic", policy_type="simple_heuristic"),
    )
    expected_ids = set(config["research_design"]["policy_ids"])
    if set(roster) != expected_ids or len(roster) != 9:
        raise FrozenPolicyError("loaded policy IDs differ from the exactly frozen nine-policy roster")
    return roster, config


def make_atari_adapters(
    roster: dict[str, tuple[Any, PolicyIdentity]],
    *,
    ale_seed: int,
) -> dict[str, M6PolicyAdapter]:
    """Create fresh episode adapters so frame histories cannot leak across games."""
    return {
        policy_id: M6PolicyAdapter(policy, identity, rng_seed=ale_seed)
        for policy_id, (policy, identity) in roster.items()
    }
