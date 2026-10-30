"""Immutable, recoverable source bundles for M5 training attempts.

The run manifest's source digest is useful only if the corresponding bytes can
be recovered. This module stores the exact project Python sources, M5 config,
and dependency lock files in a private ZIP artifact before training starts.
"""

from __future__ import annotations

import hashlib
import json
import os
import stat
import subprocess
import tempfile
import zipfile
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path, PurePosixPath
from typing import Any

SOURCE_BUNDLE_SCHEMA = "videochess-m5-source-bundle/1.0"
_REQUIRED_ROOT_FILES = (
    ".python-version",
    "pyproject.toml",
    "uv.lock",
    "configs/rl/m5-double-dqn-v1.json",
)
_ZIP_TIME = (1980, 1, 1, 0, 0, 0)


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _safe_relative_path(value: str) -> bool:
    path = PurePosixPath(value)
    return (not path.is_absolute() and "\\" not in value and "\x00" not in value and bool(path.parts)
            and all(part not in ("", ".", "..") for part in path.parts))


def _source_paths(root: Path) -> list[Path]:
    package = root / "videochess_rl"
    if package.is_symlink() or not package.is_dir():
        raise ValueError("M5 Python source directory is missing or unsafe")

    paths: list[Path] = []
    for directory, dirnames, filenames in os.walk(package, followlinks=False):
        current = Path(directory)
        for dirname in tuple(dirnames):
            child = current / dirname
            if child.is_symlink():
                raise ValueError(f"symlink in executable source tree: {child.relative_to(root).as_posix()}")
        for filename in filenames:
            child = current / filename
            if child.suffix != ".py":
                continue
            if child.is_symlink() or not child.is_file():
                raise ValueError(f"unsafe executable source file: {child.relative_to(root).as_posix()}")
            paths.append(child)

    if not paths:
        raise ValueError("M5 Python source tree contains no Python files")
    for name in _REQUIRED_ROOT_FILES:
        path = root / name
        if path.is_symlink() or not path.is_file():
            raise ValueError(f"required source/configuration input is missing or unsafe: {name}")
        paths.append(path)
    return sorted(paths, key=lambda path: path.relative_to(root).as_posix())


def _read_source(root: Path, additional_files: tuple[str, ...]) -> dict[str, bytes]:
    files: dict[str, bytes] = {}
    for path in _source_paths(root):
        relative = path.relative_to(root).as_posix()
        if not _safe_relative_path(relative) or relative in files:
            raise ValueError(f"unsafe or duplicate source path: {relative}")
        files[relative] = path.read_bytes()
    for relative in additional_files:
        if not _safe_relative_path(relative):
            raise ValueError(f"unsafe additional runtime input path: {relative}")
        path = root / relative
        if path.is_symlink() or not path.is_file():
            raise ValueError(f"additional runtime input is missing or unsafe: {relative}")
        if any(parent.is_symlink() for parent in (path, *path.parents) if parent != root.parent and parent != root):
            raise ValueError(f"symlink in additional runtime input path: {relative}")
        if relative in files:
            if files[relative] != path.read_bytes():
                raise RuntimeError(f"source input changed during collection: {relative}")
            continue
        files[relative] = path.read_bytes()
    return files


def _package_source_sha256(files: dict[str, bytes]) -> str:
    digest = hashlib.sha256()
    for path in sorted(name for name in files if name.startswith("videochess_rl/") and name.endswith(".py")):
        digest.update(path.encode("utf-8") + b"\0")
        digest.update(files[path])
    return digest.hexdigest()


def _git_identity(root: Path) -> dict[str, Any]:
    revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
    status = subprocess.check_output(
        ["git", "status", "--porcelain=v1", "--untracked-files=all", "--",
         "videochess_rl", "configs/rl/m5-double-dqn-v1.json", "pyproject.toml", "uv.lock", ".python-version",
         ".agents/state/PROJECT_STATE.yaml", ".agents/tasks/BACKLOG.yaml"],
        cwd=root,
        text=True,
    )
    entries = status.splitlines()
    return {
        "source_revision": revision,
        "source_dirty": bool(entries),
        "source_status_entries": entries,
        "source_status_sha256": _sha256(status.encode("utf-8")),
    }


def _zip_info(name: str) -> zipfile.ZipInfo:
    info = zipfile.ZipInfo(name, date_time=_ZIP_TIME)
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = (stat.S_IFREG | 0o644) << 16
    return info


def _archive_bytes(files: dict[str, bytes], manifest: dict[str, Any]) -> bytes:
    output = BytesIO()
    with zipfile.ZipFile(output, mode="w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        archive.writestr(_zip_info("manifest.json"), json.dumps(
            manifest, sort_keys=True, indent=2, allow_nan=False
        ).encode("utf-8") + b"\n")
        for relative in sorted(files):
            archive.writestr(_zip_info(f"source/{relative}"), files[relative])
    return output.getvalue()


def capture_source_snapshot(root: str | Path, destination: str | Path, *,
                            additional_files: tuple[str, ...] | list[str] = ()) -> dict[str, Any]:
    """Atomically preserve the current runnable source/config/lock bytes.

    The caller records the returned content-addressed archive identity in each
    run and initialization manifest. Source is read twice to reject a capture
    racing with an in-place edit. Existing archives are never overwritten.
    """
    project = Path(root).resolve()
    output_dir = Path(destination)
    if not output_dir.is_absolute():
        output_dir = project / output_dir
    output_dir = output_dir.resolve()
    try:
        output_dir.relative_to(project)
    except ValueError as exc:
        raise ValueError("source bundle destination must remain inside the project artifact root") from exc

    extra = tuple(additional_files)
    if len(set(extra)) != len(extra):
        raise ValueError("duplicate additional runtime input path")
    files = _read_source(project, extra)
    git = _git_identity(project)
    captured_at = datetime.now(timezone.utc).isoformat()
    entries = [{"path": name, "size_bytes": len(data), "sha256": _sha256(data)}
               for name, data in sorted(files.items())]
    config_sha = _sha256(files["configs/rl/m5-double-dqn-v1.json"])
    manifest = {
        "schema": SOURCE_BUNDLE_SCHEMA,
        **git,
        "source_sha256": _package_source_sha256(files),
        "configuration_sha256": config_sha,
        "dependency_lock_sha256": _sha256(files["uv.lock"]),
        "additional_runtime_inputs": list(extra),
        "files": entries,
    }
    archive_data = _archive_bytes(files, manifest)
    if files != _read_source(project, extra):
        raise RuntimeError("M5 source tree changed while its immutable snapshot was being captured")
    archive_sha = _sha256(archive_data)
    output_dir.mkdir(parents=True, exist_ok=True)
    archive_path = output_dir / f"source-snapshot-{archive_sha}.zip"
    if archive_path.is_symlink():
        raise ValueError("refusing to use a symlink as an immutable source bundle")
    if archive_path.exists():
        if not archive_path.is_file() or _sha256(archive_path.read_bytes()) != archive_sha:
            raise ValueError("existing content-addressed source bundle is corrupt")
    else:
        fd, temp_name = tempfile.mkstemp(prefix=".source-snapshot.", suffix=".tmp", dir=output_dir)
        temp_path = Path(temp_name)
        try:
            with os.fdopen(fd, "wb") as stream:
                stream.write(archive_data)
                stream.flush()
                os.fsync(stream.fileno())
            try:
                os.link(temp_path, archive_path)
            except FileExistsError:
                if not archive_path.is_file() or _sha256(archive_path.read_bytes()) != archive_sha:
                    raise ValueError("concurrent source bundle publication produced a different artifact")
            directory_fd = os.open(output_dir, os.O_DIRECTORY)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
        finally:
            try:
                temp_path.unlink()
            except FileNotFoundError:
                pass

    return {
        "schema": SOURCE_BUNDLE_SCHEMA,
        "path": archive_path.relative_to(project).as_posix(),
        "captured_at_utc": captured_at,
        "archive_sha256": archive_sha,
        "size_bytes": len(archive_data),
        "source_sha256": manifest["source_sha256"],
        "configuration_sha256": config_sha,
        "dependency_lock_sha256": manifest["dependency_lock_sha256"],
        "source_revision": git["source_revision"],
        "source_dirty": git["source_dirty"],
        "source_status_entries": git["source_status_entries"],
        "source_status_sha256": git["source_status_sha256"],
        "file_count": len(entries),
    }


def verify_source_snapshot(path: str | Path, *, expected_archive_sha256: str | None = None) -> dict[str, Any]:
    """Verify archive integrity, safe member paths, and each source byte hash."""
    archive_path = Path(path)
    if archive_path.is_symlink() or not archive_path.is_file():
        raise ValueError("source snapshot is missing or unsafe")
    archive_data = archive_path.read_bytes()
    archive_sha = _sha256(archive_data)
    if expected_archive_sha256 is not None and archive_sha != expected_archive_sha256:
        raise ValueError("source snapshot archive checksum mismatch")
    try:
        with zipfile.ZipFile(BytesIO(archive_data), mode="r") as archive:
            names = archive.namelist()
            if len(names) != len(set(names)) or "manifest.json" not in names:
                raise ValueError("source snapshot contains duplicate members or no manifest")
            manifest = json.loads(archive.read("manifest.json"))
            if manifest.get("schema") != SOURCE_BUNDLE_SCHEMA:
                raise ValueError("unsupported source snapshot schema")
            expected: dict[str, dict[str, Any]] = {}
            for item in manifest.get("files", []):
                relative = item.get("path")
                if not isinstance(relative, str) or not _safe_relative_path(relative) or relative in expected:
                    raise ValueError("source snapshot manifest contains an unsafe or duplicate path")
                expected[relative] = item
            additional = manifest.get("additional_runtime_inputs", [])
            if (not isinstance(additional, list)
                    or any(not isinstance(name, str) or not _safe_relative_path(name) or name not in expected
                           for name in additional)
                    or len(set(additional)) != len(additional)):
                raise ValueError("source snapshot additional runtime-input inventory is invalid")
            expected_names = {"manifest.json", *(f"source/{name}" for name in expected)}
            if set(names) != expected_names:
                raise ValueError("source snapshot members differ from the embedded inventory")
            files: dict[str, bytes] = {}
            for relative, item in expected.items():
                data = archive.read(f"source/{relative}")
                if len(data) != item.get("size_bytes") or _sha256(data) != item.get("sha256"):
                    raise ValueError(f"source snapshot file hash mismatch: {relative}")
                files[relative] = data
    except (OSError, zipfile.BadZipFile, json.JSONDecodeError) as exc:
        raise ValueError(f"invalid source snapshot archive: {exc}") from exc

    if _package_source_sha256(files) != manifest.get("source_sha256"):
        raise ValueError("source snapshot aggregate source hash mismatch")
    config = files.get("configs/rl/m5-double-dqn-v1.json")
    lock = files.get("uv.lock")
    if config is None or _sha256(config) != manifest.get("configuration_sha256"):
        raise ValueError("source snapshot configuration hash mismatch")
    if lock is None or _sha256(lock) != manifest.get("dependency_lock_sha256"):
        raise ValueError("source snapshot dependency lock hash mismatch")
    return {"archive_sha256": archive_sha, "size_bytes": len(archive_data), **manifest}
