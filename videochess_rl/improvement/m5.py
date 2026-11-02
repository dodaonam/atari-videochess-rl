"""Single warm Double DQN runner. Official execution belongs to Phase 2."""
from __future__ import annotations
from collections import Counter
import argparse
import hashlib
import json
import math
import os
import platform
from pathlib import Path
import random
import shutil
import time

import chess
import torch
import numpy as np
from videochess_rl.baselines import RandomLegalAgent, SimpleHeuristicAgent
from videochess_rl.model.features import encode_board, replay_observation_history
from videochess_rl.model.training import configure_determinism
from videochess_rl.rl.training import DoubleDqnLearner, _batch, epsilon_at
from videochess_rl.rl.network import make_warm_scorer
from videochess_rl.rl.replay import JOURNAL_SCHEMA
from .journal import SafeReplayJournal as ReplayJournal
from videochess_rl.rl.checkpoint import save_training_checkpoint, restore_training_checkpoint, load_training_checkpoint_bundle
from videochess_rl.rl.transition import Transition
from videochess_rl.m5_seeding import EXPERIMENT_ID as TRANSITION_SEED_DOMAIN, paired_seed_schedule
from videochess_rl.simulator import ChessSimulator
from .learner import ImprovementLearner, features as cached_features
from .m4 import load_source
from .snapshot import save_snapshot
from . import SEED, EXPERIMENT_ID
from .common import ROOT, ARTIFACTS, write, sha, utc, revision
from videochess_rl.data.contracts import digest


def config_default():
    return json.loads((ROOT/'configs/improvement/m5.json').read_text())


def validate_config(c):
    expected=config_default()
    if set(c)!=set(expected):raise ValueError('unknown or missing M5 config keys')
    fixed=('experiment_id','algorithm','training_seed','initialization','scratch_training','optimizer','loss','gradient_updates_per_decision','target_sync_interval_gradient_updates','reward_win','reward_loss','reward_draw','reward_nonterminal','reward_shaping','snapshot_interval_decisions')
    for k in fixed:
        if c[k]!=expected[k] or type(c[k]) is not type(expected[k]):raise ValueError(f'unsupported {k}')
    for k,v in c.items():
        if isinstance(expected[k],(int,float)) and not isinstance(expected[k],bool) and (isinstance(v,bool) or not isinstance(v,(int,float))):raise ValueError(k)
        if isinstance(v,(int,float)) and not isinstance(v,bool) and (not math.isfinite(v) or (v<0 and k!='reward_loss')):raise ValueError(k)
    for k in ('batch_size','replay_capacity','replay_warmup_transitions','agent_decisions','epsilon_decay_decisions','maximum_agent_decisions_per_episode','m4_guidance_end_decision','checkpoint_interval_decisions','snapshot_interval_decisions','threads'):
        if type(c[k]) is not int or c[k]<1:raise ValueError(k)
    if c['batch_size'] not in (32,64) or c['agent_decisions']>250000:raise ValueError('batch/decision range')
    if c['replay_capacity']<max(c['batch_size'],c['replay_warmup_transitions']):raise ValueError('replay too small')
    if not 0<=c['epsilon_end']<=c['epsilon_start']<=1:raise ValueError('epsilon range')
    if not 0<=c['m4_guidance_initial']<=1 or not 0<=c['gamma']<=1:raise ValueError('probability range')
    if c['learning_rate']<=0 or c['gradient_clip_norm']<=0:raise ValueError('optimizer range')
    return c


def domain_seed(name,index=0):
    return int(digest([EXPERIMENT_ID,SEED,name,index])[:15],16)


def guidance_at(t,c):
    if type(t) is not int or t<0:raise ValueError('invalid decision count')
    return c['m4_guidance_initial']*max(0.,1.-t/c['m4_guidance_end_decision'])


def random_opponent_probability(t):
    if type(t) is not int or t<0:raise ValueError('invalid decision count')
    return .5 if t<=50000 else .35 if t<=150000 else .25


def opponent_for(t,episode):
    # Indexed independent RNG stream: fully restored by completed episode count.
    rng=random.Random(domain_seed('curriculum',episode))
    return RandomLegalAgent() if rng.random()<random_opponent_probability(t) else SimpleHeuristicAgent()


@torch.inference_mode()
def choose_action(learner,m4,features,c):
    rng=learner.exploration_rng
    eps=epsilon_at(learner.valid_decisions,start=c['epsilon_start'],end=c['epsilon_end'],decay=c['epsilon_decay_decisions'])
    if rng.random()<eps:
        if rng.random()>=guidance_at(learner.valid_decisions,c):
            return rng.choice(features.candidate_uci),'uniform_exploration'
        model,source=m4,'m4_guided'
    else:model,source=learner.online,'q_greedy'
    scores=model(**_batch((features,),learner.device))[0].tolist()
    if not scores or any(not math.isfinite(x) for x in scores):raise FloatingPointError('invalid action scores')
    index=max(range(len(scores)),key=lambda i:(scores[i],-i))
    return features.candidate_uci[index],source


def resource_snapshot(directory):
    values={}
    with open('/proc/meminfo') as f:
        mem={x.split(':')[0]:int(x.split()[1])*1024 for x in f}
    with open('/proc/self/status') as f:
        for line in f:
            if line.startswith('VmRSS:'):values['rss_bytes']=int(line.split()[1])*1024
    values.update(available_ram_bytes=mem['MemAvailable'],free_disk_bytes=shutil.disk_usage(directory).free,
                  artifact_bytes=sum(x.stat().st_size for x in Path(directory).rglob('*') if x.is_file()))
    return values


def source_identity():
    paths=sorted([* (ROOT/'videochess_rl').rglob('*.py'),ROOT/'configs/improvement/m5.json'])
    return digest({p.relative_to(ROOT).as_posix():sha(p) for p in paths})


def make_learner(c,path,checkpoint_sha):
    # Vary intra-op workers only; hold the inter-op pool at one in every
    # benchmark and fresh official process so settings remain comparable.
    configure_determinism(SEED,threads=1)
    torch.set_num_threads(c['threads'])
    if torch.get_num_interop_threads()!=1 or torch.get_num_threads()!=c['threads']:
        raise RuntimeError('requested CPU thread configuration cannot be honored')
    m4,_=load_source(path,checkpoint_sha);m4.eval().requires_grad_(False)
    online=make_warm_scorer(m4,q_head_seed=domain_seed('q_head'))
    learner=ImprovementLearner(online,seed=domain_seed('replay'),exploration_seed=domain_seed('exploration'),config={**c,'update_interval_decisions':4})
    return learner,m4


def copy_journal_prefix(source,target,count):
    """Fork only the checkpoint-pinned prefix; preserve discarded attempt evidence."""
    with Path(source).open('rb') as inp,Path(target).open('xb') as out:
        for _ in range(count):
            line=inp.readline()
            if not line:raise ValueError('short replay prefix')
            out.write(line)
        out.flush();os.fsync(out.fileno())


def valid_tail_records(path,pinned_count,pinned_hash):
    """Count only complete hash-chain records after the committed prefix."""
    previous=pinned_hash;count=0;damaged=False
    with Path(path).open('rb') as stream:
        for i,line in enumerate(stream):
            if i<pinned_count:continue
            try:
                if not line.endswith(b'\n'):raise ValueError('partial tail')
                row=json.loads(line)
                payload={k:row[k] for k in ('schema','previous','transition')}
                expected=hashlib.sha256(json.dumps(payload,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
                if row['schema']!=JOURNAL_SCHEMA or row['previous']!=previous or row['chain_sha256']!=expected:raise ValueError('invalid tail chain')
            except (ValueError,KeyError,TypeError):
                damaged=True;break
            previous=expected;count+=1
    return count,damaged


def _execute(c,checkpoint,checkpoint_sha,out,*,resume=None,stop_at=None,wall_limit=None):
    start=time.monotonic();start_utc=utc()
    validate_config(c)
    out=Path(out);out.mkdir(parents=True,exist_ok=False)
    learner,m4=make_learner(c,checkpoint,checkpoint_sha)
    identity=dict(experiment_id=EXPERIMENT_ID,training_seed=SEED,arm='warm',execution_kind='probe' if stop_at is not None else 'official',config_sha256=digest(c),code_sha256=source_identity(),m4_sha256=checkpoint_sha,runtime=dict(python=platform.python_version(),torch=str(torch.__version__),numpy=str(np.__version__),chess=str(chess.__version__),device=str(learner.device),intraop_threads=torch.get_num_threads(),interop_threads=torch.get_num_interop_threads()))
    previous_wall=0.;sources=Counter();repeated=0;damaged_tail=False
    if resume:
        bundle=load_training_checkpoint_bundle(resume)
        restore_training_checkpoint(resume,learner,expected_identity=identity)
        previous_wall=bundle['resource_accounting']['cumulative_wall_seconds']
        parent=Path(resume).parent
        if (parent/'run.json').exists():
            previous_wall=max(previous_wall,json.loads((parent/'run.json').read_text())['cumulative_wall_seconds'])
        elif (parent/'attempt.json').exists():
            from datetime import datetime,timezone
            attempt=json.loads((parent/'attempt.json').read_text())
            # Crash interval charged conservatively through recovery, including downtime.
            previous_wall=max(previous_wall,attempt['previous_wall_seconds']+(datetime.now(timezone.utc)-datetime.fromisoformat(attempt['started_at_utc'])).total_seconds())
        repeated,damaged_tail=valid_tail_records(bundle['journal']['path'],bundle['journal']['record_count'],bundle['journal']['chain_sha256'])
        sources.update(bundle['resource_accounting']['action_sources'])
        copy_journal_prefix(bundle['journal']['path'],out/'replay.jsonl',bundle['journal']['record_count'])
    # Account for every sibling attempt in this execution namespace, including
    # failed forks which never reached a new episode checkpoint.
    from datetime import datetime,timezone
    billed=0.
    for attempt_path in out.parent.glob('*/attempt.json'):
        prior=json.loads(attempt_path.read_text())
        if prior.get('identity')!=identity:continue
        report_path=attempt_path.parent/'run.json'
        if report_path.exists():
            billed+=json.loads(report_path.read_text())['wall_seconds']
        else:
            billed+=(datetime.now(timezone.utc)-datetime.fromisoformat(prior['started_at_utc'])).total_seconds()
    previous_wall=max(previous_wall,billed)
    write(out/'attempt.json',dict(identity=identity,started_at_utc=start_utc,previous_wall_seconds=previous_wall,resume=str(resume) if resume else None))
    journal=ReplayJournal(out/'replay.jsonl',verify_existing=False)
    last_checkpoint_decisions=learner.valid_decisions
    limit=c['agent_decisions'] if stop_at is None else min(stop_at,c['agent_decisions'])
    next_checkpoint=(learner.valid_decisions//c['checkpoint_interval_decisions']+1)*c['checkpoint_interval_decisions']
    snapshots=set();episode_records=[];resources=[];checkpoint_times=[]
    def snapshot():
        t=learner.valid_decisions
        if t%c['snapshot_interval_decisions']==0 and t not in snapshots:
            save_snapshot(out/f'snapshot-{t:06d}.pt',learner.online,metadata={**identity,'stage':'evaluation_only','valid_decisions':t,'source_revision':revision(),'model_config':learner.online.config.as_json(),'q_only_evaluation':True})
            snapshots.add(t)
    snapshot()
    stopped=None;last_complete=True;checkpoint_path=None
    while learner.valid_decisions<limit:
        ep=learner.completed_episodes
        # Reuse the validated low-level transition seed contract, without paired orchestration.
        schedule=paired_seed_schedule(TRANSITION_SEED_DOMAIN,SEED,ep)
        opponent=opponent_for(learner.valid_decisions,ep)
        sim=ChessSimulator(opponent,max_decisions=c['maximum_agent_decisions_per_episode'])
        obs=sim.reset(seed=int(schedule['episode_seed']),opponent_seed=int(schedule['opponent_rng_seed']),agent_color=chess.WHITE if ep%2==0 else chess.BLACK)
        while learner.valid_decisions<limit:
            elapsed=previous_wall+time.monotonic()-start
            if learner.valid_decisions%100==0:
                r=resource_snapshot(out);r.update(valid_decisions=learner.valid_decisions,cumulative_wall_seconds=elapsed,journal_bytes=journal.path.stat().st_size);resources.append(r)
                write(out/'resources.json',resources)
                if r['available_ram_bytes']<c['minimum_available_ram_bytes'] or r['free_disk_bytes']<c['minimum_free_disk_bytes'] or r['rss_bytes']>c['maximum_process_rss_bytes']:
                    stopped='resource_guard';break
            if elapsed>=c['maximum_cumulative_wall_seconds'] or (wall_limit and time.monotonic()-start>=wall_limit):
                stopped='wall_guard';break
            before=obs
            features=cached_features(tuple(obs.history_uci))
            uci,source=choose_action(learner,m4,features,c)
            result=sim.step_uci(uci)
            row=Transition.from_step(before,result,run_id=EXPERIMENT_ID,attempt_id=out.name,episode_index=ep,decision_index=learner.valid_decisions,training_seed=SEED,seed_schedule=schedule)
            # Hash-chain append is durable before in-memory mutation.
            head=journal.append(row)
            learner.step_decision(row);sources[source]+=1;obs=result.observation
            with (out/'actions.jsonl').open('a') as action_log:
                action_log.write(json.dumps(dict(transition_id=row.transition_id,decision=row.decision_index,source=source,selected_uci=uci))+'\n')
            last_complete=result.terminated or result.truncated
            snapshot()
            if last_complete:
                learner.completed_episodes+=1
                episode_records.append(dict(episode=ep,end_decision=learner.valid_decisions,opponent=opponent.policy_id,color='white' if sim.agent_color else 'black',reward=result.reward,terminated=result.terminated,truncated=result.truncated))
                if learner.valid_decisions>=next_checkpoint:
                    checkpoint_path=out/f'resume-{learner.valid_decisions:06d}.pt'
                    tick=time.monotonic()
                    save_training_checkpoint(checkpoint_path,learner,identity=identity,journal=journal,journal_head=head,episode_complete=True,resource_accounting=dict(cumulative_wall_seconds=previous_wall+time.monotonic()-start,action_sources=dict(sources),resources=resources[-1] if resources else {},source_revision=revision()))
                    checkpoint_times.append(time.monotonic()-tick)
                    last_checkpoint_decisions=learner.valid_decisions
                    next_checkpoint=(learner.valid_decisions//c['checkpoint_interval_decisions']+1)*c['checkpoint_interval_decisions']
                break
        if stopped:break
    elapsed=time.monotonic()-start
    report=dict(identity=identity,effective_decision_limit=limit,requested_probe_stop_decision=stop_at,source_revision=revision(),created_at_utc=utc(),valid_decisions=learner.valid_decisions,optimizer_updates=learner.optimizer_updates,target_syncs=learner.target_syncs,completed_episodes=learner.completed_episodes,transitions=learner.transitions,action_sources=dict(sources),wall_seconds=elapsed,cumulative_wall_seconds=previous_wall+elapsed,decisions_per_hour=(learner.valid_decisions-(bundle['counters']['valid_decisions'] if resume else 0))/elapsed*3600,final_episode_incomplete=not last_complete,stopped=stopped,last_checkpoint=str(checkpoint_path) if checkpoint_path else str(resume) if resume else None,last_checkpoint_decisions=last_checkpoint_decisions,repeated_parent_tail_decisions=repeated,ignored_damaged_parent_tail=damaged_tail,uncommitted_tail_decisions=learner.valid_decisions-last_checkpoint_decisions,checkpoint_serialization_seconds=checkpoint_times,resources=resources,episode_records=episode_records)
    write(out/'run.json',report)
    return learner,m4,report


def execute(c,checkpoint,checkpoint_sha,out,*,resume=None,stop_at=None,wall_limit=None):
    """One active attempt per private campaign namespace; no source-tree payloads."""
    import fcntl
    resolved=Path(out).resolve()
    if not resolved.is_relative_to(ARTIFACTS.resolve()):
        raise ValueError('training artifacts must remain in the ignored improvement namespace')
    out=resolved.relative_to(ROOT)
    out.parent.mkdir(parents=True,exist_ok=True)
    with (out.parent/'.execution.lock').open('a') as lock:
        try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError as exc:raise RuntimeError('another attempt is active in this namespace') from exc
        return _execute(c,checkpoint,checkpoint_sha,out,resume=resume,stop_at=stop_at,wall_limit=wall_limit)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config',type=Path,default=ROOT/'configs/improvement/m5.json')
    parser.add_argument('--checkpoint',type=Path,required=True)
    parser.add_argument('--checkpoint-sha256',required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--resume',type=Path)
    parser.add_argument('--probe-decisions',type=int)
    parser.add_argument('--phase2-official',action='store_true',help='Only use under the separate Phase 2 assignment')
    args=parser.parse_args()
    if not args.phase2_official and (args.probe_decisions is None or not 1<=args.probe_decisions<=5000):parser.error('Phase 1 requires an explicit disposable probe of at most 5000 decisions')
    c=validate_config(json.loads(args.config.read_text()))
    if args.phase2_official:
        selected=json.loads((ARTIFACTS/'m4-selection.json').read_text())['selected']
        if args.checkpoint_sha256!=selected['sha256'] or c['agent_decisions']!=250000:
            parser.error('official run requires the Phase 1 selected M4 identity and 250000-decision config')
    _,_,result=execute(c,args.checkpoint,args.checkpoint_sha256,args.output,resume=args.resume,stop_at=args.probe_decisions)
    print(json.dumps(result),flush=True)


if __name__=='__main__':main()
