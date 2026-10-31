"""Read-only audit of the post-merge M6 closeout evidence provenance."""

from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path
import re
import subprocess
from typing import Any


REQUIRED_FILE_PATHS = (
    ".agents/evidence/M6-PR-handover-20261031.md",
    ".agents/evidence/M6-001-PM-acceptance-20261031.md",
    ".agents/evidence/M6-post-merge-verification-20261031.md",
    ".agents/evidence/M6-post-merge-verification-20261031.json",
)
REPORT_PATH = ".agents/evidence/M6-post-merge-verification-20261031.json"
HEX40 = re.compile(r"^[0-9a-f]{40}$")


def _git(root: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        ["git", "-C", str(root), *args],
        check=check,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def _timestamp(value: Any) -> bool:
    if not isinstance(value, str) or not value.endswith("Z"):
        return False
    try:
        datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError:
        return False
    return True


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def audit(repo: Path) -> dict[str, Any]:
    root = repo.resolve()
    errors: list[str] = []
    backlog = json.loads((root / ".agents/tasks/BACKLOG.yaml").read_text(encoding="utf-8"))
    task = next(item for item in backlog["tasks"] if item["id"] == "M6-001")
    evidence = task["evidence"]

    scoped = [item for item in evidence if item.get("audit_scope") == "PM6C-F01"]
    scoped_files = {item.get("path"): item for item in scoped if item.get("kind") == "file"}
    for relpath in REQUIRED_FILE_PATHS:
        if relpath not in scoped_files:
            errors.append(f"required PM6C-F01 file evidence is missing: {relpath}")
    file_results: list[dict[str, Any]] = []
    for item in scoped:
        if item.get("kind") != "file":
            continue
        relpath = item.get("path")
        if not isinstance(relpath, str):
            errors.append("PM6C-F01 file evidence has no path")
            continue
        provenance = item.get("provenance") or {}
        revision = provenance.get("git_revision")
        if provenance.get("status") != "verified":
            errors.append(f"{relpath}: evidence is not marked verified")
        if not _timestamp(provenance.get("recorded_at_utc")):
            errors.append(f"{relpath}: missing valid read-only verification timestamp")
        if not isinstance(revision, str) or not HEX40.fullmatch(revision):
            errors.append(f"{relpath}: git_revision is not a full commit SHA")
            continue
        resolved = _git(root, "cat-file", "-e", f"{revision}^{{commit}}", check=False).returncode == 0
        blob = _git(root, "show", f"{revision}:{relpath}", check=False)
        if not resolved:
            errors.append(f"{relpath}: git_revision {revision} does not resolve")
        if blob.returncode:
            errors.append(f"{relpath}: file is absent from commit {revision}")
            continue
        digest = _sha256(blob.stdout)
        if item.get("file_sha256") != digest:
            errors.append(f"{relpath}: recorded committed-file SHA-256 does not match ({digest})")
        current = (root / relpath).read_bytes()
        if current != blob.stdout:
            errors.append(f"{relpath}: working file differs from the verified committed bytes")
        file_results.append({
            "path": relpath,
            "status": "PASS" if resolved and not blob.returncode and item.get("file_sha256") == digest and current == blob.stdout else "FAIL",
            "git_revision": revision,
            "sha256": digest,
            "recorded_at_utc": provenance.get("recorded_at_utc"),
            "prior_revision_note": item.get("detail"),
        })

    log_results: list[dict[str, Any]] = []
    for item in scoped:
        if item.get("kind") not in {"command", "test"}:
            continue
        provenance = item["provenance"]
        relpath = provenance.get("log_path")
        if provenance.get("status") == "historical_unverified":
            required_nulls = ("executed_at_utc", "recorded_at_utc", "exit_code", "git_revision", "log_path")
            if any(provenance.get(key) is not None for key in required_nulls):
                errors.append(f"{item.get('command')}: historical evidence retains unavailable execution metadata")
            historical_path = item.get("historical_log_path")
            historical_digest = item.get("historical_log_sha256")
            historical_revision = item.get("historical_git_revision")
            if not isinstance(historical_path, str) or not (root / historical_path).is_file():
                errors.append(f"historical diagnostic log is missing: {historical_path}")
            elif _sha256((root / historical_path).read_bytes()) != historical_digest:
                errors.append(f"historical diagnostic log hash mismatch: {historical_path}")
            if not isinstance(historical_revision, str) or _git(root, "cat-file", "-e", f"{historical_revision}^{{commit}}", check=False).returncode == 0:
                errors.append(f"historical diagnostic source should remain explicitly unresolved: {historical_revision}")
            continue
        if provenance.get("status") != "verified":
            errors.append(f"{item.get('command')}: unsupported PM6C-F01 evidence status")
            continue
        revision = provenance.get("git_revision")
        if not isinstance(revision, str) or not HEX40.fullmatch(revision) or _git(root, "cat-file", "-e", f"{revision}^{{commit}}", check=False).returncode:
            errors.append(f"{relpath}: recorded git_revision does not resolve")
        if not _timestamp(provenance.get("executed_at_utc")) or not _timestamp(provenance.get("recorded_at_utc")):
            errors.append(f"{relpath}: command timestamps are invalid")
        path = root / relpath
        if not path.is_file():
            errors.append(f"{relpath}: retained command log is missing")
            continue
        raw = path.read_bytes()
        text = raw.decode("utf-8", errors="replace")
        digest = _sha256(raw)
        if provenance.get("log_sha256") != digest:
            errors.append(f"{relpath}: recorded log SHA-256 does not match ({digest})")
        for label, value in (("command", item.get("command")), ("result", item.get("result")), ("exit", f"Exit code: {provenance.get('exit_code')}")):
            if not isinstance(value, str) or value not in text:
                errors.append(f"{relpath}: retained log does not match recorded {label}")
        started = re.search(r"(?m)^started_at_utc: (\S+)", text)
        executed = provenance.get("executed_at_utc")
        if not started or not isinstance(executed, str) or started.group(1)[:19] != executed[:19]:
            errors.append(f"{relpath}: log start time differs from the recorded execution timestamp")
        log_results.append({
            "path": relpath,
            "provenance_status": "verified" if not any(relpath in error for error in errors) else "invalid",
            "execution_status": "PASS" if provenance.get("exit_code") == 0 else "FAIL",
            "git_revision": revision,
            "log_sha256": digest,
            "executed_at_utc": executed,
            "exit_code": provenance.get("exit_code"),
        })
    verified_log_paths = {item["path"] for item in log_results}
    required_log_paths = {
        ".agents/evidence/logs/M6-postmerge-identity-verification-20261031.log",
        ".agents/evidence/logs/M6-postmerge-lock-check-20261031.log",
        ".agents/evidence/logs/M6-postmerge-final-focused-20261031.log",
        ".agents/evidence/logs/M6-postmerge-final-focused-correct-env-20261031.log",
        ".agents/evidence/logs/M6-postmerge-final-full-suite-20261031.log",
        ".agents/evidence/logs/M6-postmerge-clean-checkout-preflight-20261031.log",
        ".agents/evidence/logs/M6-postmerge-clean-checkout-focused-20261031.log",
        ".agents/evidence/logs/M6-postmerge-clean-checkout-full-suite-20261031.log",
    }
    for relpath in sorted(required_log_paths - verified_log_paths):
        errors.append(f"required verified PM6C-F01 command log is not in scope: {relpath}")

    historical_results = [
        {"path": item.get("historical_log_path"), "status": "historical_unverified", "historical_git_revision": item.get("historical_git_revision")}
        for item in scoped
        if item.get("kind") in {"command", "test"} and (item.get("provenance") or {}).get("status") == "historical_unverified"
    ]

    report = json.loads((root / REPORT_PATH).read_text(encoding="utf-8"))
    report_checks: list[dict[str, Any]] = []
    for check in report.get("postmerge_checks", []):
        log_rel = check.get("command_log")
        if not log_rel:
            continue
        path = root / log_rel
        if not path.is_file():
            errors.append(f"machine report references missing log {log_rel}")
            continue
        raw = path.read_bytes()
        if check.get("log_sha256") != _sha256(raw):
            errors.append(f"machine report log hash mismatch for {log_rel}")
        for key in ("revision", "git_head_at_execution", "tested_commit"):
            revision = check.get(key)
            if revision and (not isinstance(revision, str) or not HEX40.fullmatch(revision) or _git(root, "cat-file", "-e", f"{revision}^{{commit}}", check=False).returncode):
                errors.append(f"machine report {check.get('name')} has unresolved {key}: {revision}")
        report_checks.append({"name": check.get("name"), "log_path": log_rel, "log_sha256": _sha256(raw), "status": check.get("status")})

    current_head = _git(root, "rev-parse", "HEAD").stdout.decode().strip()
    current_tree = _git(root, "rev-parse", "HEAD^{tree}").stdout.decode().strip()
    return {
        "schema": "videochess-m6-closeout-provenance-audit/1.0",
        "audit_source_head": current_head,
        "audit_source_tree": current_tree,
        "file_evidence": file_results,
        "command_log_evidence": log_results,
        "historical_diagnostics": historical_results,
        "machine_report_checks": report_checks,
        "errors": errors,
        "ok": not errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--json", action="store_true", help="emit the complete audit object as JSON")
    args = parser.parse_args()
    result = audit(args.repo)
    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(f"M6 closeout provenance audit: {'PASS' if result['ok'] else 'FAIL'}")
        print(f"Verified file entries: {len(result['file_evidence'])}; command logs: {len(result['command_log_evidence'])}; machine report logs: {len(result['machine_report_checks'])}")
        for error in result["errors"]:
            print(f"ERROR: {error}")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
