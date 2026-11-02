import unittest
import json
import tempfile
from pathlib import Path
import torch
from videochess_rl.rl.evaluate import (planned_scenarios, evaluate_policy, QPolicy, summarize_games,
    paired_white_black_comparison, paired_capped_reward_differences, require_evaluation_snapshot_stage)
from videochess_rl.rl.evaluation_journal import (EvaluationEventJournal, EvaluationJournalCorruption,
    read_evaluation_event_journal, recover_policy_attempt_rows)
from videochess_rl.rl.network import make_scratch_scorer


class EvaluationTests(unittest.TestCase):
    def test_frozen_evaluation_scenario_schedule(self):
        rows=planned_scenarios()
        self.assertEqual(len(rows),100)
        self.assertEqual({r['evaluation_seed'] for r in rows},set(range(20261130,20261155)))
        self.assertEqual({r['opponent_id'] for r in rows},{'random_legal','simple_material_heuristic'})
        self.assertEqual({r['agent_color'] for r in rows},{'white','black'})
        self.assertEqual(len({(r['evaluation_seed'],r['opponent_id'],r['agent_color']) for r in rows}),100)

    def test_frozen_policy_evaluation_does_not_mutate_model(self):
        model=make_scratch_scorer(representation_seed=1,q_head_seed=2).eval()
        policy=QPolicy(model,policy_id='scratch:test:pre_rl',checkpoint_sha256='0'*64)
        before=[x.detach().clone() for x in model.parameters()]
        events=[];progress=[]
        rows=evaluate_policy(policy,policy_id=policy.policy_id,seeds=[20261130],max_wall_seconds=60,
            attempt_id='test-attempt-0000',on_scenario_event=lambda event,payload:events.append((event,payload)),
            progress_callback=lambda payload:progress.append(payload))
        self.assertEqual(len(rows),4)
        self.assertTrue(all(r['status']=='completed_game' for r in rows))
        self.assertEqual(summarize_games(rows)['game_rows'],4)
        self.assertEqual([event for event,_ in events].count('scenario_started'),4)
        self.assertEqual([event for event,_ in events].count('scenario_completed'),4)
        self.assertTrue(all(row['evaluation_attempt_id']=='test-attempt-0000' for row in rows))
        self.assertTrue(progress)
        self.assertTrue(all(torch.equal(a,b) for a,b in zip(before,model.parameters())))
        self.assertTrue(all(p.grad is None for p in model.parameters()))

    def test_snapshot_stage_identity_is_exact(self):
        require_evaluation_snapshot_stage({'stage':'pre_rl'},'pre_rl')
        with self.assertRaises(ValueError):
            require_evaluation_snapshot_stage({'stage':'post_rl'},'pre_rl')

    def test_evaluation_event_journal_recovers_completed_rows_and_checks_chain(self):
        policy='warm:20261104:post_rl'
        row={'policy_id':policy,'evaluation_seed':20261130,'opponent_id':'random_legal',
             'agent_color':'white','scenario_attempt_id':'attempt:game-1',
             'status':'completed_game','agent_reward':1.0,'truncated':False}
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)/'policy'
            path=root/'events-attempt-0000.jsonl'
            with EvaluationEventJournal(path,policy_id=policy,attempt_id='evaluation-attempt-0000') as journal:
                journal.append('scenario_started',{'scenario_attempt_id':'attempt:game-1',
                    'evaluation_seed':20261130,'opponent_id':'random_legal','agent_color':'white','scenario_seed':17})
                journal.append('scenario_progress',{'scenario_attempt_id':'attempt:game-1',
                    'agent_decisions':3,'plies':6,'history_uci':['e2e4','e7e5']})
                journal.append('scenario_completed',{'scenario_attempt_id':'attempt:game-1','row':row})
            events,diagnostics=read_evaluation_event_journal(path)
            self.assertEqual(len(events),3)
            self.assertEqual(diagnostics,[])
            rows,diagnostics=recover_policy_attempt_rows(root,policy)
            self.assertEqual(diagnostics,[])
            self.assertEqual(rows,[row])
            self.assertEqual(path.read_bytes().count(b'\n'),3)

    def test_torn_final_journal_tail_is_preserved_as_interrupted_scenario(self):
        policy='scratch:20261106:post_rl'
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)/'policy'; path=root/'events-attempt-0000.jsonl'
            with EvaluationEventJournal(path,policy_id=policy,attempt_id='evaluation-attempt-0000') as journal:
                journal.append('scenario_started',{'scenario_attempt_id':'attempt:game-7',
                    'evaluation_seed':20261131,'opponent_id':'simple_material_heuristic',
                    'agent_color':'black','scenario_seed':23})
                journal.append('scenario_progress',{'scenario_attempt_id':'attempt:game-7',
                    'agent_decisions':9,'plies':18,'history_uci':['e2e4','e7e5']})
            original=path.read_bytes(); path.write_bytes(original+b'{"schema":"torn')
            preserved=path.read_bytes()
            rows,diagnostics=recover_policy_attempt_rows(root,policy)
            self.assertEqual(path.read_bytes(),preserved)
            self.assertEqual(len(rows),1)
            self.assertEqual(rows[0]['status'],'interrupted_scenario_attempt')
            self.assertEqual(rows[0]['agent_decisions'],9)
            self.assertIsNone(rows[0]['agent_reward'])
            self.assertIsNone(rows[0]['truncated'])
            self.assertEqual(diagnostics[0]['status'],'malformed_final_record')
            with self.assertRaises(FileExistsError):
                EvaluationEventJournal(path,policy_id=policy,attempt_id='wrongly-reused-file')

    def test_non_tail_evaluation_journal_corruption_is_rejected(self):
        policy='warm:20261105:pre_rl'
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'events-attempt-0000.jsonl'
            with EvaluationEventJournal(path,policy_id=policy,attempt_id='evaluation-attempt-0000') as journal:
                journal.append('scenario_started',{'scenario_attempt_id':'attempt:game-1'})
                journal.append('scenario_completed',{'scenario_attempt_id':'attempt:game-1','row':{'status':'completed_game'}})
            raw=path.read_bytes(); path.write_bytes(b'corrupt\n'+raw.splitlines(keepends=True)[1])
            with self.assertRaises(EvaluationJournalCorruption):
                read_evaluation_event_journal(path)

    def test_white_black_comparison_resamples_evaluation_seed_clusters(self):
        rows=[]
        for scenario in planned_scenarios():
            rows.append({**scenario,'status':'completed_game','agent_reward':1.0 if scenario['agent_color']=='white' else -1.0,
                         'truncated':False})
        summary=paired_white_black_comparison(rows,iterations=1000)
        self.assertEqual(summary['matched_color_pairs'],50)
        self.assertEqual(summary['planned_color_pairs'],50)
        self.assertEqual(summary['mean_white_minus_black_score'],1.0)
        self.assertEqual(summary['evaluation_seed_cluster_bootstrap']['evaluation_seed_clusters'],25)
        self.assertEqual(summary['evaluation_seed_cluster_bootstrap']['ci_95_evaluation_seed_cluster'],[1.0,1.0])
        rows[0]['truncated']=True
        censored=paired_white_black_comparison(rows,iterations=100)
        self.assertEqual(censored['matched_color_pairs'],49)
        self.assertIsNone(censored['evaluation_seed_cluster_bootstrap'])

    def test_capped_reward_pairing_keeps_truncations_as_observed_zero_not_wdl(self):
        a=[];b=[]
        for scenario in planned_scenarios():
            base={**scenario,'status':'completed_game'}
            if scenario['evaluation_seed']==20261130 and scenario['opponent_id']=='random_legal' and scenario['agent_color']=='white':
                a.append({**base,'agent_reward':0.0,'truncated':True})
                b.append({**base,'agent_reward':1.0,'truncated':False})
            else:
                a.append({**base,'agent_reward':1.0,'truncated':False})
                b.append({**base,'agent_reward':0.0,'truncated':False})
        differences=paired_capped_reward_differences(a,b)
        self.assertEqual(len(differences),100)
        timeout=next(row for row in differences if row['evaluation_seed']==20261130 and
                     row['opponent_id']=='random_legal' and row['agent_color']=='white')
        self.assertTrue(timeout['a_truncated'])
        self.assertEqual(timeout['difference'],-0.5)
        self.assertEqual(sum(row['difference'] for row in differences)/100,0.49)
        with self.assertRaisesRegex(ValueError,'identical completed scenario keys'):
            paired_capped_reward_differences(a[:-1],b)
