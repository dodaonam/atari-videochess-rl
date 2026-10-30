import json
import unittest
from pathlib import Path
from videochess_rl.rl.targets import double_dqn_target


class TargetTests(unittest.TestCase):
    def test_actual_target_calculator_matches_retained_oracles(self):
        cases=json.loads(Path('tests/fixtures/m5_double_dqn_targets.json').read_text())['cases']
        for case in cases:
            row=double_dqn_target(reward=case['reward_agent'],gamma=.9,terminated=case['bootstrap_mask']==0,
                truncated=case.get('id')=='valid_time_limit_truncation_bootstraps',legal_uci=case['legal_uci'],
                q_online_by_uci=case['q_online_by_uci'],q_target_by_uci=case['q_target_by_uci'])
            self.assertEqual(row.selected_uci,case['expected_online_action_uci'])
            self.assertEqual(row.target_value,case['expected_target_value'])
            self.assertAlmostEqual(row.bellman_target,case['expected_bellman_target'],places=12)

    def test_online_selection_and_semantic_mismatch(self):
        args=dict(reward=0,gamma=.99,terminated=False,truncated=False,legal_uci=('b1c3','g1f3'),
            q_online_by_uci={'b1c3':5,'g1f3':0},q_target_by_uci={'b1c3':-2,'g1f3':100})
        result=double_dqn_target(**args)
        self.assertEqual((result.selected_uci,result.target_value),('b1c3',-2))
        args['q_target_by_uci']={'b1c3':1}
        with self.assertRaises(ValueError): double_dqn_target(**args)
