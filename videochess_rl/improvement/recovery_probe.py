"""Compare interrupted/replayed warm training with its uninterrupted continuation."""
import json
from pathlib import Path
import torch
from .common import ROOT,ARTIFACTS,write,sha
from .m5 import execute,config_default
from videochess_rl.rl.checkpoint import load_training_checkpoint_bundle


def equal(a,b):
    if isinstance(a,torch.Tensor):return torch.equal(a,b)
    if isinstance(a,dict):return a.keys()==b.keys() and all(equal(a[k],b[k]) for k in a)
    if isinstance(a,(tuple,list)):return len(a)==len(b) and all(equal(x,y) for x,y in zip(a,b))
    return a==b


def semantic(row):
    return tuple(row[k] if not isinstance(row[k],list) else tuple(row[k]) for k in ('episode_index','decision_index','history_before','selected_uci','history_after','reward','terminated','truncated'))


def main():
    selection=json.loads((ARTIFACTS/'m4-selection.json').read_text())['selected']
    root=ARTIFACTS/'recovery-probe';root.mkdir(exist_ok=False)
    c=config_default()
    left,m4,original=execute(c,ROOT/selection['checkpoint'],selection['sha256'],root/'original',stop_at=2300)
    checkpoints=sorted((root/'original').glob('resume-*.pt'))
    if not checkpoints:raise RuntimeError('no episode-boundary checkpoint produced')
    pinned=checkpoints[0]
    right,restored_m4,recovered=execute(c,ROOT/selection['checkpoint'],selection['sha256'],root/'recovered',resume=pinned,stop_at=2300)
    tests=dict(online=equal(left.online.state_dict(),right.online.state_dict()),target=equal(left.target.state_dict(),right.target.state_dict()),optimizer=equal(left.optimizer.state_dict(),right.optimizer.state_dict()),exploration_rng=left.exploration_rng.getstate()==right.exploration_rng.getstate(),replay_rng=left.replay.rng.getstate()==right.replay.rng.getstate(),frozen_m4=equal(m4.state_dict(),restored_m4.state_dict()),action_source_counters=original['action_sources']==recovered['action_sources'],semantic_replay=[semantic(r.to_json()) for r in left.replay.transitions]==[semantic(r.to_json()) for r in right.replay.transitions],unique_replay_ids=len({r.transition_id for r in right.replay.transitions})==len(right.replay),cumulative_wall=recovered['cumulative_wall_seconds']>=original['wall_seconds']+recovered['wall_seconds']-.1)
    for k in ('valid_decisions','transitions','optimizer_updates','completed_episodes','target_syncs'):
        tests[k]=getattr(left,k)==getattr(right,k)
    write(root/'verification.json',dict(tests=tests,passed=all(tests.values()),checkpoint=str(pinned.relative_to(ROOT)),checkpoint_sha256=sha(pinned),pinned_counters=load_training_checkpoint_bundle(pinned)['counters'],discarded_tail_decisions=recovered['repeated_parent_tail_decisions'],new_attempt_ids='Expected to differ for replayed work; semantic transitions and model/optimizer/RNG states must match.',official_run=False))
    print(json.dumps(tests),flush=True)
    if not all(tests.values()):raise AssertionError('recovery equivalence failed')


if __name__=='__main__':main()
