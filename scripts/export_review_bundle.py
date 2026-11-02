#!/usr/bin/env python3
"""Create a review archive from one explicit Git snapshot."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import posixpath
import re
import stat
import subprocess
import sys
import tempfile
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath


REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ".agents/review-bundles"
MAX_FILE_SIZE = 2 * 1024 * 1024
EXCLUSION_POLICIES = (
    {"path": ".git/", "reason": "Git metadata is never exported"},
    {"path": ".venv/ and cache directories", "reason": "local environments and generated caches are never exported"},
    {"path": ".env* and credential paths", "reason": "private configuration and credentials are never exported"},
    {"path": "chat_history.md and conversation records", "reason": "private conversation history is never exported"},
    {"path": "data/, datasets/, artifacts/, runs/, checkpoints/, models/", "reason": "excluded by default; inclusion requires explicit approval"},
    {"path": f"{OUTPUT_DIR}/", "reason": "review archives are excluded to prevent recursive inclusion"},
    {"path": "*.zip", "reason": "previous archives are never exported"},
)
REQUIRED_CONTEXT = (
    "AGENTS.md",
    "README.md",
    "docs/01-foundation/REQUIREMENTS.md",
    "docs/01-foundation/PROJECT_OVERVIEW.md",
    "docs/01-foundation/ROADMAP.md",
    "docs/02-management/EXECUTION_PLAN.md",
    "docs/06-quality/ACCEPTANCE_CRITERIA.md",
    "docs/06-quality/TEST_STRATEGY.md",
    ".agents/state/PROJECT_STATE.yaml",
    ".agents/state/SESSION_HANDOFF.md",
    ".agents/state/BLOCKERS.md",
    ".agents/state/VERIFIED_FINDINGS.md",
    ".agents/tasks/BACKLOG.yaml",
    "docs/02-management/decisions/ADR-0001-governance-crosswalk-and-file-priorities.md",
)
CONFIG_NAMES = {
    ".gitignore",
    ".python-version",
    "pyproject.toml",
    "setup.py",
    "setup.cfg",
    "tox.ini",
    "pytest.ini",
    "mypy.ini",
    "uv.lock",
    "poetry.lock",
    "pdm.lock",
    "Pipfile",
    "Pipfile.lock",
    "requirements.txt",
    "environment.yml",
    "environment.yaml",
    "Dockerfile",
    "compose.yaml",
    "docker-compose.yml",
}
EXCLUDED_DIRS = {
    ".git",
    ".venv",
    "venv",
    "env",
    "__pycache__",
    ".cache",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "node_modules",
    "build",
    "dist",
    "site-packages",
    "review-bundles",
    ".aws",
    ".ssh",
    "credentials",
}
APPROVAL_DIRS = {"data", "datasets", "artifacts", "runs", "checkpoints", "models"}
SECRET_PATTERNS = (
    ("private-key", re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----")),
    ("OpenAI-style key", re.compile(rb"\bsk-[A-Za-z0-9_-]{20,}\b")),
    ("GitHub token", re.compile(rb"\bgh[pousr]_[A-Za-z0-9]{30,}\b")),
    ("AWS access key", re.compile(rb"\bAKIA[0-9A-Z]{16}\b")),
    ("Google API key", re.compile(rb"\bAIza[0-9A-Za-z_-]{35}\b")),
    ("Slack token", re.compile(rb"\bxox[baprs]-[A-Za-z0-9-]{20,}\b")),
    (
        "credential assignment",
        re.compile(
            rb"(?i)\b(?:api[_-]?key|access[_-]?token|auth[_-]?token|client[_-]?secret|token|secret|password)"
            rb"\s*[:=]\s*[\"']?(?!your\b|example\b|placeholder\b|changeme\b|\$)[A-Za-z0-9_./+=-]{12,}"
        ),
    ),
)


class ExportError(Exception):
    """A safe, user-facing export failure."""


@dataclass
class FileRecord:
    path: str
    mode: str
    source: str
    loader: object
    head_blob: str | None = None
    index_blob: str | None = None
    git_status: str = "unknown"
    commit: str | None = None
    size_hint: int | None = None

    def read(self) -> bytes:
        try:
            value = self.loader()
        except (OSError, subprocess.CalledProcessError) as exc:
            raise ExportError(f"Unable to read selected snapshot file: {self.path}") from exc
        if not isinstance(value, bytes):
            raise ExportError(f"Invalid content for selected snapshot file: {self.path}")
        return value


def git(repo: Path, *args: str, input_bytes: bytes | None = None, check: bool = True) -> bytes:
    result = subprocess.run(
        ["git", *args], cwd=repo, input=input_bytes, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, check=False,
    )
    if check and result.returncode:
        detail = result.stderr.decode("utf-8", "replace").strip()
        raise ExportError(f"git {' '.join(args)} failed: {detail}")
    return result.stdout


def decode_path(raw: bytes) -> str:
    try:
        value = raw.decode("utf-8", "strict")
    except UnicodeDecodeError as exc:
        raise ExportError("Git contains a path that is not valid UTF-8") from exc
    validate_path(value)
    return value


def validate_path(value: str) -> str:
    if (
        not value
        or "\\" in value
        or ":" in value
        or any(ord(char) < 32 or ord(char) == 127 for char in value)
    ):
        raise ExportError(f"Unsafe archive path rejected: {value!r}")
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in ("", ".", "..") for part in path.parts):
        raise ExportError(f"Unsafe archive path rejected: {value!r}")
    if path.as_posix() != value:
        raise ExportError(f"Unsafe archive path rejected: {value!r}")
    return value


def excluded_reason(path: str, size: int | None, include_large: bool) -> str | None:
    parts = PurePosixPath(path).parts
    lowered = tuple(part.lower() for part in parts)
    name = lowered[-1]
    if any(part in EXCLUDED_DIRS for part in lowered):
        return "generated, private, artifact, or export directory"
    if not include_large and any(part in APPROVAL_DIRS for part in lowered):
        return "large or private artifact requires explicit approval and --include-large"
    if name == "chat_history.md" or "conversation" in name or "transcript" in name:
        return "private conversation history"
    if name.startswith(".env"):
        return "environment or private configuration"
    if any(term in name for term in ("credential", "service-account", "secret-store")):
        return "credential-like path"
    if name in {"token", "token.json", "auth.json", "oauth.json", "secrets.json", ".netrc"}:
        return "credential-like path"
    if name in {"id_rsa", "id_ed25519", "known_hosts"} or name.endswith(
        (".pem", ".key", ".p12", ".pfx", ".keystore")
    ):
        return "private key or credential file"
    if name.endswith(".zip"):
        return "previous archive"
    if not include_large and name.endswith((".pt", ".pth", ".ckpt", ".onnx", ".safetensors")):
        return "model weights or checkpoint"
    if size is not None and size > MAX_FILE_SIZE and not include_large:
        return "large file requires explicit approval and --include-large"
    return None


def parse_tree(repo: Path, revision: str) -> dict[str, tuple[str, str]]:
    raw = git(repo, "ls-tree", "-rz", "--full-tree", revision)
    result = {}
    for item in raw.split(b"\0"):
        if not item:
            continue
        meta, raw_path = item.split(b"\t", 1)
        mode, kind, oid = meta.decode("ascii").split(" ", 2)
        if kind == "blob":
            result[decode_path(raw_path)] = (mode, oid)
    return result


def parse_index(repo: Path) -> dict[str, tuple[str, str]]:
    raw = git(repo, "ls-files", "--stage", "-z")
    result = {}
    for item in raw.split(b"\0"):
        if not item:
            continue
        meta, raw_path = item.split(b"\t", 1)
        mode, oid, stage = meta.decode("ascii").split(" ", 2)
        if stage != "0":
            raise ExportError("The Git index has unresolved conflicts; staged export stopped.")
        result[decode_path(raw_path)] = (mode, oid)
    return result


def object_bytes(repo: Path, oid: str) -> bytes:
    return git(repo, "cat-file", "blob", oid)


def snapshot_files(repo: Path, mode: str, commit: str | None):
    if mode == "committed":
        if not commit:
            raise ExportError("--mode committed requires --commit <revision>.")
        revision = git(repo, "rev-parse", "--verify", f"{commit}^{{commit}}").decode().strip()
        tree = parse_tree(repo, revision)
        records = {}
        for path, (file_mode, oid) in tree.items():
            records[path] = FileRecord(
                path, file_mode, "commit", lambda oid=oid: object_bytes(repo, oid),
                commit=revision,
                size_hint=int(git(repo, "cat-file", "-s", oid).decode().strip()),
            )
        return records, revision, None

    head_raw = git(repo, "rev-parse", "--verify", "HEAD^{commit}").decode().strip()
    head = parse_tree(repo, head_raw)
    index = parse_index(repo)
    branch_raw = git(repo, "symbolic-ref", "--quiet", "--short", "HEAD", check=False)
    branch = branch_raw.decode("utf-8", "replace").strip() or None
    records: dict[str, FileRecord] = {}

    if mode == "staged":
        for path, (file_mode, oid) in index.items():
            same_head = head.get(path, (None, None))[1] == oid
            source = "HEAD" if same_head else "index"
            records[path] = FileRecord(
                path, file_mode, source, lambda oid=oid: object_bytes(repo, oid),
                head_blob=head.get(path, (None, None))[1], index_blob=oid,
                git_status="clean" if same_head else "staged",
                size_hint=int(git(repo, "cat-file", "-s", oid).decode().strip()),
            )
        return records, head_raw, branch

    untracked_raw = git(repo, "ls-files", "--others", "--exclude-standard", "-z")
    untracked = {decode_path(item) for item in untracked_raw.split(b"\0") if item}
    for path in sorted(set(head) | set(index) | untracked):
        file_path = repo.joinpath(*PurePosixPath(path).parts)
        head_blob = head.get(path, (None, None))[1]
        index_blob = index.get(path, (None, None))[1]
        is_tracked = path in head or path in index
        try:
            size = file_path.lstat().st_size
        except OSError:
            size = None
        records[path] = FileRecord(
            path,
            index.get(path, head.get(path, ("100644", None)))[0],
            "worktree" if is_tracked else "untracked",
            lambda file_path=file_path, repo=repo, path=path: read_worktree_file(repo, path, file_path),
            head_blob=head_blob,
            index_blob=index_blob,
            git_status="untracked" if not is_tracked else "unknown",
            size_hint=size,
        )
    return records, head_raw, branch


def read_worktree_file(repo: Path, path: str, file_path: Path) -> bytes:
    current = repo
    for part in PurePosixPath(path).parts:
        current = current / part
        try:
            if current.is_symlink():
                raise ExportError(f"Selected symlink is not followed: {path}")
        except OSError as exc:
            raise ExportError(f"Unable to inspect selected path: {path}") from exc
    try:
        mode = file_path.lstat().st_mode
    except OSError:
        raise ExportError(f"Required selected snapshot file is missing: {path}")
    if not stat.S_ISREG(mode):
        raise ExportError(f"Selected path is not a regular file: {path}")
    return file_path.read_bytes()


def json_record(records: dict[str, FileRecord], path: str, description: str):
    record = records.get(path)
    if record is None:
        raise ExportError(f"Required {description} is missing from the selected snapshot: {path}")
    reason = excluded_reason(path, record.size_hint, False)
    if reason:
        raise ExportError(f"Required {description} is excluded ({reason}): {path}")
    try:
        return json.loads(record.read().decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ExportError(f"Canonical {description} is not JSON-compatible YAML: {path}") from exc


def task_text(task: dict) -> str:
    return json.dumps(task, ensure_ascii=False, sort_keys=True).lower()


def scope_task_ids(scope: str, tasks: list[dict]) -> set[str]:
    scope = scope.strip().lower()
    code = re.fullmatch(r"([gm]\d+(?:-\d{3})?)", scope)
    if code:
        target = code.group(1).upper()
        return {
            str(task.get("id"))
            for task in tasks
            if str(task.get("id", "")).upper() == target
            or str(task.get("milestone", "")).upper() == target
            or str(task.get("id", "")).upper().startswith(target + "-")
        }
    terms = {part for part in re.findall(r"[a-z0-9][a-z0-9_-]*", scope) if len(part) > 2}
    matched = set()
    for task in tasks:
        text = task_text(task)
        if scope in text:
            matched.add(str(task.get("id")))
            continue
        if terms and len(terms & set(re.findall(r"[a-z0-9][a-z0-9_-]*", text))) >= max(1, (len(terms) + 1) // 2):
            matched.add(str(task.get("id")))
    return matched


def declared_file_references(value) -> set[str]:
    found = set()
    if isinstance(value, dict):
        for key, child in value.items():
            key = key.lower()
            if isinstance(child, str) and (
                key in {"path", "file", "plan_ref", "log_path"}
                or key.endswith(("_path", "_file", "_ref"))
            ):
                candidate = child.strip().strip("`'\" ")
                if candidate and not re.match(r"(?i)(?:[a-z][a-z0-9+.-]*:|//)", candidate):
                    if "/" in candidate or PurePosixPath(candidate).suffix:
                        found.add(validate_path(candidate))
            found.update(declared_file_references(child))
    elif isinstance(value, list):
        for child in value:
            found.update(declared_file_references(child))
    return found


def config_path(path: str) -> bool:
    name = PurePosixPath(path).name
    low = name.lower()
    return (
        name in CONFIG_NAMES
        or low.startswith("requirements") and low.endswith((".txt", ".in"))
        or low.endswith((".lock", ".toml", ".ini")) and not low.endswith(".tmp")
        or low in {"makefile", "justfile", "dockerfile"}
    )


def module_names(path: str) -> tuple[str, ...]:
    pure = PurePosixPath(path)
    if pure.suffix != ".py":
        return ()
    parts = list(pure.with_suffix("").parts)
    if parts[-1] == "__init__":
        parts.pop()
    if not parts:
        return ()
    return (".".join(parts),)


def import_targets(path: str, content: bytes, module_map: dict[str, str]):
    try:
        tree = ast.parse(content.decode("utf-8"), filename=path)
    except (SyntaxError, UnicodeDecodeError):
        return set(), "imports could not be parsed", set()
    current = module_names(path)
    package = current[0].split(".")[:-1] if current else []
    targets = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            targets.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                base = package[: max(0, len(package) - node.level + 1)]
                prefix = ".".join(base + ([node.module] if node.module else []))
            else:
                prefix = node.module or ""
            if prefix:
                targets.add(prefix)
            for alias in node.names:
                if alias.name != "*":
                    targets.add(".".join(filter(None, (prefix, alias.name))))
    resolved = set()
    unresolved_internal = set()
    known_tops = {name.split(".")[0] for name in module_map}
    for target in targets:
        matched = False
        parts = target.split(".")
        for end in range(len(parts), 0, -1):
            candidate = ".".join(parts[:end])
            if candidate in module_map:
                resolved.add(module_map[candidate])
                matched = True
                break
        if not matched and parts[0] in known_tops:
            unresolved_internal.add(target)
    return resolved, None, unresolved_internal


def python_path_targets(content: bytes, available: set[str]) -> set[str]:
    try:
        tree = ast.parse(content.decode("utf-8"))
    except (SyntaxError, UnicodeDecodeError):
        return set()

    def joined_parts(node):
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
            return joined_parts(node.left) + joined_parts(node.right)
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            return [node.value]
        return []

    found = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
            parts = joined_parts(node)
            if len(parts) > 1:
                candidate = posixpath.normpath(posixpath.join(*parts))
                if candidate in available:
                    found.add(candidate)
        elif isinstance(node, ast.Constant) and isinstance(node.value, str) and "/" in node.value:
            candidate = posixpath.normpath(node.value)
            if candidate in available:
                found.add(candidate)
    return found


def markdown_links(path: str, content: bytes):
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        return []
    links = re.findall(r"\]\(([^)]+)\)", text)
    results = []
    for link in links:
        value = link.strip().split()[0].strip("<>")
        if not value or re.match(r"(?i)(?:[a-z][a-z0-9+.-]*:|//|#)", value):
            continue
        value = value.split("#", 1)[0].split("?", 1)[0]
        if not value:
            continue
        joined = posixpath.normpath(posixpath.join(posixpath.dirname(path), value))
        if joined == ".." or joined.startswith("../") or joined.startswith("/"):
            continue
        results.append(joined)
    return results


def source_status(repo: Path, record: FileRecord, content: bytes) -> str:
    if record.source == "untracked":
        return "untracked"
    blob_id = git(repo, "hash-object", "--stdin", input_bytes=content).decode().strip()
    if record.source == "worktree":
        if blob_id == record.head_blob:
            return "clean"
        if record.index_blob and record.index_blob != record.head_blob and blob_id != record.index_blob:
            return "staged and unstaged changes"
        return "modified"
    return record.git_status


def sensitive_matches(content: bytes) -> list[str]:
    return [label for label, pattern in SECRET_PATTERNS if pattern.search(content)]


def collect_task_closure(tasks: list[dict], initial: set[str]) -> list[dict]:
    by_id = {str(task.get("id")): task for task in tasks if task.get("id")}
    pending = list(sorted(initial))
    selected = set()
    while pending:
        task_id = pending.pop()
        if task_id in selected:
            continue
        task = by_id.get(task_id)
        if task is None:
            raise ExportError(f"Review scope references missing backlog task: {task_id}")
        selected.add(task_id)
        dependencies = task.get("depends_on", []) or []
        for dependency in dependencies:
            if str(dependency) not in by_id:
                raise ExportError(f"Task {task_id} has missing dependency: {dependency}")
            pending.append(str(dependency))
    return [by_id[task_id] for task_id in sorted(selected)]


def verify_output_ignored(repo: Path, output_dir: Path) -> str:
    try:
        relative = output_dir.resolve().relative_to(repo.resolve()).as_posix()
    except ValueError as exc:
        raise ExportError("Output directory must be inside this repository.") from exc
    if relative != OUTPUT_DIR:
        raise ExportError(f"Output directory must be the dedicated {OUTPUT_DIR} directory.")
    ignored = subprocess.run(
        ["git", "check-ignore", "-q", "--", relative.rstrip("/") + "/.review-bundle-check.zip"], cwd=repo,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False,
    )
    if ignored.returncode != 0:
        raise ExportError(f"The output directory is not ignored by Git: {relative}")
    return relative


def _publish_archive(temp_path: Path, archive: Path) -> None:
    try:
        os.link(temp_path, archive)
    except FileExistsError as exc:
        raise ExportError(f"Refusing to overwrite existing review archive: {archive.name}") from exc
    except OSError as exc:
        raise ExportError("Unable to publish review archive without replacing an existing file.") from exc


def git_guard(repo: Path) -> dict:
    state_paths = (
        ".agents/state/PROJECT_STATE.yaml",
        ".agents/state/SESSION_HANDOFF.md",
        ".agents/state/BLOCKERS.md",
        ".agents/state/VERIFIED_FINDINGS.md",
        ".agents/tasks/BACKLOG.yaml",
        "docs/01-foundation/REQUIREMENTS.md",
        "docs/02-management/EXECUTION_PLAN.md",
    )
    return {
        "head": git(repo, "rev-parse", "HEAD").decode().strip(),
        "index": git(repo, "ls-files", "--stage", "-z"),
        "tracked_diff": git(repo, "diff", "--raw", "--full-index", "HEAD"),
        "status": git(repo, "status", "--porcelain=v1", "--untracked-files=all", "-z"),
        "state": {
            path: hashlib.sha256((repo / path).read_bytes()).hexdigest()
            for path in state_paths if (repo / path).is_file()
        },
    }


def state_summary(state: dict) -> dict:
    governance = state.get("governance", {})
    engineering = state.get("engineering", {})
    task_refs = state.get("task_refs", {})
    return {
        "current_gate": governance.get("current_gate"),
        "gate_status": governance.get("gate_status"),
        "approved_gates": governance.get("approved_gates", []),
        "next_user_action": governance.get("next_user_action"),
        "active_milestone": engineering.get("active_milestone"),
        "next_milestone": engineering.get("next_milestone"),
        "next_milestone_status": engineering.get("next_milestone_status"),
        "start_authorized": engineering.get("start_authorized"),
        "active_task_id": task_refs.get("active_task_id"),
        "next_task_id": task_refs.get("next_task_id"),
        "active_blocker_ids": state.get("active_blocker_ids", []),
    }


def open_confirmation_ids(requirements: bytes) -> list[str]:
    text = requirements.decode("utf-8", "replace")
    heading = re.search(r"(?im)^#{1,6}\s+[^\n]*(?:open approvals|open confirmations)[^\n]*\n", text)
    if not heading:
        return []
    tail = text[heading.end():]
    next_heading = re.search(r"(?m)^#{1,6}\s+", tail)
    section = tail[: next_heading.start()] if next_heading else tail
    return sorted(set(re.findall(r"\bO-\d{2}\b", section)))


def make_readme(scope, mode, revision, summary, tasks, commands, limitations, files):
    lines = [
        "# Review Bundle",
        "",
        f"Review scope: {scope}",
        f"Snapshot mode: {mode}",
        f"Git revision: `{revision}`",
        "Selected files follow canonical task and evidence references, local Markdown links, first-party imports, and project configuration.",
        "",
        "## Project state",
        "",
    ]
    for key, value in summary.items():
        lines.append(f"- `{key}`: {json.dumps(value, ensure_ascii=False)}")
    lines += ["", "## Selected task records", ""]
    lines.extend(f"- `{task.get('id')}` — {task.get('title', '')} ({task.get('status', 'status not recorded')})" for task in tasks)
    lines += ["", "## Included evidence and project files", ""]
    lines.extend(f"- `{path}`" for path in files)
    lines += ["", "## Reproduction commands", "", "These are commands recorded in the selected task evidence; this export did not run them.", ""]
    lines.extend(f"- `{command}`" for command in commands)
    if not commands:
        lines.append("- No reproduction command was recorded in the selected task references.")
    lines += ["", "## Review limitations", ""]
    lines.extend(f"- {item}" for item in limitations)
    if not limitations:
        lines.append("- No additional limitations were discovered during file selection.")
    lines += ["", "File hashes, sizes, exclusions, and per-file Git provenance are in `REVIEW_MANIFEST.json`.", ""]
    return "\n".join(lines).encode("utf-8")


def export_bundle(scope: str, mode: str = "working-tree", commit: str | None = None,
                  repo: Path = REPO_ROOT, output_dir: Path | None = None,
                  include_large: bool = False) -> Path:
    repo = repo.resolve()
    if git(repo, "rev-parse", "--show-toplevel").decode().strip() != str(repo):
        raise ExportError(f"Not a Git repository root: {repo}")
    output_dir = output_dir or repo / OUTPUT_DIR
    verify_output_ignored(repo, output_dir)
    guard_before = git_guard(repo)
    records, revision, branch = snapshot_files(repo, mode, commit)

    # Excluded paths are recorded without reading their contents.
    exclusions = [
        {"path": path, "reason": reason}
        for path, record in records.items()
        if (reason := excluded_reason(path, record.size_hint, include_large))
    ]
    usable = {
        path: record for path, record in records.items()
        if not excluded_reason(path, record.size_hint, include_large)
    }
    for path in records:
        validate_path(path)
    missing = [path for path in REQUIRED_CONTEXT if path not in usable]
    if missing:
        raise ExportError("Required review context is missing or excluded: " + ", ".join(missing))

    state = json_record(usable, ".agents/state/PROJECT_STATE.yaml", "project state")
    backlog = json_record(usable, ".agents/tasks/BACKLOG.yaml", "task backlog")
    if not isinstance(backlog, dict) or not isinstance(backlog.get("tasks"), list):
        raise ExportError("Canonical task backlog has no tasks list.")
    tasks = backlog["tasks"]
    selected_ids = scope_task_ids(scope, tasks)
    selected_tasks = collect_task_closure(tasks, selected_ids)
    limitations = []
    selected = set(REQUIRED_CONTEXT)
    selected.update(path for path in usable if config_path(path))
    available = set(usable)
    for task in selected_tasks:
        task_references = declared_file_references(task)
        selected.update(task_references & available)
        for path in sorted(task_references - available):
            reason = next((item["reason"] for item in exclusions if item["path"] == path), None)
            if reason:
                limitations.append(f"Task {task.get('id')} references an excluded file: {path} ({reason}).")
            else:
                limitations.append(f"Task {task.get('id')} references a file unavailable in this snapshot: {path}.")

    # Evidence commands may name tests or scripts without a separate file-reference field.
    for task in selected_tasks:
        for evidence in task.get("evidence", []) or []:
            command = evidence.get("command", "") if isinstance(evidence, dict) else ""
            if not isinstance(command, str):
                continue
            if "unittest discover -s tests" in command or "pytest" in command:
                selected.update(path for path in available if path.startswith("tests/") and path.endswith(".py"))
            for path in available:
                basename = PurePosixPath(path).name
                if basename and re.search(r"(?<![A-Za-z0-9_.-])" + re.escape(basename) + r"(?![A-Za-z0-9_.-])", command):
                    selected.add(path)

    if not selected_tasks:
        terms = {term for term in re.findall(r"[a-z0-9][a-z0-9_-]*", scope.lower()) if len(term) > 2}
        matches = set()
        for path, record in usable.items():
            if terms and terms & set(re.findall(r"[a-z0-9][a-z0-9_-]*", path.lower())):
                matches.add(path)
                continue
            if PurePosixPath(path).suffix.lower() in {".md", ".py", ".toml", ".yaml", ".yml", ".json", ".txt", ".sh"}:
                content = record.read()
                text = content.decode("utf-8", "ignore").lower()
                if scope.lower() in text or (terms and len(terms & set(re.findall(r"[a-z0-9][a-z0-9_-]*", text))) >= max(1, (len(terms) + 1) // 2)):
                    matches.add(path)
        if matches:
            selected.update(matches)
        else:
            selected.update(
                path for path in usable
                if path.startswith(("src/", "scripts/", "tests/", "docs/", ".agents/"))
                and PurePosixPath(path).suffix.lower() in {".md", ".py", ".toml", ".yaml", ".yml", ".json", ".txt", ".sh"}
            )
            limitations.append("Scope did not match a backlog task or file content; eligible first-party text files were included broadly.")

    selected.update(path for path in REQUIRED_CONTEXT if path in usable)
    selected = {path for path in selected if path in usable}
    contents: dict[str, bytes] = {}
    sources: dict[str, str] = {}
    status_by_path: dict[str, str] = {}
    for path in sorted(selected):
        record = usable[path]
        if path in {"REVIEW_README.md", "REVIEW_MANIFEST.json"}:
            raise ExportError(f"Project path collides with reserved archive metadata: {path}")
        if record.mode == "120000":
            raise ExportError(f"Selected symlink is not followed: {path}")
        content = record.read()
        if len(content) > MAX_FILE_SIZE and not include_large:
            exclusions.append({"path": path, "reason": "large file requires explicit approval and --include-large"})
            limitations.append(f"Large referenced file omitted: {path}")
            continue
        if b"\0" in content and not path.lower().endswith((".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico")):
            exclusions.append({"path": path, "reason": "binary or unsupported content"})
            limitations.append(f"Binary referenced file omitted: {path}")
            continue
        findings = sensitive_matches(content)
        if findings:
            labels = ", ".join(findings)
            raise ExportError(f"Potential sensitive content detected in selected file(s): {path} ({labels}). No archive was written.")
        contents[path] = content
        sources[path] = record.source
        status_by_path[path] = source_status(repo, record, content)

    # Follow local Markdown links and first-party Python imports to a fixed point.
    module_map = {}
    for path in usable:
        for module in module_names(path):
            module_map[module] = path
    queue = list(sorted(contents))
    seen = set()
    while queue:
        path = queue.pop()
        if path in seen:
            continue
        seen.add(path)
        content = contents[path]
        links = markdown_links(path, content) if path.lower().endswith(".md") else []
        imports, parse_issue, unresolved_imports = import_targets(path, content, module_map) if path.endswith(".py") else (set(), None, set())
        if parse_issue:
            limitations.append(f"Python import dependencies could not be parsed for {path}.")
        for unresolved in sorted(unresolved_imports):
            limitations.append(f"First-party Python import could not be resolved: {path} imports {unresolved}.")
        dependencies = set(links) | imports
        if path.endswith(".py"):
            dependencies.update(python_path_targets(content, available))
        for dependency in sorted(dependencies):
            if dependency not in usable:
                if dependency in records:
                    limitations.append(f"Referenced file is excluded: {dependency}")
                elif dependency in links:
                    limitations.append(f"Local Markdown link is unavailable in this snapshot: {dependency}")
                continue
            if dependency in contents:
                continue
            record = usable[dependency]
            if record.mode == "120000":
                raise ExportError(f"Selected symlink is not followed: {dependency}")
            content = record.read()
            if len(content) > MAX_FILE_SIZE and not include_large:
                exclusions.append({"path": dependency, "reason": "large dependency requires explicit approval and --include-large"})
                limitations.append(f"Large dependency omitted: {dependency}")
                continue
            findings = sensitive_matches(content)
            if findings:
                raise ExportError(f"Potential sensitive content detected in selected file(s): {dependency} ({', '.join(findings)}). No archive was written.")
            contents[dependency] = content
            sources[dependency] = record.source
            status_by_path[dependency] = source_status(repo, record, content)
            queue.append(dependency)

    missing_required = sorted(set(REQUIRED_CONTEXT) - set(contents))
    if missing_required:
        raise ExportError("Required review context could not be read: " + ", ".join(missing_required))

    requirement_content = contents["docs/01-foundation/REQUIREMENTS.md"]
    confirmation_ids = open_confirmation_ids(requirement_content)
    if confirmation_ids:
        limitations.append("Open confirmation IDs are listed in requirements: " + ", ".join(confirmation_ids) + ".")
    for task in selected_tasks:
        if task.get("blocker_ids"):
            limitations.append(f"Task {task.get('id')} has blocker references: {', '.join(map(str, task['blocker_ids']))}.")
    limitations.append("Sensitive-content scanning uses pattern heuristics and cannot guarantee the absence of every secret.")

    commands = []
    for task in selected_tasks:
        for evidence in task.get("evidence", []) or []:
            if isinstance(evidence, dict):
                command = evidence.get("command")
                if isinstance(command, str) and command not in commands:
                    commands.append(command)
    files = sorted(contents)
    timestamp = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    manifest_files = []
    for path in files:
        data = contents[path]
        record = records[path]
        provenance = {"source": sources[path], "git_status": status_by_path[path]}
        if record.head_blob:
            provenance["head_blob"] = record.head_blob
        if record.index_blob:
            provenance["index_blob"] = record.index_blob
        if record.commit:
            provenance["commit"] = record.commit
        elif mode != "committed":
            provenance["head_revision"] = revision
        manifest_files.append({
            "path": path,
            "size_bytes": len(data),
            "sha256": hashlib.sha256(data).hexdigest(),
            "provenance": provenance,
        })
    readme = make_readme(scope, mode, revision, state_summary(state), selected_tasks,
                         commands, sorted(set(limitations)), files)
    manifest_files.append({
        "path": "REVIEW_README.md",
        "size_bytes": len(readme),
        "sha256": hashlib.sha256(readme).hexdigest(),
        "provenance": {"source": "generated", "role": "review guide"},
    })
    manifest = {
        "format_version": 1,
        "scope": scope,
        "snapshot_mode": mode,
        "exported_at_utc": timestamp,
        "git_revision": revision,
        "git_branch": branch if mode != "committed" else None,
        "selection_method": "canonical tasks and evidence, local Markdown links, first-party imports, and project configuration",
        "files": manifest_files,
        "manifest_self_hash": "omitted because a manifest cannot contain its own final hash",
        "excluded_paths": sorted(exclusions + list(EXCLUSION_POLICIES), key=lambda item: (item["path"], item["reason"])),
        "unresolved_review_limitations": sorted(set(limitations)),
        "project_state": state_summary(state),
        "task_ids": [task.get("id") for task in selected_tasks],
    }
    manifest_bytes = (json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")

    output_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    safe_scope = re.sub(r"[^A-Za-z0-9._-]+", "-", scope).strip("-._") or "review"
    archive = output_dir / f"{safe_scope}-{mode}-{stamp}.zip"
    with tempfile.NamedTemporaryFile(prefix=".review-bundle-", suffix=".tmp", dir=output_dir, delete=False) as temp:
        temp_path = Path(temp.name)
    try:
        with zipfile.ZipFile(temp_path, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
            for path in files:
                validate_path(path)
                bundle.writestr(path, contents[path])
            bundle.writestr("REVIEW_README.md", readme)
            bundle.writestr("REVIEW_MANIFEST.json", manifest_bytes)
        with zipfile.ZipFile(temp_path, "r") as bundle:
            bad = bundle.testzip()
            if bad:
                raise ExportError(f"ZIP CRC verification failed for: {bad}")
            expected_names = set(files) | {"REVIEW_README.md", "REVIEW_MANIFEST.json"}
            if set(bundle.namelist()) != expected_names:
                raise ExportError("Archive member list does not match its manifest.")
            for item in manifest_files:
                value = bundle.read(item["path"])
                if hashlib.sha256(value).hexdigest() != item["sha256"] or len(value) != item["size_bytes"]:
                    raise ExportError(f"Archived content verification failed: {item['path']}")
            verified_manifest = json.loads(bundle.read("REVIEW_MANIFEST.json"))
            if {entry["path"] for entry in verified_manifest["files"]} != set(files) | {"REVIEW_README.md"}:
                raise ExportError("Manifest file list is inconsistent with archive members.")
        if git_guard(repo) != guard_before:
            raise ExportError("Export changed Git state or canonical project state; archive withheld.")
        _publish_archive(temp_path, archive)
    finally:
        if temp_path.exists():
            temp_path.unlink()
    return archive


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Export a secure, reproducible project review ZIP.")
    parser.add_argument("--scope", required=True, help="Review scope, such as M0, G1, or a task description.")
    parser.add_argument("--mode", choices=("working-tree", "staged", "committed"), default="working-tree")
    parser.add_argument("--commit", help="Git commit or ref; required in committed mode.")
    parser.add_argument("--repo", type=Path, default=REPO_ROOT, help=argparse.SUPPRESS)
    parser.add_argument("--output-dir", type=Path, help=argparse.SUPPRESS)
    parser.add_argument("--include-large", action="store_true", help="Include referenced files over 2 MiB after explicit approval.")
    return parser.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    if args.mode == "committed" and not args.commit:
        print("error: --mode committed requires --commit <revision>", file=sys.stderr)
        return 2
    if args.mode != "committed" and args.commit:
        print("error: --commit is only valid with --mode committed", file=sys.stderr)
        return 2
    try:
        archive = export_bundle(args.scope, args.mode, args.commit, args.repo,
                                args.output_dir, args.include_large)
    except ExportError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(f"Created review bundle: {archive}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
