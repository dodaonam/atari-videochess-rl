# M04 — Supervised Pretraining Plan

- **Plan ID:** M04
- **Milestone:** M4 — supervised pretraining, within the sequence owned by `docs/02-management/EXECUTION_PLAN.md`
- **Plan status:** `in_progress`; BLK-002 was resolved by the dated PM-approved M4-02 sampling amendment. M4-02 passed and is recorded in `.agents/evidence/M4-02-revised-sanity-pass-20261027.md`. Run r3 completed all three seeds and validation selection, then failed safe checkpoint reload because runtime metadata contained a PyTorch `TorchVersion` object; see `.agents/evidence/M4-run-r3-checkpoint-load-failure-20261027.md`. The serialization fix is being verified before a cumulative-budget-aware rerun; no test evaluation or accepted checkpoint is claimed.
- **Authorization:** The direct M4-001 execution authorization recorded in `.agents/evidence/M4-001-execution-authorization-20261027.md` remains active. The PM protocol amendment is `.agents/evidence/M4-02-protocol-amendment-20261027.md`; the O-01 supersession remains in `.agents/evidence/M4-001-authorization-conditional-20261023.md`.
- **Canonical task:** `M4-001` in `.agents/tasks/BACKLOG.yaml` is `in_progress`. The original lexical-128 sanity run reached 126/128 and failed; it remains immutable historical evidence. The PM amendment changes only selection to the first 128 distinct complete effective inputs in ascending train `sample_id` order. The revised gate passed at 140 updates. Run r3 completed all three seeds and selected a checkpoint using validation NLL, then failed at safe reload due to serialized PyTorch version metadata. The fix is in progress; no final test evaluation, simulator benchmark, or accepted pretrained checkpoint is yet claimed.
- **Dependency:** `M3-001` complete; accepted M3 release identity and split contracts are recorded in `.agents/evidence/M3-acceptance-20261021.md` and `.agents/evidence/M3-final-closure-record-20261021.json`.
- **Plan and protocol:** [MODEL_DESIGN.md](../../docs/03-technical/MODEL_DESIGN.md), [TRAINING_PROTOCOL.md](../../docs/04-research/TRAINING_PROTOCOL.md), and accepted [ADR-0003](../../docs/02-management/decisions/ADR-0003-pretraining-model-interface.md).
- **Acceptance:** `M4-01` through `M4-04` in `docs/06-quality/ACCEPTANCE_CRITERIA.md`.
- **Readiness evidence:** `.agents/evidence/PRE-M4-final-closure-20261027.md` (final `R01`–`R08` and PM4 matrix); `.agents/evidence/PRE-M4-readiness-20261022.md` preserves the original dated review. These IDs are not formal acceptance criteria.

This plan records the implementation and evidence work for the already authorized M4-001 task. The accepted design keeps behavior cloning a small support experiment for the project's Double DQN objective. M5 core work must not wait for M4, consistent with `EXECUTION_PLAN.md` and the current M5 acceptance contracts. This task does not approve G3 or start M5. The original blocker diagnosis is `.agents/evidence/M4-02-sanity-gate-blocker-20261027.md`; its sample-selection impossibility was resolved by the dated PM decision `.agents/evidence/M4-02-protocol-amendment-20261027.md`. Preserve the exact M3 release and all original failed-run evidence.

## 1. Objective and scope

Implement and evaluate a bounded supervised behavior-cloning baseline using only the `played_move_uci` labels in the accepted M3 training split. Preserve validation and test partitions, save a pretraining-only checkpoint, and verify that the model chooses only among the simulator's semantic legal moves.

In scope under the direct authorization; the canonical task/milestone is now `in_progress` after the PM protocol amendment resolved BLK-002:

1. Implement the versioned model input/action contract and the accepted shared board/history/candidate scorer.
2. Verify model shape, finite logits, gradients, deterministic legal-action masking, and checkpoint round-trip (`M4-01`).
3. Demonstrate the revised 128-example overfit sanity check before full training (`M4-02`). The original lexical-ID attempt failed at 500 updates and remains preserved. The dated PM amendment selects the first 128 train examples with pairwise-distinct complete effective model inputs, independent of labels, while preserving the seed, model, optimizer, update cap, and numeric thresholds. This revised gate passed and the run proceeds to full training.
4. Train the behavior baseline on the M3 train partition, select using validation only, preserve the test set for one final report, and keep Stockfish absent from inference (`M4-03`, `M4-04`).
5. Store model/run artifacts outside Git with a manifest that identifies source revision, configuration, seeds, data release and split IDs, dependency versions, metrics, and checkpoint hashes.

Out of scope: new data acquisition or generation, expanded Stockfish labeling or evaluation, model-based ALE work, ROM activity, cloud/GPU allocation, M5 Double DQN implementation/training, and any milestone or gate approval.

## 2. Entry conditions

The owner authorization and Pre-M4 entry conditions are recorded in `.agents/evidence/M4-001-execution-authorization-20261027.md` and the dated addendum to `.agents/evidence/M4-001-authorization-conditional-20261023.md`. The PM's dated protocol amendment resolved BLK-002, and canonical task/milestone state returned to `in_progress`; `start_authorized` remains true. G3 remains unapproved and is not a start prerequisite; do not add `requires_user_gate_approval: G3`.

The executor must also:

- Confirm M3-001 still has status `done`, M4-001's direct authorization remains valid, G3 remains unapproved, and BLK-002 is resolved by the dated PM amendment in canonical blocker/state records.
- The exact accepted release is outside Git and was independently reverified read-only at the owner-specified local sibling-worktree path; see `.agents/evidence/M3-release-local-verification-20261027.md` and the current M4 pre-run verifier record `.agents/evidence/logs/M4-release-reverification-20261027-r1.json`. The M4 run command uses this path and the loader reruns the verifier against all nine files before tensorization. The final run result must be retained in versioned evidence. Do not copy, upload, rebuild, or commit bulk data; if the release becomes unavailable, stop rather than rebuilding from the license-uncertain package.
- Continue within the owner's established local/internal use boundary. The third-party curated package license is unstated; no bulk source or derived data may be uploaded or redistributed. Do not request another confirmation of this settled scope.
- O-01 is closed for internal project planning and execution authorization by the owner's 2026-10-27 decision. No separate instructor-policy approval has been evidenced or is claimed; that absence is informational and is not an activation prerequisite. If an actual authoritative rule explicitly prohibits a selected activity, stop only that activity and record the concrete rule.
- Use local CPU for the initial run. Any Colab/GPU, cloud storage, paid compute, new dataset use, or expanded teacher role requires separate authorization.
- PR #5 is integrated. Checkpoint history is already held in immutable, ordered archive segments with a manifest and byte-exact source-state backup; verify it with `python3 scripts/migrate_checkpoint_history.py verify` and preflight. The compact-state projected-write guard remains 4 MiB (including its reserve) and refuses a write before changing canonical files; it does not require another history migration. The archive grows linearly, integrity checks read/hash/decompress its contents, and separately atomic multi-file updates are not crash-atomic; follow the documented roll-forward/recovery boundary. Review storage and verification performance before the archive approaches 64 MiB. Never delete, truncate, reorder, or rewrite existing history.

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

Fixed initial authorization limits, to measure during this M4 run:

- Laptop CPU only; one process, no background engine. No runtime allocation is authorized by this plan.
- Three fixed seeds at most; maximum 45 minutes per seed and 3 hours aggregate for data verification, training, and evaluation.
- Model parameter cap: 250,000; the current implementation test measures 121,897 parameters against the accepted module configuration.
- Peak working-memory cap: 2 GiB for the process; aim to keep cached features below 512 MiB.
- Stop at the first wall, memory, nonfinite-gradient, corrupt-artifact, or data-identity limit. Do not expand data or compute to rescue a weak result.
- No real M4 training or throughput result is claimed until the bounded run evidence is recorded. Measure epoch time, examples/candidates per second, p50/p95 inference latency, peak RSS, and checkpoint size during M4.

If the run exceeds its time cap or M5 schedule is at risk, record the failure and prioritize M5 core work. Compare validation against the uniform-legal baseline and report any failure to exceed it, without changing the model or compute budget. Do not report PGN move prediction as playing strength, Elo, successful RL, or Atari performance.

## 6. M5 compatibility and verification boundary

The M4 checkpoint is a behavior-cloning policy checkpoint, not a Q-network or Double DQN agent. Transfer the board encoder, move-history embeddings/GRU, state metadata projection, candidate encoder, and candidate hidden scorer. Reinitialize the final scalar output layer for Q-values; do not interpret softmax probabilities or behavior logits as Q-values. Initialize/synchronize the M5 target network only after constructing the new Q head.

At M5 start, test feature parity between M3 reconstruction and M2 observation/history replay, UCI round-trip for the selected candidate, legal masking for variable and empty sets, Double DQN online selection/target evaluation of the same semantic move, reward perspective, terminal/no-bootstrap behavior, and the explicit truncation/bootstrap rule. Keep an identical-architecture random-initialized DDQN arm. Use paired seeds, equal M5 environment transitions/update counts, opponents, evaluation colors and settings; report M4 pretraining compute separately from equalized M5 compute.

The M4 design is not an ALE perception solution. M6 must obtain board state from verified ALE RGB and history from successfully observed moves. On uncertain occupancy, missed moves, or desynchronization, inference stops. Validate representability of special moves, move history, official ALE settings, and throughput under M6; do not infer those results here.

## 7. Checkpoints, risks, and completion

Checkpoint only at meaningful state/gate transitions and before long runs. The checkpoint command now avoids writing a new record when state, handoff, Git index, and workspace content are unchanged. Preserve the full history in the existing append-only archive. The 4 MiB projected compact-state guard is a write refusal boundary, not a trigger for another migration. Verify the archive manifest, segments, logical digest and source backup before recovery. The archive grows linearly and verification I/O grows with it; multiple file replacements are not crash-atomic. Review storage/performance before 64 MiB. Store training checkpoints in approved artifact storage, not Git.

Primary risks: the third-party package license remains unstated outside the bounded owner-authorized local use; the 1,000-game PGN sample may be unrepresentative; move-history model overfitting; CPU schedule; incomplete M6/ALE observability; and the untested M4/M5 weight-transfer boundary. Availability and integrity of the exact local M3 release were verified once and must be checked again immediately before training.

M4 is complete only when `M4-01`–`M4-04` each have their required verified evidence, the behavior-only checkpoint and run manifest are hashed and reproducible, inference loads without Stockfish, all requested tests pass, and state/backlog record M4 complete. A strong supervised score is not a prerequisite for M5 and does not complete M5. `M4-001` is `in_progress`; the revised gate, full training, frozen test evaluation, simulator evaluation, and final checkpoint acceptance remain unverified. Do not mark M4 accepted on the basis of source implementation, passing unit tests, or the failed original sanity run.

## 8. Acceptance evidence map for the active M4 executor

The checks below define required evidence; they are not passed by this plan. The focused M4 modules now exist and have initial unit coverage. The real M3 release loading/training command and final verification results must still be executed and logged. Use the repository's standard-library `unittest` modules; no pytest dependency is needed.

| Criterion | Planned implementation/check | PASS evidence | Failure state |
|---|---|---|---|
| `M4-01` | Run from the repository root: `uv run --locked --no-sync --project . python -m unittest tests.test_m4_model tests.test_m4_data tests.test_m4_training tests.test_m4_checkpoint tests.test_pre_m4_contracts tests.test_m2_simulator tests.test_m3_data -v`. This uses the project's locked standard-library `unittest` workflow; no `pytest` dependency is declared or needed. Assert shapes/dtypes, candidate UCI identity and masks, finite forward/loss/gradients, gradient flow, terminal empty sets, edge moves, determinism, checkpoint round trip and no Stockfish import/inference. Measure and record actual parameter count against 250,000. | Test log, versioned feature/model config, parameter-count measurement, checkpoint reload and SHA-256, feature-version compatibility report. | Any interface mismatch, nonfinite value, illegal candidate, parameter cap exceedance or unreproducible load is FAIL; do not train. |
| `M4-02` | Run protocol revision `M4-02-distinct-effective-inputs/1.0`: select the first 128 pairwise-distinct complete effective inputs in ascending training `sample_id`, independent of labels; persist IDs, input hashes and seed; initialize fresh weights. | Within 500 updates, cross-entropy ≤0.05 and legal top-1 ≥99%; evidence includes selection version, exact IDs/hashes, seed, revision, timing, loss and accuracy. | If thresholds miss, diagnose/fix only in-scope implementation defects and stay within budget; never waive the gate or start full training. |
| `M4-03` | Serialize the selected behavior-only checkpoint and load it in an inference-only process with Stockfish unavailable; hash checkpoint and run manifest. | Clean reload, finite legal-candidate logits and correct feature/data version identities; no engine call/dependency. | Missing/mismatched hash, feature version, illegal output or engine dependency is FAIL. |
| `M4-04` | Run the bounded training protocol, validation-only selection, one frozen test evaluation and the prescribed M2 random/heuristic simulator check. | Per-seed train/validation metrics, selected epoch, one test result, side/move-type strata, latency/throughput/memory/checkpoint measurements and complete simulator W/D/L trace summary. | Any unrun/incomplete budget-limited portion is marked BLOCKED or NOT RUN; do not infer Elo, RL learning or Atari strength. |

M4 execution command: `python -m videochess_rl.model.cli run --release-dir /home/dodaonam/Projects/atari-videochess-rl-m3/artifacts/m3/training-support/release-final-closure-r6 --artifact-root /home/dodaonam/Projects/atari-videochess-rl-m4/artifacts/m4`. The runner enforces the recorded CPU, seed, memory, and aggregate limits and preserves run artifacts outside Git. The full locked regression command remains `uv run --locked --no-sync --project . python -m unittest discover -s tests -v`; if `uv` is unavailable but the existing verified `.venv` works, use its interpreter without installing dependencies and record the deviation.

This plan does not itself confer M4 acceptance. Existing feature-branch source/contract evidence supports M4-01 within its tested scope; the original fixed gate failed M4-02 and remains historical; the revised M4-02 run is pending; M4-03 and M4-04 are not yet complete. `M4-001` is `in_progress` under direct owner authorization and the dated PM amendment; O-01 does not require another owner or instructor confirmation. See the protocol amendment, blocker history, and canonical state before reporting any M4 result.
