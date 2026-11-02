"""Derive a coverage-complete release without repeating the HPO campaign."""
from collections import Counter,defaultdict
import hashlib
import json
import shutil
import chess
from .common import ARTIFACTS,ROOT,read_rows,write_rows,write,sha,utc,revision
from .data import complete_game_coverage
from videochess_rl.data.contracts import digest,sampling_run_identity


def main():
    source=ARTIFACTS/'dataset-v3';target=ARTIFACTS/'dataset-v4';target.mkdir(exist_ok=False)
    manifest=json.loads((source/'manifest.json').read_text())
    for name,value in manifest['files'].items():
        if sha(source/name)!=value:raise ValueError('parent release integrity failure')
    config=json.loads((ROOT/'configs/improvement/dataset.json').read_text())
    old=read_rows(source/'positions.jsonl');games=read_rows(source/'games.jsonl')
    source_id=old[0]['source_id'];config_sha=digest(config)
    rows=[{**r,'sampling_config_sha256':config_sha,'sampling_id':sampling_run_identity(source_id,config['sampling_seed'],config_sha)} for r in old]
    historical=ROOT/config['historical_release']
    exposed={r['board_position_signature'] for r in read_rows(historical/'positions.jsonl') if r['split'] in ('train','validation')}
    rows,additions=complete_game_coverage(games,rows,source_id=source_id,seed=config['sampling_seed'],config_sha=config_sha,historical_exposure=exposed,max_positions=config['max_positions'])
    if len({r['game_id'] for r in rows})!=5000:raise ValueError('5000 represented games required')
    old_ids={r['sample_id']:r for r in old};new_ids={r['sample_id']:r for r in rows}
    def core(r):return {k:v for k,v in r.items() if k not in ('sampling_id','sampling_config_sha256')}
    if any(core(r)!=core(new_ids[sid]) for sid,r in old_ids.items()):raise ValueError('existing HPO input changed')
    split=json.loads((source/'split.json').read_text());initial_purged=split['purged_samples'];added_ids={r['sample_id'] for r in additions}
    split['core_purged_samples']=initial_purged
    split['purged_samples']=[r for r in initial_purged if r[0] not in added_ids]
    split['coverage_completion_sample_ids']=sorted(added_ids)
    stats=dict(manifest['stats'])
    stats['core_purge_reasons']=stats['purge_reasons'];stats['purge_reasons']=dict(Counter(r[1] for r in split['purged_samples']))
    stats['positions_after_core_purge']=len(old);stats['positions_after_purge']=len(rows)
    stats['coverage_completion_records']=len(additions);stats['games_with_retained_positions']=len({r['game_id'] for r in rows})
    stats['coverage_restored_from_core_purge']=sum(r[0] in added_ids for r in initial_purged)
    stats['position_counts']=dict(Counter(r['split'] for r in rows))
    stats['distinct_board_signatures']=len({r['board_position_signature'] for r in rows})
    stats['exact_history_target_duplicates']=len(rows)-len({(r['history_state_id'],r['played_move_uci']) for r in rows})
    for split_name in ('train','validation','test'):
        before={r['history_state_id'] for r in old if r['split']==split_name}
        if len(before)!=manifest['stats']['effective_input_uniqueness'][split_name]:raise ValueError('history/model-input uniqueness equivalence failed')
    stats['effective_input_uniqueness']={s:len({r['history_state_id'] for r in rows if r['split']==s}) for s in ('train','validation','test')}
    for r in additions:
        board=chess.Board(r['fen']);phase='opening' if r['ply_index']<20 else 'endgame' if len(board.piece_map())<=12 else 'middlegame'
        stats['phases'][r['split']][phase]+=1
    represented=Counter(r['game_id'] for r in rows)
    stats['maximum_records_per_game']=max(represented.values())
    stats['repeated_fen_observations']=len(rows)-len({r['fen'] for r in rows})
    stats['repeated_board_signature_observations']=len(rows)-stats['distinct_board_signatures']
    seen=defaultdict(set)
    for r in rows:seen[r['board_position_signature']].add(r['split'])
    if any(len(v)>1 for v in seen.values()):raise ValueError('cross-split exposure')
    if any(r['split']!='train' and r['board_position_signature'] in exposed for r in rows):raise ValueError('historical holdout exposure')
    for name in ('accepted-source.jsonl',):shutil.copyfile(source/name,target/name)
    write_rows(target/'games.jsonl',games);write_rows(target/'positions.jsonl',rows)
    write(target/'split.json',split);write(target/'stats.json',stats);write(target/'config.json',config)
    files={name:sha(target/name) for name in ('games.jsonl','positions.jsonl','split.json','stats.json','config.json','accepted-source.jsonl')}
    identity={**manifest['identity'],'config_sha256':config_sha,'files':files}
    final={**manifest,'release_id':digest(identity),'identity':identity,'files':files,'stats':stats,'created_at_utc':utc(),'source_revision':revision(),'derivation':dict(parent_manifest_sha256=sha(source/'manifest.json'),rule=config['coverage_rule'],existing_position_core_preserved=True,coverage_additions=len(additions))}
    final.pop('wall_seconds',None)
    write(target/'manifest.json',final)
    train=sorted([r for r in old if r['split']=='train'],key=lambda r:hashlib.sha256((str(20261103)+r['sample_id']).encode()).hexdigest())[:8192]
    subset_sha=hashlib.sha256('\n'.join(r['sample_id'] for r in train).encode()).hexdigest()
    hpo=json.loads((ARTIFACTS/'hpo/result.json').read_text())
    if subset_sha!=hpo['subset_sha256']:raise ValueError('HPO subset identity mismatch')
    write(ARTIFACTS/'hpo-final-release-compatibility.json',dict(all_hpo_inputs_unchanged=True,final_release_id=final['release_id'],parent_release_id=manifest['release_id'],parent_manifest_sha256=sha(source/'manifest.json'),final_manifest_sha256=sha(target/'manifest.json'),training_subset_sha256=subset_sha,training_subset_count=8192,hpo_validation_count=sum(r['split']=='validation' for r in old),final_validation_count=stats['position_counts']['validation'],projection='Existing sample IDs, parent histories, FENs, legal actions, human labels, and splits are identical. Only sampling provenance metadata differs. All eight HPO trials used the same unchanged 8192 train/8964 validation projection. No extra HPO trial is authorized or performed.'))
    print(json.dumps(dict(release_id=final['release_id'],stats=stats)),flush=True)


if __name__=='__main__':main()
