# M05 — Double DQN and Simulator Learning Plan

**plan_id:** `M05-double-dqn`. **Milestone:** M5. **Plan status:** ready for independent PM review as a plan. **Plan revision:** `m05-execution/1.1`, prepared 2026-10-28. **Source requirements:** `docs/01-foundation/REQUIREMENTS.md` §§1, 3–7 and M5-01 through M5-05 in `docs/06-quality/ACCEPTANCE_CRITERIA.md`. **Relevant decisions:** ADR-0001, ADR-0002, ADR-0003. **Task:** M5-001. M5 is not authorized, not active, and no M5 learner/training is implemented here. This plan does not approve G3 or permit PR merge by its author.

## 1. Objective and boundary

Implement and evaluate an independently written PyTorch Double DQN against the M2 standard-chess simulator. Compare a correctly transferred M4 representation with an architecture-matched random initialization under equal simulator transition/update budgets. Preserve M4 behavior cloning as a separate frozen baseline. Produce reproducible simulator evidence that honestly reports improvement, neutral result, or regression. M5 does not implement ALE integration (M6), does not claim Atari performance, and does not authorize itself.

Out of scope: Stable-Baselines/Ray RLlib; Stockfish in inference, opponent play, or rewards; additional datasets/teacher labels; reward shaping/curriculum/auxiliary losses in the baseline; M6; G3 approval; external/paid compute; and public release of local data/model artifacts.

## 2. Authorization and prerequisites

Before any implementation, re-read `AGENTS.md`, `REQUIREMENTS.md`, live state/backlog, acceptance criteria, ADR-0001 through ADR-0003, M2/M4 acceptance, this plan, and the current user request. Verify that `engineering.next_milestone == M5`, no active task/milestone exists, the accepted M2, M3, and M4 tasks remain complete, blockers are absent, and any separate direct M5 authorization is present in the canonical authorization record. **This plan, PR readiness, passing CI, M4 completion, or this Pre-M5 mission does not authorize M5.** Do not infer G3 approval. Apply only the gates and approvals required by current canonical governance; never make a gate that includes M5 acceptance a circular prerequisite for implementing M5.

Create an isolated branch from the latest reviewed `initial-idea` integration commit. Preserve existing worktrees and external artifact locations. The last baseline verified for this plan was `906178775d48e98e64c709673bfe73177dd15c02`; use a newer legitimate integration SHA if present and review all intervening changes.

## 3. Fixed contracts and verified inputs

### M2 transition contract

`ChessSimulator` and `python-chess.Board` own simulator rules. One `step()` is one legal agent move plus at most one legal opponent reply. The same agent color acts at every decision; for Black, the opponent's White opening move occurs in reset and is included in history. Rewards are fixed agent-perspective terminal `+1/-1/0` and zero otherwise. Automatic chess outcomes terminate; `max_agent_decisions` is a time-limit truncation. A valid nonterminal truncation bootstraps from its final observation. Interrupted/invalid transitions are discarded, never synthesized as a draw or terminal. Standard-start roots only for input schema v1; FEN is not complete history. See [`MDP_SPEC.md`](../../docs/03-technical/MDP_SPEC.md) and [`RL_ALGORITHM.md`](../../docs/03-technical/RL_ALGORITHM.md).

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
6. `videochess_rl/rl/checkpoint.py`: versioned `videochess-ddqn-checkpoint/1.0` atomic/recoverable run bundle and completed-episode resume. Preserve previous-good checkpoints.
7. `videochess_rl/rl/evaluate.py` and CLI: immutable run config, policy evaluation, pairing/statistics, run manifests, and structured failures.
8. Focused `tests/test_m5_*.py` modules plus existing M2/M3/M4 regressions.

Keep these components small enough for a student to explain. Reuse the accepted M4 feature encoder, scorer, legal UCI contract, and safe artifact patterns where compatible; do not duplicate the feature schema or create a second Board rules state.

## 5. M5 sequence (one continuous authorized execution)

1. **Entry audit:** verify authorization, branch baseline, M2/M3/M4 state, exact local artifact hashes and protected worktrees; set M5-001/M5 `in_progress` only when code implementation actually begins.
2. **Contract/transition tests:** reconstruct observations; check fixed color, Black reset, opponent reply boundary, reward sign, automatic terminal outcomes, valid time-limit bootstrap, and invalid-transition rejection.
3. **Algorithm tests:** implement a hand-computed Double DQN fixture in which online and target rank candidates differently; select online argmax by UCI and evaluate that identical UCI using target. Cover masks, empty terminals, ties, finite values and reward/discount arithmetic.
4. **Replay/update infrastructure:** seeded insertion/sampling, identity, opponent/run context, gradients, target sync, epsilon schedule, counters and checkpoint/resume.
5. **Transfer tests:** use the verified M4 artifact, copy only shared layers, freshly seed Q head, sync target, and compare with same-shape scratch initialization. Verify source artifact unchanged and no Stockfish dependency.
6. **Deterministic sanity:** small synthetic transition fixtures with hand-verified targets and finite updates; do not confuse this with a performance result.
7. **Paired runs:** execute versioned warm-start and scratch configs with the exact paired budgets/seeds/opponents; preserve initialization and periodic/final checkpoints. Respect cumulative limits across retries.
8. **Frozen evaluation:** after the predeclared training schedule and checkpoint freeze, run equal-condition evaluation against RandomLegal and SimpleHeuristic, both colors and paired seeds. Keep M4, pre/post RL, warm/scratch, and simulator/ALE claims separate.
9. **Acceptance/review:** pass all M5-01 through M5-05 criteria; run focused/full suite, archive/preflight, clean-clone exact PR-head tests, and CI. Correct defects and rerun.
10. **PR handoff:** open one reviewable M5 PR against `initial-idea`. Engineering executor does not merge or approve own work; follow [PR review workflow](../../docs/02-management/PR_REVIEW_AND_INTEGRATION.md). PM independently reviews and decides; authorized operator alone performs any merge.

## 6. Experiment proposal and resource envelope

Use [`M5_EXPERIMENT_PROTOCOL.md`](../../docs/04-research/M5_EXPERIMENT_PROTOCOL.md) and [`m5-double-dqn-v1.json`](../../configs/rl/m5-double-dqn-v1.json). The current CPU-first proposal has three paired seeds and two DDQN arms, 10,000 valid decisions/arm/seed or 45 minutes/run, six-hour aggregate training cap, 2 GiB RSS, replay 4,096, batch 32, warm-up 512, and one gradient update per four valid decisions. It preserves three pre-RL plus three post-RL snapshots for each DDQN arm, one frozen M4 policy, and two fixed baselines: 15 policy snapshots and 600 planned evaluation games. Evaluation remains capped at 20 minutes per snapshot and three hours aggregate. The previous nine-snapshot/360-game schedule is superseded; see the dated PM remediation addendum. All are proposals, not M5 authorization or performance claims. Recompute feasibility at M5 entry. Do not allocate Colab, GPU, paid compute, cloud storage, or expand caps without separate direct authorization.

The initial 32-transition profile was exploratory only. The PM remediation adds a bounded representative profile using a real M3 feature batch of 32, an 801-ply synthetic history-shape stress (including the Black agent's opening ply), an evenly spread variable-history batch, online/target forward passes, legal masks, synthetic Double DQN targets and Huber backward/updates, a bounded replay-like store, and a 40-game frozen M4 timing workload. The new run identity, measurements, cap arithmetic, uncertainty, and schedule feasibility are in the [dated Pre-M5 remediation evidence](../evidence/PRE-M5-remediation-20261028.md). Estimates are not guarantees; if the 600-game schedule cannot fit both evaluation caps, preserve the design and obtain PM direction before M5 rather than silently reducing games or increasing time.

## 7. M5 checkpoint/resume contract

Follow §§8.1–8.2 of [`RL_ALGORITHM.md`](../../docs/03-technical/RL_ALGORITHM.md). The non-resumable `videochess-ddqn-evaluation-snapshot/1.0` captures initialization at decision 0, periodic policies at 2,500-decision boundaries, and the final policy at exactly 10,000 valid decisions after that step's replay insertion, scheduled gradient update, and target sync. The full `videochess-ddqn-checkpoint/1.0` training state is saved only at completed episode boundaries and retains online/target, optimizer/scheduler, replay or verified journal, counters, epsilon schedule, all RNGs, run/seed/color/opponent config, schemas, init artifact identity, config/code hashes, provenance, and file hashes. If a decision/time/resource stop occurs mid-episode, preserve an incomplete episode/attempt record and last valid transition; do not fabricate flags or outcomes. Resume restores the last verified episode checkpoint, replays abandoned logical work, and counts all physical attempt time toward cumulative caps. Do not claim exact mid-episode resume.

## 8. Verification matrix and acceptance

The detailed test list is [`M5_TEST_MATRIX.md`](../../docs/06-quality/M5_TEST_MATRIX.md). M5 must add executable tests for the actual learner; the Pre-M5 hand-calculated fixture is only a test vector and does not pass M5 algorithm criteria.

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

M5 depends on accepted M2 simulator contracts, M3 dataset identity only when that dataset is explicitly needed for warm-start provenance, and M4 behavior representation/checkpoint. The M5 learner is a fresh RL objective with separate optimizer/replay/targets. The M4 logits are never reused as Q targets. Current state is governed by `PROJECT_STATE.yaml`; M5-001 remains pending, active milestone/task null, `start_authorized: false`, and G3 unapproved until a future direct authorization and canonical transition.

The eventual M5 closeout may update `M5-001` and canonical milestone state to complete only after all five M5 acceptance criteria have current verified evidence and final state/backlog checks pass. Engineering completion, PM acceptance, repository integration, G3 approval, and M6 authorization remain separate statuses. The M5 PR must include exact code/config revisions, commands/exits/timestamps, test logs, both-arm manifests, initialization/final checkpoint identities, transfer evidence, all per-seed outcomes, simulator-only limitations, resource accounting, clean-clone verification, CI scope, and explicit next gate/task state. Await independent PM review and an external authorized operator decision for merge.
