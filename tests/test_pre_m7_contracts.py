"""Focused, dependency-free contracts for the proposed Pre-M7 package."""

from __future__ import annotations

import json
import re
import sys
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))
import agent_preflight  # noqa: E402


def read_json(relative: str) -> dict:
    return json.loads((REPO / relative).read_text(encoding="utf-8"))


class PreM7ContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.protocol_path = REPO / "docs/04-research/M7_EVALUATION_PROTOCOL.md"
        cls.plan_path = REPO / ".agents/plans/M07-evaluation-delivery.md"
        cls.readiness_path = REPO / ".agents/plans/PRE-M7-readiness.md"
        cls.readiness_evidence_path = REPO / ".agents/evidence/PRE-M7-readiness-20261031.md"
        cls.protocol = cls.protocol_path.read_text(encoding="utf-8")
        cls.plan = cls.plan_path.read_text(encoding="utf-8")
        cls.readiness = cls.readiness_path.read_text(encoding="utf-8")
        cls.state = read_json(".agents/state/PROJECT_STATE.yaml")
        cls.backlog = read_json(".agents/tasks/BACKLOG.yaml")
        cls.tasks = {task["id"]: task for task in cls.backlog["tasks"]}

    def test_g4_g5_criterion_mapping_matches_canonical_acceptance(self) -> None:
        self.assertEqual(
            agent_preflight._load_m7_gate_criteria(REPO),
            {
                "G4": {"M7-01", "M7-02", "M7-03"},
                "G5": {"M7-04", "M7-05"},
            },
        )
        expected = {
            "M7-001": ["M7-01"],
            "M7-002": ["M7-02"],
            "M7-003": ["M7-03"],
            "M7-004": ["M7-04"],
            "M7-005": ["M7-05"],
        }
        for task_id, criteria in expected.items():
            with self.subTest(task=task_id):
                self.assertEqual(self.tasks[task_id]["acceptance_criteria_ids"], criteria)

    def test_m7_tasks_are_pending_and_require_separate_authorization(self) -> None:
        m7_ids = [f"M7-{number:03d}" for number in range(1, 6)]
        for task_id in m7_ids:
            task = self.tasks[task_id]
            self.assertEqual(task["milestone"], "M7")
            self.assertEqual(task["status"], "pending")
            self.assertTrue(task["next_action"].strip())
            self.assertFalse(task["blocker_ids"])
        self.assertEqual(self.tasks["M7-001"]["depends_on"], ["M4-001", "M5-001", "M6-001", "M2-001", "M3-001"])
        self.assertEqual(self.tasks["M7-002"]["depends_on"], ["M7-001"])
        self.assertEqual(self.tasks["M7-003"]["depends_on"], ["M7-002"])
        self.assertEqual(self.tasks["M7-004"]["depends_on"], ["M7-003"])
        self.assertEqual(self.tasks["M7-005"]["depends_on"], ["M7-004"])
        self.assertTrue(all(self.tasks[f"M7-{n:03d}"]["requires_user_gate_approval"] is None for n in (1, 2, 3)))
        self.assertEqual(self.tasks["M7-004"]["requires_user_gate_approval"], "G4")
        self.assertEqual(self.tasks["M7-005"]["requires_user_gate_approval"], "G4")
        engineering = self.state["engineering"]
        self.assertEqual(engineering["next_milestone"], "M7")
        self.assertEqual(engineering["next_milestone_status"], "pending_user_approval")
        self.assertFalse(engineering["start_authorized"])
        self.assertIsNone(engineering["start_authorization_record"])
        self.assertEqual(self.state["task_refs"], {"active_task_id": None, "next_task_id": "M7-001"})
        self.assertEqual(self.state["governance"]["approved_gates"], ["G0", "G1", "G2", "G3"])
        self.assertEqual(self.tasks["M6-001"]["status"], "done")

    def test_canonical_state_and_backlog_are_json_yaml_and_dependency_valid(self) -> None:
        self.assertEqual(self.state["format"], "JSON-compatible YAML 1.2")
        self.assertEqual(self.backlog["format"], "JSON-compatible YAML 1.2")
        known = set(self.tasks)
        for task in self.tasks.values():
            self.assertTrue(set(task["depends_on"]).issubset(known), task["id"])
        errors: list[dict[str, str]] = []
        acceptance_ids = agent_preflight._load_acceptance_ids(REPO, errors)
        self.assertFalse(errors)
        self.assertTrue({f"M7-{n:02d}" for n in range(1, 6)}.issubset(acceptance_ids))

    def test_read_only_input_audits_bind_frozen_identities_and_provenance(self) -> None:
        audit = read_json(".agents/evidence/PRE-M7-input-integrity-20261031.json")
        self.assertEqual(audit["source_revision"], "fa7683822c436f3e9d6c3455a24cd1f4a6cbb463")
        checks = {item["name"]: item for item in audit["checks"]}
        self.assertEqual((checks["M4"]["status"], checks["M4"]["exit_code"]), ("verified", 0))
        self.assertEqual(checks["M4"]["summary"]["artifact_files_verified"], 19)
        self.assertEqual(checks["M4"]["summary"]["checkpoint"]["checkpoint_sha256"], "724ac730f3c5f2d01b48b26eb7670a3c764978a3dd4d6702b3057a99ab1a90a4")
        self.assertEqual((checks["M5"]["status"], checks["M5"]["exit_code"]), ("verified", 0))
        self.assertEqual(checks["M5"]["summary"]["run_manifests"], 7)
        self.assertEqual(checks["M5"]["summary"]["total_bytes"], 6544747450)
        m6 = read_json(".agents/evidence/PRE-M7-M6-readonly-audit-20261031.json")
        self.assertEqual((m6["exit_code"], m6["source_revision"]), (0, "fa7683822c436f3e9d6c3455a24cd1f4a6cbb463"))
        self.assertEqual(m6["result"]["integrity"]["artifact_manifest"]["sha256"], "bc0068aa2254e4c15165247ee299f48940cca9b7c21f6a288fd13812631ea2b2")
        self.assertEqual(m6["result"]["reconstructed"]["outcomes"]["ale_terminated_losses"], 11)
        self.assertEqual(m6["result"]["reconstructed"]["outcomes"]["incomplete"], 9)
        self.assertEqual(m6["result"]["reconstructed"]["rgb_verified_player_moves"], 385)
        self.assertEqual(m6["result"]["reconstructed"]["initiated_player_moves"], 405)
        self.assertTrue(m6["result"]["known_historical_discrepancy"]["finding_id"] == "PM6-F06")
        self.assertEqual(m6["result"]["disposition"], "PASS_WITH_IMMUTABLE_PM6_F06_ERRATUM_REQUIRED")
        v1 = m6["result"]["audit"]["v1_integrity_check"]
        self.assertEqual(v1["current_invocation_exit_code"], 0)
        self.assertEqual(v1["run_id"], "m6-stage3-ad3998200e31-c5ff389dc4fe")
        self.assertEqual(v1["artifact_manifest"]["file_count"], 4540)
        self.assertEqual(v1["finished_attempts"], 35)

    def test_protocol_rejects_pseudoreplication_unsupported_strength_and_elo_claims(self) -> None:
        text = self.protocol.lower()
        for required in (
            "not an independent replication count",
            "three training-seed pairs",
            "incomplete attempts are not draws",
            "no warm-start superiority is established",
            "no elo value is currently reportable",
            "never assume a 1500 baseline",
        ):
            with self.subTest(required=required):
                self.assertIn(required, text)
        forbidden_claims = (
            "1500 independent training replications",
            "strong atari chess skill is demonstrated",
            "v1 and v2 are pooled",
        )
        for claim in forbidden_claims:
            with self.subTest(claim=claim):
                self.assertNotIn(claim, text)

    def test_tracks_protocols_terminal_states_and_historical_provenance_stay_distinct(self) -> None:
        text = self.protocol.lower()
        for item in (
            "supervised pretraining",
            "m2 simulator rl",
            "real ale atari evaluation",
            "stage 3 v1",
            "stage 3 v2",
            "v1 and v2 must never be pooled",
            "truncated",
            "incomplete / censored",
            "rsk-014",
            "pm6-f06",
            "not authorized",
        ):
            with self.subTest(item=item):
                self.assertIn(item, text)
        self.assertIn("11 ale-terminal losses", text)
        self.assertIn("9 incomplete attempts", text)
        self.assertIn("incomplete attempts are not draws", text)
        self.assertIn("the original v2 manifest's", text)

    def test_private_assets_remain_local_and_sanitized_reports_are_portable(self) -> None:
        tracked = __import__("subprocess").run(
            ["git", "ls-files", "--", "artifacts"], cwd=REPO, text=True, capture_output=True, check=True
        ).stdout.splitlines()
        self.assertFalse(any(path.startswith(("artifacts/m4/", "artifacts/m5/", "artifacts/m6/")) for path in tracked))
        private_payload_suffixes = {".pt", ".pth", ".ckpt", ".npz", ".pgn", ".png", ".rgb", ".rom"}
        self.assertFalse(any(Path(path).suffix.lower() in private_payload_suffixes for path in tracked))
        for relative in (
            ".agents/evidence/PRE-M7-input-integrity-20261031.json",
            ".agents/evidence/PRE-M7-M6-readonly-audit-20261031.json",
            ".agents/evidence/PRE-M7-resource-snapshot-20261031.json",
        ):
            content = (REPO / relative).read_text(encoding="utf-8")
            self.assertNotIn("/home/", content)
            self.assertNotRegex(content, r"(?i)(?:raw_rgb|rom_bytes|checkpoint_bytes|credential|token)\s*[:=]")
        self.assertIn("local-only", self.readiness.lower())
        self.assertIn("do not upload", self.plan.lower())

    def test_all_new_local_markdown_links_resolve(self) -> None:
        sources = (self.protocol_path, self.plan_path, self.readiness_path, self.readiness_evidence_path)
        checked = 0
        for source in sources:
            text = source.read_text(encoding="utf-8")
            for target in re.findall(r"\]\(([^)]+)\)", text):
                if target.startswith(("https://", "http://", "mailto:")):
                    continue
                path = target.split("#", 1)[0]
                if not path:
                    continue
                resolved = (source.parent / path).resolve()
                with self.subTest(source=source.relative_to(REPO), target=target):
                    self.assertTrue(resolved.is_file(), f"unresolved local link: {target}")
                    relative = resolved.relative_to(REPO).as_posix()
                    committed = __import__("subprocess").run(
                        ["git", "cat-file", "-e", f"HEAD:{relative}"],
                        cwd=REPO,
                        text=True,
                        capture_output=True,
                    )
                    self.assertEqual(committed.returncode, 0, f"local link target is not committed in HEAD: {target}")
                checked += 1
        self.assertGreaterEqual(checked, 13)


if __name__ == "__main__":
    unittest.main()
