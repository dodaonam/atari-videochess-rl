#!/usr/bin/env python3
"""Read-only verification of an owner-local M6/M7 artifact manifest."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from videochess_rl.m6.ledger import sha256_file, verify_artifact_manifest


SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def verify_root(root_value: str | Path, expected_sha256: str | None = None) -> dict[str, object]:
    supplied = Path(root_value).expanduser()
    if supplied.is_symlink():
        raise ValueError("artifact root must not be a symbolic link")
    root = supplied.resolve(strict=True)
    if not root.is_dir():
        raise ValueError("artifact root must be a directory")
    manifest_path = root / "artifact-manifest.json"
    if manifest_path.is_symlink() or not manifest_path.is_file():
        raise ValueError("artifact-manifest.json is missing or unsafe")
    manifest_sha256 = sha256_file(manifest_path)
    if expected_sha256 is not None and manifest_sha256 != expected_sha256:
        raise ValueError("artifact manifest SHA-256 differs from the expected identity")
    manifest = verify_artifact_manifest(root)
    return {
        "status": "verified",
        "root_label": root.name,
        "manifest_sha256": manifest_sha256,
        "file_count": len(manifest["files"]),
        "total_bytes": manifest["total_bytes"],
        "read_only": True,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True, help="owner-local artifact root")
    parser.add_argument("--expected-manifest-sha256", help="optional frozen root-manifest SHA-256")
    args = parser.parse_args(argv)
    expected = args.expected_manifest_sha256
    if expected is not None and not SHA256_RE.fullmatch(expected):
        parser.error("--expected-manifest-sha256 must be 64 lowercase hexadecimal characters")
    try:
        result = verify_root(args.root, expected)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"artifact verification failed: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, sort_keys=True, ensure_ascii=False, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
