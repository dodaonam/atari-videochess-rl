#!/usr/bin/env python3
"""Versioned, lossless storage for checkpoint history.

Legacy state keeps complete records inline. Migrated state keeps an empty
inline list and a small pointer to a portable, separately verified archive.
"""

from __future__ import annotations

import copy
import gzip
import hashlib
import json
import os
import re
import tempfile
import zlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ARCHIVE_REL = ".agents/state/checkpoint-history"
MANIFEST_REL = f"{ARCHIVE_REL}/manifest.json"
POINTER_KEY = "checkpoint_history_archive"
FORMAT = "atari-videochess-checkpoint-history"
SCHEMA_VERSION = 1
RECORD_SCHEMA_VERSION = 1
SEGMENT_RECORD_LIMIT = 16
MAX_CHECKPOINT_STATE_BYTES = 4 * 1024 * 1024
CHECKPOINT_STATE_RESERVE_BYTES = 64 * 1024
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$")
SEGMENT_RE = re.compile(r"^segments/segment-(\d{6})\.jsonl\.gz$")


class CheckpointHistoryError(ValueError):
    """Raised when checkpoint history is malformed or fails integrity checks."""


@dataclass(frozen=True)
class ArchiveAppendPlan:
    pointer: dict[str, object]
    writes: dict[str, bytes]
    previous_bytes: dict[str, bytes | None]
    appended: bool


@dataclass
class HistoryInspection:
    records: list[dict[str, object]]
    errors: list[tuple[str, str]]
    manifest: dict[str, object] | None = None
    manifest_bytes: bytes | None = None
    pending_pointer: dict[str, object] | None = None
    orphan_record: dict[str, object] | None = None
    orphan_path: str | None = None


def canonical_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def logical_history_sha256(records: list[dict[str, object]]) -> str:
    return sha256_bytes(canonical_bytes(records))


def _record_from_checkpoint(checkpoint: object) -> dict[str, object]:
    if not isinstance(checkpoint, dict):
        raise CheckpointHistoryError("last_checkpoint must be an object before it can enter history")
    git_snapshot = checkpoint.get("git")
    if not isinstance(git_snapshot, dict):
        raise CheckpointHistoryError("last_checkpoint.git must be an object before it can enter history")
    record: dict[str, object] = {
        "id": checkpoint.get("id"),
        "created_at_utc": checkpoint.get("created_at_utc"),
        "workspace_git": git_snapshot,
        "portable_git": checkpoint.get("portable_git"),
    }
    if "workspace_id" in checkpoint:
        record["workspace_id"] = checkpoint.get("workspace_id")
    _validate_record(record)
    return record


def _validate_record(record: object) -> None:
    if not isinstance(record, dict):
        raise CheckpointHistoryError("history record must be an object")
    if not isinstance(record.get("id"), str) or not record["id"].strip():
        raise CheckpointHistoryError("history record id must be a non-empty string")
    if not isinstance(record.get("created_at_utc"), str) or not record["created_at_utc"].strip():
        raise CheckpointHistoryError(f"history record {record.get('id')} has no timestamp")
    if not isinstance(record.get("workspace_git", record.get("git")), dict):
        raise CheckpointHistoryError(f"history record {record.get('id')} has no workspace Git snapshot")
    workspace_id = record.get("workspace_id")
    if workspace_id is not None and (not isinstance(workspace_id, str) or not UUID_RE.fullmatch(workspace_id)):
        raise CheckpointHistoryError(f"history record {record.get('id')} has an invalid workspace id")
    portable = record.get("portable_git")
    if portable is not None and not isinstance(portable, dict):
        raise CheckpointHistoryError(f"history record {record.get('id')} has an invalid portable snapshot")


def validate_records(records: object) -> list[dict[str, object]]:
    if not isinstance(records, list):
        raise CheckpointHistoryError("checkpoint_history must be a list in legacy state")
    result: list[dict[str, object]] = []
    seen: set[str] = set()
    for item in records:
        _validate_record(item)
        record_id = str(item["id"])
        if record_id in seen:
            raise CheckpointHistoryError(f"duplicate checkpoint history id: {record_id}")
        seen.add(record_id)
        result.append(item)
    return result


def _legacy_logical_history(state: dict[str, object]) -> list[dict[str, object]]:
    history = validate_records(state.get("checkpoint_history", []))
    current = _record_from_checkpoint(state.get("last_checkpoint"))
    matches = [record for record in history if record["id"] == current["id"]]
    if matches:
        if matches[0] != current:
            raise CheckpointHistoryError("current last_checkpoint ID conflicts with an existing history record")
        return history
    return [*history, current]


def _segment_bytes(records: list[dict[str, object]]) -> tuple[bytes, bytes]:
    plain = b"".join(canonical_bytes(item) + b"\n" for item in records)
    return gzip.compress(plain, compresslevel=9, mtime=0), plain


def _segment_entry(path: str, packed: bytes, plain: bytes, records: list[dict[str, object]]) -> dict[str, object]:
    return {
        "path": path,
        "sha256": sha256_bytes(packed),
        "uncompressed_sha256": sha256_bytes(plain),
        "uncompressed_bytes": len(plain),
        "record_count": len(records),
        "first_id": records[0]["id"] if records else None,
        "last_id": records[-1]["id"] if records else None,
    }


def _pointer(manifest_bytes: bytes, manifest: dict[str, object]) -> dict[str, object]:
    source = manifest["source_backup"]
    assert isinstance(source, dict)
    return {
        "format_version": SCHEMA_VERSION,
        "manifest_path": MANIFEST_REL,
        "manifest_sha256": sha256_bytes(manifest_bytes),
        "record_count": manifest["record_count"],
        "logical_sha256": manifest["logical_sha256"],
        "source_state_sha256": source["raw_sha256"],
        "source_backup_path": f"{ARCHIVE_REL}/{source['path']}",
        "source_backup_sha256": source["gzip_sha256"],
    }


def _migration_payload(source_state_bytes: bytes, state: dict[str, object]) -> tuple[dict[str, bytes], dict[str, object], bytes]:
    source_history = validate_records(state.get("checkpoint_history", []))
    history = _legacy_logical_history(state)
    current_record = _record_from_checkpoint(state.get("last_checkpoint"))
    state_sha = sha256_bytes(source_state_bytes)
    backup_path = f"{ARCHIVE_REL}/backups/source-state-{state_sha[:16]}.json.gz"
    backup_bytes = gzip.compress(source_state_bytes, compresslevel=9, mtime=0)
    source_backup = {
        "path": f"backups/source-state-{state_sha[:16]}.json.gz",
        "raw_sha256": state_sha,
        "raw_bytes": len(source_state_bytes),
        "gzip_sha256": sha256_bytes(backup_bytes),
    }
    writes: dict[str, bytes] = {backup_path: backup_bytes}
    segments: list[dict[str, object]] = []
    for offset in range(0, len(history), SEGMENT_RECORD_LIMIT):
        chunk = history[offset:offset + SEGMENT_RECORD_LIMIT]
        sequence = len(segments) + 1
        rel = f"{ARCHIVE_REL}/segments/segment-{sequence:06d}.jsonl.gz"
        packed, plain = _segment_bytes(chunk)
        writes[rel] = packed
        segments.append(_segment_entry(f"segments/segment-{sequence:06d}.jsonl.gz", packed, plain, chunk))
    manifest: dict[str, object] = {
        "format": FORMAT,
        "schema_version": SCHEMA_VERSION,
        "record_schema_version": RECORD_SCHEMA_VERSION,
        "segment_record_limit": SEGMENT_RECORD_LIMIT,
        "record_count": len(history),
        "logical_sha256": logical_history_sha256(history),
        "source_history_count": len(source_history),
        "source_checkpoint_id": current_record["id"],
        "source_backup": source_backup,
        "segments": segments,
    }
    manifest_bytes = _render_json(manifest)
    writes[MANIFEST_REL] = manifest_bytes
    return writes, manifest, manifest_bytes


def _safe_archive_rel(value: object) -> bool:
    if not isinstance(value, str) or not value or "\\" in value:
        return False
    path = Path(value)
    return not path.is_absolute() and ".." not in path.parts and len(path.parts) >= 2


def _parse_manifest_bytes(raw: bytes) -> dict[str, object]:
    try:
        manifest = json.loads(raw.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise CheckpointHistoryError(f"archive manifest is not valid JSON: {exc}") from exc
    if not isinstance(manifest, dict):
        raise CheckpointHistoryError("archive manifest top-level value must be an object")
    required = {
        "format", "schema_version", "record_schema_version", "segment_record_limit",
        "record_count", "logical_sha256", "source_history_count", "source_checkpoint_id", "source_backup", "segments",
    }
    if set(manifest) != required:
        raise CheckpointHistoryError("archive manifest keys do not match schema version 1")
    if manifest.get("format") != FORMAT or type(manifest.get("schema_version")) is not int or manifest.get("schema_version") != SCHEMA_VERSION:
        raise CheckpointHistoryError("unsupported checkpoint history archive format or schema version")
    if type(manifest.get("record_schema_version")) is not int or manifest.get("record_schema_version") != RECORD_SCHEMA_VERSION:
        raise CheckpointHistoryError("unsupported checkpoint history record schema version")
    if type(manifest.get("segment_record_limit")) is not int or manifest.get("segment_record_limit") != SEGMENT_RECORD_LIMIT:
        raise CheckpointHistoryError("archive segment record limit is unsupported")
    if type(manifest.get("record_count")) is not int or manifest["record_count"] < 0:
        raise CheckpointHistoryError("archive record_count must be a non-negative integer")
    if type(manifest.get("source_history_count")) is not int or manifest["source_history_count"] < 0:
        raise CheckpointHistoryError("archive source_history_count must be a non-negative integer")
    if not isinstance(manifest.get("source_checkpoint_id"), str) or not manifest["source_checkpoint_id"].strip():
        raise CheckpointHistoryError("archive source_checkpoint_id must be a non-empty string")
    if not isinstance(manifest.get("logical_sha256"), str) or not SHA256_RE.fullmatch(manifest["logical_sha256"]):
        raise CheckpointHistoryError("archive logical_sha256 is invalid")
    if not isinstance(manifest.get("segments"), list) or not isinstance(manifest.get("source_backup"), dict):
        raise CheckpointHistoryError("archive segments and source_backup must be structured values")
    return manifest


def _load_manifest_records(root: Path, manifest: dict[str, object]) -> list[dict[str, object]]:
    backup = manifest["source_backup"]
    assert isinstance(backup, dict)
    if set(backup) != {"path", "raw_sha256", "raw_bytes", "gzip_sha256"}:
        raise CheckpointHistoryError("source backup fields do not match schema version 1")
    backup_rel = backup.get("path")
    if not _safe_archive_rel(backup_rel) or not str(backup_rel).startswith("backups/"):
        raise CheckpointHistoryError("source backup path is unsafe")
    if not isinstance(backup.get("raw_sha256"), str) or not SHA256_RE.fullmatch(str(backup["raw_sha256"])):
        raise CheckpointHistoryError("source backup raw hash is invalid")
    if not isinstance(backup.get("gzip_sha256"), str) or not SHA256_RE.fullmatch(str(backup["gzip_sha256"])):
        raise CheckpointHistoryError("source backup compressed hash is invalid")
    if type(backup.get("raw_bytes")) is not int or backup["raw_bytes"] < 0:
        raise CheckpointHistoryError("source backup byte count is invalid")
    backup_path = root / ARCHIVE_REL / str(backup_rel)
    try:
        packed_backup = backup_path.read_bytes()
    except OSError as exc:
        raise CheckpointHistoryError(f"source state backup is missing or corrupt: {exc}") from exc
    if sha256_bytes(packed_backup) != backup["gzip_sha256"]:
        raise CheckpointHistoryError("source state backup compressed SHA-256 mismatch")
    try:
        source_state_bytes = gzip.decompress(packed_backup)
    except (OSError, EOFError, zlib.error) as exc:
        raise CheckpointHistoryError(f"source state backup is missing or corrupt: {exc}") from exc
    if len(source_state_bytes) != backup["raw_bytes"] or sha256_bytes(source_state_bytes) != backup["raw_sha256"]:
        raise CheckpointHistoryError("source state backup raw size or SHA-256 mismatch")
    try:
        source_state = json.loads(source_state_bytes.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise CheckpointHistoryError(f"source state backup is not recoverable JSON: {exc}") from exc
    if not isinstance(source_state, dict) or not isinstance(source_state.get("checkpoint_history", []), list):
        raise CheckpointHistoryError("source backup does not contain a legacy checkpoint_history list")
    source_history = validate_records(source_state.get("checkpoint_history", []))
    if len(source_history) != manifest["source_history_count"]:
        raise CheckpointHistoryError("source backup history count differs from the manifest")
    try:
        source_checkpoint = _record_from_checkpoint(source_state.get("last_checkpoint"))
    except CheckpointHistoryError as exc:
        raise CheckpointHistoryError(f"source backup last checkpoint is invalid: {exc}") from exc
    if manifest.get("source_checkpoint_id") != source_checkpoint.get("id"):
        raise CheckpointHistoryError("source backup checkpoint ID differs from the manifest")

    rows: list[dict[str, object]] = []
    expected_sequence = 1
    for entry in manifest["segments"]:
        if not isinstance(entry, dict) or set(entry) != {
            "path", "sha256", "uncompressed_sha256", "uncompressed_bytes", "record_count", "first_id", "last_id",
        }:
            raise CheckpointHistoryError("segment metadata does not match schema version 1")
        rel = entry.get("path")
        match = SEGMENT_RE.fullmatch(str(rel))
        if not _safe_archive_rel(rel) or not match or int(match.group(1)) != expected_sequence:
            raise CheckpointHistoryError("archive segments must have safe, contiguous sequence paths")
        expected_sequence += 1
        if not isinstance(entry.get("sha256"), str) or not SHA256_RE.fullmatch(str(entry["sha256"])):
            raise CheckpointHistoryError("segment SHA-256 is invalid")
        if not isinstance(entry.get("uncompressed_sha256"), str) or not SHA256_RE.fullmatch(str(entry["uncompressed_sha256"])):
            raise CheckpointHistoryError("segment uncompressed SHA-256 is invalid")
        if type(entry.get("record_count")) is not int or not 1 <= entry["record_count"] <= SEGMENT_RECORD_LIMIT:
            raise CheckpointHistoryError("segment record_count is outside the versioned bound")
        if type(entry.get("uncompressed_bytes")) is not int or entry["uncompressed_bytes"] < 0:
            raise CheckpointHistoryError("segment uncompressed_bytes must be a non-negative integer")
        segment_path = root / ARCHIVE_REL / str(rel)
        try:
            packed = segment_path.read_bytes()
        except OSError as exc:
            raise CheckpointHistoryError(f"archive segment {rel} is missing or corrupt: {exc}") from exc
        if sha256_bytes(packed) != entry["sha256"]:
            raise CheckpointHistoryError(f"archive segment {rel} compressed SHA-256 mismatch")
        try:
            plain = gzip.decompress(packed)
        except (OSError, EOFError, zlib.error) as exc:
            raise CheckpointHistoryError(f"archive segment {rel} is missing or corrupt: {exc}") from exc
        if len(plain) != entry["uncompressed_bytes"] or sha256_bytes(plain) != entry["uncompressed_sha256"]:
            raise CheckpointHistoryError(f"archive segment {rel} uncompressed size or SHA-256 mismatch")
        segment_rows: list[dict[str, object]] = []
        for line_number, line in enumerate(plain.splitlines(), start=1):
            try:
                record = json.loads(line.decode("utf-8"))
            except (UnicodeError, json.JSONDecodeError) as exc:
                raise CheckpointHistoryError(f"archive segment {rel} line {line_number} is invalid JSON: {exc}") from exc
            _validate_record(record)
            segment_rows.append(record)
        if len(segment_rows) != entry["record_count"]:
            raise CheckpointHistoryError(f"archive segment {rel} record count mismatch")
        if segment_rows and (segment_rows[0]["id"] != entry["first_id"] or segment_rows[-1]["id"] != entry["last_id"]):
            raise CheckpointHistoryError(f"archive segment {rel} boundary IDs mismatch")
        rows.extend(segment_rows)
    rows = validate_records(rows)
    if len(rows) != manifest["record_count"]:
        raise CheckpointHistoryError("archive aggregate record count mismatch")
    if logical_history_sha256(rows) != manifest["logical_sha256"]:
        raise CheckpointHistoryError("archive logical history SHA-256 mismatch")
    if rows[:len(source_history)] != source_history:
        raise CheckpointHistoryError("archived source prefix differs from the byte-verified original state")
    included_checkpoint = [item for item in rows if item.get("id") == source_checkpoint.get("id")]
    if len(included_checkpoint) != 1 or included_checkpoint[0] != source_checkpoint:
        raise CheckpointHistoryError("archived source checkpoint differs from the byte-verified original state")
    return rows


def _manifest_pointer_matches(pointer: dict[str, object], manifest: dict[str, object], raw: bytes) -> bool:
    expected = _pointer(raw, manifest)
    return all(pointer.get(key) == value for key, value in expected.items())


def _record_from_state(state: dict[str, object]) -> dict[str, object]:
    return _record_from_checkpoint(state.get("last_checkpoint"))


def _expected_archive_files(manifest: dict[str, object]) -> set[str]:
    result = {str(manifest["source_backup"]["path"])}
    result.update(str(item["path"]) for item in manifest["segments"])
    return result


def _find_orphan_segments(root: Path, manifest: dict[str, object]) -> list[tuple[str, bytes]]:
    expected = _expected_archive_files(manifest)
    directory = root / ARCHIVE_REL / "segments"
    if not directory.exists():
        return []
    result: list[tuple[str, bytes]] = []
    for path in sorted(directory.iterdir()):
        rel = f"segments/{path.name}"
        if rel not in expected:
            result.append((rel, path.read_bytes()))
    return result


def _unreferenced_archive_files(root: Path, manifest: dict[str, object]) -> list[str]:
    expected = _expected_archive_files(manifest) | {"manifest.json"}
    base = root / ARCHIVE_REL
    if not base.exists():
        return []
    return sorted(
        path.relative_to(base).as_posix()
        for path in base.rglob("*")
        if path.is_file() and path.relative_to(base).as_posix() not in expected
    )


def _manifest_with_append(
    manifest: dict[str, object], records: list[dict[str, object]], record: dict[str, object], packed: bytes, plain: bytes,
) -> tuple[dict[str, object], bytes, str]:
    sequence = len(manifest["segments"]) + 1
    rel = f"segments/segment-{sequence:06d}.jsonl.gz"
    appended_records = [*records, record]
    updated = dict(manifest)
    updated["record_count"] = len(appended_records)
    updated["logical_sha256"] = logical_history_sha256(appended_records)
    updated["segments"] = [*manifest["segments"], _segment_entry(rel, packed, plain, [record])]
    raw = _render_json(updated)
    return updated, raw, f"{ARCHIVE_REL}/{rel}"


def inspect_history_storage(root: Path, state: dict[str, object]) -> HistoryInspection:
    """Verify inline or archived history and report safe pending append states."""
    root = root.resolve()
    pointer = state.get(POINTER_KEY)
    archive_dir = root / ARCHIVE_REL
    if pointer is None:
        try:
            history = validate_records(state.get("checkpoint_history", []))
        except CheckpointHistoryError as exc:
            return HistoryInspection([], [("CHECKPOINT_HISTORY_SCHEMA", str(exc))])
        if archive_dir.exists() and any(archive_dir.rglob("*")):
            return HistoryInspection(history, [("CHECKPOINT_HISTORY_UNREFERENCED", "archive files exist but canonical state has no archive pointer; rerun migration or inspect the partial archive")])
        return HistoryInspection(history, [])
    if not isinstance(pointer, dict) or set(pointer) != {
        "format_version", "manifest_path", "manifest_sha256", "record_count", "logical_sha256",
        "source_state_sha256", "source_backup_path", "source_backup_sha256",
    }:
        return HistoryInspection([], [("CHECKPOINT_HISTORY_POINTER", "checkpoint_history_archive pointer fields do not match schema version 1")])
    if state.get("checkpoint_history") != []:
        return HistoryInspection([], [("CHECKPOINT_HISTORY_POINTER", "archived state must keep checkpoint_history empty")])
    if type(pointer.get("format_version")) is not int or pointer.get("format_version") != SCHEMA_VERSION or pointer.get("manifest_path") != MANIFEST_REL:
        return HistoryInspection([], [("CHECKPOINT_HISTORY_POINTER", "unsupported archive pointer version or path")])
    if not isinstance(pointer.get("manifest_sha256"), str) or not SHA256_RE.fullmatch(str(pointer["manifest_sha256"])):
        return HistoryInspection([], [("CHECKPOINT_HISTORY_POINTER", "archive manifest hash is invalid")])
    manifest_path = root / MANIFEST_REL
    try:
        raw_manifest = manifest_path.read_bytes()
    except OSError as exc:
        return HistoryInspection([], [("CHECKPOINT_HISTORY_MANIFEST_MISSING", f"cannot read archive manifest: {exc}")])
    try:
        manifest = _parse_manifest_bytes(raw_manifest)
        records = _load_manifest_records(root, manifest)
    except CheckpointHistoryError as exc:
        return HistoryInspection([], [("CHECKPOINT_HISTORY_CORRUPT", str(exc))])

    source = manifest["source_backup"]
    assert isinstance(source, dict)
    pointer_source_matches = (
        pointer.get("source_state_sha256") == source.get("raw_sha256")
        and pointer.get("source_backup_path") == f"{ARCHIVE_REL}/{source.get('path')}"
        and pointer.get("source_backup_sha256") == source.get("gzip_sha256")
    )
    if not pointer_source_matches:
        return HistoryInspection(records, [("CHECKPOINT_HISTORY_POINTER", "source backup identity differs between state pointer and archive manifest")], manifest, raw_manifest)

    if _manifest_pointer_matches(pointer, manifest, raw_manifest):
        try:
            unreferenced = _unreferenced_archive_files(root, manifest)
        except OSError as exc:
            return HistoryInspection(records, [("CHECKPOINT_HISTORY_CORRUPT", f"cannot inspect archive segment directory: {exc}")], manifest, raw_manifest)
        if not unreferenced:
            return HistoryInspection(records, [], manifest, raw_manifest)
        orphans = _find_orphan_segments(root, manifest)
        if len(orphans) == 1:
            orphan_rel, packed = orphans[0]
            expected_sequence = len(manifest["segments"]) + 1
            if orphan_rel == f"segments/segment-{expected_sequence:06d}.jsonl.gz":
                try:
                    plain = gzip.decompress(packed)
                    rows = [json.loads(line.decode("utf-8")) for line in plain.splitlines()]
                    if len(rows) == 1:
                        _validate_record(rows[0])
                        expected_record = _record_from_state(state)
                        expected_packed, _ = _segment_bytes([rows[0]])
                        if rows[0] == expected_record and packed == expected_packed:
                            return HistoryInspection(records, [("CHECKPOINT_HISTORY_PENDING_APPEND", "one verified archive segment matches the current last_checkpoint and can be rolled forward")], manifest, raw_manifest, orphan_record=rows[0], orphan_path=orphan_rel)
                except (OSError, EOFError, zlib.error, UnicodeError, json.JSONDecodeError, CheckpointHistoryError):
                    pass
        return HistoryInspection(records, [("CHECKPOINT_HISTORY_UNREFERENCED", "unreferenced checkpoint-history archive file exists; preserve it and inspect migration/recovery state")], manifest, raw_manifest)

    # A crash after the manifest replacement and before the state pointer
    # replacement leaves exactly one recoverable record: the current checkpoint.
    try:
        current_record = _record_from_state(state)
        prefix = records[:-1]
        is_pending = (
            len(records) == int(pointer.get("record_count", -2)) + 1
            and logical_history_sha256(prefix) == pointer.get("logical_sha256")
            and records[-1] == current_record
            and pointer_source_matches
        )
    except (ValueError, TypeError, CheckpointHistoryError):
        is_pending = False
    if is_pending:
        try:
            extras = _unreferenced_archive_files(root, manifest)
        except OSError as exc:
            return HistoryInspection(records, [("CHECKPOINT_HISTORY_CORRUPT", f"cannot inspect archive files during pending append recovery: {exc}")], manifest, raw_manifest)
        if extras:
            return HistoryInspection(records, [("CHECKPOINT_HISTORY_UNREFERENCED", "unreferenced archive files prevent pending append recovery: " + ", ".join(extras))], manifest, raw_manifest)
        return HistoryInspection(records, [("CHECKPOINT_HISTORY_PENDING_APPEND", "archive manifest is one verified record ahead of the state pointer and can be rolled forward")], manifest, raw_manifest, pending_pointer=_pointer(raw_manifest, manifest))
    return HistoryInspection(records, [("CHECKPOINT_HISTORY_POINTER_MISMATCH", "canonical archive pointer does not match the verified manifest")], manifest, raw_manifest)


def prepare_archive_append(root: Path, state: dict[str, object], record: dict[str, object]) -> ArchiveAppendPlan:
    """Prepare a single immutable segment append without mutating files."""
    root = root.resolve()
    _validate_record(record)
    inspection = inspect_history_storage(root, state)
    if inspection.errors:
        code, message = inspection.errors[0]
        raise CheckpointHistoryError(f"{code}: {message}")
    pointer = state.get(POINTER_KEY)
    if not isinstance(pointer, dict) or inspection.manifest is None or inspection.manifest_bytes is None:
        raise CheckpointHistoryError("archive append requires a verified migrated archive")
    for existing in inspection.records:
        if existing["id"] == record["id"]:
            if existing == record:
                return ArchiveAppendPlan(pointer, {}, {}, False)
            raise CheckpointHistoryError(f"checkpoint id already exists with different data: {record['id']}")
    packed, plain = _segment_bytes([record])
    manifest, manifest_bytes, segment_rel = _manifest_with_append(inspection.manifest, inspection.records, record, packed, plain)
    writes = {segment_rel: packed, MANIFEST_REL: manifest_bytes}
    previous: dict[str, bytes | None] = {}
    for rel in writes:
        path = root / rel
        if rel == MANIFEST_REL:
            if not path.is_file() or path.read_bytes() != inspection.manifest_bytes:
                raise CheckpointHistoryError("archive manifest changed after verification; refusing concurrent append")
            previous[rel] = inspection.manifest_bytes
        else:
            if path.exists():
                raise CheckpointHistoryError(f"append target already exists outside the verified manifest: {rel}")
            previous[rel] = None
    return ArchiveAppendPlan(_pointer(manifest_bytes, manifest), writes, previous, True)


def atomic_write_bytes(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: str | None = None
    try:
        with tempfile.NamedTemporaryFile(mode="wb", prefix=f".{path.name}.tmp-", dir=path.parent, delete=False) as handle:
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


def apply_archive_append(root: Path, plan: ArchiveAppendPlan) -> None:
    for rel, content in plan.writes.items():
        atomic_write_bytes(root / rel, content)


def rollback_archive_append(root: Path, previous_bytes: dict[str, bytes | None]) -> list[str]:
    errors: list[str] = []
    for rel, content in reversed(list(previous_bytes.items())):
        path = root / rel
        try:
            if content is None:
                path.unlink(missing_ok=True)
            else:
                atomic_write_bytes(path, content)
        except OSError as exc:
            errors.append(f"{rel}: {exc}")
    return errors


def _portable_state_sha256(state: dict[str, object]) -> str:
    stable = {key: value for key, value in state.items() if key != "last_checkpoint"}
    payload = json.dumps(stable, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")
    return sha256_bytes(payload)


def _update_state_pointer(state: dict[str, object], pointer: dict[str, object]) -> None:
    state["checkpoint_history"] = []
    state[POINTER_KEY] = pointer
    last = state.get("last_checkpoint")
    if isinstance(last, dict):
        portable = last.get("portable_git")
        if isinstance(portable, dict):
            portable["state_sha256"] = _portable_state_sha256(state)


def _write_manifest_files(root: Path, writes: dict[str, bytes], *, resume: bool) -> list[str]:
    created: list[str] = []
    archive_root = root / ARCHIVE_REL
    expected_paths = {str(Path(rel).relative_to(ARCHIVE_REL).as_posix()) for rel in writes}
    if archive_root.exists():
        existing_paths = {path.relative_to(archive_root).as_posix() for path in archive_root.rglob("*") if path.is_file()}
        extras = sorted(existing_paths - expected_paths)
        if extras:
            raise CheckpointHistoryError("existing archive directory has unrecognized files; refusing migration resume: " + ", ".join(extras))
    try:
        for rel, content in writes.items():
            path = root / rel
            if path.exists():
                if not resume or path.read_bytes() != content:
                    raise CheckpointHistoryError(f"existing migration output differs; refusing to overwrite: {rel}")
                continue
            atomic_write_bytes(path, content)
            created.append(rel)
        return created
    except Exception:
        for rel in reversed(created):
            try:
                (root / rel).unlink(missing_ok=True)
            except OSError:
                pass
        raise


def migration_preview(state_bytes: bytes, state: dict[str, object]) -> dict[str, object]:
    writes, manifest, manifest_bytes = _migration_payload(state_bytes, state)
    pointer = _pointer(manifest_bytes, manifest)
    candidate = copy.deepcopy(state)
    candidate["checkpoint_history"] = []
    candidate[POINTER_KEY] = pointer
    last = candidate.get("last_checkpoint")
    if isinstance(last, dict) and isinstance(last.get("portable_git"), dict):
        last["portable_git"]["state_sha256"] = _portable_state_sha256(candidate)
    state_size = len(_render_json(candidate))
    if state_size + CHECKPOINT_STATE_RESERVE_BYTES > MAX_CHECKPOINT_STATE_BYTES:
        raise CheckpointHistoryError(f"migrated state remains above the guarded size: {state_size} bytes")
    return {
        "source_history_count": manifest["source_history_count"],
        "history_count": manifest["record_count"],
        "first_id": manifest["segments"][0]["first_id"] if manifest["segments"] else None,
        "last_id": manifest["segments"][-1]["last_id"] if manifest["segments"] else None,
        "source_state_bytes": len(state_bytes),
        "source_state_sha256": pointer["source_state_sha256"],
        "migrated_state_bytes": state_size,
        "archive_compressed_bytes": sum(len(value) for rel, value in writes.items() if rel != MANIFEST_REL),
        "archive_file_count": len(writes),
        "manifest_sha256": pointer["manifest_sha256"],
        "logical_history_sha256": pointer["logical_sha256"],
    }


def migrate_legacy_history(root: Path) -> dict[str, object]:
    """Create and verify a lossless archive, then atomically switch state pointer."""
    root = root.resolve()
    state_path = root / ".agents/state/PROJECT_STATE.yaml"
    original = state_path.read_bytes()
    try:
        state = json.loads(original.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise CheckpointHistoryError(f"canonical state is not valid JSON-compatible YAML: {exc}") from exc
    if not isinstance(state, dict):
        raise CheckpointHistoryError("canonical state top level must be an object")
    if POINTER_KEY in state:
        inspection = inspect_history_storage(root, state)
        if inspection.errors:
            raise CheckpointHistoryError("already-migrated archive is invalid: " + "; ".join(f"{c}: {m}" for c, m in inspection.errors))
        # If a process stopped after the atomic pointer switch but before the
        # ordinary checkpoint refresh, finish that finalization on retry.
        portable = state.get("last_checkpoint", {}).get("portable_git", {}) if isinstance(state.get("last_checkpoint"), dict) else {}
        handoff_path = root / ".agents/state/SESSION_HANDOFF.md"
        try:
            handoff = handoff_path.read_text(encoding="utf-8")
        except OSError as exc:
            raise CheckpointHistoryError(f"cannot verify migration handoff finalization: {exc}") from exc
        needs_finalize = (
            not isinstance(portable, dict)
            or portable.get("state_sha256") != _portable_state_sha256(state)
            or portable.get("handoff_sha256") != sha256_bytes(handoff.encode("utf-8"))
            or not re.search(rf"(?m)^<!-- checkpoint-id: {re.escape(str(state.get('last_checkpoint', {}).get('id', '')))} -->$", handoff)
        )
        if needs_finalize:
            from agent_checkpoint import checkpoint as run_checkpoint
            code, message = run_checkpoint(root, False, False)
            if code:
                raise CheckpointHistoryError("archive is valid but migration checkpoint finalization needs recovery: " + message)
            final_state = json.loads(state_path.read_text(encoding="utf-8"))
            final_inspection = inspect_history_storage(root, final_state)
            if final_inspection.errors:
                raise CheckpointHistoryError("migration finalization did not restore valid archive state: " + "; ".join(f"{c}: {m}" for c, m in final_inspection.errors))
            state = final_state
            inspection = final_inspection
            status = "finalized_existing_migration"
        else:
            status = "already_migrated"
        return {"status": status, "history_count": len(inspection.records), "logical_history_sha256": state[POINTER_KEY]["logical_sha256"]}
    history = _legacy_logical_history(state)
    writes, manifest, manifest_bytes = _migration_payload(original, state)
    preview = migration_preview(original, state)
    archive_dir = root / ARCHIVE_REL
    resume = archive_dir.exists()
    created = _write_manifest_files(root, writes, resume=resume)
    try:
        pointer = _pointer(manifest_bytes, manifest)
        # Independently read the generated bytes from disk and compare the
        # decoded records with the pre-migration in-memory inventory.
        parsed = _parse_manifest_bytes((root / MANIFEST_REL).read_bytes())
        reconstructed = _load_manifest_records(root, parsed)
        if reconstructed != history:
            raise CheckpointHistoryError("independent archive reconstruction differs from original history")
        state["checkpoint_history"] = []
        state[POINTER_KEY] = pointer
        candidate_bytes = _render_json(state)
        if len(candidate_bytes) + CHECKPOINT_STATE_RESERVE_BYTES > MAX_CHECKPOINT_STATE_BYTES:
            raise CheckpointHistoryError("migrated canonical state exceeds the configured checkpoint reserve")
        atomic_write_bytes(state_path, candidate_bytes)
        # Preserve the original current checkpoint in the archive, then record
        # a new compact-state checkpoint through the normal checkpoint path.
        from agent_checkpoint import checkpoint as run_checkpoint
        checkpoint_code, checkpoint_message = run_checkpoint(root, False, False)
        if checkpoint_code:
            raise CheckpointHistoryError("archive was written but migration checkpoint finalization failed: " + checkpoint_message)
        final_state_for_verify = json.loads(state_path.read_text(encoding="utf-8"))
        post = inspect_history_storage(root, final_state_for_verify)
        if post.errors or post.records != history:
            raise CheckpointHistoryError("post-migration archive verification failed: " + "; ".join(f"{c}: {m}" for c, m in post.errors))
        final_state = json.loads(state_path.read_text(encoding="utf-8"))
        final_report = __import__("agent_preflight").build_report(root)
        if final_report["errors"]:
            raise CheckpointHistoryError("post-migration preflight failed: " + "; ".join(item["message"] for item in final_report["errors"]))
        return {
            "status": "migrated",
            **preview,
            "reconstructed_history_count": len(post.records),
            "migration_checkpoint_id": final_state.get("last_checkpoint", {}).get("id"),
            "final_state_bytes": state_path.stat().st_size,
        }
    except Exception:
        try:
            current = json.loads(state_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            current = None
        if not isinstance(current, dict) or current.get(POINTER_KEY) != _pointer(manifest_bytes, manifest):
            for rel in reversed(created):
                try:
                    (root / rel).unlink(missing_ok=True)
                except OSError:
                    pass
        raise


def restore_original_state_bytes(root: Path, state: dict[str, object]) -> bytes:
    pointer = state.get(POINTER_KEY)
    if not isinstance(pointer, dict):
        raise CheckpointHistoryError("canonical state has no checkpoint history archive pointer")
    rel = pointer.get("source_backup_path")
    expected_gzip_hash = pointer.get("source_backup_sha256")
    expected_raw_hash = pointer.get("source_state_sha256")
    if not _safe_archive_rel(rel) or not str(rel).startswith(f"{ARCHIVE_REL}/backups/"):
        raise CheckpointHistoryError("source backup path in state pointer is unsafe")
    try:
        packed = (root / str(rel)).read_bytes()
        raw = gzip.decompress(packed)
    except (OSError, EOFError, zlib.error) as exc:
        raise CheckpointHistoryError(f"cannot recover source state backup: {exc}") from exc
    if sha256_bytes(packed) != expected_gzip_hash or sha256_bytes(raw) != expected_raw_hash:
        raise CheckpointHistoryError("source state backup hash mismatch; refusing restoration")
    try:
        recovered = json.loads(raw.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise CheckpointHistoryError(f"source state backup is not valid JSON: {exc}") from exc
    if not isinstance(recovered, dict) or not isinstance(recovered.get("checkpoint_history", []), list):
        raise CheckpointHistoryError("source state backup does not contain recoverable legacy history")
    return raw


def recover_pending_append(root: Path) -> dict[str, object]:
    """Roll forward only a single append proven to match the current checkpoint."""
    root = root.resolve()
    state_path = root / ".agents/state/PROJECT_STATE.yaml"
    raw = state_path.read_bytes()
    state = json.loads(raw.decode("utf-8"))
    if not isinstance(state, dict) or POINTER_KEY not in state:
        raise CheckpointHistoryError("pending append recovery requires migrated canonical state")
    inspection = inspect_history_storage(root, state)
    if len(inspection.errors) != 1 or inspection.errors[0][0] != "CHECKPOINT_HISTORY_PENDING_APPEND":
        raise CheckpointHistoryError("no single verifiable pending history append was found")
    if inspection.pending_pointer is not None:
        pointer = inspection.pending_pointer
    elif inspection.orphan_record is not None and inspection.manifest is not None:
        packed, plain = _segment_bytes([inspection.orphan_record])
        updated, manifest_bytes, segment_rel = _manifest_with_append(
            inspection.manifest, inspection.records, inspection.orphan_record, packed, plain,
        )
        if segment_rel != f"{ARCHIVE_REL}/{inspection.orphan_path}":
            raise CheckpointHistoryError("orphan segment path is not the next archive sequence")
        if (root / segment_rel).read_bytes() != packed:
            raise CheckpointHistoryError("orphan segment bytes do not match the canonical checkpoint record")
        atomic_write_bytes(root / MANIFEST_REL, manifest_bytes)
        pointer = _pointer(manifest_bytes, updated)
    else:
        raise CheckpointHistoryError("pending append is not recoverable from verified archive data")
    state[POINTER_KEY] = pointer
    atomic_write_bytes(state_path, _render_json(state))
    from agent_checkpoint import checkpoint as run_checkpoint
    code, message = run_checkpoint(root, False, False)
    if code:
        raise CheckpointHistoryError("pending archive append was rolled forward, but checkpoint finalization failed: " + message)
    return {"status": "recovered", "record_count": pointer["record_count"], "logical_sha256": pointer["logical_sha256"], "checkpoint_message": message}


def _render_json(value: object) -> bytes:
    return (json.dumps(value, separators=(",", ":"), ensure_ascii=False) + "\n").encode("utf-8")
