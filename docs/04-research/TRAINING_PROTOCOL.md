# M4 Supervised Training Protocol

**Status:** Protocol for the architecture accepted in [ADR-0003](../02-management/decisions/ADR-0003-pretraining-model-interface.md). No M4 model, training, checkpoint, or neural-throughput measurement has been produced. `M4-001` remains pending because its conditional authorization still requires authoritative O-01 course-policy evidence and canonical activation.

**Objective:** Produce a small, reproducible behavior-cloning baseline that supports later Double DQN experiments. Supervised prediction is not reinforcement learning and is not a chess-strength or Atari-performance claim.

## 1. Dataset identity and permissible targets

Use only the accepted M3 closure release:

- Release ID: `f10a679deddf06f3e1e3c39cf58db4e21176629c26c09034a271bf278189e890`.
- Release-manifest SHA-256: `be1e1f9316fac01be893774cfe09a313de193fbd1a12ab2d219ff5c041104a12`.
- 1,000 selected games; 19,268 retained position rows.
- Train: 15,196 rows; validation: 2,015; test: 2,057.
- Split assignment SHA-256: `84efed824e57de45c0058b73818bb7a9d740201ead38e9171308cee43bc0934e`.
- The split is game-grouped and then purged to zero cross-split board-position signatures. Reuse its recorded assignment and do not re-split.

All identities are supported by accepted M3 evidence and the exact local release was independently verified read-only in the sibling M3 worktree; see `.agents/evidence/M3-release-local-verification-20261023.md`. The raw release, source archive, and teacher sidecar remain outside this checkout and Git. No M4 data loading or training is claimed. Before training, re-run the project verifier against the configured local release path. Do not download, copy, upload or regenerate the license-uncertain package.

Owner-confirmed technical direction is custom PyTorch, Double DQN as the principal RL method, and a bounded supporting behavior-cloning stage; Stockfish is not used by this initial behavior-only run or by inference. O-01 remains open only for authoritative external course-policy constraints on wrappers, custom implementations, behavior cloning, and any engine role. Obtain or locate that evidence before activating M4-001; this protocol does not invent instructor approval.

For this behavior-only experiment, the target is only the recorded `played_move_uci` in each valid M3 position. The move is a historical PGN action, not an optimality label. M3 validation already requires the move to be legal and present in the candidate set. The accepted 128-position Stockfish teacher sidecar is not used in this first run; broader M4 teacher training/evaluation use needs separate owner direction under the existing Stockfish boundary.

Do not expose game result, player names/ratings, future moves, engine scores/PVs, teacher ranks, split labels, or source/release metadata to the model. Dataset provenance and split membership remain in the loader/run manifest, not feature tensors.

## 2. Efficient and bounded example construction

Do not call `validate_position_record()` independently for every example on every epoch. That function calls `reconstruct_position()`, which revalidates the whole game and replays its prefix. Repeating that path across 19,268 examples and epochs multiplies replay work.

Use this future M4 loading sequence instead:

1. Verify the immutable release identity, manifest and each listed file once; run the M3 release verifier once before tensorization.
2. Read the game and position JSONL files once and index position rows by `game_id` and `ply_index`.
3. Validate each game record once. Replay each game's main line once from `initial_fen`, visiting requested plies in order. At each selected ply, compare its canonical FEN, legal UCI set, target move, identity and split fields with the stored row.
4. Tensorize board planes, scalars, full history tokens, sorted legal candidates, and target candidate location during that pass. Cache only those bounded features for training; do not retain duplicate `Board` objects or every intermediate position.
5. Shuffle/bucket examples deterministically each epoch. Bound a collated batch by 64 positions, at most 32,768 padded history tokens, and at most 8,192 candidate slots; reduce the physical batch and accumulate gradients when a batch hits a tensor budget.
6. Keep the feature cache below 512 MiB. The model process has a 2 GiB peak-RSS cap. Measure actual memory and feature counts; if the cap is exceeded, stop and record it rather than dropping examples silently.

The selected release has roughly 30 legal candidates per retained position on average (578,351 candidate rows across 19,268 positions in the accepted summary). Actual per-split candidate counts and maximum history length must be measured from the provided release before model training; the aggregate does not determine batch padding behavior.

## 3. Loss and baselines

For each nonterminal example, score exactly its legal candidates and minimize cross-entropy over the candidate set, with the played UCI move as the sole target. Apply the candidate mask before normalization. No ranking loss, Stockfish distillation, result prediction, or reward regression is part of the initial experiment.

Required baseline: a uniform distribution over each position's legal moves. For a row with `n` candidates its expected top-k accuracy is `min(k,n)/n`, expected reciprocal rank is `H_n/n` (where `H_n` is the nth harmonic number), top-1 expectation is `1/n`, and negative log likelihood is `log(n)`. Average the per-row values and report the measured baseline on the same validation/test rows. It is a chance/reference baseline, not an opponent or strength rating.

Optional if it fits the cap: a move-frequency prior fitted only on the training split and restricted to each row's legal candidates. Do not let it delay M5 or alter the base acceptance; clearly label it as a train-only statistical baseline.

## 4. Proposed initial optimization configuration

These are fixed starting values for the first authorized run, not optimized or previously measured settings:

| Setting | Initial value / control |
|---|---|
| Model | Proposed action-conditioned architecture in `MODEL_DESIGN.md`; parameter cap 250,000 (estimated 121,897). |
| Objective | Legal-candidate behavior cross-entropy. |
| Optimizer | AdamW; learning rate `3e-4`; weight decay `1e-4`. |
| Physical batch | Up to 64 positions, bounded further by history-token and candidate-slot limits above. |
| Gradient | Norm clip at 1.0; fail the run on nonfinite loss, logits, gradients, or parameters. |
| Epoch cap | 20 per seed. |
| Seeds | `20261022`, `20261023`, `20261024`; record all Python/PyTorch RNG states. |
| Determinism | CPU-only initial run, one PyTorch intra-op and inter-op thread, deterministic data order per seed, fixed runtime/library versions; enable PyTorch deterministic algorithms and record any unsupported operation rather than silently disabling the setting. Use zero data-loader workers; seed Python, PyTorch, and any additional RNG used by the loader. |
| Device | Laptop CPU only. No Colab/GPU/cloud runtime is allocated by this plan. |

Checkpoint only model/optimizer state and run metadata. Keep the model in evaluation mode for all reported metrics. Resolve ties by sorted UCI order for deterministic greedy selection.

## 5. Validation, selection, and stopping

Before full training, run `M4-02`'s fixed 128-example overfit sanity test using only the train partition. Select the 128 lexicographically smallest training `sample_id` values once from the verified release; store their IDs in the run manifest and reuse the same examples, candidate sets and target identities. Within 500 optimizer updates, require training cross-entropy at or below 0.05 and legal top-1 accuracy at or above 99%; if it fails, stop before full training and diagnose the implementation.

For full runs, evaluate validation negative log likelihood and legal top-1 after every epoch. Select the lowest validation NLL checkpoint; if tied, select the earlier epoch. Stop after four consecutive epochs without validation-NLL improvement or at 20 epochs. Do not inspect test metrics for model/config selection.

Abort the run on a manifest/hash/count mismatch, missing expected split, invalid target, nonfinite output/gradient, checkpoint write/reload mismatch, process RSS above 2 GiB, 45 minutes for one seed, or the 3-hour aggregate wall cap. Report the failure without relaxing the criterion or expanding the data, labels, or compute budget. Stop earlier if the behavior work starts to delay M5 Double DQN implementation.

## 6. M4 metrics and interpretation

Report train and validation metrics by seed while selecting the final checkpoint. After the validation-only checkpoint/seed choice is frozen, report test metrics once for that selected checkpoint; do not test every seed or use test values to choose among them:

- legal-candidate negative log likelihood and top-1, top-3, and top-5 accuracy;
- mean reciprocal rank of the played PGN move and the uniform-legal baseline values;
- per-side-to-move top-1/NLL;
- counts and accuracy for promotions, castling, en passant, captures, and checking moves when the stratum has enough examples; otherwise report counts and mark the estimate descriptive/underpowered;
- validation-selected epoch, train/validation curves, seed variability, and any failed/aborted runs;
- p50/p95 single-position inference latency at representative candidate counts, examples/candidates per second, peak RSS, model/checkpoint bytes, and hardware/runtime versions.

After freezing the checkpoint and all settings, evaluate the test partition once for the selected checkpoint and record its results. Do not use test performance to select a seed, epoch, or model. Also run a bounded simulator-only greedy-policy check with the selected checkpoint and Stockfish absent: use seeds `20261030` through `20261039` for each of the existing `RandomLegalAgent` and `SimpleHeuristicAgent`, with each seed paired across both agent colors (40 games total). Cap each game at the M2 maximum of 400 agent decisions, and impose a 20-minute aggregate cap. Record W/D/L, termination/truncation, decision count, and latency. If the cap interrupts the set, report an incomplete benchmark; do not substitute Elo or an Atari claim.

These metrics measure imitation of this PGN sample and a small M2 simulator behavior check. They do not prove best-move quality, general chess strength, Double DQN learning, transfer to new games, or actual Atari performance.

## 7. Compute and schedule limits

Initial total budget: three CPU seeds maximum, 45 minutes per seed, 3 hours aggregate including one-time data verification and the bounded 40-game simulator check, 2 GiB process RSS maximum, 250,000 parameters maximum, and 512 MiB target feature-cache size. The first run must record load time, epoch time, examples/candidates per second, peak memory, test/validation time, and inference latency to calibrate these estimates.

No neural model or training throughput exists to benchmark during Pre-M4. M3's historical CPU dataset run is a different workload and is not used as a neural throughput estimate. If the first authorized CPU profile cannot meet the cap, stop and seek owner direction before proposing GPU/Colab, changing the model budget, or extending the schedule. Paid compute, cloud storage, and runtime allocation remain separately authorized decisions.

## 8. Required M5 paired comparison

M5 must compare two otherwise identical Double DQN systems:

1. The proposed model initialized by transferring M4's board/history/state/candidate encoders and hidden candidate scorer, with a freshly initialized Q output head.
2. The same Q architecture randomly initialized, with no M4 pretrained weights.

Match M5 environment transitions, gradient updates, replay capacity/sampling, target-network schedule, optimizer, exploration schedule, opponent identities/configs, colors, evaluation settings, and paired random seeds. Use the same model feature version and legal candidate pipeline in both arms. Report M4 pretraining compute as a separate cost, then report equalized M5 compute and total compute for each arm. Use the same held-out simulator opponent pool for both; no Stockfish role is implied. Report raw W/D/L, uncertainty, seeds, truncations, and any ALE evaluation separately. This experiment estimates the effect of warm-start initialization under the chosen protocol; it does not turn the M4 policy logits into Q-values.

## 9. Reproducibility and artifact record

Every authorized run records:

- full Git revision and clean/dirty status, exact command, model/data config, and run ID;
- M3 release ID, manifest/checksum identities, split IDs/counts, per-split selected record identities, and target semantics;
- Python, PyTorch, `python-chess`, OS/CPU/device versions and thread count;
- seed and RNG state, determinism setting, optimizer/scheduler, batch/token budgets, selected epoch and early-stop reason;
- raw per-epoch metrics, frozen test metrics, simulator game traces/results, throughput/latency, wall time, peak RSS, model parameter count and file size;
- checkpoint SHA-256, artifact location, and restore/load verification.

Keep the source archive, release JSONL, model checkpoints, and full game artifacts out of Git. Retain only sanitized portable manifests/logs and paths/hashes in repository evidence. This protocol neither retrieves the source nor authorizes external upload.
