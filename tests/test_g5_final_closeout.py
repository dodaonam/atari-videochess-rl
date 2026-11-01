"""Contracts for G5-F02 provenance correction and M0-M7 research closure."""

from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def read_json(relative: str) -> dict:
    return json.loads(read(relative))


class G5FinalCloseoutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.status = read_json(".agents/evidence/G5-F02-provenance-status-20261101.json")
        cls.state = read_json(".agents/state/PROJECT_STATE.yaml")
        cls.backlog = read_json(".agents/tasks/BACKLOG.yaml")
        cls.tasks = {task["id"]: task for task in cls.backlog["tasks"]}
        cls.erratum = read(".agents/evidence/G5-F02-provenance-erratum-20261101.md")
        cls.research_decision = read(".agents/evidence/PROJECT-OWNER-final-research-scope-decision-20261101.md")
        cls.release = read("docs/07-delivery/RELEASE_DISPOSITION.md")
        cls.closeout = read(".agents/evidence/M0-M7-final-project-closure-20261101.md")
        cls.old_owner_record = read(".agents/evidence/M7-005-owner-no-release-decision-20261101.md")
        cls.old_authorization = read(".agents/evidence/M7-005-authorization-20261101.md")
        cls.old_pm_decision = read_json(".agents/evidence/G5-PM-acceptance-20261101.json")
        cls.m7_results = read_json(".agents/evidence/M7-analysis-final-r2-20261101/m7-analysis.json")

    def test_owner_instruction_and_executor_attribution_are_distinct(self) -> None:
        auth = self.status["owner_release_authorization"]
        self.assertEqual(auth["explicit_blanket_owner_prohibition"], "unverified")
        self.assertEqual(auth["affirmative_authorization_for_restricted_artifacts"], "not_established")
        self.assertFalse(auth["release_or_publication_performed_by_this_remediation"])
        self.assertIn("historical executor-authored record", self.old_owner_record.lower())
        self.assertIn("unverified", self.old_owner_record.lower())
        self.assertIn("historical executor-authored record", self.old_authorization.lower())
        self.assertIn("unsupported by an independently verifiable primary source", self.old_owner_record.lower())
        self.assertIn("G5-F02", self.erratum)
        self.assertIn("do not contain a primary-source permalink", self.erratum)

    def test_absence_of_permission_is_not_an_owner_prohibition_or_release_permission(self) -> None:
        auth = self.status["owner_release_authorization"]
        self.assertEqual(auth["affirmative_authorization_for_restricted_artifacts"], "not_established")
        self.assertEqual(auth["explicit_blanket_owner_prohibition"], "unverified")
        self.assertIn("absence of affirmative authorization is not publication permission", auth["interpretation"])
        self.assertIn("does not authorize publication", self.research_decision.lower())
        self.assertIn("does not state a blanket owner prohibition", self.research_decision)
        self.assertIn("No new release is performed", self.release)
        self.assertNotIn("NO RELEASE / NO PUBLICATION AUTHORIZED", self.release)
        self.assertIn("not an attributed owner prohibition", self.release)

    def test_project_owner_final_research_decision_is_scoped_and_has_truthful_provenance(self) -> None:
        decision = self.status["owner_final_research_scope_decision"]
        self.assertEqual(decision["status"], "recorded_from_direct_user_instruction_in_current_execution_context")
        self.assertIsNone(decision["separate_external_permalink_or_signature"])
        self.assertIsNone(decision["exact_issuance_timestamp"])
        self.assertFalse(decision["publication_authorized_by_this_decision"])
        self.assertIn("currently accepted research and experimental results are the final results", self.research_decision)
        self.assertIn("no further supervised pretraining", self.research_decision.lower())
        self.assertIn("no further", self.research_decision.lower())
        self.assertIn("simulator evaluation", self.research_decision.lower())
        self.assertIn("ale evaluation", self.research_decision.lower())
        self.assertIn("new research milestone is requested or authorized", self.research_decision.lower())

    def test_current_governance_uses_fresh_independent_pm_approval(self) -> None:
        self.assertEqual(
            self.status["finding"]["latest_pm_source"],
            "https://github.com/dodaonam/atari-videochess-rl/pull/21#issuecomment-6558975009",
        )
        self.assertEqual(self.status["finding"]["reviewed_pr21_head"], "57555b4c9da588b0122fffbc01f61b8cb13075a8")
        governance = self.state["governance"]
        self.assertEqual(governance["current_gate"], "G5")
        self.assertEqual(governance["gate_status"], "approved")
        self.assertEqual(governance["approved_gates"], ["G0", "G1", "G2", "G3", "G4", "G5"])
        self.assertIn("G5-F02", governance["next_user_action"])
        self.assertEqual(self.status["current_governance"]["g5"], "approved_with_scientific_environment_and_distribution_authorization_limitations")
        self.assertEqual(self.status["current_governance"]["m7_04"], "accepted; not reopened by G5-F02")
        self.assertEqual(self.status["current_governance"]["g5_f01"], "resolved_and_preserved")
        self.assertEqual(self.status["finding"]["pm_disposition"], "resolved_by_fresh_independent_pm_review")
        self.assertEqual(self.status["final_pm_decision"]["pr21_merge_commit"], "6495bda01daae557a084e8863d2148e08be6cca7")
        self.assertFalse(self.status["final_pm_decision"]["publication_or_release_authorized"])
        final_record = read(".agents/evidence/G5-PM-final-decision-20261101.md")
        self.assertIn("issuecomment-6558975009", final_record)
        self.assertIn("G5-F02 RESOLVED", final_record)
        self.assertIn("no affirmative permission", final_record.lower())
        self.assertEqual(self.old_pm_decision["decision"], "approved_with_limitations")
        self.assertIn("suspended pending correction and fresh review", self.erratum)
        self.assertEqual(self.state["engineering"]["start_authorization_record"]["authorization_id"], "M7-AUTH-20261031-OPTION-B")

    def test_historical_release_claim_records_are_clearly_supplemented(self) -> None:
        records = (
            ".agents/evidence/M7-001-authorization-20261031.md",
            ".agents/evidence/M7-005-authorization-20261101.md",
            ".agents/evidence/M7-005-owner-no-release-decision-20261101.md",
            ".agents/evidence/M7-005-acceptance-20261101.md",
            ".agents/evidence/M7-005-failure-history-20261101.md",
            ".agents/evidence/M7-005-G5-F01-remediation-20261101.md",
            ".agents/evidence/M7-005-source-verification-20261101.md",
            ".agents/evidence/M7-G5-review-handover-20261101.md",
            ".agents/evidence/G5-PM-acceptance-20261101.md",
            ".agents/evidence/G5-governance-closeout-handover-20261101.md",
        )
        for relative in records:
            with self.subTest(record=relative):
                self.assertIn("G5-F02", read(relative)[:900])

    def test_hash_pinned_g4_acceptance_record_remains_unchanged_and_is_classified_historically(self) -> None:
        import hashlib

        accepted = read(".agents/evidence/G4-PM-acceptance-20261101.md").encode("utf-8")
        self.assertEqual(
            hashlib.sha256(accepted).hexdigest(),
            "b26a07a792bcd07ffccca5f79005c0ae37d290ef49372a965d62f1dafc2c4d47",
        )
        self.assertIn("G4-PM-acceptance-20261101.md", self.erratum)
        self.assertIn("Historical PM status assessment, not a primary owner authorization", self.erratum)

    def test_research_results_and_limitations_are_not_changed(self) -> None:
        policies = self.m7_results["analysis"]["tracks"]["M7_option_B_ALE"]["policy_summary"]["by_policy"]
        self.assertEqual(len(policies), 9)
        self.assertEqual(sum(policy["scheduled"] for policy in policies.values()), 90)
        self.assertEqual(sum(policy["attempt_process_count"] for policy in policies.values()), 90)
        self.assertEqual(sum(policy["losses"] for policy in policies.values()), 60)
        self.assertEqual(sum(policy["incomplete"] for policy in policies.values()), 30)
        self.assertEqual(sum(policy["wins"] for policy in policies.values()), 0)
        self.assertEqual(sum(policy["draws"] for policy in policies.values()), 0)
        reconcile = self.m7_results["analysis"]["tracks"]["M7_option_B_ALE"]["summary_reconciliation"]
        self.assertTrue(reconcile["summary_matches_verified_schedule"])
        self.assertEqual(reconcile["reset_observed_cells_from_raw"], 90)
        self.assertIn("9/30", self.closeout)
        self.assertIn("no valid paired confidence interval", self.closeout.lower())
        self.assertIn("The findings do not establish RL superiority", self.closeout)
        self.assertIn("Elo not reported", self.closeout)
        self.assertIn("RSK-014", self.closeout)
        self.assertIn("PM6-F06", self.closeout)
        self.assertEqual([self.tasks[f"M7-{i:03d}"]["status"] for i in range(1, 6)], ["done"] * 5)

    def test_final_acceptance_matrix_covers_every_milestone(self) -> None:
        for milestone in ("M0-01", "M1-01", "M2-01", "M3-01", "M4-01", "M5-01", "M6-01", "M7-01", "M7-04", "M7-05"):
            with self.subTest(milestone=milestone):
                self.assertIn(milestone, self.closeout)
        self.assertIn("M7-05 | Engineering complete; independently accepted with limitations", self.closeout)
        self.assertIn("PR #21", self.closeout)
        self.assertIn("G5-F02 is resolved", self.closeout)


if __name__ == "__main__":
    unittest.main()
