# M5 Double DQN Experiment Protocol

**Status:** Proposed, version `m5-ddqn-comparison/1.0`, 2026-10-28. This is an execution-ready proposal, not M5 authorization, G3 approval, implementation, or training evidence. All values are in `configs/rl/m5-double-dqn-v1.json`; a changed config hash creates a new protocol/run identity.

**Ownership:** The algorithm semantics belong to [`RL_ALGORITHM.md`](../03-technical/RL_ALGORITHM.md). This document owns controlled comparisons, run/evaluation identity, metrics, and resource accounting. M5 acceptance IDs remain in [`ACCEPTANCE_CRITERIA.md`](../06-quality/ACCEPTANCE_CRITERIA.md).

## 1. Questions and evidence tracks

Primary question: under the same simulator interaction and update budget, does initializing the action-conditioned Double DQN representation from M4 behavior cloning change learning relative to random initialization? Report improvement, no improvement, and regression equally. This experiment does not guarantee a positive result.

Keep four claims separate:

1. M4 behavior-only imitation: frozen policy and historical PGN labels; no RL.
2. Before/after RL: each DDQN arm's pre-RL snapshot versus its own post-training checkpoint.
3. Warm-start versus scratch: paired Double DQN runs with matched seeds, transitions, replay, update schedule, opponents, colors, and evaluation.
4. Simulator versus ALE: all M5 results are `python-chess` simulator results. No M5 metric is an Atari result.

Stockfish is not used for inference, gameplay, rewards, opponents, or Q targets. M4 logits and probabilities are behavior preferences, not Q-values; teacher scores are not used to initialize Q values. No additional PGNs or teacher labels are acquired.

## 2. Comparison arms

| Arm | Initialization | Learning | Purpose |
|---|---|---|---|
| A — frozen M4 behavior | Exact verified M4 checkpoint | None; deterministic legal argmax | Pretraining-only reference. |
| B — warm Double DQN | Verified shared M4 representation plus fresh seeded Q head; target copied from resulting online network | Simulator rewards and transitions | RL after supervised representation initialization. |
| C — scratch Double DQN | Same model shape, entirely fresh representation and Q head; target copied from online | Same simulator rewards and transitions as B | Controlled initialization comparator. |
| D — `RandomLegalAgent` | No learned model | None | M2 baseline. |
| E — `SimpleHeuristicAgent` | No learned model | None | Transparent one-ply M2 baseline. |

Preserve B/C pre-RL initialization checkpoints separately from their trained checkpoints. B and C must use the same run config except for initialization source and paired seed. The Q head is freshly initialized in both arms. Neither B nor C receives M4 optimizer state. A, D, and E never enter replay training.

## 3. Training configuration and paired design

Versioned proposal: `configs/rl/m5-double-dqn-v1.json`.

- Three paired seeds: `20261104`, `20261105`, `20261106`.
- Fixed 10,000 valid agent-decision transitions per arm/seed, or the 45-minute per-run hard cap, whichever comes first. Both arms of each seed have equal stopping budgets. Any capped shortfall is recorded and makes that seed's controlled pair incomplete; do not fill one arm's budget with extra work.
- Episode reset samples both agent colors evenly under paired episode seeds; agent color stays fixed during an episode. Each step remains one agent move plus at most one opponent reply.
- Training opponent mixture is fixed 50:50 `RandomLegalAgent` / `SimpleHeuristicAgent`; opponent identity/config is stored per transition. Pair assignment and RNG streams are fixed by the config.
- Replay capacity 4,096 validated transitions; warm-up 512; minibatch 32; one optimizer update every four valid agent decisions; target hard copy every 500 gradient updates; AdamW `1e-4`, weight decay `1e-4`, Huber loss, clip norm `1.0`; `gamma=0.99`.
- Epsilon decreases linearly from `1.0` to `0.05` over 7,500 agent decisions, then remains `0.05`. Evaluation epsilon is always `0`.
- CPU is the baseline device; one PyTorch intra-op and one inter-op thread. No Colab, paid compute, or external storage is part of this proposal.
- Profile-gated start: before the full run, measure the authorized short deterministic learning smoke fixture and estimate whether both paired arms can fit the remaining run caps. Do not scale budgets to consume all available resources.

Expected gradient updates per complete run are approximately 2,372 after the 512-transition warm-up; the realized count is authoritative. Episode caps, decision counts, update counts, and elapsed time are all recorded independently.

## 4. Evaluation and checkpoint selection

Use only fixed-schedule checkpoints. The primary result is the model at exactly 10,000 valid decisions. Do not select epochs/steps/seeds by held-out game outcomes. Preserve checkpoints at 2,500-decision boundaries and the final boundary; they are for recovery and learning curves, not selective reporting.

Frozen evaluation conditions:

- `RandomLegalAgent` and `SimpleHeuristicAgent`, exact code versions/configs.
- Seeds `20261130`–`20261139`, both agent colors for each opponent and seed: 40 games per checkpoint.
- Standard initial board only; no opening book or custom positions.
- Maximum 400 agent decisions/game. Record a cap as truncation separately from terminal W/D/L.
- Same paired game IDs and conditions for A–E and each trained B/C seed where the policy permits; preserve opponent RNG seeds. No training/evaluation RNG sharing.
- 40-game frozen test schedule occurs once after each final checkpoint is frozen. Interim development checks, if necessary, use different explicitly named seeds and cannot replace the frozen results.

Report per-game outcomes, terminations/truncations, decision counts, colors, seed, opponent, policy errors, latency, and wall time. Summarize W/D/L by opponent and color. Provide paired differences for B versus C and each post-RL policy versus its own initialization. Include raw counts and Wilson 95% intervals for proportions; note that games sharing seed/opponent are paired and not independent. Do not report Elo without a separate calibrated pool and approved rating protocol.

For the RL diagnostics report valid and invalid transitions, replay distribution, reward/outcome counts, episode length, epsilon trajectory, update count, target synchronization, mean/max absolute TD error, loss, finite-value failures, checkpoint selection, run stop reason, and resource use. Report all failed, capped, or excluded runs. Do not delete an unfavorable seed.

## 5. Budget and hard stops

Proposed caps are deliberately independent of M4's budget:

- Three seeds × two DDQN arms; 10,000 valid agent decisions/run, 45 minutes/run.
- Six-hour aggregate CPU wall cap for the M5 paired training campaign, including failed/restarted runs; counters do not reset across new run IDs.
- 2 GiB maximum process RSS, 4,096 replay transitions, batch size 32, and 1 GiB per-run artifact directory cap.
- One 40-game frozen evaluation per checkpoint/seed, 20-minute aggregate cap per evaluation schedule; report any unfinished games honestly.
- No paid/GPU/Colab allocation, external upload, or new persistent storage. A future mission must authorize those separately.

Hard-stop on nonfinite outputs/targets/gradients, corrupt or incompatible state, repeated illegal transition, state/history mismatch, opponent failure, checkpoint integrity failure, resource cap, or accumulated campaign budget exhaustion. Preserve the last verified completed-episode checkpoint and failure diagnostics. Do not silently alter the paired budgets, hyperparameters, opponent mix, or acceptance criteria. If feasibility profiling predicts the comparison cannot fit, reduce neither arm selectively; report the constrained design before M5 authorization.

## 6. Reproducibility and limitations

Each paired run gets a unique run ID and canonical JSON config hash. Record source SHA/dirty status; M4 checkpoint SHA or scratch initialization seed; input/transition/model schemas; Python/PyTorch/python-chess versions; CPU/OS; all RNG states; exact opponent configs; per-episode seeds/colors; transition and update counts; checkpoint hashes; times/memory; metric code revision; exclusions; and stop reasons. Keep large model/replay artifacts outside Git in approved local storage and commit only sanitized, portable metadata/evidence.

M4 weights and the M3 release are local artifacts outside Git. Verify exact hashes before future use; do not regenerate/copy/upload/re-distribute either artifact. This proposal's CPU feasibility is uncertain until the measured Pre-M5 report is considered. A small simulator benchmark and synthetic gradient do not demonstrate that 60,000 transitions or learning will complete in these caps. M5 is not started by this protocol; a separate direct authorization and applicable prerequisite check are required.
