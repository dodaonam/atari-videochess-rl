# RL-First Alignment and M5 Feasibility Contract

**Status:** Project-owner RL-first direction is confirmed and applied in current planning as of 2026-10-27. This research note bounds supporting work; it does not itself authorize M5 or start any milestone. M4-001 has separate direct authorization recorded in canonical state.
**Owner:** This document assesses whether supporting data and pretraining lead to the course's principal Double DQN objective. Canonical milestone acceptance remains in [ACCEPTANCE_CRITERIA.md](../06-quality/ACCEPTANCE_CRITERIA.md).
**Related contracts:** [M2 MDP](../03-technical/MDP_SPEC.md), [ADR-0002](../02-management/decisions/ADR-0002-chess-mdp-action-and-perspective.md), [DATASET_SPEC.md](DATASET_SPEC.md), [STOCKFISH_TEACHER.md](STOCKFISH_TEACHER.md), [EXPERIMENT_PROTOCOL.md](EXPERIMENT_PROTOCOL.md), and [M03 plan](../../.agents/plans/M03-expert-dataset.md).

**Current status update (2026-10-28):** M4 is implemented, accepted, and integrated; its frozen behavior-only checkpoint is a verified input to the M5 warm-start comparison. Older statements below that M5 core work can precede M4 describe the earlier schedule proposal, not the current M5 comparison contract. The operative algorithm, comparison, and budget are in [RL_ALGORITHM.md](../03-technical/RL_ALGORITHM.md), [M5_EXPERIMENT_PROTOCOL.md](M5_EXPERIMENT_PROTOCOL.md), and the [M05 plan](../../.agents/plans/M05-double-dqn.md). M5 remains not started and requires separate direct authorization; G3 remains unapproved. O-01 is closed internally; this does not establish instructor approval.

## 1. Research objective and verdict

Double DQN trained from simulator transitions remains the central academic algorithm. The required result is evidence that an independently implemented RL learner improves through interaction with the M2 simulator and reward, with its Bellman update, legal-action behavior, reward perspective, terminal/truncation handling, replay, target network, exploration, and checkpoints independently tested.

The M3/M4 direction is compatible with that objective, but the previous framing gave PGN/Stockfish work too much independent weight: M4 behavior cloning was first, teacher labels could expand without a measured RL benefit, and the plan did not sufficiently constrain time spent before Double DQN. This creates a material scope-drift risk. Corrective direction: keep M3 small and evidence-driven; use behavior cloning only as a baseline/warm-start experiment; limit real Stockfish analysis to the bounded subset required by M3-02 if permitted; start the M5 core implementation and sanity experiment as soon as the authorized M3 path and M2 interfaces permit. M4 does not block DDQN implementation or its first sanity run. The current M5-04 acceptance still requires a pretraining-only checkpoint for the final paired comparison, so keep that baseline small or formally revise acceptance before claiming M5 complete if it is omitted. Do not expand dataset scale or label coverage for its own sake.

The M3 data schema supplies precise game/position/history identities and compact replay references without a larger corpus or exhaustive engine scores. ADR-0003 and MODEL_DESIGN.md now accept the M4/M5 model interface; its implementation, parameter count, and performance remain unmeasured. M5 training hyperparameters and experiment refinements remain proposals until separately implemented and measured.

## 2. Pretraining options

| Option | RL/course alignment | Initialization compatibility | Cost and principal risk | Disposition |
|---|---|---|---|---|
| **A. Engine-guided action-value/scoring pretraining** | Potentially useful as a warm-start experiment, but the primary target is still teacher analysis rather than environment return. | An action-conditioned scorer can share parameter shapes with a candidate Q-network. Teacher scores/ranks are not Bellman-consistent discounted returns; copied values must not be called Q-values. | Highest CPU/labeling cost, especially if every legal candidate is searched. Sparse-reward RL remains unsolved. | Do not use as the default pretraining task. A capped side experiment requires a measured reason and separate authorization under O-07. |
| **B. Behavior cloning** | A clear supervised baseline; useful for measuring retained demonstration ability, but not RL. | Policy logits express relative action preference, not return. A shared encoder may transfer; do not treat policy logits as initialized Q-values. Compare a fresh/reinitialized Q head and a random-init DDQN control. | Low label cost; can overfit games/openings and consume time without improving reward learning. | Use only as a small behavior-only baseline if it fits the schedule. |
| **C. No pretraining** | Strongest clean test that the independent Double DQN learns from simulator rewards. | No transfer assumption. | Sparse terminal rewards, long episodes, and large branching can make learning slow; positive result is not guaranteed. | Keep as the RL control wherever compute permits; the core RL implementation must work without supervised weights. |
| **D. RL-first hybrid** | Allows one behavior baseline while reserving the principal budget for environment interaction and RL ablation. | Under accepted ADR-0003, transfer only the specified compatible representation components and reinitialize the M5 Q output head. Treat transfer benefit as a hypothesis, not a semantic identity. | Moderate complexity, controllable by hard limits; still risks overemphasizing pretraining if not time-boxed. | **Recommended.** Build the tiny baseline without making it a prerequisite to starting DDQN; then complete the required paired comparison and controlled RL experiment. |

### Minimum useful supervised preparation

For Double DQN itself, no supervised training is technically required. The minimum data contract remains source-valid standard PGN game/position rows, stable UCI candidates, source/result perspective, history reconstruction reference, deterministic split, and a small capped Stockfish sidecar needed to satisfy the current M3-02 acceptance criterion after permission. The current M5-04 acceptance additionally requires a small pretraining-only checkpoint for its paired comparison; use played-move behavior cloning over legal candidates as the lowest-cost baseline if that criterion remains unchanged. It must not label played moves as optimal, and its training can follow the start of DDQN implementation/sanity work.

Do not add exhaustive legal-move teacher scoring, outcome auxiliary losses, rating-based data balancing, a large tactical puzzle corpus, or a broad PGN collection before M5 demonstrates a specific need. Stockfish analysis required by M3-02 is not a commitment to train on those labels. If the assignment prohibits it, keep M3-02 pending and request a formal acceptance-scope change; do not silently skip it.

## 3. M5 Double DQN implementation requirements

These are future requirements, not implementation work in this Pre-M3 mission. M2's fixed-agent-color, agent-perspective reward and agent-move/opponent-reply transition remain authoritative.

### Bellman update and legal action choice

For a sampled transition, select the next action with the **online** network over only legal UCI actions and evaluate that same action with the **target** network:

```text
a* = argmax over a in legal_moves(next_state) of Q_online(next_state, a)
y  = reward_agent + gamma * bootstrap_mask * Q_target(next_state, a*)
```

Online action selection and target evaluation must use distinct parameter sets. A hand-computed test must use values where online and target argmax disagree, proving the implementation uses online argmax and target evaluation of that action. Empty next legal actions are valid only for terminal states. No temporary legal-list index is persisted as an action identity; store UCI and recompute the mask/candidate set from the authoritative simulator state.

### Replay transition contract

Every replay row retains: serialized observation/reference and observation-schema version; current legal UCI set; selected UCI action; scalar reward from the fixed episode-agent perspective; next observation/reference and legal UCI set where available; `terminated`; `truncated`; stop/terminal reason; agent color; initial state or reconstruction identity; episode/decision index; opponent policy name/version/config hash; seed; and environment/simulator code revision. Store separate flags rather than one `done` bit.

M2 returns reward for one agent decision plus at most one opponent reply. Replay boundaries must match that contract. The opponent identity is part of the transition distribution and every run manifest. Use the Board/history replay path or another tested sufficient representation for repetition and clock-sensitive rules; FEN alone is insufficient. If the selected model view omits relevant history, document and measure the resulting partial observability.

### Terminal, truncation, reward, and perspective

- `terminated=true` for a chess outcome under M2 automatic-outcome semantics: no bootstrap.
- `truncated=true` for an external runner/safety cap while the game remains live: retain the valid final observation and bootstrap only if the experiment defines the cap as an external time limit and the final state/legal actions are valid.
- If a finite decision horizon is part of the task objective, include remaining horizon in state or define the horizon as terminal and test that contract. Never silently turn truncation into a chess draw.
- Keep rewards from the episode agent's perspective for both colors. Checkmate win/loss is the M2 terminal reward; automatic draw is 0. Teacher scores, game results, policy logits, and simulator returns remain separately typed.

### Replay, target network, exploration, and checkpoints

Use experience replay and an independently parameterized target network. The config must state replay capacity, warm-up size, batch size, target synchronization method and interval, optimizer/update ratio, discount, exploration policy and schedule, epsilon floor, legal-action sampling, reward semantics, per-episode cap, and stop budgets. A first exploration policy can be epsilon-greedy over legal moves; decay against environment decisions/transitions and record the exact counter. Do not silently change opponent/color sampling during a run.

Checkpoint online and target weights, optimizer, replay contents or a verifiably reproducible replay journal, counters, scheduler/exploration state, all RNG states, environment/opponent configuration, source revision, config hash, and current seed/episode. Preserve the behavior-only/pretraining-only checkpoint and the post-RL checkpoint as separate immutable artifacts.

### Budget controls and learning evidence

Before M5, predeclare hard maximums for episodes, agent decisions/transitions, wall time, memory, artifact bytes, and seeds. Measure a tiny simulator throughput pilot first; no workload is authorized here. Stop at a hard limit, corrupted replay/checkpoint identity, persistent non-finite targets/weights, invalid legal actions, or transition/perspective inconsistency. Do not use supervised accuracy alone as a reason to extend training, and do not stop early on a noisy single-seed win rate without a predeclared rule.

Retain per-seed learning curves for completed-game returns/W-D-L, terminal and truncation counts, episode lengths, win/draw/loss by color, legal-action failures, TD loss/target scale, Q-value ranges, replay occupancy, epsilon, gradient/update counts, and wall/resource use. Include small-sample sanity checks that overfit a tiny supervised subset and hand-verify TD targets; these validate code, not strength.

## 4. Comparisons and evidence that RL contributed

Use the same opponent policies/configurations, initial-position/opening rules, colors, decision caps, and seed list for any paired checkpoint comparison. Record per-seed results and uncertainty; separate complete-game W/D/L from truncation, interruption, and policy failure.

Priority under constrained time/compute:

1. **Required core:** random-legal and transparent heuristic simulator baselines; independently tested Double DQN target/action/mask/reward/terminal logic; one bounded learning run with multiple recorded seeds if feasible; retain and compare its pre-RL and post-RL checkpoints under identical conditions.
2. **High-value comparison:** behavior-cloned/pretraining-only checkpoint versus post-RL checkpoint, plus random-init Double DQN where feasible. This distinguishes imitation retention from reward-driven change.
3. **One meaningful RL ablation:** Double DQN versus a controlled DQN target-selection baseline (same architecture, data, seeds, exploration, opponent, and budget), or one isolated component change such as target-network update cadence. Do not combine changes.
4. **After core evidence:** broader opponent pool/color/opening coverage and more seeds, followed by ALE transfer work under M6 authorization.

Call the result genuine RL learning only when the agent has consumed recorded simulator transitions/rewards and its post-RL behavior/returns improve over its own pre-RL checkpoint under comparable evaluation conditions, with per-seed results and uncertainty shown. If it retains supervised move accuracy but simulator return does not improve, report that as imitation retention without demonstrated RL improvement. If it regresses, report the regression. A behavior-cloning score, teacher ranking, simulator benchmark alone, or ALE metric cannot substitute for the others.

## 5. Transfer to ALE and remaining feasibility risks

The simulator gives exact chess state and legal moves; ALE supplies pixels, control actions, actual opponent responses, reward, terminal flags, and runtime behavior. Standard-chess data does not establish pixel extraction, Atari move execution, ROM parity, or transfer performance. M6 must retain ALE RGB and actual step responses as source of truth and report simulator and Atari evidence separately.

**Readiness answer:** the owner-selected direction retains Double DQN as the principal project result; the corrected design can support it if source/teacher work remains hard-bounded and M5 core work starts after the authorized M3 path and M2 interfaces permit. The prior design had material scope-drift risk because M3 labeling and M4 behavior prediction were foregrounded without an equally concrete RL budget. Sparse terminal reward, remaining schedule questions (O-03), and compute/storage limits (O-04) can still affect M5. O-01 is closed for internal execution by the 2026-10-27 owner decision; no instructor approval is claimed, and only an actual authoritative prohibition discovered later would constrain the affected activity. Keep M4 bounded, preserve Double DQN correctness tests and core learning, and keep the M5-04 baseline/comparison or formally revise that criterion before claiming M5 complete.

## 6. Decisions and deferred scope

The original [ROADMAP.md](../01-foundation/ROADMAP.md) remains verbatim. This RL-first staging is a project-owner-approved prioritization refinement, not a rewrite of the roadmap. ADR-0003 and MODEL_DESIGN.md now fix the M4/M5 state/action interface; this does not freeze M5 training hyperparameters, reward changes, curriculum, or experimental refinements. Those remain proposals until implemented and measured.

M4 owns model shape and a behavior-only checkpoint. M5 owns Double DQN implementation/training and RL ablations. M6 owns actual ALE integration and its separate performance evidence. M7 owns integrated evaluation/reporting. No model, trainer, data pipeline, or experiment was implemented or run for this Pre-M3 contract.
