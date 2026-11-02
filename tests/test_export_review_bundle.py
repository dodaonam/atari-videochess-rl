import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch


REPO_ROOT = Path(__file__).resolve().parents[1]
EXPORTER = REPO_ROOT / "scripts" / "export_review_bundle.py"
sys.path.insert(0, str(REPO_ROOT / "scripts"))
import export_review_bundle as exporter_module


def run_git(repo, *args, check=True):
    result = subprocess.run(
        ["git", *args], cwd=repo, text=True, capture_output=True, check=False
    )
    if check and result.returncode:
        raise AssertionError(f"git {args!r} failed: {result.stderr}")
    return result


class ExportReviewBundleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.repo = Path(self.temp.name) / "repo"
        self.repo.mkdir()
        run_git(self.repo, "init", "-q")
        run_git(self.repo, "config", "user.email", "review@example.invalid")
        run_git(self.repo, "config", "user.name", "Review Test")
        self.write_fixture()
        run_git(self.repo, "add", ".")
        run_git(self.repo, "commit", "-qm", "baseline")
        self.head = run_git(self.repo, "rev-parse", "HEAD").stdout.strip()
        self.output = self.repo / ".agents" / "review-bundles"

    def tearDown(self):
        self.temp.cleanup()

    def write(self, relative, content):
        path = self.repo / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def write_fixture(self):
        files = {
            ".gitignore": "/.agents/review-bundles/\n__pycache__/\n*.env\n",
            "AGENTS.md": "# Agent rules\nRead canonical state before reviews.\n",
            "README.md": "# Fixture project\n",
            "docs/01-foundation/REQUIREMENTS.md": "# Requirements\nFixture objective.\n\n## Open approvals\n| O-01 | Open assignment question |\n| O-02 | Open data question |\n\n## Later section\nHistorical O-99 is closed.\n",
            "docs/01-foundation/PROJECT_OVERVIEW.md": "# Overview\n",
            "docs/01-foundation/ROADMAP.md": "# Roadmap\n",
            "docs/02-management/EXECUTION_PLAN.md": "# Execution plan\n",
            "docs/02-management/decisions/ADR-0001-governance-crosswalk-and-file-priorities.md": "# Accepted decision\n",
            "docs/06-quality/ACCEPTANCE_CRITERIA.md": "# Acceptance\nM0-01\n",
            "docs/06-quality/TEST_STRATEGY.md": "# Test strategy\n",
            ".agents/state/PROJECT_STATE.yaml": json.dumps(
                {
                    "project_id": "fixture",
                    "governance": {
                        "current_gate": "G2",
                        "gate_status": "in_progress",
                        "approved_gates": ["G0", "G1"],
                        "next_user_action": "Review M0",
                    },
                    "engineering": {
                        "active_milestone": "M0",
                        "next_milestone": "M1",
                        "next_milestone_status": "pending_user_approval",
                        "start_authorized": False,
                    },
                    "active_blocker_ids": [],
                }
            ),
            ".agents/state/SESSION_HANDOFF.md": "# Handoff\nUse the state and backlog.\n",
            ".agents/state/BLOCKERS.md": "# Blockers\nNone.\n",
            ".agents/state/VERIFIED_FINDINGS.md": "# Findings\n",
            ".agents/tasks/BACKLOG.yaml": json.dumps(
                {
                    "tasks": [
                        {
                            "id": "G1-007",
                            "title": "Context verification",
                            "milestone": "G1",
                            "status": "done",
                            "depends_on": [],
                            "evidence": [
                                {"kind": "file", "path": ".agents/evidence/G1-007.md"}
                            ],
                        },
                        {
                            "id": "G1-008",
                            "title": "Recovery validation",
                            "milestone": "G1",
                            "status": "done",
                            "depends_on": ["G1-007"],
                            "plan_ref": ".agents/plans/G1.md",
                            "evidence": [
                                {"kind": "file", "path": ".agents/evidence/G1-008.md"}
                            ],
                        },
                        {
                            "id": "M0-001",
                            "title": "Technical project bootstrap",
                            "milestone": "M0",
                            "status": "done",
                            "depends_on": ["G1-008"],
                            "plan_ref": ".agents/plans/M00-bootstrap.md",
                            "acceptance_criteria_ids": ["M0-01"],
                            "evidence": [
                                {"kind": "file", "path": ".agents/evidence/M0.md"},
                                {"kind": "test", "path": "tests/test_app.py", "command": "python -m unittest tests.test_app"},
                                {"kind": "file", "path": "datasets/sample.pgn"},
                            ],
                        },
                    ]
                }
            ),
            ".agents/plans/M00-bootstrap.md": "# M0 plan\n",
            ".agents/plans/G1.md": "# G1 dependency plan\n",
            ".agents/evidence/M0.md": "M0 checks: python -m unittest discover -s tests -v\n",
            ".agents/evidence/G1-007.md": "G1-007 evidence\n",
            ".agents/evidence/G1-008.md": "G1-008 evidence\n",
            "pyproject.toml": '[project]\nname = "fixture"\n',
            "uv.lock": "version = 1\n",
            "src/app.py": "from src.helper import answer\n\ndef run():\n    return answer()\n",
            "src/helper.py": "def answer():\n    return 42\n",
            "tests/test_app.py": "from pathlib import Path\nfrom src.app import run\nTOOL = Path(__file__).resolve().parents[1] / \"scripts\" / \"tool.py\"\n\ndef test_run():\n    assert run() == 42\n",
            "scripts/tool.py": "def helper():\n    return 1\n",
            "datasets/sample.pgn": '[Event "private fixture"]\n*\n',
        }
        for path, content in files.items():
            self.write(path, content)

    def export(self, *args, expected=0, scope="M0"):
        command = [
            sys.executable,
            str(EXPORTER),
            "--repo",
            str(self.repo),
            "--scope",
            scope,
            "--output-dir",
            str(self.output),
            *args,
        ]
        result = subprocess.run(command, text=True, capture_output=True, check=False)
        self.assertEqual(
            expected,
            result.returncode,
            f"stdout={result.stdout}\nstderr={result.stderr}",
        )
        return result

    def archive(self):
        archives = sorted(self.output.glob("*.zip"))
        self.assertTrue(archives, "export command produced no ZIP")
        return archives[-1]

    def manifest(self, archive):
        with zipfile.ZipFile(archive) as bundle:
            data = json.loads(bundle.read("REVIEW_MANIFEST.json"))
        return data

    def test_working_tree_uses_dirty_and_relevant_untracked_files(self):
        self.write("src/helper.py", "def answer():\n    return 43\n")
        self.write("src/extra.py", "VALUE = 'untracked and imported'\n")
        self.write(
            "src/app.py",
            "from src.helper import answer\nimport src.extra\n\ndef run():\n    return answer()\n",
        )

        self.export()
        archive = self.archive()
        with zipfile.ZipFile(archive) as bundle:
            self.assertIn("return 43", bundle.read("src/helper.py").decode())
            self.assertIn("src/extra.py", bundle.namelist())
            self.assertIn("scripts/tool.py", bundle.namelist())
            self.assertIn("REVIEW_README.md", bundle.namelist())
        manifest = self.manifest(archive)
        self.assertEqual("working-tree", manifest["snapshot_mode"])
        provenance = {entry["path"]: entry["provenance"] for entry in manifest["files"]}
        self.assertEqual("worktree", provenance["src/helper.py"]["source"])
        self.assertEqual("untracked", provenance["src/extra.py"]["source"])

    def test_clean_working_tree_is_exported_from_worktree(self):
        self.export()
        archive = self.archive()
        provenance = {
            entry["path"]: entry["provenance"] for entry in self.manifest(archive)["files"]
        }
        self.assertEqual("worktree", provenance["src/helper.py"]["source"])
        self.assertEqual("clean", provenance["src/helper.py"]["git_status"])

    def test_unrelated_untracked_user_file_is_not_included(self):
        self.write("main.py", "USER_WORK = 'keep this local'\n")
        self.export()
        with zipfile.ZipFile(self.archive()) as bundle:
            self.assertNotIn("main.py", bundle.namelist())

    def test_staged_uses_index_for_staged_content_and_head_for_unchanged(self):
        self.write("src/helper.py", "def answer():\n    return 44\n")
        run_git(self.repo, "add", "src/helper.py")
        self.write("src/helper.py", "def answer():\n    return 45\n")
        self.write("src/untracked.py", "SHOULD_NOT_APPEAR = True\n")

        self.export("--mode", "staged")
        archive = self.archive()
        with zipfile.ZipFile(archive) as bundle:
            content = bundle.read("src/helper.py").decode()
            names = bundle.namelist()
        self.assertIn("44", content)
        self.assertNotIn("45", content)
        self.assertNotIn("src/untracked.py", names)
        provenance = {
            entry["path"]: entry["provenance"] for entry in self.manifest(archive)["files"]
        }
        self.assertEqual("index", provenance["src/helper.py"]["source"])
        self.assertIn(provenance["src/app.py"]["source"], {"HEAD", "index"})

    def test_committed_mode_reads_only_requested_commit(self):
        first = self.head
        self.write("src/helper.py", "def answer():\n    return 99\n")
        run_git(self.repo, "add", "src/helper.py")
        run_git(self.repo, "commit", "-qm", "second version")
        self.write("src/helper.py", "def answer():\n    return 100\n")

        self.export("--mode", "committed", "--commit", first)
        archive = self.archive()
        with zipfile.ZipFile(archive) as bundle:
            content = bundle.read("src/helper.py").decode()
        self.assertIn("42", content)
        self.assertNotIn("100", content)
        manifest = self.manifest(archive)
        self.assertEqual(first, manifest["git_revision"])
        self.assertEqual("committed", manifest["snapshot_mode"])

    def test_missing_required_context_fails_without_archive(self):
        (self.repo / "docs/01-foundation/REQUIREMENTS.md").unlink()
        result = self.export(expected=2)
        self.assertIn("REQUIREMENTS.md", result.stderr)
        self.assertFalse(self.output.exists())

    def test_ignored_private_file_is_excluded_and_candidate_secret_stops_export(self):
        self.write("private.env", "OPENAI_API_KEY=" + "sk-test-not-for-output\n")
        self.write("src/helper.py", "TOKEN = '" + "ghp_" + "a" * 36 + "'\n")
        result = self.export(expected=2)
        self.assertIn("src/helper.py", result.stderr)
        self.assertNotIn("ghp_", result.stderr)
        self.assertFalse(self.output.exists())

    def test_ignored_files_are_excluded(self):
        self.write("private.env", "ordinary local setting\n")
        self.write("src/__pycache__/helper.pyc", "generated bytes\n")
        self.export()
        archive = self.archive()
        with zipfile.ZipFile(archive) as bundle:
            names = bundle.namelist()
        self.assertNotIn("private.env", names)
        self.assertNotIn("src/__pycache__/helper.pyc", names)

    def test_external_symlink_is_rejected_without_reading_target(self):
        outside = Path(self.temp.name) / "outside.py"
        outside.write_text("SECRET_OUTSIDE_CONTENT\n", encoding="utf-8")
        link = self.repo / "src" / "outside.py"
        link.symlink_to(outside)
        self.write("src/app.py", "import src.outside\n")

        result = self.export(expected=2)
        self.assertIn("src/outside.py", result.stderr)
        self.assertNotIn("SECRET_OUTSIDE_CONTENT", result.stderr)
        self.assertFalse(self.output.exists())

    def test_unsafe_git_path_is_rejected(self):
        self.write("bad\\name.py", "VALUE = 1\n")
        run_git(self.repo, "add", "--", "bad\\name.py")
        run_git(self.repo, "commit", "-qm", "unsafe path")
        result = self.export("--mode", "committed", "--commit", "HEAD", expected=2)
        self.assertIn("unsafe", result.stderr.lower())
        self.assertFalse(self.output.exists())

    def test_windows_drive_path_is_rejected(self):
        self.write("C:/escape.txt", "VALUE = 1\n")
        run_git(self.repo, "add", "--", "C:/escape.txt")
        run_git(self.repo, "commit", "-qm", "drive path")

        result = self.export("--mode", "committed", "--commit", "HEAD", expected=2)
        self.assertIn("unsafe", result.stderr.lower())
        self.assertFalse(self.output.exists())

    def test_manifest_hashes_crc_and_required_coverage_are_consistent(self):
        self.export()
        archive = self.archive()
        with zipfile.ZipFile(archive) as bundle:
            self.assertIsNone(bundle.testzip())
            names = set(bundle.namelist())
            manifest = json.loads(bundle.read("REVIEW_MANIFEST.json"))
            listed = {entry["path"] for entry in manifest["files"]}
            self.assertEqual(names, listed | {"REVIEW_MANIFEST.json", "REVIEW_README.md"})
            for entry in manifest["files"]:
                payload = bundle.read(entry["path"])
                self.assertEqual(entry["size_bytes"], len(payload))
                self.assertEqual(entry["sha256"], hashlib.sha256(payload).hexdigest())
        self.assertTrue(manifest["excluded_paths"])
        self.assertIn("AGENTS.md", listed)
        self.assertIn(".agents/state/PROJECT_STATE.yaml", listed)
        self.assertIn("src/helper.py", listed)
        self.assertIn("REVIEW_README.md", listed)
        self.assertNotIn("datasets/sample.pgn", listed)

    def test_arbitrary_task_scope_resolves_dependencies_and_records_current_gate(self):
        self.export(scope="technical project bootstrap")
        archive = self.archive()
        manifest = self.manifest(archive)
        self.assertEqual(["G1-007", "G1-008", "M0-001"], manifest["task_ids"])
        self.assertEqual("G2", manifest["project_state"]["current_gate"])
        self.assertFalse(manifest["project_state"]["start_authorized"])
        self.assertTrue(any("O-01, O-02" in item for item in manifest["unresolved_review_limitations"]))
        with zipfile.ZipFile(archive) as bundle:
            readme = bundle.read("REVIEW_README.md").decode()
        self.assertIn("pending_user_approval", readme)
        self.assertIn("tests/test_app.py", readme)

    def test_short_credential_assignment_is_reported_without_value(self):
        self.write("src/helper.py", "TOKEN = '" + "abc123456789" + "xyz'\n")
        result = self.export(expected=2)
        self.assertIn("src/helper.py", result.stderr)
        self.assertNotIn("abc123456789xyz", result.stderr)

    def test_artifact_reference_is_omitted_by_default_and_included_only_with_opt_in(self):
        self.export()
        default_manifest = self.manifest(self.archive())
        self.assertIn("datasets/sample.pgn", {item["path"] for item in default_manifest["excluded_paths"]})

        self.export("--include-large")
        with zipfile.ZipFile(self.archive()) as bundle:
            self.assertEqual(b'[Event "private fixture"]\n*\n', bundle.read("datasets/sample.pgn"))

    def test_missing_task_evidence_is_reported_as_a_limitation(self):
        backlog_path = self.repo / ".agents/tasks/BACKLOG.yaml"
        backlog = json.loads(backlog_path.read_text(encoding="utf-8"))
        m0 = next(task for task in backlog["tasks"] if task["id"] == "M0-001")
        m0["evidence"].append({"kind": "file", "path": ".agents/evidence/missing-review.md"})
        backlog_path.write_text(json.dumps(backlog), encoding="utf-8")

        self.export()

        limitations = self.manifest(self.archive())["unresolved_review_limitations"]
        self.assertTrue(any("missing-review.md" in item and "unavailable" in item for item in limitations))

    def test_repeated_export_does_not_include_prior_archives(self):
        self.export()
        self.export()
        archives = sorted(self.output.glob("*.zip"))
        self.assertGreaterEqual(len(archives), 2)
        manifests = [self.manifest(archive) for archive in archives]
        selection = lambda value: [(entry["path"], entry["sha256"]) for entry in value["files"]]
        self.assertEqual(selection(manifests[0]), selection(manifests[1]))
        for archive in archives:
            with zipfile.ZipFile(archive) as bundle:
                self.assertFalse(any("review-bundles/" in name for name in bundle.namelist()))
                self.assertFalse(any(name.endswith(".zip") for name in bundle.namelist()))

    def test_export_does_not_change_state_index_or_tracked_working_files(self):
        state = self.repo / ".agents/state/PROJECT_STATE.yaml"
        state_before = state.read_bytes()
        staged_before = run_git(self.repo, "diff", "--cached", "--binary").stdout
        tracked_before = run_git(self.repo, "status", "--porcelain=v1").stdout

        self.export()

        self.assertEqual(state_before, state.read_bytes())
        self.assertEqual(staged_before, run_git(self.repo, "diff", "--cached", "--binary").stdout)
        status_after = run_git(self.repo, "status", "--porcelain=v1").stdout
        self.assertEqual(tracked_before, status_after)
        self.assertEqual(0, run_git(self.repo, "check-ignore", "-q", str(self.output.relative_to(self.repo) / ".archive.zip"), check=False).returncode)

    def test_archive_name_collision_does_not_overwrite_existing_file(self):
        self.output.mkdir(parents=True)
        archive = self.output / "M0-working-tree-20260102T030405678901Z.zip"
        archive.write_bytes(b"preserve existing user file")

        with patch.object(exporter_module, "datetime") as clock:
            clock.now.return_value = datetime(2026, 1, 2, 3, 4, 5, 678901, tzinfo=timezone.utc)
            with self.assertRaises(exporter_module.ExportError):
                exporter_module.export_bundle("M0", repo=self.repo, output_dir=self.output)

        self.assertEqual(b"preserve existing user file", archive.read_bytes())


if __name__ == "__main__":
    unittest.main()
