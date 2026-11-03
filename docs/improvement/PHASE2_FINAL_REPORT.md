# Phase 2 Final Report

## Executive verdict

**Engineering execution is complete and ready for independent PM review.** The authorized single warm-start Double DQN run reached 250,000 valid decisions with seed `20261103`; the snapshots and replay journal passed integrity checks; all fixed simulator evaluations and the bounded actual-ALE evaluation ran; and the repository-contained live demo was smoke-tested with both the selected Q checkpoint and M4-A.

Consolidation PR [#24](https://github.com/dodaonam/atari-videochess-rl/pull/24) is open, non-draft, targets `main`, and remains unmerged. Its repository-preflight check was queued at creation.

The simulator results do not show an improvement over M4-A in the reserved sample. The selected Q model did not produce an Atari terminal result in the bounded paired attempts: each of its three attempts stopped on an RGB target-confirmation uncertainty after nine verified player moves and replies. M4-A completed 12 verified turns in each of its three capped attempts, which also did not reach a game terminal. These are separate findings from engineering readiness.

## Campaign identity and preserved history

- Experiment: `videochess-improvement-20261103-v1`
- Repository branch: `feature/videochess-performance-improvement-20261103`
- Base: `main` at `7415d821acf11dd3e07e4990c2f5539cfdf31916`
- Phase 1 accepted head: `5a983d9ae8b945b78b84e5f6decd2c92dd49d61e`
- Phase 2 pushed head/tree before PR creation: `5b9f93f3092a8e9b97c4061813bbd150bdd1b837` / `03346066361e7a14a3396bee2bea00282604a2c9`
- Official training source revision/tree: `76c898ed0dd8a2e8bf0c76cbd8565f83077284e0` / `b5877036a2e954c085e0da386c0bcb596ff21ab3`
- Training code digest: `cf329438880a82b7b39b05b8f1f3bc1af21e262edb4143e1035e494f891a5705`
- Training configuration digest: `2cfe2805edd3e05756fd3ef981a6e4441e3b4ad717649d5647085228e837aabd`

The campaign remains independently attributed. Historical M0–M7 reports and their limitations have not been edited to imply new evidence. No third-party dataset, ROM, checkpoint, replay, RGB frame, or raw game trace is included in Git.

## M4 foundation

Phase 1 inputs were verified and reused without rebuilding them:

- Dataset release: `f2b3b52724958ffa845894681013cdc40915da179bbec3ae011087fe8a8ce0cc`
- 5,000 normalized games; 4,000/500/500 game-group train/validation/test split.
- 94,805 retained position observations: 76,606 train, 8,965 validation, 9,234 test.
- Eight Optuna Gaussian-process trials selected learning rate `0.00015` and weight decay `0.00005`.
- Offline Stockfish 19 labels: 4,000 training positions and 128 separate development labels at a fixed 50,000-node limit.
- Selected model: M4-A at `artifacts/improvement/videochess-improvement-20261103-v1/m4-a/epoch-22.pt`, SHA-256 `cf5e437ff4e2d6a8e85739df751dec33f16b7bc4c92268f996ec4c612d62feed`.

M4-A had validation NLL 2.208634, top-1 34.40%, top-3 60.70%, and the predetermined 20-game simulator development score 0.875. Its reserved-test NLL was 2.202227, top-1 34.08%, and top-3 60.45%. The original historical M4 test top-1 was about 29.90%. These are human-move prediction measures, not winning probabilities. M4-A remained the selected checkpoint because it led the fixed development simulator rule; the 20-game comparison is small and does not establish general superiority.

## Official Double DQN training

The one official run used a fresh Q head over the shared M4 representation, seed `20261103`, AdamW, Huber loss, gamma 0.99, replay 16,384/warmup 1,024, batch 32, one gradient update per four decisions, target synchronization every 500 optimizer updates, epsilon 1.0 to 0.05 over 175,000 decisions, and the frozen decaying M4 exploration schedule. The M4 model was frozen. Q snapshots and all final evaluation used greedy legal Q inference only.

| Measure | Observed |
|---|---:|
| Valid decisions / transitions | 250,000 / 250,000 |
| Optimizer updates | 62,245 |
| Target synchronizations | 124 |
| Completed episodes | 3,203 |
| Wall time | 23,417.4 s (6 h 30 m 17 s) |
| Effective throughput | 38,433 decisions/hour |
| Frozen cumulative-time guard | 36,000 s (10 h); used 23,417.4 s |
| Peak process RSS | 1,100,021,760 bytes |
| Minimum sampled available RAM | 22,513,188,864 bytes |
| Minimum sampled free disk | 32,687,590,400 bytes |
| Action sources | 19,353 M4-guided; 76,194 uniform exploration; 154,453 Q-greedy |

The final decision limit ended in the middle of an episode. The last episode-boundary resumable checkpoint is `resume-249174.pt` (SHA-256 `64b09505cb68a36e34c4f08f26eeaaa259c32ee981bee08e5912766c91b3be27`). The final 826 journal transitions are beyond that checkpoint prefix, but they are present in the verified journal and represented in the final 250,000-decision Q snapshot. No recovery attempt was needed; no transition tail was replayed or discarded as damaged. Wall, RSS, free-RAM, and free-disk guards all remained within their frozen bounds. This checkpoint/snapshot distinction is recorded in the run evidence.

All eleven scheduled Q-only snapshots from 0 through 250,000 were created, sidecar-verified, loaded, and checked for finite parameters. The 250,000 snapshot SHA-256 is `48dbbb860c8f997105b7bd30863892294e68ef489185ac6172fb7b459df5c293`.

## Simulator development selection

Before inspecting candidate scores, the committed protocol fixed 20 matched development games per available snapshot (five in each opponent/color stratum), then extended the top three candidates to 60 matched games apiece. Opponents were RandomLegal and SimpleHeuristic; both colors were evaluated; the same scenarios were used for candidates within each stage; Q snapshots used greedy Q-only action selection. Truncations and incomplete games stayed in the scheduled denominator and were not counted as draws.

The selection rule was maximum scheduled-game score `(wins + 0.5 × true draws) / scheduled games`, then fewer incomplete games, higher SimpleHeuristic score, and earlier snapshot. The selected snapshot was the 250,000-decision Q checkpoint:

| Training decisions | Games | Wins | Losses | True draws | Incomplete | Score |
|---:|---:|---:|---:|---:|---:|---:|
| 250,000 | 60 | 49 | 0 | 11 | 0 | 0.9083 |

The 225,000 and 175,000 finalists scored 0.8833 (46/0/14) and 0.7917 (35/0/25). These are small simulator samples against the project's simple opponents and do not establish Atari strength or statistical superiority.

## Reserved simulator evaluation

Checkpoint selection was frozen before these seeds were run. The protocol used 40 matched games per policy across both opponents and colors. Results below are Python `ChessSimulator` outcomes, not Atari outcomes.

| Policy | Scheduled | Wins | Losses | True draws | Truncations | Incomplete | Score |
|---|---:|---:|---:|---:|---:|---:|---:|
| Selected Double DQN, 250k | 40 | 30 | 0 | 10 | 0 | 0 | 0.8750 |
| M4-A behavior cloning | 40 | 31 | 0 | 9 | 0 | 0 | 0.8875 |
| Historical M5 warm policy | 40 | 3 | 4 | 32 | 1 | 0 | 0.4750 |

The chosen Q snapshot did not outperform M4-A in this reserved sample. The M4-A and Double DQN samples are small and neither is a robust estimate of general strength. The historical M5 comparison is context only; it is from a different training campaign and evaluation protocol.

## Actual Atari evaluation

The bounded evaluation used `ALE/VideoChess-v5`, RGB observations, mode 4, frameskip 1, repeat-action probability 0, ROM SHA-256 `d44f2a115393b0a6cbcd5398d62369e652f3670a9ee585883d183e740edad0f7`, ALE-Py 0.11.2, and Gymnasium 1.4.0. Paired reset seeds were 20261210, 20261211, and 20261212. The current verified Atari runner controls White only; the embedded Atari opponent cannot be forced to replay identical moves after policies diverge.

| Policy | Attempts | Verified player moves | Verified opponent replies | Terminal W/L/D | Bounded/control outcomes |
|---|---:|---:|---:|---:|---|
| Selected Double DQN | 3 | 27 | 27 | 0 / 0 / 0 | 3 target-confirmation control uncertainties after 9 turns each |
| M4-A | 3 | 36 | 36 | 0 / 0 / 0 | 3 runner move-cap stops after 12 turns each |

The Double DQN's repeated target-confirmation uncertainty is an Atari input/control limitation observed after otherwise RGB-verified moves. The M4-A attempts stopped at the 12-player-move budget. No attempt reached an Atari terminal state, so no Atari win rate is reported. An initial evaluation harness reused an RGB adapter across ALE resets and was rejected as stale; its raw results were preserved, the harness was corrected to create a fresh adapter per episode, and the corrected six-attempt run above is the reported evaluation.

## Live demonstration

The repository-contained Tk demo was exercised live in ALE with both model families. Each bounded smoke showed two RGB-verified player turns and two verified Atari replies, displayed the move list, resized to 900×560, stepped backward and forward through captured verified states with the left/right keys, saved a local trace, and exited cleanly. The GUI labels policy family, checkpoint hash, and decision count. It distinguishes selected-but-pending actions from RGB-verified moves and does not invent opponent moves.

M4-A is the better-supported instructor demonstration fallback because the Q policy's formal Atari attempts reached the repeated input-confirmation issue and the reserved simulator score was slightly below M4-A. The Q demo remains selectable and clearly labeled; it must not be described as an Atari win or as using M4 guidance.

See [PHASE2_DEMO_GUIDE.md](PHASE2_DEMO_GUIDE.md) for exact launch commands and private prerequisites.

## Engineering, privacy, and scientific limitations

- Full replay-chain and semantic audit passed for 250,000 transitions; action-source events aligned one-to-one with unique transition identities and sequential decision indexes.
- The initial full repository suite ran on revision `17804732a4bd8a11a5e63b17bbc18d8bad242c77`: 550 tests, 545 passed, four private-artifact tests skipped, and one environment failure because Stockfish was not on `PATH`. Review remediation found the existing Phase 1 Stockfish 19 binary in the virtual environment and reran the readiness test and full suite successfully; see the remediation verification ledger for exact totals and hashes.
- The final training configuration and training code digest match the frozen official-start record. Post-training changes added evaluation/demo/reporting only.
- Simulator metrics evaluate the Python simulator; Atari metrics evaluate actual ALE. They are not interchangeable.
- There was one training seed and no scratch comparison. No multi-seed inference is justified.
- The private Lichess archive's redistribution license remains unestablished. Dataset, labels, models, replay, ROM, RGB frames, and raw traces remain local and ignored by Git.
- The exact academic submission deadline was not supplied to the Phase 2 executor. The run itself used 6.50 hours, under the explicit 10-hour cumulative guard. Deadline feasibility beyond the completed work is therefore not represented as a guaranteed margin.
- The single official training run, all bounded evaluations, tests, docs, and an open unmerged PR constitute the completion boundary. No later training or HPO campaign was run.

The original Atari aggregate was found to contain 63 individual opponent UCI
moves. The sanitized current evidence contains aggregate counts, outcomes and
private-trace SHA-256 values only; the detailed traces remain under the ignored
`artifacts/improvement/videochess-improvement-20261103-v1/` namespace. The
intermediate branch commit that first contained the sequence remains reachable
in the PR history. Integration must account for that history as documented in
[`PM24_REMEDIATION.md`](PM24_REMEDIATION.md).

The post-campaign PM review also found that development selection ranked
20-game stage-one candidates alongside 60-game finalists. The evaluator now
restricts final selection to the three extended finalists. The previously
selected 250,000-decision snapshot was one of those finalists and remains the
winner. No training or simulator evaluation was repeated.
