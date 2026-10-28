#!/usr/bin/env python3
"""Validate persistent project context and print a conversation-free recovery summary."""

from __future__ import annotations

import argparse
import html
import hashlib
import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import unquote, urlsplit

from checkpoint_history import ARCHIVE_REL as CHECKPOINT_HISTORY_ARCHIVE_REL
from checkpoint_history import POINTER_KEY as CHECKPOINT_HISTORY_POINTER_KEY
from checkpoint_history import inspect_history_storage

SCHEMA_VERSION = 2
STATE_REL = ".agents/state/PROJECT_STATE.yaml"
ROADMAP_REL = "docs/01-foundation/ROADMAP.md"
ROADMAP_HTML_REL = "atari-videochess-rl-roadmap.html"
BACKLOG_REL = ".agents/tasks/BACKLOG.yaml"
HANDOFF_REL = ".agents/state/SESSION_HANDOFF.md"
BLOCKERS_REL = ".agents/state/BLOCKERS.md"
REQUIREMENTS_REL = "docs/01-foundation/REQUIREMENTS.md"
CHECKPOINT_MARKER = re.compile(r"(?m)^<!-- checkpoint-id: ([^\s]+) -->$")
TASK_ID = re.compile(r"^(?:G[0-5]|M[0-7])-\d{3}$")
MILESTONE_ID = re.compile(r"^M[0-7]$")
GATE_ID = re.compile(r"^G[0-5]$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")
GIT_OBJECT_ID = re.compile(r"^(?:[0-9a-f]{40}|[0-9a-f]{64})$")
BLOCKER_HEADING = re.compile(r"(?m)^## (BLK-\d{3})\b")
MARKDOWN_LINK = re.compile(r"(!?)\[([^\]]*)\]\(([^)\s]+)(?:\s+[^)]*)?\)")

REQUIRED_FILES = (
    "AGENTS.md",
    "README.md",
    ROADMAP_REL,
    ROADMAP_HTML_REL,
    REQUIREMENTS_REL,
    "docs/01-foundation/PROJECT_OVERVIEW.md",
    "docs/02-management/EXECUTION_PLAN.md",
    "docs/02-management/RISK_REGISTER.md",
    "docs/02-management/decisions/ADR-0001-governance-crosswalk-and-file-priorities.md",
    "docs/05-operations/SETUP.md",
    "docs/06-quality/ACCEPTANCE_CRITERIA.md",
    "docs/06-quality/TEST_STRATEGY.md",
    ".agents/PLANS.md",
    STATE_REL,
    HANDOFF_REL,
    BLOCKERS_REL,
    ".agents/state/VERIFIED_FINDINGS.md",
    BACKLOG_REL,
    ".agents/plans/G1-consistency-hardening.md",
    ".agents/plans/M00-bootstrap.md",
    ".agents/evidence/G1-hardening-verification.md",
    "scripts/agent_preflight.py",
    "scripts/agent_checkpoint.py",
    "tests/test_agent_context.py",
)
PARTIAL_STATE_PATTERNS = (".PROJECT_STATE.yaml.tmp-*", ".SESSION_HANDOFF.md.tmp-*")
ALLOWED_TASK_STATUSES = {"pending", "in_progress", "blocked", "done", "cancelled"}
ALLOWED_GATE_STATUSES = {"in_progress", "ready_for_user_review", "approved"}
ALLOWED_MILESTONE_STATUSES = {
    "not_started",
    "pending_user_approval",
    "ready_to_start",
    "in_progress",
    "blocked",
    "complete",
}
ARTIFACT_DIR_NAMES = {"artifacts", "datasets", "checkpoints"}
HASH_EXCLUDED_DIRS = {".git", ".venv", "venv", "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache", ".tox", ".nox", "node_modules", "artifacts", "datasets", "checkpoints", "build", "dist"}
SENSITIVE_DIRS = {"secrets", "credentials", ".ssh", ".aws"}
SENSITIVE_NAMES = {"credentials.json", "credentials.yaml", "credentials.yml", "service-account.json", "google-services.json", "id_rsa", "id_ed25519"}
SENSITIVE_SUFFIXES = {".pem", ".key", ".p12", ".pfx", ".keystore"}
MAX_HASH_BYTES = 2 * 1024 * 1024
PORTABLE_EXCLUDED_PATHS = {STATE_REL, HANDOFF_REL}
WORKSPACE_CONFIG_KEY = "codex.contextWorkspaceId"
WORKSPACE_ID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$")


def _sha_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _sha_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _repo_file_hash_inventory(root: Path) -> tuple[dict[str, str], dict[str, object]]:
    hashes: dict[str, str] = {}
    oversized: list[str] = []
    unreadable: list[str] = []
    artifact_dirs: list[str] = []
    excluded_dirs: list[str] = []
    excluded_symlink_files = 0
    for directory, dirs, files in os.walk(root, followlinks=False):
        base = Path(directory)
        for name in dirs:
            path = base / name
            if path.is_symlink():
                continue
            rel = path.relative_to(root).as_posix()
            if name in HASH_EXCLUDED_DIRS or rel == CHECKPOINT_HISTORY_ARCHIVE_REL:
                excluded_dirs.append(rel)
            if name in ARTIFACT_DIR_NAMES:
                artifact_dirs.append(rel)
        dirs[:] = sorted(
            name for name in dirs
            if name not in HASH_EXCLUDED_DIRS
            and (base / name).relative_to(root).as_posix() != CHECKPOINT_HISTORY_ARCHIVE_REL
            and not (base / name).is_symlink()
        )
        for name in sorted(files):
            path = base / name
            rel = path.relative_to(root).as_posix()
            sensitive = _sensitive_relative_path(rel)
            if sensitive or rel == STATE_REL or ".tmp-" in name:
                continue
            if path.is_symlink():
                excluded_symlink_files += 1
                continue
            try:
                if path.stat().st_size > MAX_HASH_BYTES:
                    oversized.append(rel)
                else:
                    hashes[rel] = _sha_file(path)
            except OSError:
                unreadable.append(rel)
    return hashes, {
        "unhashed_large_files": sorted(oversized),
        "unreadable_files": sorted(unreadable),
        "artifact_dirs_requiring_manifest": sorted(artifact_dirs),
        "excluded_directories": sorted(excluded_dirs),
        "excluded_symlink_files": excluded_symlink_files,
    }


def _status_digest(entries: list[str]) -> str:
    payload = "\n".join(entries) + ("\n" if entries else "")
    return _sha_text(payload)


def _workspace_comparable_status(entries: list[str]) -> list[str]:
    # Checkpointing rewrites these control files; their content has separate
    # portable checksums, so their staged/unstaged status flip is expected.
    return [entry for entry in entries if entry[3:] not in PORTABLE_EXCLUDED_PATHS]


def _relative_path(value: object) -> bool:
    if not isinstance(value, str) or not value or "\\" in value:
        return False
    path = Path(value)
    return not path.is_absolute() and ".." not in path.parts


def _sensitive_relative_path(value: str) -> bool:
    path = Path(value)
    name = path.name.lower()
    return (
        name == "chat_history.md"
        or name.startswith(".env")
        or name in SENSITIVE_NAMES
        or path.suffix.lower() in SENSITIVE_SUFFIXES
        or any(part.lower() in SENSITIVE_DIRS for part in path.parts)
    )


def _git(root: Path, *args: str) -> str:
    env = os.environ.copy()
    env["GIT_OPTIONAL_LOCKS"] = "0"
    result = subprocess.run(
        ["git", "-C", str(root), *args],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or f"git {args[0]} failed")
    return result.stdout.strip()


def _git_bytes(root: Path, *args: str) -> bytes:
    env = os.environ.copy()
    env["GIT_OPTIONAL_LOCKS"] = "0"
    result = subprocess.run(
        ["git", "-C", str(root), *args],
        capture_output=True,
        check=False,
        env=env,
    )
    if result.returncode:
        detail = result.stderr.decode("utf-8", "replace").strip()
        raise RuntimeError(detail or f"git {args[0]} failed")
    return result.stdout


def _git_workspace_id(root: Path) -> str | None:
    try:
        value = _git(root, "config", "--local", "--get", WORKSPACE_CONFIG_KEY)
    except RuntimeError:
        return None
    return value or None


def _portable_path(path: str) -> bool:
    # Never fingerprint credential or conversation content. Git status still
    # reports tracked edits to these paths; ordinary tracked files use the
    # portable manifest, excluding only the two self-referential controls.
    return (
        path not in PORTABLE_EXCLUDED_PATHS
        and path != CHECKPOINT_HISTORY_ARCHIVE_REL
        and not path.startswith(CHECKPOINT_HISTORY_ARCHIVE_REL + "/")
        and not _sensitive_relative_path(path)
    )


def _git_index_manifest(root: Path) -> dict[str, dict[str, str]]:
    manifest: dict[str, dict[str, str]] = {}
    raw = _git_bytes(root, "ls-files", "--stage", "-z")
    for record in raw.split(b"\0"):
        if not record:
            continue
        metadata, encoded_path = record.split(b"\t", 1)
        mode, object_id, stage = metadata.decode("ascii").split(" ")
        if stage != "0":
            raise RuntimeError(f"Git index has an unmerged entry for {os.fsdecode(encoded_path)}")
        path = os.fsdecode(encoded_path)
        if not _portable_path(path):
            continue
        manifest[path] = {"mode": mode, "object_id": object_id}
    return dict(sorted(manifest.items()))


def _git_head_manifest(root: Path, include_control_files: bool = False) -> dict[str, dict[str, str]]:
    manifest: dict[str, dict[str, str]] = {}
    raw = _git_bytes(root, "ls-tree", "-r", "-z", "--full-tree", "HEAD")
    for record in raw.split(b"\0"):
        if not record:
            continue
        metadata, encoded_path = record.split(b"\t", 1)
        mode, _object_type, object_id = metadata.decode("ascii").split(" ")
        path = os.fsdecode(encoded_path)
        if include_control_files:
            if _sensitive_relative_path(path) or ".tmp-" in Path(path).name or path == CHECKPOINT_HISTORY_ARCHIVE_REL or path.startswith(CHECKPOINT_HISTORY_ARCHIVE_REL + "/"):
                continue
        elif not _portable_path(path):
            continue
        manifest[path] = {"mode": mode, "object_id": object_id}
    return dict(sorted(manifest.items()))


def _canonical_sha256(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(payload.encode("ascii")).hexdigest()


def _portable_state_sha256(state: dict[str, object]) -> str:
    stable_fields = {key: value for key, value in state.items() if key != "last_checkpoint"}
    return _canonical_sha256(stable_fields)


def _legacy_portable_match(
    root: Path,
    git_expected: dict[str, object],
    current_hashes: dict[str, str],
) -> bool:
    expected_hashes = git_expected.get("repo_file_hashes", {})
    if not isinstance(expected_hashes, dict):
        return False
    try:
        head_paths = set(_git_head_manifest(root, include_control_files=True)) - {STATE_REL}
    except RuntimeError:
        return False
    entries = git_expected.get("status_entries", [])
    previously_untracked = {
        entry[3:]
        for entry in entries
        if isinstance(entry, str) and entry.startswith("?? ")
    } if isinstance(entries, list) else set()
    previously_untracked.discard(HANDOFF_REL)
    if not head_paths or head_paths & previously_untracked:
        return False
    if any(path not in expected_hashes or path not in current_hashes for path in head_paths):
        return False
    return all(expected_hashes[path] == current_hashes[path] for path in head_paths)


def _validate_portable_snapshot(portable: object, errors: list[dict[str, str]]) -> None:
    code = "STATE_SCHEMA"
    if not isinstance(portable, dict):
        errors.append({"code": code, "path": STATE_REL, "message": "last_checkpoint.portable_git must be an object."})
        return
    if not _require_keys(portable, ("format_version", "tracked_manifest", "manifest_sha256", "state_sha256", "handoff_sha256"), code, STATE_REL, errors):
        return
    if portable["format_version"] != 1:
        errors.append({"code": code, "path": STATE_REL, "message": "Unknown portable Git snapshot format_version."})
    manifest = portable["tracked_manifest"]
    valid_manifest = isinstance(manifest, dict)
    if valid_manifest:
        for path, record in manifest.items():
            if not _relative_path(path) or not _portable_path(path) or not isinstance(record, dict):
                valid_manifest = False
                break
            if set(record) != {"mode", "object_id"}:
                valid_manifest = False
                break
            if record["mode"] not in {"100644", "100755", "120000", "160000"}:
                valid_manifest = False
                break
            if not isinstance(record["object_id"], str) or not GIT_OBJECT_ID.fullmatch(record["object_id"]):
                valid_manifest = False
                break
    if not valid_manifest:
        errors.append({"code": code, "path": STATE_REL, "message": "portable tracked_manifest must map safe paths to Git modes and object IDs."})
    elif portable["manifest_sha256"] != _canonical_sha256(manifest):
        errors.append({"code": code, "path": STATE_REL, "message": "portable tracked_manifest checksum does not match its recorded files."})
    for field in ("manifest_sha256", "state_sha256", "handoff_sha256"):
        if not isinstance(portable[field], str) or not SHA256.fullmatch(portable[field]):
            errors.append({"code": code, "path": STATE_REL, "message": f"portable {field} must be a SHA-256 digest."})


def _live_git_snapshot(root: Path) -> dict[str, object]:
    branch = _git(root, "branch", "--show-current") or "DETACHED"
    head = _git(root, "rev-parse", "HEAD")
    raw = _git_bytes(
        root, "status", "--porcelain=v1", "--untracked-files=all", "--", ".",
        f":(exclude){CHECKPOINT_HISTORY_ARCHIVE_REL}/**",
    ).decode("utf-8", "surrogateescape")
    entries = sorted(line for line in raw.splitlines() if line)
    return {
        "branch": branch,
        "head": head,
        "status_entries": entries,
        "status_sha256": _status_digest(entries),
    }


def _load_json_yaml(root: Path, rel: str, code: str, errors: list[dict[str, str]]) -> dict[str, object] | None:
    path = root / rel
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        errors.append({"code": code, "path": rel, "message": f"Expected JSON-compatible YAML: {exc}"})
        return None
    if not isinstance(value, dict):
        errors.append({"code": code, "path": rel, "message": "Top-level value must be an object."})
        return None
    return value


def _require_keys(value: dict[str, object], keys: tuple[str, ...], code: str, rel: str, errors: list[dict[str, str]]) -> bool:
    missing = [key for key in keys if key not in value]
    if missing:
        errors.append({"code": code, "path": rel, "message": "Missing required keys: " + ", ".join(missing)})
        return False
    return True


def _validate_state(state: dict[str, object], errors: list[dict[str, str]]) -> None:
    code = "STATE_SCHEMA"
    if not _require_keys(
        state,
        ("format", "schema_version", "project_id", "governance", "engineering", "task_refs", "active_blocker_ids", "last_checkpoint", "g1_baseline"),
        code,
        STATE_REL,
        errors,
    ):
        return
    if state["format"] != "JSON-compatible YAML 1.2" or state["schema_version"] != SCHEMA_VERSION:
        errors.append({"code": code, "path": STATE_REL, "message": "Unsupported format or schema_version."})
    if state["project_id"] != "atari-videochess-rl":
        errors.append({"code": code, "path": STATE_REL, "message": "project_id must be atari-videochess-rl."})
    history = state.get("checkpoint_history", [])
    if CHECKPOINT_HISTORY_POINTER_KEY not in state:
        if not isinstance(history, list) or any(
            not isinstance(item, dict)
            or not isinstance(item.get("id"), str)
            or not isinstance(item.get("created_at_utc"), str)
            or not isinstance(item.get("workspace_git", item.get("git")), dict)
            or (item.get("workspace_id") is not None and (not isinstance(item.get("workspace_id"), str) or not WORKSPACE_ID.fullmatch(item["workspace_id"])))
            for item in history
        ):
            errors.append({"code": code, "path": STATE_REL, "message": "Legacy checkpoint_history must preserve prior checkpoint IDs, timestamps, and workspace snapshots."})
    else:
        archive_pointer = state.get(CHECKPOINT_HISTORY_POINTER_KEY)
        if history != []:
            errors.append({"code": code, "path": STATE_REL, "message": "Archived checkpoint history requires an empty inline checkpoint_history list."})
        if not isinstance(archive_pointer, dict) or set(archive_pointer) != {
            "format_version", "manifest_path", "manifest_sha256", "record_count", "logical_sha256",
            "source_state_sha256", "source_backup_path", "source_backup_sha256",
        }:
            errors.append({"code": code, "path": STATE_REL, "message": "checkpoint_history_archive must match the versioned pointer schema."})
        elif (
            type(archive_pointer.get("format_version")) is not int
            or archive_pointer.get("format_version") != 1
            or archive_pointer.get("manifest_path") != f"{CHECKPOINT_HISTORY_ARCHIVE_REL}/manifest.json"
            or not isinstance(archive_pointer.get("record_count"), int)
            or isinstance(archive_pointer.get("record_count"), bool)
            or archive_pointer.get("record_count", -1) < 0
            or any(not isinstance(archive_pointer.get(key), str) or not SHA256.fullmatch(archive_pointer[key]) for key in ("manifest_sha256", "logical_sha256", "source_state_sha256", "source_backup_sha256"))
            or not isinstance(archive_pointer.get("source_backup_path"), str)
        ):
            errors.append({"code": code, "path": STATE_REL, "message": "checkpoint_history_archive contains an unsupported version or invalid path/count/hash."})

    governance = state["governance"]
    if not isinstance(governance, dict):
        errors.append({"code": code, "path": STATE_REL, "message": "governance must be an object."})
        return
    if not _require_keys(governance, ("current_gate", "gate_status", "approved_gates", "next_governance_gate", "user_authorized_g1", "next_user_action"), code, STATE_REL, errors):
        return
    if not isinstance(governance["current_gate"], str) or not GATE_ID.fullmatch(governance["current_gate"]):
        errors.append({"code": code, "path": STATE_REL, "message": "governance.current_gate must be G0–G5."})
    if not isinstance(governance["gate_status"], str) or governance["gate_status"] not in ALLOWED_GATE_STATUSES:
        errors.append({"code": code, "path": STATE_REL, "message": "Unknown governance.gate_status."})
    if not isinstance(governance["approved_gates"], list) or any(not isinstance(g, str) or not GATE_ID.fullmatch(g) for g in governance["approved_gates"]):
        errors.append({"code": code, "path": STATE_REL, "message": "governance.approved_gates must be a list of G0–G5 IDs."})
    if not isinstance(governance["user_authorized_g1"], bool) or not isinstance(governance["next_user_action"], str):
        errors.append({"code": code, "path": STATE_REL, "message": "Invalid G1 authorization/action fields."})

    engineering = state["engineering"]
    if not isinstance(engineering, dict):
        errors.append({"code": code, "path": STATE_REL, "message": "engineering must be an object."})
        return
    if not _require_keys(engineering, ("active_milestone", "next_milestone", "next_milestone_status", "start_authorized", "hold_reason"), code, STATE_REL, errors):
        return
    active = engineering["active_milestone"]
    if active is not None and (not isinstance(active, str) or not MILESTONE_ID.fullmatch(active)):
        errors.append({"code": code, "path": STATE_REL, "message": "engineering.active_milestone must be null or M0–M7."})
    if not isinstance(engineering["next_milestone"], str) or not MILESTONE_ID.fullmatch(engineering["next_milestone"]):
        errors.append({"code": code, "path": STATE_REL, "message": "engineering.next_milestone must be M0–M7."})
    if not isinstance(engineering["next_milestone_status"], str) or engineering["next_milestone_status"] not in ALLOWED_MILESTONE_STATUSES:
        errors.append({"code": code, "path": STATE_REL, "message": "Unknown engineering.next_milestone_status."})
    if not isinstance(engineering["start_authorized"], bool) or not isinstance(engineering["hold_reason"], str):
        errors.append({"code": code, "path": STATE_REL, "message": "Invalid engineering authorization/hold fields."})
    authorization_record = engineering.get("start_authorization_record")
    if engineering.get("start_authorized") is True:
        required_record_keys = (
            "authorization_id", "task_id", "milestone", "authority",
            "authorized_at_utc", "scope", "evidence_path",
        )
        if not isinstance(authorization_record, dict) or any(key not in authorization_record for key in required_record_keys):
            errors.append({"code": "MILESTONE_AUTHORIZATION_EVIDENCE", "path": STATE_REL, "message": "An authorized milestone requires a structured direct-authorization record with task, scope, timestamp, and evidence path."})
        else:
            if not isinstance(authorization_record["authorization_id"], str) or not authorization_record["authorization_id"].strip():
                errors.append({"code": "MILESTONE_AUTHORIZATION_EVIDENCE", "path": STATE_REL, "message": "Authorization record needs a non-empty authorization_id."})
            if authorization_record["authority"] != "direct_user_or_pm_instruction":
                errors.append({"code": "MILESTONE_AUTHORIZATION_EVIDENCE", "path": STATE_REL, "message": "Authorization must cite a direct user/PM instruction; plans and completed dependencies are not authority."})
            if authorization_record["milestone"] != engineering.get("next_milestone"):
                errors.append({"code": "MILESTONE_AUTHORIZATION_EVIDENCE", "path": STATE_REL, "message": "Authorization record milestone must match engineering.next_milestone."})
            if not isinstance(authorization_record["task_id"], str) or not TASK_ID.fullmatch(authorization_record["task_id"]):
                errors.append({"code": "MILESTONE_AUTHORIZATION_EVIDENCE", "path": STATE_REL, "message": "Authorization record task_id must be a task ID."})
            if not isinstance(authorization_record["scope"], str) or not authorization_record["scope"].strip():
                errors.append({"code": "MILESTONE_AUTHORIZATION_EVIDENCE", "path": STATE_REL, "message": "Authorization record must state its bounded scope."})
            timestamp = authorization_record["authorized_at_utc"]
            if not isinstance(timestamp, str) or not timestamp.endswith("Z"):
                errors.append({"code": "MILESTONE_AUTHORIZATION_EVIDENCE", "path": STATE_REL, "message": "Authorization timestamp must be UTC ISO 8601 ending in Z."})
            else:
                try:
                    datetime.fromisoformat(timestamp[:-1] + "+00:00")
                except ValueError:
                    errors.append({"code": "MILESTONE_AUTHORIZATION_EVIDENCE", "path": STATE_REL, "message": "Authorization timestamp is not valid ISO 8601."})
            evidence_path = authorization_record["evidence_path"]
            if not _relative_path(evidence_path) or not evidence_path.startswith(".agents/evidence/"):
                errors.append({"code": "MILESTONE_AUTHORIZATION_EVIDENCE", "path": STATE_REL, "message": "Authorization evidence_path must be a repository-relative .agents/evidence/ path."})
    if governance.get("current_gate") == "G1" and "G1" not in governance.get("approved_gates", []) and engineering.get("start_authorized"):
        errors.append({"code": code, "path": STATE_REL, "message": "M0/M1 cannot be authorized before G1 approval."})
    if engineering.get("next_milestone") == "M0" and not engineering.get("start_authorized") and engineering.get("next_milestone_status") != "pending_user_approval":
        errors.append({"code": code, "path": STATE_REL, "message": "Unapproved M0 must be pending_user_approval."})
    milestone_status = engineering.get("next_milestone_status")
    authorized = engineering.get("start_authorized") is True
    if authorized:
        if milestone_status == "in_progress" and active != engineering.get("next_milestone"):
            errors.append({"code": "MILESTONE_AUTHORIZATION_MISMATCH", "path": STATE_REL, "message": "An in-progress authorized milestone must be the active next milestone."})
        elif milestone_status == "blocked" and active != engineering.get("next_milestone"):
            errors.append({"code": "MILESTONE_AUTHORIZATION_MISMATCH", "path": STATE_REL, "message": "A blocked authorized milestone must remain the active next milestone."})
        elif milestone_status == "ready_to_start" and active is not None:
            errors.append({"code": "MILESTONE_AUTHORIZATION_MISMATCH", "path": STATE_REL, "message": "A ready_to_start milestone must not be active before implementation begins."})
        elif milestone_status not in {"ready_to_start", "in_progress", "blocked"}:
            errors.append({"code": "MILESTONE_AUTHORIZATION_MISMATCH", "path": STATE_REL, "message": "An authorized milestone must be ready_to_start, in_progress, or blocked."})
    elif milestone_status in {"ready_to_start", "in_progress"}:
        errors.append({"code": "MILESTONE_AUTHORIZATION_MISMATCH", "path": STATE_REL, "message": "A ready_to_start or in-progress milestone requires separate explicit start authorization."})

    task_refs = state["task_refs"]
    if not isinstance(task_refs, dict):
        errors.append({"code": code, "path": STATE_REL, "message": "task_refs must be an object."})
        return
    if not _require_keys(task_refs, ("active_task_id", "next_task_id"), code, STATE_REL, errors):
        return
    for key in ("active_task_id", "next_task_id"):
        task_id = task_refs[key]
        if task_id is not None and (not isinstance(task_id, str) or not TASK_ID.fullmatch(task_id)):
            errors.append({"code": code, "path": STATE_REL, "message": f"task_refs.{key} must be null or a valid task ID."})

    active_blocker_ids = state["active_blocker_ids"]
    if not isinstance(active_blocker_ids, list) or any(not isinstance(item, str) or not re.fullmatch(r"BLK-\d{3}", item) for item in active_blocker_ids):
        errors.append({"code": code, "path": STATE_REL, "message": "active_blocker_ids must contain BLK-NNN IDs."})

    checkpoint = state["last_checkpoint"]
    if not isinstance(checkpoint, dict):
        errors.append({"code": code, "path": STATE_REL, "message": "last_checkpoint must be an object."})
        return
    if not _require_keys(checkpoint, ("id", "created_at_utc", "git"), code, STATE_REL, errors):
        return
    if not isinstance(checkpoint["id"], str) or not checkpoint["id"] or not isinstance(checkpoint["created_at_utc"], str):
        errors.append({"code": code, "path": STATE_REL, "message": "Invalid last_checkpoint id/timestamp."})
    if "workspace_id" in checkpoint and (not isinstance(checkpoint["workspace_id"], str) or not WORKSPACE_ID.fullmatch(checkpoint["workspace_id"])):
        errors.append({"code": code, "path": STATE_REL, "message": "last_checkpoint.workspace_id must be a local UUID when present."})
    git = checkpoint["git"]
    if not isinstance(git, dict):
        errors.append({"code": code, "path": STATE_REL, "message": "last_checkpoint.git must be an object."})
        return
    if not _require_keys(
        git,
        ("branch", "head", "status_entries", "status_sha256", "repo_file_hashes", "unhashed_large_files", "unreadable_files", "artifact_dirs_requiring_manifest", "excluded_directories", "excluded_symlink_files"),
        code,
        STATE_REL,
        errors,
    ):
        return
    if git.get("scope", "workspace") != "workspace":
        errors.append({"code": code, "path": STATE_REL, "message": "last_checkpoint.git must be a workspace-local observation."})
    if not isinstance(git["branch"], str) or not isinstance(git["head"], str) or not git["head"]:
        errors.append({"code": code, "path": STATE_REL, "message": "Invalid last_checkpoint.git branch/head."})
    entries = git["status_entries"]
    if not isinstance(entries, list) or any(not isinstance(entry, str) for entry in entries):
        errors.append({"code": code, "path": STATE_REL, "message": "last_checkpoint.git.status_entries must be strings."})
    elif not isinstance(git["status_sha256"], str) or git["status_sha256"] != _status_digest(entries):
        errors.append({"code": code, "path": STATE_REL, "message": "last_checkpoint.git.status_sha256 does not match status_entries."})
    hashes = git["repo_file_hashes"]
    if not isinstance(hashes, dict) or any(not _relative_path(path) or not isinstance(digest, str) or not SHA256.fullmatch(digest) for path, digest in hashes.items()):
        errors.append({"code": code, "path": STATE_REL, "message": "repo_file_hashes must map repository-relative paths to SHA-256."})
    elif any(_sensitive_relative_path(path) for path in hashes):
        errors.append({"code": code, "path": STATE_REL, "message": "Credential/chat-history paths must not be content-hashed into project state."})
    large_paths = git["unhashed_large_files"]
    if not isinstance(large_paths, list) or any(not _relative_path(path) or _sensitive_relative_path(path) for path in large_paths):
        errors.append({"code": code, "path": STATE_REL, "message": "unhashed_large_files must contain repository-relative non-sensitive paths."})
    unreadable_paths = git["unreadable_files"]
    if not isinstance(unreadable_paths, list) or any(not _relative_path(path) or _sensitive_relative_path(path) for path in unreadable_paths):
        errors.append({"code": code, "path": STATE_REL, "message": "unreadable_files must contain repository-relative non-sensitive paths."})
    artifact_dirs = git["artifact_dirs_requiring_manifest"]
    excluded_dirs = git["excluded_directories"]
    if not isinstance(artifact_dirs, list) or any(not _relative_path(path) for path in artifact_dirs):
        errors.append({"code": code, "path": STATE_REL, "message": "artifact_dirs_requiring_manifest must contain repository-relative paths."})
    if not isinstance(excluded_dirs, list) or any(not _relative_path(path) for path in excluded_dirs):
        errors.append({"code": code, "path": STATE_REL, "message": "excluded_directories must contain repository-relative paths."})
    if isinstance(artifact_dirs, list) and isinstance(excluded_dirs, list) and not set(artifact_dirs).issubset(excluded_dirs):
        errors.append({"code": code, "path": STATE_REL, "message": "Artifact directories must also appear in excluded_directories."})
    if not isinstance(git["excluded_symlink_files"], int) or isinstance(git["excluded_symlink_files"], bool) or git["excluded_symlink_files"] < 0:
        errors.append({"code": code, "path": STATE_REL, "message": "excluded_symlink_files must be a non-negative integer."})
    if "portable_git" in checkpoint:
        _validate_portable_snapshot(checkpoint["portable_git"], errors)

    baseline = state["g1_baseline"]
    if not isinstance(baseline, dict):
        errors.append({"code": code, "path": STATE_REL, "message": "g1_baseline must be an object."})
        return
    if not _require_keys(baseline, ("verified_at_utc", "branch", "head", "status_entries", "preserved_sha256", "g1_expected_modified_sha256", "comparison_policy", "baseline_sha256"), code, STATE_REL, errors):
        return
    baseline_payload = {key: value for key, value in baseline.items() if key != "baseline_sha256"}
    baseline_digest = hashlib.sha256(json.dumps(baseline_payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")).hexdigest()
    if baseline.get("baseline_sha256") != baseline_digest:
        errors.append({"code": "G1_BASELINE_INTEGRITY", "path": STATE_REL, "message": "Historical G1 baseline checksum does not match its recorded fields."})
    for key in ("preserved_sha256", "g1_expected_modified_sha256"):
        value = baseline[key]
        if not isinstance(value, dict) or any(not _relative_path(path) or _sensitive_relative_path(path) or not isinstance(digest, str) or not SHA256.fullmatch(digest) for path, digest in value.items()):
            errors.append({"code": code, "path": STATE_REL, "message": f"g1_baseline.{key} must map relative paths to SHA-256."})
    if not isinstance(baseline["status_entries"], list) or any(not isinstance(entry, str) for entry in baseline["status_entries"]):
        errors.append({"code": code, "path": STATE_REL, "message": "g1_baseline.status_entries must be strings."})


def _parse_blockers(text: str) -> set[str]:
    ids = set()
    matches = list(BLOCKER_HEADING.finditer(text))
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        section = text[match.start():end]
        if re.search(r"(?im)^- \*\*Status:\*\* `active`\s*$", section):
            ids.add(match.group(1))
    return ids


def _load_gate_milestone_coverage(root: Path) -> dict[str, set[str]]:
    """Read milestone coverage from ADR-0001 instead of maintaining a second crosswalk."""
    path = root / "docs/02-management/decisions/ADR-0001-governance-crosswalk-and-file-priorities.md"
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return {}
    coverage: dict[str, set[str]] = {}
    row = re.compile(r"(?m)^\s*\|\s*(G[0-5])\s+—[^|]*\|\s*([^|]+)\|")
    milestone = re.compile(r"M([0-7])(?:\s*[–-]\s*M?([0-7]))?")
    for gate, description in row.findall(text):
        covered: set[str] = set()
        for match in milestone.finditer(description):
            first = int(match.group(1))
            last = int(match.group(2)) if match.group(2) is not None else first
            covered.update(f"M{number}" for number in range(first, last + 1))
        if covered:
            coverage[gate] = covered
    return coverage


def _load_m7_gate_criteria(root: Path) -> dict[str, set[str]]:
    """Read M7's split G4/G5 acceptance ownership from the canonical criteria file."""
    path = root / "docs/06-quality/ACCEPTANCE_CRITERIA.md"
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return {}
    allocation = re.search(r"(?m)^M7 remains one engineering milestone,.*$", text)
    if allocation is None:
        return {}
    coverage: dict[str, set[str]] = {}
    pattern = re.compile(r"(G[0-5]) owns the [^.;]*? (M7-\d{2})[–-](?:M7-)?(\d{2})")
    for gate, first_id, last_number in pattern.findall(allocation.group(0)):
        first_number = int(first_id[-2:])
        last_number = int(last_number)
        coverage.setdefault(gate, set()).update(
            f"M7-{number:02d}" for number in range(first_number, last_number + 1)
        )
    return coverage


def _load_acceptance_ids(root: Path, errors: list[dict[str, str]]) -> set[str]:
    rel = "docs/06-quality/ACCEPTANCE_CRITERIA.md"
    try:
        text = (root / rel).read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        errors.append({"code": "ACCEPTANCE_READ", "path": rel, "message": str(exc)})
        return set()
    text = _strip_fenced_code(text)
    table_ids = re.findall(r"(?m)^\|\s*((?:G[0-5]|M[0-7])-\d{2})\s*\|", text)
    bullet_ids = re.findall(r"(?m)^\s*[-*]\s+\*\*((?:G[0-5]|M[0-7])-\d{2}):\*\*", text)
    return set(table_ids + bullet_ids)


def _check_task_graph(backlog: dict[str, object], root: Path, state: dict[str, object], blockers: set[str], acceptance_ids: set[str], errors: list[dict[str, str]]) -> tuple[dict[str, dict[str, object]], dict[str, int]]:
    code = "BACKLOG_SCHEMA"
    rel = BACKLOG_REL
    if not _require_keys(backlog, ("format", "schema_version", "project_id", "tasks"), code, rel, errors):
        return {}, {}
    if backlog["format"] != "JSON-compatible YAML 1.2" or backlog["schema_version"] != SCHEMA_VERSION or backlog["project_id"] != "atari-videochess-rl":
        errors.append({"code": code, "path": rel, "message": "Unsupported backlog format/schema_version/project_id."})
    raw_tasks = backlog["tasks"]
    if not isinstance(raw_tasks, list):
        errors.append({"code": code, "path": rel, "message": "tasks must be a list."})
        return {}, {}
    gate_coverage = _load_gate_milestone_coverage(root)
    m7_gate_criteria = _load_m7_gate_criteria(root)
    tasks: dict[str, dict[str, object]] = {}
    for index, task in enumerate(raw_tasks):
        where = f"{rel}:tasks[{index}]"
        if not isinstance(task, dict):
            errors.append({"code": "TASK_SCHEMA", "path": where, "message": "Task must be an object."})
            continue
        keys = ("id", "title", "milestone", "status", "next_action", "depends_on", "requires_user_gate_approval", "acceptance_criteria_ids", "blocker_ids", "evidence")
        if not _require_keys(task, keys, "TASK_SCHEMA", where, errors):
            continue
        task_id = task["id"]
        if not isinstance(task_id, str) or not TASK_ID.fullmatch(task_id):
            errors.append({"code": "TASK_SCHEMA", "path": where, "message": "Invalid task ID."})
            continue
        if task_id in tasks:
            errors.append({"code": "TASK_DUPLICATE", "path": where, "message": f"Duplicate task ID {task_id}."})
            continue
        if not isinstance(task["status"], str) or task["status"] not in ALLOWED_TASK_STATUSES:
            errors.append({"code": "TASK_SCHEMA", "path": where, "message": f"Unknown task status {task['status']!r}."})
        if not isinstance(task["title"], str) or not task["title"].strip():
            errors.append({"code": "TASK_SCHEMA", "path": where, "message": "Task title must be non-empty."})
        if not isinstance(task["next_action"], str) or (
            isinstance(task["status"], str) and task["status"] in {"pending", "in_progress", "blocked"} and not task["next_action"].strip()
        ):
            errors.append({"code": "TASK_SCHEMA", "path": where, "message": "Incomplete tasks require an explicit next_action string."})
        if (
            isinstance(task["status"], str)
            and task["status"] in {"done", "cancelled"}
            and isinstance(task["next_action"], str)
            and task["next_action"].strip()
        ):
            errors.append({"code": "TASK_SCHEMA", "path": where, "message": "Completed or cancelled tasks must have an empty next_action string."})
        if not isinstance(task["milestone"], str) or task["milestone"] != task_id.rsplit("-", 1)[0]:
            errors.append({"code": "TASK_SCHEMA", "path": where, "message": "Task milestone must match its ID prefix."})
        required_gate = task.get("requires_user_gate_approval")
        if required_gate is not None and (not isinstance(required_gate, str) or not GATE_ID.fullmatch(required_gate)):
            errors.append({"code": "TASK_SCHEMA", "path": where, "message": "requires_user_gate_approval must be null or a G0–G5 ID."})
        if isinstance(required_gate, str) and isinstance(task.get("milestone"), str):
            milestone = task["milestone"]
            task_criteria = task.get("acceptance_criteria_ids", [])
            circular = milestone != "M7" and milestone in gate_coverage.get(required_gate, set())
            if milestone == "M7" and milestone in gate_coverage.get(required_gate, set()):
                covered_criteria = m7_gate_criteria.get(required_gate)
                if covered_criteria is None:
                    errors.append({"code": "GATE_ACCEPTANCE_COVERAGE_UNRESOLVED", "path": where, "message": f"{required_gate} covers part of M7 in ADR-0001 but its criterion allocation could not be read from ACCEPTANCE_CRITERIA.md."})
                elif isinstance(task_criteria, list):
                    task_criterion_ids = {item for item in task_criteria if isinstance(item, str)}
                    circular = bool(task_criterion_ids & covered_criteria)
            if circular:
                errors.append({"code": "TASK_GATE_CIRCULAR", "path": where, "message": f"{required_gate} covers this task's {milestone} acceptance work in the canonical crosswalk and cannot be required before starting it; use separate milestone authorization."})
        if isinstance(required_gate, str) and task.get("status") == "in_progress":
            governance = state.get("governance", {}) if isinstance(state, dict) else {}
            if not isinstance(governance, dict) or required_gate not in governance.get("approved_gates", []):
                errors.append({"code": "TASK_GATE_NOT_APPROVED", "path": where, "message": f"In-progress task {task_id} requires already approved upstream gate {required_gate}."})
        plan_ref = task.get("plan_ref")
        if plan_ref is not None and (not _relative_path(plan_ref) or not (root / plan_ref).is_file()):
            errors.append({"code": "TASK_PLAN_MISSING", "path": where, "message": f"Task plan_ref is missing or not repository-relative: {plan_ref!r}."})
        for key in ("depends_on", "acceptance_criteria_ids", "blocker_ids", "evidence"):
            if not isinstance(task[key], list):
                errors.append({"code": "TASK_SCHEMA", "path": where, "message": f"{key} must be a list."})
        criteria = task["acceptance_criteria_ids"]
        if isinstance(criteria, list):
            if not criteria or any(not isinstance(item, str) or not re.fullmatch(r"(?:G[0-5]|M[0-7])-\d{2}", item) for item in criteria):
                errors.append({"code": "TASK_SCHEMA", "path": where, "message": "acceptance_criteria_ids must contain criterion IDs."})
            for criterion_id in criteria:
                if isinstance(criterion_id, str) and criterion_id not in acceptance_ids:
                    errors.append({"code": "TASK_ACCEPTANCE_UNKNOWN", "path": where, "message": f"Unknown acceptance criterion {criterion_id}."})
        if isinstance(task["depends_on"], list) and any(not isinstance(dep, str) or not TASK_ID.fullmatch(dep) for dep in task["depends_on"]):
            errors.append({"code": "TASK_SCHEMA", "path": where, "message": "depends_on contains an invalid task ID."})
        if isinstance(task["blocker_ids"], list) and any(not isinstance(item, str) or not re.fullmatch(r"BLK-\d{3}", item) for item in task["blocker_ids"]):
            errors.append({"code": "TASK_SCHEMA", "path": where, "message": "blocker_ids must contain BLK-NNN IDs."})
        if task["status"] == "blocked" and not task["blocker_ids"]:
            errors.append({"code": "TASK_BLOCKER_MISSING", "path": where, "message": "A blocked task must reference an active blocker."})
        if task["status"] == "done" and not task["evidence"]:
            errors.append({"code": "TASK_EVIDENCE_MISSING", "path": where, "message": "A done task must cite evidence."})
        if isinstance(task["evidence"], list):
            for evidence in task["evidence"]:
                if not isinstance(evidence, dict) or not isinstance(evidence.get("kind"), str) or evidence["kind"] not in {"file", "command", "test", "finding"}:
                    errors.append({"code": "TASK_EVIDENCE_SCHEMA", "path": where, "message": "Evidence entries need a supported kind."})
                    continue
                if evidence["kind"] == "file":
                    path = evidence.get("path")
                    if not _relative_path(path) or not (root / path).is_file():
                        errors.append({"code": "TASK_EVIDENCE_MISSING", "path": where, "message": f"Evidence file is missing or not repository-relative: {path!r}."})
                elif evidence.get("kind") in {"command", "test"} and (
                    not isinstance(evidence.get("command"), str) or not isinstance(evidence.get("result"), str)
                ):
                    errors.append({"code": "TASK_EVIDENCE_SCHEMA", "path": where, "message": "Command/test evidence requires command and result strings."})
                elif evidence.get("kind") == "finding" and (
                    not isinstance(evidence.get("finding_id"), str) or not isinstance(evidence.get("result"), str)
                ):
                    errors.append({"code": "TASK_EVIDENCE_SCHEMA", "path": where, "message": "Finding evidence requires finding_id and result strings."})
                provenance = evidence.get("provenance")
                if not isinstance(provenance, dict) or not isinstance(provenance.get("status"), str) or provenance["status"] not in {"verified", "historical_unverified", "manual_pending", "manual_verified"}:
                    errors.append({"code": "TASK_EVIDENCE_PROVENANCE", "path": where, "message": "Evidence requires a supported provenance status."})
                    continue
                required_provenance = ("executed_at_utc", "recorded_at_utc", "exit_code", "git_revision", "log_path")
                if any(key not in provenance for key in required_provenance):
                    errors.append({"code": "TASK_EVIDENCE_PROVENANCE", "path": where, "message": "Evidence provenance requires executed_at_utc, recorded_at_utc, exit_code, git_revision, and log_path fields."})
                    continue
                if provenance["status"] in {"verified", "manual_verified"}:
                    timestamp = provenance["recorded_at_utc"]
                    revision = provenance["git_revision"]
                    if not isinstance(timestamp, str) or not timestamp.endswith("Z"):
                        errors.append({"code": "TASK_EVIDENCE_PROVENANCE", "path": where, "message": "Verified evidence requires a UTC recorded_at_utc timestamp ending in Z."})
                    else:
                        try:
                            datetime.fromisoformat(timestamp[:-1] + "+00:00")
                        except ValueError:
                            errors.append({"code": "TASK_EVIDENCE_PROVENANCE", "path": where, "message": "Verified evidence recorded_at_utc is not a valid ISO 8601 timestamp."})
                    if not isinstance(revision, str) or not re.fullmatch(r"[0-9a-f]{40,64}", revision):
                        errors.append({"code": "TASK_EVIDENCE_PROVENANCE", "path": where, "message": "Verified evidence requires a full lowercase Git revision."})
                    kind = evidence.get("kind")
                    if kind in {"command", "test"} and provenance["status"] == "verified":
                        executed_at = provenance["executed_at_utc"]
                        if not isinstance(executed_at, str) or not executed_at.endswith("Z"):
                            errors.append({"code": "TASK_EVIDENCE_PROVENANCE", "path": where, "message": "Verified command/test evidence requires executed_at_utc in UTC ending in Z."})
                        else:
                            try:
                                datetime.fromisoformat(executed_at[:-1] + "+00:00")
                            except ValueError:
                                errors.append({"code": "TASK_EVIDENCE_PROVENANCE", "path": where, "message": "Verified command/test evidence executed_at_utc is not a valid ISO 8601 timestamp."})
                        exit_code = provenance["exit_code"]
                        log_path = provenance["log_path"]
                        if not isinstance(exit_code, int) or isinstance(exit_code, bool):
                            errors.append({"code": "TASK_EVIDENCE_PROVENANCE", "path": where, "message": "Verified command/test evidence requires an integer exit_code."})
                        if not _relative_path(log_path) or _sensitive_relative_path(log_path) or not (root / log_path).is_file():
                            errors.append({"code": "TASK_EVIDENCE_PROVENANCE", "path": where, "message": "Verified command/test evidence requires an existing repository-relative log_path."})
                        elif isinstance(evidence.get("command"), str) and isinstance(evidence.get("result"), str) and isinstance(exit_code, int) and not isinstance(exit_code, bool):
                            try:
                                log_text = (root / log_path).read_text(encoding="utf-8")
                            except (OSError, UnicodeError) as exc:
                                errors.append({"code": "TASK_EVIDENCE_LOG_MISMATCH", "path": where, "message": f"Could not read the retained command log: {exc}"})
                            else:
                                if evidence["command"] not in log_text or evidence["result"] not in log_text or f"Exit code: {exit_code}" not in log_text:
                                    errors.append({"code": "TASK_EVIDENCE_LOG_MISMATCH", "path": where, "message": "Retained command log does not contain the recorded command, result, and exit code."})
                    elif provenance["status"] == "manual_verified":
                        executed_at = provenance["executed_at_utc"]
                        if not isinstance(executed_at, str) or not executed_at.endswith("Z"):
                            errors.append({"code": "TASK_EVIDENCE_PROVENANCE", "path": where, "message": "Manual evidence requires executed_at_utc in UTC ending in Z."})
                        else:
                            try:
                                datetime.fromisoformat(executed_at[:-1] + "+00:00")
                            except ValueError:
                                errors.append({"code": "TASK_EVIDENCE_PROVENANCE", "path": where, "message": "Manual evidence executed_at_utc is not a valid ISO 8601 timestamp."})
                        log_path = provenance["log_path"]
                        if provenance["exit_code"] is not None or not _relative_path(log_path) or _sensitive_relative_path(log_path) or not (root / log_path).is_file():
                            errors.append({"code": "TASK_EVIDENCE_PROVENANCE", "path": where, "message": "Manual evidence requires null exit_code and an existing repository-relative sanitized log_path."})
                        elif isinstance(result_text := evidence.get("result"), str):
                            try:
                                log_text = (root / log_path).read_text(encoding="utf-8")
                            except (OSError, UnicodeError) as exc:
                                errors.append({"code": "TASK_EVIDENCE_LOG_MISMATCH", "path": where, "message": f"Could not read the retained manual evidence record: {exc}"})
                            else:
                                if result_text not in log_text:
                                    errors.append({"code": "TASK_EVIDENCE_LOG_MISMATCH", "path": where, "message": "Retained manual record does not contain the recorded result."})
                    elif provenance["executed_at_utc"] is not None or provenance["exit_code"] is not None or provenance["log_path"] is not None:
                        errors.append({"code": "TASK_EVIDENCE_PROVENANCE", "path": where, "message": "File/finding evidence must not claim a command execution time, exit_code, or log_path."})
                    result_text = evidence.get("result", evidence.get("detail"))
                    if not isinstance(result_text, str) or not result_text.strip():
                        errors.append({"code": "TASK_EVIDENCE_PROVENANCE", "path": where, "message": "Verified evidence requires a non-empty result or detail."})
                else:
                    if any(provenance[key] is not None for key in required_provenance):
                        errors.append({"code": "TASK_EVIDENCE_PROVENANCE", "path": where, "message": "Historical or pending evidence must leave unavailable execution metadata null."})
        if task["status"] == "done" and isinstance(task["evidence"], list):
            verified = any(
                isinstance(item, dict)
                and isinstance(item.get("provenance"), dict)
                and item["provenance"].get("status") in {"verified", "manual_verified"}
                for item in task["evidence"]
            )
            if not verified:
                errors.append({"code": "TASK_EVIDENCE_UNVERIFIED", "path": where, "message": "A done task needs at least one currently verified evidence entry; historical reports alone are insufficient."})
        tasks[task_id] = task

    for task_id, task in tasks.items():
        for dep in task.get("depends_on", []):
            if dep not in tasks:
                errors.append({"code": "TASK_DEPENDENCY_MISSING", "path": rel, "message": f"{task_id} depends on unknown task {dep}."})
        for blocker_id in task.get("blocker_ids", []):
            if blocker_id not in blockers or task["status"] != "blocked":
                errors.append({"code": "TASK_BLOCKER_MISMATCH", "path": rel, "message": f"{task_id} references a missing/non-active blocker {blocker_id}."})

    colors: dict[str, int] = {}
    cycle_found = False

    def visit(task_id: str) -> None:
        nonlocal cycle_found
        color = colors.get(task_id, 0)
        if color == 1:
            cycle_found = True
            return
        if color == 2:
            return
        colors[task_id] = 1
        for dep in tasks[task_id].get("depends_on", []):
            if dep in tasks:
                visit(dep)
        colors[task_id] = 2

    for task_id in tasks:
        visit(task_id)
    if cycle_found:
        errors.append({"code": "DEPENDENCY_CYCLE", "path": rel, "message": "Task dependencies contain a cycle."})

    engineering = state.get("engineering", {}) if isinstance(state, dict) else {}
    if isinstance(engineering, dict):
        authorized = engineering.get("start_authorized") is True
        milestone = engineering.get("next_milestone")
        authorization = engineering.get("start_authorization_record")
        if authorized and isinstance(authorization, dict):
            task_id = authorization.get("task_id")
            refs = state.get("task_refs", {}) if isinstance(state.get("task_refs"), dict) else {}
            active_task_id = refs.get("active_task_id")
            next_task_id = refs.get("next_task_id")
            task = tasks.get(task_id) if isinstance(task_id, str) else None
            running_match = (
                engineering.get("next_milestone_status") == "in_progress"
                and active_task_id == task_id
                and isinstance(task, dict)
                and task.get("status") == "in_progress"
                and task.get("milestone") == milestone
            )
            blocked_match = (
                engineering.get("next_milestone_status") == "blocked"
                and active_task_id == task_id
                and isinstance(task, dict)
                and task.get("status") == "blocked"
                and task.get("milestone") == milestone
                and bool(task.get("blocker_ids"))
            )
            ready_match = (
                engineering.get("next_milestone_status") == "ready_to_start"
                and active_task_id is None
                and next_task_id == task_id
                and isinstance(task, dict)
                and task.get("status") == "pending"
                and task.get("milestone") == milestone
            )
            if not (running_match or blocked_match or ready_match):
                errors.append({"code": "MILESTONE_AUTHORIZATION_EVIDENCE", "path": rel, "message": "Authorization must identify either the pending next task in ready_to_start state, the active in-progress task, or an active blocked task with a blocker."})
            else:
                path = authorization.get("evidence_path")
                matches = [
                    item for item in task.get("evidence", [])
                    if isinstance(item, dict) and item.get("kind") == "file"
                    and item.get("path") == path
                    and isinstance(item.get("provenance"), dict)
                    and item["provenance"].get("status") == "manual_verified"
                    and isinstance(item.get("result"), str)
                    and "direct" in item["result"].lower()
                    and "authoriz" in item["result"].lower()
                ]
                if not matches:
                    errors.append({"code": "MILESTONE_AUTHORIZATION_EVIDENCE", "path": rel, "message": "The authorized task must cite a manual_verified evidence file recording the direct authorization."})
        for task_id, task in tasks.items():
            if task.get("status") != "in_progress" or not isinstance(task.get("milestone"), str) or not re.fullmatch(r"M[0-7]", task["milestone"]):
                continue
            if not authorized or task.get("milestone") != milestone:
                errors.append({"code": "MILESTONE_AUTHORIZATION_MISMATCH", "path": rel, "message": f"In-progress engineering task {task_id} must match the explicitly authorized next milestone."})

    refs = state.get("task_refs", {}) if isinstance(state, dict) else {}
    if isinstance(refs, dict):
        for key in ("active_task_id", "next_task_id"):
            task_id = refs.get(key)
            if task_id is not None and task_id not in tasks:
                errors.append({"code": "TASK_REFERENCE_MISSING", "path": STATE_REL, "message": f"task_refs.{key} refers to unknown task {task_id}."})
        next_id = refs.get("next_task_id")
        if next_id in tasks and tasks[next_id].get("status") in {"done", "cancelled"}:
            errors.append({"code": "NEXT_TASK_INVALID", "path": STATE_REL, "message": "next_task_id must point to an incomplete task."})
        active_id = refs.get("active_task_id")
        if active_id in tasks and tasks[active_id].get("status") not in {"in_progress", "blocked"}:
            errors.append({"code": "ACTIVE_TASK_INVALID", "path": STATE_REL, "message": "active_task_id must point to an in_progress or blocked task."})

    counts = {status: sum(1 for task in tasks.values() if task.get("status") == status) for status in sorted(ALLOWED_TASK_STATUSES)}
    return tasks, counts


def _strip_fenced_code(text: str) -> str:
    kept: list[str] = []
    fence: str | None = None
    for line in text.splitlines():
        match = re.match(r"^\s*(`{3,}|~{3,})", line)
        if match:
            token = match.group(1)[0]
            if fence is None:
                fence = token
            elif token == fence:
                fence = None
            continue
        if fence is None:
            kept.append(line)
    return "\n".join(kept)


def _slug(heading: str) -> str:
    value = re.sub(r"`([^`]*)`", r"\1", heading).strip().lower()
    value = re.sub(r"[^\w\- ]", "", value, flags=re.UNICODE)
    return re.sub(r"[\s]+", "-", value)


def _check_markdown_links(root: Path, errors: list[dict[str, str]]) -> None:
    files: set[Path] = {root / "AGENTS.md", root / "README.md"}
    for base in (root / "docs", root / ".agents"):
        if base.exists():
            files.update(path for path in base.rglob("*.md") if path.is_file())
    for source in sorted(files):
        if not source.is_file():
            continue
        rel_source = source.relative_to(root).as_posix()
        try:
            text = _strip_fenced_code(source.read_text(encoding="utf-8"))
        except (OSError, UnicodeError) as exc:
            errors.append({"code": "MARKDOWN_READ", "path": rel_source, "message": str(exc)})
            continue
        heading_slugs: set[str] = set()
        for line in text.splitlines():
            heading = re.match(r"^#{1,6}\s+(.+?)\s*#*\s*$", line)
            if heading:
                slug = _slug(heading.group(1))
                if slug in heading_slugs:
                    suffix = 1
                    while f"{slug}-{suffix}" in heading_slugs:
                        suffix += 1
                    slug = f"{slug}-{suffix}"
                heading_slugs.add(slug)
        for match in MARKDOWN_LINK.finditer(text):
            target = unquote(match.group(3).strip("<>"))
            parsed = urlsplit(target)
            if parsed.scheme or target.startswith("//"):
                continue
            path_text = parsed.path
            if path_text:
                target_path = (source.parent / path_text).resolve()
            else:
                target_path = source.resolve()
            try:
                target_path.relative_to(root.resolve())
            except ValueError:
                errors.append({"code": "LINK_OUTSIDE_REPO", "path": rel_source, "message": f"Link target leaves repository: {target!r}."})
                continue
            if not target_path.is_file():
                errors.append({"code": "LINK_BROKEN", "path": rel_source, "message": f"Local Markdown target does not exist: {target!r}."})
                continue
            if parsed.fragment:
                try:
                    target_text = target_path.read_text(encoding="utf-8")
                except (OSError, UnicodeError):
                    continue
                slugs: set[str] = set()
                for line in target_text.splitlines():
                    heading = re.match(r"^#{1,6}\s+(.+?)\s*#*\s*$", line)
                    if heading:
                        slug = _slug(heading.group(1))
                        if slug in slugs:
                            suffix = 1
                            while f"{slug}-{suffix}" in slugs:
                                suffix += 1
                            slug = f"{slug}-{suffix}"
                        slugs.add(slug)
                if unquote(parsed.fragment).lower() not in slugs:
                    errors.append({"code": "LINK_ANCHOR_BROKEN", "path": rel_source, "message": f"Markdown heading anchor does not exist: {target!r}."})


def _validate_roadmap_source(root: Path, errors: list[dict[str, str]]) -> dict[str, object]:
    try:
        source = (root / ROADMAP_HTML_REL).read_bytes().decode("utf-8")
        roadmap = (root / ROADMAP_REL).read_bytes().decode("utf-8")
    except (OSError, UnicodeError) as exc:
        errors.append({"code": "ROADMAP_SOURCE_READ", "path": ROADMAP_HTML_REL, "message": str(exc)})
        return {"matches": False, "sha256": None, "roman_sections": 0}
    archive_match = re.search(r'<script id="rawArchive" type="text/plain">(.*?)</script>', source, re.S)
    pre_match = re.search(r'<details class="source-archive">.*?<pre>(.*?)</pre>\s*</details>', source, re.S)
    if not archive_match or not pre_match:
        errors.append({"code": "ROADMAP_SOURCE_MISSING", "path": ROADMAP_HTML_REL, "message": "Embedded rawArchive or displayed source archive is missing."})
        return {"matches": False, "sha256": hashlib.sha256(roadmap.encode("utf-8")).hexdigest(), "roman_sections": 0}
    embedded = archive_match.group(1)
    displayed = html.unescape(pre_match.group(1))
    roman = re.compile(r"^## (?:I|II|III|IV|V|VI|VII|VIII|IX|X|XI|XII|XIII|XIV|XV|XVI|XVII|XVIII|XIX)\. ")
    sections = [line for line in embedded.splitlines() if roman.match(line)]
    digest = hashlib.sha256(roadmap.encode("utf-8")).hexdigest()
    if embedded != displayed or roadmap != embedded:
        errors.append({"code": "ROADMAP_SOURCE_MISMATCH", "path": ROADMAP_REL, "message": "Extracted Markdown differs from the embedded or displayed original source."})
    if len(sections) != 19:
        errors.append({"code": "ROADMAP_SECTION_COUNT", "path": ROADMAP_REL, "message": f"Expected 19 Roman-numeral sections; found {len(sections)}."})
    return {"matches": embedded == displayed == roadmap, "sha256": digest, "roman_sections": len(sections)}


def _open_approvals(root: Path, errors: list[dict[str, str]]) -> list[dict[str, str]]:
    path = root / REQUIREMENTS_REL
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        errors.append({"code": "REQUIREMENTS_READ", "path": REQUIREMENTS_REL, "message": str(exc)})
        return []
    match = re.search(r"(?ms)^## 6\. Open approvals and evidence needed\s*$([\s\S]*?)(?=^## |\Z)", text)
    if not match:
        return []
    approvals: dict[str, str] = {}
    for line in match.group(1).splitlines():
        if not line.startswith("|"):
            continue
        columns = [column.strip() for column in line.strip().strip("|").split("|")]
        if len(columns) >= 2 and re.fullmatch(r"O-\d{2}", columns[0]):
            approvals[columns[0]] = columns[1]
    return [{"id": key, "title": approvals[key]} for key in sorted(approvals)]


def _validate_state_consistency(
    root: Path,
    state: dict[str, object],
    errors: list[dict[str, str]],
    warnings: list[dict[str, str]],
) -> tuple[set[str], dict[str, object], dict[str, object]]:
    blockers_path = root / BLOCKERS_REL
    try:
        blockers_text = blockers_path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        errors.append({"code": "BLOCKERS_READ", "path": BLOCKERS_REL, "message": str(exc)})
        return set(), {}, {}
    active_blockers = _parse_blockers(blockers_text)
    state_blockers = set(state.get("active_blocker_ids", []))
    if active_blockers != state_blockers:
        errors.append({"code": "BLOCKER_STATE_MISMATCH", "path": BLOCKERS_REL, "message": f"Active blockers in state {sorted(state_blockers)} differ from records {sorted(active_blockers)}."})

    handoff_path = root / HANDOFF_REL
    try:
        handoff = handoff_path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        errors.append({"code": "HANDOFF_READ", "path": HANDOFF_REL, "message": str(exc)})
        handoff = ""
    markers = CHECKPOINT_MARKER.findall(handoff)
    state_id = state.get("last_checkpoint", {}).get("id") if isinstance(state.get("last_checkpoint"), dict) else None
    if len(markers) != 1:
        errors.append({"code": "HANDOFF_POINTER_MISSING", "path": HANDOFF_REL, "message": "Expected exactly one checkpoint-id marker."})
    elif markers[0] != state_id:
        warnings.append({"code": "HANDOFF_STALE", "path": HANDOFF_REL, "message": "Handoff checkpoint ID differs from canonical project state; refresh from state/backlog."})

    for pattern in PARTIAL_STATE_PATTERNS:
        for rel in (root / ".agents/state").glob(pattern):
            warnings.append({"code": "PARTIAL_WRITE", "path": rel.relative_to(root).as_posix(), "message": "Agent-owned temporary file is not canonical state; inspect it and use --recover-partials if stale."})

    checkpoint = state.get("last_checkpoint", {})
    git_expected = checkpoint.get("git", {}) if isinstance(checkpoint, dict) else {}
    if not isinstance(git_expected, dict):
        git_expected = {}
    portable = checkpoint.get("portable_git") if isinstance(checkpoint, dict) else None
    try:
        live = _live_git_snapshot(root)
        index_manifest = _git_index_manifest(root)
        head_manifest = _git_head_manifest(root)
        current_workspace_id = _git_workspace_id(root)
    except RuntimeError as exc:
        errors.append({"code": "GIT_UNAVAILABLE", "path": ".", "message": str(exc)})
        live = {}
        index_manifest = {}
        head_manifest = {}
        current_workspace_id = None

    current_hashes, current_inventory = _repo_file_hash_inventory(root)
    workspace_snapshot_matches = False
    portable_baseline_matches = False
    portable_index_matches = False
    snapshot_mode = "workspace"
    expected_entries = git_expected.get("status_entries", [])
    if not isinstance(expected_entries, list):
        expected_entries = []
    live_entries = live.get("status_entries", []) if isinstance(live, dict) else []
    if not isinstance(live_entries, list):
        live_entries = []
    changed_keys = [key for key in ("branch", "head") if git_expected.get(key) != live.get(key)] if live else []
    if live and _workspace_comparable_status(expected_entries) != _workspace_comparable_status(live_entries):
        changed_keys.append("status_entries")
    workspace_snapshot_matches = bool(live and not changed_keys)
    strict_git_matches = workspace_snapshot_matches

    if live:
        if any(Path(path).name == "chat_history.md" for path in git_expected.get("repo_file_hashes", {})):
            errors.append({"code": "SENSITIVE_HISTORY_IN_STATE", "path": STATE_REL, "message": "Project state must not store a hash of chat_history.md."})

        portable_manifest = portable.get("tracked_manifest", {}) if isinstance(portable, dict) else {}
        usable_portable = isinstance(portable_manifest, dict) and bool(portable_manifest) and "README.md" in portable_manifest
        recorded_workspace_id = checkpoint.get("workspace_id") if isinstance(checkpoint, dict) else None
        same_workspace = bool(recorded_workspace_id and current_workspace_id == recorded_workspace_id)
        if usable_portable:
            portable_index_matches = index_manifest == portable_manifest
            portable_head_matches = head_manifest == portable_manifest
            current_state_hash = _portable_state_sha256(state)
            state_matches = current_state_hash == portable.get("state_sha256")
            handoff_matches = _sha_text(handoff) == portable.get("handoff_sha256")
            tracked_status = [
                entry for entry in live_entries
                if not entry.startswith("?? ") and entry[3:] not in PORTABLE_EXCLUDED_PATHS
            ]

            if not state_matches:
                warnings.append({"code": "PORTABLE_STATE_DRIFT", "path": STATE_REL, "message": "Portable semantic state checksum differs from the recorded checkpoint."})
            if not handoff_matches:
                warnings.append({"code": "PORTABLE_HANDOFF_DRIFT", "path": HANDOFF_REL, "message": "Portable handoff checksum differs from the recorded checkpoint."})

            if portable_head_matches:
                portable_baseline_matches = True
            if portable_head_matches and portable_index_matches and not tracked_status and state_matches and handoff_matches:
                if (
                    live.get("head") != git_expected.get("head")
                    or live.get("branch") != git_expected.get("branch")
                    or not same_workspace
                ):
                    snapshot_mode = "portable_commit_transition"
                elif strict_git_matches:
                    snapshot_mode = "workspace_portable_match"
                else:
                    snapshot_mode = "portable_baseline_with_local_changes"
            elif portable_head_matches:
                snapshot_mode = "portable_baseline_with_local_changes"
                if not portable_index_matches:
                    added = sorted(set(index_manifest) - set(portable_manifest))
                    removed = sorted(set(portable_manifest) - set(index_manifest))
                    changed = sorted(path for path in set(index_manifest) & set(portable_manifest) if index_manifest[path] != portable_manifest[path])
                    details = []
                    if added: details.append("staged paths added: " + ", ".join(added[:10]) + (", …" if len(added) > 10 else ""))
                    if removed: details.append("staged paths removed: " + ", ".join(removed[:10]) + (", …" if len(removed) > 10 else ""))
                    if changed: details.append("staged objects changed: " + ", ".join(changed[:10]) + (", …" if len(changed) > 10 else ""))
                    warnings.append({"code": "PORTABLE_INDEX_DRIFT", "path": ".", "message": "; ".join(details) + ". Inspect staged changes before refreshing the checkpoint."})
                if tracked_status:
                    warnings.append({"code": "WORKTREE_CONTENT_DRIFT", "path": ".", "message": "Tracked worktree changes exist after the portable baseline checkpoint: " + "; ".join(tracked_status[:10]) + ("; …" if len(tracked_status) > 10 else "") + "."})
            elif live.get("head") != git_expected.get("head"):
                snapshot_mode = "unexplained_git_transition"
                changed_paths = sorted(set(head_manifest) ^ set(portable_manifest))
                altered_paths = sorted(path for path in set(head_manifest) & set(portable_manifest) if head_manifest[path] != portable_manifest[path])
                details = []
                if changed_paths:
                    details.append("tracked paths added/removed: " + ", ".join(changed_paths[:10]) + (", …" if len(changed_paths) > 10 else ""))
                if altered_paths:
                    details.append("tracked objects changed: " + ", ".join(altered_paths[:10]) + (", …" if len(altered_paths) > 10 else ""))
                warnings.append({"code": "PORTABLE_BASELINE_DRIFT", "path": ".", "message": ("; ".join(details) or "HEAD differs from the portable baseline") + ". The Git transition is not explained by the recorded tracked-file manifest."})
            elif not portable_index_matches:
                snapshot_mode = "workspace_with_index_drift"
                added = sorted(set(index_manifest) - set(portable_manifest))
                removed = sorted(set(portable_manifest) - set(index_manifest))
                changed = sorted(path for path in set(index_manifest) & set(portable_manifest) if index_manifest[path] != portable_manifest[path])
                details = []
                if added: details.append("staged paths added: " + ", ".join(added[:10]) + (", …" if len(added) > 10 else ""))
                if removed: details.append("staged paths removed: " + ", ".join(removed[:10]) + (", …" if len(removed) > 10 else ""))
                if changed: details.append("staged objects changed: " + ", ".join(changed[:10]) + (", …" if len(changed) > 10 else ""))
                warnings.append({"code": "PORTABLE_INDEX_DRIFT", "path": ".", "message": "; ".join(details) + ". Inspect staged changes before refreshing the checkpoint."})
        elif (
            (live.get("head") != git_expected.get("head") or not same_workspace)
            and not [entry for entry in live_entries if not entry.startswith("?? ") and entry[3:] not in PORTABLE_EXCLUDED_PATHS]
            and _legacy_portable_match(root, git_expected, current_hashes)
        ):
            snapshot_mode = "legacy_portable_commit_transition"
            portable_baseline_matches = True
        elif live.get("head") != git_expected.get("head"):
            snapshot_mode = "unverified_legacy_git_transition"
            warnings.append({"code": "GIT_COMMIT_TRANSITION_UNVERIFIED", "path": ".", "message": "Legacy checkpoint has no portable manifest and its tracked files could not be verified against the current checkout. Run agent_checkpoint.py to migrate safely."})

        portable_mode = snapshot_mode in {"portable_commit_transition", "legacy_portable_commit_transition"}
        same_workspace_head = live.get("head") == git_expected.get("head") and live.get("branch") == git_expected.get("branch")
        if not portable_mode and same_workspace_head:
            if changed_keys:
                added_entries = sorted(set(live_entries) - set(expected_entries))
                removed_entries = sorted(set(expected_entries) - set(live_entries))
                details = f"Changed fields: {', '.join(changed_keys)}."
                if added_entries:
                    details += " New/changed status entries: " + "; ".join(added_entries[:10]) + ("; …" if len(added_entries) > 10 else "") + "."
                if removed_entries:
                    details += " Entries no longer present: " + "; ".join(removed_entries[:10]) + ("; …" if len(removed_entries) > 10 else "") + "."
                warnings.append({"code": "GIT_SNAPSHOT_DRIFT", "path": ".", "message": details + " Inspect the workspace snapshot; do not discard changes."})

            expected_hashes = git_expected.get("repo_file_hashes", {})
            if isinstance(expected_hashes, dict):
                added = sorted(set(current_hashes) - set(expected_hashes))
                removed = sorted(set(expected_hashes) - set(current_hashes))
                changed = sorted(path for path in set(current_hashes) & set(expected_hashes) if current_hashes[path] != expected_hashes[path])
                if added or removed or changed:
                    details = []
                    if added: details.append("newly hashed workspace files: " + ", ".join(added[:10]) + (", …" if len(added) > 10 else ""))
                    if removed: details.append("workspace files missing/excluded: " + ", ".join(removed[:10]) + (", …" if len(removed) > 10 else ""))
                    if changed: details.append("workspace content changed: " + ", ".join(changed[:10]) + (", …" if len(changed) > 10 else ""))
                    warnings.append({"code": "WORKTREE_CONTENT_DRIFT", "path": ".", "message": "; ".join(details) + ". Inspect before checkpointing."})

            for field in ("unhashed_large_files", "unreadable_files", "artifact_dirs_requiring_manifest", "excluded_symlink_files"):
                expected_value = git_expected.get(field, 0 if field == "excluded_symlink_files" else [])
                current_value = current_inventory.get(field, 0 if field == "excluded_symlink_files" else [])
                if field == "excluded_symlink_files":
                    changed_inventory = expected_value != current_value
                    added_paths = []
                    removed_paths = []
                else:
                    expected_paths = sorted(expected_value) if isinstance(expected_value, list) else []
                    current_paths = sorted(current_value) if isinstance(current_value, list) else []
                    added_paths = sorted(set(current_paths) - set(expected_paths))
                    removed_paths = sorted(set(expected_paths) - set(current_paths))
                    changed_inventory = expected_paths != current_paths
                if changed_inventory:
                    details = [f"{field} changed"]
                    if added_paths: details.append("new: " + ", ".join(added_paths[:10]) + (", …" if len(added_paths) > 10 else ""))
                    if removed_paths: details.append("removed: " + ", ".join(removed_paths[:10]) + (", …" if len(removed_paths) > 10 else ""))
                    warnings.append({"code": "WORKTREE_HASH_INVENTORY_DRIFT", "path": ".", "message": "; ".join(details) + ". Inspect workspace-specific artifacts and refresh the checkpoint when understood."})

        if current_inventory.get("unhashed_large_files"):
            large = current_inventory["unhashed_large_files"]
            warnings.append({"code": "WORKTREE_LARGE_FILES_UNHASHED", "path": ".", "message": "Files above the 2 MiB hash limit are excluded from local content verification: " + ", ".join(large[:10]) + (", …" if len(large) > 10 else "") + ". Verify relevant artifacts with an independent manifest/checksum."})
        if current_inventory.get("unreadable_files"):
            unreadable = current_inventory["unreadable_files"]
            warnings.append({"code": "WORKTREE_UNREADABLE_FILES", "path": ".", "message": "Files that could not be read or hashed are not content-verified: " + ", ".join(unreadable[:10]) + (", …" if len(unreadable) > 10 else "") + ". Inspect permissions or concurrent changes."})
        if current_inventory.get("artifact_dirs_requiring_manifest"):
            artifact_dirs = current_inventory["artifact_dirs_requiring_manifest"]
            warnings.append({"code": "ARTIFACT_MANIFEST_REQUIRED", "path": ".", "message": "Artifact/data directories are excluded from content hashing and require independent manifest verification: " + ", ".join(artifact_dirs[:10]) + (", …" if len(artifact_dirs) > 10 else "") + "."})

    portable_mode = snapshot_mode in {"portable_commit_transition", "legacy_portable_commit_transition"}
    git_matches = bool(strict_git_matches or portable_mode)
    inventory_summary = {
        "repo_file_hashes": current_hashes,
        **current_inventory,
        "git_snapshot_mode": snapshot_mode,
        "workspace_snapshot_matches": workspace_snapshot_matches,
        "portable_baseline_matches": portable_baseline_matches,
        "portable_index_matches": portable_index_matches,
        "git_snapshot_matches": git_matches,
    }
    return active_blockers, live, inventory_summary


def build_report(root: Path) -> dict[str, object]:
    errors: list[dict[str, str]] = []
    warnings: list[dict[str, str]] = []
    root = root.resolve()
    for rel in REQUIRED_FILES:
        if not (root / rel).is_file():
            errors.append({"code": "REQUIRED_FILE_MISSING", "path": rel, "message": "Required G1 context or validation file is missing."})

    _check_markdown_links(root, errors)
    roadmap_source = {"matches": False, "sha256": None, "roman_sections": 0}
    if (root / ROADMAP_REL).is_file() and (root / ROADMAP_HTML_REL).is_file():
        roadmap_source = _validate_roadmap_source(root, errors)
    state = _load_json_yaml(root, STATE_REL, "STATE_SCHEMA", errors)
    backlog = _load_json_yaml(root, BACKLOG_REL, "BACKLOG_SCHEMA", errors)
    history_inspection = None
    if state is None:
        state = {}
    else:
        _validate_state(state, errors)
        history_inspection = inspect_history_storage(root, state)
        for history_code, history_message in history_inspection.errors:
            errors.append({"code": history_code, "path": CHECKPOINT_HISTORY_ARCHIVE_REL, "message": history_message})
    if backlog is None:
        backlog = {}

    blockers: set[str] = set()
    try:
        blockers_text = (root / BLOCKERS_REL).read_text(encoding="utf-8")
        blockers = _parse_blockers(blockers_text)
    except (OSError, UnicodeError):
        pass
    tasks: dict[str, dict[str, object]] = {}
    counts: dict[str, int] = {}
    acceptance_ids = _load_acceptance_ids(root, errors)
    if isinstance(backlog, dict):
        tasks, counts = _check_task_graph(backlog, root, state, blockers, acceptance_ids, errors)
    active_blockers, live_git, content_inventory = _validate_state_consistency(root, state, errors, warnings) if state else (set(), {}, {})
    governance_state = state.get("governance", {}) if isinstance(state, dict) else {}
    if isinstance(governance_state, dict) and governance_state.get("current_gate") == "G1":
        engineering_state = state.get("engineering", {})
        g1_tasks = [task for task in tasks.values() if task.get("milestone") == "G1"]
        gate_status = governance_state.get("gate_status")
        if not isinstance(engineering_state, dict) or engineering_state.get("next_milestone") != "M0" or engineering_state.get("start_authorized") is not False:
            errors.append({"code": "G1_M0_GATE_MISMATCH", "path": STATE_REL, "message": "During G1, M0 must remain next and unauthorized."})
        if gate_status == "in_progress" and not any(task.get("status") == "in_progress" for task in g1_tasks):
            errors.append({"code": "G1_PROGRESS_MISMATCH", "path": BACKLOG_REL, "message": "G1 is in progress but no G1 task is in progress."})
        if gate_status == "ready_for_user_review" and any(task.get("status") != "done" for task in g1_tasks):
            errors.append({"code": "G1_REVIEW_INCOMPLETE", "path": BACKLOG_REL, "message": "G1 cannot be ready for review while a G1 task is incomplete."})

    open_approvals = _open_approvals(root, errors) if (root / REQUIREMENTS_REL).is_file() else []
    decision_dir = root / "docs/02-management/decisions"
    decision_refs = sorted(path.relative_to(root).as_posix() for path in decision_dir.glob("ADR-*.md")) if decision_dir.exists() else []
    governance = state.get("governance", {}) if isinstance(state, dict) else {}
    engineering = state.get("engineering", {}) if isinstance(state, dict) else {}
    refs = state.get("task_refs", {}) if isinstance(state, dict) else {}
    next_id = refs.get("next_task_id") if isinstance(refs, dict) else None
    next_task = tasks.get(next_id) if isinstance(next_id, str) else None
    active_id = refs.get("active_task_id") if isinstance(refs, dict) else None
    active_task = tasks.get(active_id) if isinstance(active_id, str) else None
    snapshot = state.get("last_checkpoint", {}) if isinstance(state, dict) else {}
    snapshot_git = snapshot.get("git", {}) if isinstance(snapshot, dict) else {}
    snapshot_branch = snapshot_git.get("branch") if isinstance(snapshot_git, dict) else None
    snapshot_head = snapshot_git.get("head") if isinstance(snapshot_git, dict) else None
    expected_status = set(snapshot_git.get("status_entries", [])) if isinstance(snapshot_git, dict) else set()
    live_status = set(live_git.get("status_entries", [])) if isinstance(live_git, dict) else set()
    comparable_expected_status = set(_workspace_comparable_status(sorted(expected_status)))
    comparable_live_status = set(_workspace_comparable_status(sorted(live_status)))
    snapshot_mode = content_inventory.get("git_snapshot_mode", "workspace")
    workspace_snapshot_matches = bool(content_inventory.get("workspace_snapshot_matches", False))
    portable_baseline_matches = bool(content_inventory.get("portable_baseline_matches", False))
    portable_index_matches = bool(content_inventory.get("portable_index_matches", False))
    git_matches = bool(content_inventory.get("git_snapshot_matches", workspace_snapshot_matches))
    live_branch = live_git.get("branch") if isinstance(live_git, dict) else None
    live_head = live_git.get("head") if isinstance(live_git, dict) else None
    portable_commit_modes = {"portable_commit_transition", "legacy_portable_commit_transition"}
    if snapshot_mode in portable_commit_modes:
        expected_status = set(live_status)
    content_drift_codes = {
        "WORKTREE_CONTENT_DRIFT",
        "WORKTREE_HASH_INVENTORY_DRIFT",
        "WORKTREE_UNREADABLE_FILES",
        "WORKTREE_TRACKED_DRIFT",
        "PORTABLE_BASELINE_DRIFT",
        "PORTABLE_INDEX_DRIFT",
        "PORTABLE_STATE_DRIFT",
        "PORTABLE_HANDOFF_DRIFT",
        "GIT_COMMIT_TRANSITION_UNVERIFIED",
    }
    repo_content_matches = not any(item.get("code") in content_drift_codes for item in warnings)
    return {
        "ok": not errors,
        "errors": errors,
        "warnings": warnings,
        "summary": {
            "current_gate": governance.get("current_gate"),
            "gate_status": governance.get("gate_status"),
            "approved_gates": governance.get("approved_gates", []),
            "next_milestone": engineering.get("next_milestone"),
            "next_milestone_status": engineering.get("next_milestone_status"),
            "engineering_start_authorized": engineering.get("start_authorized"),
            "next_user_action": governance.get("next_user_action"),
            "active_task_id": active_id,
            "active_task_title": active_task.get("title") if active_task else None,
            "active_task_next_action": active_task.get("next_action") if active_task else None,
            "next_task_id": next_id,
            "next_task_title": next_task.get("title") if next_task else None,
            "next_task_status": next_task.get("status") if next_task else None,
            "next_task_next_action": next_task.get("next_action") if next_task else None,
            "next_task_dependencies": next_task.get("depends_on", []) if next_task else [],
            "next_task_acceptance_criteria_ids": next_task.get("acceptance_criteria_ids", []) if next_task else [],
            "task_counts": counts,
            "task_ids_by_status": {
                status: sorted(task_id for task_id, task in tasks.items() if task.get("status") == status)
                for status in sorted(ALLOWED_TASK_STATUSES)
            },
            "active_blocker_ids": sorted(active_blockers),
            "open_approval_ids": [item["id"] for item in open_approvals],
            "open_approvals": open_approvals,
            "decision_refs": decision_refs,
            "acceptance_criteria_ids": sorted(acceptance_ids),
            "last_checkpoint_id": snapshot.get("id") if isinstance(snapshot, dict) else None,
            "checkpoint_history_storage": "archive" if isinstance(state, dict) and CHECKPOINT_HISTORY_POINTER_KEY in state else "legacy_inline",
            "checkpoint_history_count": len(history_inspection.records) if history_inspection is not None else None,
            "checkpoint_history_sha256": state.get(CHECKPOINT_HISTORY_POINTER_KEY, {}).get("logical_sha256") if isinstance(state, dict) and isinstance(state.get(CHECKPOINT_HISTORY_POINTER_KEY), dict) else None,
            "last_verified_branch": snapshot_branch,
            "last_verified_head": snapshot_head,
            "live_git_branch": live_branch,
            "live_git_head": live_head,
            "git_snapshot_mode": snapshot_mode,
            "workspace_snapshot_matches": workspace_snapshot_matches,
            "portable_baseline_matches": portable_baseline_matches,
            "portable_index_matches": portable_index_matches,
            "last_verified_status_entries": sorted(expected_status),
            "live_git_status_entries": sorted(live_status),
            "new_dirty_entries": sorted(comparable_live_status - comparable_expected_status),
            "removed_dirty_entries": sorted(comparable_expected_status - comparable_live_status),
            "git_snapshot_matches": git_matches,
            "repo_content_matches": repo_content_matches,
            "repo_file_hashes": content_inventory.get("repo_file_hashes", {}),
            "unhashed_large_files": content_inventory.get("unhashed_large_files", []),
            "unreadable_files": content_inventory.get("unreadable_files", []),
            "artifact_dirs_requiring_manifest": content_inventory.get("artifact_dirs_requiring_manifest", []),
            "excluded_directories": content_inventory.get("excluded_directories", []),
            "excluded_symlink_files": content_inventory.get("excluded_symlink_files", 0),
            "roadmap_source": roadmap_source,
        },
    }


def _format_human(report: dict[str, object]) -> str:
    summary = report["summary"]
    status = "PASS" if report["ok"] else "FAIL"
    lines = [f"Agent context preflight: {status}"]
    lines.append(f"Governance: {summary['current_gate']} ({summary['gate_status']}); approved: {', '.join(summary['approved_gates']) or 'none'}")
    milestone_status = summary["next_milestone_status"]
    if milestone_status == "pending_user_approval":
        milestone_phrase = "not started (pending user approval)"
    elif milestone_status == "ready_to_start":
        milestone_phrase = "ready to start (authorized; not started)"
    else:
        milestone_phrase = str(milestone_status)
    lines.append(f"Next engineering milestone: {summary['next_milestone']} — {milestone_phrase}")
    if summary["active_task_id"]:
        lines.append(f"Active task: {summary['active_task_id']} — {summary['active_task_title']}")
        if summary["active_task_next_action"]:
            lines.append("Active task next action: " + summary["active_task_next_action"])
    if summary["next_task_id"]:
        lines.append(f"Next task: {summary['next_task_id']} ({summary['next_task_status']}) — {summary['next_task_title']}")
        if summary["next_task_next_action"] and summary["next_task_id"] != summary["active_task_id"]:
            lines.append("Next task action: " + summary["next_task_next_action"])
        if summary["next_task_dependencies"]:
            lines.append("Next task dependencies: " + ", ".join(summary["next_task_dependencies"]))
        lines.append("Next task acceptance criteria: " + (", ".join(summary["next_task_acceptance_criteria_ids"]) or "none"))
    counts = summary["task_counts"]
    lines.append("Tasks: " + ", ".join(f"{key}={counts.get(key, 0)}" for key in ("done", "in_progress", "pending", "blocked", "cancelled")))
    task_ids = summary["task_ids_by_status"]
    for status, label in (("done", "Completed"), ("in_progress", "In progress"), ("pending", "Pending"), ("blocked", "Blocked")):
        lines.append(f"{label} task IDs: " + (", ".join(task_ids.get(status, [])) if task_ids.get(status) else "none"))
    lines.append("Active blockers: " + (", ".join(summary["active_blocker_ids"]) if summary["active_blocker_ids"] else "none recorded"))
    lines.append("Open confirmations:")
    if summary["open_approvals"]:
        lines.extend(f"  {item['id']}: {item['title']}" for item in summary["open_approvals"])
    else:
        lines.append("  none found")
    lines.append("Relevant decisions: " + (", ".join(summary["decision_refs"]) if summary["decision_refs"] else "none recorded"))
    lines.append(f"Acceptance criteria recognized: {len(summary['acceptance_criteria_ids'])}")
    lines.append(f"Last verified Git: {summary['last_verified_branch']} @ {summary['last_verified_head']}")
    lines.append(f"Live Git: {summary['live_git_branch']} @ {summary['live_git_head']}")
    roadmap = summary["roadmap_source"]
    lines.append(f"Roadmap source: {'exact match' if roadmap['matches'] else 'MISMATCH'}; {roadmap['roman_sections']} sections; SHA-256 {roadmap['sha256']}")
    snapshot_mode = summary["git_snapshot_mode"]
    if snapshot_mode == "portable_commit_transition":
        lines.append("Git recovery: expected commit/checkout transition; portable tracked-file manifest matches.")
    elif snapshot_mode == "legacy_portable_commit_transition":
        lines.append("Git recovery: legacy checkpoint safely matched the clean tracked-file checkout.")
    elif snapshot_mode == "workspace_portable_match":
        lines.append("Git recovery: workspace and portable tracked-file snapshots match.")
    elif snapshot_mode == "portable_baseline_with_local_changes":
        lines.append("Git recovery: portable HEAD matches, but local tracked or state changes remain.")
    elif snapshot_mode == "unexplained_git_transition":
        lines.append("Git recovery: unexplained branch/HEAD transition; inspect portable baseline warnings.")
    elif snapshot_mode == "unverified_legacy_git_transition":
        lines.append("Git recovery: legacy checkpoint cannot verify this commit transition; refresh the portable checkpoint.")
    else:
        lines.append("Git recovery: workspace-specific checkpoint snapshot.")
    lines.append("Workspace Git status: " + ("matches checkpoint" if summary["workspace_snapshot_matches"] else "differs from checkpoint"))
    lines.append("Portable tracked baseline: " + ("matches" if summary["portable_baseline_matches"] else "not yet committed or differs"))
    lines.append("Portable Git index: " + ("matches checkpoint" if summary["portable_index_matches"] else "differs from checkpoint"))
    lines.append("Hashed ordinary-file snapshot: " + ("matches" if summary["repo_content_matches"] else "differs"))
    lines.append(f"Content hashes: {len(summary['repo_file_hashes'])} ordinary files verified by SHA-256.")
    lines.append("Not content-verified by this hash map: PROJECT_STATE self-reference, chat history/credential-like paths, temp files, symlinks, and the excluded directories listed below.")
    if summary["excluded_directories"]:
        lines.append("Excluded directories: " + ", ".join(summary["excluded_directories"]))
    if summary["unhashed_large_files"]:
        lines.append("Large files requiring independent checksums: " + ", ".join(summary["unhashed_large_files"]))
    if summary["unreadable_files"]:
        lines.append("Unreadable files requiring inspection: " + ", ".join(summary["unreadable_files"]))
    if summary["artifact_dirs_requiring_manifest"]:
        lines.append("Artifact directories requiring independent manifests: " + ", ".join(summary["artifact_dirs_requiring_manifest"]))
    if summary["excluded_symlink_files"]:
        lines.append(f"Excluded symlink files: {summary['excluded_symlink_files']}")
    lines.append(f"Last verified dirty paths ({len(summary['last_verified_status_entries'])}): " + ("; ".join(summary["last_verified_status_entries"]) if summary["last_verified_status_entries"] else "none"))
    if summary["new_dirty_entries"]:
        lines.append("New/changed dirty paths since checkpoint: " + "; ".join(summary["new_dirty_entries"]))
    if summary["removed_dirty_entries"]:
        lines.append("Dirty paths no longer present since checkpoint: " + "; ".join(summary["removed_dirty_entries"]))
    lines.append(f"Next user action: {summary['next_user_action']}")
    for item in report["warnings"]:
        lines.append(f"WARNING {item['code']} [{item['path']}]: {item['message']}")
    for item in report["errors"]:
        lines.append(f"ERROR {item['code']} [{item['path']}]: {item['message']}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1], help="Repository root (default: this script's repository).")
    parser.add_argument("--json", action="store_true", help="Emit the recovery report as JSON.")
    args = parser.parse_args(argv)
    report = build_report(args.repo)
    print(json.dumps(report, indent=2) if args.json else _format_human(report))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
