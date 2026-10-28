# M5 Double DQN Experiment Protocol

**Status:** Proposed, version `m5-ddqn-comparison/1.1`, 2026-10-28. This is a bounded execution proposal, not M5 authorization, G3 approval, implementation, or training evidence. It supersedes the v1.0 proposed checkpoint roster and checkpoint naming where they conflict; the historical proposal and its results remain preserved in Git/evidence. Values are mirrored in `configs/rl/m5-double-dqn-v1.json`; the config hash is part of each run identity.

**Ownership:** Algorithm and recovery semantics belong to [`RL_ALGORITHM.md`](../03-technical/RL_ALGORITHM.md). This protocol owns comparison arms, pairing, frozen evaluation, metrics, and experiment/resource accounting. M5 acceptance IDs remain in [`ACCEPTANCE_CRITERIA.md`](../06-quality/ACCEPTANCE_CRITERIA.md).

## 1. Questions and evidence tracks

The experiment asks (A) whether M4 representation initialization changes Double DQN learning relative to scratch initialization, and (B) how each trained DDQN policy compares with its own pre-RL initialization. Positive, neutral, and negative results are all valid outcomes; no improvement is guaranteed.

Keep the claims separate:

1. Frozen M4 behavior-only imitation is a policy trained on historical PGN move labels, with no RL.
2. Pre-RL versus post-RL compares each DDQN run's initialization snapshot with its own frozen trained policy.
3. Warm-start versus scratch compares paired Double DQN runs under matched protocols and budgets.
4. Every M5 game and metric uses the `python-chess` simulator. It is not Atari evidence.

Stockfish is excluded from M5 policy inference, gameplay, opponents, rewards, and Q targets. M4 behavior scores are not Q values. No teacher scores or additional PGNs are used.

## 2. Policy groups and initialization snapshots

| Group | Policy snapshots | Capture point | Role |
|---|---:|---|---|
| Frozen M4 behavior-only | 1 | Existing accepted immutable checkpoint | Supervised-only baseline; no DDQN updates. |
| Warm-start DDQN before RL | 3 | One per paired training seed, after M4 representation transfer, fresh Q-head initialization and target copy, before any RL gradient update | Initialization snapshot for Comparison B. |
| Warm-start DDQN after RL | 3 | Exact 10,000-valid-decision evaluation snapshot, or mark that seed incomplete if a hard cap prevents it | Trained warm-start policy. |
| Scratch DDQN before RL | 3 | One per paired training seed, after fresh representation/Q-head initialization and target copy, before any RL gradient update | Initialization snapshot for Comparison B. |
| Scratch DDQN after RL | 3 | Exact 10,000-valid-decision evaluation snapshot, or mark that seed incomplete if a hard cap prevents it | Trained scratch policy. |
| `RandomLegalAgent` | 1 | Fixed implementation/configuration | M2 baseline. |
| `SimpleHeuristicAgent` | 1 | Fixed implementation/configuration | Transparent one-ply M2 baseline. |
| **Total** | **15** |  |  |

Initialization artifacts have schema `videochess-ddqn-evaluation-snapshot/1.0`, decision count zero, and a stable identity `(arm, training_seed, stage=pre_rl)`. The target is already copied from the initialized online network. Capture occurs before creating the first RL gradient. Keep them separate from frozen M4, post-RL snapshots, and resumable training checkpoints. The online-policy parameters are used for all policy snapshots; no M4 behavior head becomes a Q head. Policy identity is `(arm, training_seed, stage)`; `training_seed` is explicitly null for frozen M4 and fixed baselines.

## 3. Training arms and controlled conditions

| Arm | Initialization | Learning |
|---|---|---|
| Warm-start Double DQN | Accepted M4 shared representation + newly initialized scalar Q head | M2 simulator transitions/rewards. |
| Scratch Double DQN | Same architecture, independently initialized representation + newly initialized scalar Q head | Same M2 simulator protocol. |

Use paired training seeds `20261104`, `20261105`, `20261106`. Within a seed pair, match the M2 simulator implementation, reward/termination rules, opponent mixture and versions, fixed agent-color schedule, episode-seed derivation, exploration protocol, replay/update protocol, decision and wall-time caps, and all non-initialization configuration. Derive independent named RNG streams for episode seeds, opponent actions, exploration, replay sampling, and model initialization. Use the same paired Q-head initialization seed and same initial seed for matching random streams; warm representation comes from the fixed M4 artifact, while scratch representation uses its separately named seed stream.

**Do not claim that the two independently acting policies receive identical realized transitions or trajectories.** Different initial Q scores can choose different actions, state histories, rewards, opponent responses, and replay contents. The controlled claim is matched protocol/configuration and equal decision/update budget when completed, with initialization source as the intended policy difference. Record and compare each arm's actual transition identities independently. If one arm stops early, preserve its run and mark that seed pair incomplete; do not extend only the other arm.

Configuration remains the bounded CPU proposal in `configs/rl/m5-double-dqn-v1.json`: up to 10,000 valid agent decisions per arm/seed, 45 minutes/run, six hours aggregate training including retries, 2 GiB process RSS, replay capacity 4,096, batch 32, warm-up 512, one update per four valid decisions after warm-up, AdamW `1e-4`, Huber loss, clip norm 1.0, and `gamma=0.99`. Seeds, schedules, run identity, and caps are fixed there. These are proposals to revalidate at M5 entry; they do not authorize training or external compute.

## 4. Frozen evaluation design

The frozen outcome comparison evaluates exactly the **15 policy snapshots in the table above**. Periodic 2,500/5,000/7,500-decision snapshots are retained for learning-curve/recovery provenance but are not part of the 600-game frozen comparison. Each of the 15 evaluated snapshots receives one game for every scenario key `(evaluation_seed, opponent_id, agent_color)`, using evaluation seeds `20261130`–`20261139`, both fixed agent colors, and both versioned M2 opponents (`RandomLegalAgent`, `SimpleHeuristicAgent`). This yields:

- 10 × 2 × 2 = **40 games per policy snapshot**;
- 15 × 40 = **600 planned games** for a complete schedule;
- at most 400 agent decisions per game.

The stable game ID includes protocol/config hash, policy checkpoint ID, evaluation seed, opponent ID/config hash, and agent color. `RandomLegalAgent` baselines are also evaluated against both specified opponents under the same scenario scheme. A policy must be frozen before its evaluation. All pre-RL snapshots, post-RL snapshots, frozen M4, and both fixed baselines are retained and reported; poor results are not grounds for exclusion.

### Pairing and statistical reporting

- Warm versus scratch pairing key: `(training_seed, stage, evaluation_seed, opponent_id, agent_color)`; only the same stage is compared (pre-RL to pre-RL or post-RL to post-RL).
- Before versus after pairing: `(arm, training_seed, evaluation_seed, opponent_id, agent_color)`.
- All snapshots share the same predeclared scenario seeds, opponent configurations, and color schedule. These are matched evaluation conditions, not identical game-state trajectories.
- Report per-game W/D/L, termination reason, truncation separately, decision count, and any policy/simulator error. Aggregate W/D/L by opponent and agent color and retain raw rows.
- Report paired score differences (win=1, draw=0.5, loss=0) for the two comparisons above. Use a crossed paired cluster bootstrap that resamples the three training-seed pairs and the ten evaluation-seed clusters, retaining all four opponent/color scenario rows within each evaluation-seed cluster; an explicitly described paired randomization method with the same dependency structure is also acceptable. Report each training-seed pair's result and raw paired counts. Do not treat the 40 scenario rows as independent when constructing uncertainty. With only three training-seed clusters, emphasize the low precision and present the cross-seed interval as descriptive evidence, not a high-powered population estimate. For fixed M4/baseline policies, cluster by evaluation seed. Wilson intervals may accompany marginal proportions only with a dependence caveat.
- Report all completed, capped, failed, and excluded rows. Do not replace a missing scenario with another seed or selectively drop a seed.
- No held-out evaluation outcome selects a model, seed, checkpoint, or hyperparameter. Do not claim Elo without a separate calibrated pool and approved rating method.

## 5. Evaluation budget and feasibility rule

The existing limits remain unchanged: **20 minutes maximum per policy snapshot** and **three hours aggregate across all evaluation snapshots**. Fifteen individual caps sum to 300 minutes, but the 180-minute aggregate cap controls. A complete 600-game schedule therefore has an aggregate average budget of 18 seconds/game (and no checkpoint may exceed an average of 30 seconds/game). These are arithmetic limits, not measured runtime guarantees.

The Pre-M5 CPU profile found that the 600-game schedule is plausible under these unchanged limits: a same-schedule M4 timing sample projected 240 seconds, and a conservative 400-decision-per-game p95 projection was 4,811 seconds against the 10,800-second aggregate cap. Training feasibility is less certain. In a 32-row synthetic history-range batch capped at the 419-ply maximum observed in the 40-game M4 workload, five measured TD/Huber updates had median 0.999 seconds and p95 1.216 seconds; the estimated 10,000-decision run was 2,571 seconds at the median update and 3,085 seconds at p95, before replay/validation/checkpoint overhead, against a 2,700-second cap. An all-801-ply upper stress projected 9,390 seconds. The exact M5 replay-history and update-time distribution is therefore not established, and the current 45-minute run cap is marginal, not guaranteed. The evidence and commands are in the [Pre-M5 remediation report](../../.agents/evidence/PRE-M5-remediation-20261028.md).

After separate M5 authorization and implementation of the replay boundary, but before starting any paired run, fill the proposed 512-transition replay warm-up and run the configured five-update feasibility probe on a disposable model copy using actual seeded replay samples. Count that work against the aggregate campaign budget. If the measured p95 full-run projection exceeds 45 minutes, stop before the paired campaign and obtain a PM budget or in-scope optimization decision; do not continue one arm selectively or relax a cap.

Before M5, run the bounded workload profile and verify its measurements in the dated [Pre-M5 remediation evidence](../../.agents/evidence/PRE-M5-remediation-20261028.md), using the accepted M4 scorer as a same-architecture inference-cost proxy, representative real M3 feature batches, both variable-history and maximum-history shape stresses, synthetic online/target TD updates, bounded replay-like storage, and a 40-game M4 policy workload sample. Report sample sizes, history/candidate distributions, decision/game timings, update cost, RSS, and uncertainty. Project the schedule from observed timings and the 400-decision cap; a projection is not a guarantee because game lengths and replay history lengths vary. If 600 games cannot plausibly fit both evaluation limits, preserve the 600-game comparison design and ask PM to revise resources or approve a defined alternative before M5. Do not silently raise the three-hour cap, reduce the sample, or begin the campaign with an infeasible plan. If training-update projections approach or exceed the 45-minute run cap, require an authorized, measured warm-up/profile before the full run and mark an early-stopped arm incomplete rather than exceeding the cap.

For the future authorized evaluation, maintain one cumulative timer across all 15 snapshots and retries. Stop starting new games before a per-snapshot or aggregate cap is exceeded. Preserve partial rows and mark any incomplete comparison; missing outcomes are not imputed.

## 6. Counters, snapshots, and run provenance

Evaluation snapshots and resumable training checkpoints are different artifact classes. Follow §8 of [`RL_ALGORITHM.md`](../03-technical/RL_ALGORITHM.md): the configured filenames end in `__eval-snapshot-v1.pt`, `__resume-v1.pt`, and `__incomplete.json` respectively, and their schemas/purposes are not interchangeable. Each 2,500-decision snapshot is captured after valid transition insertion, any due optimizer update, and any due target sync; it is evaluation-valid and non-resumable. A periodic snapshot inside a live episode does not stop or reset that episode. Only the exact 10,000-decision endpoint stops the training run; it preserves the final valid transition and, if the simulator episode is still live, records an incomplete run-end episode without inventing terminal/truncation flags or reward. Full training checkpoints are committed only at completed episode boundaries. If a process interruption is retried before cumulative caps are exhausted, resume only from the last verified episode checkpoint, restore committed counters/RNG, and deterministically replay abandoned logical work; all physical attempt time remains charged. Exhausted caps cause an incomplete stop, never an extension.

For each run, record code/config hashes, source revision/dirty state, software/hardware, M4 SHA or scratch initializer, schemas, seed/stream derivation, opponent identity/config, agent color, episode seeds, every transition and update count, replay/sync schedule, snapshot/checkpoint IDs and hashes, W/D/L raw rows, stop/failure reasons, wall time, and memory. Simulator outcomes remain distinct from ALE evidence. Failed historical runs and retries are retained.

## 7. Stops and interpretation

Hard-stop and preserve the last valid resumable checkpoint on nonfinite values/gradients, invalid or unreconstructable states, repeated illegal actions, opponent/simulator error, checkpoint-integrity failure, or any configured resource cap. An arm that stops before its matched budget is an incomplete comparison; do not claim controlled equal-budget evidence for it.

Behavior-cloning performance, Double DQN learning, simulator outcomes, and Atari performance are separate claims. The frozen M4 policy is not an RL policy. A DDQN pre-RL snapshot is an untrained Q policy; its score is not a post-RL result. A simulator win-rate change is not ALE success. A weak or negative result remains an honest result.

This proposal does not authorize M5, G3, resource allocation, Stockfish gameplay, or ALE integration. M5 remains not started until separately authorized in canonical state.
