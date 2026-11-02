"""Observable invariants of the independent improvement campaign."""
import copy
from dataclasses import replace
import json
from pathlib import Path
import random
import tempfile
import unittest

import chess
import torch
from videochess_rl.model.network import BehaviorScorer
from videochess_rl.model.features import encode_board
from videochess_rl.model.dataset import effective_model_input_sha256
from videochess_rl.rl.training import DoubleDqnLearner, epsilon_at
from videochess_rl.rl.network import make_warm_scorer
from videochess_rl.rl.checkpoint import load_evaluation_snapshot
from videochess_rl.improvement.data import fixed_splits, protect_positions
from videochess_rl.improvement.m4 import train_epoch, metrics, select_candidate
from videochess_rl.improvement.m5 import config_default, validate_config, guidance_at, choose_action, domain_seed, random_opponent_probability, opponent_for, copy_journal_prefix
from videochess_rl.improvement.snapshot import save_snapshot


class ImprovementTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):torch.set_num_threads(1)

    def test_parallel_parser_preserves_global_source_ordinals(self):
        from videochess_rl.improvement.data import _parse_chunk,source_chunks
        import zipfile
        pgn=b'[Event "Test"]\n[Result "1-0"]\n\n1. e4 e5 1-0\n\n'
        with tempfile.TemporaryDirectory() as d:
            archive=Path(d)/'games.zip'
            with zipfile.ZipFile(archive,'w') as z:z.writestr('games.pgn',pgn+pgn)
            source=dict(source_id='a'*64,archive_sha256='b'*64,member_name='games.pgn',archive_path=str(archive))
            chunks=list(source_chunks(source,chunk_games=1))
            self.assertEqual([c[2] for c in chunks],[0,1])
            results=[_parse_chunk(c)[0][0] for c in chunks]
            self.assertEqual([r['source_ordinal'] for r in results],[1,2])
            self.assertEqual(results[0]['normalized_game_sha256'],results[1]['normalized_game_sha256'])

    def test_fixed_splits_independent_of_order(self):
        games=[dict(normalized_game_sha256=str(i)) for i in range(5000)]
        a=fixed_splits(games,20261103)
        self.assertEqual(a,fixed_splits(list(reversed(games)),20261103))
        self.assertEqual([sum(v==s for v in a.values()) for s in ('train','validation','test')],[4000,500,500])

    def test_overlap_and_historical_exposure(self):
        rows=[dict(sample_id=str(i),normalized_game_sha256=g,board_position_signature=s) for i,(g,s) in enumerate([('a','common'),('b','common'),('b','historical'),('b','fresh'),('b','fresh')])]
        kept,purged,n=protect_positions(rows,{'a':'train','b':'test'},{'historical'},1)
        sigs={}
        for r in kept:sigs.setdefault(r['board_position_signature'],set()).add(r['split'])
        self.assertTrue(all(len(x)==1 for x in sigs.values()))
        self.assertEqual(sum(r['board_position_signature']=='fresh' for r in kept),2)
        self.assertTrue(any(reason=='historical_train_validation_exposure' for _,reason in purged))
        self.assertEqual(n,1)

    def test_config_rejects_unhonored_values(self):
        self.assertEqual(validate_config(config_default())['training_seed'],20261103)
        for k,v in [('scratch_training',True),('training_seed',[1,2]),('loss','MSE'),('agent_decisions',250001),('batch_size',16),('gamma',float('nan')),('unbound',1),('threads',1.5),('gamma',True),('learning_rate','invalid')]:
            c=config_default();c[k]=v
            with self.assertRaises(ValueError):validate_config(c)

    def test_schedules_and_opponent_recovery(self):
        c=config_default()
        for t,p in [(0,.6),(25000,.4),(50000,.2),(75000,0),(250000,0)]:self.assertAlmostEqual(guidance_at(t,c),p)
        for t,p in [(0,.5),(50000,.5),(50001,.35),(150000,.35),(150001,.25),(250000,.25)]:self.assertEqual(random_opponent_probability(t),p)
        self.assertAlmostEqual(epsilon_at(175000,decay=175000),.05)
        self.assertEqual([opponent_for(50001,i).policy_id for i in range(12)],[opponent_for(50001,i).policy_id for i in range(12)])
        self.assertEqual(len({domain_seed(n) for n in ('q_head','replay','exploration','curriculum')}),4)

    def make_pair(self):
        torch.manual_seed(11)
        m4=BehaviorScorer().eval().requires_grad_(False)
        learner=DoubleDqnLearner(make_warm_scorer(m4,q_head_seed=123),seed=1,config=config_default())
        return learner,m4

    def test_warm_head_target_frozen_and_rng(self):
        learner,m4=self.make_pair();f=encode_board(chess.Board());c=config_default()
        original={k:v.clone() for k,v in m4.state_dict().items()}
        for k,v in learner.online.state_dict().items():
            if not k.startswith('q_head.'):self.assertTrue(torch.equal(v,m4.state_dict()[k]))
            self.assertTrue(torch.equal(v,learner.target.state_dict()[k]))
        self.assertFalse(torch.equal(learner.online.q_head.weight,m4.behavior_head.weight))
        state=learner.exploration_rng.getstate()
        one=[choose_action(learner,m4,f,c) for _ in range(80)]
        learner.exploration_rng.setstate(state)
        self.assertEqual(one,[choose_action(learner,m4,f,c) for _ in range(80)])
        self.assertTrue(all(a in f.candidate_uci for a,_ in one))
        self.assertIn('m4_guided',{s for _,s in one});self.assertIn('uniform_exploration',{s for _,s in one})
        learner.valid_decisions=75000
        self.assertNotIn('m4_guided',{choose_action(learner,m4,f,c)[1] for _ in range(80)})
        for k,v in original.items():self.assertTrue(torch.equal(v,m4.state_dict()[k]))
        self.assertTrue(all(p.grad is None for p in m4.parameters()))

    def test_snapshot_boundaries_and_nonresume(self):
        learner,_=self.make_pair()
        with tempfile.TemporaryDirectory() as d:
            for t in range(0,250001,25000):
                p=Path(d)/f'{t}.pt'
                rng=torch.get_rng_state().clone()
                save_snapshot(p,learner.online,dict(valid_decisions=t,model_config=learner.online.config.as_json()))
                self.assertTrue(torch.equal(rng,torch.get_rng_state()))
                model,meta=load_evaluation_snapshot(p)
                self.assertFalse(meta['resumable'])
                for k,v in model.state_dict().items():self.assertTrue(torch.equal(v,learner.online.state_dict()[k]))
            with self.assertRaises(FileExistsError):save_snapshot(Path(d)/'0.pt',learner.online,dict(valid_decisions=0))
            with self.assertRaises(ValueError):save_snapshot(Path(d)/'1.pt',learner.online,dict(valid_decisions=1))

    def test_microbatch_expert_normalization_and_fresh_optimizer(self):
        torch.manual_seed(4)
        model=BehaviorScorer();other=copy.deepcopy(model)
        b=chess.Board();rows=[]
        for u in ('e2e4','e7e5','g1f3','b8c6'):
            rows.append(encode_board(b,target_uci=u,split='train'));b.push_uci(u)
        expert=[replace(r,target_index=(r.target_index+1)%r.candidate_count,target_uci=r.candidate_uci[(r.target_index+1)%r.candidate_count]) for r in rows]
        opt=torch.optim.AdamW(model.parameters(),lr=1e-4);opt2=torch.optim.AdamW(other.parameters(),lr=1e-4)
        self.assertFalse(opt.state);self.assertFalse(opt2.state)
        opt.step=lambda: None
        opt2.step=lambda: None
        train_epoch(model,opt,rows,1,expert,logical_batch=4,physical_batch=4)
        train_epoch(other,opt2,rows,1,expert,logical_batch=4,physical_batch=1)
        for a,b in zip(model.parameters(),other.parameters()):self.assertTrue(torch.allclose(a.grad,b.grad,atol=1e-6,rtol=1e-4))
        self.assertEqual(metrics(model,rows)['examples'],4)

    def test_selection_uses_development_and_b_guard(self):
        hist=dict(stage='historical',validation={'nll':3},simulator_score=.7,order=0)
        a=dict(stage='M4-A',validation={'nll':2},simulator_score=.8,order=1)
        b=dict(stage='M4-B',validation={'nll':2.11},simulator_score=.9,order=2)
        self.assertEqual(select_candidate([hist,a,b]),a)
        b['validation']['nll']=2.1
        self.assertEqual(select_candidate([hist,a,b]),b)
        b['simulator_score']=.8;b['validation']['nll']=2
        self.assertEqual(select_candidate([hist,a,b]),a)

    def test_optimized_ddqn_matches_reference_and_recovers(self):
        from videochess_rl.improvement.learner import ImprovementLearner
        from videochess_rl.rl.replay import ReplayJournal
        from videochess_rl.rl.transition import Transition
        from videochess_rl.rl.checkpoint import save_training_checkpoint,restore_training_checkpoint
        from videochess_rl.m5_seeding import paired_seed_schedule
        from videochess_rl.baselines import RandomLegalAgent
        from videochess_rl.simulator import ChessSimulator
        c={**config_default(),'replay_capacity':64,'replay_warmup_transitions':32}
        base,m4=self.make_pair()
        one=ImprovementLearner(copy.deepcopy(base.online),seed=8,config=c)
        ref=DoubleDqnLearner(copy.deepcopy(base.online),seed=8,config=c)
        sim=ChessSimulator(RandomLegalAgent(),max_decisions=32)
        obs=sim.reset(seed=9,agent_color=chess.WHITE)
        schedule=paired_seed_schedule('m5-double-dqn-paired-v1',20261103,0)
        rows=[]
        while True:
            result=sim.step_uci(random.Random(len(rows)+93).choice(obs.legal_moves_uci))
            row=Transition.from_step(obs,result,run_id='unit',attempt_id='unit',episode_index=0,decision_index=len(rows),training_seed=20261103,seed_schedule=schedule)
            rows.append(row);obs=result.observation
            one.step_decision(row);ref.step_decision(row)
            if result.terminated or result.truncated:break
        self.assertEqual(len(rows),32)
        for k,v in one.online.state_dict().items():self.assertTrue(torch.allclose(v,ref.online.state_dict()[k],atol=3e-6,rtol=1e-4),k)
        self.assertEqual(one.optimizer_updates,1)
        one.optimizer_updates=499
        one.update()
        self.assertEqual(one.target_syncs,1)
        for k,v in one.online.state_dict().items():self.assertTrue(torch.equal(v,one.target.state_dict()[k]))
        one.completed_episodes=1
        with tempfile.TemporaryDirectory() as d:
            journal=ReplayJournal(Path(d)/'replay')
            for row in rows:head=journal.append(row)
            save_training_checkpoint(Path(d)/'resume.pt',one,identity={'unit':1},journal=journal,journal_head=head,episode_complete=True,resource_accounting={})
            clone=ImprovementLearner(copy.deepcopy(base.online),seed=99,config=c)
            restore_training_checkpoint(Path(d)/'resume.pt',clone,expected_identity={'unit':1})
            self.assertEqual(clone.replay.rng.getstate(),one.replay.rng.getstate())
            self.assertEqual(clone.exploration_rng.getstate(),one.exploration_rng.getstate())
            self.assertEqual(clone.replay.sample(32),one.replay.sample(32))
            self.assertEqual(clone.optimizer_updates,500)
            clone.update();one.update()
            for k,v in one.online.state_dict().items():self.assertTrue(torch.equal(v,clone.online.state_dict()[k]),k)
            self.assertTrue(all(p.grad is None for p in m4.parameters()))

    def test_recovery_journal_fork_keeps_only_prefix(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'journal';p.write_bytes(b'one\ntwo\npartial')
            q=Path(d)/'fork'
            copy_journal_prefix(p,q,2)
            self.assertEqual(q.read_bytes(),b'one\ntwo\n')
            self.assertEqual(p.read_bytes(),b'one\ntwo\npartial')


if __name__=='__main__':unittest.main()
