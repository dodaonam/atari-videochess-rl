# Phase 2 Live Demo Guide

This demo runs the actual local ALE VideoChess environment and renders live RGB frames. It does not use a prerecorded video or substitute the Python chess simulator for Atari.

## Canonical entrypoint

Use the repository module for live sessions. It shares the audited episode runner
and checkpoint loader, retains the stop category and reason through worker
completion, writes a concise `live_summary.json`, and replays only RGB snapshots
associated with verified progress. The separate user-local viewer is preserved
for reference, but it is not the supported launch path: its final `done` event
replaced the more detailed `episode_finished` footer, and its replay builder
warned about an optional candidate frame before checking whether the move had
reached RGB confirmation.

The regular Double DQN command is:

```bash
uv run --locked --no-sync python -m videochess_rl.improvement.demo \
  --policy double-dqn \
  --checkpoint artifacts/improvement/videochess-improvement-20261103-v1/official/attempt-0000/snapshot-250000.pt \
  --checkpoint-sha256 48dbbb860c8f997105b7bd30863892294e68ef489185ac6172fb7b459df5c293 \
  --seed 20261103 \
  --max-player-moves 200 \
  --max-seconds 1800 \
  --close-on-finish
```

`--close-on-finish` is useful for unattended full-game runs. It closes the
window only after ALE ends and the trace and summary have been persisted. The
default limits remain bounded. If the runner, time, or ALE frame limit stops
the session first, the result is incomplete rather than a completed chess
game.

For a bounded live GUI check that also exercises resize and Left/Right replay,
add `--auto-smoke`; that mode deliberately limits the session to two player
moves and two Atari replies. It is a GUI integration smoke, not a full-game run.

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

## M4-A fallback policy

Use the selected Q-only Double DQN checkpoint for the improved-policy demo.
Its identity is checked against the required SHA-256 before loading. The
earlier M4-A behavior-cloning checkpoint remains available as a separately
labeled fallback; its historical bounded turns are not evidence for the
Double DQN policy or for a complete game.

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
uv run --locked --no-sync python -m videochess_rl.improvement.demo \
  --policy double-dqn \
  --checkpoint artifacts/improvement/videochess-improvement-20261103-v1/official/attempt-0000/snapshot-250000.pt \
  --checkpoint-sha256 48dbbb860c8f997105b7bd30863892294e68ef489185ac6172fb7b459df5c293 \
  --seed 20261103 \
  --max-player-moves 200 \
  --max-seconds 1800
```

The historical `h1h4` stop was reproduced and traced to target FIRE being held
for 16 ALE frames when the ROM acknowledged that particular capture only on
held frame 22. A RAM probe was validated against the exact bundled ROM and
multiple RGB-verified positions. The controller now requires the source and
target preview to be independently confirmed, holds one target FIRE press for
up to 32 frames, and releases as soon as ALE reports the matching move-search
state. It never retries FIRE. Acknowledgement alone does not advance the chess
shadow: a complete RGB board transition and the Atari reply are still required.

The pinned VideoChess ROM also exposes a terminal blue screen after some
checkmates, with no usable final chessboard image. In that case, the final
pending player move and Atari reply are recorded separately as terminal-RAM
verified only when actual ALE termination, the exact full RAM board, one
unique legal reply, checkmate, and matching ALE reward all agree. The terminal
screen is kept as terminal evidence and is not rendered as a fabricated
board snapshot. RGB and terminal-RAM move counts remain separate in the GUI,
trace, and summary.

## Display and controls

- The left pane shows actual ALE RGB frames.
- The fixed-width right pane displays policy family, checkpoint SHA, training decision count where applicable, current verified side-to-move, active session limits, separate terminal/trace status, and a scrollable White/Black move scorecard. This layout follows the owner-provided local presentation reference; that script is not modified or required.
- A policy selection is visibly pending until its Atari transition is verified. At session end, an unconfirmed selection is labeled unverified and receives no replay snapshot. Terminal-RAM verified moves are labeled separately and do not gain fabricated RGB snapshots.
- Once a complete player/Atari transition is RGB-verified, **Left** and **Right** step through the captured White candidate and Atari reply frames. If the candidate was only cursor-masked at the time, the viewer labels it as a candidate whose transition was confirmed by the later full-board evidence. Buttons provide the same controls.
- The GUI keeps White and Black move columns separate. Ordinary Atari replies are recorded only after RGB evidence identifies them. A terminal reply without a usable final board frame is labeled terminal-RAM verified only under the strict checkmate contract above; missing replies remain unverified.
- Session lifecycle status, primary stop reason, terminal category, and trace
  persistence are displayed independently. A trace-save notification cannot
  overwrite a controller/game outcome. Worker failures close automated smoke
  mode and return a nonzero status even when no trace exists.
- The console and `live_summary.json` retain the outcome class, exact runner
  stop category and reason, incomplete-move fields, ALE terminal/truncation
  flags, attempted and verified counts, checkpoint hash, model training seed,
  and ALE reset seed. The summary contains no frame arrays or move-level trace.
- Replay artifact diagnostics classify an absent optional candidate for an
  unverified move as `INFO`, a missing image for a verified move as `WARNING`,
  and a conflict between trace verification and artifacts as `ERROR`. No
  synthetic verified snapshot is created; replay errors also fail auto-smoke.
- The live panel reports the player-move cap, wall-clock cap, runner frame and
  step caps, observed ALE frame horizon, opponent response timeout, and local
  artifact cap. The current ALE profile reports 108,000 frames; the runner's
  150,000-frame ceiling does not override it. ALE truncation is incomplete,
  never a chess win/loss/draw.
- A runner stop, ALE termination, ALE truncation, cancellation, incomplete
  game, or controller warning is stated without inventing a result. A terminal
  reward by itself is not labeled checkmate; the terminal board must also
  match a legal checkmating sequence.
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
  --checkpoint-sha256 48dbbb860c8f997105b7bd30863892294e68ef489185ac6172fb7b459df5c293 \
  --seed 20261103 --auto-smoke

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
