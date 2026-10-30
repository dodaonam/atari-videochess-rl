#!/usr/bin/env python3
"""Reconcile immutable M5 run/evaluation source identities with Git/checkpoint evidence.

This verifier reconstructs the exact evaluation source snapshot from the
recorded final source state plus the two explicitly documented post-evaluation
edits. It also reports (but cannot reconstruct) the two earlier dirty training
trees whose per-file content was not retained.
"""

from __future__ import annotations

import gzip
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE_SOURCE_REVISION = "575dce5978567417d2915d5dd36a47873293b607"
EVALUATION_IDENTITY = ROOT / ".agents/evidence/M5-evaluation-source-identity-20261029.json"
TRAINING_IDENTITY = ROOT / ".agents/evidence/M5-training-campaign-verification-20261029.json"
CHECKPOINTS = ROOT / ".agents/state/checkpoint-history/segments"
CHECKPOINT_BEFORE = "cp-08f98f9d-20261029T043013180672Z"
CHECKPOINT_AFTER = "cp-08f98f9d-20261029T143803674896Z"
POST_EVAL_HELPER = b"def paired_capped_reward_differences("
EVALUATION_FILE_LENGTH = 14853


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def git_blob(revision: str, path: str) -> bytes:
    return subprocess.check_output(["git", "show", f"{revision}:{path}"], cwd=ROOT)


def checkpoint_records() -> dict[str, dict[str, object]]:
    wanted = {CHECKPOINT_BEFORE, CHECKPOINT_AFTER}
    found: dict[str, dict[str, object]] = {}
    for segment in sorted(CHECKPOINTS.glob("*.jsonl.gz")):
        with gzip.open(segment, "rt", encoding="utf-8") as stream:
            for line in stream:
                row = json.loads(line)
                if row.get("id") in wanted:
                    found[row["id"]] = row
    missing = wanted - found.keys()
    if missing:
        raise ValueError(f"checkpoint-history records missing: {sorted(missing)}")
    return found


def git_blob_availability(hashes: set[str]) -> dict[str, str | None]:
    """Search every locally available Git blob by its SHA-256 file content."""
    metadata = subprocess.check_output(
        ["git", "cat-file", "--batch-all-objects", "--batch-check=%(objectname) %(objecttype) %(objectsize)"],
        cwd=ROOT,
        text=True,
    ).splitlines()
    remaining = set(hashes)
    found: dict[str, str] = {}
    for row in metadata:
        oid, object_type, size_text = row.split()
        if object_type != "blob" or int(size_text) > 200_000:
            continue
        blob = subprocess.check_output(["git", "cat-file", "blob", oid], cwd=ROOT)
        digest = sha(blob)
        if digest in remaining:
            found[digest] = oid
            remaining.remove(digest)
            if not remaining:
                break
    return {digest: found.get(digest) for digest in sorted(hashes)}


def main() -> int:
    identity = json.loads(EVALUATION_IDENTITY.read_text(encoding="utf-8"))
    training = json.loads(TRAINING_IDENTITY.read_text(encoding="utf-8"))
    recorded_files = {item["path"]: item for item in identity["files"]}
    source: dict[str, bytes] = {path: git_blob(BASE_SOURCE_REVISION, path) for path in recorded_files}
    direct_matches: list[str] = []
    reconstructed: list[dict[str, object]] = []
    for path, metadata in recorded_files.items():
        actual = source[path]
        if sha(actual) == metadata["sha256"]:
            direct_matches.append(path)
            continue
        if path == "videochess_rl/rl/evaluate.py":
            helper_at = actual.find(POST_EVAL_HELPER)
            if helper_at < 0 or helper_at < EVALUATION_FILE_LENGTH:
                raise ValueError("post-evaluation sensitivity helper boundary not found")
            old = actual[:EVALUATION_FILE_LENGTH]
            kind = "post-evaluation helper appended after official evaluation"
        elif path in {"videochess_rl/rl/training.py", "videochess_rl/rl/transition.py"}:
            old = actual + b"\n"
            kind = "one terminal LF removed during later whitespace cleanup"
        else:
            raise ValueError(f"unexplained evaluation source mismatch: {path}")
        if sha(old) != metadata["sha256"] or len(old) != metadata["size_bytes"]:
            raise ValueError(f"reconstruction does not match recorded file identity: {path}")
        source[path] = old
        reconstructed.append({"path": path, "recorded_sha256": metadata["sha256"],
                              "head_sha256": sha(actual), "recorded_size_bytes": metadata["size_bytes"],
                              "head_size_bytes": len(actual), "reconstruction": kind})

    digest = hashlib.sha256()
    for path in sorted(source):
        digest.update(path.encode("utf-8") + b"\0")
        digest.update(source[path])
    aggregate = digest.hexdigest()
    if len(direct_matches) != 39 or len(reconstructed) != 3 or aggregate != identity["evaluation_source_sha256"]:
        raise ValueError("evaluation source identity did not reconcile exactly")

    runs = training["runs"]
    run_groups: dict[str, list[dict[str, object]]] = {}
    for run in runs:
        run_groups.setdefault(run["code_sha256"], []).append(run)
    if set(run_groups) != {
        "093992c50e893a7fdd92f2f95faafe28d4f1e73c7351a4a8179a3056c4e63b00",
        "cdcc1fdc0ca0b324e49cfb8b0ff571496a554e9892dfb3620d6454a65ee16da0",
    }:
        raise ValueError("unexpected training source-hash grouping")
    if sorted(len(group) for group in run_groups.values()) != [2, 4]:
        raise ValueError("training source-hash group sizes differ from recorded campaign")

    records = checkpoint_records()
    before = records[CHECKPOINT_BEFORE]["workspace_git"]["repo_file_hashes"]
    after = records[CHECKPOINT_AFTER]["workspace_git"]["repo_file_hashes"]
    changed = []
    for path in sorted(set(before) | set(after)):
        if path.startswith("videochess_rl/") and path.endswith(".py") and before.get(path) != after.get(path):
            changed.append({"path": path, "before_sha256": before.get(path), "after_sha256": after.get(path)})

    historical_file_hashes = {
        row[field]
        for row in changed
        for field in ("before_sha256", "after_sha256")
        if isinstance(row.get(field), str)
    }
    blob_availability = git_blob_availability(historical_file_hashes)

    report = {
        "schema": "videochess-m5-source-reconciliation/1.0",
        "evaluation_identity": {
            "source_revision": identity["git_revision"],
            "recorded_source_sha256": identity["evaluation_source_sha256"],
            "verified_direct_file_matches": len(direct_matches),
            "verified_reconstructed_file_matches": reconstructed,
            "reconstructed_aggregate_sha256": aggregate,
            "result": "exact match",
        },
        "training_identity": {
            "run_hash_group_sizes": {key: len(value) for key, value in sorted(run_groups.items())},
            "distinct_source_hashes": sorted(run_groups),
            "checkpoint_interval": [CHECKPOINT_BEFORE, CHECKPOINT_AFTER],
            "changed_python_paths_in_interval": changed,
            "sha256_file_blob_availability_in_local_git_object_database": blob_availability,
            "all_changed_snapshot_contents_recovered": all(value is not None for value in blob_availability.values()),
            "interpretation": "File hash changes are observed. Only versions with a found Git blob can be read and diffed; absent blobs and source backups are not reconstructed.",
        },
    }
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
