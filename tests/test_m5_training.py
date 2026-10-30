import random
import unittest
import chess
import torch
from videochess_rl.baselines import RandomLegalAgent
from videochess_rl.m5_seeding import paired_seed_schedule
from videochess_rl.rl.network import make_scratch_scorer, clone_target
from videochess_rl.rl.cli import _campaign_usage_with_active_run
from videochess_rl.rl.training import DoubleDqnLearner, epsilon_at, select_action, _features, run_training_episodes
from videochess_rl.rl.transition import Transition
from videochess_rl.simulator import ChessSimulator


def make_transition(index):
    sim=ChessSimulator(RandomLegalAgent(),max_decisions=1)
    obs=sim.reset(seed=100+index,opponent_seed=200+index,agent_color=chess.WHITE)
    result=sim.step(sorted(sim.legal_moves,key=lambda m:m.uci())[0])
    return Transition.from_step(obs,result,run_id='r',attempt_id='a',episode_index=index,decision_index=index,
        training_seed=20261104,seed_schedule=paired_seed_schedule('m5-double-dqn-paired-v1',20261104,index))


class TrainingTests(unittest.TestCase):
    def test_campaign_budget_counts_only_the_uncommitted_active_run(self):
        committed_after_first_run = 1010.0
        second_run_started = 70.0
        now = 80.0
        self.assertEqual(
            _campaign_usage_with_active_run(committed_after_first_run, second_run_started, now),
            1020.0,
        )

    def test_epsilon_schedule_and_legal_exploration(self):
        self.assertEqual(epsilon_at(0),1.0); self.assertAlmostEqual(epsilon_at(37500),.05); self.assertEqual(epsilon_at(50000),.05)
        model=make_scratch_scorer(representation_seed=2,q_head_seed=3); features=_features(tuple())
        action=select_action(model,features,epsilon=1,rng=random.Random(3),device=torch.device('cpu'))
        self.assertIn(action,features.candidate_uci)

    def test_real_batch_update_changes_online_then_syncs(self):
        model=make_scratch_scorer(representation_seed=4,q_head_seed=5)
        learner=DoubleDqnLearner(model,seed=6,config={'batch_size':2,'replay_warmup_transitions':2,'target_sync_interval_gradient_updates':2})
        initial=[x.detach().clone() for x in learner.target.parameters()]
        for i in range(2): learner.step_decision(make_transition(i))
        self.assertEqual(learner.optimizer_updates,0)
        update=learner.update(); self.assertIsNotNone(update)
        self.assertTrue(torch.isfinite(torch.tensor(update['loss'])))
        self.assertEqual(learner.optimizer_updates,1)
        self.assertTrue(all(torch.equal(a,b) for a,b in zip(initial,learner.target.parameters())))
        learner.update()
        self.assertEqual(learner.optimizer_updates,2); self.assertEqual(learner.target_syncs,1)
        self.assertTrue(all(torch.equal(a,b) for a,b in zip(learner.online.parameters(),learner.target.parameters())))

    def test_target_initialization_equals_online(self):
        model=make_scratch_scorer(representation_seed=8,q_head_seed=9); target=clone_target(model)
        self.assertTrue(all(torch.equal(a,b) for a,b in zip(model.parameters(),target.parameters())))
        self.assertTrue(all(p.grad is None for p in target.parameters()))

    def test_decision_cap_mid_episode_keeps_real_transitions_without_synthetic_flags(self):
        learner=DoubleDqnLearner(make_scratch_scorer(representation_seed=18,q_head_seed=19),seed=20,
            exploration_seed=21,config={'batch_size':32,'replay_warmup_transitions':1024})
        rows=[]
        summary=run_training_episodes(learner,training_seed=20261104,arm='scratch',run_id='smoke',
            attempt_id='attempt-0000',max_decisions=5,on_transition=lambda _learner,row,_update:rows.append(row))
        self.assertEqual(summary['valid_decisions'],5)
        self.assertEqual(summary['completed_episodes'],0)
        self.assertTrue(summary['final_episode_incomplete'])
        self.assertEqual(len(rows),5)
        self.assertFalse(any(row.terminated or row.truncated for row in rows))
        self.assertEqual(learner.transitions,5)
