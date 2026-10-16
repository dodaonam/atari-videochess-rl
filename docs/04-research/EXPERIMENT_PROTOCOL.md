# Experiment and Evaluation Protocol

**Status:** Proposed research protocol. It does not approve M3–M7 execution or choose a final model architecture.  
**Owners:** This file defines experiment identity, comparisons, and metric separation. Dataset and teacher meanings are defined in [DATASET_SPEC.md](DATASET_SPEC.md) and [STOCKFISH_TEACHER.md](STOCKFISH_TEACHER.md).

## 1. Experiment identity

Every run receives a unique immutable experiment ID and a machine-readable manifest. Store:

- milestone/stage and objective;
- source Git revision, dirty-tree status, code/config hashes, exact command, and UTC start/end times;
- Python, OS, CPU/GPU, ALE/ROM, python-chess, PyTorch, Stockfish, and relevant library versions;
- source archive and derived dataset release IDs/hashes, source rights decision, schema version, split hash, and sampling rule;
- teacher binary/config/run hash where used, including explicit no-teacher status otherwise;
- experiment seed and derivation rule; Python, NumPy, PyTorch CPU/CUDA, environment, simulator, and agent RNG seeds as applicable;
- requested/effective CPU threads, RAM/hash limits, GPU type/memory when used, elapsed wall time, peak memory/disk, and stop reason;
- raw per-example/per-episode metrics, aggregation code revision, exclusions, missing results, and artifact hashes;
- checkpoint path outside ordinary Git, SHA-256, checkpoint role, and whether it is pretraining-only, post-RL, or another stage.

A config hash is computed from canonical UTF-8 JSON with sorted keys and stable numeric/string representations. Keep the original human-readable config as well as its hash. A change to source, split, model checkpoint, teacher config, environment, or metric code creates a new run ID.

Seeds improve repeatability but do not guarantee bitwise identity across different hardware, package builds, nondeterministic kernels, engine versions, or ALE builds. Record actual RNG state when a run must resume midstream.

## 2. M3 — data and label validity

M3 evidence is a data-engineering result, not a playing-strength result. Report:

- archive/member hashes, source and license decision, retrieval date, parser/version/config/code revision;
- games seen, accepted, quarantined, rejected, and reason counts;
- parsed headers and missing/invalid metadata rates;
- move counts, legal replay failures, duplicate games, duplicate positions, and per-ply sampling;
- side-to-move/result distributions, ratings/time controls where present, legal-candidate counts, and opening/middle/later-ply coverage;
- teacher label coverage/failure/mate/MultiPV rates only if an approved teacher run occurs;
- split counts, source-game overlap, canonical-position overlap before and after purge, holdout size, and split/config hashes;
- output byte counts, SHA-256 manifests, resume proof, and resource use.

No source statistics may be backfilled from the publisher's listing as if measured locally.

## 3. M4 — supervised pretraining

Keep a behavior-only checkpoint as the baseline. If an outcome or teacher task is added, run it as a separately named configuration and retain its own checkpoint.

For a played-move objective, report held-out cross-entropy, legal top-1/top-k accuracy, candidate ranking metrics, and metrics stratified by side, ply band, rating/time-control availability, and source. All candidates for a position stay together. Invalid model outputs outside legal candidates are an inference/test defect, not a correct prediction.

Compare against a legal-random policy and a transparent heuristic where evaluation is permitted. Do not turn PGN accuracy into an Elo estimate. A held-out split measures prediction on that split's sampled games; it does not establish general chess strength.

Small-sample overfit/sanity checks are engineering diagnostics, not final evaluation. Save training/validation curves and actual checkpoint hashes. Do not run Stockfish during model inference.

## 4. M5 — simulator reinforcement learning

Record the simulator state/action/transition contract, python-chess version, Board/history reconstruction, fixed agent color, opponent policy/configuration, reward perspective, terminal reason, truncation reason, and episode decision cap.

Compare:

1. pretraining-only checkpoint;
2. post-RL checkpoint;
3. random-legal and heuristic baselines.

Use the same opponent set, color coverage, opening/start-state rules, decision caps, and seed list across compared checkpoints. Report complete-game W/D/L separately from truncations, interruptions, and policy failures. Use multiple seeds and report per-seed results, variance/uncertainty, and all exclusions. If a comparison changes the opponent pool or configuration, identify it as a different experiment.

Simulator returns and M2 benchmark metrics remain labeled simulator evidence. They are not ALE gameplay or Atari reward.

## 5. M6 — real ALE integration and evaluation

The ALE observation and actual step response remain the source of truth. A python-chess Board is a shadow/cross-check and may not repair an RGB mismatch or invent an Atari state.

Every move follows observe → validate → decide → execute → observe → verify. Record environment ID/version, ROM identity/hash, ALE/Gymnasium versions, wrapper order, sticky actions, frame skip, mode/difficulty, seed, raw reward, terminated/truncated flags, input sequence, observed move result, desynchronization and recovery/stop reason.

Report per-game completion, win/draw/loss where interpretable, raw reward and perspective, legal move execution rate, opponent reply recognition, desynchronizations, step/frame counts, wall time, and failures. Separate terminal events from runner timeouts and safety stops. Real ALE results cannot be replaced by simulator games, synthetic frames, or extracted-board-only checks.

Do not use Stockfish in the inference path. Any engine opponent or offline ALE evaluation requires the relevant assignment decision first.

## 6. M7 — integrated reporting

Use named evidence tracks: expert PGN behavior, optional Stockfish teacher, supervised learning, simulator RL, and actual ALE evaluation. State which checkpoint and data/teacher/config hash produced each metric. Report negative, neutral, and regressive outcomes with the same prominence as positive results.

Any Elo claim needs an approved, named, calibrated opponent pool, colors, time controls, opening protocol, game count, and uncertainty estimate. Until then report raw W/D/L and conditions only. The aspirational 1500 Elo in project background is not a measured result or acceptance threshold.

