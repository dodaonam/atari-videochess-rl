from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import unittest
from urllib.parse import unquote, urlsplit


ROOT = Path(__file__).resolve().parents[1]
DELIVERY = ROOT / "docs/07-delivery"
DOCS = ("FINAL_REPORT.md", "MODEL_CARD.md", "USER_GUIDE.md", "HANDOVER.md")
LINK_RE = re.compile(r"\[[^\]]+\]\(([^)]+)\)")


class M7DeliveryDocumentationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.texts = {
            name: (DELIVERY / name).read_text(encoding="utf-8")
            for name in DOCS
        }
        cls.analysis_document = json.loads(
            (ROOT / ".agents/evidence/M7-analysis-final-r2-20261101/m7-analysis.json")
            .read_text(encoding="utf-8")
        )

    def test_all_delivery_documents_exist_and_have_substantive_content(self) -> None:
        for name in DOCS:
            path = DELIVERY / name
            self.assertTrue(path.is_file(), name)
            self.assertGreater(path.stat().st_size, 1000, name)
            self.assertNotRegex(self.texts[name], r"(?i)\b(TODO|TBD|placeholder)\b")

    def test_local_markdown_links_resolve_inside_repository(self) -> None:
        errors: list[str] = []
        for name, content in self.texts.items():
            source = DELIVERY / name
            for raw_target in LINK_RE.findall(content):
                target = unquote(raw_target.strip("<>"))
                parsed = urlsplit(target)
                if parsed.scheme or target.startswith("//"):
                    continue
                destination = (
                    (source.parent / parsed.path).resolve()
                    if parsed.path
                    else source.resolve()
                )
                try:
                    destination.relative_to(ROOT.resolve())
                except ValueError:
                    errors.append(f"{name}: link leaves repository: {target}")
                    continue
                if not destination.is_file():
                    errors.append(f"{name}: missing local link: {target}")
        self.assertEqual(errors, [])

    def test_m7_report_totals_match_machine_readable_raw_derived_analysis(self) -> None:
        track = self.analysis_document["analysis"]["tracks"]["M7_option_B_ALE"]
        rows = track["policy_summary"]["by_policy"].values()
        totals = {
            key: sum(row[key] for row in rows)
            for key in (
                "attempt_process_count",
                "wins",
                "draws",
                "losses",
                "incomplete",
                "not_started",
                "terminal_unknown",
                "truncated",
            )
        }
        self.assertEqual(totals, {
            "attempt_process_count": 90,
            "wins": 0,
            "draws": 0,
            "losses": 60,
            "incomplete": 30,
            "not_started": 0,
            "terminal_unknown": 0,
            "truncated": 0,
        })
        report = self.texts["FINAL_REPORT.md"]
        self.assertIn("60 terminal White losses, 30 incomplete", report)
        self.assertIn("90 / 90", report)
        self.assertIn("Undefined (0)", report)
        self.assertIn("Only 9/30 Warm/Scratch", report)
        self.assertIn("no paired confidence interval is available", report.lower())

    def test_all_m7_rl_baseline_paired_rows_are_present(self) -> None:
        track = self.analysis_document["analysis"]["tracks"]["M7_option_B_ALE"]
        comparisons = track["paired_comparisons"]["rl_policy_vs_baseline"]
        self.assertEqual(len(comparisons), 18)
        report = self.texts["FINAL_REPORT.md"]
        baseline_labels = {
            "m4-behavior-only-seed-20261024": "M4",
            "random-legal": "RandomLegal",
            "simple-heuristic": "SimpleHeuristic",
        }
        for item in comparisons:
            policy_id, baseline_id = item["comparison"].split("_minus_")
            _, arm, _, seed, *_ = policy_id.split("-")
            label = f"{arm.title()} {seed} vs {baseline_labels[baseline_id]}"
            self.assertIn(label, report)
            bootstrap = item["paired_cluster_bootstrap"]
            expected_cells = (
                f"| {label} | {item['training_seed']} | "
                f"{bootstrap['matched_pair_rows']} | {bootstrap['censored_pairs']} |"
            )
            self.assertIn(expected_cells, report)

    def test_checkpoint_hashes_and_frozen_run_identity_are_traceable(self) -> None:
        report = self.texts["FINAL_REPORT.md"]
        card = self.texts["MODEL_CARD.md"]
        acceptance = (ROOT / ".agents/evidence/M7-001-acceptance-20261101.md").read_text(
            encoding="utf-8"
        )
        for source in (report, card, acceptance):
            self.assertIn("m7-option-b-20261031-v1-8387b289432f", source)
            self.assertIn(
                "8ec8a42a808f4ffc410c938b4400d02461f96823eb5ac1b16cbd6e0d5e35f255",
                source,
            )
        config = json.loads((ROOT / "configs/m7/m7-option-b-1.0.0.json").read_text())
        expected_hashes = {
            config["accepted_inputs"]["m4"]["checkpoint_sha256"],
            *(
                policy["checkpoint_file_sha256"]
                for policy in config["accepted_inputs"]["m5"]["policies"]
            ),
        }
        for digest in expected_hashes:
            self.assertIn(digest, card)
            self.assertIn(digest, acceptance)

    def test_evidence_inventory_source_hashes_and_analysis_manifest_are_valid(self) -> None:
        inventory_path = ROOT / ".agents/evidence/M7-004-evidence-inventory-20261101.json"
        inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
        self.assertEqual(inventory["scope"]["base_revision"], "d7332b91128d3daf919421db2e71a9f2ee4b48ec")
        for source in inventory["committed_source_file_sha256"]:
            path = ROOT / source["path"]
            self.assertTrue(path.is_file(), source["path"])
            self.assertEqual(
                hashlib.sha256(path.read_bytes()).hexdigest(),
                source["sha256"],
                source["path"],
            )
        bundle = ROOT / ".agents/evidence/M7-analysis-final-r2-20261101"
        manifest_path = bundle / "manifest.json"
        self.assertEqual(
            hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
            inventory["analysis_bundle"]["manifest_sha256"],
        )
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        for entry in manifest["files"]:
            content = (bundle / entry["path"]).read_bytes()
            self.assertEqual(len(content), entry["bytes"], entry["path"])
            self.assertEqual(hashlib.sha256(content).hexdigest(), entry["sha256"], entry["path"])

    def test_governance_and_scientific_limits_are_explicit(self) -> None:
        all_docs = "\n".join(self.texts.values())
        for required in (
            "G4",
            "G5",
            "NOT APPROVED",
            "RSK-014",
            "PM6-F06",
            "Elo is not reported",
            "O-02",
            "no public",
        ):
            self.assertIn(required.lower(), all_docs.lower())
        self.assertIn("M7-005 is pending", self.texts["HANDOVER.md"])
        self.assertIn("undefined", self.texts["FINAL_REPORT.md"].lower())

    def test_delivery_docs_do_not_contain_machine_specific_private_paths(self) -> None:
        for name, content in self.texts.items():
            for pattern in (r"/home/[^ \n]+", r"/Users/[^ \n]+", r"/mnt/[^ \n]+"):
                self.assertNotRegex(content, pattern, name)


if __name__ == "__main__":
    unittest.main()
