"""Current landing-page contracts, without rejecting historical status snapshots."""
import hashlib
import json
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]


class FinalConsolidationTests(unittest.TestCase):
    def test_landing_status_agrees_with_canonical_closure(self):
        state = json.loads((ROOT / '.agents/state/PROJECT_STATE.yaml').read_text())
        tasks = json.loads((ROOT / '.agents/tasks/BACKLOG.yaml').read_text())['tasks']
        self.assertEqual(state['governance']['approved_gates'], [f'G{i}' for i in range(6)])
        self.assertTrue(all(t['status'] == 'done' for t in tasks))
        self.assertEqual(len(tasks), 20)
        self.assertIsNone(state['task_refs']['next_task_id'])
        readme = (ROOT / 'README.md').read_text()
        self.assertIn('PROJECT CLOSED WITH DOCUMENTED LIMITATIONS', readme)
        self.assertNotRegex(readme, r'M6 (?:is |remains )?(?:not authorized|not started)')
        self.assertIn('G5-F01 and G5-F02 are resolved', readme)
        current = (ROOT / '.agents/state/BLOCKERS.md').read_text().split('## Current status')[1].split('## Record format')[0]
        self.assertIn('G0–G5 are approved', current)
        self.assertNotIn('pending fresh', current)

    def test_landing_results_agree_with_structured_final_analysis(self):
        analysis = json.loads((ROOT / '.agents/evidence/M7-analysis-final-r2-20261101/m7-analysis.json').read_text())
        rows = analysis['analysis']['tracks']['M7_option_B_ALE']['policy_summary']['by_policy'].values()
        totals = {k: sum(r[k] for r in rows) for k in ('scheduled','losses','incomplete','wins','draws')}
        self.assertEqual(totals, {'scheduled':90,'losses':60,'incomplete':30,'wins':0,'draws':0})
        text = (ROOT / 'README.md').read_text()
        for claim in ('90 reset-observed attempts','60 genuine terminal White losses','30 incomplete attempts','9/30 Warm/Scratch','No calibrated Elo'):
            self.assertIn(claim, text)

    def test_historical_test_denominator_is_corrected_without_editing_log(self):
        log = (ROOT / '.agents/evidence/logs/G5-F02-final-clean-clone-full-c2-20261101.log').read_text()
        total = int(re.search(r'Ran (\d+) tests', log)[1])
        skips = int(re.search(r'OK \(skipped=(\d+)\)', log)[1])
        self.assertEqual((total, total-skips, skips), (524,521,3))
        for path in ('README.md','.agents/evidence/FINAL-CONSOLIDATION-test-count-erratum-20261102.md'):
            self.assertIn('524 executed', (ROOT/path).read_text())
            self.assertIn('521 passed', (ROOT/path).read_text())

    def test_historical_archive_exception_is_exact_and_disclosed(self):
        payload = (ROOT / '.agents/evidence/BLK-001-diagnostic-20261015-r2.zip').read_bytes()
        self.assertEqual(hashlib.sha256(payload).hexdigest(), '91b0d03907b1b6764f18991880596f9c09b90986ad982b05f106bed948f96a32')
        text = (ROOT / 'README.md').read_text()
        self.assertIn('CONSOLIDATION-01', text)
        self.assertIn('grants no third-party rights', text)
        policy = (ROOT / 'docs/02-management/PR_REVIEW_AND_INTEGRATION.md').read_text()
        self.assertIn('issuecomment-6559282303', policy)
        self.assertIn('no independent GitHub review submission', policy)

    def test_context_workflow_includes_default_branch(self):
        workflow = (ROOT / '.github/workflows/preflight.yml').read_text()
        self.assertRegex(workflow, r'branches:\s*\n\s+- initial-idea\s*\n\s+- main')
        self.assertIn('contents: read', workflow)
        self.assertNotIn('pull_request_target', workflow)


if __name__ == '__main__':
    unittest.main()
