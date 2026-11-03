# Phase 2 Live Demo Guide

This demo runs the actual local ALE VideoChess environment and renders live RGB frames. It does not use a prerecorded video or substitute the Python chess simulator for Atari.

## Prerequisites

- Repository checkout and virtual environment at project root.
- Installed project dependencies, including ALE-Py 0.11.2 and Gymnasium 1.4.0.
- Atari VideoChess ROM available through ALE-Py with SHA-256 `d44f2a115393b0a6cbcd5398d62369e652f3670a9ee585883d183e740edad0f7`.
- A local graphical display with Tk available.
- Local private model artifacts from the Phase 1/2 artifact namespace.

## Recommended demonstration policy

Use the selected Phase 1 M4-A behavior-cloning checkpoint as the fallback demonstration policy. It completed all 12 configured player turns in each of the three bounded Phase 2 Atari baseline attempts, with every player move and opponent reply verified from RGB. Those attempts were incomplete at the move cap and did not observe a terminal game result.

```bash
PYTHONPATH=. .venv/bin/python -m videochess_rl.improvement.demo \
  --policy m4-a \
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
  --max-player-moves 24 \
  --max-seconds 900
```

The Q policy's three paired evaluation attempts each stopped after nine verified turns because Atari RGB did not confirm target FIRE. The runner stopped without retrying or claiming a move. The live demo can therefore end early with a visible control warning; this was observed and is a known limitation.

## Display and controls

- The left pane shows actual ALE RGB frames.
- The right pane displays policy family, checkpoint SHA, training decision count where applicable, current verified side-to-move, status, and a scrollable two-sided move history.
- SAN and UCI are shown only after the Atari controller and RGB state verifier confirm the move.
- A selected move remains marked as pending until verified. Unverified opponent responses are never fabricated.
- After the session stops, **Left** steps backward and **Right** steps forward through the captured reset and RGB-verified board states. Buttons provide the same controls.
- A runner stop, ALE terminal, incomplete game, or control warning is stated in the status area.

Verified demo smoke commands used by the Phase 2 executor:

```bash
DISPLAY=:1 PYTHONPATH=. .venv/bin/python -m videochess_rl.improvement.demo \
  --policy double-dqn --checkpoint artifacts/improvement/videochess-improvement-20261103-v1/official/attempt-0000/snapshot-250000.pt \
  --checkpoint-sha256 48dbbb860c8f997105b7bd30863892294e68ef489185ac6172fb7b459df5c293 --auto-smoke

DISPLAY=:1 PYTHONPATH=. .venv/bin/python -m videochess_rl.improvement.demo \
  --policy m4-a --auto-smoke
```

`--auto-smoke` is a bounded two-player-move live ALE run. It automatically resizes the window, generates left/right replay key events, verifies two-sided moves and a reply, writes a local `demo-verification.json`, and exits. The actual local traces and captured frames are ignored artifacts and are not part of the PR.

The previous user-owned script in Downloads was not edited or required by the repository demo.
