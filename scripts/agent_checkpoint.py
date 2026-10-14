#!/usr/bin/env python3
"""Atomically refresh the repository Git snapshot and the handoff pointer."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import subprocess
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path

# A dry-run must not create an import cache as an incidental side effect.
sys.dont_write_bytecode = True

from agent_preflight import (
    HANDOFF_REL,
    STATE_REL,
    PARTIAL_STATE_PATTERNS,
    WORKSPACE_CONFIG_KEY,
    WORKSPACE_ID,
    _canonical_sha256,
    _git_workspace_id,
    _git_index_manifest,
    _live_git_snapshot,
    _portable_state_sha256,
    _repo_file_hash_inventory,
    _sha_text,
    build_report,
)

MARKER = re.compile(r"(?m)^<!-- checkpoint-id: ([^\s]+) -->$")
TEMP_AGE_SECONDS = 600


def _atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            prefix=f".{path.name}.tmp-",
            dir=path.parent,
            delete=False,
        ) as handle:
            temporary = handle.name
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        temporary = None
        try:
            directory_fd = os.open(path.parent, os.O_RDONLY)
        except OSError:
            directory_fd = None
        if directory_fd is not None:
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
    finally:
        if temporary is not None:
            try:
                os.unlink(temporary)
            except FileNotFoundError:
                pass


def _partial_candidates(root: Path) -> tuple[list[Path], list[str]]:
    cutoff = datetime.now(timezone.utc).timestamp() - TEMP_AGE_SECONDS
    stale: list[Path] = []
    recent: list[str] = []
    state_dir = root / ".agents/state"
    for pattern in PARTIAL_STATE_PATTERNS:
        for path in sorted(state_dir.glob(pattern)):
            try:
                mtime = path.stat().st_mtime
                if mtime <= cutoff and path.is_file():
                    stale.append(path)
                else:
                    recent.append(path.relative_to(root).as_posix())
            except FileNotFoundError:
                continue
            except OSError:
                recent.append(path.relative_to(root).as_posix())
    return stale, recent


def _remove_stale_partials(root: Path) -> tuple[int, list[str]]:
    stale, recent = _partial_candidates(root)
    for path in stale:
        try:
            path.unlink()
        except FileNotFoundError:
            continue
    return len(stale), recent


def _checkpoint_id(head: str) -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    return f"cp-{head[:8]}-{stamp}"


def _get_or_create_workspace_id(root: Path, dry_run: bool) -> tuple[str | None, bool]:
    current = _git_workspace_id(root)
    if current and WORKSPACE_ID.fullmatch(current):
        return current, False
    if dry_run:
        return None, True
    created = str(uuid.uuid4())
    result = subprocess.run(
        ["git", "-C", str(root), "config", "--local", "--replace-all", WORKSPACE_CONFIG_KEY, created],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or "could not create local Git workspace identity")
    return created, True


def _render_state(state: dict[str, object]) -> str:
    return json.dumps(state, indent=2, ensure_ascii=False) + "\n"


def checkpoint(root: Path, recover_partials: bool, dry_run: bool) -> tuple[int, str]:
    root = root.resolve()
    report = build_report(root)
    if report["errors"]:
        return 1, "Preflight errors prevent checkpoint; fix them before writing state.\n" + "\n".join(
            f"ERROR {item['code']} [{item['path']}]: {item['message']}" for item in report["errors"]
        )

    removed = 0
    recent: list[str] = []
    stale_partials: list[Path] = []
    if recover_partials:
        stale_partials, recent = _partial_candidates(root)
        if dry_run:
            removed = len(stale_partials)
        else:
            removed, recent = _remove_stale_partials(root)

    state_path = root / STATE_REL
    handoff_path = root / HANDOFF_REL
    try:
        state = json.loads(state_path.read_text(encoding="utf-8"))
        handoff = handoff_path.read_text(encoding="utf-8")
        snapshot = _live_git_snapshot(root)
        workspace_id = _git_workspace_id(root)
        workspace_id_would_be_created = not bool(workspace_id and WORKSPACE_ID.fullmatch(workspace_id))
    except (OSError, UnicodeError, json.JSONDecodeError, RuntimeError) as exc:
        return 1, f"Could not checkpoint canonical state: {exc}"

    marker_matches = list(MARKER.finditer(handoff))
    if len(marker_matches) != 1:
        return 1, f"Expected exactly one checkpoint-id marker in {HANDOFF_REL}."

    history = state.get("checkpoint_history", [])
    if not isinstance(history, list):
        return 1, "checkpoint_history is malformed; inspect canonical state before checkpointing."
    previous = state.get("last_checkpoint")
    if isinstance(previous, dict) and isinstance(previous.get("id"), str):
        if not any(isinstance(item, dict) and item.get("id") == previous["id"] for item in history):
            history.append({
                "id": previous["id"],
                "created_at_utc": previous.get("created_at_utc", ""),
                "workspace_id": previous.get("workspace_id"),
                "workspace_git": previous.get("git", {}),
                "portable_git": previous.get("portable_git"),
            })
    state["checkpoint_history"] = history

    checkpoint_id = _checkpoint_id(str(snapshot["head"]))
    repo_hashes, inventory = _repo_file_hash_inventory(root)
    try:
        tracked_manifest = _git_index_manifest(root)
    except RuntimeError as exc:
        return 1, f"Could not capture the portable Git index: {exc}"
    if workspace_id_would_be_created and not dry_run:
        try:
            workspace_id, _ = _get_or_create_workspace_id(root, dry_run=False)
        except RuntimeError as exc:
            return 1, str(exc)
    refreshed_handoff = MARKER.sub(f"<!-- checkpoint-id: {checkpoint_id} -->", handoff, count=1)
    portable = {
        "format_version": 1,
        "tracked_manifest": tracked_manifest,
        "manifest_sha256": _canonical_sha256(tracked_manifest),
        "state_sha256": _portable_state_sha256(state),
        "handoff_sha256": _sha_text(refreshed_handoff),
    }
    state["last_checkpoint"] = {
        "id": checkpoint_id,
        "created_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        **({"workspace_id": workspace_id} if workspace_id else {}),
        "git": {
            "scope": "workspace",
            **snapshot,
            "repo_file_hashes": repo_hashes,
            **inventory,
        },
        "portable_git": portable,
    }

    if dry_run:
        lines = [f"Would write checkpoint {checkpoint_id}.", f"Git snapshot contains {len(snapshot['status_entries'])} dirty path entries."]
        if workspace_id_would_be_created:
            lines.append("Would create a local Git workspace identity; dry-run leaves Git config unchanged.")
        if recover_partials:
            lines.append(f"Would remove {removed} stale partial file(s).")
        if recent:
            lines.append("Recent partial files retained: " + ", ".join(recent))
        return 0, "\n".join(lines)

    try:
        _atomic_write(state_path, _render_state(state))
        _atomic_write(handoff_path, refreshed_handoff)
        # Capture the final status and file inventory after both writes. PROJECT_STATE
        # is excluded from content hashes, so writing this final snapshot does not
        # change the Git path set or create a self-referential checksum.
        final_snapshot = _live_git_snapshot(root)
        repo_hashes, inventory = _repo_file_hash_inventory(root)
        state["last_checkpoint"]["git"] = {
            "scope": "workspace",
            **final_snapshot,
            "repo_file_hashes": repo_hashes,
            **inventory,
        }
        _atomic_write(state_path, _render_state(state))
    except (OSError, TypeError, KeyError, RuntimeError) as exc:
        return 1, f"Atomic checkpoint write failed; rerun preflight and inspect agent temp files: {exc}"

    final_report = build_report(root)
    lines = [f"Checkpoint written: {checkpoint_id}.", f"Git snapshot captured {len(snapshot['status_entries'])} dirty path entries."]
    if recover_partials:
        lines.append(f"Removed {removed} stale agent partial file(s).")
    if recent:
        lines.append("Recent partial files retained: " + ", ".join(recent))
    lines.append("Post-checkpoint preflight: " + ("PASS" if final_report["ok"] else "FAIL"))
    for item in final_report["warnings"]:
        lines.append(f"WARNING {item['code']} [{item['path']}]: {item['message']}")
    for item in final_report["errors"]:
        lines.append(f"ERROR {item['code']} [{item['path']}]: {item['message']}")
    return (0 if final_report["ok"] else 1), "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1], help="Repository root (default: this script's repository).")
    parser.add_argument("--recover-partials", action="store_true", help="Remove only agent-owned temp files older than 10 minutes before refreshing state.")
    parser.add_argument("--dry-run", action="store_true", help="Describe the checkpoint without writing files.")
    args = parser.parse_args(argv)
    code, message = checkpoint(args.repo, args.recover_partials, args.dry_run)
    print(message)
    return code


if __name__ == "__main__":
    sys.exit(main())
