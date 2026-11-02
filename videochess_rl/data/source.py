"""Bounded source acquisition and fail-closed ZIP validation."""

from __future__ import annotations

import hashlib
import json
import os
import random
import re
import stat
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
import zlib
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any

from .contracts import canonical_json, require_sha256

CHUNK_SIZE = 1024 * 1024


class SourceError(ValueError):
    """Source input violates its manifest or safety budget."""


@dataclass(frozen=True)
class ArchiveMember:
    name: str
    compressed_bytes: int
    uncompressed_bytes: int
    crc32: str
    compression: str


def sha256_file(path: Path, *, max_bytes: int | None = None) -> tuple[str, int]:
    digest = hashlib.sha256()
    total = 0
    with path.open("rb") as stream:
        while True:
            chunk = stream.read(CHUNK_SIZE)
            if not chunk:
                break
            total += len(chunk)
            if max_bytes is not None and total > max_bytes:
                raise SourceError(f"file exceeds configured byte cap ({max_bytes})")
            digest.update(chunk)
    return digest.hexdigest(), total


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _check_member_path(name: str) -> None:
    if not name or "\\" in name or name.startswith(("/", "\\")):
        raise SourceError(f"unsafe ZIP member path: {name!r}")
    path = PurePosixPath(name)
    if path.is_absolute() or any(part in ("..", "") for part in path.parts):
        raise SourceError(f"unsafe ZIP member path: {name!r}")
    if path.parts and ":" in path.parts[0]:
        raise SourceError(f"drive-prefixed ZIP member path: {name!r}")


def inspect_zip(
    archive: Path, *, max_archive_bytes: int, max_member_bytes: int,
    max_total_uncompressed_bytes: int, max_members: int = 16,
    max_compression_ratio: int = 200, expected_member: str | None = None,
    expected_sha256: str | None = None, expected_bytes: int | None = None,
) -> dict[str, Any]:
    archive_sha, archive_bytes = sha256_file(archive, max_bytes=max_archive_bytes)
    if expected_sha256 is not None and archive_sha != require_sha256(expected_sha256, "archive_sha256"):
        raise SourceError("archive SHA-256 does not match the approved source manifest")
    if expected_bytes is not None and archive_bytes != expected_bytes:
        raise SourceError("archive byte count does not match the approved source manifest")
    if archive_bytes == 0 or not zipfile.is_zipfile(archive):
        raise SourceError("source is empty or is not a ZIP archive")
    try:
        with zipfile.ZipFile(archive, "r") as bundle:
            infos = bundle.infolist()
            if len(infos) > max_members:
                raise SourceError(f"ZIP has {len(infos)} entries, above cap {max_members}")
            names = [info.filename for info in infos]
            if len(names) != len(set(names)):
                raise SourceError("ZIP contains duplicate member names")
            for info in infos:
                _check_member_path(info.filename)
                mode = info.external_attr >> 16
                if stat.S_ISLNK(mode):
                    raise SourceError(f"ZIP symlink is not allowed: {info.filename}")
                if info.flag_bits & 0x1:
                    raise SourceError(f"encrypted ZIP member is not allowed: {info.filename}")
            data_infos = [info for info in infos if not info.is_dir()]
            pgn_infos = [info for info in data_infos if info.filename.lower().endswith(".pgn")]
            if len(pgn_infos) != 1 or len(data_infos) != 1:
                raise SourceError("archive must contain exactly one non-directory PGN member")
            info = pgn_infos[0]
            if expected_member is not None and info.filename != expected_member:
                raise SourceError("PGN member name does not match the approved source manifest")
            if info.file_size > max_member_bytes:
                raise SourceError(f"PGN member declares {info.file_size} bytes, above cap {max_member_bytes}")
            total_uncompressed = sum(item.file_size for item in data_infos)
            if total_uncompressed > max_total_uncompressed_bytes:
                raise SourceError("declared uncompressed archive size exceeds configured cap")
            ratio = info.file_size / max(info.compress_size, 1)
            if ratio > max_compression_ratio:
                raise SourceError(f"PGN compression ratio {ratio:.2f} exceeds review cap {max_compression_ratio}")
            member = ArchiveMember(
                info.filename, info.compress_size, info.file_size,
                f"{info.CRC:08x}", str(info.compress_type),
            )
            return {
                "archive_sha256": archive_sha,
                "archive_bytes": archive_bytes,
                "member": asdict(member),
                "declared_total_uncompressed_bytes": total_uncompressed,
                "compression_ratio": ratio,
                "zip_entry_count": len(infos),
                "archive_path": archive.name,
            }
    except zipfile.BadZipFile as exc:
        raise SourceError("ZIP central directory or CRC metadata is invalid") from exc


def read_member_chunks(
    archive: Path, member_name: str, *, max_decompressed_bytes: int,
    chunk_size: int = CHUNK_SIZE,
):
    """Yield bounded raw PGN bytes; reaching EOF forces ZIP CRC validation."""
    if chunk_size < 1 or max_decompressed_bytes < 1:
        raise ValueError("byte limits must be positive")
    total = 0
    digest = hashlib.sha256()
    try:
        with zipfile.ZipFile(archive, "r") as bundle:
            matches = [info for info in bundle.infolist() if info.filename == member_name]
            if len(matches) != 1 or matches[0].is_dir():
                raise SourceError("approved PGN member is absent or ambiguous")
            with bundle.open(matches[0], "r") as stream:
                while True:
                    request_size = min(chunk_size, max_decompressed_bytes - total + 1)
                    chunk = stream.read(request_size)
                    if not chunk:
                        break
                    total += len(chunk)
                    if total > max_decompressed_bytes:
                        raise SourceError("PGN member exceeded streaming decompressed-byte cap")
                    digest.update(chunk)
                    yield chunk
    except (zipfile.BadZipFile, RuntimeError, EOFError, NotImplementedError, zlib.error) as exc:
        raise SourceError(f"ZIP member failed CRC/decompression validation: {exc}") from exc
    # Callers can obtain the final digest by consuming the generator's companion
    # helper below; this function deliberately streams bytes only.


def hash_member(archive: Path, member_name: str, *, max_decompressed_bytes: int) -> tuple[str, int]:
    digest = hashlib.sha256()
    total = 0
    for chunk in read_member_chunks(
        archive, member_name, max_decompressed_bytes=max_decompressed_bytes,
    ):
        digest.update(chunk)
        total += len(chunk)
    return digest.hexdigest(), total


def download_archive(
    url: str, destination: Path, *, max_bytes: int, timeout_seconds: int = 30,
    retries: int = 2,
) -> dict[str, Any]:
    """Download a source with bounded retries; never resumes partial bytes."""
    if destination.exists():
        raise SourceError(f"refusing to overwrite existing source file: {destination}")
    if not url.startswith("https://"):
        raise SourceError("source URL must use HTTPS")
    if max_bytes < 1 or retries < 0 or retries > 3:
        raise ValueError("invalid download cap or retry count")
    destination.parent.mkdir(parents=True, exist_ok=True)
    observed_etag: str | None = None
    observed_modified: str | None = None
    observed_length: str | None = None
    last_error: Exception | None = None
    for attempt in range(retries + 1):
        temp_path: Path | None = None
        response_started = False
        attempt_bytes = 0
        try:
            request = urllib.request.Request(
                url, headers={"User-Agent": "atari-videochess-rl-m3/1.0"},
            )
            with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
                status = getattr(response, "status", 200)
                if status < 200 or status >= 300:
                    raise SourceError(f"unexpected HTTP status {status}")
                headers = {key.lower(): value for key, value in response.headers.items()}
                final_url = response.geturl()
                initial_host = urllib.parse.urlparse(url).hostname
                final_parts = urllib.parse.urlparse(final_url)
                if final_parts.scheme != "https" or final_parts.hostname != initial_host:
                    raise SourceError("download redirect left the approved HTTPS source host")
                response_started = True
                length = headers.get("content-length")
                if length:
                    try:
                        content_length = int(length)
                    except ValueError as exc:
                        raise SourceError("HTTP Content-Length is malformed") from exc
                    if content_length < 0:
                        raise SourceError("HTTP Content-Length is negative")
                    if content_length > max_bytes:
                        raise SourceError("HTTP Content-Length exceeds configured archive cap")
                etag = headers.get("etag")
                modified = headers.get("last-modified")
                if attempt and ((observed_etag and etag != observed_etag)
                                or (observed_modified and modified != observed_modified)
                                or (observed_length and length != observed_length)):
                    raise SourceError("source HTTP identity changed between download attempts")
                observed_etag = observed_etag or etag
                observed_modified = observed_modified or modified
                observed_length = observed_length or length
                fd, raw_path = tempfile.mkstemp(
                    prefix=f".{destination.name}.", suffix=".partial", dir=destination.parent,
                )
                temp_path = Path(raw_path)
                digest = hashlib.sha256()
                total = 0
                with os.fdopen(fd, "wb") as output:
                    while True:
                        chunk = response.read(CHUNK_SIZE)
                        if not chunk:
                            break
                        total += len(chunk)
                        attempt_bytes = total
                        if total > max_bytes:
                            raise SourceError("download exceeded configured archive cap")
                        digest.update(chunk)
                        output.write(chunk)
                    output.flush()
                    os.fsync(output.fileno())
                if length and total != content_length:
                    raise SourceError("download byte count differs from HTTP Content-Length")
                os.replace(temp_path, destination)
                return {
                    "url": url, "final_url": final_url,
                    "retrieved_at_utc": _utc_now(), "http_status": status,
                    "http_headers": {
                        key: headers[key] for key in ("content-length", "content-type", "etag", "last-modified", "accept-ranges") if key in headers
                    },
                    "attempt": attempt + 1, "archive_bytes": total,
                    "archive_sha256": digest.hexdigest(), "archive_path": destination.name,
                }
        except SourceError:
            if temp_path is not None:
                temp_path.unlink(missing_ok=True)
            raise
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            last_error = exc
            if temp_path is not None:
                temp_path.unlink(missing_ok=True)
            if attempt >= retries:
                break
            if response_started and attempt_bytes and not (observed_etag or observed_modified):
                raise SourceError("download interrupted after bytes arrived without a stable HTTP validator; retry halted") from exc
            time.sleep(min(2 ** attempt + random.random() / 10, 4))
    raise SourceError(f"bounded download failed after {retries + 1} attempts: {last_error}")


def write_json_atomic(path: Path, value: dict[str, Any]) -> None:
    if path.exists():
        raise SourceError(f"refusing to overwrite manifest: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(f".{path.name}.{os.getpid()}.partial")
    with temp.open("xb") as stream:
        stream.write(json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False).encode("utf-8") + b"\n")
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temp, path)


def validate_source_manifest(value: dict[str, Any]) -> None:
    """Validate the authorized source identity and its measured archive/member."""
    from .contracts import source_identity

    expected_source_id = source_identity(
        "lichess-elite", "https://database.nikonoel.fr/", "lichess-elite-2022-05",
    )
    if value.get("schema") != "videochess-source-manifest/1.0" or value.get("schema_version") != "videochess-source-manifest/1.0":
        raise SourceError("unsupported source manifest schema")
    if value.get("source_id") != expected_source_id:
        raise SourceError("source manifest identity does not match the authorized collection")
    if value.get("publisher") != "Lichess Elite Database (third-party curated package)":
        raise SourceError("source manifest publisher identity is unexpected")
    if not isinstance(value.get("original_data_provenance"), str) or not value["original_data_provenance"].startswith("Lichess games"):
        raise SourceError("source manifest upstream provenance is missing")
    if value.get("canonical_source_url") != "https://database.nikonoel.fr/":
        raise SourceError("source manifest publisher URL is unexpected")
    if value.get("archive_url") != "https://database.nikonoel.fr/lichess_elite_2022-05.zip":
        raise SourceError("source manifest archive URL does not match the authorized source")
    if value.get("source_decision_id") != "M3-SOURCE-ELITE-2022-05-LOCAL-20261020":
        raise SourceError("source manifest is missing its recorded source decision")
    if value.get("authorization_id") != "M3-001-owner-20261020":
        raise SourceError("source manifest is missing its direct owner authorization")
    if value.get("license_status") != "third_party_license_unstated_internal_use_owner_authorized_no_redistribution":
        raise SourceError("source manifest contains an unapproved rights status")
    if value.get("rights_boundary") != "bounded internal academic research; local retention; no upload or redistribution of archive or bulk derived game records":
        raise SourceError("source manifest rights boundary is missing or changed")
    if value.get("license_name") is not None or value.get("license_url") is not None:
        raise SourceError("source manifest must not invent a third-party package license")
    if value.get("license_unknown_reason") != "publisher page does not state a license for this filtered third-party package":
        raise SourceError("source manifest must state the third-party package license uncertainty")
    if value.get("approval_id") != value.get("authorization_id"):
        raise SourceError("source manifest approval_id differs from the owner authorization")
    if value.get("published_archive_checksum") is not None:
        raise SourceError("source manifest must not invent a publisher checksum")
    for field in ("archive_sha256", "member_sha256"):
        require_sha256(value.get(field), field)
    for field in ("archive_bytes", "member_bytes"):
        if not isinstance(value.get(field), int) or value[field] <= 0:
            raise SourceError(f"source manifest {field} must be a positive integer")
    member = value.get("member")
    if not isinstance(member, dict) or not isinstance(member.get("name"), str):
        raise SourceError("source manifest has no selected archive member")
    _check_member_path(member["name"])
    if member["name"] != value.get("member_name") or not member["name"].lower().endswith(".pgn"):
        raise SourceError("source manifest PGN member name is inconsistent")
    if value.get("archive_member") != member or value.get("member_crc") != member.get("crc32"):
        raise SourceError("archive member metadata aliases disagree")
    if not isinstance(member.get("compressed_bytes"), int) or member["compressed_bytes"] < 0:
        raise SourceError("source manifest compressed member size is malformed")
    if value["member_bytes"] != member.get("uncompressed_bytes"):
        raise SourceError("source manifest member byte counts are inconsistent")
    if not re.fullmatch(r"[0-9a-f]{8}", str(member.get("crc32", ""))):
        raise SourceError("source manifest member CRC is malformed")
    if value.get("crc_verified") is not True:
        raise SourceError("source manifest does not attest that the full member passed CRC")
    retrieval = value.get("retrieval")
    if not isinstance(retrieval, dict) or retrieval.get("http_status") != 200:
        raise SourceError("source manifest has no successful retrieval metadata")
    if retrieval.get("archive_bytes") != value["archive_bytes"] or retrieval.get("archive_sha256") != value["archive_sha256"]:
        raise SourceError("source retrieval fields disagree with archive identity")
    if value.get("retrieved_at_utc") != retrieval.get("retrieved_at_utc"):
        raise SourceError("source retrieval timestamp aliases disagree")
    if value.get("archive_filename") != retrieval.get("archive_path"):
        raise SourceError("archive filename differs from retrieval metadata")
    if retrieval.get("url") != value.get("archive_url"):
        raise SourceError("source retrieval URL differs from the approved archive URL")
    final_parts = urllib.parse.urlparse(str(retrieval.get("final_url", "")))
    if final_parts.scheme != "https" or final_parts.hostname != "database.nikonoel.fr":
        raise SourceError("source retrieval final URL left the approved HTTPS host")
    try:
        datetime.fromisoformat(str(retrieval.get("retrieved_at_utc", "")).replace("Z", "+00:00"))
    except ValueError as exc:
        raise SourceError("source retrieval timestamp is malformed") from exc
    terms = value.get("source_terms_evidence")
    if not isinstance(terms, dict) or not isinstance(terms.get("path"), str):
        raise SourceError("source terms evidence reference is missing")
    require_sha256(terms.get("sha256", ""), "source_terms_evidence.sha256")
    require_sha256(terms.get("publisher_page_sha256", ""), "publisher_page_sha256")
    require_sha256(terms.get("upstream_terms_page_sha256", ""), "upstream_terms_page_sha256")
    if value.get("source_page_sha256") != terms["publisher_page_sha256"]:
        raise SourceError("source page hash alias differs from terms evidence")
    if value.get("rights_evidence_path") != terms.get("path") or value.get("rights_evidence_sha256") != terms.get("sha256"):
        raise SourceError("rights evidence reference aliases disagree")
    approval = value.get("approval_evidence")
    if not isinstance(approval, dict):
        raise SourceError("source approval evidence references are missing")
    for path_key, hash_key in (
        ("source_decision_path", "source_decision_sha256"),
        ("authorization_path", "authorization_sha256"),
    ):
        if not isinstance(approval.get(path_key), str) or not approval[path_key]:
            raise SourceError(f"source approval evidence path is missing: {path_key}")
        require_sha256(approval.get(hash_key, ""), hash_key)
    if value.get("python_chess_version") is None or value.get("python_version") is None or value.get("code_revision") is None:
        raise SourceError("source parser/runtime/code provenance is incomplete")
    if value.get("filter_config_sha256") is not None or not value.get("filter_config_unknown_reason"):
        raise SourceError("unpublished source filter configuration must remain explicitly unknown")
    limits = value.get("retrieval_limits")
    if not isinstance(limits, dict):
        raise SourceError("hard retrieval limits are missing from source manifest")
    if value["archive_bytes"] > limits.get("max_archive_bytes", 0):
        raise SourceError("retrieved archive exceeds its recorded byte cap")
    if value["member_bytes"] > min(
        limits.get("max_member_bytes", 0), limits.get("max_total_decompressed_bytes", 0),
    ):
        raise SourceError("PGN member exceeds its recorded decompression cap")
    if value.get("compression_ratio", 0) > limits.get("max_compression_ratio", 0):
        raise SourceError("PGN member exceeds its recorded compression-ratio cap")
