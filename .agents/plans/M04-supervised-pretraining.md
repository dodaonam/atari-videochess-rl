# M04 — Supervised Pretraining Plan

- **Plan ID:** M04
- **Milestone:** M4 — supervised pretraining, within the sequence owned by `docs/02-management/EXECUTION_PLAN.md`
- **Plan status:** `ready`
- **Review/authorization note:** Ready for owner review; the owner recorded a direct conditional M4-001 authorization in `.agents/evidence/M4-001-authorization-conditional-20261023.md`. It is not operational until every listed entry condition is verified and owner decisions are recorded.
- **Canonical task:** `M4-001` in `BACKLOG.yaml`, pending because the conditional authorization's entry conditions are unmet.
- **Dependency:** `M3-001` complete; accepted M3 release identity and split contracts are recorded in `.agents/evidence/M3-acceptance-20261021.md` and `.agents/evidence/M3-final-closure-record-20261021.json`.
- **Plan and protocol:** [MODEL_DESIGN.md](../../docs/03-technical/MODEL_DESIGN.md), [TRAINING_PROTOCOL.md](../../docs/04-research/TRAINING_PROTOCOL.md), and proposed [ADR-0003](../../docs/02-management/decisions/ADR-0003-pretraining-model-interface.md).
- **Acceptance:** `M4-01` through `M4-04` in `docs/06-quality/ACCEPTANCE_CRITERIA.md`.
- **Readiness evidence:** `.agents/evidence/PRE-M4-readiness-20261022.md` (mission-local `R01`–`R08`; these are not formal acceptance criteria).

This plan does not start M4, authorize training, approve G3, or start M5. Its proposed design keeps behavior cloning a small support experiment for the project's Double DQN objective. M5 core work must not wait for M4, consistent with `EXECUTION_PLAN.md` and the current M5 acceptance contracts.

## 1. Objective and scope

Implement and evaluate a bounded supervised behavior-cloning baseline using only the `played_move_uci` labels in the accepted M3 training split. Preserve validation and test partitions, save a pretraining-only checkpoint, and verify that the model chooses only among the simulator's semantic legal moves.

In scope only after the recorded conditional authorization is operational:

1. Implement the versioned model input/action contract and the proposed shared board/history/candidate scorer.
2. Verify model shape, finite logits, gradients, deterministic legal-action masking, and checkpoint round-trip (`M4-01`).
3. Demonstrate a fixed 128-example overfit sanity check before full training (`M4-02`).
4. Train the behavior baseline on the M3 train partition, select using validation only, preserve the test set for one final report, and keep Stockfish absent from inference (`M4-03`, `M4-04`).
5. Store model/run artifacts outside Git with a manifest that identifies source revision, configuration, seeds, data release and split IDs, dependency versions, metrics, and checkpoint hashes.

Out of scope: new data acquisition or generation, expanded Stockfish labeling or evaluation, model-based ALE work, ROM activity, cloud/GPU allocation, M5 Double DQN implementation/training, and any milestone or gate approval.

## 2. Entry conditions

Before changing the task to `in_progress`, verify and record activation of the owner's direct conditional authorization in `.agents/evidence/M4-001-authorization-conditional-20261023.md` and the required canonical state/backlog fields. This conditional instruction does not become operational merely because the plan or M3 dependency is ready. G3 remains unapproved; do not add `requires_user_gate_approval: G3`, because G3 covers M4 and would create a circular start prerequisite under the existing governance model.

The executor must also:

- Confirm M3-001 still has status `done`, M4 is still `next_milestone`, `active_milestone` is `null`, and G3 remains unapproved.
- Obtain or locate the exact accepted local release `f10a679deddf06f3e1e3c39cf58db4e21176629c26c09034a271bf278189e890`; this checkout does not contain `artifacts/m3`. Verify its nine release files against the accepted manifest before training. If unavailable, stop and ask the owner to provide the retained artifact or authorize a permitted recovery path. Do not silently rebuild from the license-uncertain package.
- Reconfirm that the exact local/internal use boundary remains acceptable. The third-party curated package license is unstated; no bulk source or derived data may be uploaded or redistributed.
- Resolve the applicable assignment/instructor rule for behavior cloning and custom PyTorch training under O-01 before any M4 run; this mission's design work does not close that question.
- Use local CPU for the initial run. Any Colab/GPU, cloud storage, paid compute, new dataset use, or expanded teacher role requires separate authorization.
- Checkpoint-history migration is implemented on `feature/rsk010-lossless-checkpoint-history` and documented in [`CHECKPOINT_HISTORY.md`](../../docs/05-operations/CHECKPOINT_HISTORY.md), but remains unmerged. Before M4 starts, the owner must review/merge that migration PR and a clean clone of the resulting integration commit must pass archive verification and preflight. Until then, `initial-idea` retains the legacy state-size limit; do not start checkpoint-heavy M4 work there. After integration, preserve the full archive and review durable-storage policy before its lossless growth approaches 64 MiB. The 4 MiB state guard remains a final refusal boundary, not history storage.

## 3. Data and state/action contracts

- Use exactly the final M3 release identity above, train/validation/test counts of 15,196/2,015/2,057, and the recorded split assignment. No re-splitting or cross-split merging.
- For behavior cloning, each example is one nonterminal M3 position and its single recorded `played_move_uci`. The target must appear exactly once in the position's legal UCI candidate set.
- Do not feed the PGN result, player ratings/names, game outcome, future moves, Stockfish scores, teacher ranks, or split labels to the model. The limited 128-position teacher sidecar is excluded from this behavior-only run unless separately authorized for a distinct experiment.
- M2 and M3 keep their own FEN serializers. At the model boundary use legal-en-passant canonical FEN semantics; preserve the halfmove clock, castling rights, side to move, and the full move history separately.
- Candidate identities are UCI strings. Sort legal candidates lexically by UCI for reproducibility, but never treat an array offset as a persistent action ID. Promotions, castling, captures, and en passant remain distinct legal moves.
- Use side-to-move-oriented board planes and action coordinates. The trained scorer returns one uncalibrated behavior logit for each supplied legal candidate.
- M3 and normal M2 episodes start from standard chess. If a future M5 integration uses a nonstandard initial board, it must provide and test the root position in the model input contract before inference.

## 4. Task decomposition and deliverables

| Work item | Deliverable | M4 acceptance mapping |
|---|---|---|
| M4-A: implement inputs and model | Versioned feature encoder, legal-candidate scorer, unit tests for shape, masking, finite outputs and gradients. | M4-01 |
| M4-B: verify the training path | One-time release verification, one-pass per-game replay/tensorization, fixed small-sample overfit record. | M4-01, M4-02 |
| M4-C: bounded behavior run | Config, deterministic seeds, epoch/validation metrics, early-stop record and model-only checkpoint. | M4-02, M4-04 |
| M4-D: held-out evaluation | Frozen checkpoint, one test report, side/move-type strata, latency/size/throughput measurements, inference-without-Stockfish check. | M4-03, M4-04 |
| M4-E: handoff | Checksums, run manifest, limitations, exact commands and updated task/state evidence; M4 task complete only after all rows pass. | M4-01–M4-04 |

Acceptance IDs are owned only by `ACCEPTANCE_CRITERIA.md`. Mission readiness IDs `R01`–`R08` remain in the Pre-M4 evidence document.

## 5. Training, evaluation, and resource limits

Use the proposed protocol in `docs/04-research/TRAINING_PROTOCOL.md`. Initial settings are starting values, not optimized findings: AdamW, learning rate `3e-4`, weight decay `1e-4`, batch size 64 positions, gradient norm cap 1.0, and at most 20 epochs. Select the checkpoint by validation negative log likelihood, with a four-epoch patience rule. Evaluate the test split once after freezing the selected checkpoint.

Initial budget proposal, to calibrate on the first authorized M4 run:

- Laptop CPU only; one process, no background engine. No runtime allocation is authorized by this plan.
- Three fixed seeds at most; maximum 45 minutes per seed and 3 hours aggregate for data verification, training, and evaluation.
- Model parameter cap: 250,000; estimated proposed design: 121,897 parameters, to be verified against the actual module configuration in M4.
- Peak working-memory cap: 2 GiB for the process; aim to keep cached features below 512 MiB.
- Stop at the first wall, memory, nonfinite-gradient, corrupt-artifact, or data-identity limit. Do not expand data or compute to rescue a weak result.
- No neural training or throughput benchmark has been performed during Pre-M4. Measure epoch time, examples/candidates per second, p50/p95 inference latency, peak RSS, and checkpoint size during M4 before deciding whether any later resource request is justified.

If the run exceeds its time cap, validation fails to beat the uniform-legal baseline, or M5 schedule is at risk, record the failure and prioritize M5 core work. Do not report PGN move prediction as playing strength, Elo, successful RL, or Atari performance.

## 6. M5 compatibility and verification boundary

The M4 checkpoint is a behavior-cloning policy checkpoint, not a Q-network or Double DQN agent. Transfer the board encoder, move-history embeddings/GRU, state metadata projection, candidate encoder, and candidate hidden scorer. Reinitialize the final scalar output layer for Q-values; do not interpret softmax probabilities or behavior logits as Q-values. Initialize/synchronize the M5 target network only after constructing the new Q head.

At M5 start, test feature parity between M3 reconstruction and M2 observation/history replay, UCI round-trip for the selected candidate, legal masking for variable and empty sets, Double DQN online selection/target evaluation of the same semantic move, reward perspective, terminal/no-bootstrap behavior, and the explicit truncation/bootstrap rule. Keep an identical-architecture random-initialized DDQN arm. Use paired seeds, equal M5 environment transitions/update counts, opponents, evaluation colors and settings; report M4 pretraining compute separately from equalized M5 compute.

The M4 design is not an ALE perception solution. M6 must obtain board state from verified ALE RGB and history from successfully observed moves. On uncertain occupancy, missed moves, or desynchronization, inference stops. Validate representability of special moves, move history, official ALE settings, and throughput under M6; do not infer those results here.

## 7. Checkpoints, risks, and completion

Checkpoint only at meaningful state/gate transitions and before long runs. The checkpoint command now avoids writing a new record when state, handoff, Git index, and workspace content are unchanged. Preserve the full history; a projected state above 4 MiB requires a separately tested lossless history migration. Store training checkpoints in approved artifact storage, not Git.

Primary risks: unavailable local M3 artifacts; unresolved third-party package license; small and potentially unrepresentative PGN sample; move-history model overfitting; CPU schedule; incomplete M6/ALE observability; and the M4/M5 weight-transfer boundary.

M4 is complete only when `M4-01`–`M4-04` each have their required verified evidence, the behavior-only checkpoint and run manifest are hashed and reproducible, inference loads without Stockfish, all requested tests pass, and state/backlog record M4 complete. A strong supervised score is not a prerequisite for M5 and does not complete M5. Until the conditional authorization is activated after all entry conditions are met, keep `M4-001` pending, `active_milestone: null`, and `start_authorized: false`.
