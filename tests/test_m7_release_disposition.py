"""Release-safety and G5 governance contracts for M7-005."""

from __future__ import annotations

import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def matching_rows(markdown: str, predicate) -> list[list[str]]:
    rows: list[list[str]] = []
    in_table = False
    for line in markdown.splitlines():
        if line.startswith("|"):
            cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
            if cells and cells[0] == "Artifact category":
                in_table = True
                continue
            if in_table:
                if not cells or all(set(cell) <= {"-", ":", " "} for cell in cells):
                    continue
                if predicate(cells):
                    rows.append(cells)
        elif in_table:
            break
    return rows


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
        cls.m3_acceptance = read(".agents/evidence/M3-acceptance-20261021.md")
        cls.m3_final = json.loads(read(".agents/evidence/M3-final-closure-record-20261021.json"))
        cls.m3_corrective_release = json.loads(
            read(".agents/evidence/M3-corrective-release-manifest-r4-20261021.json")
        )
        cls.m3_corrective_teacher = json.loads(
            read(".agents/evidence/M3-corrective-teacher-manifest-r2-20261021.json")
        )
        cls.m3_corrective_repeat = json.loads(
            read(".agents/evidence/M3-corrective-reproducibility-r4-r5-20261021.json")
        )

    def test_accepted_final_m3_dataset_identity_pair_matches_closure(self) -> None:
        final_releases = [
            release for release in self.m3_final["releases"]
            if release["label"] in {"r6", "r7"}
        ]
        self.assertEqual({release["label"] for release in final_releases}, {"r6", "r7"})
        final_pairs = {
            (release["release_id"], release["manifest_sha256"])
            for release in final_releases
        }
        self.assertEqual(len(final_pairs), 1, "accepted r6/r7 identities must agree")
        final_release_id, final_manifest_sha = next(iter(final_pairs))
        for release in final_releases:
            self.assertEqual(
                (release["verification"]["release_id"], release["verification"]["manifest_sha256"]),
                (final_release_id, final_manifest_sha),
                f"{release['label']} verifier must confirm its recorded identity pair",
            )

        # Pin the accepted identity too, so an internally consistent but wrong
        # historical generation cannot silently become the final release.
        self.assertEqual(
            (final_release_id, final_manifest_sha),
            (
                "f10a679deddf06f3e1e3c39cf58db4e21176629c26c09034a271bf278189e890",
                "be1e1f9316fac01be893774cfe09a313de193fbd1a12ab2d219ff5c041104a12",
            ),
        )
        self.assertIn(f"`{final_release_id}`", self.m3_acceptance)
        self.assertIn(f"`{final_manifest_sha}`", self.m3_acceptance)

        rows = matching_rows(
            self.disposition,
            lambda cells: "M3" in cells[0]
            and "normalized/released derived dataset" in cells[0]
            and "historical" not in cells[0].lower(),
        )
        self.assertEqual(len(rows), 1, "inventory must contain one accepted-final M3 dataset row")
        identity = rows[0][1]
        self.assertIn(final_release_id, identity)
        self.assertIn(final_manifest_sha, identity)
        self.assertNotIn(self.m3_corrective_release["release_id"], identity)
        self.assertNotIn(self.m3_corrective_teacher["dataset_manifest_sha256"], identity)
        self.assertIn("M3-final-closure-record-20261021.json", rows[0][9])
        self.assertIn("M3-final-closure-20261021.md", rows[0][9])
        self.assertIn("M3-acceptance-20261021.md", rows[0][9])

    def test_historical_corrective_dataset_and_teacher_are_separate_from_final(self) -> None:
        historical_release_id = self.m3_corrective_release["release_id"]
        historical_manifest_file = next(
            item for item in self.m3_corrective_repeat["files"]
            if item["path"] == "manifest.json"
        )
        historical_manifest_sha = historical_manifest_file["r4_sha256"]
        self.assertEqual(
            (self.m3_corrective_repeat["r4_release_id"], self.m3_corrective_repeat["r5_release_id"]),
            (historical_release_id, historical_release_id),
        )
        self.assertEqual(
            (historical_manifest_file["r4_sha256"], historical_manifest_file["r5_sha256"]),
            (historical_manifest_sha, historical_manifest_sha),
        )
        self.assertEqual(self.m3_corrective_teacher["dataset_release_id"], historical_release_id)
        self.assertEqual(
            self.m3_corrective_teacher["dataset_manifest_sha256"], historical_manifest_sha
        )

        dataset_rows = matching_rows(
            self.disposition,
            lambda cells: "m3 historical corrective derived dataset" in cells[0].lower(),
        )
        self.assertEqual(len(dataset_rows), 1, "historical corrective dataset needs a separate row")
        historical_dataset_identity = dataset_rows[0][1]
        self.assertIn(historical_release_id, historical_dataset_identity)
        self.assertIn(historical_manifest_sha, historical_dataset_identity)
        self.assertNotIn("f10a679deddf06f3e1e3c39cf58db4e21176629c26c09034a271bf278189e890", historical_dataset_identity)
        self.assertNotIn("be1e1f9316fac01be893774cfe09a313de193fbd1a12ab2d219ff5c041104a12", historical_dataset_identity)
        self.assertIn("M3-corrective-release-manifest-r4-20261021.json", dataset_rows[0][9])
        self.assertIn("M3-corrective-reproducibility-r4-r5-20261021.json", dataset_rows[0][9])

        historical_teacher_rows = matching_rows(
            self.disposition,
            lambda cells: "m3 historical corrective teacher" in cells[0].lower(),
        )
        self.assertEqual(len(historical_teacher_rows), 1)
        historical_teacher_identity = historical_teacher_rows[0][1]
        self.assertIn(self.m3_corrective_teacher["teacher_run_id"], historical_teacher_identity)
        self.assertIn(self.m3_corrective_teacher["dataset_release_id"], historical_teacher_identity)
        self.assertIn(self.m3_corrective_teacher["dataset_manifest_sha256"], historical_teacher_identity)
        self.assertNotIn("58febd814bb6bdd6fa67b990a1e4906ada14c31fafa265829fb49b7d3c203272", historical_teacher_identity)
        self.assertNotIn("be1e1f9316fac01be893774cfe09a313de193fbd1a12ab2d219ff5c041104a12", historical_teacher_identity)
        self.assertIn("M3-corrective-teacher-manifest-r2-20261021.json", historical_teacher_rows[0][9])

    def test_final_m3_teacher_is_bound_to_final_dataset_in_closure_and_inventory(self) -> None:
        final_teacher = self.m3_final["teacher"]
        final_releases = [
            release for release in self.m3_final["releases"]
            if release["label"] in {"r6", "r7"}
        ]
        final_pairs = {
            (release["release_id"], release["manifest_sha256"])
            for release in final_releases
        }
        self.assertEqual(len(final_pairs), 1)
        final_release_id, final_manifest_sha = next(iter(final_pairs))
        self.assertEqual(
            (final_teacher["dataset_release_id"], final_teacher["dataset_manifest_sha256"]),
            (final_release_id, final_manifest_sha),
            "accepted final teacher must bind to the accepted final dataset pair",
        )
        self.assertEqual(
            final_teacher["run_id"],
            "58febd814bb6bdd6fa67b990a1e4906ada14c31fafa265829fb49b7d3c203272",
        )
        self.assertIn(f"Teacher run ID `{final_teacher['run_id']}`", self.m3_acceptance)

        rows = matching_rows(
            self.disposition,
            lambda cells: "m3 accepted final teacher" in cells[0].lower(),
        )
        self.assertEqual(len(rows), 1, "inventory must identify the accepted final teacher separately")
        identity = rows[0][1]
        for expected in (
            final_teacher["run_id"], final_release_id, final_manifest_sha,
            final_teacher["manifest_sha256"],
        ):
            self.assertIn(expected, identity)
        self.assertNotIn(self.m3_corrective_teacher["teacher_run_id"], identity)
        self.assertIn("M3-final-closure-record-20261021.json", rows[0][9])
        self.assertIn("M3-final-closure-20261021.md", rows[0][9])
        self.assertIn("M3-acceptance-20261021.md", rows[0][9])

    def test_all_m3_inventory_generations_remain_restricted(self) -> None:
        rows = matching_rows(self.disposition, lambda cells: cells[0].startswith("M3 "))
        self.assertGreaterEqual(len(rows), 4)
        for row in rows:
            with self.subTest(category=row[0]):
                self.assertIn("NO RELEASE", row[8])
                self.assertIn("no redistribution", row[7].lower())

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
            "M3 accepted final teacher labels",
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
