import unittest
from dataclasses import replace
import chess
from videochess_rl.baselines import RandomLegalAgent
from videochess_rl.m5_seeding import paired_seed_schedule
from videochess_rl.rl.transition import Transition
from videochess_rl.simulator import ChessSimulator


def make_transition(seed=10):
    sim=ChessSimulator(RandomLegalAgent(),max_decisions=1)
    obs=sim.reset(seed=seed,opponent_seed=seed+1,agent_color=chess.WHITE)
    result=sim.step(sorted(sim.legal_moves,key=lambda m:m.uci())[0])
    schedule=paired_seed_schedule('m5-double-dqn-paired-v1',20261104,0)
    return Transition.from_step(obs,result,run_id='run',attempt_id='attempt-0000',episode_index=0,
        decision_index=0,training_seed=20261104,seed_schedule=schedule)


class TransitionTests(unittest.TestCase):
    def test_real_simulator_transition_roundtrip_and_truncation(self):
        row=make_transition()
        self.assertTrue(row.truncated); self.assertFalse(row.terminated); self.assertEqual(row.reward,0.0)
        self.assertEqual(len(row.history_after),2)
        self.assertEqual(Transition.from_json(row.to_json()),row)
        row.validate()

    def test_corrupt_history_is_rejected(self):
        value=make_transition().to_json(); value['selected_uci']='e2e5'
        with self.assertRaises(ValueError): Transition.from_json(value)

    def test_transition_identity_and_pair_seed_provenance_are_bound(self):
        value=make_transition().to_json(); value['transition_id']='0'*64
        with self.assertRaises(ValueError): Transition.from_json(value)
        value=make_transition().to_json(); value['seed_schedule']['episode_seed']+=1
        with self.assertRaises(ValueError): Transition.from_json(value)

    def test_non_object_seed_schedule_is_rejected(self):
        row=replace(make_transition(),seed_schedule=None)
        with self.assertRaisesRegex(ValueError,'seed schedule'):
            row.validate()
