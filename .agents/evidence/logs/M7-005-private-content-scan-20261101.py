"""Scan M7-005 candidate additions and retained logs for payloads/secrets/paths."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path


BASE = "origin/initial-idea"
TEXT_SUFFIXES = {".md", ".json", ".yaml", ".yml", ".txt", ".log", ".py"}
FORBIDDEN_SUFFIXES = {".pt", ".pth", ".bin", ".rom", ".pgn", ".npz", ".npy", ".zip", ".tar", ".tar.gz"}
CHECKS = {
    "concrete_machine_path": re.compile(r"/(?:home|root|Users|mnt)/[A-Za-z0-9._-]+/(?:Projects|Documents|Desktop|Downloads|tmp)/[^\s`]+"),
    "github_credential": re.compile(r"gh[pousr]_[A-Za-z0-9_]{20,}"),
    "aws_access_key": re.compile(r"AKIA[0-9A-Z]{16}"),
    "private_key_header": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
}


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], text=True)


added = git("diff", "--unified=0", BASE)
added_lines = "\n".join(
    line[1:] for line in added.splitlines()
    if line.startswith("+") and not line.startswith("+++")
)
untracked = git("ls-files", "--others", "--exclude-standard").splitlines()
text_files: list[tuple[str, str]] = []
for name in untracked:
    path = Path(name)
    if path.suffix.lower() not in TEXT_SUFFIXES:
        continue
    raw = path.read_bytes()
    if b"\0" not in raw:
        text_files.append((name, raw.decode("utf-8", "replace")))
for path in sorted(Path(".agents/evidence/logs").glob("M7-005-*.log")):
    text_files.append((path.as_posix(), path.read_text(encoding="utf-8", errors="replace")))

matches: list[tuple[str, str]] = []
for label, content in [("added_tracked_lines", added_lines), *text_files]:
    for check_name, pattern in CHECKS.items():
        if pattern.search(content):
            matches.append((label, check_name))

changed_paths = set(git("diff", "--name-only", BASE).splitlines()) | set(untracked)
restricted_payloads = sorted(
    name for name in changed_paths
    if any(name.lower().endswith(suffix) for suffix in FORBIDDEN_SUFFIXES)
)

print(f"source_revision={git('rev-parse', 'HEAD').strip()}")
print(f"added_tracked_lines={len(added_lines.splitlines())}")
print(f"untracked_text_and_task_logs={len(text_files)}")
print(f"concrete_path_or_credential_matches={matches}")
print(f"restricted_payload_suffixes={restricted_payloads}")
raise SystemExit(1 if matches or restricted_payloads else 0)
