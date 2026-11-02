# Phase 1 handoff — READY_FOR_PHASE_2

Experiment `videochess-improvement-20261103-v1`. This is a separate owner-authorized campaign; historical M0–M7 results and approvals remain unchanged.

## Repository and verification identity

Repository: https://github.com/dodaonam/atari-videochess-rl. Branch: `feature/videochess-performance-improvement-20261103`. Base main: `7415d821acf11dd3e07e4990c2f5539cfdf31916`.

Campaign compute revision: `c744dd6e895ff8a9000fb7bb328fe3e449de1314`. The final pushed source HEAD and clean-clone verification are recorded in `.agents/evidence/improvement/final-verification.json`; the Phase 1 results ledger separately records the tested source parent commit and all command identities.

Machine-readable aggregate evidence: `.agents/evidence/improvement/phase1-results.json`. Each retained command record includes actual UTC timestamps, exit code, revision, source-file inventory/hash, output log path/hash. The machine UTC date can precede the local campaign date in Asia/Ho_Chi_Minh.

## Private artifact prerequisites

Artifact root: `artifacts/improvement/videochess-improvement-20261103-v1/`. This is persistent local project storage on this machine, ignored by Git; a clone does not transfer it. Obtain these artifacts from the owner locally, without publishing them. Verify `artifact-inventory.json` and the individual sidecars before use.

Selected M4 checkpoint: `artifacts/improvement/videochess-improvement-20261103-v1/m4-a/epoch-22.pt`. SHA-256: `cf5e437ff4e2d6a8e85739df751dec33f16b7bc4c92268f996ec4c612d62feed`. Its adjacent `.pt.manifest.json` and the artifact-root `m4-selection.json` are required; the official CLI checks that selection identity. Historical M4 SHA-256 was verified as `724ac730f3c5f2d01b48b26eb7670a3c764978a3dd4d6702b3057a99ab1a90a4`; no fresh initialization substituted for it.

The accepted M3 release was independently loaded and verified. Source archive: `artifacts/m3/source/lichess_elite_2022-05.zip`, SHA-256 `ad374c8fd9fb2fe5f03c1297aa1d47cbbce5caedf6e6e2d387ee816930afdb11`. The third-party license remains unstated; use and all derived records remain internal and local.

## Dataset and leakage audit

Final release: `f2b3b52724958ffa845894681013cdc40915da179bbec3ae011087fe8a8ce0cc`, located at `dataset-v4/` under the artifact root. It selected exactly 5,000 normalized games, excluding all 1,000 historical games by identity. Exact game split: 4,000/500/500. Position split: {'test': 9234, 'train': 76606, 'validation': 8965}; total 94805. All 5,000 selected games have retained records. The 100,000-record bottom-k core had a 32-record per-game cap; leakage protection removed {'cross_split_board_overlap': 4770, 'historical_train_validation_exposure': 427}. Six zero-record parents were completed using one lowest-ranked eligible candidate from each original per-game reservoir, preserving existing records, splits, the 32-per-game limit and the 100k final cap. No records were synthesized.

Zero remaining cross-split board signatures and zero historical train/validation board exposure in the new holdouts. There are 90511 distinct board signatures; records are not claimed to be unique board positions. Duplicate sample IDs: 0. Repeated complete-history/target pairs: 2796; these are legitimate cross-game observations, not identical whole release records. Effective-input uniqueness by split: {'test': 9181, 'train': 73277, 'validation': 8939}.

Phase coverage: {'test': {'endgame': 1646, 'middlegame': 6073, 'opening': 1515}, 'train': {'endgame': 12265, 'middlegame': 48447, 'opening': 15894}, 'validation': {'endgame': 1359, 'middlegame': 6106, 'opening': 1500}}. Phase is a disclosed descriptive heuristic: opening before ply 20; otherwise endgame at at most 12 pieces; otherwise middlegame. No phase quota was applied to the dataset. Two independent full archive scans produced identical protected core position bytes and normalized game sets. A subsequent coverage audit found six zero-record parents. The v4 release adds six deterministic leakage-safe coverage records; HPO used an unchanged input projection (8,192 train and 8,964 validation), verified against v4 without additional trials. The superseded first build retained chunk-local ordinals; v4 contains global archive ordinals and excludes runtime duration from release identity. The failed v2 tuple-shape diagnostic is retained.

Rebuild: `.venv/bin/python -m videochess_rl.improvement.data --output artifacts/improvement/videochess-improvement-20261103-v1/dataset-reproduction` into a fresh output namespace (the builder refuses overwrite). Verify/load: `videochess_rl.improvement.data.verify_release`. Manifests bind config, archive/member, historical exclusion inputs, splits, every data file and cache by SHA-256.

## HPO, expert labels, and M4 training

Optuna GP search: eight-trial/six-epoch/45-minute ceiling; three deliberately enqueued completed startup trials; fixed seed 20261103 and an identical 8192-record training subset. Objective: minimum human-validation NLL. GP proposals reached: 5. Best: {'learning_rate': 0.00015, 'weight_decay': 5e-05}, objective 2.400505335402244. Runtime: 473.6 seconds. All trial states and intermediate objectives are retained in `hpo/trials.json` and private `hpo/study.sqlite3`.

Stockfish 19: Threads=1, Hash=64 MiB, MultiPV=1, fixed nodes=50000; pilot measurements and engine binary hash are in `expert/pilot.json`. Labels: 4000 train plus 128 separate validation-development positions. All 4128 labels passed independent sample/split/FEN/legal-move checks. Score perspective is side to move; mate scores remain distinct. Training subset phase coverage: {'endgame': 500, 'middlegame': 3000, 'opening': 500}. Label SHA-256: `fd648bfada1be468d662b2f696639e73c5826ed31a6e7a85f6a4bd49fc9429e0`. No test positions were labeled for training.

M4-A loads the verified historical model, uses a fresh AdamW optimizer and HPO parameters, clipping 1.0, max 25 epochs/patience 5. M4-B loads best A, uses half its learning rate, max 5 epochs/patience 2, and .8 human mean CE plus .2 independently normalized expert mean CE. Both use only seed 20261103. Logical batch 64 is accumulated through bounded physical microbatches of at most 32. HPO trials are separate short optimization probes.

Actual M4-A epochs: 25; early stopped: False. Actual M4-B epochs: 3; early stopped: True. Both immutable stage results identify the best epoch/checkpoint and SHA-256.

| Candidate | Validation NLL | Human top-1 | Human top-3 | Expert dev agreement | Simulator development score | SHA-256 |
|---|---:|---:|---:|---:|---:|---|
| historical | 2.430262 | 0.2986 | 0.5433 | 0.3203 | 0.725 | `724ac730f3c5f2d01b48b26eb7670a3c764978a3dd4d6702b3057a99ab1a90a4` |
| M4-A | 2.208634 | 0.3440 | 0.6070 | 0.3047 | 0.875 | `cf5e437ff4e2d6a8e85739df751dec33f16b7bc4c92268f996ec4c612d62feed` |
| M4-B | 2.203648 | 0.3476 | 0.6127 | 0.3281 | 0.850 | `5def36a4d607fac2ebc887617d17e28e9e766b5d8c0bd66dcbf05aa58b115fc6` |

Selected: **M4-A**. Selection was saved before test inspection. Invalid checkpoints are rejected; B requires NLL <=1.05*A; maximize fixed simulator development score, then lower validation NLL, then earlier candidate. Each candidate played the same five development scenario seeds, both opponents and colors: 20 games at a 400-decision cap. Score is (wins + .5 true draws)/20; truncations contribute zero and are reported separately, never invented as draws. Outcome breakdown: `{"M4-A": {"random_legal/black": {"draw": 1, "win": 4}, "random_legal/white": {"draw": 1, "win": 4}, "simple_material_heuristic/black": {"draw": 3, "win": 2}, "simple_material_heuristic/white": {"win": 5}}, "M4-B": {"random_legal/black": {"draw": 3, "win": 2}, "random_legal/white": {"draw": 2, "win": 3}, "simple_material_heuristic/black": {"draw": 1, "win": 4}, "simple_material_heuristic/white": {"win": 5}}, "historical": {"random_legal/black": {"draw": 3, "win": 2}, "random_legal/white": {"draw": 1, "win": 4}, "simple_material_heuristic/black": {"draw": 3, "win": 2}, "simple_material_heuristic/white": {"draw": 4, "win": 1}}}`.

Selected reserved-test evaluation occurred once: `{"examples": 9234, "nll": 2.202227017206626, "top1": 0.34080571799870046, "top3": 0.6045050898852068}`. Human move prediction, offline engine agreement, simulator score and Atari outcomes are separate measures; none is Elo or a chess winning probability.

## M5 implementation and final configuration

Independent entry point: `videochess_rl.improvement.m5`. Exactly one fixed seed and one warm arm; no scratch CLI. Fresh Q head uses an independent deterministic seed domain; only shared M4 representation transfers. Target starts equal to online. The frozen behavior head supplies exploration preferences, not calibrated Q values. Evaluation snapshots load only the Q-network.

Final configuration: `configs/improvement/m5-phase2.json`. All fields are bound and validated, including the 250,000-decision limit, AdamW, Huber, gamma .99, replay 16,384/warmup 1,024, one update per four decisions, clipping 1, target sync every 500 updates, terminal rewards +1/-1/0 and no shaping. Unsupported seed/arm/algorithm/reward/snapshot combinations are rejected.

Exploration: epsilon 1 -> .05 over 175,000 valid decisions; within exploration, p(M4)=.6*max(0,1-t/75000), else uniform legal action. Every action source is logged against the actual replay transition ID. The frozen M4 is not an optimizer parameter. No Stockfish process is used by the runner.

Opponent schedule is deterministic per episode, with RandomLegal probability .5 through t=50,000, .35 through 150,000, then .25; other episodes use SimpleHeuristic. Opponents are selected at episode reset using indexed curriculum RNG; an existing game never changes opponent mid-game. Agent color alternates. The validated low-level legacy transition seed contract is reused; the historical paired campaign runner is not invoked.

## Recovery and snapshot procedure

Evaluation-only snapshots occur at 0,25k,...,250k. Their sidecars explicitly mark non-resumable semantics. Snapshot verification preserves training RNG. Resumable checkpoints occur after crossing each 1,000-decision interval at the next completed episode boundary. Online/target/optimizer, replay pinned journal prefix, RNG streams, episode/update/sync counters, config/code/M4 hashes and cumulative resource usage are saved.

A mid-episode decision or wall cap does not fabricate a terminal transition. Preserve that attempt directory. Recover from its latest verified completed-episode checkpoint into a new sibling attempt directory using the same exact code/config/M4 SHA. `--resume <checkpoint>` forks only the committed journal prefix; original discarded tails remain evidence. Never concatenate an uncommitted tail into replay. Changed attempt IDs for repeated work are expected; semantic transitions, model/optimizer states and RNG must match.

Recovery probe passed all invariants: `{"action_source_counters": true, "completed_episodes": true, "cumulative_wall": true, "exploration_rng": true, "frozen_m4": true, "online": true, "optimizer": true, "optimizer_updates": true, "replay_rng": true, "semantic_replay": true, "target": true, "target_syncs": true, "transitions": true, "unique_replay_ids": true, "valid_decisions": true}`. Repeated parent tail: 3271 decisions. The runner charges previous attempts, including failed sibling forks. A crash without a final report is conservatively billed through recovery time, including downtime. Keep all official attempts under the same `official/` parent. An OS file lock prevents simultaneous attempts in that namespace.

The selected machine observed peak RSS of about 529 MB, available RAM around 26.0 GB, and more than 34 GB free disk during benchmarks. At 4,000 transitions, a full representative replay journal used about 2,873 bytes per decision. The conservative artifact projection is about 2.09 GB; the simple fourfold RSS allowance is about 2.12 GB. See `.agents/evidence/improvement/resource-feasibility.json` for the formulas and limits. Resource guards monitor process RSS, available system RAM, free disk, artifact/journal growth, serialization times, throughput and cumulative wall time. The requested local safeguards are in the final config; they are independent of historical experiment ceilings. A code/config mismatch is a stop condition, not permission to relax identity checks.

## Benchmark and feasibility

Selected batch/thread settings: 32/4. Observed post-warmup throughput: 60433 decisions/hour over 166.8 seconds and 2800 measured decisions. Projected 250k: 4.14 hours; with a 30% throughput discount: 5.91 hours. Supports indicative 15-hour target: True.

Six disposable 4,000-decision probes compared batch 32/64 and CPU intra-op thread settings 1/2/4 with inter-op fixed at one. They contain real post-warmup replay and optimizer work. Batch 64 is selected only with a measured >5% end-to-end advantage. `benchmarks/results.json` retains sample throughput, replay sampling, optimizer latency, early M4-guided and late Q-dominant action latency, and checkpoint costs. These are readiness measurements, not official training or scientific performance comparisons. Action-latency timings at schedule points 0 and 200,000 reuse real replay features; they are not achieved training counts. The twelve additional optimizer microtiming updates per case are disposable and are not represented as training decisions.

The short probes do not establish a 15-hour guarantee. Later policies, longer episodes/history, a full replay buffer, higher heuristic-opponent share, CPU load and checkpoint costs can change throughput. Monitor and update the projection during Phase 2. No external GPU, Colab allocation, storage purchase or cost was incurred.

## Phase 2 launch — requires the separate Phase 2 assignment

Use this exact source branch and final pushed HEAD, verify all private prerequisite hashes and run repository preflight first. Do not run `uv sync` blindly after the additional Optuna installation; the historical base lock remains unchanged. The additional package pins are in `configs/improvement/requirements.txt`. Stockfish is unnecessary for M5 execution.

```bash
.venv/bin/python -m videochess_rl.improvement.m5 --config configs/improvement/m5-phase2.json --checkpoint artifacts/improvement/videochess-improvement-20261103-v1/m4-a/epoch-22.pt --checkpoint-sha256 cf5e437ff4e2d6a8e85739df751dec33f16b7bc4c92268f996ec4c612d62feed --output artifacts/improvement/videochess-improvement-20261103-v1/official/attempt-0000 --phase2-official
```

Expected outputs: `official/attempt-0000/` containing `run.json`, resource telemetry, action-source log, replay journal, immutable evaluation snapshots and episode-boundary resume checkpoints plus sidecars. Resume with a new sibling output path and `--resume` pointing to the latest verified boundary checkpoint; retain the same config and selected source SHA.

Phase 2 still owns the single official run, Q-only final selection/evaluation, bounded Atari evaluation authorized in that assignment, final presentation/demo integration and the eventual consolidation PR. Phase 1 does not authorize a merge or publication of private artifacts.


The fresh-process Phase 2 CLI/recovery check passed with `PATH=/usr/bin:/bin` and no Stockfish executable available. It completed a 4,500-decision disposable probe, restored its 4,026-decision checkpoint after one target sync and resumed to 4,800 decisions. Source/config/M4 identities, intra-op/inter-op threads, replay/transition counts and cumulative wall time all matched. Full details are in `.agents/evidence/improvement/phase2-cli-verification.json`; private output and checkpoints remain in `cli-verification-v2/`. The attempt identities are `probe`, so those checkpoints cannot resume the official Phase 2 identity.


## Live demo

Baseline command: `.venv/bin/python -m videochess_rl.improvement.demo --live`. The historical frozen M4 path verified startup, checkpoint load, RGB recognition, legal choices, cursor execution and two player/opponent cycles. This is a smoke test, not an Atari game result.

The optional owner GUI `/home/dodaonam/Downloads/atari_videochess_live.py` was inspected and preserved. It loaded a historical warm M5 checkpoint, displayed live frames and four verified half-moves, and replayed five snapshots in both directions. Its checksum and shortened smoke profile are in `existing-demo/summary.json`. Launch it locally from repo root with `.venv/bin/python /home/dodaonam/Downloads/atari_videochess_live.py --m5-root artifacts/m5 --policy m5-warm-seed-20261104-post-rl`. It is not part of a clone and currently loads historical M5 identities; Phase 2 must explicitly adapt the new Q snapshot for the final presentation. No prerecorded video is required.

## Verification and limits

The final full repository suite passed 545 tests, with four skips for unavailable private historical M5 artifacts and synthetic historical revision fixtures. Focused improvement checks passed for dataset coverage/provenance, HPO projection, M4 source verification and stopping rules, expert-label validation, batch 32/64 equivalence, schedules, M4-guided action legality, snapshots, target/replay recovery, interrupted journal tails, and cached action-feature equivalence. The fresh-process CLI/recovery check passed after a real target-network sync at decision 4,026. Clean-clone project-state recovery and preflight passed. The pushed `11a99b58` detached worktree also passed preflight and 44 focused campaign/M5/context regression checks. `scripts/agent_preflight.py` reports no errors and the expected artifact-inventory warning. Compilation and whitespace checks passed. Exact timestamps, revisions, commands and retained log hashes are listed in `.agents/evidence/improvement/final-verification.json`.

No official 250,000-decision training run, multi-seed training campaign, scratch comparison, merge, release, deployment or restricted-artifact upload occurred. All historical results remain preserved. Software readiness and time feasibility remain separate assertions. The feature branch was pushed without opening a PR; the final pushed HEAD and clean worktree verification are recorded in `final-verification.json`. Phase 1 ready status does not authorize Phase 2 until its separate direct assignment is given.
