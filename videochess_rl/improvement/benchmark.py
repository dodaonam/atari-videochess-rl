"""Disposable post-warmup batch/thread benchmarks, not a scientific M5 run."""
from collections import Counter
import copy
import json
from pathlib import Path
import random
import statistics
import time

import torch
from .common import ARTIFACTS,ROOT,write,sha,usage
from .m5 import config_default,execute,choose_action,make_learner
from .learner import features
from videochess_rl.model.features import encode_board,replay_observation_history


def main():
    selection=json.loads((ARTIFACTS/'m4-selection.json').read_text())['selected']
    path=ROOT/selection['checkpoint'];identity=selection['sha256']
    directory=ARTIFACTS/'benchmarks';directory.mkdir(exist_ok=False)
    results=[]
    for threads in (1,2,4):
        for batch in (32,64):
            c={**config_default(),'threads':threads,'batch_size':batch}
            learner,m4,report=execute(c,path,identity,directory/f't{threads}-b{batch}',stop_at=4000)
            samples=[r for r in report['resources'] if r['valid_decisions']>=1100]
            first,last=samples[0],samples[-1]
            seconds=last['cumulative_wall_seconds']-first['cumulative_wall_seconds']
            decisions=last['valid_decisions']-first['valid_decisions']
            rate=decisions/seconds*3600
            # Additional microtimings use populated real replay and actual legal states.
            tick=time.perf_counter()
            for _ in range(200):learner.replay.sample(batch)
            replay_ms=(time.perf_counter()-tick)*1000/200
            update_times=[]
            for _ in range(12):
                tick=time.perf_counter();learner.update();update_times.append(time.perf_counter()-tick)
            feature_rows=[features(row.history_before) for row in learner.replay.sample(32)]
            action_times={}
            for t in (0,200000):
                learner.valid_decisions=t
                tick=time.perf_counter()
                sources=Counter()
                for f in feature_rows:
                    _,source=choose_action(learner,m4,f,c);sources[source]+=1
                action_times[str(t)]=dict(ms=(time.perf_counter()-tick)*1000/len(feature_rows),sources=dict(sources))
            result=dict(microtiming_schedule_points_not_achieved_training_decisions=[0,200000],additional_disposable_optimizer_microtiming_updates=12,batch_size=batch,threads=threads,actual_intraop_threads=torch.get_num_threads(),actual_interop_threads=torch.get_num_interop_threads(),postwarmup_valid_decisions=decisions,postwarmup_seconds=seconds,postwarmup_decisions_per_hour=rate,total_seconds=report['wall_seconds'],total_decisions=4000,optimizer_updates=report['optimizer_updates'],real_replay_rows=len(learner.replay),replay_sample_ms=replay_ms,optimizer_update_median_ms=statistics.median(update_times)*1000,optimizer_samples_per_second=batch/statistics.mean(update_times),action_selection=action_times,checkpoint_serialization_seconds=report['checkpoint_serialization_seconds'],resources=usage(),projected_250k_hours=250000/rate)
            results.append(result);write(directory/'results.json',results)
            print(json.dumps(result),flush=True)
            features.cache_clear()
    best32=max((x for x in results if x['batch_size']==32),key=lambda x:x['postwarmup_decisions_per_hour'])
    best64=max((x for x in results if x['batch_size']==64),key=lambda x:x['postwarmup_decisions_per_hour'])
    # Require measured >5% advantage to change the requested default batch.
    chosen=best64 if best64['postwarmup_decisions_per_hour']>best32['postwarmup_decisions_per_hour']*1.05 else best32
    rates=[x['postwarmup_decisions_per_hour'] for x in results if x['batch_size']==chosen['batch_size']]
    conservative=chosen['postwarmup_decisions_per_hour']*.7
    write(directory/'feasibility.json',dict(selected=chosen,conservative_decisions_per_hour=conservative,conservative_250k_hours=250000/conservative,supports_15_hour_target=conservative>=16667,uncertainty='Disposable short simulator probes; later Q policy, longer histories, replay occupancy, CPU load, and checkpoints may alter throughput. Conservative rate discounts the selected measured hardware condition by 30%; it is a planning estimate, not a bound.',official_run_started=False))


if __name__=='__main__':main()
