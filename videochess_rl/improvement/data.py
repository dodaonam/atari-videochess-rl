"""Full-source parsing, bottom-k selection, and exposure-protected release."""
from __future__ import annotations
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
import io
import json
from pathlib import Path
import time
import zipfile

import chess
from videochess_rl.data.pgn import iter_pgn_games
from videochess_rl.data.sampling import BottomKGroups, sample_positions
from videochess_rl.data.contracts import digest, board_signature_owner, ply_sample_key
from videochess_rl.model.dataset import _features_from_verified_records, effective_model_input_sha256
from .common import ARTIFACTS, ROOT, read_rows, write_rows, sha, write, utc, revision


def _parse_chunk(args):
    data, source, ordinal_offset = args
    stats = {}
    rows, rejected = [], Counter()
    for _, parsed in iter_pgn_games(
        io.BytesIO(data), source_id=source['source_id'], archive_sha256=source['archive_sha256'],
        member_name=source['member_name'], max_games_seen=400000,
        max_game_bytes=8388608, max_total_decompressed_bytes=2147483648,
        stream_stats=stats,
    ):
        if parsed.status == 'accepted':
            parsed.game['source_ordinal'] += ordinal_offset
            parsed.game['source_game_ordinal'] += ordinal_offset
            rows.append(parsed.game)
        else:
            rejected[str(parsed.reason_code)] += 1
    return rows, dict(rejected)


def source_chunks(source, chunk_games=1000):
    """Split at top-level Event headers; parser validates every resulting game."""
    with zipfile.ZipFile(ROOT / source['archive_path']) as z:
        with z.open(source['member_name']) as f:
            pieces, games, ordinal_offset = [], 0, 0
            for line in f:
                if line.startswith(b'[Event '):
                    if games == chunk_games:
                        yield b''.join(pieces), source, ordinal_offset
                        ordinal_offset += games
                        pieces, games = [], 0
                    games += 1
                pieces.append(line)
            if pieces:
                yield b''.join(pieces), source, ordinal_offset


def fixed_splits(games, seed):
    ordered = sorted(games, key=lambda g: (digest([seed, 'split', g['normalized_game_sha256']]), g['normalized_game_sha256']))
    n = len(ordered)
    train, val = int(n*.8), int(n*.1)
    return {g['normalized_game_sha256']: ('train' if i < train else 'validation' if i < train+val else 'test') for i,g in enumerate(ordered)}


def protect_positions(positions, assignments, historical_exposure, seed):
    signatures = defaultdict(set)
    for p in positions:
        signatures[p['board_position_signature']].add(assignments[p['normalized_game_sha256']])
    owners = {s: board_signature_owner(seed, s, splits) for s,splits in signatures.items()}
    kept, purged = [], []
    for p in positions:
        split = assignments[p['normalized_game_sha256']]
        if owners[p['board_position_signature']] != split:
            purged.append([p['sample_id'], 'cross_split_board_overlap'])
        elif split != 'train' and p['board_position_signature'] in historical_exposure:
            purged.append([p['sample_id'], 'historical_train_validation_exposure'])
        else:
            kept.append({**p, 'split':split, 'split_id':split})
    return kept, purged, sum(len(x)>1 for x in signatures.values())


def complete_game_coverage(games, positions, *, source_id, seed, config_sha,
                           historical_exposure, max_positions=100000):
    """Retain the protected bottom-k core, then cover zero-record parents.

    Select one lowest-ranked eligible position from each missing game's original
    per-game candidate reservoir. Never change an existing split or board owner.
    """
    represented={p['game_id'] for p in positions}
    missing=[g for g in games if g['game_id'] not in represented]
    if len(positions)+len(missing)>max_positions:
        raise ValueError('insufficient position budget for complete game coverage')
    owners={p['board_position_signature']:p['split'] for p in positions}
    additions=[]
    for game in sorted(missing,key=lambda g:g['normalized_game_sha256']):
        candidates=sample_positions([game],source_id=source_id,seed=seed,
            max_positions_per_game=32,max_positions=32,sampling_config_sha256=config_sha)
        eligible=[p for p in candidates
            if owners.get(p['board_position_signature'],game['split'])==game['split']
            and (game['split']=='train' or p['board_position_signature'] not in historical_exposure)]
        if not eligible:
            raise ValueError('selected game has no leakage-safe coverage position: '+game['normalized_game_sha256'])
        row=min(eligible,key=lambda p:(ply_sample_key(seed,source_id,p['game_id'],p['ply_index']),p['sample_id']))
        row.update(split=game['split'],split_id=game['split'])
        owners[row['board_position_signature']]=game['split']
        additions.append(row)
    return sorted([*positions,*additions],key=lambda p:p['sample_id']), additions


def verify_release(path):
    path = Path(path)
    manifest = json.loads((path/'manifest.json').read_text())
    for name, expected in manifest['files'].items():
        if sha(path/name) != expected:
            raise ValueError(f'dataset checksum mismatch: {name}')
    games, positions = read_rows(path/'games.jsonl'), read_rows(path/'positions.jsonl')
    splits = json.loads((path/'split.json').read_text())
    if len({g['normalized_game_sha256'] for g in games}) != len(games):
        raise ValueError('duplicate normalized games')
    examples, counts = _features_from_verified_records(games, positions, splits)
    seen = {}
    for p in positions:
        prior = seen.setdefault(p['board_position_signature'],p['split'])
        if prior != p['split']:
            raise ValueError('cross-split board exposure')
    return examples, manifest


def build(output=None):
    started = time.monotonic()
    config = json.loads((ROOT/'configs/improvement/dataset.json').read_text())
    source = json.loads((ROOT/config['source_manifest']).read_text())
    if sha(ROOT/source['archive_path']) != source['archive_sha256']:
        raise ValueError('source archive hash mismatch')
    with zipfile.ZipFile(ROOT/source['archive_path']) as z:
        member = z.read(source['member_name'])
        import hashlib
        if hashlib.sha256(member).hexdigest() != source['member_sha256']:
            raise ValueError('source member hash mismatch')
        expected_headers = sum(line.startswith(b'[Event ') for line in member.splitlines())
        del member
    history = ROOT/config['historical_release']
    historical_games = read_rows(history/'games.jsonl')
    excluded = {g['normalized_game_sha256'] for g in historical_games}
    hist_rows = read_rows(history/'positions.jsonl')
    historical_exposure = {p['board_position_signature'] for p in hist_rows if p['split'] in ('train','validation')}
    directory = Path(output) if output is not None else ARTIFACTS/'dataset-v4'
    if not directory.resolve().is_relative_to(ARTIFACTS.resolve()):
        raise ValueError('dataset output must remain in the ignored improvement namespace')
    directory.mkdir(parents=True, exist_ok=False)
    cache = directory/'accepted-source.jsonl'
    grouper = BottomKGroups(seed=config['selection_seed'],max_games=config['max_games'],source_id=source['source_id'],archive_sha256=source['archive_sha256'],member_name=source['member_name'])
    rejected, accepted, exclusions = Counter(), 0, 0
    with cache.open('x') as out, ProcessPoolExecutor(max_workers=config['workers']) as pool:
        # Executor.map prefetches the bounded 326 MiB archive, within local RAM.
        for rows, reasons in pool.map(_parse_chunk, source_chunks(source)):
            rejected.update(reasons)
            for row in rows:
                accepted += 1
                if row['normalized_game_sha256'] in excluded:
                    exclusions += 1
                    continue
                grouper.observe(row)
                out.write(json.dumps(row,separators=(',',':'))+'\n')
            print(json.dumps({'accepted':accepted,'rejected':sum(rejected.values()),'seconds':time.monotonic()-started}),flush=True)
    if accepted + sum(rejected.values()) != expected_headers:
        raise ValueError('chunk boundary game-count mismatch')
    grouper.begin_selection()
    with cache.open() as f:
        for line in f:
            grouper.select(json.loads(line))
    grouper.verify_selection_complete()
    games = grouper.selected_records()
    if len(games) != config['max_games']:
        raise ValueError('insufficient eligible disjoint games')
    assignments = fixed_splits(games,config['split_seed'])
    for g in games:
        g.update(split=assignments[g['normalized_game_sha256']],split_id=assignments[g['normalized_game_sha256']])
    positions = sample_positions(games,source_id=source['source_id'],seed=config['sampling_seed'],max_positions_per_game=config['max_positions_per_game'],max_positions=config['max_positions'],sampling_config_sha256=digest(config))
    before = len(positions)
    positions,purged,overlap_before = protect_positions(positions,assignments,historical_exposure,config['split_seed'])
    positions,coverage_additions=complete_game_coverage(games,positions,source_id=source['source_id'],seed=config['sampling_seed'],config_sha=digest(config),historical_exposure=historical_exposure,max_positions=config['max_positions'])
    core_purged=purged
    restored_ids={p['sample_id'] for p in coverage_additions}
    purged=[p for p in core_purged if p[0] not in restored_ids]
    split_doc = dict(core_purged_samples=core_purged,coverage_completion_sample_ids=sorted(p['sample_id'] for p in coverage_additions),game_group_assignments=sorted([list(x) for x in assignments.items()]),purged_samples=purged)
    examples, counts = _features_from_verified_records(games,positions,split_doc)
    phases = defaultdict(Counter)
    effective = defaultdict(set)
    for split,rows in examples.items():
        for row in rows:
            material = sum(row.board_planes[:12].sum(axis=(1,2)))
            phase = 'opening' if row.ply_index < 20 else 'endgame' if material <= 12 else 'middlegame'
            phases[split][phase] += 1
            effective[split].add(effective_model_input_sha256(row))
    if not all(examples[s] for s in ('train','validation','test')):
        raise ValueError('empty split after leakage protection')
    stats = dict(core_purge_reasons=dict(Counter(x[1] for x in core_purged)),positions_after_core_purge=len(positions)-len(coverage_additions),coverage_restored_from_core_purge=sum(x[0] in restored_ids for x in core_purged),maximum_records_per_game=max(Counter(p['game_id'] for p in positions).values()),repeated_fen_observations=len(positions)-len({p['fen'] for p in positions}),repeated_board_signature_observations=len(positions)-len({p['board_position_signature'] for p in positions}),coverage_completion_records=len(coverage_additions),games_with_retained_positions=len({p['game_id'] for p in positions}),games=len(games),game_counts=counts,position_counts={s:len(v) for s,v in examples.items()},positions_before_purge=before,positions_after_purge=len(positions),purge_reasons=dict(Counter(x[1] for x in purged)),historical_game_overlap=0,historical_holdout_board_overlap=0,cross_split_board_signatures_before=overlap_before,cross_split_board_signatures_after=0,normalized_duplicate_groups=grouper.normalized_duplicate_groups,normalized_duplicate_observations=grouper.normalized_duplicate_observations,conflicting_groups=len(grouper.conflicting_groups),source_ref_conflicts=len(grouper.conflicting_source_refs),duplicate_sample_ids=len(positions)-len({p['sample_id'] for p in positions}),exact_history_target_duplicates=len(positions)-len({(p['history_state_id'],p['played_move_uci']) for p in positions}),distinct_board_signatures=len({p['board_position_signature'] for p in positions}),effective_input_uniqueness={s:len(v) for s,v in effective.items()},phases={s:dict(v) for s,v in phases.items()},accepted_source_games=accepted,rejection_reasons=dict(rejected),historical_excluded_observations=exclusions,source_games_seen=expected_headers)
    write_rows(directory/'games.jsonl',games)
    write_rows(directory/'positions.jsonl',positions)
    write(directory/'split.json',split_doc)
    write(directory/'stats.json',stats)
    write(directory/'config.json',config)
    files = {name:sha(directory/name) for name in ('games.jsonl','positions.jsonl','split.json','stats.json','config.json','accepted-source.jsonl')}
    identity = dict(config_sha256=digest(config),source_archive_sha256=source['archive_sha256'],source_member_sha256=source['member_sha256'],historical_games_sha256=sha(history/'games.jsonl'),historical_positions_sha256=sha(history/'positions.jsonl'),exclusion_set_sha256=digest(sorted(excluded)),files=files)
    write(directory/'manifest.json',dict(schema='videochess-improvement-dataset/1',release_id=digest(identity),identity=identity,files=files,stats=stats,created_at_utc=utc(),wall_seconds=time.monotonic()-started,source_revision=revision(),normalization='videochess-normalized-game/v1: standard initial FEN plus complete legal mainline UCI; reuse M3 parser',selection='global hash bottom-k over all eligible normalized groups excluding historical 1000; conflicts rejected',split='exact 80/10/10 hash-ranked game groups; deterministic board ownership purge; remove historical train/validation board signatures from new holdouts'))
    print(json.dumps(stats),flush=True)


if __name__ == '__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=ARTIFACTS/'dataset-v4')
    build(parser.parse_args().output)
