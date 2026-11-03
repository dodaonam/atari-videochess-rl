#!/usr/bin/env python3
"""Disposable fresh-process CLI/recovery check; never starts the official run."""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from videochess_rl.improvement.common import ARTIFACTS,write,sha,utc,revision
from videochess_rl.improvement.m5 import source_identity,validate_config
from videochess_rl.rl.checkpoint import load_training_checkpoint_bundle


def main():
    argparse.ArgumentParser(description=__doc__).parse_args()
    selected=json.loads((ARTIFACTS/'m4-selection.json').read_text())['selected']
    config=ROOT/'configs/improvement/m5-phase2.json'
    settings=validate_config(json.loads(config.read_text()))
    freeze=json.loads((ROOT/'.agents/evidence/improvement/readiness-source-freeze.json').read_text())
    if source_identity()!=freeze['code_sha256']:raise ValueError('source freeze mismatch')
    directory=ARTIFACTS/'cli-verification-v2';directory.mkdir(exist_ok=False)
    environment=dict(os.environ)
    environment['PATH']='/usr/bin:/bin'
    environment.pop('PYTHONPATH',None)
    if shutil.which('stockfish',path=environment['PATH']) is not None:raise RuntimeError('engine-free PATH prerequisite failed')
    base=[sys.executable,'-m','videochess_rl.improvement.m5','--config',str(config),
          '--checkpoint',str(ROOT/selected['checkpoint']),'--checkpoint-sha256',selected['sha256']]
    records=[]
    def execute(name,extra):
        command=[*base,*extra]
        started=utc()
        log=directory/(name+'-private-console.log')
        with log.open('x') as stream:
            result=subprocess.run(command,cwd=ROOT,env=environment,stdout=stream,stderr=subprocess.STDOUT)
        records.append(dict(command=command,started_at_utc=started,ended_at_utc=utc(),exit_code=result.returncode,private_log_path=log.relative_to(ROOT).as_posix(),private_log_sha256=sha(log)))
        write(directory/'commands.json',records)
        if result.returncode:raise RuntimeError('CLI check failed: '+name)
    first=directory/'attempt-0000'
    execute('fresh',['--output',str(first),'--probe-decisions','4500'])
    first_report=json.loads((first/'run.json').read_text())
    checkpoint=first_report['last_checkpoint']
    bundle=load_training_checkpoint_bundle(checkpoint)
    if bundle['counters']['target_syncs']<1 or not bundle['optimizer']['state']:raise ValueError('post-target-sync checkpoint required')
    second=directory/'attempt-0001'
    execute('resume',['--output',str(second),'--probe-decisions','4800','--resume',checkpoint])
    resumed=json.loads((second/'run.json').read_text())
    checks=dict(fresh_decisions=first_report['valid_decisions']==4500,resumed_decisions=resumed['valid_decisions']==4800,
                runtime_intraop=resumed['identity']['runtime']['intraop_threads']==settings['threads'],runtime_interop=resumed['identity']['runtime']['interop_threads']==1,
                probe_role=resumed['identity']['execution_kind']=='probe',selected_m4=resumed['identity']['m4_sha256']==selected['sha256'],
                cumulative_wall=resumed['cumulative_wall_seconds']>=first_report['wall_seconds']+resumed['wall_seconds']-.1,
                valid_counters=resumed['valid_decisions']==resumed['transitions'],target_sync=resumed['target_syncs']>=1,engine_absent_on_path=True,
                official_namespace_absent=not (ARTIFACTS/'official').exists(),frozen_code=source_identity()==freeze['code_sha256'])
    result=dict(checks=checks,passed=all(checks.values()),source_revision=revision(),code_sha256=source_identity(),config_sha256=sha(config),selected_m4_sha256=selected['sha256'],checkpoint_sha256=sha(checkpoint),checkpoint_decisions=bundle['counters']['valid_decisions'],checkpoint_updates=bundle['counters']['optimizer_updates'],checkpoint_target_syncs=bundle['counters']['target_syncs'],repeated_tail_decisions=resumed['repeated_parent_tail_decisions'],commands=records,official_run=False)
    write(ROOT/'.agents/evidence/improvement/phase2-cli-verification.json',result)
    print(json.dumps({k:v for k,v in result.items() if k!='commands'}),flush=True)
    if not result['passed']:raise AssertionError('CLI/recovery checks failed')


if __name__=='__main__':main()
