"""Produce a payload-free Phase 1 evidence index and Phase 2 handoff."""
from collections import Counter,defaultdict
import json
from pathlib import Path
import statistics
import shlex

from .common import ROOT,ARTIFACTS,read_rows,sha,write,utc,revision
from . import EXPERIMENT_ID,HISTORICAL_M4_SHA256


def load(name):return json.loads((ARTIFACTS/name).read_text())


def main():
    dataset=load('dataset-v3/manifest.json');stats=dataset['stats']
    hpo=load('hpo/result.json');trials=load('hpo/trials.json')
    labels=read_rows(ARTIFACTS/'expert/labels.jsonl');expert=load('expert/manifest.json');pilot=load('expert/pilot.json')
    positions=read_rows(ARTIFACTS/'dataset-v3/positions.jsonl');by_id={p['sample_id']:p for p in positions}
    checks=[]
    for row in labels:
        parent=by_id[row['sample_id']]
        checks.append(row['split'] in ('train','validation') and row['split']==parent['split'] and row['move_uci'] in parent['legal_moves_uci'] and row['fen']==parent['fen'] and row['score_perspective']=='side_to_move' and not(row['score_cp'] is not None and row['score_mate'] is not None))
    if not all(checks) or len({r['sample_id'] for r in labels})!=len(labels):raise ValueError('expert audit failure')
    if sha(ARTIFACTS/'expert/labels.jsonl')!=expert['sha256']:raise ValueError('expert checksum mismatch')
    selection=load('m4-selection.json');selected=selection['selected'];test=load('m4-test-once.json')
    if sha(ROOT/selected['checkpoint'])!=selected['sha256'] or test['checkpoint_sha256']!=selected['sha256']:raise ValueError('selected model identity mismatch')
    recovery=load('recovery-probe/verification.json');feasibility=load('benchmarks/feasibility.json')
    if not recovery['passed']:raise ValueError('recovery not verified')
    opponents={}
    for candidate in selection['candidates']:
        rows=load(candidate['stage']+'-development-games.json');groups=defaultdict(Counter)
        for row in rows:
            outcome='incomplete' if row['truncated'] else 'win' if row['agent_reward']==1 else 'loss' if row['agent_reward']==-1 else 'draw'
            groups[row['opponent_id']+'/'+row['agent_color']][outcome]+=1
        opponents[candidate['stage']]={k:dict(v) for k,v in groups.items()}
    c=json.loads((ROOT/'configs/improvement/m5.json').read_text())
    c={**c,'batch_size':feasibility['selected']['batch_size'],'threads':feasibility['selected']['threads']}
    write(ROOT/'configs/improvement/m5-phase2.json',c)
    command=['.venv/bin/python','-m','videochess_rl.improvement.m5','--config','configs/improvement/m5-phase2.json','--checkpoint',selected['checkpoint'],'--checkpoint-sha256',selected['sha256'],'--output','artifacts/improvement/'+EXPERIMENT_ID+'/official/attempt-0000','--phase2-official']
    # Reproducibility across two independent complete archive scans. The first
    # attempt had corrected ordinal metadata pending; its sampled rows are identical.
    reproduction=dict(position_sha256=sha(ARTIFACTS/'dataset-v3/positions.jsonl'),independent_first_position_sha256=sha(ARTIFACTS/'dataset/positions.jsonl'),same_sampled_position_bytes=sha(ARTIFACTS/'dataset-v3/positions.jsonl')==sha(ARTIFACTS/'dataset/positions.jsonl'),same_normalized_game_set={g['normalized_game_sha256'] for g in read_rows(ARTIFACTS/'dataset-v3/games.jsonl')}=={g['normalized_game_sha256'] for g in read_rows(ARTIFACTS/'dataset/games.jsonl')},final_source_ordinals_global=True)
    if not reproduction['same_sampled_position_bytes'] or not reproduction['same_normalized_game_set']:raise ValueError('independent selection mismatch')
    evidence={p.stem:json.loads(p.read_text()) for p in sorted((ROOT/'.agents/evidence/improvement').glob('*.json')) if 'command' in json.loads(p.read_text())}
    expert_summary={**expert,'pilot':pilot,'verified_labels':sum(checks),'actual_depth_median':statistics.median(r['depth'] for r in labels),'actual_nodes_median':statistics.median(r['actual_nodes'] for r in labels),'mate_score_records':sum(r['score_mate'] is not None for r in labels),'all_scores_side_to_move':True,'labels_unique_by_sample_id':True}
    verdict='READY_FOR_PHASE_2' if feasibility['supports_15_hour_target'] else 'PHASE_1_INCOMPLETE_WITH_BLOCKERS'
    summary=dict(experiment_id=EXPERIMENT_ID,verdict=verdict,created_at_utc=utc(),source_revision=revision(),dataset=dict(release_id=dataset['release_id'],manifest_sha256=sha(ARTIFACTS/'dataset-v3/manifest.json'),stats=stats,reproduction=reproduction),hpo=hpo,trials=trials,expert=expert_summary,m4=selection,reserved_test=test,m4_a=load('m4-a/result.json'),m4_b=load('m4-b/result.json'),simulator_outcomes=opponents,m5_config=c,benchmarks=load('benchmarks/results.json'),feasibility=feasibility,recovery=recovery,environment=load('environment.json'),demo=load('existing-demo/summary.json'),verification_ledger=evidence,phase2_command=shlex.join(command),official_250k_run_started=False,multi_seed_training_campaign=False,scratch_comparison=False,merged=False)
    write(ROOT/'.agents/evidence/improvement/phase1-results.json',summary)
    inventory={}
    for p in sorted(ARTIFACTS.rglob('*')):
        if p.is_file() and p.name!='artifact-inventory.json' and '.tmp' not in p.name:
            inventory[p.relative_to(ROOT).as_posix()]=dict(sha256=sha(p),bytes=p.stat().st_size)
    write(ARTIFACTS/'artifact-inventory.json',dict(created_at_utc=utc(),files=inventory,publication='private local retention only; inventory is not permission to upload payloads'))
    lines=[f'# Phase 1 handoff — {verdict}',
        f'\nExperiment `{EXPERIMENT_ID}`. This is a separate owner-authorized campaign; historical M0–M7 results and approvals remain unchanged.',
        '\n## Repository and verification identity',
        '\nRepository: https://github.com/dodaonam/atari-videochess-rl. Branch: `feature/videochess-performance-improvement-20261103`. Base main: `7415d821acf11dd3e07e4990c2f5539cfdf31916`.',
        f'\nCampaign compute revision: `{revision()}`. Final pushed revision, tree, clean-checkout results and checks belong to `.agents/evidence/improvement/final-verification.json`, which is recorded after publication of source changes. Never infer final Git identity from this document\'s own future commit.',
        '\nMachine-readable aggregate evidence: `.agents/evidence/improvement/phase1-results.json`. Each retained command record includes actual UTC timestamps, exit code, revision, source-file inventory/hash, output log path/hash. The machine UTC date can precede the local campaign date in Asia/Ho_Chi_Minh.',
        '\n## Private artifact prerequisites',
        f'\nArtifact root: `artifacts/improvement/{EXPERIMENT_ID}/`. This is persistent local project storage on this machine, ignored by Git; a clone does not transfer it. Obtain these artifacts from the owner locally, without publishing them. Verify `artifact-inventory.json` and the individual sidecars before use.',
        f'\nSelected M4 checkpoint: `{selected["checkpoint"]}`. SHA-256: `{selected["sha256"]}`. Its adjacent `.pt.manifest.json` is required. Historical M4 SHA-256 was verified as `{HISTORICAL_M4_SHA256}`; no fresh initialization substituted for it.',
        '\nThe accepted M3 release was independently loaded and verified. Source archive: `artifacts/m3/source/lichess_elite_2022-05.zip`, SHA-256 `ad374c8fd9fb2fe5f03c1297aa1d47cbbce5caedf6e6e2d387ee816930afdb11`. The third-party license remains unstated; use and all derived records remain internal and local.',
        '\n## Dataset and leakage audit',
        f'\nFinal release: `{dataset["release_id"]}`, located at `dataset-v3/` under the artifact root. It selected exactly 5,000 normalized games, excluding all 1,000 historical games by identity. Exact game split: 4,000/500/500. Position split: {stats["position_counts"]}; total {stats["positions_after_purge"]}. The 100,000-record bottom-k sample had a 32-record per-game cap; leakage protection removed {stats["purge_reasons"]}. No records were synthesized or backfilled.',
        f'\nZero remaining cross-split board signatures and zero historical train/validation board exposure in the new holdouts. There are {stats["distinct_board_signatures"]} distinct board signatures; records are not claimed to be unique board positions. Duplicate sample IDs: {stats["duplicate_sample_ids"]}. Repeated complete-history/target pairs: {stats["exact_history_target_duplicates"]}; these are legitimate cross-game observations, not identical whole release records. Effective-input uniqueness by split: {stats["effective_input_uniqueness"]}.',
        f'\nPhase coverage: {stats["phases"]}. Phase is a disclosed descriptive heuristic: opening before ply 20; otherwise endgame at at most 12 pieces; otherwise middlegame. No phase quota was applied to the dataset. Two independent full archive scans produced identical selected position bytes and normalized game sets. The superseded first build retained chunk-local ordinals; v3 contains global archive ordinals and excludes runtime duration from release identity. The failed v2 tuple-shape diagnostic is retained.',
        '\nRebuild: `.venv/bin/python -m videochess_rl.improvement.data --output artifacts/improvement/videochess-improvement-20261103-v1/dataset-reproduction` into a fresh output namespace (the builder refuses overwrite). Verify/load: `videochess_rl.improvement.data.verify_release`. Manifests bind config, archive/member, historical exclusion inputs, splits, every data file and cache by SHA-256.',
        '\n## HPO, expert labels, and M4 training',
        f'\nOptuna GP search: eight-trial/six-epoch/45-minute ceiling; three deliberately enqueued completed startup trials; fixed seed 20261103 and an identical {hpo["subset_count"]}-record training subset. Objective: minimum human-validation NLL. GP proposals reached: {hpo["bayesian_proposals"]}. Best: {hpo["best_params"]}, objective {hpo["best_value"]}. Runtime: {hpo["wall_seconds"]:.1f} seconds. All trial states and intermediate objectives are retained in `hpo/trials.json` and private `hpo/study.sqlite3`.',
        f'\nStockfish 19: Threads=1, Hash=64 MiB, MultiPV=1, fixed nodes={pilot["selected_fixed_nodes"]}; pilot measurements and engine binary hash are in `expert/pilot.json`. Labels: {expert["training"]} train plus {expert["development"]} separate validation-development positions. All {len(labels)} labels passed independent sample/split/FEN/legal-move checks. Score perspective is side to move; mate scores remain distinct. Training subset phase coverage: {pilot["training_phase_counts"]}. Label SHA-256: `{expert["sha256"]}`. No test positions were labeled for training.',
        '\nM4-A loads the verified historical model, uses a fresh AdamW optimizer and HPO parameters, clipping 1.0, max 25 epochs/patience 5. M4-B loads best A, uses half its learning rate, max 5 epochs/patience 2, and .8 human mean CE plus .2 independently normalized expert mean CE. Both use only seed 20261103. Logical batch 64 is accumulated through bounded physical microbatches of at most 32. HPO trials are separate short optimization probes.',
        '\n| Candidate | Validation NLL | Human top-1 | Human top-3 | Expert dev agreement | Simulator development score | SHA-256 |',
        '|---|---:|---:|---:|---:|---:|---|']
    for x in selection['candidates']:
        lines.append(f'| {x["stage"]} | {x["validation"]["nll"]:.6f} | {x["validation"]["top1"]:.4f} | {x["validation"]["top3"]:.4f} | {x["expert_development"]["top1"]:.4f} | {x["simulator_score"]:.3f} | `{x["sha256"]}` |')
    lines += [f'\nSelected: **{selected["stage"]}**. Selection was saved before test inspection. Invalid checkpoints are rejected; B requires NLL <=1.05*A; maximize fixed simulator development score, then lower validation NLL, then earlier candidate. Each candidate played the same five development scenario seeds, both opponents and colors: 20 games at a 400-decision cap. Score is (wins + .5 true draws)/20; truncations contribute zero and are reported separately, never invented as draws. Outcome breakdown: `{json.dumps(opponents,sort_keys=True)}`.',
        f'\nSelected reserved-test evaluation occurred once: `{json.dumps(test["metrics"],sort_keys=True)}`. Human move prediction, offline engine agreement, simulator score and Atari outcomes are separate measures; none is Elo or a chess winning probability.',
        '\n## M5 implementation and final configuration',
        '\nIndependent entry point: `videochess_rl.improvement.m5`. Exactly one fixed seed and one warm arm; no scratch CLI. Fresh Q head uses an independent deterministic seed domain; only shared M4 representation transfers. Target starts equal to online. The frozen behavior head supplies exploration preferences, not calibrated Q values. Evaluation snapshots load only the Q-network.',
        '\nFinal configuration: `configs/improvement/m5-phase2.json`. All fields are bound and validated, including the 250,000-decision limit, AdamW, Huber, gamma .99, replay 16,384/warmup 1,024, one update per four decisions, clipping 1, target sync every 500 updates, terminal rewards +1/-1/0 and no shaping. Unsupported seed/arm/algorithm/reward/snapshot combinations are rejected.',
        '\nExploration: epsilon 1 -> .05 over 175,000 valid decisions; within exploration, p(M4)=.6*max(0,1-t/75000), else uniform legal action. Every action source is logged against the actual replay transition ID. The frozen M4 is not an optimizer parameter. No Stockfish process is used by the runner.',
        '\nOpponent schedule is deterministic per episode, with RandomLegal probability .5 through t=50,000, .35 through 150,000, then .25; other episodes use SimpleHeuristic. Opponents are selected at episode reset using indexed curriculum RNG; an existing game never changes opponent mid-game. Agent color alternates. The validated low-level legacy transition seed contract is reused; the historical paired campaign runner is not invoked.',
        '\n## Recovery and snapshot procedure',
        '\nEvaluation-only snapshots occur at 0,25k,...,250k. Their sidecars explicitly mark non-resumable semantics. Snapshot verification preserves training RNG. Resumable checkpoints occur after crossing each 1,000-decision interval at the next completed episode boundary. Online/target/optimizer, replay pinned journal prefix, RNG streams, episode/update/sync counters, config/code/M4 hashes and cumulative resource usage are saved.',
        '\nA mid-episode decision or wall cap does not fabricate a terminal transition. Preserve that attempt directory. Recover from its latest verified completed-episode checkpoint into a new sibling attempt directory using the same exact code/config/M4 SHA. `--resume <checkpoint>` forks only the committed journal prefix; original discarded tails remain evidence. Never concatenate an uncommitted tail into replay. Changed attempt IDs for repeated work are expected; semantic transitions, model/optimizer states and RNG must match.',
        f'\nRecovery probe passed all invariants: `{json.dumps(recovery["tests"],sort_keys=True)}`. Repeated parent tail: {recovery["discarded_tail_decisions"]} decisions. The runner charges previous attempts, including failed sibling forks. A crash without a final report is conservatively billed through recovery time, including downtime. Keep all official attempts under the same `official/` parent. An OS file lock prevents simultaneous attempts in that namespace.',
        '\nResource guards monitor process RSS, available system RAM, free disk, artifact/journal growth, serialization times, throughput and cumulative wall time. The requested local safeguards are in the final config; they are independent of historical experiment ceilings. A code/config mismatch is a stop condition, not permission to relax identity checks.',
        '\n## Benchmark and feasibility',
        f'\nSelected batch/thread settings: {c["batch_size"]}/{c["threads"]}. Observed post-warmup throughput: {feasibility["selected"]["postwarmup_decisions_per_hour"]:.0f} decisions/hour over {feasibility["selected"]["postwarmup_seconds"]:.1f} seconds and {feasibility["selected"]["postwarmup_valid_decisions"]} measured decisions. Projected 250k: {feasibility["selected"]["projected_250k_hours"]:.2f} hours; with a 30% throughput discount: {feasibility["conservative_250k_hours"]:.2f} hours. Supports indicative 15-hour target: {feasibility["supports_15_hour_target"]}.',
        '\nSix disposable 4,000-decision probes compared batch 32/64 and CPU intra-op thread settings 1/2/4 with inter-op fixed at one. They contain real post-warmup replay and optimizer work. Batch 64 is selected only with a measured >5% end-to-end advantage. `benchmarks/results.json` retains sample throughput, replay sampling, optimizer latency, early M4-guided and late Q-dominant action latency, and checkpoint costs. These are readiness measurements, not official training or scientific performance comparisons.',
        '\nThe short probes do not establish a 15-hour guarantee. Later policies, longer episodes/history, a full replay buffer, higher heuristic-opponent share, CPU load and checkpoint costs can change throughput. Monitor and update the projection during Phase 2. No external GPU, Colab allocation, storage purchase or cost was incurred.',
        '\n## Phase 2 launch — requires the separate Phase 2 assignment',
        '\nUse this exact source branch and final pushed HEAD, verify all private prerequisite hashes and run repository preflight first. Do not run `uv sync` blindly after the additional Optuna installation; the historical base lock remains unchanged. The additional package pins are in `configs/improvement/requirements.txt`. Stockfish is unnecessary for M5 execution.',
        '\n```bash\n'+shlex.join(command)+'\n```',
        '\nExpected outputs: `official/attempt-0000/` containing `run.json`, resource telemetry, action-source log, replay journal, immutable evaluation snapshots and episode-boundary resume checkpoints plus sidecars. Resume with a new sibling output path and `--resume` pointing to the latest verified boundary checkpoint; retain the same config and selected source SHA.',
        '\nPhase 2 still owns the single official run, Q-only final selection/evaluation, bounded Atari evaluation authorized in that assignment, final presentation/demo integration and the eventual consolidation PR. Phase 1 does not authorize a merge or publication of private artifacts.',
        '\n## Live demo',
        '\nBaseline command: `.venv/bin/python -m videochess_rl.improvement.demo --live`. The historical frozen M4 path verified startup, checkpoint load, RGB recognition, legal choices, cursor execution and two player/opponent cycles. This is a smoke test, not an Atari game result.',
        '\nThe optional owner GUI `/home/dodaonam/Downloads/atari_videochess_live.py` was inspected and preserved. It loaded a historical warm M5 checkpoint, displayed live frames and four verified half-moves, and replayed five snapshots in both directions. Its checksum and shortened smoke profile are in `existing-demo/summary.json`. Launch it locally from repo root with `.venv/bin/python /home/dodaonam/Downloads/atari_videochess_live.py --m5-root artifacts/m5 --policy m5-warm-seed-20261104-post-rl`. It is not part of a clone and currently loads historical M5 identities; Phase 2 must explicitly adapt the new Q snapshot for the final presentation. No prerecorded video is required.',
        '\n## Verification and limits',
        '\nThe first full suite recorded three failures under a changing/loaded workspace and missing Stockfish PATH. A corrected stable run passed 540 tests with four skips. Focused checks then verified snapshot RNG isolation and config/lock changes. The final clean-checkout ledger records the final rerun and any private-artifact skips; skipped checks are never counted as passes. The repository has no configured source formatter; compileall and diff whitespace checks are required.',
        '\nNo official 250,000-decision training run, multi-seed training campaign, scratch comparison, merge, release, deployment or restricted-artifact upload occurred. All historical results remain preserved. Software readiness and time feasibility remain separate assertions.']
    (ROOT/'docs/improvement/PHASE1_HANDOFF.md').write_text('\n'.join(lines)+'\n')
    print(json.dumps(dict(verdict=verdict,selected=selected['sha256'],launch=shlex.join(command),inventory_sha256=sha(ARTIFACTS/'artifact-inventory.json'))))


if __name__=='__main__':main()
