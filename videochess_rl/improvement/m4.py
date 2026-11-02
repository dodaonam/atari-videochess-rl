"""Fixed-seed fine-tuning with bounded GP search and separate engine labels."""
from __future__ import annotations
from dataclasses import replace
import hashlib
import json
import math
from pathlib import Path
import random
import time

import chess
import chess.engine
import numpy as np
import torch
from torch.nn import functional as F

from videochess_rl.model.checkpoint import load_checkpoint, save_checkpoint
from videochess_rl.model.dataset import collate_examples, model_inputs
from videochess_rl.model.training import configure_determinism, _bounded_index_batches, _bucketed_training_batches
from videochess_rl.model.inference import BehaviorPolicy
from videochess_rl.rl.evaluate import evaluate_policy
from . import SEED, EXPERIMENT_ID, HISTORICAL_M4_SHA256
from .common import ROOT, ARTIFACTS, sha, write, read_rows, write_rows, utc, revision, usage
from .data import verify_release

SOURCE = ROOT/'artifacts/m4/m4-behavior-20261027-r4/pretrained-behavior-only.pt'


def load_source(path=SOURCE, expected_sha=HISTORICAL_M4_SHA256):
    if sha(path) != expected_sha:
        raise ValueError('M4 source SHA-256 mismatch')
    return load_checkpoint(path)


@torch.inference_mode()
def metrics(model, rows):
    model.eval()
    nll = top1 = top3 = 0
    for ids in _bounded_index_batches(tuple(rows),range(len(rows)),64):
        batch = collate_examples([rows[i] for i in ids])
        logits = model(**model_inputs(batch)).masked_fill(~batch['candidate_mask'], -torch.inf)
        target = batch['target_indices']
        nll += F.cross_entropy(logits,target,reduction='sum').item()
        ranks = logits.argsort(dim=1,descending=True,stable=True)
        top1 += (ranks[:,0]==target).sum().item()
        top3 += (ranks[:,:min(3,logits.shape[1])]==target[:,None]).any(dim=1).sum().item()
    if not rows:
        raise ValueError('empty evaluation')
    return dict(examples=len(rows),nll=nll/len(rows),top1=top1/len(rows),top3=top3/len(rows))


def train_epoch(model,optimizer,rows,epoch,expert=None,logical_batch=64,physical_batch=32):
    """Each logical human mean and independent expert mean contribute .8/.2."""
    model.train()
    expert_rng = random.Random(SEED+epoch)
    totals=[]
    rows=tuple(rows)
    for ids in _bucketed_training_batches(rows,seed=SEED+epoch,batch_size=logical_batch):
        optimizer.zero_grad(set_to_none=True)
        groups=[([rows[i] for i in ids],.8 if expert else 1.)]
        if expert:
            groups.append(([expert[expert_rng.randrange(len(expert))] for _ in ids],.2))
        loss_value=0.
        for group,weight in groups:
            for micro_ids in _bounded_index_batches(tuple(group),range(len(group)),physical_batch):
                micro=[group[i] for i in micro_ids]
                batch=collate_examples(micro)
                logits=model(**model_inputs(batch)).masked_fill(~batch['candidate_mask'],-torch.inf)
                loss=F.cross_entropy(logits,batch['target_indices'],reduction='sum')*weight/len(group)
                if not torch.isfinite(loss):raise FloatingPointError('nonfinite M4 loss')
                loss.backward()
                loss_value+=loss.item()
        norm=torch.nn.utils.clip_grad_norm_(model.parameters(),1.)
        if not torch.isfinite(norm):raise FloatingPointError('nonfinite M4 gradient')
        optimizer.step()
        totals.append(loss_value)
    return float(np.mean(totals))


def fit(source,source_sha,examples,lr,wd,epochs,patience,out,expert=None,trial=None,deadline=None):
    configure_determinism(SEED,threads=1)
    model,bundle=load_source(source,source_sha)
    optimizer=torch.optim.AdamW(model.parameters(),lr=lr,weight_decay=wd)
    assert not optimizer.state
    out=Path(out);out.mkdir(parents=True,exist_ok=False)
    best=math.inf;stale=0;ledger=[];best_path=None
    for epoch in range(1,epochs+1):
        if deadline is not None and time.monotonic()>=deadline:
            raise TimeoutError('HPO wall budget reached before next epoch')
        tick=time.monotonic()
        loss=train_epoch(model,optimizer,examples['train'],epoch,expert)
        val=metrics(model,examples['validation'])
        record=dict(epoch=epoch,train_loss=loss,validation=val,wall_seconds=time.monotonic()-tick,resources=usage())
        ledger.append(record)
        if val['nll']<best:
            best=val['nll'];stale=0
            metadata={**bundle['metadata'],'run_id':EXPERIMENT_ID,'seed':SEED,'checkpoint_role':'improvement_m4',
                'source_checkpoint_sha256':source_sha,'source_revision':revision(),'checkpoint_created_at_utc':utc(),
                'selected_epoch_for_seed':epoch,'validation_record':val,'dataset_release_id':examples['manifest']['release_id'],
                'split_counts':{k:len(examples[k]) for k in ('train','validation','test')},
                'early_stopping_state_at_checkpoint':dict(best_epoch=epoch,best_validation_nll=val['nll'],no_improvement_epochs=0,patience=patience,maximum_epochs=epochs),
                'command':__import__('sys').argv,
                'source_worktree_dirty':bool(__import__('subprocess').check_output(['git','status','--porcelain'],cwd=ROOT,text=True).strip()),
                'runtime_environment':dict(python=__import__('sys').version,torch=str(torch.__version__),numpy=np.__version__,python_chess=chess.__version__,device='cpu',intraop_threads=torch.get_num_threads(),interop_threads=torch.get_num_interop_threads()),
                'release_manifest_sha256':sha(ARTIFACTS/'dataset-v4/manifest.json'),
                'split_assignment_sha256':sha(ARTIFACTS/'dataset-v4/split.json'),
                'training_config':dict(optimizer='AdamW',learning_rate=lr,weight_decay=wd,maximum_epochs=epochs,early_stopping_patience=patience,seed=SEED,logical_batch=64,physical_batch=32,gradient_clip_norm=1.),
                'teacher_scores_or_targets_used':bool(expert),'stockfish_used_for_training_or_inference':bool(expert),'stockfish_process_used_during_training_or_inference':False,
                'label_semantics':'0.8 human plus 0.2 offline expert legal CE' if expert else 'human PGN move CE',
                'parameter_output_semantics':'uncalibrated behavior logits; not Q values'}
            best_path=out/f'epoch-{epoch:02d}.pt'
            save_checkpoint(best_path,model,metadata=metadata,optimizer_state=optimizer.state_dict())
        else:stale+=1
        write(out/'epochs.json',ledger)
        print(json.dumps(dict(stage=str(out),**record)),flush=True)
        if trial is not None:
            trial.report(val['nll'],epoch)
            if trial.number>=3 and trial.should_prune():
                import optuna
                raise optuna.TrialPruned()
        if stale>=patience:break
    summary=dict(best_checkpoint=str(best_path.relative_to(ROOT)),sha256=sha(best_path),best_validation_nll=best,epochs_completed=len(ledger),early_stopped=stale>=patience,optimizer_reinitialized=True)
    write(out/'result.json',summary)
    return summary


def hpo(examples):
    import optuna
    directory=ARTIFACTS/'hpo';directory.mkdir(exist_ok=False)
    subset=sorted(examples['train'],key=lambda x:hashlib.sha256((str(SEED)+x.sample_id).encode()).hexdigest())[:8192]
    study=optuna.create_study(study_name=EXPERIMENT_ID,storage='sqlite:///'+str(directory/'study.sqlite3'),direction='minimize',sampler=optuna.samplers.GPSampler(seed=SEED,n_startup_trials=3),pruner=optuna.pruners.SuccessiveHalvingPruner(min_resource=2,reduction_factor=2))
    for lr,wd in ((3e-4,1e-4),(1.5e-4,5e-5),(4e-4,2e-4)):
        study.enqueue_trial(dict(learning_rate=lr,weight_decay=wd))
    started=time.monotonic();deadline=started+2700
    subset_identity=hashlib.sha256('\n'.join(x.sample_id for x in subset).encode()).hexdigest()
    def objective(trial):
        lr=trial.suggest_float('learning_rate',5e-5,5e-4,log=True)
        wd=trial.suggest_float('weight_decay',1e-6,5e-4,log=True)
        trial.set_user_attr('subset_sha256',subset_identity)
        trial.set_user_attr('source_checkpoint_sha256',HISTORICAL_M4_SHA256)
        trial.set_user_attr('training_seed',SEED)
        result=fit(SOURCE,HISTORICAL_M4_SHA256,{**examples,'train':subset},lr,wd,6,6,directory/f'trial-{trial.number}',trial=trial,deadline=deadline)
        return result['best_validation_nll']
    try:
        study.optimize(objective,n_trials=8,timeout=2700,catch=(TimeoutError,))
    finally:
        write(directory/'trials.json',[dict(number=t.number,state=t.state.name,value=t.value,params=t.params,intermediate_values=t.intermediate_values,user_attrs=t.user_attrs) for t in study.trials])
    completed=[t for t in study.trials if t.state==optuna.trial.TrialState.COMPLETE]
    if len(completed)<3:raise RuntimeError('three completed initialization trials required')
    result=dict(best_params=study.best_params,best_value=study.best_value,trial=study.best_trial.number,wall_seconds=time.monotonic()-started,subset_count=len(subset),subset_sha256=subset_identity,bayesian_proposals=sum(t.number>=3 and bool(t.params) for t in study.trials),sampler='GPSampler',n_startup_trials=3)
    write(directory/'result.json',result)
    return result


def expert_labels(examples):
    directory=ARTIFACTS/'expert';directory.mkdir(exist_ok=False)
    model,_=load_source();model.eval()
    rows_by_id={p['sample_id']:p for p in read_rows(ARTIFACTS/'dataset-v4/positions.jsonl')}
    games={g['game_id']:g for g in read_rows(ARTIFACTS/'dataset-v4/games.jsonl')}
    ranked=[]
    with torch.inference_mode():
        train=examples['train']
        for ids in _bounded_index_batches(tuple(train),range(len(train)),64):
            batch=collate_examples([train[i] for i in ids]);logits=model(**model_inputs(batch)).masked_fill(~batch['candidate_mask'],-torch.inf)
            confidence=logits.softmax(-1).max(-1).values.tolist()
            for i,conf in zip(ids,confidence):
                row=train[i]; flags=row.candidate_flags
                material=int(row.board_planes[:12].sum())
                priority=(1-conf)+.15*bool(flags[:,0].any())+.25*bool(flags[:,3].any())+.2*(row.ply_index>=20 and material>12)
                ranked.append((-priority,row.sample_id,row))
    ranked.sort(key=lambda x:(x[0],x[1]))
    # Diversity: max two labels per training game, plus deterministic phase strata.
    chosen=[];per_game=Counter();seen=set()
    def phase(row):
        return 'opening' if row.ply_index<20 else 'endgame' if row.board_planes[:12].sum()<=12 else 'middlegame'
    # Expert subset only: retain diverse phases while prioritizing uncertainty,
    # checks and exchanges within each stratum. No phase quota is applied to M4 data.
    for stratum,budget in (('middlegame',3000),('opening',500),('endgame',500)):
        count=0
        for _,sid,row in ranked:
            game=rows_by_id[sid]['game_id']
            if phase(row)==stratum and per_game[game]<2 and sid not in seen:
                chosen.append(row);per_game[game]+=1;seen.add(sid);count+=1
            if count>=budget:break
    for _,sid,row in ranked:
        if len(chosen)>=4000:break
        game=rows_by_id[sid]['game_id']
        if per_game[game]<2 and sid not in seen:
            chosen.append(row);per_game[game]+=1;seen.add(sid)
    dev=sorted(examples['validation'],key=lambda x:hashlib.sha256(('expert-dev'+x.sample_id).encode()).hexdigest())[:128]
    def board_for(row):
        p=rows_by_id[row.sample_id];g=games[p['game_id']];b=chess.Board()
        for u in g['moves_uci'][:p['ply_index']]:b.push_uci(u)
        return b
    engine_sha=sha((ROOT/'.venv/bin/stockfish').resolve())
    with chess.engine.SimpleEngine.popen_uci(str(ROOT/'.venv/bin/stockfish')) as engine:
        if engine.id.get('name')!='Stockfish 19':raise ValueError('Stockfish 19 required')
        engine.configure({'Threads':1,'Hash':64})
        pilot=[]
        for row in chosen[:16]:
            b=board_for(row);tick=time.monotonic();info=engine.analyse(b,chess.engine.Limit(nodes=10000),multipv=1)[0]
            pilot.append(dict(sample_id=row.sample_id,seconds=time.monotonic()-tick,nodes=info.get('nodes'),depth=info.get('depth'),nps=info.get('nps'),legal=info['pv'][0].uci() in row.candidate_uci))
        per_position=sum(p['seconds'] for p in pilot)/len(pilot)
        nodes=min(50000,max(4000,int(10000*1500/((len(chosen)+len(dev))*per_position))))
        write(directory/'pilot.json',dict(training_phase_counts=dict(Counter(phase(row) for row in chosen)),engine=engine.id,threads=1,hash_mib=64,multipv=1,pilot=pilot,selected_fixed_nodes=nodes,estimated_seconds=per_position*(len(chosen)+len(dev))*nodes/10000,engine_sha256=engine_sha))
        labels=[];started=time.monotonic()
        for row in [*chosen,*dev]:
            if time.monotonic()-started>1800:raise TimeoutError('labeling 30 minute budget reached')
            b=board_for(row)
            # Clear caches so every label is independently reproducible at fixed nodes.
            engine.configure({'Clear Hash':None})
            tick=time.monotonic();info=engine.analyse(b,chess.engine.Limit(nodes=nodes),multipv=1)[0]
            move=info['pv'][0].uci()
            if move not in row.candidate_uci:raise ValueError('expert move outside legal candidate set')
            score=info['score'].pov(b.turn)
            labels.append(dict(sample_id=row.sample_id,split=row.split,fen=b.fen(en_passant='legal'),side_to_move='white' if b.turn else 'black',engine=engine.id,engine_sha256=engine_sha,limit_nodes=nodes,actual_nodes=info.get('nodes'),depth=info.get('depth'),nps=info.get('nps'),move_uci=move,score_cp=None if score.is_mate() else score.score(),score_mate=score.mate() if score.is_mate() else None,score_perspective='side_to_move',wall_seconds=time.monotonic()-tick))
            if len(labels)%100==0:print('expert labels',len(labels),flush=True)
    write_rows(directory/'labels.jsonl',labels)
    write(directory/'manifest.json',dict(labels=len(labels),training=sum(r['split']=='train' for r in labels),development=sum(r['split']=='validation' for r in labels),sha256=sha(directory/'labels.jsonl'),dataset_manifest_sha256=sha(ARTIFACTS/'dataset-v4/manifest.json'),wall_seconds=time.monotonic()-started))
    return labels


def select_candidate(candidates):
    a=next(x for x in candidates if x['stage']=='M4-A')
    eligible=[x for x in candidates if x.get('valid',True) and (x['stage']!='M4-B' or x['validation']['nll']<=a['validation']['nll']*1.05)]
    return min(eligible,key=lambda x:(-x['simulator_score'],x['validation']['nll'],x['order']))


def main():
    configure_determinism(SEED,threads=1)
    rows,manifest=verify_release(ARTIFACTS/'dataset-v4');examples={**rows,'manifest':manifest}
    # A completed HPO study may be reused only with a verified immutable
    # input-projection compatibility record for the coverage-completed release.
    if (ARTIFACTS/'hpo/result.json').exists():
        compatibility=json.loads((ARTIFACTS/'hpo-final-release-compatibility.json').read_text())
        if not compatibility.get('all_hpo_inputs_unchanged') or compatibility['final_release_id']!=manifest['release_id']:
            raise ValueError('completed HPO inputs do not match final release projection')
        hp=json.loads((ARTIFACTS/'hpo/result.json').read_text())
    else:hp=hpo(examples)
    labels=expert_labels(examples)
    a=fit(SOURCE,HISTORICAL_M4_SHA256,examples,hp['best_params']['learning_rate'],hp['best_params']['weight_decay'],25,5,ARTIFACTS/'m4-a')
    targets={r['sample_id']:r['move_uci'] for r in labels if r['split']=='train'}
    expert=[replace(row,target_uci=targets[row.sample_id],target_index=row.candidate_uci.index(targets[row.sample_id])) for row in rows['train'] if row.sample_id in targets]
    b=fit(ROOT/a['best_checkpoint'],a['sha256'],examples,hp['best_params']['learning_rate']*.5,hp['best_params']['weight_decay'],5,2,ARTIFACTS/'m4-b',expert=expert)
    dev_targets={r['sample_id']:r['move_uci'] for r in labels if r['split']=='validation'}
    dev=[replace(row,target_uci=dev_targets[row.sample_id],target_index=row.candidate_uci.index(dev_targets[row.sample_id])) for row in rows['validation'] if row.sample_id in dev_targets]
    candidates=[]
    for order,(stage,path,identity) in enumerate([('historical',SOURCE,HISTORICAL_M4_SHA256),('M4-A',ROOT/a['best_checkpoint'],a['sha256']),('M4-B',ROOT/b['best_checkpoint'],b['sha256'])]):
        model,_=load_source(path,identity);val=metrics(model,rows['validation']);agreement=metrics(model,dev)
        policy=BehaviorPolicy(model,checkpoint_sha256=identity)
        tick=time.monotonic();games=evaluate_policy(policy,policy_id=stage,seeds=tuple(range(20270101,20270106)),max_wall_seconds=1200.)
        if len(games)!=20 or any(g.get('status')!='completed_game' for g in games):
            raise RuntimeError('incomplete fixed simulator development protocol')
        # Fixed-schedule score: truncations contribute zero, never an invented draw.
        score=sum((g['agent_reward']+1)/2 for g in games if not g['truncated'])/len(games)
        write(ARTIFACTS/f'{stage}-development-games.json',games)
        candidates.append(dict(stage=stage,order=order,checkpoint=str(path.relative_to(ROOT)),sha256=identity,validation=val,expert_development=agreement,simulator_score=score,simulator_truncated_games=sum(g['truncated'] for g in games),simulator_score_definition='(wins + 0.5*true_draws)/20 scheduled games; truncations contribute zero without being labeled losses',simulator_wall_seconds=time.monotonic()-tick))
    selected=select_candidate(candidates)
    write(ARTIFACTS/'m4-selection.json',dict(candidates=candidates,selected=selected,test_metrics_inspected=False,rule='B NLL <= 1.05*A; maximize fixed simulator score; min validation NLL; earlier checkpoint'))
    model,_=load_source(ROOT/selected['checkpoint'],selected['sha256'])
    write(ARTIFACTS/'m4-test-once.json',dict(checkpoint_sha256=selected['sha256'],metrics=metrics(model,rows['test']),selected_before_test=True))


from collections import Counter
if __name__=='__main__':main()
