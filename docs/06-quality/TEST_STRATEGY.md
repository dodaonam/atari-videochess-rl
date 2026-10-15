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

`tests/test_m1_vision.py`, `tests/test_m1_control.py`, and `tests/test_m1_shadow.py` cover RGB square parsing, cursor ambiguity, measured action timing, legal shadow transitions, and safe mismatch handling. Synthetic frames are unit fixtures only; they do not count as ALE evidence.

`tests/test_m1_environment.py` and `tests/test_m1_ale_integration.py` use the real packaged VideoChess ROM. The integration checks reset/capture the actual RGB screen, execute a player move through joystick/FIRE actions, observe the computer reply from RGB, and compare the result against legal `python-chess` shadow transitions. It runs once with deterministic development settings and once with the registered v5 defaults. Neither test reads RAM to choose actions.

Run the M1 checks and bounded demo from the repository root:

```bash
uv run --locked python -m unittest tests.test_m1_vision tests.test_m1_control tests.test_m1_shadow tests.test_m1_environment tests.test_m1_ale_integration -v
uv run --locked python scripts/run_m1_demo.py --profile deterministic-dev --seed 20261015 --max-opponent-wait-frames 10000
uv run --locked python scripts/run_m1_demo.py --profile v5-default --seed 20261016 --max-opponent-wait-frames 10000
```

The runner writes JSON traces and raw RGB frames under ignored `artifacts/m1/`. Only sanitized hashes, settings, action summaries, and findings belong in version-controlled evidence. Terminal behavior is reported as unverified unless a real game-ending position is observed; an ALE API or mock termination flag is not a substitute.

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
