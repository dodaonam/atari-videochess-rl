# M05 — Double DQN and Simulator Learning Plan

**plan_id:** `M05-double-dqn`. **Milestone:** M5. **Plan status:** owner-authorized campaign executed; M5-001 is blocked by BLK-003 pending source-version disposition. **Plan revision:** `m05-execution/2.0`, updated 2026-10-28; post-review status is in canonical project state. **Source requirements:** `docs/01-foundation/REQUIREMENTS.md` §§1, 3–7 and M5-01 through M5-05 in `docs/06-quality/ACCEPTANCE_CRITERIA.md`. **Relevant decisions:** ADR-0001, ADR-0002, ADR-0003. **Task:** M5-001. The authorization record remains valid for M5 scope, but does not resolve BLK-003, approve G3, or permit PR merge/self-approval by its author.

## 1. Objective and boundary

Implement and evaluate an independently written PyTorch Double DQN against the M2 standard-chess simulator. Compare a correctly transferred M4 representation with an architecture-matched random initialization under equal simulator transition/update budgets. Preserve M4 behavior cloning as a separate frozen baseline. Produce reproducible simulator evidence that honestly reports improvement, neutral result, or regression. M5 does not implement ALE integration (M6), does not claim Atari performance, and does not authorize itself.

Out of scope: Stable-Baselines/Ray RLlib; Stockfish in inference, opponent play, or rewards; additional datasets/teacher labels; reward shaping/curriculum/auxiliary losses in the baseline; M6; G3 approval; external/paid compute; and public release of local data/model artifacts.

## 2. Authorization and prerequisites

Before any implementation, re-read `AGENTS.md`, `REQUIREMENTS.md`, live state/backlog, acceptance criteria, ADR-0001 through ADR-0003, M2/M4 acceptance, this plan, and the current user request. Verify `engineering.next_milestone == M5`, the canonical active milestone/task are M5/M5-001 with in-progress status, the accepted M2, M3, and M4 tasks remain complete, blockers are absent, and the direct M5 authorization is present in the canonical authorization record. **The direct owner authorization is recorded in canonical state and this plan; readiness, CI, or M4 completion alone did not authorize M5.** Do not infer G3 approval. Apply only the gates and approvals required by current canonical governance; never make a gate that includes M5 acceptance a circular prerequisite for implementing M5.

Create an isolated branch from the latest reviewed `initial-idea` integration commit. Preserve existing worktrees and external artifact locations. The verified integration baseline for this execution is `08f98f9dfc58fbf54e29afabb009020b787f2718` (PR #10 merged).

## 3. Fixed contracts and verified inputs

### M2 transition contract

`ChessSimulator` and `python-chess.Board` own simulator rules. One `step()` is one legal agent move plus at most one legal opponent reply. The same agent color acts at every decision; for Black, the opponent's White opening move occurs in reset and is included in history. Rewards are fixed agent-perspective terminal `+1/-1/0` and zero otherwise. Automatic chess outcomes terminate; `max_agent_decisions` is a time-limit truncation. A valid nonterminal truncation bootstraps from its final observation. Interrupted/invalid transitions are discarded, never synthesized as a draw or terminal. Standard-start roots only for input schema v1; FEN is not complete history. M5 supplies a pair-derived `episode_seed` and separate `opponent_rng_seed` to `ChessSimulator.reset`; the optional `opponent_seed` argument preserves old single-seed behavior for all existing callers. See [`MDP_SPEC.md`](../../docs/03-technical/MDP_SPEC.md) and [`RL_ALGORITHM.md`](../../docs/03-technical/RL_ALGORITHM.md).

### Paired seed and run identities

Use only `videochess-m5-seed-derivation/1.0`, implemented by `videochess_rl.m5_seeding` with known-answer vectors in `tests/fixtures/m5_seed_derivation_v1.json`. The stable pair ID is SHA-256 over the canonical experiment ID and training seed, with `master_seed == training_seed`. Named stream seeds use the exact big-endian/length-prefixed SHA-256 encoding and disjoint domain-code ranges in [`RL_ALGORITHM.md`](../../docs/03-technical/RL_ALGORITHM.md#61-versioned-paired-seed-derivation). A unique `run_id` includes pair ID, arm, and a monotonically increasing zero-based attempt index (never reused) for provenance/artifact naming and is excluded from every pair-level seed calculation. A retry references its resume parent but restores the verified pair/checkpoint state and cumulative budgets. Episode/opponent seeds use zero-based `completed_episodes`; exploration/replay states are restored from the arm's episode checkpoint. Warm/scratch share paired episode, opponent, exploration, replay, and Q-head initial seeds, while only scratch uses the scratch-representation initialization domain; the warm representation is the accepted M4 transfer. A shared seed schedule does not assert identical RNG consumption or realized trajectories.

### M4 transfer artifact

Expected accepted local checkpoint:

```text
/home/dodaonam/Projects/atari-videochess-rl-m4/artifacts/m4/m4-behavior-20261027-r4/pretrained-behavior-only.pt
SHA-256 724ac730f3c5f2d01b48b26eb7670a3c764978a3dd4d6702b3057a99ab1a90a4
model videochess-behavior-scorer/1.0
input videochess-model-input/1.0
parameters 121897 (historical verified measurement)
```

It is outside Git. Verify the manifest, sidecar, checkpoint, schemas, and dataset provenance immediately before loading. If unavailable, do not fabricate it or mark real transfer acceptance passed. Transfer only representation state through `initialize_q_head`; reinitialize the scalar Q head; initialize target from the post-transfer online net; retain an independent scratch arm. Do not transfer M4 optimizer state or treat its behavior output as Q. The M3 release identity is `f10a679deddf06f3e1e3c39cf58db4e21176629c26c09034a271bf278189e890`; reverify its manifest/split before any training or loader use. Both artifacts remain local-only and outside Git.

## 4. Planned implementation areas

The exact module layout may follow current repository conventions, but responsibilities remain separate:

1. `videochess_rl/rl/transition.py`: immutable validated `videochess-ddqn-transition/1.0` record, replay from complete standard-start history, terminal/truncation and reward checks.
2. `videochess_rl/rl/replay.py`: bounded seeded replay buffer or verifiable journal keyed by semantic UCI; serialization, insertion/sampling, provenance, and corruption rejection.
3. `videochess_rl/rl/network.py`: a narrow M5 Q-scoring wrapper around the ADR-0003 representation; no M4 behavior head reuse.
4. `videochess_rl/rl/targets.py`: legal online selection plus target evaluation of the identical UCI action; finite targets and explicit bootstrap masks.
5. `videochess_rl/rl/training.py`: epsilon-greedy legal selection, replay update, Huber loss, clipping, target sync, counters, validation/evaluation separation, resource stop behavior.
6. `videochess_rl/rl/checkpoint.py`: versioned `videochess-ddqn-checkpoint/2.0` atomic/recoverable run bundle and completed-episode resume. Preserve previous-good checkpoints.
7. `videochess_rl/rl/evaluate.py`, `videochess_rl/rl/evaluation_journal.py`, and CLI: frozen policy evaluation, exact stage identity, append-only hash-chained per-scenario persistence/recovery, paired statistics including color contrasts, and structured incomplete attempts; `scripts/m5_artifact_manifests.py` publishes and verifies immutable per-attempt run manifests and the private campaign artifact inventory.
8. Focused `tests/test_m5_*.py` modules plus existing M2/M3/M4 regressions.

Keep these components small enough for a student to explain. Reuse the accepted M4 feature encoder, scorer, legal UCI contract, and safe artifact patterns where compatible; do not duplicate the feature schema or create a second Board rules state.

## 5. M5 sequence (one continuous authorized execution)

1. **Entry audit:** verify authorization, branch baseline, M2/M3/M4 state, exact local artifact hashes and protected worktrees; record M5-001/M5 as `in_progress` when implementation begins; the canonical transition and direct authorization are now recorded.
2. **Contract/transition tests:** reconstruct observations; check fixed color, Black reset, opponent reply boundary, reward sign, automatic terminal outcomes, valid time-limit bootstrap, and invalid-transition rejection.
3. **Algorithm and seed tests:** implement a hand-computed Double DQN fixture in which online and target rank candidates differently; select online argmax by UCI and evaluate that identical UCI using target. Cover masks, empty terminals, ties, finite values and reward/discount arithmetic. Verify the seed contract known-answer vectors, arm-pair parity, run-ID exclusion, domain separation, episode indexing, and restart derivation before implementing the paired runner.
4. **Replay/update infrastructure:** seeded insertion/sampling, identity, opponent/run context, gradients, target sync, epsilon schedule, counters and checkpoint/resume.
5. **Transfer tests:** use the verified M4 artifact, copy only shared layers, freshly seed Q head, sync target, and compare with same-shape scratch initialization. Verify source artifact unchanged and no Stockfish dependency.
6. **Deterministic sanity:** small synthetic transition fixtures with hand-verified targets and finite updates; do not confuse this with a performance result.
7. **Paired runs:** execute versioned warm-start and scratch configs with the exact paired budgets/seeds/opponents; preserve initialization and periodic/final checkpoints. Respect cumulative limits across retries.
8. **Frozen evaluation:** after the predeclared training schedule and checkpoint freeze, run equal-condition evaluation against RandomLegal and SimpleHeuristic, both colors and paired seeds. Keep M4, pre/post RL, warm/scratch, and simulator/ALE claims separate.
9. **Acceptance/review:** pass all M5-01 through M5-05 criteria; run focused/full suite, archive/preflight, clean-clone exact PR-head tests, and CI. Correct defects and rerun. The first official Warm-start attempt (seed 20261104) failed at its first checkpoint after 215 decisions due to PyTorch `TorchVersion` metadata under weights-only loading; its checkpoint and replay journal were subsequently verified and restored, and attempt 0001 will resume from that exact episode boundary. See [recovery evidence](../evidence/M5-training-recovery-20261028.json).
10. **PR handoff:** open one reviewable M5 PR against `initial-idea`. Engineering executor does not merge or approve own work; follow [PR review workflow](../../docs/02-management/PR_REVIEW_AND_INTEGRATION.md). PM independently reviews and decides; authorized operator alone performs any merge.

## 6. Authorized experiment and resource envelope

Use [`M5_EXPERIMENT_PROTOCOL.md`](../../docs/04-research/M5_EXPERIMENT_PROTOCOL.md) and config schema `videochess-m5-ddqn-config/2.0` in [`m5-double-dqn-v1.json`](../../configs/rl/m5-double-dqn-v1.json). The fixed training schedule is three paired seeds × Warm-start/Scratch × 50,000 valid decisions = six runs and 300,000 decisions. Per-run cumulative wall cap is eight hours; the profile, retries, and all runs share 60 hours. Replay is 16,384/1,024 capacity/warm-up, batch 32, one update per four valid decisions, AdamW `1e-4`/`1e-4`, Huber, clipping 1.0, gamma 0.99, and hard target copy every 500 optimizer updates. Epsilon is 1.0→0.05 over 37,500 decisions. RAM caps are 24 GiB local and 9 GiB Colab host; all M5 artifacts share an 8 GiB ceiling. Official snapshots are 0/10k/20k/30k/40k/50k.

The fixed evaluation is 15 policies and 1,500 games: 25 evaluation seeds × two approved M2 opponents × both colors per policy. Per-policy cap is 40 minutes and campaign cap is 12 hours. Final matched real-replay profile attempt 5 passed before official runs: 1,029 actual M2 transitions, five batch-32 updates for each of 1/2/4 CPU threads, and measured checkpoint/RSS costs. Four intra-op/one-inter-op local CPU was frozen. The 50k/run upper-95 projection is 10,453 s (2.90 h); all six runs plus measured and conservatively reserved profile time project to 63,115 s (17.53 h), within 8 h/run and 60 h aggregate. The artifact planning estimate is 5.61 GB for six runs against the 8 GiB ceiling. No Colab/T4 runtime was accessible; no GPU comparison is claimed. See [M5 profile evidence](../evidence/M5-real-replay-feasibility-20261028.md).

Local CPU and accessible Colab CPU/T4 resources are authorized with no paid compute and at most one concurrent T4. If a Colab/T4 becomes actually available before official runs, only one session at a time is permitted; backend changes during the paired campaign require compatibility/recovery evidence and a comparison impact assessment. Every failed or incomplete attempt remains visible; all measured and conservatively reserved failed-profile time counts across retries. These caps are ceilings, not a requirement to consume the entire allowance.
## 7. M5 checkpoint/resume contract

Follow §§8.1–8.2 of [`RL_ALGORITHM.md`](../../docs/03-technical/RL_ALGORITHM.md). The non-resumable `videochess-ddqn-evaluation-snapshot/2.0` captures initialization at decision 0, periodic policies at 10,000, 20,000, 30,000 and 40,000, and the final policy at exactly 50,000 valid decisions after that step's replay insertion, scheduled gradient update, and target sync. The full `videochess-ddqn-checkpoint/2.0` training state is saved only at completed episode boundaries and retains online/target, optimizer/scheduler, replay or verified journal, counters, epsilon schedule, all RNG states, experiment/pair/run identities, seed derivation schema, committed episode index, color/opponent config, schemas, init artifact identity, config/code hashes, provenance, and file hashes. Resume restores the last verified episode checkpoint and per-arm evolving RNG states, then derives the next episode/opponent seeds from the unchanged pair ID and restored completed-episode count; the run ID never seeds a stream. If a decision/time/resource stop occurs mid-episode, preserve an incomplete episode/attempt record and last valid transition; do not fabricate flags or outcomes. Resume restores the last verified episode checkpoint, replays abandoned logical work, and counts all physical attempt time toward cumulative caps. Do not claim exact mid-episode resume.

Use `python scripts/verify_m5_episode_checkpoint.py --training-seed <seed> --arm <warm|scratch>` to validate a recovery point before resuming. After training and evaluation have finished, create and verify the immutable manifests with `python scripts/m5_artifact_manifests.py` and `python scripts/m5_artifact_manifests.py --verify`. The script refuses to call the campaign complete unless all six 50,000-decision runs and all 15 × 100 evaluation schedules are present. `artifacts/m5/` is private local output and remains outside Git; commit the reports and manifest procedures, not checkpoints or game/replay datasets.

## 8. Verification matrix and acceptance

The detailed test list is [`M5_TEST_MATRIX.md`](../../docs/06-quality/M5_TEST_MATRIX.md). The implementation now includes focused learner tests, and the retained hand-calculated fixture is checked by the live target calculator; these tests do not pass campaign acceptance by themselves.

| Criterion | Required outcome |
|---|---|
| M5-01 | Online legal argmax, target evaluation by identical UCI, terminal and truncation targets, finite numerical behavior independently tested. |
| M5-02 | Fixed agent-perspective reward and opponent-reply transition boundary verified; teacher score is not used as Q/reward. |
| M5-03 | Replay, seeded exploration, target network, opponent identity, checkpoint integrity, completed-episode resume verified. |
| M5-04 | Frozen M4-only, warm DDQN, scratch DDQN, RandomLegal and SimpleHeuristic comparisons use paired equal conditions; report positive, neutral or negative results honestly. |
| M5-05 | Any curriculum, shaping or auxiliary loss is a separate named/configured experiment and not mixed with baseline. |

Never mark M5 criteria passed from a plan, synthetic-only fixture, preflight, or CI workflow that does not run the tests. G3 is separately governed and this plan does not approve it. M6/ALE acceptance remains later work.

## 9. Failure, recovery and stop conditions

Reject invalid histories, stale/illegal actions, empty bootstrap action sets, candidate-set mismatch between online/target, inconsistent terminal flags, nonfinite values/gradients, invalid opponent results, corrupt artifacts, or wrong dataset/checkpoint identities. Preserve last verified checkpoint and diagnostics. Do not coerce invalid states to zero reward/draw/terminal. Re-run only within the cumulative budget. An external artifact unavailable, explicit course restriction, infeasible hard cap, unavailable authorization, or repository protection requiring an external review is a truthful blocker; preserve in-scope verified work.

Do not reset usage counters by creating a new run ID. Do not use test outcomes for selection. If one paired arm fails or is capped early, preserve it and mark that comparison incomplete. Keep all data and model files outside Git; do not commit secrets or bulk source material.

## 10. Handoff and dependencies

M5 depends on accepted M2 simulator contracts, M3 dataset identity only when that dataset is explicitly needed for warm-start provenance, and M4 behavior representation/checkpoint. The M5 learner is a fresh RL objective with separate optimizer/replay/targets. The M4 logits are never reused as Q targets. Current state is governed by `PROJECT_STATE.yaml`; the owner authorized M5-001 and its six-run campaign, which has executed. M5-001 is now blocked by BLK-003 pending source-version disposition; G3 remains unapproved.

The owner-authorized 2026-10-29 resumption followed the prior four-run pause; all four earlier runs and artifacts remain preserved. Both seed `20261106` arms completed exactly 50,000 decisions; all six runs total 300,000 decisions. The prior incomplete Scratch restore check passed exact online/target/optimizer/replay/counter/RNG comparisons, and the final replay chain was verified through 50,000. The frozen evaluation completed all 1,500 schedules with six valid 400-decision truncations. See the training/evaluation verification records and `docs/04-research/M5_FINAL_REPORT.md`. Post-review, 28 ignored evidence logs were verified and force-added; the clean-clone preflight failure was reproduced at prior PR HEAD `575dce5`; artifact manifests and campaign chains pass read-only verification. The evaluation source identity reconstructs exactly. However, four runs use source SHA `093992…` and the seed-20261106 pair uses `cdcc1f…`; checkpoint history names changed files `checkpoint.py`, `cli.py`, and `replay.py`, whose earlier/source-group content is not fully recoverable. Because the old replay implementation cannot be compared, source semantics and pooled cross-seed equivalence are not established. This is tracked as RSK-014; no run has been repeated. The timer double-count guard, transition unreachable-code cleanup, M5 log-tracking check, and private input path overrides have focused regression coverage. Continue full regression, checkpoint/preflight, clean-clone exact-head verification, and final-head GitHub CI. M5-03/M5-04 remain incomplete for source-provenance disposition until independent PM review. G3 remains unapproved, M6 has not started, and the PR must remain open/unmerged.
