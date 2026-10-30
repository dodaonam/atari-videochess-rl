# M5 Final Research and Engineering Report

**Status:** Training and frozen simulator evaluation complete; independent PM review remains pending. This report summarizes the evidence currently retained in the private M5 artifact tree and committed evidence records. It does not claim G3 acceptance, Atari performance, or a calibrated rating.

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

### Training source identity and limitation

Run manifests record source SHA `093992c50e893a7fdd92f2f95faafe28d4f1e73c7351a4a8179a3056c4e63b00` for all four seed-20261104/20261105 runs, and `cdcc1fdc0ca0b324e49cfb8b0ff571496a554e9892dfb3620d6454a65ee16da0` for both seed-20261106 runs. The two arms within each seed pair share a source hash. Training timestamps place the seed-20261106 pair after the resumption/recovery work.

Checkpoint-history snapshots before and after that work show exactly three Python paths changed between `cp-08f98f9d-20261029T043013180672Z` and `cp-08f98f9d-20261029T143803674896Z`:

| File | Earlier workspace SHA-256 | Later workspace SHA-256 | Later Git blob |
|---|---|---|---|
| `videochess_rl/rl/checkpoint.py` | `19ab713b5a1450c2e4506d9d761768317e0b48fb96a3cb0083965d6a037bc410` (not found) | `924a95e6accb04c727e2858dbcd6cbda84b970750decc27fd09621bdc61821aa` | `bc1494666d3234c82ff82f2fb8ee851d9558c24b` |
| `videochess_rl/rl/cli.py` | `795ca9865da80bf982480b25d97367c846255e167d9c64320a73030106c2efe3` (not found) | `3f966fffa3a31ed9330004448ca84bc86a4fd6446764d3184e248cff978b60b7` (not found) | unavailable |
| `videochess_rl/rl/replay.py` | `5ae4d3d928c524539bcf6b29f4102f09b246d5703b66539f2fad4aa7e2aaa278` (not found) | `21845b0755809d07d480da821c2e809540a0ca4b8e1eddc5785ebdec5cf59b7f` | `355f8f0868152815debce129cc327d8bcecef970` |

The dated resumption evidence describes streaming full-journal verification, reconstruction of only the bounded replay tail, and newest-first recovery-checkpoint selection; its final recovery test exact-matched model, target, optimizer, replay state, counters, and RNG state. The unchanged configuration, network, target calculator, `training.py`, and `transition.py` hashes further bound the likely scope. **The old `checkpoint.py`, `cli.py`, and `replay.py` bytes were not retained in Git objects, checkpoint-history, local backups, or another source worktree.** Only their old hashes remain. A repository-wide Git object scan found the later checkpoint/replay blobs but not any earlier blobs or either CLI version from the training groups. Therefore no line-by-line diff can be substantiated, and the old `replay.py` sampling implementation cannot be compared directly to the later implementation. A change to replay sampling would affect the learning data distribution; it cannot be ruled out from the available old bytes.

This source-version change is confounded with the third training seed in pooled cross-seed analysis. Warm/Scratch remain source-matched within each seed, but the overall three-seed estimate cannot separate seed-20261106 from a possible code-version effect. No run has been repeated or selectively replaced. **Independent PM disposition is required before treating M5-04 or the pooled training-seed comparison as fully accepted.** Options are to accept the results with this disclosed confound as exploratory, or separately authorize a predeclared supplemental campaign after deciding its scope and budget. This report does not initiate additional training.

### Additional implementation findings and fixes

- The live aggregate-budget check added committed time from completed runs and then added elapsed time since the whole campaign start. On later runs in one invocation this could double-count prior run time in the stop guard. It did not affect the recorded ledger or stop any run; all six runs completed below the caps. The guard now adds only the active run's uncommitted interval to the committed ledger, with a regression test.
- `Transition._identity_document` contained unreachable code after `return`; seed schedules were already validated before calling it. The dead branch was removed, with a regression test confirming non-object schedules still fail validation.
- The M5 CLI's M3/M4 artifact locations now support `VIDEOCHESS_M5_M3_RELEASE_DIR` and `VIDEOCHESS_M5_M4_DIR`; pinned release/checkpoint hashes remain mandatory. Private artifacts remain outside Git. The README documents this clean-checkout limitation.
- The 28 verified M5 evidence logs existed locally and matched recorded commands/results/exit codes; all passed the credential-pattern scan. They were ignored by `*.log`, explaining the clean-clone preflight failure. Exactly those referenced logs were force-added, and preflight now rejects future untracked M5 evidence logs. The audit inventory is `.agents/evidence/M5-remediation-log-inventory-20261030.json`.

The final engineering state remains **incomplete pending source-history disposition** even if local tests, clean-clone checks, and CI pass. G3 and M6 remain outside scope.

## Acceptance assessment

| Criterion | Assessment | Evidence |
|---|---|---|
| M5-01 Double DQN arithmetic and legal semantic next action | PASS | `tests/test_m5_targets.py`, `tests/test_m5_transition.py`, target-disagreement fixtures; see focused/full test logs. |
| M5-02 Reward/player perspective and transition semantics | PASS | transition tests and `docs/03-technical/RL_ALGORITHM.md`; terminal/truncation distinction is represented explicitly. |
| M5-03 Replay, target, exploration, recovery, opponent provenance | INCOMPLETE for provenance closure | Runtime replay/checkpoint evidence and all journal chains verify, but old replay source bytes for the first four runs are unavailable for a line-level semantic comparison with the later two runs. |
| M5-04 Controlled Warm/Scratch/M4/baseline evaluation | INCOMPLETE for pooled cross-seed inference | All six runs and 1,500 games verify, but one source-version change is confounded with the third training-seed cluster; primary terminal comparisons also have censored pairs. PM must disposition the implementation-version limitation. |
| M5-05 No silent curriculum, shaping, or auxiliary objective | PASS | fixed config/protocol, training manifests, and source/test review. |

## Reproduction and evidence identities

Canonical config SHA-256: `84d305084397ad18397dfe395fab58de824fa056729675d0d1cd9ca8bdd06d8d`. Training campaign verification SHA-256: `32098bd4a2df7b2d317c29adcd0d6c258319dd35724eb84575e74135207bd93c`. Evaluation verification SHA-256: `64f4c10450440e17bd8e2758b8edc03196633021a0d652eff7d62368f111d5c8`. Evaluation report SHA-256: `5786aaf4889c748468455ee31ecb2dd3f7185ee084d7b8ce8ced99df58ae6748`. Artifact inventory: `artifacts/m5/artifact-manifest.json`; verify locally with `python scripts/m5_artifact_manifests.py --verify`. Private checkpoints, journals, and raw game rows are not included in a clean Git clone; their manifests and identities are committed as evidence.

To reproduce evaluation analysis in the M5 environment, use the supported M5 evaluation CLI and frozen roster/config under `configs/rl/m5-double-dqn-v1.json`, then run `python scripts/m5_evaluation_sensitivity.py` for the explicitly supplementary sensitivity. Full command lines, software versions, logs, run/attempt IDs, per-policy journals, hashes, and raw rows are in `.agents/evidence/` and the private `artifacts/m5/` inventory. GitHub's context/preflight workflow, when reported, must not be described as the full PyTorch regression suite.

## Limitations and next milestone boundary

Evaluation is simulator-only; M6 must separately integrate the actual Atari ALE observation/control loop and test synchronization between emulator state and chess history. The small training-seed count, two-opponent pool, sparse reward, censored terminal pairs, and limited compute constrain generalization and uncertainty. M5 did not run GPU benchmarking, hyperparameter search, or actual Atari evaluation. The M5 PR is for independent PM review; G3 remains unapproved, M6 has not started, and merge/acceptance are outside this engineering report.
