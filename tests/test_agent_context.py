"""Recovery-tool contract tests using disposable repositories only."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
PREFLIGHT = REPO / "scripts" / "agent_preflight.py"
CHECKPOINT = REPO / "scripts" / "agent_checkpoint.py"
CHECKPOINT_ID = "cp-fixture-0001"
G1_BASELINE_REVISION = "9449b3f3508c55e1a34893a49c2670498310f78f"
G1_RECOVERY_FIXTURE = REPO / "tests" / "fixtures" / "g1-recovery-baseline.json"
sys.dont_write_bytecode = True
sys.path.insert(0, str(REPO / "scripts"))
import agent_checkpoint
import agent_preflight

REQUIRED_FILES = [
    "AGENTS.md",
    "README.md",
    "docs/01-foundation/ROADMAP.md",
    "atari-videochess-rl-roadmap.html",
    "docs/01-foundation/REQUIREMENTS.md",
    "docs/01-foundation/PROJECT_OVERVIEW.md",
    "docs/02-management/EXECUTION_PLAN.md",
    "docs/02-management/RISK_REGISTER.md",
    "docs/02-management/decisions/ADR-0001-governance-crosswalk-and-file-priorities.md",
    "docs/05-operations/SETUP.md",
    "docs/06-quality/ACCEPTANCE_CRITERIA.md",
    "docs/06-quality/TEST_STRATEGY.md",
    ".agents/PLANS.md",
    ".agents/state/PROJECT_STATE.yaml",
    ".agents/state/SESSION_HANDOFF.md",
    ".agents/state/BLOCKERS.md",
    ".agents/state/VERIFIED_FINDINGS.md",
    ".agents/tasks/BACKLOG.yaml",
    ".agents/plans/G1-consistency-hardening.md",
    ".agents/plans/M00-bootstrap.md",
    ".agents/evidence/G1-hardening-verification.md",
    "scripts/agent_preflight.py",
    "scripts/agent_checkpoint.py",
    "tests/test_agent_context.py",
]


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_json_hash(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def git(root: Path, *args: str) -> str:
    env = os.environ.copy()
    env["GIT_OPTIONAL_LOCKS"] = "0"
    return subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        capture_output=True,
        text=True,
        env=env,
    ).stdout.strip()


def status_entries(root: Path) -> list[str]:
    result = subprocess.run(
        ["git", "-C", str(root), "status", "--porcelain=v1", "--untracked-files=all"],
        check=True,
        capture_output=True,
        text=True,
    )
    return sorted(line for line in result.stdout.splitlines() if line)


def status_hash(entries: list[str]) -> str:
    payload = "\n".join(entries) + ("\n" if entries else "")
    return hashlib.sha256(payload.encode()).hexdigest()


def commit_all(root: Path, message: str) -> None:
    subprocess.run(["git", "-C", str(root), "add", "-A"], check=True, capture_output=True, text=True)
    subprocess.run(
        ["git", "-C", str(root), "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid", "commit", "-qm", message],
        check=True,
        capture_output=True,
        text=True,
    )


def create_repo_from_revision(root: Path, revision: str) -> None:
    root.mkdir(parents=True, exist_ok=True)
    git(root, "init", "-q", "-b", "main")
    paths = subprocess.check_output(
        ["git", "-C", str(REPO), "ls-tree", "-r", "--name-only", "-z", revision]
    ).decode().split("\0")
    for rel in filter(None, paths):
        destination = root / rel
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(subprocess.check_output(["git", "-C", str(REPO), "show", f"{revision}:{rel}"]))
    commit_all(root, f"fixture from {revision[:8]}")


def checkpoint_and_commit(root: Path, message: str) -> None:
    for private_path in (root / "chat_history.md", root / ".env"):
        private_path.unlink(missing_ok=True)
    git(root, "add", "--all")
    result = subprocess.run(
        [sys.executable, str(CHECKPOINT), "--repo", str(root)],
        capture_output=True,
        text=True,
    )
    if result.returncode:
        raise AssertionError(result.stdout + result.stderr)
    commit_all(root, message)


def run_preflight(root: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(root / "scripts/agent_preflight.py"), "--repo", str(root), "--json"],
        capture_output=True,
        text=True,
    )


def make_fixture(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    git(root, "init", "-q", "-b", "main")
    subprocess.run(
        ["git", "-C", str(root), "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid", "commit", "--allow-empty", "-qm", "fixture"],
        check=True,
        capture_output=True,
        text=True,
    )

    for rel in REQUIRED_FILES:
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        if rel.endswith(".yaml"):
            path.write_text("{}\n", encoding="utf-8")
        elif rel == ".agents/state/SESSION_HANDOFF.md":
            path.write_text(f"<!-- checkpoint-id: {CHECKPOINT_ID} -->\n# Handoff\n", encoding="utf-8")
        elif rel == ".agents/state/BLOCKERS.md":
            path.write_text("# Active Blockers\nNo active blockers.\n", encoding="utf-8")
        elif rel == "docs/01-foundation/REQUIREMENTS.md":
            path.write_text("# Requirements\n## 6. Open approvals and evidence needed\n| O-01 | Assignment/instructor rules | User approval |\n", encoding="utf-8")
        elif rel == "docs/06-quality/ACCEPTANCE_CRITERIA.md":
            path.write_text("# Criteria\n| ID | Pass condition | Evidence |\n|---|---|---|\n| G1-01 | Inventory is audited. | File list. |\n| G1-02 | Mapping is recorded. | ADR. |\n| M0-01 | M0 passes. | Evidence. |\n", encoding="utf-8")
        elif rel == "docs/02-management/decisions/ADR-0001-governance-crosswalk-and-file-priorities.md":
            path.write_text((REPO / rel).read_text(encoding="utf-8"), encoding="utf-8")
        elif rel == "AGENTS.md":
            path.write_text("# Agent rules\nSee [requirements](docs/01-foundation/REQUIREMENTS.md).\n", encoding="utf-8")
        else:
            path.write_text(f"# Fixture: {rel}\n", encoding="utf-8")
    (root / "chat_history.md").write_text("private conversation fixture\n", encoding="utf-8")
    (root / ".env").write_text("placeholder fixture only\n", encoding="utf-8")

    roman = ("I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI", "XII", "XIII", "XIV", "XV", "XVI", "XVII", "XVIII", "XIX")
    roadmap = "# Fixture Roadmap\n\n" + "\n\n".join(f"## {item}. Section {item}" for item in roman) + "\n"
    (root / "docs/01-foundation/ROADMAP.md").write_text(roadmap, encoding="utf-8")
    source_html = f'<details class="source-archive"><summary>source</summary><pre>{roadmap}</pre></details><script id="rawArchive" type="text/plain">{roadmap}</script>'
    (root / "atari-videochess-rl-roadmap.html").write_text(source_html, encoding="utf-8")

    backlog = {
        "format": "JSON-compatible YAML 1.2",
        "schema_version": 2,
        "project_id": "atari-videochess-rl",
        "tasks": [
            {
                "id": "G1-001",
                "title": "Fixture audit",
                "milestone": "G1",
                "status": "done",
                "next_action": "",
                "depends_on": [],
                "requires_user_gate_approval": None,
                "acceptance_criteria_ids": ["G1-01"],
                "blocker_ids": [],
            "evidence": [{
                "kind": "file", "path": "README.md", "detail": "Fixture evidence.",
                "provenance": {
                    "status": "verified", "executed_at_utc": None,
                    "recorded_at_utc": "2026-10-14T00:00:00Z", "exit_code": None,
                    "git_revision": git(root, "rev-parse", "HEAD"), "log_path": None
                }
            }],
            },
            {
                "id": "M0-001",
                "title": "Technical bootstrap",
                "milestone": "M0",
                "status": "pending",
                "next_action": "Wait for explicit G1 user approval before M0.",
                "depends_on": ["G1-001"],
                "requires_user_gate_approval": "G1",
                "acceptance_criteria_ids": ["M0-01"],
                "blocker_ids": [],
                "evidence": [],
            },
        ],
    }
    write_json(root / ".agents/tasks/BACKLOG.yaml", backlog)

    paths = status_entries(root)
    repo_hashes = {
        rel: file_hash(root / rel)
        for rel in REQUIRED_FILES
        if rel != ".agents/state/PROJECT_STATE.yaml"
    }
    state = {
        "format": "JSON-compatible YAML 1.2",
        "schema_version": 2,
        "project_id": "atari-videochess-rl",
        "governance": {
            "current_gate": "G1",
            "gate_status": "ready_for_user_review",
            "approved_gates": ["G0"],
            "next_governance_gate": "G2",
            "user_authorized_g1": True,
            "next_user_action": "Review G1 before M0.",
        },
        "engineering": {
            "active_milestone": None,
            "next_milestone": "M0",
            "next_milestone_status": "pending_user_approval",
            "start_authorized": False,
            "hold_reason": "G1 approval is required.",
        },
        "task_refs": {"active_task_id": None, "next_task_id": "M0-001"},
        "active_blocker_ids": [],
        "last_checkpoint": {
            "id": CHECKPOINT_ID,
            "created_at_utc": "2026-10-14T00:00:00Z",
            "git": {
                "branch": "main",
                "head": git(root, "rev-parse", "HEAD"),
                "status_entries": paths,
                "status_sha256": status_hash(paths),
                "repo_file_hashes": repo_hashes,
                "unhashed_large_files": [],
                "unreadable_files": [],
                "artifact_dirs_requiring_manifest": [],
                "excluded_directories": [".git"],
                "excluded_symlink_files": 0,
            },
        },
        "g1_baseline": {
            "verified_at_utc": "2026-10-14T00:00:00Z",
            "branch": "main",
            "head": git(root, "rev-parse", "HEAD"),
            "status_entries": paths,
            "preserved_sha256": {"README.md": file_hash(root / "README.md")},
            "g1_expected_modified_sha256": {},
            "comparison_policy": "Historical baseline only; compare current drift with last_checkpoint.git.",
        },
    }
    state["g1_baseline"]["baseline_sha256"] = canonical_json_hash(state["g1_baseline"])
    write_json(root / ".agents/state/PROJECT_STATE.yaml", state)


class AgentContextRecoveryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name) / "repo"
        make_fixture(self.root)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def run_script(self, path: Path, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(path), "--repo", str(self.root), *args],
            capture_output=True,
            text=True,
        )

    def test_preflight_recovers_project_state_without_conversation(self) -> None:
        result = self.run_script(PREFLIGHT)
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        self.assertIn("G1", result.stdout)
        self.assertIn("M0", result.stdout)
        self.assertIn("G1-001", result.stdout)
        self.assertIn("O-01", result.stdout)
        self.assertIn("Assignment/instructor rules", result.stdout)
        self.assertIn("ADR-0001-governance-crosswalk-and-file-priorities.md", result.stdout)
        self.assertIn("Next task acceptance criteria: M0-01", result.stdout)
        self.assertIn("not started", result.stdout.lower())
        payload = json.loads(self.run_script(PREFLIGHT, "--json").stdout)
        self.assertTrue(payload["summary"]["roadmap_source"]["matches"])
        self.assertEqual(payload["summary"]["roadmap_source"]["roman_sections"], 19)

    def test_preflight_discovers_every_documented_acceptance_criterion(self) -> None:
        document = (REPO / "docs/06-quality/ACCEPTANCE_CRITERIA.md").read_text(encoding="utf-8")
        expected = set(re.findall(r"(?m)^\|\s*((?:G[0-5]|M[0-7])-\d{2})\s*\|", document))
        expected.update(re.findall(r"(?m)^\s*-\s+\*\*((?:G[0-5]|M[0-7])-\d{2}):\*\*", document))
        result = subprocess.run(
            [sys.executable, str(PREFLIGHT), "--repo", str(REPO), "--json"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        payload = json.loads(result.stdout)
        self.assertEqual(set(payload["summary"]["acceptance_criteria_ids"]), expected)
        self.assertEqual(len(expected), 51)

    def test_future_milestone_bullet_criteria_are_valid_task_references(self) -> None:
        criteria = self.root / "docs/06-quality/ACCEPTANCE_CRITERIA.md"
        added_bullets = "\n".join(f"- **M{milestone}-01:** Future milestone {milestone} acceptance fixture." for milestone in range(2, 8))
        criteria.write_text(criteria.read_text(encoding="utf-8") + "\n" + added_bullets + "\n", encoding="utf-8")
        backlog_path = self.root / ".agents/tasks/BACKLOG.yaml"
        backlog = json.loads(backlog_path.read_text(encoding="utf-8"))
        previous = "G1-001"
        for milestone in range(2, 8):
            task_id = f"M{milestone}-001"
            backlog["tasks"].append({
                "id": task_id, "title": f"Future milestone M{milestone} fixture", "milestone": f"M{milestone}", "status": "pending",
                "next_action": "Wait for its milestone gate.", "depends_on": [previous],
                "requires_user_gate_approval": None, "acceptance_criteria_ids": [f"M{milestone}-01"],
                "blocker_ids": [], "evidence": []
            })
            previous = task_id
        write_json(backlog_path, backlog)
        result = self.run_script(PREFLIGHT, "--json")
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        payload = json.loads(result.stdout)
        for milestone in range(2, 8):
            self.assertIn(f"M{milestone}-01", payload["summary"]["acceptance_criteria_ids"])

    def test_dry_run_with_partial_recovery_does_not_mutate_files(self) -> None:
        partial = self.root / ".agents/state/.PROJECT_STATE.yaml.tmp-interrupted"
        partial.write_text("{partial", encoding="utf-8")
        old = time.time() - 7200
        os.utime(partial, (old, old))
        before_status = status_entries(self.root)
        before_files = {
            path.relative_to(self.root).as_posix(): (path.read_bytes(), path.stat().st_mtime_ns)
            for path in self.root.rglob("*")
            if path.is_file()
        }
        source_cache = REPO / "scripts/__pycache__"
        before_source_cache = None if not source_cache.exists() else {
            path.relative_to(REPO).as_posix(): (path.read_bytes(), path.stat().st_mtime_ns)
            for path in source_cache.rglob("*") if path.is_file()
        }

        result = self.run_script(CHECKPOINT, "--dry-run", "--recover-partials")

        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        self.assertTrue(partial.is_file(), "dry-run must preserve stale partial files")
        after_files = {
            path.relative_to(self.root).as_posix(): (path.read_bytes(), path.stat().st_mtime_ns)
            for path in self.root.rglob("*")
            if path.is_file()
        }
        self.assertEqual(after_files, before_files)
        after_source_cache = None if not source_cache.exists() else {
            path.relative_to(REPO).as_posix(): (path.read_bytes(), path.stat().st_mtime_ns)
            for path in source_cache.rglob("*") if path.is_file()
        }
        self.assertEqual(after_source_cache, before_source_cache)
        self.assertEqual(status_entries(self.root), before_status)

    def test_checkpoint_is_consistent_after_one_run_from_clean_worktree(self) -> None:
        commit_all(self.root, "clean fixture")
        self.assertEqual(status_entries(self.root), [])
        baseline_before = json.loads((self.root / ".agents/state/PROJECT_STATE.yaml").read_text(encoding="utf-8"))["g1_baseline"]

        checkpoint = self.run_script(CHECKPOINT)
        self.assertEqual(checkpoint.returncode, 0, checkpoint.stderr + checkpoint.stdout)
        self.assertIn("Post-checkpoint preflight: PASS", checkpoint.stdout)
        state = json.loads((self.root / ".agents/state/PROJECT_STATE.yaml").read_text(encoding="utf-8"))
        portable = state["last_checkpoint"]["portable_git"]
        self.assertIn("README.md", portable["tracked_manifest"])
        self.assertNotIn(".agents/state/PROJECT_STATE.yaml", portable["tracked_manifest"])
        self.assertNotIn(".agents/state/SESSION_HANDOFF.md", portable["tracked_manifest"])
        self.assertNotIn("chat_history.md", portable["tracked_manifest"])
        self.assertNotIn(".env", portable["tracked_manifest"])
        self.assertIn(CHECKPOINT_ID, [item["id"] for item in state["checkpoint_history"]])
        self.assertEqual(state["g1_baseline"], baseline_before)
        after = self.run_script(PREFLIGHT)
        self.assertEqual(after.returncode, 0, after.stderr + after.stdout)
        self.assertNotIn("GIT_SNAPSHOT_DRIFT", after.stdout)
        self.assertNotIn("WORKTREE_CONTENT_DRIFT", after.stdout)

    def test_checkpoint_compacts_serialization_without_changing_history(self) -> None:
        commit_all(self.root, "compact checkpoint fixture")
        state_path = self.root / ".agents/state/PROJECT_STATE.yaml"
        before = json.loads(state_path.read_text(encoding="utf-8"))
        expected_history = list(before.get("checkpoint_history", []))
        previous = before["last_checkpoint"]
        if not any(item.get("id") == previous["id"] for item in expected_history):
            expected_history.append({
                "id": previous["id"],
                "created_at_utc": previous.get("created_at_utc", ""),
                "workspace_id": previous.get("workspace_id"),
                "workspace_git": previous.get("git", {}),
                "portable_git": previous.get("portable_git"),
            })

        checkpoint = self.run_script(CHECKPOINT)

        self.assertEqual(checkpoint.returncode, 0, checkpoint.stderr + checkpoint.stdout)
        serialized = state_path.read_text(encoding="utf-8")
        after = json.loads(serialized)
        self.assertEqual(after["checkpoint_history"], expected_history)
        self.assertEqual(serialized, json.dumps(after, separators=(",", ":"), ensure_ascii=False) + "\n")
        self.assertEqual(serialized.count("\n"), 1)
        self.assertEqual(self.run_script(PREFLIGHT).returncode, 0)

    def test_repeated_checkpoint_does_not_append_unchanged_snapshot(self) -> None:
        commit_all(self.root, "repeat checkpoint fixture")
        first = self.run_script(CHECKPOINT)
        self.assertEqual(first.returncode, 0, first.stderr + first.stdout)
        state_path = self.root / ".agents/state/PROJECT_STATE.yaml"
        handoff_path = self.root / ".agents/state/SESSION_HANDOFF.md"
        state_before = state_path.read_bytes()
        handoff_before = handoff_path.read_bytes()
        history_before = json.loads(state_before)["checkpoint_history"]

        second = self.run_script(CHECKPOINT)

        self.assertEqual(second.returncode, 0, second.stderr + second.stdout)
        self.assertIn("no new history entry was written", second.stdout)
        self.assertEqual(state_path.read_bytes(), state_before)
        self.assertEqual(handoff_path.read_bytes(), handoff_before)
        self.assertEqual(json.loads(state_path.read_bytes())["checkpoint_history"], history_before)

    def test_checkpoint_size_limit_fails_before_state_or_workspace_mutation(self) -> None:
        commit_all(self.root, "checkpoint size guard fixture")
        initial_checkpoint = self.run_script(CHECKPOINT)
        self.assertEqual(initial_checkpoint.returncode, 0, initial_checkpoint.stderr + initial_checkpoint.stdout)
        subprocess.run(
            ["git", "-C", str(self.root), "config", "--local", "--unset-all", "codex.contextWorkspaceId"],
            check=True,
            capture_output=True,
            text=True,
        )
        state_path = self.root / ".agents/state/PROJECT_STATE.yaml"
        handoff_path = self.root / ".agents/state/SESSION_HANDOFF.md"
        state = json.loads(state_path.read_text(encoding="utf-8"))
        state["checkpoint_history"] = [
            {
                "id": f"cp-size-fixture-{index:03d}",
                "created_at_utc": "2026-10-22T00:00:00Z",
                "workspace_git": {"preserved_payload": "x" * 70_000},
            }
            for index in range(60)
        ]
        state["last_checkpoint"]["portable_git"]["state_sha256"] = agent_preflight._portable_state_sha256(state)
        state_path.write_text(json.dumps(state, separators=(",", ":"), ensure_ascii=False) + "\n", encoding="utf-8")
        readme = self.root / "README.md"
        readme.write_text(readme.read_text(encoding="utf-8") + "\nContent change for size-guard fixture.\n", encoding="utf-8")
        before_state = state_path.read_bytes()
        before_handoff = handoff_path.read_bytes()
        workspace_id_before_result = subprocess.run(
            ["git", "-C", str(self.root), "config", "--local", "--get", "codex.contextWorkspaceId"], capture_output=True,
        )
        workspace_id_before = workspace_id_before_result.stdout.decode().strip() if workspace_id_before_result.returncode == 0 else None

        result = self.run_script(CHECKPOINT)

        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertIn("no state or handoff files were written", result.stdout)
        self.assertEqual(state_path.read_bytes(), before_state)
        self.assertEqual(handoff_path.read_bytes(), before_handoff)
        state_dir = self.root / ".agents/state"
        self.assertEqual(list(state_dir.glob(".PROJECT_STATE.yaml.tmp-*")), [])
        self.assertEqual(list(state_dir.glob(".SESSION_HANDOFF.md.tmp-*")), [])
        workspace_id_after_result = subprocess.run(
            ["git", "-C", str(self.root), "config", "--local", "--get", "codex.contextWorkspaceId"],
            capture_output=True,
            text=True,
        )
        workspace_id_after = workspace_id_after_result.stdout.strip() if workspace_id_after_result.returncode == 0 else None
        self.assertEqual(workspace_id_after, workspace_id_before)

    def _prepare_post_write_checkpoint_failure(self) -> tuple[Path, Path, bytes, bytes, list[dict[str, object]]]:
        commit_all(self.root, "post-write checkpoint failure fixture")
        initial_code, initial_message = agent_checkpoint.checkpoint(self.root, False, False)
        self.assertEqual(initial_code, 0, initial_message)
        commit_all(self.root, "checkpoint baseline")

        subprocess.run(
            ["git", "-C", str(self.root), "config", "--local", "--unset-all", "codex.contextWorkspaceId"],
            check=False,
            capture_output=True,
            text=True,
        )
        state_path = self.root / ".agents/state/PROJECT_STATE.yaml"
        handoff_path = self.root / ".agents/state/SESSION_HANDOFF.md"
        before_state = state_path.read_bytes()
        before_handoff = handoff_path.read_bytes()
        expected_history = json.loads(before_state)["checkpoint_history"]
        readme = self.root / "README.md"
        readme.write_text(readme.read_text(encoding="utf-8") + "\npost-write failure fixture change\n", encoding="utf-8")

        preflight = subprocess.run(
            [sys.executable, str(PREFLIGHT), "--repo", str(self.root), "--json"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(preflight.returncode, 0, preflight.stderr + preflight.stdout)
        self.assertTrue(json.loads(preflight.stdout)["ok"])
        return state_path, handoff_path, before_state, before_handoff, expected_history

    def _assert_post_write_failure_rolled_back(
        self,
        result: tuple[int, str],
        state_path: Path,
        handoff_path: Path,
        before_state: bytes,
        before_handoff: bytes,
        expected_history: list[dict[str, object]],
    ) -> None:
        code, message = result
        self.assertNotEqual(code, 0)
        self.assertIn("original state, handoff, and local workspace identity were restored", message)
        self.assertEqual(state_path.read_bytes(), before_state)
        self.assertEqual(handoff_path.read_bytes(), before_handoff)

        state = json.loads(state_path.read_bytes())
        self.assertEqual(state["checkpoint_history"], expected_history)
        marker = re.search(r"(?m)^<!-- checkpoint-id: ([^\s]+) -->$", handoff_path.read_text(encoding="utf-8"))
        self.assertIsNotNone(marker)
        self.assertEqual(state["last_checkpoint"]["id"], marker.group(1))
        workspace_id = subprocess.run(
            ["git", "-C", str(self.root), "config", "--local", "--get-all", "codex.contextWorkspaceId"],
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(workspace_id.returncode, 0)

        preflight = subprocess.run(
            [sys.executable, str(PREFLIGHT), "--repo", str(self.root), "--json"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(preflight.returncode, 0, preflight.stderr + preflight.stdout)
        report = json.loads(preflight.stdout)
        self.assertTrue(report["ok"], report)
        self.assertEqual(report["errors"], [])
        self.assertIn("WORKTREE_CONTENT_DRIFT", {item["code"] for item in report["warnings"]})

    def test_checkpoint_rolls_back_provisional_files_after_final_snapshot_failure(self) -> None:
        (
            state_path,
            handoff_path,
            before_state,
            before_handoff,
            expected_history,
        ) = self._prepare_post_write_checkpoint_failure()
        original_snapshot = agent_checkpoint._live_git_snapshot
        calls = 0

        def fail_final_snapshot(root: Path) -> dict[str, object]:
            nonlocal calls
            calls += 1
            if calls == 2:
                raise RuntimeError("injected final snapshot construction failure")
            return original_snapshot(root)

        with patch.object(agent_checkpoint, "_live_git_snapshot", side_effect=fail_final_snapshot):
            result = agent_checkpoint.checkpoint(self.root, False, False)

        self.assertEqual(calls, 2)
        self.assertIn("injected final snapshot construction failure", result[1])
        self._assert_post_write_failure_rolled_back(
            result, state_path, handoff_path, before_state, before_handoff, expected_history,
        )

    def test_checkpoint_rolls_back_provisional_files_after_final_size_guard_failure(self) -> None:
        (
            state_path,
            handoff_path,
            before_state,
            before_handoff,
            expected_history,
        ) = self._prepare_post_write_checkpoint_failure()
        original_snapshot = agent_checkpoint._live_git_snapshot
        calls = 0

        def expand_final_snapshot(root: Path) -> dict[str, object]:
            nonlocal calls
            calls += 1
            snapshot = original_snapshot(root)
            if calls == 2:
                snapshot["injected_expansion"] = "x" * (agent_checkpoint.MAX_CHECKPOINT_STATE_BYTES + 1)
            return snapshot

        with patch.object(agent_checkpoint, "_live_git_snapshot", side_effect=expand_final_snapshot):
            result = agent_checkpoint.checkpoint(self.root, False, False)

        self.assertEqual(calls, 2)
        self.assertIn("final workspace snapshot exceeds the PROJECT_STATE size limit", result[1])
        self._assert_post_write_failure_rolled_back(
            result, state_path, handoff_path, before_state, before_handoff, expected_history,
        )

    def test_staging_checkpoint_control_files_does_not_create_snapshot_drift(self) -> None:
        commit_all(self.root, "checkpoint control fixture")
        checkpoint = self.run_script(CHECKPOINT)
        self.assertEqual(checkpoint.returncode, 0, checkpoint.stderr + checkpoint.stdout)
        git(self.root, "add", ".agents/state/PROJECT_STATE.yaml", ".agents/state/SESSION_HANDOFF.md")

        result = self.run_script(PREFLIGHT, "--json")

        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        report = json.loads(result.stdout)
        self.assertNotIn("GIT_SNAPSHOT_DRIFT", {item["code"] for item in report["warnings"]})
        self.assertTrue(report["summary"]["git_snapshot_matches"])

    def test_tracked_content_drift_is_detected_without_a_status_path_change(self) -> None:
        commit_all(self.root, "tracked fixture")
        first = self.run_script(CHECKPOINT)
        self.assertEqual(first.returncode, 0, first.stderr + first.stdout)
        note = self.root / "README.md"
        note.write_text("tracked change one\n", encoding="utf-8")
        checkpoint = self.run_script(CHECKPOINT)
        self.assertEqual(checkpoint.returncode, 0, checkpoint.stderr + checkpoint.stdout)
        status_before_content_edit = status_entries(self.root)
        note.write_text("tracked change two\n", encoding="utf-8")
        self.assertEqual(status_entries(self.root), status_before_content_edit)

        result = self.run_script(PREFLIGHT)
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        self.assertIn("WORKTREE_CONTENT_DRIFT", result.stdout)

    def test_large_files_and_artifact_directories_are_reported_once_and_separately(self) -> None:
        (self.root / "oversized-checkpoint.bin").write_bytes(b"x" * (2 * 1024 * 1024 + 1))
        artifact = self.root / "artifacts/run-17/model.bin"
        artifact.parent.mkdir(parents=True)
        artifact.write_bytes(b"model payload")

        result = self.run_script(PREFLIGHT, "--json")
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        payload = json.loads(result.stdout)
        codes = [item["code"] for item in payload["warnings"]]
        self.assertEqual(codes.count("WORKTREE_LARGE_FILES_UNHASHED"), 1)
        summary = payload["summary"]
        self.assertIn("oversized-checkpoint.bin", summary["unhashed_large_files"])
        self.assertIn("artifacts", summary["artifact_dirs_requiring_manifest"])
        self.assertNotIn("artifacts/run-17/model.bin", summary["repo_file_hashes"])

    def test_git_ignored_zip_is_still_content_hashed(self) -> None:
        (self.root / ".gitignore").write_text("*.zip\n", encoding="utf-8")
        archive = self.root / "atari-videochess-rl-documentation-g1.zip"
        archive.write_bytes(b"documentation archive fixture")
        result = self.run_script(PREFLIGHT, "--json")
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        payload = json.loads(result.stdout)
        self.assertNotIn("documentation-g1.zip", "\n".join(payload["summary"]["live_git_status_entries"]))
        self.assertIn("atari-videochess-rl-documentation-g1.zip", payload["summary"]["repo_file_hashes"])

    def test_ignored_cache_generation_does_not_create_source_content_drift(self) -> None:
        commit_all(self.root, "cache fixture")
        checkpoint = self.run_script(CHECKPOINT)
        self.assertEqual(checkpoint.returncode, 0, checkpoint.stderr + checkpoint.stdout)
        for cache_dir in (self.root / "scripts/__pycache__", self.root / "tests/__pycache__"):
            cache_dir.mkdir(parents=True, exist_ok=True)
            (cache_dir / "generated.pyc").write_bytes(b"ordinary ignored cache output")

        result = self.run_script(PREFLIGHT, "--json")
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        report = json.loads(result.stdout)
        warning_codes = {warning["code"] for warning in report["warnings"]}
        self.assertNotIn("WORKTREE_CONTENT_DRIFT", warning_codes)
        self.assertNotIn("WORKTREE_HASH_INVENTORY_DRIFT", warning_codes)
        self.assertTrue(report["summary"]["repo_content_matches"])

    @unittest.skipIf(os.environ.get("ATARI_VIDEOCHESS_SKIP_CLONE_RECOVERY_TEST") == "1", "avoid recursive clean-clone test invocation")
    def test_clean_clone_recovers_current_committed_state_without_local_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            source = temp / "committed-state"
            clone = temp / "clean-clone"
            source.mkdir()
            git(source, "init", "-q", "-b", "main")

            inventory_path = ".agents/evidence/G1-portability-consistency-verification.md"
            record = subprocess.check_output(
                ["git", "-C", str(REPO), "show", f"HEAD:{inventory_path}"],
                text=True,
            )
            section = record.split("## Approved baseline inventory", 1)[1].split("## Explicit exclusions", 1)[0]
            approved_files = set(re.findall(r"^- `([^`]+)`$", section, flags=re.MULTILINE))
            tree_entries = subprocess.check_output(
                ["git", "-C", str(REPO), "ls-tree", "-r", "-z", "HEAD"]
            ).split(b"\0")
            file_modes = {}
            for entry in filter(None, tree_entries):
                header, raw_path = entry.split(b"\t", 1)
                mode = header.split(b" ", 1)[0].decode("ascii")
                file_modes[raw_path.decode("utf-8")] = mode
            committed_files = set(file_modes)
            self.assertGreater(len(approved_files), 20)
            self.assertTrue(approved_files <= committed_files)
            self.assertNotIn("chat_history.md", committed_files)
            self.assertEqual(
                {path for path in committed_files if path.endswith(".zip")},
                {".agents/evidence/BLK-001-diagnostic-20261015-r2.zip"},
                "Only the explicitly portable M1 diagnostic bundle may be committed as a ZIP",
            )
            self.assertNotIn("main.py", committed_files)
            baseline_files = sorted(committed_files)

            for rel in baseline_files:
                destination = source / rel
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(subprocess.check_output(["git", "-C", str(REPO), "show", f"HEAD:{rel}"]))
                if file_modes[rel] == "100755":
                    destination.chmod(0o755)

            # Some repositories deliberately commit selected files inside
            # ignored artifact/evidence paths. Recreate the actual HEAD tree
            # in this synthetic clone fixture, including those paths.
            git(source, "add", "-f", "--all")
            subprocess.run(
                ["git", "-C", str(source), "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid", "commit", "-qm", "approved baseline"],
                check=True,
                capture_output=True,
                text=True,
            )
            subprocess.run(
                ["git", "clone", "--quiet", str(source), str(clone)],
                check=True,
                capture_output=True,
                text=True,
            )

            def clone_preflight(repo: Path = clone) -> subprocess.CompletedProcess[str]:
                return subprocess.run(
                    [sys.executable, str(repo / "scripts/agent_preflight.py"), "--repo", str(repo), "--json"],
                    capture_output=True,
                    text=True,
                )

            self.assertFalse((clone / "chat_history.md").exists())
            self.assertFalse((clone / "atari-videochess-rl-documentation-g1.zip").exists())
            self.assertFalse((clone / "atari-videochess-rl-documentation-g1-finalization.zip").exists())
            self.assertFalse((clone / "main.py").exists())
            self.assertFalse((clone / "scripts/__pycache__").exists())
            self.assertFalse((clone / "tests/__pycache__").exists())

            result = clone_preflight()
            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            report = json.loads(result.stdout)
            summary = report["summary"]
            state = json.loads((clone / ".agents/state/PROJECT_STATE.yaml").read_text(encoding="utf-8"))
            backlog = json.loads((clone / ".agents/tasks/BACKLOG.yaml").read_text(encoding="utf-8"))
            tasks = {task["id"]: task for task in backlog["tasks"]}
            self.assertIsNone(agent_preflight._git_workspace_id(clone))
            self.assertEqual(summary["git_snapshot_mode"], "portable_commit_transition")
            self.assertTrue(summary["portable_baseline_matches"])
            self.assertEqual(summary["current_gate"], state["governance"]["current_gate"])
            self.assertEqual(summary["gate_status"], state["governance"]["gate_status"])
            self.assertEqual(summary["approved_gates"], state["governance"]["approved_gates"])
            requirements = (clone / "docs/01-foundation/REQUIREMENTS.md").read_text(encoding="utf-8")
            expected_approvals = sorted(set(re.findall(r"(?m)^\|\s*(O-\d{2})\s*\|", requirements)))
            self.assertEqual(summary["open_approval_ids"], expected_approvals)
            self.assertEqual(summary["next_task_id"], state["task_refs"]["next_task_id"])
            self.assertEqual(summary["next_milestone"], state["engineering"]["next_milestone"])
            self.assertEqual(summary["next_milestone_status"], state["engineering"]["next_milestone_status"])
            self.assertEqual(summary["engineering_start_authorized"], state["engineering"]["start_authorized"])
            self.assertEqual(summary["active_task_id"], state["task_refs"]["active_task_id"])
            self.assertEqual(
                summary["task_ids_by_status"],
                {
                    status: sorted(task["id"] for task in backlog["tasks"] if task["status"] == status)
                    for status in ("done", "in_progress", "pending", "blocked", "cancelled")
                },
            )
            next_task_id = state["task_refs"]["next_task_id"]
            if next_task_id is None:
                self.assertIsNone(summary["next_task_id"])
                self.assertEqual(summary["next_task_acceptance_criteria_ids"], [])
            else:
                self.assertIn(next_task_id, tasks)
                self.assertEqual(summary["next_task_status"], tasks[next_task_id]["status"])
                self.assertEqual(summary["next_task_dependencies"], tasks[next_task_id]["depends_on"])
                self.assertEqual(summary["next_task_acceptance_criteria_ids"], tasks[next_task_id]["acceptance_criteria_ids"])
            self.assertEqual(summary["next_user_action"], state["governance"]["next_user_action"])
            warning_codes = {warning["code"] for warning in report["warnings"]}
            self.assertNotIn("GIT_SNAPSHOT_DRIFT", warning_codes)
            self.assertNotIn("WORKTREE_CONTENT_DRIFT", warning_codes)
            self.assertTrue(summary["git_snapshot_matches"])
            self.assertTrue(summary["repo_content_matches"])

            clone_env = os.environ.copy()
            clone_env["ATARI_VIDEOCHESS_SKIP_CLONE_RECOVERY_TEST"] = "1"
            clone_tests = subprocess.run(
                [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-p", "test_agent_context.py", "-v"],
                cwd=clone,
                env=clone_env,
                capture_output=True,
                text=True,
            )
            self.assertEqual(clone_tests.returncode, 0, clone_tests.stdout + clone_tests.stderr)
            nested_test_output = clone_tests.stdout + clone_tests.stderr
            self.assertRegex(nested_test_output, r"Ran [1-9][0-9]* tests?")
            self.assertIn("OK", nested_test_output)

            legacy_clone = temp / "legacy-clone"
            subprocess.run(
                ["git", "clone", "--quiet", str(source), str(legacy_clone)],
                check=True,
                capture_output=True,
                text=True,
            )
            legacy_state_path = legacy_clone / ".agents/state/PROJECT_STATE.yaml"
            legacy_state = json.loads(legacy_state_path.read_text(encoding="utf-8"))
            legacy_state["last_checkpoint"].pop("portable_git", None)
            legacy_state["last_checkpoint"].pop("workspace_id", None)
            legacy_state["last_checkpoint"]["git"].pop("scope", None)
            legacy_state.pop("checkpoint_history", None)
            # This fixture intentionally models a pre-archive checkpoint. An
            # archive pointer without its inline list or archive files is a
            # malformed migrated state, not a legacy-format checkpoint.
            legacy_state.pop("checkpoint_history_archive", None)
            shutil.rmtree(legacy_clone / ".agents/state/checkpoint-history")
            legacy_git = legacy_state["last_checkpoint"]["git"]
            legacy_hashes = legacy_git.get("repo_file_hashes", {})
            legacy_head_paths = set(agent_preflight._git_head_manifest(legacy_clone, include_control_files=True)) - {".agents/state/PROJECT_STATE.yaml"}
            legacy_untracked = {
                entry[3:] for entry in legacy_git.get("status_entries", [])
                if isinstance(entry, str) and entry.startswith("?? ")
            }
            legacy_snapshot_matches = bool(legacy_head_paths) and not (legacy_head_paths & legacy_untracked) and all(
                rel in legacy_hashes
                and (legacy_clone / rel).is_file()
                and file_hash(legacy_clone / rel) == legacy_hashes[rel]
                for rel in legacy_head_paths
            )
            write_json(legacy_state_path, legacy_state)
            git(legacy_clone, "add", "-A")
            subprocess.run(
                ["git", "-C", str(legacy_clone), "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid", "commit", "-qm", "legacy checkpoint format"],
                check=True,
                capture_output=True,
                text=True,
            )
            legacy_result = clone_preflight(legacy_clone)
            self.assertEqual(legacy_result.returncode, 0, legacy_result.stderr + legacy_result.stdout)
            legacy_report = json.loads(legacy_result.stdout)
            legacy_codes = {warning["code"] for warning in legacy_report["warnings"]}
            expected_legacy_mode = (
                "legacy_portable_commit_transition"
                if legacy_snapshot_matches
                else "unverified_legacy_git_transition"
            )
            self.assertEqual(legacy_report["summary"]["git_snapshot_mode"], expected_legacy_mode)
            if legacy_snapshot_matches:
                self.assertNotIn("GIT_SNAPSHOT_DRIFT", legacy_codes)
                self.assertNotIn("WORKTREE_CONTENT_DRIFT", legacy_codes)
                self.assertTrue(legacy_report["summary"]["repo_content_matches"])
            else:
                self.assertIn("GIT_COMMIT_TRANSITION_UNVERIFIED", legacy_codes)
                self.assertFalse(legacy_report["summary"]["repo_content_matches"])

            for cache_dir in (clone / "scripts/__pycache__", clone / "tests/__pycache__"):
                cache_dir.mkdir(parents=True, exist_ok=True)
                (cache_dir / "generated.pyc").write_bytes(b"ordinary ignored cache output")
            cached = clone_preflight()
            self.assertEqual(cached.returncode, 0, cached.stderr + cached.stdout)
            cached_report = json.loads(cached.stdout)
            cached_codes = {warning["code"] for warning in cached_report["warnings"]}
            self.assertNotIn("WORKTREE_CONTENT_DRIFT", cached_codes)
            self.assertNotIn("WORKTREE_HASH_INVENTORY_DRIFT", cached_codes)
            self.assertTrue(cached_report["summary"]["repo_content_matches"])

            overview = clone / "docs/01-foundation/PROJECT_OVERVIEW.md"
            overview.write_text(overview.read_text(encoding="utf-8") + "\nTracked edit fixture.\n", encoding="utf-8")
            modified = clone_preflight()
            self.assertEqual(modified.returncode, 0, modified.stderr + modified.stdout)
            modified_report = json.loads(modified.stdout)
            modified_codes = {warning["code"] for warning in modified_report["warnings"]}
            self.assertIn("WORKTREE_CONTENT_DRIFT", modified_codes)
            self.assertFalse(modified_report["summary"]["repo_content_matches"])

    @unittest.skipIf(os.environ.get("ATARI_VIDEOCHESS_SKIP_CLONE_RECOVERY_TEST") == "1", "avoid nested historical recovery fixture")
    def test_historical_g1_recovery_matches_recorded_baseline(self) -> None:
        fixture = json.loads(G1_RECOVERY_FIXTURE.read_text(encoding="utf-8"))
        available = subprocess.run(
            ["git", "-C", str(REPO), "cat-file", "-e", f"{fixture['source_revision']}^{{commit}}"],
            capture_output=True,
        )
        if available.returncode:
            self.skipTest("the pinned G1 baseline commit is unavailable in this checkout")

        with tempfile.TemporaryDirectory() as temp_dir:
            source = Path(temp_dir) / "g1-baseline"
            clone = Path(temp_dir) / "g1-clean-clone"
            create_repo_from_revision(source, fixture["source_revision"])
            subprocess.run(["git", "clone", "--quiet", str(source), str(clone)], check=True, capture_output=True)

            result = run_preflight(clone)
            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            report = json.loads(result.stdout)
            summary = report["summary"]
            state = json.loads((clone / ".agents/state/PROJECT_STATE.yaml").read_text(encoding="utf-8"))
            backlog = json.loads((clone / ".agents/tasks/BACKLOG.yaml").read_text(encoding="utf-8"))
            tasks = {task["id"]: task for task in backlog["tasks"]}

            self.assertEqual(state["governance"]["current_gate"], fixture["governance"]["current_gate"])
            self.assertEqual(summary["current_gate"], fixture["governance"]["current_gate"])
            self.assertEqual(state["governance"]["gate_status"], fixture["governance"]["gate_status"])
            self.assertEqual(summary["approved_gates"], fixture["governance"]["approved_gates"])
            self.assertEqual(state["engineering"]["next_milestone"], fixture["engineering"]["next_milestone"])
            self.assertEqual(summary["next_milestone_status"], fixture["engineering"]["next_milestone_status"])
            self.assertEqual(summary["engineering_start_authorized"], fixture["engineering"]["start_authorized"])
            self.assertIsNone(state["engineering"]["active_milestone"])
            self.assertEqual(state["task_refs"]["next_task_id"], fixture["task_refs"]["next_task_id"])
            self.assertEqual(tasks["M0-001"]["status"], fixture["tasks"]["M0-001"]["status"])
            self.assertEqual(tasks["M0-001"]["depends_on"], fixture["tasks"]["M0-001"]["depends_on"])
            self.assertEqual(summary["open_approval_ids"], fixture["open_approval_ids"])
            self.assertTrue(summary["portable_baseline_matches"])
            self.assertTrue(summary["repo_content_matches"])

    @unittest.skipIf(os.environ.get("ATARI_VIDEOCHESS_SKIP_CLONE_RECOVERY_TEST") == "1", "avoid nested milestone transition fixture")
    def test_clean_clone_recovers_g2_and_future_milestone_transitions(self) -> None:
        def state_and_backlog(root: Path):
            state_path = root / ".agents/state/PROJECT_STATE.yaml"
            backlog_path = root / ".agents/tasks/BACKLOG.yaml"
            return (
                state_path,
                json.loads(state_path.read_text(encoding="utf-8")),
                backlog_path,
                json.loads(backlog_path.read_text(encoding="utf-8")),
            )

        def clone_and_assert(source: Path, name: str, milestone: str, milestone_status: str, authorized: bool):
            clone = source.parent / name
            subprocess.run(["git", "clone", "--quiet", str(source), str(clone)], check=True, capture_output=True)
            result = run_preflight(clone)
            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            report = json.loads(result.stdout)
            summary = report["summary"]
            state = json.loads((clone / ".agents/state/PROJECT_STATE.yaml").read_text(encoding="utf-8"))
            self.assertEqual(summary["current_gate"], state["governance"]["current_gate"])
            self.assertEqual(summary["approved_gates"], state["governance"]["approved_gates"])
            self.assertEqual(summary["next_milestone"], milestone)
            self.assertEqual(summary["next_milestone_status"], milestone_status)
            self.assertEqual(summary["engineering_start_authorized"], authorized)
            self.assertEqual(summary["next_user_action"], state["governance"]["next_user_action"])
            self.assertTrue(summary["portable_baseline_matches"])
            self.assertTrue(summary["repo_content_matches"])
            warning_codes = {warning["code"] for warning in report["warnings"]}
            self.assertNotIn("GIT_SNAPSHOT_DRIFT", warning_codes)
            self.assertNotIn("WORKTREE_CONTENT_DRIFT", warning_codes)
            return clone

        with tempfile.TemporaryDirectory() as temp_dir:
            source = Path(temp_dir) / "transition-source"
            create_repo_from_revision(source, G1_BASELINE_REVISION)

            # This is a disposable future-state fixture. It tests recorded state transitions only;
            # it does not authorize or perform any milestone work in the real repository.
            state_path, state, backlog_path, backlog = state_and_backlog(source)
            state["governance"].update({
                "current_gate": "G2",
                "gate_status": "in_progress",
                "approved_gates": ["G0", "G1"],
                "next_governance_gate": "G3",
                "next_user_action": "Review M0 results; M1 requires separate explicit authorization.",
            })
            state["engineering"].update({
                "active_milestone": None,
                "next_milestone": "M1",
                "next_milestone_status": "pending_user_approval",
                "start_authorized": False,
                "hold_reason": "M1 awaits explicit user authorization.",
            })
            state["task_refs"].update({"active_task_id": None, "next_task_id": None})
            task = next(item for item in backlog["tasks"] if item["id"] == "M0-001")
            evidence_path = ".agents/evidence/M0-future-state-fixture.md"
            (source / evidence_path).parent.mkdir(parents=True, exist_ok=True)
            (source / evidence_path).write_text("Synthetic state-transition fixture; no M0 result is asserted.\n", encoding="utf-8")
            task["status"] = "done"
            task["next_action"] = ""
            task["evidence"] = [{
                "kind": "file",
                "path": evidence_path,
                "detail": "Synthetic fixture evidence to exercise a completed M0 task state.",
                "provenance": {
                    "status": "verified",
                    "executed_at_utc": None,
                    "recorded_at_utc": "2026-10-15T00:00:00Z",
                    "exit_code": None,
                    "git_revision": git(source, "rev-parse", "HEAD"),
                    "log_path": None,
                },
            }]
            write_json(state_path, state)
            write_json(backlog_path, backlog)
            checkpoint_and_commit(source, "fixture G1 to G2 with M0 complete")
            clone_and_assert(source, "g2-clone", "M1", "pending_user_approval", False)

            state_path, state, _, _ = state_and_backlog(source)
            state["engineering"].update({
                "active_milestone": "M1",
                "next_milestone": "M1",
                "next_milestone_status": "in_progress",
                "start_authorized": True,
                "hold_reason": "",
                "start_authorization_record": {
                    "authorization_id": "fixture-m1-auth-001",
                    "task_id": "M1-001",
                    "milestone": "M1",
                    "authority": "direct_user_or_pm_instruction",
                    "authorized_at_utc": "2026-10-15T06:24:49Z",
                    "scope": "Synthetic state-transition fixture; no M1 work is performed.",
                    "evidence_path": ".agents/evidence/M1-authorization-fixture.md",
                },
            })
            state["task_refs"].update({"active_task_id": "M1-001", "next_task_id": "M1-001"})
            state["governance"]["next_user_action"] = "Complete the synthetic M1 transition before M2 review."
            auth_path = source / ".agents/evidence/M1-authorization-fixture.md"
            auth_path.parent.mkdir(parents=True, exist_ok=True)
            auth_result = "The project authority directly authorized this synthetic M1 state transition only."
            auth_path.write_text(auth_result + "\n", encoding="utf-8")
            backlog_path = source / ".agents/tasks/BACKLOG.yaml"
            backlog = json.loads(backlog_path.read_text(encoding="utf-8"))
            backlog["tasks"].append({
                "id": "M1-001", "title": "Synthetic M1 authorization transition", "milestone": "M1",
                "status": "in_progress", "next_action": "Fixture only.", "depends_on": ["M0-001"],
                "requires_user_gate_approval": None, "acceptance_criteria_ids": ["M1-01"],
                "blocker_ids": [], "evidence": [{
                    "kind": "file", "path": ".agents/evidence/M1-authorization-fixture.md",
                    "detail": "Synthetic direct authorization evidence; no milestone work is performed.",
                    "result": auth_result,
                    "provenance": {"status": "manual_verified", "executed_at_utc": "2026-10-15T06:24:49Z",
                        "recorded_at_utc": "2026-10-15T06:24:49Z", "exit_code": None,
                        "git_revision": git(source, "rev-parse", "HEAD"),
                        "log_path": ".agents/evidence/M1-authorization-fixture.md"},
                }],
            })
            write_json(state_path, state)
            write_json(backlog_path, backlog)
            checkpoint_and_commit(source, "fixture M1 active")
            clone_and_assert(source, "m1-clone", "M1", "in_progress", True)

            state_path, state, backlog_path, backlog = state_and_backlog(source)
            state["engineering"].update({
                "active_milestone": None,
                "next_milestone": "M2",
                "next_milestone_status": "pending_user_approval",
                "start_authorized": False,
                "start_authorization_record": None,
                "hold_reason": "M2 awaits explicit user authorization.",
            })
            state["task_refs"].update({"active_task_id": None, "next_task_id": None})
            backlog["tasks"] = [task for task in backlog["tasks"] if task["id"] != "M1-001"]
            state["governance"]["next_user_action"] = "Review synthetic M1 completion before authorizing M2."
            write_json(state_path, state)
            write_json(backlog_path, backlog)
            checkpoint_and_commit(source, "fixture M1 to M2")
            clone_and_assert(source, "m2-clone", "M2", "pending_user_approval", False)

    def test_preflight_reports_files_it_could_not_hash(self) -> None:
        with patch.object(agent_preflight, "_sha_file", side_effect=PermissionError("fixture read denial")):
            report = agent_preflight.build_report(self.root)
        self.assertTrue(report["ok"], report["errors"])
        self.assertIn("README.md", report["summary"]["unreadable_files"])
        self.assertIn("WORKTREE_UNREADABLE_FILES", [warning["code"] for warning in report["warnings"]])

    def test_historical_baseline_is_not_recompared_to_current_files(self) -> None:
        (self.root / "README.md").write_text("an authorized later edit\n", encoding="utf-8")

        result = self.run_script(PREFLIGHT)

        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        self.assertNotIn("BASELINE_FILE_CHANGED", result.stdout)
        self.assertIn("WORKTREE_CONTENT_DRIFT", result.stdout)

    def test_historical_baseline_checksum_detects_record_mutation(self) -> None:
        state_path = self.root / ".agents/state/PROJECT_STATE.yaml"
        state = json.loads(state_path.read_text(encoding="utf-8"))
        state["g1_baseline"]["head"] = "a" * 40
        write_json(state_path, state)
        result = self.run_script(PREFLIGHT)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("G1_BASELINE_INTEGRITY", result.stdout + result.stderr)

    def test_preflight_rejects_invalid_state_schema(self) -> None:
        (self.root / ".agents/state/PROJECT_STATE.yaml").write_text("{\"schema_version\": 99}\n", encoding="utf-8")
        result = self.run_script(PREFLIGHT)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("STATE_SCHEMA", result.stdout + result.stderr)

    def test_preflight_reports_malformed_git_snapshot_without_crashing(self) -> None:
        path = self.root / ".agents/state/PROJECT_STATE.yaml"
        state = json.loads(path.read_text(encoding="utf-8"))
        state["last_checkpoint"]["git"] = []
        write_json(path, state)
        result = self.run_script(PREFLIGHT)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("STATE_SCHEMA", result.stdout + result.stderr)
        self.assertNotIn("Traceback", result.stdout + result.stderr)

    def test_preflight_reports_malformed_task_status_without_crashing(self) -> None:
        path = self.root / ".agents/tasks/BACKLOG.yaml"
        backlog = json.loads(path.read_text(encoding="utf-8"))
        backlog["tasks"][0]["status"] = []
        write_json(path, backlog)
        result = self.run_script(PREFLIGHT)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("TASK_SCHEMA", result.stdout + result.stderr)
        self.assertNotIn("Traceback", result.stdout + result.stderr)

    def test_completed_task_must_have_empty_next_action(self) -> None:
        backlog = json.loads((REPO / ".agents/tasks/BACKLOG.yaml").read_text(encoding="utf-8"))
        state = json.loads((REPO / ".agents/state/PROJECT_STATE.yaml").read_text(encoding="utf-8"))
        task = next(item for item in backlog["tasks"] if item["id"] == "M4-001")
        task["next_action"] = "Historical completed action must be cleared."
        errors: list[dict[str, str]] = []
        acceptance_ids = agent_preflight._load_acceptance_ids(REPO, errors)
        agent_preflight._check_task_graph(backlog, REPO, state, set(), acceptance_ids, errors)
        matching = [item for item in errors if item["code"] == "TASK_SCHEMA" and "empty next_action" in item["message"]]
        self.assertEqual(len(matching), 1)

    def test_pr_review_policy_explicitly_separates_codex_and_pm_authority(self) -> None:
        policy_path = REPO / "docs/02-management/PR_REVIEW_AND_INTEGRATION.md"
        text = policy_path.read_text(encoding="utf-8")
        for required in (
            "Codex implements",
            "Codex verifies",
            "Codex opens",
            "PM independently reviews",
            "authorized human/operator",
            "must not merge",
            "green CI",
        ):
            with self.subTest(required=required):
                self.assertIn(required, text)


    def test_context_ci_runs_m5_fixture_as_a_contract_oracle(self) -> None:
        workflow = (REPO / ".github/workflows/preflight.yml").read_text(encoding="utf-8")
        self.assertIn("tests.test_m5_contract_fixtures", workflow)
        self.assertIn("not a DDQN learner test", (REPO / "tests/test_m5_contract_fixtures.py").read_text(encoding="utf-8"))

    def test_m0_cannot_be_authorized_before_g1_approval(self) -> None:
        path = self.root / ".agents/state/PROJECT_STATE.yaml"
        state = json.loads(path.read_text(encoding="utf-8"))
        state["engineering"]["start_authorized"] = True
        write_json(path, state)
        result = self.run_script(PREFLIGHT)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("STATE_SCHEMA", result.stdout + result.stderr)

    def test_preflight_detects_gate_coverage_used_as_its_own_start_prerequisite(self) -> None:
        coverage = agent_preflight._load_gate_milestone_coverage(self.root)
        self.assertEqual(coverage["G3"], {"M2", "M3", "M4", "M5"})
        self.assertEqual(coverage["G4"], {"M6", "M7"})
        self.assertEqual(agent_preflight._load_m7_gate_criteria(REPO), {
            "G4": {"M7-01", "M7-02", "M7-03"},
            "G5": {"M7-04", "M7-05"},
        })

        for milestone, gate in (("M3", "G3"), ("M4", "G3"), ("M5", "G3"), ("M6", "G4")):
            with self.subTest(milestone=milestone, gate=gate):
                task_id = f"{milestone}-001"
                backlog = {
                    "format": "JSON-compatible YAML 1.2", "schema_version": 2,
                    "project_id": "atari-videochess-rl", "tasks": [{
                        "id": task_id, "title": "Fixture", "milestone": milestone,
                        "status": "pending", "next_action": "Await explicit authorization.",
                        "depends_on": [], "requires_user_gate_approval": gate,
                        "acceptance_criteria_ids": ["M3-01"], "blocker_ids": [], "evidence": [],
                    }],
                }
                state = {"task_refs": {"active_task_id": None, "next_task_id": task_id}}
                errors: list[dict[str, str]] = []
                agent_preflight._check_task_graph(backlog, self.root, state, set(), {"M3-01"}, errors)
                self.assertIn("TASK_GATE_CIRCULAR", {item["code"] for item in errors})

        for gate, criterion, should_be_circular in (
            ("G4", "M7-01", True), ("G5", "M7-04", True), ("G4", "M7-04", False),
        ):
            with self.subTest(milestone="M7", gate=gate, criterion=criterion):
                task = {
                    "id": "M7-001", "title": "Fixture", "milestone": "M7",
                    "status": "pending", "next_action": "Await upstream gate if required.",
                    "depends_on": [], "requires_user_gate_approval": gate,
                    "acceptance_criteria_ids": [criterion], "blocker_ids": [], "evidence": [],
                }
                backlog = {"format": "JSON-compatible YAML 1.2", "schema_version": 2,
                    "project_id": "atari-videochess-rl", "tasks": [task]}
                errors: list[dict[str, str]] = []
                agent_preflight._check_task_graph(
                    backlog, REPO, {"task_refs": {"active_task_id": None, "next_task_id": "M7-001"}},
                    set(), {criterion}, errors,
                )
                is_circular = "TASK_GATE_CIRCULAR" in {item["code"] for item in errors}
                self.assertEqual(is_circular, should_be_circular)

        with tempfile.TemporaryDirectory() as temp_dir:
            incomplete_root = Path(temp_dir)
            adr_path = incomplete_root / "docs/02-management/decisions/ADR-0001-governance-crosswalk-and-file-priorities.md"
            adr_path.parent.mkdir(parents=True, exist_ok=True)
            adr_path.write_text((REPO / adr_path.relative_to(incomplete_root)).read_text(encoding="utf-8"), encoding="utf-8")
            task = {
                "id": "M7-001", "title": "Fixture", "milestone": "M7",
                "status": "pending", "next_action": "Await criterion allocation.",
                "depends_on": [], "requires_user_gate_approval": "G4",
                "acceptance_criteria_ids": ["M7-01"], "blocker_ids": [], "evidence": [],
            }
            errors: list[dict[str, str]] = []
            agent_preflight._check_task_graph(
                {"format": "JSON-compatible YAML 1.2", "schema_version": 2,
                    "project_id": "atari-videochess-rl", "tasks": [task]},
                incomplete_root, {"task_refs": {"active_task_id": None, "next_task_id": "M7-001"}},
                set(), {"M7-01"}, errors,
            )
            self.assertIn("GATE_ACCEPTANCE_COVERAGE_UNRESOLVED", {item["code"] for item in errors})

    def test_m3_authorization_does_not_change_governance_approvals(self) -> None:
        state = json.loads((REPO / ".agents/state/PROJECT_STATE.yaml").read_text(encoding="utf-8"))
        approved_gates_before = list(state["governance"]["approved_gates"])
        state["engineering"].update({
            "active_milestone": "M3", "next_milestone": "M3",
            "next_milestone_status": "in_progress", "start_authorized": True,
            "hold_reason": "",
            "start_authorization_record": {
                "authorization_id": "test-m3-auth-001", "task_id": "M3-001",
                "milestone": "M3", "authority": "direct_user_or_pm_instruction",
                "authorized_at_utc": "2026-10-17T00:00:00Z", "scope": "Synthetic authorization fixture only.",
                "evidence_path": ".agents/evidence/M3-authorization-fixture.md",
            },
        })
        state["task_refs"].update({"active_task_id": "M3-001", "next_task_id": "M3-001"})
        task = {
            "id": "M3-001", "title": "Fixture", "milestone": "M3",
            "status": "in_progress", "next_action": "Continue explicitly authorized fixture work.",
            "depends_on": [], "requires_user_gate_approval": None,
            "acceptance_criteria_ids": ["M3-01"], "blocker_ids": [], "evidence": [{
                "kind": "file", "path": ".agents/evidence/M3-authorization-fixture.md",
                "detail": "Synthetic direct authorization evidence for preflight behavior only.",
                "result": "The project authority directly authorized this synthetic M3 fixture.",
                "provenance": {"status": "manual_verified", "executed_at_utc": "2026-10-17T00:00:00Z",
                    "recorded_at_utc": "2026-10-17T00:00:00Z", "exit_code": None,
                    "git_revision": "a" * 40, "log_path": ".agents/evidence/M3-authorization-fixture.md"},
            }],
        }
        backlog = {
            "format": "JSON-compatible YAML 1.2", "schema_version": 2,
            "project_id": "atari-videochess-rl", "tasks": [task],
        }
        evidence_path = self.root / ".agents/evidence/M3-authorization-fixture.md"
        evidence_path.parent.mkdir(parents=True, exist_ok=True)
        evidence_path.write_text(task["evidence"][0]["result"] + "\n", encoding="utf-8")
        errors: list[dict[str, str]] = []
        agent_preflight._validate_state(state, errors)
        agent_preflight._check_task_graph(
            backlog, self.root, state, set(), {"M3-01"}, errors,
        )
        self.assertEqual(errors, [])
        self.assertEqual(state["governance"]["approved_gates"], approved_gates_before)

    def test_m4_authorization_can_be_ready_without_claiming_implementation_started(self) -> None:
        state = json.loads((REPO / ".agents/state/PROJECT_STATE.yaml").read_text(encoding="utf-8"))
        approved_gates_before = list(state["governance"]["approved_gates"])
        state["engineering"].update({
            "active_milestone": None, "next_milestone": "M4",
            "next_milestone_status": "ready_to_start", "start_authorized": True,
            "hold_reason": "",
            "start_authorization_record": {
                "authorization_id": "M4-001-owner-20261027", "task_id": "M4-001",
                "milestone": "M4", "authority": "direct_user_or_pm_instruction",
                "authorized_at_utc": "2026-10-27T10:26:30Z",
                "scope": "Synthetic authorization fixture only; no implementation is started.",
                "evidence_path": ".agents/evidence/M4-authorization-fixture.md",
            },
        })
        state["task_refs"].update({"active_task_id": None, "next_task_id": "M4-001"})
        result = "The project owner directly authorized M4-001 for this synthetic fixture."
        task = {
            "id": "M4-001", "title": "Fixture", "milestone": "M4",
            "status": "pending", "next_action": "Begin only when the executor starts the task.",
            "depends_on": [], "requires_user_gate_approval": None,
            "acceptance_criteria_ids": ["M4-01"], "blocker_ids": [], "evidence": [{
                "kind": "file", "path": ".agents/evidence/M4-authorization-fixture.md",
                "detail": "Synthetic direct authorization evidence for ready_to_start validation.",
                "result": result,
                "provenance": {"status": "manual_verified", "executed_at_utc": "2026-10-27T10:26:30Z",
                    "recorded_at_utc": "2026-10-27T10:26:30Z", "exit_code": None,
                    "git_revision": "a" * 40, "log_path": ".agents/evidence/M4-authorization-fixture.md"},
            }],
        }
        backlog = {
            "format": "JSON-compatible YAML 1.2", "schema_version": 2,
            "project_id": "atari-videochess-rl", "tasks": [task],
        }
        evidence_path = self.root / ".agents/evidence/M4-authorization-fixture.md"
        evidence_path.parent.mkdir(parents=True, exist_ok=True)
        evidence_path.write_text(result + "\n", encoding="utf-8")
        errors: list[dict[str, str]] = []
        agent_preflight._validate_state(state, errors)
        agent_preflight._check_task_graph(backlog, self.root, state, set(), {"M4-01"}, errors)
        self.assertEqual(errors, [])
        self.assertEqual(task["status"], "pending")
        self.assertIsNone(state["engineering"]["active_milestone"])
        self.assertEqual(state["governance"]["approved_gates"], approved_gates_before)

    def test_g3_approval_does_not_implicitly_authorize_m6(self) -> None:
        state = json.loads((REPO / ".agents/state/PROJECT_STATE.yaml").read_text(encoding="utf-8"))
        backlog = json.loads((REPO / ".agents/tasks/BACKLOG.yaml").read_text(encoding="utf-8"))
        self.assertEqual(state["governance"]["current_gate"], "G3")
        self.assertEqual(state["governance"]["gate_status"], "approved")
        self.assertIn("G3", state["governance"]["approved_gates"])
        self.assertEqual(state["governance"]["next_governance_gate"], "G4")
        self.assertIsNone(state["engineering"]["active_milestone"])
        self.assertEqual(state["engineering"]["next_milestone"], "M6")
        self.assertEqual(state["engineering"]["next_milestone_status"], "pending_user_approval")
        self.assertFalse(state["engineering"]["start_authorized"])
        self.assertIsNone(state["task_refs"]["active_task_id"])
        self.assertNotIn("M6-001", {task["id"] for task in backlog["tasks"]})
        report = agent_preflight.build_report(REPO)
        self.assertTrue(report["ok"], report["errors"])

    def test_start_authorized_boolean_without_direct_record_is_rejected(self) -> None:
        state = json.loads((REPO / ".agents/state/PROJECT_STATE.yaml").read_text(encoding="utf-8"))
        state["engineering"].pop("start_authorization_record", None)
        state["engineering"].update({
            "active_milestone": "M3", "next_milestone": "M3",
            "next_milestone_status": "in_progress", "start_authorized": True,
            "hold_reason": "",
        })
        errors: list[dict[str, str]] = []
        agent_preflight._validate_state(state, errors)
        self.assertIn("MILESTONE_AUTHORIZATION_EVIDENCE", {item["code"] for item in errors})

    def test_direct_m3_authorization_is_preserved_across_milestone_completion(self) -> None:
        state = json.loads((REPO / ".agents/state/PROJECT_STATE.yaml").read_text(encoding="utf-8"))
        approved_gates_before = list(state["governance"]["approved_gates"])
        backlog = json.loads((REPO / ".agents/tasks/BACKLOG.yaml").read_text(encoding="utf-8"))
        m3 = next(task for task in backlog["tasks"] if task["id"] == "M3-001")
        authorization_id = "M3-001-owner-20261020"
        self.assertTrue((REPO / ".agents/evidence/M3-authorization-20261020.md").is_file())
        self.assertTrue(any(
            item.get("path") == ".agents/evidence/M3-authorization-20261020.md"
            and item.get("provenance", {}).get("status") == "manual_verified"
            for item in m3["evidence"]
        ))
        engineering = state["engineering"]
        if m3["status"] == "in_progress":
            self.assertEqual(engineering["next_milestone"], "M3")
            self.assertTrue(engineering["start_authorized"])
            self.assertEqual(engineering["next_milestone_status"], "in_progress")
            authorization = engineering["start_authorization_record"]
            self.assertEqual(authorization["authorization_id"], authorization_id)
            self.assertEqual(authorization["task_id"], "M3-001")
        elif m3["status"] == "done":
            m4 = next(task for task in backlog["tasks"] if task["id"] == "M4-001")
            self.assertIn(m4["status"], {"pending", "in_progress", "blocked", "done"})
            self.assertTrue(any(
                item.get("path") == ".agents/evidence/M3-acceptance-20261021.md"
                and item.get("provenance", {}).get("status") == "manual_verified"
                for item in m3["evidence"]
            ))
            self.assertTrue((REPO / ".agents/evidence/M3-acceptance-20261021.md").is_file())
            if m4["status"] == "pending":
                self.assertEqual(engineering["next_milestone"], "M4")
                self.assertIsNone(engineering["active_milestone"])
                self.assertEqual(engineering["next_milestone_status"], "ready_to_start")
                self.assertTrue(engineering["start_authorized"])
                self.assertIsNone(state["task_refs"]["active_task_id"])
                self.assertEqual(state["task_refs"]["next_task_id"], "M4-001")
                self.assertEqual(engineering["start_authorization_record"]["task_id"], "M4-001")
            elif m4["status"] == "in_progress":
                self.assertEqual(engineering["active_milestone"], "M4")
                self.assertEqual(state["task_refs"]["active_task_id"], "M4-001")
                self.assertEqual(state["task_refs"]["next_task_id"], "M4-001")
                self.assertEqual(engineering["start_authorization_record"]["task_id"], "M4-001")
            elif m4["status"] == "blocked":
                self.assertEqual(engineering["active_milestone"], "M4")
                self.assertEqual(engineering["next_milestone_status"], "blocked")
                self.assertEqual(state["task_refs"]["active_task_id"], "M4-001")
                self.assertEqual(state["task_refs"]["next_task_id"], "M4-001")
                self.assertTrue(m4["blocker_ids"])
                self.assertEqual(state["active_blocker_ids"], m4["blocker_ids"])
                self.assertEqual(engineering["start_authorization_record"]["task_id"], "M4-001")
            else:
                self.assertNotEqual(engineering["active_milestone"], "M4")
                self.assertNotEqual(state["task_refs"]["active_task_id"], "M4-001")
        else:
            self.fail(f"Unexpected M3 status: {m3['status']}")
        self.assertEqual(state["governance"]["approved_gates"], approved_gates_before)
        report = agent_preflight.build_report(REPO)
        self.assertTrue(report["ok"], report["errors"])
        self.assertEqual(report["summary"]["engineering_start_authorized"], engineering["start_authorized"])

    def test_g1_cannot_be_ready_with_incomplete_g1_tasks(self) -> None:
        path = self.root / ".agents/state/PROJECT_STATE.yaml"
        state = json.loads(path.read_text(encoding="utf-8"))
        state["governance"]["gate_status"] = "ready_for_user_review"
        write_json(path, state)
        backlog_path = self.root / ".agents/tasks/BACKLOG.yaml"
        backlog = json.loads(backlog_path.read_text(encoding="utf-8"))
        backlog["tasks"].append({
            "id": "G1-002", "title": "Pending G1 work", "milestone": "G1", "status": "pending",
            "next_action": "Complete G1 evidence.",
            "depends_on": ["G1-001"], "requires_user_gate_approval": None,
            "acceptance_criteria_ids": ["G1-02"], "blocker_ids": [], "evidence": []
        })
        write_json(backlog_path, backlog)
        result = self.run_script(PREFLIGHT)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("G1_REVIEW_INCOMPLETE", result.stdout + result.stderr)

    def test_preflight_finds_broken_markdown_link(self) -> None:
        (self.root / "AGENTS.md").write_text("[missing](absent.md)\n", encoding="utf-8")
        result = self.run_script(PREFLIGHT)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("LINK_BROKEN", result.stdout + result.stderr)

    def test_preflight_detects_roadmap_source_mismatch(self) -> None:
        path = self.root / "docs/01-foundation/ROADMAP.md"
        path.write_text(path.read_text(encoding="utf-8") + "\nchanged\n", encoding="utf-8")
        result = self.run_script(PREFLIGHT)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("ROADMAP_SOURCE_MISMATCH", result.stdout + result.stderr)

    def test_preflight_rejects_dependency_cycle(self) -> None:
        path = self.root / ".agents/tasks/BACKLOG.yaml"
        backlog = json.loads(path.read_text(encoding="utf-8"))
        backlog["tasks"][0]["depends_on"] = ["M0-001"]
        write_json(path, backlog)
        result = self.run_script(PREFLIGHT)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("DEPENDENCY_CYCLE", result.stdout + result.stderr)

    def test_blocked_task_must_reference_an_active_blocker(self) -> None:
        path = self.root / ".agents/tasks/BACKLOG.yaml"
        backlog = json.loads(path.read_text(encoding="utf-8"))
        backlog["tasks"][1]["status"] = "blocked"
        backlog["tasks"][1]["blocker_ids"] = ["BLK-999"]
        write_json(path, backlog)
        result = self.run_script(PREFLIGHT)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("TASK_BLOCKER_MISMATCH", result.stdout + result.stderr)

    def test_state_blocker_index_must_match_active_blocker_records(self) -> None:
        path = self.root / ".agents/tasks/BACKLOG.yaml"
        backlog = json.loads(path.read_text(encoding="utf-8"))
        backlog["tasks"][1]["status"] = "blocked"
        backlog["tasks"][1]["blocker_ids"] = ["BLK-001"]
        write_json(path, backlog)
        blocker_path = self.root / ".agents/state/BLOCKERS.md"
        blocker_path.write_text("# Active Blockers\n## BLK-001 — Fixture blocker\n- **Status:** `active`\n", encoding="utf-8")
        result = self.run_script(PREFLIGHT)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("BLOCKER_STATE_MISMATCH", result.stdout + result.stderr)

    def test_preflight_reports_dirty_worktree_and_checkpoint_refreshes_it(self) -> None:
        (self.root / "operator-note.txt").write_text("preserve me\n", encoding="utf-8")
        backlog_before = (self.root / ".agents/tasks/BACKLOG.yaml").read_bytes()
        before = self.run_script(PREFLIGHT)
        self.assertEqual(before.returncode, 0, before.stderr + before.stdout)
        self.assertIn("GIT_SNAPSHOT_DRIFT", before.stdout)
        checkpoint = self.run_script(CHECKPOINT)
        self.assertEqual(checkpoint.returncode, 0, checkpoint.stderr + checkpoint.stdout)
        self.assertTrue((self.root / "operator-note.txt").is_file())
        self.assertEqual((self.root / ".agents/tasks/BACKLOG.yaml").read_bytes(), backlog_before)
        after = self.run_script(PREFLIGHT)
        self.assertEqual(after.returncode, 0, after.stderr + after.stdout)
        self.assertNotIn("GIT_SNAPSHOT_DRIFT", after.stdout)

    def test_preflight_detects_content_change_inside_existing_dirty_path(self) -> None:
        note = self.root / "operator-note.txt"
        note.write_text("initial\n", encoding="utf-8")
        first_checkpoint = self.run_script(CHECKPOINT)
        self.assertEqual(first_checkpoint.returncode, 0, first_checkpoint.stderr + first_checkpoint.stdout)
        note.write_text("changed without changing the Git status path\n", encoding="utf-8")
        before = self.run_script(PREFLIGHT)
        self.assertEqual(before.returncode, 0, before.stderr + before.stdout)
        self.assertIn("WORKTREE_CONTENT_DRIFT", before.stdout)
        second_checkpoint = self.run_script(CHECKPOINT)
        self.assertEqual(second_checkpoint.returncode, 0, second_checkpoint.stderr + second_checkpoint.stdout)
        after = self.run_script(PREFLIGHT)
        self.assertEqual(after.returncode, 0, after.stderr + after.stdout)
        self.assertNotIn("WORKTREE_CONTENT_DRIFT", after.stdout)

    def test_checkpoint_repairs_stale_handoff_pointer(self) -> None:
        handoff = self.root / ".agents/state/SESSION_HANDOFF.md"
        handoff.write_text("<!-- checkpoint-id: stale-id -->\n# Handoff\n", encoding="utf-8")
        before = self.run_script(PREFLIGHT)
        self.assertIn("HANDOFF_STALE", before.stdout)
        checkpoint = self.run_script(CHECKPOINT)
        self.assertEqual(checkpoint.returncode, 0, checkpoint.stderr + checkpoint.stdout)
        state = json.loads((self.root / ".agents/state/PROJECT_STATE.yaml").read_text(encoding="utf-8"))
        self.assertNotIn("chat_history.md", state["last_checkpoint"]["git"]["repo_file_hashes"])
        self.assertNotIn(".env", state["last_checkpoint"]["git"]["repo_file_hashes"])
        after = self.run_script(PREFLIGHT)
        self.assertEqual(after.returncode, 0, after.stderr + after.stdout)
        self.assertNotIn("HANDOFF_STALE", after.stdout)

    def test_partial_state_file_is_detected_and_recovered(self) -> None:
        partial = self.root / ".agents/state/.PROJECT_STATE.yaml.tmp-interrupted"
        partial.write_text("{partial", encoding="utf-8")
        old = time.time() - 7200
        os.utime(partial, (old, old))
        before = self.run_script(PREFLIGHT)
        self.assertIn("PARTIAL_WRITE", before.stdout)
        checkpoint = self.run_script(CHECKPOINT, "--recover-partials")
        self.assertEqual(checkpoint.returncode, 0, checkpoint.stderr + checkpoint.stdout)
        self.assertFalse(partial.exists())
        after = self.run_script(PREFLIGHT)
        self.assertEqual(after.returncode, 0, after.stderr + after.stdout)
        self.assertNotIn("PARTIAL_WRITE", after.stdout)

    def test_completed_task_requires_existing_evidence(self) -> None:
        path = self.root / ".agents/tasks/BACKLOG.yaml"
        backlog = json.loads(path.read_text(encoding="utf-8"))
        backlog["tasks"][0]["evidence"] = [{"kind": "file", "path": "missing-evidence.txt", "detail": "absent"}]
        write_json(path, backlog)
        result = self.run_script(PREFLIGHT)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("TASK_EVIDENCE_MISSING", result.stdout + result.stderr)

    def test_verified_command_evidence_requires_timestamp_revision_exit_and_log(self) -> None:
        path = self.root / ".agents/tasks/BACKLOG.yaml"
        backlog = json.loads(path.read_text(encoding="utf-8"))
        backlog["tasks"][0]["evidence"] = [{
            "kind": "command", "command": "python3 -m unittest", "result": "PASS",
            "provenance": {
                "status": "verified", "recorded_at_utc": None, "exit_code": None,
                "git_revision": None, "log_path": None
            }
        }]
        write_json(path, backlog)
        result = self.run_script(PREFLIGHT)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("TASK_EVIDENCE_PROVENANCE", result.stdout + result.stderr)

    def test_verified_command_evidence_with_provenance_passes(self) -> None:
        path = self.root / ".agents/tasks/BACKLOG.yaml"
        backlog = json.loads(path.read_text(encoding="utf-8"))
        log = self.root / "test-output.log"
        log.write_text("Command: python3 -m unittest\nResult: PASS: 1 test.\nExit code: 0\n", encoding="utf-8")
        backlog["tasks"][0]["evidence"] = [{
            "kind": "command", "command": "python3 -m unittest", "result": "PASS: 1 test.",
            "provenance": {
                "status": "verified", "executed_at_utc": "2026-10-14T00:00:00Z",
                "recorded_at_utc": "2026-10-14T00:00:01Z", "exit_code": 0,
                "git_revision": git(self.root, "rev-parse", "HEAD"), "log_path": "test-output.log"
            }
        }]
        write_json(path, backlog)
        result = self.run_script(PREFLIGHT, "--json")
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)

    def test_m5_verified_command_log_must_be_tracked_for_clean_clone(self) -> None:
        backlog_path = self.root / ".agents/tasks/BACKLOG.yaml"
        backlog = json.loads(backlog_path.read_text(encoding="utf-8"))
        task = backlog["tasks"][0]
        task.update({"id": "M5-001", "milestone": "M5", "status": "in_progress",
                     "next_action": "Fixture only.", "acceptance_criteria_ids": ["M5-01"]})
        log_rel = ".agents/evidence/logs/M5-fixture.log"
        log = self.root / log_rel
        log.parent.mkdir(parents=True, exist_ok=True)
        command = "python3 -m unittest"
        result_text = "PASS: fixture command."
        log.write_text(f"{command}\n{result_text}\nExit code: 0\n", encoding="utf-8")
        task["evidence"] = [{
            "kind": "command", "command": command, "result": result_text,
            "provenance": {
                "status": "verified", "executed_at_utc": "2026-10-30T00:00:00Z",
                "recorded_at_utc": "2026-10-30T00:00:01Z", "exit_code": 0,
                "git_revision": git(self.root, "rev-parse", "HEAD"), "log_path": log_rel,
            },
        }]
        write_json(backlog_path, backlog)

        untracked = self.run_script(PREFLIGHT, "--json")
        self.assertIn("TASK_EVIDENCE_LOG_UNTRACKED", untracked.stdout + untracked.stderr)

        git(self.root, "add", "--", log_rel)
        tracked = self.run_script(PREFLIGHT, "--json")
        self.assertNotIn("TASK_EVIDENCE_LOG_UNTRACKED", tracked.stdout + tracked.stderr)

    def test_verified_command_evidence_must_match_retained_log(self) -> None:
        path = self.root / ".agents/tasks/BACKLOG.yaml"
        backlog = json.loads(path.read_text(encoding="utf-8"))
        (self.root / "test-output.log").write_text("Command: another command\nResult: stale output\nExit code: 0\n", encoding="utf-8")
        backlog["tasks"][0]["evidence"] = [{
            "kind": "command", "command": "python3 -m unittest", "result": "PASS: 1 test.",
            "provenance": {
                "status": "verified", "executed_at_utc": "2026-10-14T00:00:00Z",
                "recorded_at_utc": "2026-10-14T00:00:01Z", "exit_code": 0,
                "git_revision": git(self.root, "rev-parse", "HEAD"), "log_path": "test-output.log"
            }
        }]
        write_json(path, backlog)
        result = self.run_script(PREFLIGHT)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("TASK_EVIDENCE_LOG_MISMATCH", result.stdout + result.stderr)

    def test_manual_session_evidence_requires_sanitized_record_and_revision(self) -> None:
        path = self.root / ".agents/tasks/BACKLOG.yaml"
        backlog = json.loads(path.read_text(encoding="utf-8"))
        manual_log = self.root / ".agents/evidence/manual-recovery.md"
        manual_log.parent.mkdir(parents=True, exist_ok=True)
        manual_log.write_text("Result: Independent session recovered the required state.\n", encoding="utf-8")
        backlog["tasks"][0]["evidence"] = [{
            "kind": "finding", "finding_id": "G1-10", "result": "Independent session recovered the required state.",
            "provenance": {
                "status": "manual_verified", "executed_at_utc": "2026-10-14T00:00:00Z",
                "recorded_at_utc": "2026-10-14T00:00:01Z", "exit_code": None,
                "git_revision": git(self.root, "rev-parse", "HEAD"), "log_path": ".agents/evidence/manual-recovery.md"
            }
        }]
        write_json(path, backlog)
        result = self.run_script(PREFLIGHT, "--json")
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)

    def test_done_task_cannot_rely_only_on_historical_unverified_evidence(self) -> None:
        path = self.root / ".agents/tasks/BACKLOG.yaml"
        backlog = json.loads(path.read_text(encoding="utf-8"))
        backlog["tasks"][0]["evidence"][0]["provenance"]["status"] = "historical_unverified"
        backlog["tasks"][0]["evidence"][0]["provenance"].update({
            "executed_at_utc": None, "recorded_at_utc": None, "git_revision": None
        })
        write_json(path, backlog)
        result = self.run_script(PREFLIGHT)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("TASK_EVIDENCE_UNVERIFIED", result.stdout + result.stderr)

    def test_json_output_is_machine_readable_and_paths_are_portable(self) -> None:
        result = self.run_script(PREFLIGHT, "--json")
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        payload = json.loads(result.stdout)
        state = json.loads((self.root / ".agents/state/PROJECT_STATE.yaml").read_text(encoding="utf-8"))
        self.assertEqual(payload["summary"]["current_gate"], state["governance"]["current_gate"])
        state_text = (self.root / ".agents/state/PROJECT_STATE.yaml").read_text(encoding="utf-8")
        self.assertNotIn(str(self.root), state_text)

    def test_project_context_can_be_recovered_without_chat_history(self) -> None:
        overview = (REPO / "docs/01-foundation/PROJECT_OVERVIEW.md").read_text(encoding="utf-8")
        requirements = (REPO / "docs/01-foundation/REQUIREMENTS.md").read_text(encoding="utf-8")
        self.assertIn("ALE `VideoChess-v5`", overview)
        self.assertIn("Supervised pretraining", overview)
        self.assertIn("Simulator RL", overview)
        self.assertIn("Atari evaluation", overview)
        self.assertIn("must not be part of the agent's inference path", requirements)
        self.assertIn("O-01", requirements)
        self.assertIn("O-08", requirements)
        state = json.loads((REPO / ".agents/state/PROJECT_STATE.yaml").read_text(encoding="utf-8"))
        backlog = json.loads((REPO / ".agents/tasks/BACKLOG.yaml").read_text(encoding="utf-8"))
        result = subprocess.run([sys.executable, str(PREFLIGHT), "--repo", str(REPO), "--json"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        report = json.loads(result.stdout)
        summary = report["summary"]
        self.assertEqual(summary["current_gate"], state["governance"]["current_gate"])
        self.assertEqual(summary["next_task_id"], state["task_refs"]["next_task_id"])
        self.assertEqual(summary["next_milestone"], state["engineering"]["next_milestone"])
        self.assertEqual(summary["next_milestone_status"], state["engineering"]["next_milestone_status"])
        self.assertEqual(summary["engineering_start_authorized"], state["engineering"]["start_authorized"])
        self.assertEqual(summary["next_user_action"], state["governance"]["next_user_action"])
        next_task_id = state["task_refs"]["next_task_id"]
        if next_task_id is None:
            self.assertIsNone(summary["next_task_id"])
            self.assertEqual(summary["next_task_acceptance_criteria_ids"], [])
        else:
            next_task = next(task for task in backlog["tasks"] if task["id"] == next_task_id)
            self.assertEqual(summary["next_task_acceptance_criteria_ids"], next_task["acceptance_criteria_ids"])
        self.assertEqual(summary["task_ids_by_status"]["done"], sorted(task["id"] for task in backlog["tasks"] if task["status"] == "done"))
        self.assertEqual(summary["open_approval_ids"], [f"O-{index:02d}" for index in range(2, 9)])
        self.assertNotIn("O-01", summary["open_approval_ids"])
        self.assertIn("docs/02-management/decisions/ADR-0001-governance-crosswalk-and-file-priorities.md", summary["decision_refs"])
        self.assertTrue(summary["roadmap_source"]["matches"])
        self.assertTrue(summary["git_snapshot_matches"])
        self.assertTrue(
            summary["workspace_snapshot_matches"]
            or summary["git_snapshot_mode"] in {"portable_commit_transition", "legacy_portable_commit_transition"}
        )
        self.assertEqual(len(summary["task_ids_by_status"]["done"]), sum(1 for task in backlog["tasks"] if task["status"] == "done"))


if __name__ == "__main__":
    unittest.main()
