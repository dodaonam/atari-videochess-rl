# M01 — ALE Feasibility Plan

- **Plan ID:** M01
- **Milestone:** M1 under G2
- **Plan status:** complete (task status is canonical in `BACKLOG.yaml`)
- **Task:** `M1-001` in `.agents/tasks/BACKLOG.yaml`
- **Authorization:** `.agents/evidence/M1-authorization.md`
- **Requirements at M1 authorization (2026-10-15):** O-01 was an external-policy question and no repository course/instructor rules were found. The project owner later closed O-01 for internal planning/execution on 2026-10-27, without claiming instructor approval; any actual authoritative prohibition remains binding. Keep RGB observations as the controller's source of truth, and RAM diagnostic-only.
- **Acceptance:** M1-01 through M1-06 in [`ACCEPTANCE_CRITERIA.md`](../../docs/06-quality/ACCEPTANCE_CRITERIA.md)
- **Official runtime references:** [VideoChess environment](https://ale.farama.org/environments/video_chess/), [ALE environments](https://ale.farama.org/environments/), [Python interface](https://ale.farama.org/python-interface/)

## Objective

Demonstrate a reproducible, observation-driven interaction with real ALE/VideoChess-v5, including an Atari-executed legal move, an observed opponent response, state cross-checking, and safe desynchronization handling.

## Scope and exclusions

- Inspect the real environment under both a recorded deterministic development configuration and the default v5 configuration.
- Capture RGB and diagnostic RAM observations, action/reward/termination data, and bounded action traces.
- Implement reusable environment, vision, cursor/action, board-state, synchronization, trace, and CLI components as supported by observed behavior.
- Use `python-chess` only as a shadow validator; ALE RGB remains the gameplay source of truth.
- Keep raw frames in ignored local artifacts; commit compact sanitized evidence, hashes, and reproduction commands.
- Do not start M2–M7, train models, generate datasets, allocate Colab resources, or use Stockfish for analysis/opponent/evaluation.

## Configurations

- **Default v5:** preserve the registered `ALE/VideoChess-v5` settings and record actual mode, difficulty, observation type, action space, frameskip, and sticky-action probability.
- **Deterministic development:** explicitly set RGB observations, `frameskip=1`, and `repeat_action_probability=0.0`; seed resets and report these results as development-only.
- **RAM diagnostic:** capture and analyze separately from the RGB controller. Do not use RAM offsets or values to choose the submitted controller's actions.

## Work sequence

1. Bounded reset probes: record versions, wrappers, shapes/dtypes, action meanings, info keys, rewards, termination/truncation, game startup, and initial frames/RAM.
2. Calibrate cursor displacement, board orientation, square geometry, selection/FIRE press-release timing, frameskip, sticky actions, and opponent wait behavior.
3. Implement confidence-bearing RGB board/cursor observations and a controller that maps squares to Atari joystick/FIRE actions.
4. Test unit behavior with synthetic image fixtures, then run bounded real-ALE negative-path and closed-loop checks.
5. Attempt a fresh-reset move, preferably `e2e4` when the observed position and side-to-move support it; verify the player move and opponent reply from ALE observations before updating the shadow board.
6. Verify reward perspective, turn changes, modes/difficulty, terminal/truncation where reachable, and safe desync behavior. Preserve failures and retries.
7. Run the full suite, real ALE integrations, preflight, staged diff/secret checks, clean-clone recovery, and export a sanitized final review bundle.

## Implementation entry points

- `videochess_rl/environment.py`: ALE profiles, lifecycle, RGB frames, and separately labeled selected-byte diagnostics.
- `videochess_rl/vision.py`: calibrated RGB square counts, cursor ambiguity, observed start-layout validation, and board-window comparison.
- `videochess_rl/controller.py`: chess-legal action plans using the measured joystick/FIRE frame timing.
- `videochess_rl/shadow.py`: legal `python-chess` transitions advanced only after matching RGB evidence; no silent correction.
- `videochess_rl/demo.py` and `scripts/run_m1_demo.py`: bounded closed-loop runner and structured local trace.
- M1 test modules: `tests/test_m1_vision.py`, `tests/test_m1_control.py`, `tests/test_m1_shadow.py`, `tests/test_m1_environment.py`, and `tests/test_m1_ale_integration.py`.

The final evidence-backed M1 acceptance matrix and G2 decision are in `.agents/evidence/M1-G2-final-verification-20261016.md`; earlier M1 records remain historical. Live status is canonical in `BACKLOG.yaml` and `PROJECT_STATE.yaml`. M2 was subsequently authorized under `.agents/evidence/M2-authorization-20261016.md`; G3 remains unapproved.

## Acceptance review

Record an individual PASS / FAIL / UNVERIFIED verdict and evidence for each of M1-01 through M1-06. Do not approve G2 if any mandatory criterion remains unverified, a known assignment rule is violated, a required trace uses a mock/simulator/internal-state shortcut, or preflight/tests fail. If complete, update M1, G2, and the next M2 approval gate with evidence; otherwise retain G2 in progress and document the exact blocker.
