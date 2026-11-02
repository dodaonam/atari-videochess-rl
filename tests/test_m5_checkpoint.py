import tempfile
import unittest
from pathlib import Path
import random
import unittest.mock
import numpy as np
import torch
from test_m5_transition import make_transition
from videochess_rl.rl.checkpoint import (save_training_checkpoint, restore_training_checkpoint,
    verify_training_checkpoint, load_training_checkpoint_bundle)
from videochess_rl.rl.network import make_scratch_scorer
from videochess_rl.rl.replay import ReplayJournal
from videochess_rl.rl.training import DoubleDqnLearner
from videochess_rl.rl.transition import Transition


def _nested_equal(left,right):
    if isinstance(left,torch.Tensor) and isinstance(right,torch.Tensor): return torch.equal(left,right)
    if isinstance(left,dict) and isinstance(right,dict):
        return left.keys()==right.keys() and all(_nested_equal(left[k],right[k]) for k in left)
    if isinstance(left,(list,tuple)) and isinstance(right,(list,tuple)):
        return len(left)==len(right) and all(_nested_equal(a,b) for a,b in zip(left,right))
    if isinstance(left,np.ndarray) and isinstance(right,np.ndarray): return np.array_equal(left,right)
    return left==right


class CheckpointTests(unittest.TestCase):
    def setUp(self): self.tmp=tempfile.TemporaryDirectory(); self.root=Path(self.tmp.name)
    def tearDown(self): self.tmp.cleanup()

    def test_episode_boundary_checkpoint_roundtrip_and_corruption(self):
        rows=[make_transition(i) for i in (44,45,46)]
        journal=ReplayJournal(self.root/'replay.jsonl'); head=None
        learner=DoubleDqnLearner(make_scratch_scorer(representation_seed=2,q_head_seed=3),seed=4,
                                 config={'replay_capacity':2,'replay_warmup_transitions':1,'batch_size':1})
        for row in rows:
            learner.step_decision(row); head=journal.append(row)
        # Populate AdamW state so the test verifies optimizer recovery, not only
        # the empty optimizer produced before the first gradient update.
        learner.optimizer.zero_grad(set_to_none=True)
        next(learner.online.parameters()).square().mean().backward()
        learner.optimizer.step(); learner.optimizer_updates=1
        learner.completed_episodes=1
        checkpoint=self.root/'episode-1.pt'; identity={'pair_id':'p','arm':'scratch','training_seed':20261104,
            'code_sha256':'c','environment':{'torch':torch.__version__}}
        save_training_checkpoint(checkpoint,learner,identity=identity,journal=journal,journal_head=head,
            episode_complete=True,resource_accounting={'elapsed_seconds':1})
        bundle=load_training_checkpoint_bundle(checkpoint)
        clone=DoubleDqnLearner(make_scratch_scorer(representation_seed=99,q_head_seed=3),seed=88,
                               config={'replay_capacity':2,'replay_warmup_transitions':1,'batch_size':1})
        with unittest.mock.patch('videochess_rl.rl.replay.Transition.from_json',wraps=Transition.from_json) as decode:
            result=restore_training_checkpoint(checkpoint,clone,expected_identity={'pair_id':'p','arm':'scratch'})
        self.assertEqual(decode.call_count,2)
        self.assertEqual(result['counters']['valid_decisions'],3); self.assertEqual(len(clone.replay),2)
        self.assertEqual([row.transition_id for row in clone.replay.transitions],
                         [row.transition_id for row in rows[-2:]])
        self.assertEqual(clone.replay.inserted_count,3); self.assertEqual(clone.replay.evicted_count,1)
        self.assertEqual(clone.replay.rng.getstate(),tuple(bundle['replay_control']['rng_state']))
        self.assertEqual(clone.exploration_rng.getstate(),tuple(bundle['exploration_rng_state']))
        self.assertTrue(_nested_equal(clone.online.state_dict(),bundle['online']))
        self.assertTrue(_nested_equal(clone.target.state_dict(),bundle['target']))
        self.assertTrue(_nested_equal(clone.optimizer.state_dict(),bundle['optimizer']))
        self.assertEqual(random.getstate(),tuple(bundle['python_rng_state']))
        np_state=np.random.get_state(); saved_numpy=bundle['numpy_rng_state']
        self.assertEqual(np_state[0],saved_numpy['bit_generator'])
        self.assertTrue(np.array_equal(np_state[1],np.asarray(saved_numpy['keys'],dtype=np.uint32)))
        self.assertEqual((np_state[2],np_state[3],np_state[4]),
                         (saved_numpy['position'],saved_numpy['has_gauss'],saved_numpy['cached_gaussian']))
        self.assertTrue(torch.equal(torch.get_rng_state(),bundle['torch_rng_state']))
        verify_training_checkpoint(checkpoint); checkpoint.write_bytes(checkpoint.read_bytes()+b'broken')
        with self.assertRaises(ValueError): verify_training_checkpoint(checkpoint)

    def test_checkpoint_refuses_live_episode(self):
        learner=DoubleDqnLearner(make_scratch_scorer(representation_seed=2,q_head_seed=3),seed=4)
        journal=ReplayJournal(self.root/'empty.jsonl')
        with self.assertRaises(ValueError): save_training_checkpoint(self.root/'live.pt',learner,identity={},journal=journal,
            journal_head={'record_count':0,'chain_sha256':'0'*64},episode_complete=False,resource_accounting={})
