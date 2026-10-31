# Test Strategy

**Canonical source for:** test layers and verification practices. Per-milestone pass conditions are in [`ACCEPTANCE_CRITERIA.md`](ACCEPTANCE_CRITERIA.md); current task results are in `.agents/tasks/BACKLOG.yaml` and G1 verification in `.agents/state/PROJECT_STATE.yaml`.

## Principles

- Define observable success before implementation. Add focused tests for changed behavior and run relevant suites before claiming completion.
- Keep tests deterministic where practical; record seeds and environment-dependent settings.
- Do not treat a unit test or simulator result as evidence of Atari integration.
- Preserve actual command results and sanitized logs. A test plan is not a test result.
- Use Python standard-library `unittest` for the G1 scripts so G1 adds no project dependency. The scripts must also work without PyYAML or GitPython.

## G1 context-tool checks

`tests/test_agent_context.py` exercises:

- valid and malformed JSON-compatible YAML state/backlog schemas;
- gate-to-milestone circularity, the partial M7 G4/G5 acceptance allocation, and direct milestone authorization evidence separate from gate approval or plan references;
- duplicate/missing task IDs, unknown dependencies, dependency cycles, and missing evidence on completed tasks;
- valid and broken repository-relative Markdown links (external URLs are not fetched);
- blocker/task consistency and unresolved approval reporting;
- all acceptance criterion IDs from the table and bullet forms used by the criteria document, including future M2–M7 task references;
- command/file evidence provenance, explicit historical reports with unavailable timestamps/logs, and verified done-task evidence;
- stale handoff checkpoint IDs;
- a clean committed worktree, dirty tracked and untracked paths, and content changes that leave Git status paths unchanged;
- a real commit-and-clone recovery using only approved baseline files, with expected portable commit transitions, missing local-only files, cache creation, checkpoint-control restaging, and tracked edits;
- the distinction between SHA-256-verified files, large and unreadable files excluded from hashing, excluded directories, and artifact directories requiring independent manifests;
- orphan temporary files, normal partial recovery, and `--dry-run --recover-partials` with no file or Git metadata mutation;
- a one-invocation atomic checkpoint from a clean worktree and a fresh Python-process recovery summary.
- compact checkpoint serialization that preserves every history object, no-op behavior for unchanged snapshots, and a pre-write 4 MiB projected-state guard that leaves canonical files untouched on refusal.

`tests/test_checkpoint_history.py` separately covers the versioned history archive: exact logical-order preservation and original-state backup, interrupted/resumed migration, append and no-op behavior, size-bounded segments, caught rollback and pending roll-forward, corruption/unreferenced-file detection, stale handoff repair, and clean-clone recovery. Run it with the context suite when changing archive or checkpoint code:

```bash
python3 -m unittest tests.test_checkpoint_history tests.test_agent_context -v
```

The recovery format and operator commands are specified in [`CHECKPOINT_HISTORY.md`](../05-operations/CHECKPOINT_HISTORY.md). Archive integrity is checked by its state pointer and manifest; archive files must be committed with the pointer even though the per-checkpoint portable file manifest excludes them.

Run from the repository root:

```bash
python3 -m unittest discover -s tests -v
python3 scripts/agent_preflight.py
```

To refresh the state snapshot and handoff pointer after meaningful work:

```bash
python3 scripts/agent_checkpoint.py
python3 scripts/agent_preflight.py
```

To recover old agent-owned partial files after inspecting the preflight warning:

```bash
python3 scripts/agent_checkpoint.py --recover-partials
python3 scripts/agent_preflight.py
```

These commands operate only on project context state. They do not change task statuses, run RL tests, start Colab, or install dependencies.

`--dry-run` is read-only even with `--recover-partials`. `PROJECT_STATE.yaml` is omitted from its own content hash; its dirty path remains in the Git snapshot. Ordinary files above 2 MiB are listed under `unhashed_large_files`; files that could not be read are listed under `unreadable_files`. Artifact/data directories are listed under `artifact_dirs_requiring_manifest`; their contents are not hashed and must be validated with an independent manifest. Cache/VCS/build directories, temporary files, symlinks, chat history, and credential-like paths are excluded by policy.

Verified command/test evidence records `executed_at_utc`, `recorded_at_utc`, `exit_code`, `git_revision`, and `log_path`. Historical entries without retained source output use `historical_unverified` with unavailable metadata set to null. A fresh Python process proves G1-08 only; G1-10 requires a separate Codex session with no prior conversation, followed by a sanitized manual result record.

## M0 environment smoke checks

`tests/test_m0_smoke.py` runs inside the locked project environment with `uv run`. It checks a legal opening move through `python-chess`, a CPU-only PyTorch tensor operation, the bundled ALE-Py `video_chess` ROM resource, Gymnasium registration and VideoChess construction without reset, and a Stockfish UCI readiness ping without searching a position. ROM availability and environment construction do not verify M1 reset behavior, observations, controls, or gameplay. Check Colab CLI version/help without creating a session or invoking account usage/authentication.

## M1 ALE feasibility checks

`tests/test_m1_vision.py`, `tests/test_m1_control.py`, and `tests/test_m1_shadow.py` cover RGB square parsing, cursor ambiguity, phase-specific action timing, source-selection and selected-target observation phases, legal shadow transitions, and safe mismatch handling. Synthetic frames are unit fixtures only; they do not count as ALE evidence.

`tests/test_m1_environment.py` and `tests/test_m1_ale_integration.py` use the real packaged VideoChess ROM. They reset and capture the actual RGB screen, verify the configured mode for each supported mode, execute player moves through joystick/FIRE actions, observe computer replies from RGB, and compare results against legal `python-chess` shadow transitions. Closed-loop gameplay checks use deterministic development settings and the registered v5 defaults. Diagnostic RAM is never used to choose actions. `tests/test_m1_episode.py` covers source selection, target preview, target confirmation, bounded uncertainty stops, and reward/terminal bookkeeping with synthetic environment doubles; these tests are not runtime terminal evidence. Longer real-ALE control experiments and terminal evidence are recorded separately in `.agents/evidence/BLK-001-diagnostic-20261015.md`.

Run the M1 checks and bounded demo from the repository root:

```bash
uv run --locked python -m unittest tests.test_m1_vision tests.test_m1_control tests.test_m1_shadow tests.test_m1_environment tests.test_m1_ale_integration -v
uv run --locked python scripts/run_m1_demo.py --profile deterministic-dev --seed 20261015 --max-opponent-wait-frames 10000
uv run --locked python scripts/run_m1_demo.py --profile v5-default --seed 20261016 --max-opponent-wait-frames 10000
```

The runner writes JSON traces and raw RGB frames under ignored `artifacts/m1/`. Only sanitized hashes, settings, action summaries, and findings belong in version-controlled evidence. A real ALE terminal requires the actual step result and returned reward/flags; source code, an ALE mock, a python-chess outcome, or an experiment stop is not a substitute.

## M2 chess simulator verification design

M2 implementation and verification for M2-01 through M2-04 are complete; actual outcomes and retained logs are in the [M2 acceptance record](../../.agents/evidence/M2-acceptance-20261016.md). Keep chess rules in python-chess and use focused unit, simulator-integration, seeded-episode, and benchmark checks. The contracts are owned by [MDP_SPEC.md](../03-technical/MDP_SPEC.md).

| Layer | Required checks | Expected evidence |
|---|---|---|
| State and serialization unit tests | Deterministic position serialization and FEN round trip/normalization; preserve side to move, castling rights, the selected en passant FEN convention, and move counters. Preserve Board history by replaying UCI moves from the correct standard or custom initial position. | Test output and representative before/after states. FEN alone is not evidence of complete history or repetition state. |
| Legal move and UCI tests | Generated moves equal `Board.legal_moves`; ordinary moves, captures, castling, en passant, and all four promotions round-trip through stable UCI identities. Candidate ordering must not change identity. | Move/key fixtures plus invalid or stale move rejection with unchanged Board state. No model output head or action mask is required in M2. |
| Rule and transition unit tests | Verify Board changes and turn/counter/rights updates for legal moves. Cover checkmate, stalemate, insufficient material, automatic fivefold repetition, automatic seventy-five-move outcome, and simulator truncation. | Deterministic python-chess positions and reason-specific terminal/truncation assertions using the locked rules library. |
| Simulator integration tests | Agent move followed by one opponent reply; terminal after the agent move skips the reply; terminal after the reply returns without another agent step; rewards have correct agent-color signs for both colors; invalid moves preserve state; truncation retains the final valid state. | Transition records with moves, reward, terminal/truncation flags, final position, and stop reason. |
| Seeded episode tests | Same seed, agent color, opponent identity/configuration, and initial state reproduce move/outcome records. Random-legal and lightweight heuristic baselines return legal moves and complete bounded games. | Per-game traces with seed, policy identities, colors, moves, outcome, length, and truncation count. Incomplete games are not reported as completed. |
| Benchmark and metric separation | Run a small seeded set of games between identified baselines; record W/D/L, lengths, completion/truncation counts, external failures or interruptions, configuration, and revision. Keep simulator results separate from ALE results. | Per-game records and aggregate summary; schema/report checks prevent simulator metrics being labeled as ALE. Truncations and failures are excluded from W/D/L; no unsupported Elo claim. |

M2 tests remain focused on the acceptance contract; M4/M5 scoring, replay, target networks, and training are outside the simulator. M2 acceptance criteria are M2-01 through M2-04 in [ACCEPTANCE_CRITERIA.md](ACCEPTANCE_CRITERIA.md). [ADR-0002](../02-management/decisions/ADR-0002-chess-mdp-action-and-perspective.md) is accepted for the foundational simulator contract; test results are recorded separately in the acceptance record.

## Pre-M4 model-boundary contracts

`tests/test_pre_m4_contracts.py` and `videochess_rl/action_contract.py` cover the input/action boundary only; they do not implement or train a neural model. Synthetic tests verify:

- model-boundary canonical FEN uses legal-en-passant semantics while M2 raw FEN and M3 canonical FEN APIs remain unchanged;
- a noncapturable or pinned en-passant target normalizes away, while a legally capturable en-passant square remains;
- legal candidate ordering is stable lexical UCI, preserves promotion suffixes and maps the selected PGN UCI move exactly;
- White/Black mover orientation, both castling sides, captures, en passant, checking moves, and all promotion pieces;
- illegal moves are absent; checkmate, stalemate, fivefold repetition, and the seventy-five-move automatic draw return no candidates even when a drawn Board still has legal moves; full move history cannot be replaced by FEN for repetition-sensitive state.

Run with the project environment:

```bash
uv run --locked --no-sync --project . python -m unittest discover -s tests -p 'test_pre_m4_contracts.py' -v
```

These tests establish synthetic semantic-contract behavior only. The accepted real M3 release has been independently reverified read-only on 2026-10-28 and used unchanged by the M4 run; see [.agents/evidence/M3-release-local-verification-20261027.md](../../.agents/evidence/M3-release-local-verification-20261027.md), [the M4 final acceptance report](../../.agents/evidence/M4-final-acceptance-20261027.md), and the Pre-M5 verification record. The original fixed-gate failure and exact-input conflict diagnosis remain documented in the [M4 blocker report](../../.agents/evidence/M4-02-sanity-gate-blocker-20261027.md); the revised gate and complete M4 run are documented in the [final M4 acceptance report](../../.agents/evidence/M4-final-acceptance-20261027.md). The accepted M4 model and completed bounded protocol are in [MODEL_DESIGN.md](../03-technical/MODEL_DESIGN.md) and [TRAINING_PROTOCOL.md](../04-research/TRAINING_PROTOCOL.md).

## M4 model, data, training, and checkpoint tests

The M4 implementation adds `tests/test_m4_model.py`, `tests/test_m4_data.py`, `tests/test_m4_training.py`, and `tests/test_m4_checkpoint.py`. They cover schema/tensor shapes, mover orientation and full history, special-move features, deterministic legal UCI identity, mask/padding validation, finite outputs/loss/gradients, parameter count, synthetic record replay/target legality, train-only distinct-input selection, split isolation, optimizer/early-stop/budget behavior, checkpoint hashes/round trips, M5 shared-layer transfer with a fresh Q head, and inference with Stockfish absent. Unit tests use synthetic examples and temporary checkpoints; they do not stand in for the real M3 release or experiment. Separate versioned run artifacts verify the accepted release, revised 128-example gate, three-seed training, frozen test evaluation, engine-free checkpoint reload, and 40-game simulator evaluation. The complete evidence and limitations are in the [M4 acceptance report](../../.agents/evidence/M4-final-acceptance-20261027.md).

Run the focused M4 and affected contract tests:

```bash
uv run --locked --no-sync --project . python -m unittest \
  tests.test_m4_model tests.test_m4_data tests.test_m4_training tests.test_m4_checkpoint \
  tests.test_pre_m4_contracts tests.test_m2_simulator tests.test_m3_data -v
```

The real M4 release verification, revised sanity gate, training, validation-only checkpoint selection, one frozen test evaluation, engine-free reload, profiling, and bounded simulator games run through `python -m videochess_rl.model.cli run`. The exact run, a second 40-game confirmation with Stockfish absent, and their checksums are recorded in the [M4 acceptance report](../../.agents/evidence/M4-final-acceptance-20261027.md). Unit tests cannot substitute for those experiment results. The whole-suite command remains `uv run --locked --no-sync --project . python -m unittest discover -s tests -v`.

## Future project test layers

| Layer | Examples | Run when |
|---|---|---|
| Unit | Board encoding, reward sign, legal move selection, Bellman targets, serialization | Every relevant code change. |
| Simulator integration | Chess rules, agent/opponent transitions, terminal and truncation behavior | M2–M5 changes. |
| ALE integration | Real reset/observation, cursor/FIRE calibration, move execution, turn detection, board cross-check, reward, terminal, desync | M1/M6 changes; requires authorized ALE runtime. |
| Data integrity | Teacher score perspective, split leakage, provenance, hashes | M3/M4 changes. |
| Training/evaluation | Reproducible pretraining/RL runs, fixed opponent pools/seeds, checkpoints, raw metrics | Only after the relevant milestone and compute authorization. |
| Delivery/recovery | Fresh-session handoff, artifact references, end-to-end reproduction | G1 and M7 gates. |

## Pre-M5 Double DQN readiness fixtures

The versioned fixture in `tests/fixtures/m5_double_dqn_targets.json` supplies exact online/target disagreement, terminal, and valid-truncation target vectors. `tests/test_m5_contract_fixtures.py` validates the arithmetic and fixture shape using only the standard library. It does not test a Q model, replay, Bellman implementation, trainer, or M5 acceptance. Future M5 must apply the fixture to the actual target calculator and run the full matrix in [`M5_TEST_MATRIX.md`](M5_TEST_MATRIX.md).

## Pull request CI boundary

The bounded workflow in `.github/workflows/preflight.yml` runs on pull requests targeting `initial-idea`. It uses pinned GitHub-maintained actions, read-only repository permissions, Python 3.12, agent preflight, standard-library context/review-bundle tests, and the pure-standard-library M5 Bellman fixture oracle. It installs no project dependencies, downloads no dataset, launches no Stockfish search, allocates no GPU, and runs no ALE gameplay. Its coverage protects governance, links, checkpoint/recovery behavior, review-bundle safety, and one hand-calculated target fixture; it is not a replacement for the locked full suite, PyTorch tests, or M1/M2 integration tests. Checkout fetches full Git history because a recovery fixture reconstructs the recorded G1 baseline revision.

The workflow does not configure branch protection or a mandatory status check. GitHub Actions execution is limited to the standard public-repository runner. Review actual PR check results; no local run can claim a remote workflow passed. The PR-author/PM/operator roles and non-merging executor boundary are defined in [PR_REVIEW_AND_INTEGRATION.md](../02-management/PR_REVIEW_AND_INTEGRATION.md).

## M3 data integrity tests

The Pre-M3 synthetic contract vectors in `tests/fixtures/pre_m3_identity_vectors.json` are exercised by `tests/test_pre_m3_contracts.py`. They verify deterministic identity hashes, board signature versus replay-state identity (clocks, repetition, castling, en passant, and transposition), source-game versus normalized-game identity when headers differ, promotion UCI identity, game-group split assignment, candidate inheritance/purge, and detection of a collapsed holdout. This tiny oracle is not a production parser or dataset implementation.

M3 implementation tests are in `tests/test_m3_data.py` and `tests/test_pre_m3_contracts.py`, with synthetic PGN fixtures and no downloaded player records in the fixtures. They cover source/hash gates, archive/member caps, streaming/quarantine, standard-chess replay and history reconstruction, stable legal UCI candidates, played-move legality, perspective conversion, deterministic sampling/splits, board-overlap audits, teacher score/MultiPV/mate semantics, manifests, and interrupted-run recovery. Candidate/teacher rows inherit their parent sample split and are purged with it. The real accepted release is outside Git and was independently verified read-only during Pre-M4, then reverified and tensorized by the M4 loader with unchanged release files; the M4 run identity is recorded in the [M4 acceptance report](../../.agents/evidence/M4-final-acceptance-20261027.md). Synthetic model-boundary tests do not verify that release.

M3-02 required a bounded real Stockfish 19 run; the accepted 128-position M3 teacher run and M3-001 acceptance are recorded in `.agents/evidence/M3-corrective-hardening-20261021.md` and `.agents/evidence/M3-acceptance-20261021.md`. Fake-UCI and configuration tests alone do not satisfy that criterion. Future data acquisition or expanded teacher use remains separately scoped under `REQUIREMENTS.md` and the owner decision register.

Never use a G1 context-tool test to imply M0/M1 readiness. M0 smoke checks are separate from M1 ALE resets, observation capture, control calibration, training, or Colab runtime work.

## M6 Stage 3 v2 corrective regression strategy

Stage 3 v2 is separately configured in [`m6-stage3-v2.json`](../../configs/m6/m6-stage3-v2.json); it does not replace the v1 config or historical evidence. Before its first official reset, run focused M6/episode tests, relevant M1/M4/M5 regressions, the full suite, context preflight and checkpoint-history verification; resolve both private M5 snapshots/sidecars by their exact hashes and root manifest; compare installed package versions with `uv.lock`; and construct the actual ALE instance without stepping to verify ROM, mode/difficulty, RGB/action contract, registration defaults and effective 500000-frame emulator horizon.

The focused tests must pin: v1 54000/900 versus v2 432000/1800 runner limits; exact 20-slot paired schedule and frozen policy hashes; requested versus ALE-readback episode horizon; reset counter origin and post-reset action-frame arithmetic; in-step termination/truncation; runner wall/frame/artifact/RSS stops; nonfinite/unsupported reward handling; mutually exclusive final-move censor categories; cursor correction/no-progress/ambiguity/stable-board mismatch accounting; explicit adapter timing names; streaming ledger verification; and tamper/duplicate/interruption handling. Mock tests establish software behavior only. The official v2 gate additionally requires committed clean source/config, hash-verified artifacts and v1 tree, sufficient free space, and an immutable run manifest before a real reset. Post-run aggregation must stream-verify the hash chain and independently rebuild all per-policy metrics from the retained traces. A passing test suite does not satisfy M6-04 without authoritative ALE-terminated game evidence.
