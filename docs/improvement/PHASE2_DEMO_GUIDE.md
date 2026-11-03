# Phase 2 Live Demo Guide

This demo runs the actual local ALE VideoChess environment and renders live RGB frames. It does not use a prerecorded video or substitute the Python chess simulator for Atari.

## Prerequisites

- Repository checkout and virtual environment at project root.
- Installed project dependencies, including ALE-Py 0.11.2 and Gymnasium 1.4.0.
- Atari VideoChess ROM available through ALE-Py with SHA-256 `d44f2a115393b0a6cbcd5398d62369e652f3670a9ee585883d183e740edad0f7`.
- A local graphical display with Tk available.
- Local private model artifacts from the Phase 1/2 artifact namespace.

Before launching the GUI, run the preflight. It checks the active Python
environment, importable runtime packages, ALE/Gymnasium compatibility, exact
ROM identity, supported action/RGB contract, Tk display, selected checkpoint
hash and metadata, available RAM/disk, and artifact-directory writability. It
constructs and closes the environment without resetting or stepping it.
Stockfish is not required for either demo policy.

```bash
DISPLAY=:1 PYTHONPATH=. .venv/bin/python -m videochess_rl.improvement.demo \
  --policy double-dqn \
  --checkpoint artifacts/improvement/videochess-improvement-20261103-v1/official/attempt-0000/snapshot-250000.pt \
  --checkpoint-sha256 48dbbb860c8f997105b7bd30863892294e68ef489185ac6172fb7b459df5c293 \
  --reset-seed 123456 --preflight-only
```

Use `--policy m4-a --reset-seed 123456 --preflight-only` to check the M4-A
fallback. A failed check prints the observed condition, expectation, and a
corrective action, then exits nonzero.

The default reset seed is `20261103`. `--seed` remains an alias for
`--reset-seed`. This seed controls the Atari reset and the policy adapter's
session RNG; it is never compared with the immutable checkpoint training
seed. The GUI displays both values separately. Both selected models were
loaded and smoke-tested using reset seed `123456`; the unchanged model training
seed shown in the GUI was `20261103`.

## Recommended demonstration policy

Use the selected Phase 1 M4-A behavior-cloning checkpoint as the fallback demonstration policy. It completed all 12 configured player turns in each of the three bounded Phase 2 Atari baseline attempts, with every player move and opponent reply verified from RGB. Those attempts were incomplete at the move cap and did not observe a terminal game result.

```bash
PYTHONPATH=. .venv/bin/python -m videochess_rl.improvement.demo \
  --policy m4-a \
  --seed 20261103 \
  --max-player-moves 24 \
  --max-seconds 900
```

M4-A checkpoint SHA-256: `cf5e437ff4e2d6a8e85739df751dec33f16b7bc4c92268f996ec4c612d62feed`.

## Selected Double DQN policy

To demonstrate the selected Q-only snapshot, provide its exact local path and digest. The GUI labels it `double_dqn_250000` and explicitly identifies it as Double DQN.

```bash
PYTHONPATH=. .venv/bin/python -m videochess_rl.improvement.demo \
  --policy double-dqn \
  --checkpoint artifacts/improvement/videochess-improvement-20261103-v1/official/attempt-0000/snapshot-250000.pt \
  --checkpoint-sha256 48dbbb860c8f997105b7bd30863892294e68ef489185ac6172fb7b459df5c293 \
  --seed 20261103 \
  --max-player-moves 24 \
  --max-seconds 900
```

The Q policy's three paired evaluation attempts each stopped after nine verified turns because Atari RGB did not confirm target FIRE. The runner stopped without retrying or claiming a move. The live demo can therefore end early with a visible control warning; this was observed and is a known limitation.

The historical target-confirmation issue was not “fixed” by accepting an
unverified transition or retrying FIRE. An isolated diagnostic with a single
one-frame target FIRE press reached four RGB-verified player moves, then also
stopped on target-confirmation uncertainty at a different legal move. This
does not establish that press duration caused the historical failure. The
controller remains conservative: the shadow position advances only after RGB
verification, and an uncertain capture is left pending with no retry. The
private diagnostic trace and frames remain local.

## Display and controls

- The left pane shows actual ALE RGB frames.
- The fixed-width right pane displays policy family, checkpoint SHA, training decision count where applicable, current verified side-to-move, active session limits, separate terminal/trace status, and a scrollable White/Black move scorecard. This layout follows the owner-provided local presentation reference; that script is not modified or required.
- SAN and UCI are shown only after the Atari controller and RGB state verifier confirm the move.
- A selected move remains marked as pending until verified. Unverified opponent responses are never fabricated.
- After the session stops, **Left** steps backward and **Right** steps forward through the captured reset and RGB-verified board states. Buttons provide the same controls.
- Session lifecycle status, primary stop reason, terminal category, and trace
  persistence are displayed independently. A trace-save notification cannot
  overwrite a controller/game outcome. Worker failures close automated smoke
  mode and return a nonzero status even when no trace exists.
- The live panel reports the player-move cap, wall-clock cap, runner frame and
  step caps, observed ALE frame horizon, opponent response timeout, and local
  artifact cap. The current ALE profile reports 108,000 frames; the runner's
  150,000-frame ceiling does not override it. ALE truncation is incomplete,
  never a chess win/loss/draw.
- A runner stop, ALE termination, ALE truncation, cancellation, incomplete
  game, or controller warning is stated without inventing a result.
- Each session gets an atomically-created unique artifact directory; existing
  session records are never overwritten.
- The responsive layout was checked at 1100×680 during real-ALE smoke and at
  the 980×640 minimum with a long controller warning. The sidebar does not
  cover the board; labels and the move scorecard stay within their pane. The
  scorecard scrolls vertically when fewer rows fit.

Verified demo smoke commands used by the Phase 2 executor:

```bash
DISPLAY=:1 PYTHONPATH=. .venv/bin/python -m videochess_rl.improvement.demo \
  --policy double-dqn --checkpoint artifacts/improvement/videochess-improvement-20261103-v1/official/attempt-0000/snapshot-250000.pt \
  --checkpoint-sha256 48dbbb860c8f997105b7bd30863892294e68ef489185ac6172fb7b459df5c293 --auto-smoke

DISPLAY=:1 PYTHONPATH=. .venv/bin/python -m videochess_rl.improvement.demo \
  --policy m4-a --auto-smoke
```

`--auto-smoke` is a bounded two-player-move live ALE run. It passes only when the authoritative trace records the exact `RUNNER_MAX_PLAYER_MOVES` stop after two RGB-verified player moves and two RGB-verified Atari replies; the GUI terminal event and displayed move counts agree with that trace; no move is pending; the worker completed and saved the trace; and resize/layout plus Left/Right replay checks pass. A worker that returned normally, a saved trace, or usable replay is not by itself a successful smoke.

The verification record includes `SMOKE_PASS`, `SMOKE_INCOMPLETE`, or
`SMOKE_RUNTIME_FAILURE`, the requested and verified counts, terminal category,
stop reason, worker and trace status, replay/layout results, and failed
acceptance conditions. `SMOKE_PASS` exits 0. An incomplete gameplay exercise
exits 2; malformed/missing or internally inconsistent verification evidence
exits 4. Preflight failures remain exit 3 and GUI initialization failures exit
5. Controller uncertainty, timeout, ALE termination/truncation, cancellation,
or any stop other than the expected two-move runner cap remains incomplete;
the controller continues to fail closed without advancing an unverified move
or retrying FIRE. When frames permit, an incomplete run still tests and retains
replay. The private trace is cross-checked after GUI shutdown, so replay or a
worker completion cannot override the episode result.

PM25-F01 regression verification reproduced the former permissive predicate:
one verified player/reply pair, a pending uncertain second action, a saved
trace, successful replay/layout checks, and a GUI-side zero return would have
passed the old CLI check. The corrected CLI returns nonzero and records
`SMOKE_INCOMPLETE`. A deterministic two-pair runner-cap fixture returns 0.
Bounded real-ALE runs at reset seed `123456` also passed for the selected Q-only
Double DQN and M4-A policies, each with exactly two verified player moves and
two replies. Neither observed a terminal chess result; these remain bounded
smoke checks, not full games or scientific evaluation.

On the verified environment, custom-reset-seed `123456` smoke runs succeeded
for both the selected `double_dqn_250000` Q-only snapshot and M4-A. Each showed
two RGB-verified player turns and two Atari replies, resizing, and successful
Left/Right replay key stepping. These are bounded UI/integration checks, not
full games or additional scientific evaluation attempts.

The previous user-owned script in Downloads was not edited or required by the repository demo.

## Review remediation note

The bounded custom-seed smoke also verified two player turns, two opponent
replies, resizing, replay in both directions, and clean exit. Its detailed
trace and frames remain private. See
[`PM24_REMEDIATION.md`](PM24_REMEDIATION.md) for the review finding ledger.
