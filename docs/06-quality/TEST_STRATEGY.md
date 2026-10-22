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
python -m unittest discover -s tests -p 'test_pre_m4_contracts.py' -v
```

These tests establish synthetic contract behavior; they do not revalidate the unavailable real M3 release or establish M4/M5 learning performance. The proposed M4 model and full experiment gates remain in [MODEL_DESIGN.md](../03-technical/MODEL_DESIGN.md) and [TRAINING_PROTOCOL.md](../04-research/TRAINING_PROTOCOL.md).

## Future project test layers

| Layer | Examples | Run when |
|---|---|---|
| Unit | Board encoding, reward sign, legal move selection, Bellman targets, serialization | Every relevant code change. |
| Simulator integration | Chess rules, agent/opponent transitions, terminal and truncation behavior | M2–M5 changes. |
| ALE integration | Real reset/observation, cursor/FIRE calibration, move execution, turn detection, board cross-check, reward, terminal, desync | M1/M6 changes; requires authorized ALE runtime. |
| Data integrity | Teacher score perspective, split leakage, provenance, hashes | M3/M4 changes. |
| Training/evaluation | Reproducible pretraining/RL runs, fixed opponent pools/seeds, checkpoints, raw metrics | Only after the relevant milestone and compute authorization. |
| Delivery/recovery | Fresh-session handoff, artifact references, end-to-end reproduction | G1 and M7 gates. |

## Pull request CI boundary

The bounded workflow in .github/workflows/preflight.yml runs on pull requests targeting initial-idea. It uses pinned GitHub-maintained actions, read-only repository permissions, Python 3.12, agent preflight, and the standard-library context/review-bundle test modules. It installs no project dependencies, downloads no dataset, launches no Stockfish search, allocates no GPU, and runs no ALE gameplay. Its coverage protects governance, links, checkpoint/recovery behavior, and review-bundle safety; it is not a replacement for the locked full suite or M1/M2 integration tests. Checkout fetches full Git history because a recovery fixture reconstructs the recorded G1 baseline revision.

The workflow does not configure branch protection or a mandatory status check. GitHub Actions execution is limited to the standard public-repository runner. Review actual PR check results before merge; no local run can claim a remote workflow passed.

## M3 data integrity tests

The Pre-M3 synthetic contract vectors in `tests/fixtures/pre_m3_identity_vectors.json` are exercised by `tests/test_pre_m3_contracts.py`. They verify deterministic identity hashes, board signature versus replay-state identity (clocks, repetition, castling, en passant, and transposition), source-game versus normalized-game identity when headers differ, promotion UCI identity, game-group split assignment, candidate inheritance/purge, and detection of a collapsed holdout. This tiny oracle is not a production parser or dataset implementation.

When M3 is separately authorized, add focused synthetic PGN fixtures and implementation tests in line with [DATASET_SPEC.md](../04-research/DATASET_SPEC.md). Cover source/hash approval gates, archive/member byte and path caps, PGN streaming/quarantine, standard-chess replay, game-reference/history reconstruction, stable legal UCI candidates, played-move legality, perspective conversion, deterministic sampling/splits, exact board overlap audits, teacher score/MultiPV/mate semantics, output manifests, and interrupted-run recovery. Candidate/teacher rows must inherit their parent sample's split and be purged with it. Fixtures must be authored, synthetic, and contain no downloaded public games or player identities.

Current canonical M3-02 requires an authorized real bounded Stockfish 19 run. Fake-UCI and configuration tests are necessary contract checks but do not pass M3-02; a PGN-only output is an intermediate artifact. The real engine run and any data acquisition remain gated by the source, assignment, and teacher approvals in `REQUIREMENTS.md`.

Never use a G1 context-tool test to imply M0/M1 readiness. M0 smoke checks are separate from M1 ALE resets, observation capture, control calibration, training, or Colab runtime work.
