# M5 Final Research and Engineering Report

**Status:** Independent PM accepted M5-01 through M5-05 on 2026-10-30, with documented limitations for M5-03 and M5-04. PR #11 was subsequently merged and G3 separately approved; see the [G3 decision and post-merge verification](../../.agents/evidence/G3-final-approval-20261030.md). This report summarizes the evidence retained in the private M5 artifact tree and committed evidence records. It does not claim Atari performance or a calibrated rating.

## Objective and method

M5 tested whether an action-conditioned Double DQN trained from M2 simulator rewards improves over its own initialization, and compared an accepted M4 representation warm start with an architecture-matched Scratch arm. Double DQN separates next-action selection from next-action valuation: the online network chooses the legal semantic UCI action with maximum Q, and the target network evaluates that same UCI. This reduces the maximization bias of ordinary DQN. True chess outcomes do not bootstrap; valid time-limit truncations bootstrap from their final legal position. Rewards remain in the fixed agent's perspective, including when the agent is Black.

The model reuses the accepted mover-oriented board, metadata, complete history, candidate representation, and shared M4 scorer layers, with a fresh scalar Q head. Warm-start copied only accepted shared representation weights; it did not transfer the behavior head, optimizer, logits, or teacher scores. Scratch used the same architecture and paired seed derivation. Actions are identified by UCI, never by a persistent candidate row number. The policy inference path does not require Stockfish.

The six-run paired design used seeds 20261104–20261106, 50,000 valid decisions per arm/seed (300,000 total), a 50/50 deterministic opponent schedule, and the fixed `videochess-m5-seed-derivation/1.0` contract. Replay capacity/warm-up were 16,384/1,024; batch size 32; one AdamW update per four decisions; LR and weight decay 1e-4; Smooth L1; gradient norm 1; gamma .99; target sync every 500 completed updates; epsilon 1.0→.05 over 37,500 decisions; 400-decision episode cap. No shaping, curriculum, auxiliary loss, teacher target, search opponent, or tuning campaign was used.

## Training execution and recovery

All six runs completed exactly 50,000 valid decisions, 12,245 optimizer updates, and 24 target synchronizations. CPU backend was PyTorch 2.14.1+cpu, intra-op 4/inter-op 1. Completed episode counts were 389, 379, 435, 413, 551, and 408 in the run order below. Final epsilon was .05. Two recovery events—the initial Warm-start checkpoint loader issue and the owner-directed pause—were retained and charged; recovery verification restored model, target, optimizer, replay, counters, and RNG state. Final policy snapshots are non-resumable; training checkpoints are separate episode-boundary recovery bundles.

| Arm | Seed | Decisions | Updates | Syncs | Episodes | Physical run seconds | Peak RSS bytes | Status |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| Warm-start | 20261104 | 50,000 | 12,245 | 24 | 389 | 13,702.770 | 932,016,128 | Complete |
| Scratch | 20261104 | 50,000 | 12,245 | 24 | 379 | 14,118.803 | 947,097,600 | Complete |
| Warm-start | 20261105 | 50,000 | 12,245 | 24 | 435 | 12,075.140 | 961,261,568 | Complete |
| Scratch | 20261105 | 50,000 | 12,245 | 24 | 413 | 12,055.170 | 961,261,568 | Complete |
| Warm-start | 20261106 | 50,000 | 12,245 | 24 | 551 | 9,237.468 | 833,622,016 | Complete |
| Scratch | 20261106 | 50,000 | 12,245 | 24 | 408 | 13,649.631 | 929,718,272 | Complete |

The final Scratch 20261106 snapshot SHA-256 is `94838bc8c3547a5b8ce9e1d8c1dde66b86163defb868b18be6185895acf9663c`. Its latest resumable checkpoint at decision 49,833 restored and matched the 50,000-record replay journal chain, ending at `a7ef5b08009068e8083a48366cafd02266c37741264014a81b3d41d0e5215590`. The final decision occurred mid-episode; no terminal result, truncation, reward, or reset was fabricated.

## Compute and resource accounting

The real-replay feasibility gate used 1,029 simulator transitions and five representative batch-32 updates. The selected four-thread CPU configuration was the fastest measured setting. Observed profile means: 0.0356 seconds per policy/simulator decision (p95 0.0785), 18.69 legal candidates (p95 37), 223.5 history plies (p95 497.6), and 0.583-second update mean (p95 0.683). These are feasibility measurements, not training throughput guarantees. No GPU backend was available or used.

The verified resource ledger charges 77,899.281 seconds to training (including profiling, setup, failed-attempt reserve, and recovery validation) of 216,000 seconds; 138,100.719 seconds remain. All runs stayed below their individual 28,800-second caps. Evaluation used 1,983.451 seconds of 43,200; 41,216.549 seconds remain. Artifact inventory is 6,544,747,450 bytes of 8,589,934,592; 2,045,187,142 bytes remain. No paid compute or GPU was used. The largest observed training RSS was 961,261,568 bytes.

## Frozen evaluation

The frozen schedule ran all 15 policy groups on the same 25 seeds, two opponents, and both colors: 1,500 game rows. There were 1,494 terminal games and six valid 400-decision truncations, with zero unresolved scenarios, incomplete attempts, or journal diagnostics. Weights were frozen; epsilon was zero; evaluation inserted no replay and performed no optimizer updates. The primary terminal-game score is `(wins + 0.5*draws)/terminal games`; W/D/L columns below preserve terminal outcomes and list truncations separately.

| Policy | W/D/L | Truncated | Terminal score |
|---|---:|---:|---:|
| Frozen M4 behavior-only | 48/50/2 | 0 | .730 |
| Warm 20261104 pre | 2/85/13 | 0 | .445 |
| Warm 20261104 post | 16/78/5 | 1 | .556 |
| Scratch 20261104 pre | 0/64/35 | 1 | .323 |
| Scratch 20261104 post | 12/86/2 | 0 | .550 |
| Warm 20261105 pre | 3/39/56 | 2 | .230 |
| Warm 20261105 post | 19/79/2 | 0 | .585 |
| Scratch 20261105 pre | 0/72/28 | 0 | .360 |
| Scratch 20261105 post | 3/91/6 | 0 | .485 |
| Warm 20261106 pre | 0/37/63 | 0 | .185 |
| Warm 20261106 post | 24/74/2 | 0 | .610 |
| Scratch 20261106 pre | 0/66/33 | 1 | .333 |
| Scratch 20261106 post | 8/90/1 | 1 | .535 |
| RandomLegal baseline | 3/58/39 | 0 | .320 |
| SimpleHeuristic baseline | 33/63/4 | 0 | .645 |

For the primary terminal-only crossed comparisons, truncation censors some pairs. Consequently the four campaign-level matched comparisons have point estimates but no bootstrap interval; they are not silently imputed. Warm-start post-minus-pre was +.296 and Scratch post-minus-pre +.185. Warm-minus-Scratch was -.056 pre-RL and +.062 post-RL. Per-training-seed values and censor counts are preserved in the machine report.

A clearly marked post-hoc capped-reward sensitivity analysis retains the actual zero reward for time-limit truncations and bootstraps the full paired scenario grid (10,000 crossed resamples; three training-seed clusters and 25 evaluation-seed clusters). It found Warm pre→post +.295, 95% CI [.115,.435]; Scratch pre→post +.183, CI [.118,.242]; Warm−Scratch pre −.052, CI [-.175,.110]; Warm−Scratch post +.060, CI [-.003,.118]. This is supplementary, not the terminal-outcome primary analysis, and was not used to select policies. Three training seeds provide limited precision. No calibrated Elo is reported.

The observed data suggest both arms improved over their initialization and both trained arms beat RandomLegal on aggregate, while the frozen M4 policy and SimpleHeuristic remained stronger overall. Warm-start versus Scratch differences are small and uncertain. This does not establish general chess strength: episodes have sparse terminal rewards, the opponent pool is limited, and only three training-seed clusters were used. All measurements are from the M2 simulator, not Atari ALE VideoChess.

## Post-review integrity reconciliation — 2026-10-30

The owner-requested remediation verified the private run and evaluation artifacts read-only. Six run summaries, attempt records, manifests, final snapshots, replay journals, counters, and the resource ledger agree: 300,000 transitions/valid decisions, 73,470 updates, and 144 target synchronizations. A separate read-only verifier checked all six 50,000-record replay hash chains and all 15 evaluation event journals; it found 1,500 unique frozen scenarios, 1,494 terminal games, and six valid cap truncations. The root manifest independently verifies seven manifests and 6,544,747,450 bytes. No experimental artifact was edited or regenerated.

### Evaluation source identity

The official evaluation source identity records 42 Python files and aggregate SHA-256 `ccb7d76be64c55ae4c4519da3a5647a5a2da86924a00d9490a7e807cc7497848`. At PR head `575dce5978567417d2915d5dd36a47873293b607`, 39 per-file hashes match directly. The other three are exactly reconstructible and the reconstructed aggregate matches `ccb7d76…`:

| File | Recorded SHA-256 / size | PR-head SHA-256 / size | Verified difference |
|---|---|---|---|
| `videochess_rl/rl/evaluate.py` | `694415d51bdc316648c30124d3d4df36b970484c2ce3bb04cdc0ae7a615652c8` / 14,853 B | `00eaa86c9da75606bab3f108ec00906f86db89b7407224e859913c7467f4e4d9` / 17,009 B | The documented post-evaluation `paired_capped_reward_differences` helper begins at byte 14,854. Truncating after the recorded 14,853-byte prefix reproduces the recorded file hash. |
| `videochess_rl/rl/training.py` | `eca25d8b692ce77e07a3be4736eabbb71ed629d69717259de258905fa72fe90a` / 12,356 B | `053e95db5357a8b68215e9ff00feda53000783ca327efe7596f694cb0a010af6` / 12,355 B | Appending one terminal LF reproduces the recorded hash; content is otherwise byte-identical. |
| `videochess_rl/rl/transition.py` | `df60fee8bf908e8d96901937dfc120d7e5a8f8e06a0119040e61356014aa645d` / 13,950 B | `c10821bc0b74d30acf66d582e9e9ed7148149469bb56213b25373c730ab3e09d` / 13,949 B | Appending one terminal LF reproduces the recorded hash; content is otherwise byte-identical. |

This is an exact byte reconstruction for the evaluation runner source identity. The trailing-newline and supplementary-analysis changes happened after the official runs and do not alter evaluation decisions or scoring. The reproducible checker is `scripts/verify_m5_source_identity.py`.

### Training source identity and original limitation finding

**Historical audit assessment:** this section records the evidence state before the owner supplied the full continuation-session transcript. Its missing-source and possible replay-distribution concern is superseded by the forensic follow-up at the end of this report.

Run manifests record source SHA `093992c50e893a7fdd92f2f95faafe28d4f1e73c7351a4a8179a3056c4e63b00` for all four seed-20261104/20261105 runs, and `cdcc1fdc0ca0b324e49cfb8b0ff571496a554e9892dfb3620d6454a65ee16da0` for both seed-20261106 runs. The two arms within each seed pair share a source hash. Training timestamps place the seed-20261106 pair after the resumption/recovery work.

Checkpoint-history snapshots before and after that work show exactly three Python paths changed between `cp-08f98f9d-20261029T043013180672Z` and `cp-08f98f9d-20261029T143803674896Z`:

| File | Earlier workspace SHA-256 | Later workspace SHA-256 | Later Git blob |
|---|---|---|---|
| `videochess_rl/rl/checkpoint.py` | `19ab713b5a1450c2e4506d9d761768317e0b48fb96a3cb0083965d6a037bc410` (not found) | `924a95e6accb04c727e2858dbcd6cbda84b970750decc27fd09621bdc61821aa` | `bc1494666d3234c82ff82f2fb8ee851d9558c24b` |
| `videochess_rl/rl/cli.py` | `795ca9865da80bf982480b25d97367c846255e167d9c64320a73030106c2efe3` (not found) | `3f966fffa3a31ed9330004448ca84bc86a4fd6446764d3184e248cff978b60b7` (not found) | unavailable |
| `videochess_rl/rl/replay.py` | `5ae4d3d928c524539bcf6b29f4102f09b246d5703b66539f2fad4aa7e2aaa278` (not found) | `21845b0755809d07d480da821c2e809540a0ca4b8e1eddc5785ebdec5cf59b7f` | `355f8f0868152815debce129cc327d8bcecef970` |

At the time this audit was first written, the old `checkpoint.py`, `cli.py`, and `replay.py` bytes had not been located in Git objects or local backups. The initial report therefore could not compare the replay sampler and treated a change in learning distribution as possible. The owner later supplied the full Codex continuation transcript; two runtime files were recovered byte-for-byte from it and the CLI changes were audited from its source excerpts and patch records. See the dated forensic follow-up below for the updated evidence and residual CLI limitation.

The source identity changes at seed `20261106`, so byte-identical source provenance is not established across all six runs. The initial audit treated this as a possible training-method confound. The forensic follow-up assesses whether the actual changes affect learning semantics and whether the final pair resumed from a checkpoint. No run has been repeated or selectively replaced, and this report does not initiate additional training.

### Additional implementation findings and fixes

- The live aggregate-budget check added committed time from completed runs and then added elapsed time since the whole campaign start. On later runs in one invocation this could double-count prior run time in the stop guard. It did not affect the recorded ledger or stop any run; all six runs completed below the caps. The guard now adds only the active run's uncommitted interval to the committed ledger, with a regression test.
- `Transition._identity_document` contained unreachable code after `return`; seed schedules were already validated before calling it. The dead branch was removed, with a regression test confirming non-object schedules still fail validation.
- The M5 CLI's M3/M4 artifact locations now support `VIDEOCHESS_M5_M3_RELEASE_DIR` and `VIDEOCHESS_M5_M4_DIR`; pinned release/checkpoint hashes remain mandatory. Private artifacts remain outside Git. The README documents this clean-checkout limitation.
- The 28 verified M5 evidence logs existed locally and matched recorded commands/results/exit codes; all passed the credential-pattern scan. They were ignored by `*.log`, explaining the clean-clone preflight failure. Exactly those referenced logs were force-added, and preflight now rejects future untracked M5 evidence logs. The audit inventory is `.agents/evidence/M5-remediation-log-inventory-20261030.json`.

At remediation candidate `063c24cc9ab221e264bf06aadc6f57f7b45c7017`, the full local suite passed 368 tests in 138.487 seconds. A clean clone at the same SHA passed canonical preflight and ran 368 tests in 136.734 seconds, with one documented skip because the accepted M4 checkpoint is private and absent from the clone; the same transfer test ran in the local suite with the authorized M4 artifact. GitHub Actions run `41006247210` passed at that exact SHA; its Repository preflight workflow ran the standard-library context, bundle, and M5 contract-oracle tests, not the full PyTorch suite. The remediation audit documents the source blocker.

The follow-up remediation candidate `026d41b7cb275affef5cffc27747449da7e045a3` also passed: local regression 368 tests in 142.808 seconds; clean-clone preflight passed; clean-clone regression ran 368 tests with one skip because the private M4 checkpoint is unavailable in Git; and GitHub run `41006965692` passed on that exact head. The skipped test ran without a skip in the local suite. The GitHub workflow covered canonical preflight and standard-library context/bundle/M5 oracle tests, not the full PyTorch suite.

At exact candidate `57c8bce28b151b3f30b03b3b972561e142d18b16`, a fresh local run passed all 368 tests in 145.322 seconds (peak RSS 357,588 KiB). A remote clean clone at the same SHA passed canonical preflight and all 368 tests in 144.747 seconds; one test requiring the private M4 checkpoint was skipped there and passed locally. Local and clean-clone preflight returned zero errors, with only the expected separate artifact-manifest warning. GitHub run `41007586702` passed on that exact SHA and ran repository preflight plus standard-library context, bundle, and M5 contract-oracle tests; it did not run the full PyTorch suite. The artifact manifest, private campaign journal verifier, and source-identity verifier also passed read-only at this revision.

At the time of the original audit, M5 engineering remained incomplete pending source-history disposition. The updated engineering assessment is in the forensic follow-up below; independent PM acceptance remains separate. G3 and M6 remain outside scope.

After source recovery and its regression additions, the complete local repository suite passed **383 tests** in 164.146 seconds (166.59 seconds wall time; peak RSS 360,172 KiB) on staged candidate diff `da696d5515f3dfe2ec53d8137914d444ffc4c73eb61a8679212b1d85455ec2ab`. The retained log is `.agents/evidence/logs/M5-full-suite-forensic-20261030.log`. The exact committed PR HEAD still requires a fresh clean-clone suite, canonical preflight, and GitHub Actions check; no earlier CI result is being presented as evidence for that future HEAD.

### Exact source-commit verification — `8192a6124dc0d5938bf0ac14ca729f0561573101`

The feature source commit passed the full local suite: **383/383**, 167.357 seconds test time, 169.52 seconds wall time, 358,684 KiB peak RSS, no skips. A fresh clean clone at the same SHA passed canonical preflight with zero errors and one expected private-artifact warning; its suite passed **383 tests with one expected skip** for the accepted private M4 transfer artifact (156.621 seconds test time, 158.89 seconds wall time, 358,840 KiB peak RSS). Local and clean-clone preflight portable-index checks passed; the clean clone's workspace-specific snapshot mismatch is expected for a distinct workspace identity.

At the same exact SHA, read-only private verification passed: artifact manifest **7 manifests / 6,544,747,450 bytes**; campaign **6 runs, 300,000 decisions/replay records, 73,470 optimizer updates, 144 target synchronizations**; evaluation **1,500 unique scenarios, 1,494 terminal games, six truncations**; evaluation source aggregate `ccb7d76be64c55ae4c4519da3a5647a5a2da86924a00d9490a7e807cc7497848`. The recovered-source verifier passed on the same source commit. GitHub Actions run [`41022841165`](https://github.com/dodaonam/atari-videochess-rl/actions/runs/41022841165) passed on that exact SHA. Its workflow ran canonical context/preflight and standard-library context, bundle, and M5 contract-oracle tests; it did not run the 383-test PyTorch suite. The feature branch's final delivery commit adds only evidence/report/state after this source commit; the final PR SHA and its exact-head checks are recorded in the pull request and final handoff.

## Acceptance assessment

| Criterion | Assessment | Evidence |
|---|---|---|
| M5-01 Double DQN arithmetic and legal semantic next action | ACCEPTED | `tests/test_m5_targets.py`, `tests/test_m5_transition.py`, target-disagreement fixtures; see focused/full test logs and PM acceptance record. |
| M5-02 Reward/player perspective and transition semantics | ACCEPTED | transition tests and `docs/03-technical/RL_ALGORITHM.md`; terminal/truncation distinction is represented explicitly; see PM acceptance record. |
| M5-03 Replay, target, exploration, recovery, opponent provenance | ACCEPTED WITH DOCUMENTED LIMITATION | Recovered source hashes, AST/diff verification, deterministic old/current restore test, and actual checkpoint restoration logs for both source groups. Whole historical CLI bytes remain unavailable; no full-file identity claim. |
| M5-04 Controlled Warm/Scratch/M4/baseline evaluation | ACCEPTED WITH DOCUMENTED LIMITATION | Six matched-budget runs, 1,500 frozen games, source difference mapped to recovery/metadata code, and final-seed attempts confirmed fresh. Three training-seed clusters and six truncated games limit inference. |
| M5-05 No silent curriculum, shaping, or auxiliary objective | ACCEPTED | fixed config/protocol, training manifests, and source/test review. |

## Reproduction and evidence identities

Canonical config SHA-256: `84d305084397ad18397dfe395fab58de824fa056729675d0d1cd9ca8bdd06d8d`. Training campaign verification SHA-256: `32098bd4a2df7b2d317c29adcd0d6c258319dd35724eb84575e74135207bd93c`. Evaluation verification SHA-256: `64f4c10450440e17bd8e2758b8edc03196633021a0d652eff7d62368f111d5c8`. Evaluation report SHA-256: `5786aaf4889c748468455ee31ecb2dd3f7185ee084d7b8ce8ced99df58ae6748`. Artifact inventory: `artifacts/m5/artifact-manifest.json`; verify locally with `python scripts/m5_artifact_manifests.py --verify`. Private checkpoints, journals, and raw game rows are not included in a clean Git clone; their manifests and identities are committed as evidence.

To reproduce evaluation analysis in the M5 environment, use the supported M5 evaluation CLI and frozen roster/config under `configs/rl/m5-double-dqn-v1.json`, then run `python scripts/m5_evaluation_sensitivity.py` for the explicitly supplementary sensitivity. Full command lines, software versions, logs, run/attempt IDs, per-policy journals, hashes, and raw rows are in `.agents/evidence/` and the private `artifacts/m5/` inventory. GitHub's context/preflight workflow, when reported, must not be described as the full PyTorch regression suite.

## Limitations and next milestone boundary

Evaluation is simulator-only; M6 must separately integrate the actual Atari ALE observation/control loop and test synchronization between emulator state and chess history. The small training-seed count, two-opponent pool, sparse reward, censored terminal pairs, and limited compute constrain generalization and uncertainty. M5 did not run GPU benchmarking, hyperparameter search, or actual Atari evaluation. At initial report publication, PR #11 awaited PM review and G3 was unapproved. PR #11 was subsequently merged and G3 approved; M6 remains not authorized or started.

## Forensic source-provenance follow-up — 2026-10-30

The owner supplied the complete continuation-session transcript at `/home/dodaonam/Downloads/Pasted text(20261030-060523).txt`. Its byte identity is 3,655,066 bytes, SHA-256 `c5d8706cff0f7634620b835d1a8063ac43f8bd8eec277995ed09f3b00a693e8f`. Exact UTF-8 extraction of transcript lines 1647–1873 recovers historical `checkpoint.py` at the recorded hash `19ab713b…`; lines 1874–2017 recover historical `replay.py` at the recorded hash `5ae4d3d9…`. Both source files therefore have verified byte-level provenance.

The first four training runs record aggregate source `093992c50e893a7fdd92f2f95faafe28d4f1e73c7351a4a8179a3056c4e63b00`; both `20261106` runs record `cdcc1fdc0ca0b324e49cfb8b0ff571496a554e9892dfb3620d6454a65ee16da0`. Checkpoint-history identifies three runtime files between those snapshots. Replay-buffer construction, insertion/eviction, sampling, state serialization/restoration, and replay-journal append are AST-identical. Only journal verification and checkpoint validation/restoration changed. The changes bound the recovery cost and validate state before mutation; they do not alter the sampled minibatch distribution or learning update. `training.py`, `transition.py`, `network.py`, `targets.py`, configuration, reward, and seed derivation were unchanged in the recorded source interval.

The complete historical CLI files could not be reconstructed to their recorded whole-file hashes. The transcript does contain the old resume-selector function, the final selector fragment, and all four training-time CLI patch events. They change recovery compatibility and checkpoint selection. The two last-seed official runs are verified as `attempt-0000` with no resume-parent hash and exactly 50,000 valid decisions, so neither invoked the changed checkpoint-selection/restore path. Warm/Scratch remain source-matched within each paired seed. The aggregate code identity still differs for the third seed, so the report preserves that byte-provenance fact; the recovered changes provide no evidence of a seed-correlated learning-method change. No byte-identical execution claim is made.

Read-only restoration against actual episode-boundary checkpoints passed for Scratch seed `20261105` (49,967 decisions; 16,384 replay rows; 194.32 seconds; 766,320,640-byte peak RSS) and seed `20261106` (49,833 decisions; 16,384 rows; 202.83 seconds; 779,337,728-byte peak RSS). Both checks matched online/target tensors, optimizer, counters, replay order and RNG, exploration RNG, and Python/NumPy/Torch RNG after verifying the journal prefix. The final deterministic recovered-source suite passed 15 tests, including an old/current checkpoint restore fixture, equality of the next replay minibatch, and equivalent latest-candidate selection for well-formed checkpoints.

An optional old-source-versus-current restore against two official large checkpoints did not finish: the historical full-history reconstruction was CPU-bound for 20:16.95 and reached 1,804,152 KiB RSS before it was stopped. This run is retained as **INCOMPLETE**, not PASS, and did not write official artifacts. The expensive behavior is explained by the historical path validating the journal and reconstructing every history-bearing transition before retaining the bounded replay tail; the later path hashes the complete chain while rebuilding only the capacity-sized tail. The successful artifact restoration checks and deterministic old/current fixture are the recovery evidence used here.

This forensic assessment removes the initial unverified hypothesis of changed replay sampling, while retaining two limitations for PM judgment: the whole historical CLI bytes remain unavailable, and the 3-seed design has limited statistical precision. The existing campaign results do not require a rerun on the recovered evidence; no new training or evaluation was started. At the time this forensic section was first written, the PM decision had not yet been posted; its pending-disposition wording is superseded by the formal acceptance recorded below. All outcomes remain M2 simulator results, not Atari ALE performance.

To prevent the same source-byte gap in a future authorized run, the training CLI now creates a content-addressed private source bundle before initialization/training and links its archive hash, source aggregate, configuration hash, lock hash, and Git dirty-state identity to the attempt/run/campaign records and artifact manifest. Its verifier checks member hashes and safe paths. The finalized artifact-root guard prevents this future-only code from writing into the completed M5 inventory. The guard is covered by eight focused tests; it was not run against the live campaign and generated no new official artifacts.


## Formal independent PM disposition — 2026-10-30

The independent PM accepted M5-01, M5-02, and M5-05, and accepted M5-03/M5-04 with documented limitations, on the evidence reviewed at PR HEAD `35a99f0eaf14039a94c199e51da370ec2b2e7fec`. BLK-003 was authorized for resolution by PM risk acceptance. RSK-014 remains an accepted residual provenance limitation: source aggregates differ across run groups and complete historical `cli.py` bytes remain unavailable. No claim of strict source homogeneity or byte-identical campaign reproduction is made. The PM did not require or authorize additional training or evaluation.

The acceptance is limited to the completed M2 simulator experiment. The three-seed comparison does not establish Warm-start superiority over Scratch; six evaluation games were truncated at the 400-decision limit; Frozen M4 and SimpleHeuristic were stronger overall on the reported benchmark. These results do not establish performance in Atari ALE VideoChess. Private multi-gigabyte artifact bytes were not independently rehashed remotely by the PM; local read-only verifier records and preserved artifact identities remain the available private-artifact evidence.

At the time of M5 technical acceptance, PR integration and G3 approval were still pending. PR #11 was subsequently merged and G3 approved by the independent PM. M6 remains unauthorized. See [the permanent M5 acceptance record](../../.agents/evidence/M5-PM-acceptance-20261030.md) and [G3 post-merge decision](../../.agents/evidence/G3-final-approval-20261030.md).


## Post-merge governance update — 2026-10-30

PR #11 integrated at merge commit `e0b434530df51b08595e3896c175f81b4a8f8c64`, whose tree matches the reviewed M5 feature tree. The independent PM approved G3 after confirming M2–M5 acceptance. The decision and post-merge verification are in [G3-final-approval-20261030.md](../../.agents/evidence/G3-final-approval-20261030.md). M5 remains M2 simulator evidence only; its source-provenance and three-seed limitations are unchanged. M6 is not authorized or started.
