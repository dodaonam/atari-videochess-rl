# M5 — Paired Double DQN Simulator Experiment

**Protocol:** `m5-ddqn-comparison/2.0` · **Configuration:** `videochess-m5-ddqn-config/2.0` · **Status:** six-run training and the complete frozen 1,500-game simulator evaluation have executed; use the dated M5 final report and verification evidence for observed results. The superseded 1.2 proposal remains in Git history and dated Pre-M5 evidence. This protocol does not approve G3, authorize merging, or start M6.

## Objective and fixed scientific scope

Measure simulator reward learning from an independently implemented PyTorch Double DQN, comparing the accepted M4 representation warm start with an architecture-matched scratch initialization. The M2 `ChessSimulator` and its full `python-chess` history remain the simulator source of truth. The learned policy scores current legal semantic UCI candidates; UCI, not candidate row offsets, identifies actions. Rewards are the fixed agent's terminal `+1/-1/0`, zero on nonterminal transitions, and no shaping. Each decision is one agent move plus at most one opponent reply. A true chess outcome terminates; a valid 400-agent-decision cap truncates and bootstraps from the final legal state. Stockfish is excluded from inference, gameplay, rewards, and Q targets.

Warm-start loads only the verified shared representation from the accepted M4 behavior-only checkpoint (SHA-256 `724ac730f3c5f2d01b48b26eb7670a3c764978a3dd4d6702b3057a99ab1a90a`), excludes the behavior head and optimizer, and initializes a fresh scalar Q head. Scratch uses the same model architecture with an independent representation initializer and the paired Q-head seed. Both target networks copy their fully initialized online network. M4 behavior preferences are not Q-values.

## Paired training design

Training seeds are exactly `20261104`, `20261105`, and `20261106`; each seed has one Warm-start and one Scratch run, for six official runs. Each completed run commits exactly 50,000 valid agent decisions. The total planned budget is 300,000 decisions. A 50/50 opponent mixture is implemented as a deterministic four-episode block: RandomLegal/White, SimpleHeuristic/White, RandomLegal/Black, SimpleHeuristic/Black. The sequence repeats from the zero-based completed-episode index. Both arms receive the same named pair-level RNG seed schedule, but can consume different draws, choose different moves, reach different states, and create different replay. Different initial Q scores can choose different actions; identical realized trajectories are not claimed.

The seed contract remains `videochess-m5-seed-derivation/1.0`, implemented by `videochess_rl.m5_seeding` and pinned by `tests/fixtures/m5_seed_derivation_v1.json`. Run/attempt IDs identify artifacts and are never seed inputs. Episode and opponent seeds are derived from the completed-episode index. Checkpoints restore evolving exploration and replay RNG state.

| Learner parameter | Frozen value |
|---|---:|
| Replay capacity / warm-up | 16,384 / 1,024 valid transitions |
| Batch / update cadence | 32 / 1 update per 4 valid decisions |
| Optimizer / learning rate / weight decay | AdamW / `1e-4` / `1e-4` |
| Loss / gradient clipping | Huber (Smooth L1) / norm `1.0` |
| Discount / target sync | `0.99` / hard copy every 500 completed updates |
| Epsilon | `1.0` to `0.05` linearly over 37,500 decisions, then fixed; evaluation `0.0` |
| Episode cap | 400 valid agent decisions |
| Policy snapshots | 0, 10k, 20k, 30k, 40k, 50k decisions |

No curriculum, reward shaping, auxiliary objective, teacher-derived target, search opponent, or hyperparameter search is part of this baseline. Such work requires a separate named and authorized experiment.

## Entry gate and resource feasibility

The mandatory actual M5 replay feasibility gate passed on 2026-10-28 before official paired training. Final matched attempt 5 used 1029 valid transitions from the M2 simulator (7 completed episodes), sampled genuine seeded replay, completed five batch-32 updates on disposable copies at each of 1/2/4 CPU intra-op threads, and measured checkpoint serialization, process RSS, candidate counts, and complete history lengths. Four intra-op/one inter-op was fastest. Mean policy/simulator decision latency was 0.0356 s (p95 0.0785 s); mean legal candidates were 18.69 (p95 37.0); mean history was 223.5 plies (p95 497.6; maximum 572). Four-thread update mean/p95 was 0.583/0.683 s. A 2,021,375-byte episode-boundary checkpoint serialized in 0.190 s; peak process RSS was 455,667,712 bytes. The accepted M4 checkpoint, its full 19-file artifact manifest, and M3 release output inventory/provenance were verified. Exact report, log, and artifact hashes are in [M5 feasibility evidence](../../.agents/evidence/M5-real-replay-feasibility-20261028.md).

The 50,000-decision run projection upper 95% is 10,453 seconds (2.90 hours) against 28,800 seconds. Six runs plus all profile time already measured and conservatively reserved project to 63,115 seconds (17.53 hours) against the 216,000-second aggregate campaign cap. The artifact planning estimate is 5.61 GB for six runs (checkpoint + replay journal + six snapshots per run), about 2.98 GB below the 8 GiB ceiling; this remains an estimate, not a campaign measurement. These projections retain a small-sample caveat for five update timings. The installed PyTorch build is CPU-only and no authorized Colab runtime was accessible; therefore freeze local CPU with four intra-op and one inter-op thread. No GPU comparison is claimed. The prior Pre-M5 synthetic profile and superseded inter-op-4 profile are historical only. All profile/recovery attempts, including a conservative 180-second reserve for two failed attempts without persisted in-process timers, remain charged to the same campaign ledger.

| Resource ceiling | Limit |
|---|---:|
| Physical training time per run, cumulative across attempts | 8 hours |
| Training campaign, including profile/recovery/retries | 60 hours |
| Local process RSS / Colab process host RSS | 24 GiB / 9 GiB |
| Total M5 artifacts | 8 GiB |
| Paid compute / pay-as-you-go | prohibited |

Use only the owner's existing local/Colab resources. Verify actual runtime RAM/GPU memory and preserve private artifacts. Do not upload raw M3 data or expose ROMs/checkpoints/secrets.

## Initialization, snapshots, and recovery

Produce six pre-RL snapshots at decision 0, one for each arm/seed, with initialization manifests and checksums. Each official run also emits evaluation-only snapshots after decisions 10k, 20k, 30k, 40k, and exactly 50k. On a boundary, finish and validate the simulator step, insert its actual transition, increment the valid decision count, perform any due optimizer update and target sync, then snapshot. Periodic snapshots do not reset a live episode. At 50k, stop before another agent action; if the episode is live, record the incomplete episode boundary without a fabricated terminal flag, truncation, reward, or reset.

Evaluation snapshots use `videochess-ddqn-evaluation-snapshot/2.0` and are non-resumable. Training recovery bundles use `videochess-ddqn-checkpoint/2.0`, are written only at verified completed-episode boundaries, and retain online/target/optimizer state, replay journal prefix and integrity, counters, all RNG states, pair/run/attempt and initialization identity, config/code hashes, and cumulative physical time. Publish atomically to immutable names; verify every file and keep the prior valid recovery point. On interruption, restore only a verified episode checkpoint, keep a unique attempt ID, preserve abandoned work, avoid double-counting logical decisions, and charge all physical attempt time to the same budgets.

## Frozen 1,500-game evaluation

Freeze weights before evaluation. Use epsilon zero, no optimizer, no replay insertion, and the exact seeds 20261130–20261154 inclusive. Each policy gets one game for every `(evaluation_seed, opponent_id, agent_color)` scenario: 25 × 2 opponents × 2 colors = 100 games per policy.

| Policy group | Policies |
|---|---:|
| Accepted frozen M4 behavior-only policy | 1 |
| Warm-start DDQN, pre-RL and post-RL (three training seeds each) | 6 |
| Scratch DDQN, pre-RL and post-RL (three training seeds each) | 6 |
| RandomLegal and SimpleHeuristic fixed baselines | 2 |
| **Total** | **15 policies / 1,500 games** |

Each policy has a 40-minute cap; all evaluation work and retries share a 12-hour aggregate cap. Persist append-only `videochess-m5-evaluation-event/1.0` JSONL journals per policy attempt: fsync scenario-start and terminal/incomplete rows, and persist current decision/history progress at least every five seconds while a game is live. Hash-chain every journal record. On recovery, verify the valid prefix, retain a malformed final tail as an incomplete diagnostic without modifying it, and continue in a new attempt file; completed scenarios are not replayed or double-counted. Preserve each completed row and mark unfinished scenarios/comparisons incomplete. Never replace poor or missing games with another seed. Record actual terminal W/D/L separately from 400-decision truncation and report opponent/color breakdowns, mean score, and decision counts. Require exact snapshot stage identity (`pre_rl` or `post_rl`) for every roster entry. M4 behavior cloning, simulator RL, and later Atari performance are distinct evidence tracks.

Use stable comparison keys: Warm/Scratch `(training_seed, stage, evaluation_seed, opponent_id, agent_color)` and pre/post `(arm, training_seed, evaluation_seed, opponent_id, agent_color)`. Preserve all raw game rows and per-training-seed paired summaries. Use a crossed paired cluster bootstrap over three training-seed clusters and 25 evaluation-seed clusters, retaining scenario rows within their clusters; never treat 1,500 rows as independent. For White-versus-Black performance, pair colors within the same evaluation-seed and opponent cluster, censor unfinished/truncated pairs, and bootstrap the 25 evaluation-seed clusters. The primary terminal-outcome analysis excludes cap-truncated games and marks pair intervals incomplete when terminal pairs are censored. A separate post-hoc sensitivity analysis uses each truncation's actual zero simulator reward in the complete capped-reward paired grid; it is explicitly supplementary and was not used for policy selection. Explicitly state the low precision from only three training-seed clusters. Report M4/baseline comparisons and White/Black/opponent strata. No calibrated Elo is authorized.

## Reporting and reproduction

The report records config hash, source revision/dirty state, library and hardware versions, backend/thread selection, all run/attempt identities, seed schedules and restored RNG states, M4 provenance, six pre-RL and periodic/final snapshot hashes, episode/update/sync counters, runtime/RSS/artifact size, incomplete/failed attempts, full evaluation rows, paired analysis, and exact commands. Reproduce the final inventory with `python scripts/m5_artifact_manifests.py`, then check it with `python scripts/m5_artifact_manifests.py --verify`; the per-attempt manifests and campaign inventory are private local artifacts under `artifacts/m5/`. Use the config and CLI in the M5 branch. Do not describe simulator strength as Atari performance, supervised imitation as RL, an estimate as measured runtime, or incomplete budgets as matched comparisons.

## Recovery incident during the first official attempt

The initial Warm-start attempt for seed `20261104` reached its first completed episode at 215 valid decisions, then failed when PyTorch's restricted checkpoint loader encountered a serialized `TorchVersion` value in environment metadata. The immutable checkpoint sidecar and replay journal were verified after adding a narrowly scoped safe-global allowance for that inert string subclass; restore reproduced all counters, replay rows, network/optimizer state, and RNG state. Attempt `0000` remains a failed, charged artifact. The run resumes as unique attempt `0001` from the verified 215-decision boundary. Configuration SHA remains `84d305084397ad18397dfe395fab58de824fa056729675d0d1cd9ca8bdd06d8d`. The checkpoint was written by source SHA `e2cb7a957b21e43f4b6499a5364c89de4dbf3ce0889f4cffa7307808fa2e8419`; the current recovery-compatible source SHA is `093992c50e893a7fdd92f2f95faafe28d4f1e73c7351a4a8179a3056c4e63b00`. The immutable decision-0 snapshots retain their original SHA/provenance; the only accepted metadata difference is that exact old source SHA, with configuration, seed schedule, every other metadata value, and all model tensors checked unchanged. The code change affects restricted checkpoint loading, exact-source metadata compatibility, and resource accounting only; model, optimizer update, reward, action, RNG, and experiment configuration are unchanged. Restore the verified state with `python scripts/verify_m5_episode_checkpoint.py --training-seed 20261104 --arm warm`. The incident, failure log, checkpoint identity, and cumulative time charge are in [M5 recovery evidence](../../.agents/evidence/M5-training-recovery-20261028.json). This is a recoverable software incident, not a training outcome.
