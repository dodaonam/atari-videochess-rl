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

M2 implementation tests have not been created or run. When M2 is explicitly authorized, keep rule logic in python-chess and use distinct unit, simulator-integration, seeded-episode and benchmark evidence:

| Layer | Required checks | Expected evidence |
|---|---|---|
| State and serialization unit tests | Deterministic semantic state identity; FEN parse/serialize round trip and normalization; preserve side to move, castling rights, en passant square, halfmove clock and move history needed for repetition. Compare full-history restores with claim and automatic draw behavior. | Test output plus representative before/after state records. FEN alone must not be treated as repetition history. |
| Legal action unit tests | Generated candidates equal python-chess legal moves; legal mask exactly matches candidates; illegal candidates are masked/rejected; deterministic semantic keys do not depend on legal-list ordering. | Candidate/key/mask test fixtures and negative-path state-unchanged checks. |
| Action conversion tests | Encode/decode round trip for ordinary moves, castling, en passant, queen/rook/bishop/knight promotions, `CLAIM_DRAW_NOW` and `CLAIM_DRAW_AFTER(move)`. Test claim eligibility, announced-move legality, claim-basis records, collisions and candidate reordering. If a fixed vocabulary is selected, test its full legal mapping and invalid-ID rejection. | Exact mapping and claim assertions with retained fixture positions; invalid claims leave the Board unchanged. |
| Rule/transition unit tests | Apply ordinary moves, captures, castling, en passant and promotions; verify resulting Board, side to move, clocks and rights. Cover check, checkmate, stalemate, insufficient material, fivefold repetition, seventy-five-move automatic draw, current-position threefold/fifty-move claims and claims based on a legal announced move under the chosen claim-action contract. | Deterministic python-chess position fixtures, claim-basis traces and reason-specific outcome assertions. |
| Simulator integration tests | Agent move followed by opponent response; terminal after agent action skips opponent; terminal after opponent response returns without another agent step; rewards use the agent-color perspective for both colors; invalid action preserves state; truncation is distinct from terminal and retains a valid final observation. | Complete transition records with agent move, opponent move, reward, terminated/truncated and result reason. |
| Seeded episode tests | Same seed, color, opponent identity/configuration and initial position reproduce action/outcome records. Different colors are tested without sign inversion errors. Random-legal and heuristic selectors choose only legal actions and run bounded complete games. | Episode traces with seed, policy versions, colors, moves, final result and truncation count. Incomplete games are not counted as complete. |
| Benchmark/tournament evidence | Run random-legal and heuristic baselines against identified opponents under a recorded color/seed schedule. Record W/D/L, game lengths, completion/truncation counts, policy/opponent identity, config and source revision. | Per-game data and an aggregate summary; no unsupported Elo claim or uncalibrated rating. |
| Metric separation checks | Ensure simulator result records have an explicit simulator identity and are not merged into ALE W/D/L, ALE reward, or terminal metrics. | Schema/aggregation tests and report review showing simulator and ALE evidence separately. |

M2 acceptance evidence maps to M2-01 through M2-04 in [ACCEPTANCE_CRITERIA.md](ACCEPTANCE_CRITERIA.md). The detailed contracts and provisional choices are in [MDP_SPEC.md](../03-technical/MDP_SPEC.md); action/perspective review is pending in [ADR-0002](../02-management/decisions/ADR-0002-chess-mdp-action-and-perspective.md). Do not treat this test design as an M2 result.

## Future project test layers

| Layer | Examples | Run when |
|---|---|---|
| Unit | Board encoding, reward sign, legal move selection, Bellman targets, serialization | Every relevant code change. |
| Simulator integration | Chess rules, agent/opponent transitions, terminal and truncation behavior | M2–M5 changes. |
| ALE integration | Real reset/observation, cursor/FIRE calibration, move execution, turn detection, board cross-check, reward, terminal, desync | M1/M6 changes; requires authorized ALE runtime. |
| Data integrity | Teacher score perspective, split leakage, provenance, hashes | M3/M4 changes. |
| Training/evaluation | Reproducible pretraining/RL runs, fixed opponent pools/seeds, checkpoints, raw metrics | Only after the relevant milestone and compute authorization. |
| Delivery/recovery | Fresh-session handoff, artifact references, end-to-end reproduction | G1 and M7 gates. |

Never use a G1 context-tool test to imply M0/M1 readiness. M0 smoke checks are separate from M1 ALE resets, observation capture, control calibration, training, or Colab runtime work.
