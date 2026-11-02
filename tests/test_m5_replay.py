import unittest
from unittest.mock import patch
from test_m5_transition import make_transition
from videochess_rl.rl.replay import ReplayBuffer, ReplayJournal
from videochess_rl.rl.transition import Transition


class ReplayTests(unittest.TestCase):
    def test_capacity_sampling_and_rng_recovery(self):
        rows=[make_transition(i) for i in (10,11,12)]
        buffer=ReplayBuffer(2,seed=5)
        for row in rows: buffer.insert(row)
        self.assertEqual((len(buffer),buffer.evicted_count),(2,1))
        recovered=ReplayBuffer.from_state_dict(buffer.state_dict())
        self.assertEqual([r.transition_id for r in buffer.sample(2)],[r.transition_id for r in recovered.sample(2)])
        with self.assertRaises(ValueError): recovered.insert(rows[-1])

    def test_journal_hash_chain_and_prefix_integrity(self):
        journal=ReplayJournal(self._tmp_path/'replay.jsonl')
        first,second=make_transition(20),make_transition(21)
        h1=journal.append(first); h2=journal.append(second)
        self.assertEqual(h2['record_count'],2)
        self.assertEqual(journal.verify(record_count=1,chain_sha256=h1['chain_sha256']),(first,))
        self.assertEqual(journal.verify(),(first,second))
        journal.path.write_bytes(journal.path.read_bytes().replace(b'"reward":0.0',b'"reward":0.5',1))
        with self.assertRaises(ValueError): journal.verify()

    def test_journal_tail_restore_hashes_full_prefix_but_reconstructs_only_capacity(self):
        journal=ReplayJournal(self._tmp_path/'tail.jsonl')
        rows=[make_transition(i) for i in (30,31,32,33)]
        head=None
        for row in rows: head=journal.append(row)
        with patch('videochess_rl.rl.replay.Transition.from_json', wraps=Transition.from_json) as decode:
            restored=journal.verify(record_count=head['record_count'],chain_sha256=head['chain_sha256'],retain_last=2)
        self.assertEqual(tuple(row.transition_id for row in restored),
                         tuple(row.transition_id for row in rows[-2:]))
        self.assertEqual(decode.call_count,2)
        # A bad record outside the retained replay window still invalidates the
        # full pinned chain; suffix-only materialization is not suffix-only integrity.
        content=journal.path.read_bytes().replace(b'"reward":0.0',b'"reward":0.5',1)
        journal.path.write_bytes(content)
        with self.assertRaises(ValueError):
            journal.verify(record_count=head['record_count'],chain_sha256=head['chain_sha256'],retain_last=2)

    def setUp(self):
        import tempfile
        self._tmp=tempfile.TemporaryDirectory(); from pathlib import Path
        self._tmp_path=Path(self._tmp.name)
    def tearDown(self): self._tmp.cleanup()
