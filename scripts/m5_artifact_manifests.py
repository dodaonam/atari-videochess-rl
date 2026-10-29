#!/usr/bin/env python3
"""Create and verify immutable M5 run and private artifact inventories."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ARTIFACT_ROOT = ROOT / "artifacts/m5"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def file_inventory(root: Path, *, excluded_names: frozenset[str] = frozenset()) -> list[dict[str, Any]]:
    rows = []
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise ValueError(f"symlink in artifact inventory: {path.relative_to(root)}")
        if not path.is_file() or path.name in excluded_names or path.name.endswith(".tmp"):
            continue
        rows.append({"path": path.relative_to(root).as_posix(), "size_bytes": path.stat().st_size,
                     "sha256": sha256_file(path)})
    return rows


def _atomic_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(value, stream, sort_keys=True, indent=2, allow_nan=False)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp_name, path)
        dir_fd = os.open(path.parent, os.O_DIRECTORY)
        try:
            os.fsync(dir_fd)
        finally:
            os.close(dir_fd)
    finally:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass


def verify_manifest(root: Path, manifest_path: Path) -> dict[str, Any]:
    if manifest_path.is_symlink() or not manifest_path.is_file():
        raise ValueError(f"missing or unsafe artifact manifest: {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    base = manifest_path.parent
    expected = manifest.get("files")
    if not isinstance(expected, list):
        raise ValueError(f"malformed file inventory: {manifest_path}")
    excluded = frozenset({manifest_path.name})
    actual = file_inventory(base, excluded_names=excluded)
    if actual != expected:
        raise ValueError(f"artifact inventory mismatch: {manifest_path}")
    return manifest


def _publish_immutable(path: Path, document: dict[str, Any]) -> dict[str, Any]:
    if path.exists():
        old = json.loads(path.read_text(encoding="utf-8"))
        if old != document:
            # A previously finalized inventory is immutable. A matching verified
            # manifest is returned by the caller before attempting publication.
            raise FileExistsError(f"refusing to replace immutable manifest: {path}")
        return old
    _atomic_json(path, document)
    return document


def create_manifests(artifact_root: Path, *, allow_incomplete: bool = False) -> dict[str, Any]:
    training_path = artifact_root / "training-campaign.json"
    evaluation_path = artifact_root / "evaluation/evaluation-report.json"
    training = json.loads(training_path.read_text(encoding="utf-8")) if training_path.is_file() else None
    evaluation = json.loads(evaluation_path.read_text(encoding="utf-8")) if evaluation_path.is_file() else None
    config = json.loads((ROOT / "configs/rl/m5-double-dqn-v1.json").read_text(encoding="utf-8"))
    seeds = config["training"]["paired_seeds"]
    expected_policies = {"m4_behavior_only", "baseline:random_legal", "baseline:simple_heuristic"}
    expected_policies.update(f"{arm}:{seed}:{stage}" for arm in ("warm", "scratch")
                             for seed in seeds for stage in ("pre_rl", "post_rl"))
    runs = training.get("runs", []) if training else []
    policies = evaluation.get("per_policy", []) if evaluation else []
    complete = bool(training and training.get("status") == "complete" and training.get("planned_runs") == 6
                    and training.get("completed_runs") == 6 and training.get("total_valid_decisions") == 300000
                    and len(runs) == 6 and all(run.get("completion") == "complete"
                        and run.get("valid_decisions") == 50000 for run in runs)
                    and evaluation and evaluation.get("schedule_complete") is True
                    and evaluation.get("executed_games") == 1500 and evaluation.get("planned_games") == 1500
                    and evaluation.get("policies_with_recorded_schedule") == 15 and len(policies) == 15
                    and {policy.get("policy_id") for policy in policies} == expected_policies
                    and all(policy.get("schedule_complete") is True and policy.get("games") == 100
                            and policy.get("planned_games") == 100 for policy in policies))
    if not complete and not allow_incomplete:
        raise RuntimeError("final artifact manifests require six completed runs and the complete 1,500-game evaluation")

    runs_root = artifact_root / "runs"
    if runs_root.exists():
        for run_dir in sorted(path for path in runs_root.iterdir() if path.is_dir()):
            summary_path = run_dir / "run-summary.json"
            attempt_path = run_dir / "attempt-record.json"
            if not summary_path.is_file() and not attempt_path.is_file() and not (run_dir / "initialization-manifest.json").is_file():
                continue
            run_manifest_path = run_dir / "run-manifest.json"
            if run_manifest_path.exists():
                verify_manifest(artifact_root, run_manifest_path)
                continue
            summary = json.loads(summary_path.read_text(encoding="utf-8")) if summary_path.is_file() else None
            attempt = json.loads(attempt_path.read_text(encoding="utf-8")) if attempt_path.is_file() else None
            manifest = {"schema": "videochess-m5-run-manifest/1.0", "run_id": run_dir.name,
                        "run_status": (summary or attempt or {}).get("completion", (attempt or {}).get("status", "initialization_only")),
                        "summary_sha256": sha256_file(summary_path) if summary_path.is_file() else None,
                        "configuration_sha256": (summary or {}).get("config_sha256"),
                        "source_identity": (summary or {}).get("code"),
                        "initialization_manifest_sha256": sha256_file(run_dir / "initialization-manifest.json")
                        if (run_dir / "initialization-manifest.json").is_file() else None,
                        "created_at_utc": datetime.now(timezone.utc).isoformat(),
                        "files": file_inventory(run_dir, excluded_names=frozenset({"run-manifest.json"}))}
            _publish_immutable(run_manifest_path, manifest)

    manifest_path = artifact_root / "artifact-manifest.json"
    if manifest_path.exists():
        return verify_manifest(artifact_root, manifest_path)
    config_path = ROOT / "configs/rl/m5-double-dqn-v1.json"
    config_sha = sha256_file(config_path)
    document = {"schema": "videochess-m5-artifact-manifest/1.0", "status": "complete" if complete else "partial",
                "created_at_utc": datetime.now(timezone.utc).isoformat(), "configuration_sha256": config_sha,
                "training_campaign_sha256": sha256_file(training_path) if training_path.is_file() else None,
                "evaluation_report_sha256": sha256_file(evaluation_path) if evaluation_path.is_file() else None,
                "total_bytes": sum(path.stat().st_size for path in artifact_root.rglob("*") if path.is_file()),
                "files": file_inventory(artifact_root, excluded_names=frozenset({"artifact-manifest.json"}))}
    return _publish_immutable(manifest_path, document)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=DEFAULT_ARTIFACT_ROOT)
    parser.add_argument("--allow-incomplete", action="store_true",
                        help="inventory preserved partial artifacts without calling them complete")
    parser.add_argument("--verify", action="store_true", help="verify existing root and per-run manifests")
    args = parser.parse_args()
    root = args.root.resolve()
    if args.verify:
        root_manifest = verify_manifest(root, root / "artifact-manifest.json")
        run_manifests = sorted(root.glob("runs/*/run-manifest.json"))
        for manifest_path in run_manifests:
            verify_manifest(root, manifest_path)
        print(json.dumps({"status": "verified", "artifact_manifest": str((root / "artifact-manifest.json").relative_to(ROOT)),
                          "run_manifests": len(run_manifests), "total_bytes": root_manifest.get("total_bytes")}, indent=2))
        return 0
    result = create_manifests(root, allow_incomplete=args.allow_incomplete)
    print(json.dumps({"status": result["status"], "artifact_manifest": str((root / "artifact-manifest.json").relative_to(ROOT)),
                      "run_manifests": len(list(root.glob("runs/*/run-manifest.json"))),
                      "total_bytes": result["total_bytes"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
