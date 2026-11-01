"""Release-safety and G5 governance contracts for M7-005."""

from __future__ import annotations

import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


class M7ReleaseDispositionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.state = json.loads(read(".agents/state/PROJECT_STATE.yaml"))
        cls.backlog = json.loads(read(".agents/tasks/BACKLOG.yaml"))
        cls.tasks = {task["id"]: task for task in cls.backlog["tasks"]}
        cls.owner = read(".agents/evidence/M7-005-owner-no-release-decision-20261101.md")
        cls.authorization = read(".agents/evidence/M7-005-authorization-20261101.md")
        cls.disposition = read("docs/07-delivery/RELEASE_DISPOSITION.md")
        cls.acceptance = read(".agents/evidence/M7-005-acceptance-20261101.md")
        cls.handover = read(".agents/evidence/M7-G5-review-handover-20261101.md")

    def test_owner_authorization_and_no_release_are_distinct_from_pm_approval(self) -> None:
        self.assertIn("M7-AUTH-20261101-M7-005-NO-RELEASE", self.owner)
        self.assertIn("M7-005 only", self.authorization)
        self.assertIn("NO RELEASE / NO PUBLICATION AUTHORIZED", self.owner)
        self.assertIn("separate issuance timestamp", self.owner)
        engineering = self.state["engineering"]
        self.assertEqual(
            engineering["start_authorization_record"]["authorization_id"],
            "M7-AUTH-20261031-OPTION-B",
        )
        self.assertTrue(any(
            item.get("path") == ".agents/evidence/M7-005-authorization-20261101.md"
            for item in self.tasks["M7-005"]["evidence"]
        ))
        self.assertEqual([self.tasks[f"M7-{n:03d}"]["status"] for n in range(1, 6)], ["done"] * 5)
        self.assertIn("G4", self.state["governance"]["approved_gates"])
        self.assertNotIn("G5", self.state["governance"]["approved_gates"])
        self.assertEqual(self.state["governance"]["current_gate"], "G5")
        self.assertEqual(self.state["governance"]["gate_status"], "ready_for_user_review")
        self.assertEqual(self.state["governance"]["next_governance_gate"], "G5")
        self.assertEqual(self.state["engineering"]["next_milestone_status"], "complete")

    def test_inventory_covers_restricted_artifact_classes_and_rights(self) -> None:
        for category in (
            "Atari VideoChess ROM",
            "M3 original Lichess Elite May 2022 source archive",
            "M3 teacher labels",
            "M4 supervised checkpoint",
            "M5 Warm/Scratch post-RL checkpoints",
            "M5 raw training records",
            "M5 raw simulator evaluation records",
            "M6 Stage 3 v1 raw ALE records",
            "M6 Stage 3 v2 raw ALE records",
            "M7 raw ALE ledgers",
            "Private manifests and manifest-listed payloads",
            "Credentials, machine-specific paths",
            "GitHub Release, public model package, deployment, or release tag",
        ):
            with self.subTest(category=category):
                self.assertIn(category, self.disposition)
        self.assertIn("ad374c8fd9fb2fe5f03c1297aa1d47cbbce5caedf6e6e2d387ee816930afdb11", self.disposition)
        self.assertIn("724ac730f3c5f2d01b48b26eb7670a3c764978a3dd4d6702b3057a99ab1a90a4", self.disposition)
        self.assertIn("25a8b6bcfbf1d948bed886a0a4964cf48210fb1be12809c72bf122157b8d05e4", self.disposition)
        self.assertIn("unstated/unverified", self.disposition)
        self.assertIn("A committed checksum identifies bytes; it does not grant permission", self.disposition)
        self.assertGreaterEqual(
            self.disposition.count("NO RELEASE — OWNER AUTHORIZATION NOT GRANTED"),
            10,
        )

    def test_g5_handover_preserves_accepted_scientific_boundaries(self) -> None:
        for claim in (
            "90/90",
            "60 terminal White losses",
            "30 incomplete",
            "zero wins",
            "9/30",
            "No RL superiority",
            "RSK-014",
            "PM6-F06",
        ):
            with self.subTest(claim=claim):
                self.assertIn(claim.lower(), self.handover.lower())
        self.assertIn("G5 pending Independent PM decision", self.handover)
        self.assertIn("not G5 approval", self.handover)
        self.assertIn("O-02", self.handover)
        self.assertIn("O-06", self.handover)
        self.assertIn("issuecomment-6553580590", self.handover)
        self.assertIn("M7-005", self.acceptance)
        self.assertIn("M7-05", self.acceptance)
        self.assertIn("NOT APPROVED", self.acceptance)
        self.assertIn("NO RELEASE", self.acceptance)

    def test_delivery_documents_and_governance_records_have_no_machine_paths(self) -> None:
        paths = (
            "docs/07-delivery/FINAL_REPORT.md",
            "docs/07-delivery/MODEL_CARD.md",
            "docs/07-delivery/USER_GUIDE.md",
            "docs/07-delivery/HANDOVER.md",
            "docs/07-delivery/RELEASE_DISPOSITION.md",
            ".agents/evidence/M7-005-owner-no-release-decision-20261101.md",
            ".agents/evidence/M7-005-acceptance-20261101.md",
            ".agents/evidence/M7-G5-review-handover-20261101.md",
        )
        for relative in paths:
            content = read(relative)
            for pattern in (r"/home/[^\s`]+", r"/root/[^\s`]+", r"/Users/[^\s`]+", r"/mnt/[^\s`]+"):
                with self.subTest(path=relative, pattern=pattern):
                    self.assertIsNone(re.search(pattern, content))


if __name__ == "__main__":
    unittest.main()
