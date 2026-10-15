# Atari Chess-Move Action Adapter

**Status:** The M1 move-to-joystick/FIRE adapter and phase-specific RGB checks are implemented. M6 learned-policy integration and broader special-move support are proposed and untested.

**Purpose:** Document how a semantic chess move is translated into real Atari actions and what evidence is required before a shadow transition is accepted.

## Interface and conversion

[plan_move()](../../videochess_rl/controller.py) accepts an observed cursor square, a UCI move, a python-chess Board and optional ControllerTiming. It rejects malformed or currently illegal moves. It returns a sequence of ActionFrame entries: ALE action ID, requested ALE-frame duration and a semantic input phase. It is a plan, not proof that the Atari accepted the move.

The action IDs are NOOP 0, FIRE 1, UP 2, RIGHT 3, LEFT 4, DOWN 5, UPRIGHT 6, UPLEFT 7, DOWNRIGHT 8 and DOWNLEFT 9. The controller maps source/target squares to joystick routes. The episode runner does not blindly execute the whole plan: it checks RGB after each cursor step and recomputes the route from the observed cursor if the Atari moved somewhere unexpected.

## Verified M1 phase sequence

1. **Player turn and source navigation:** Require a stable RGB board compatible with the last verified shadow and one identifiable cursor. Navigate one square at a time. After each directional action and release, observe cursor and board again. Two no-progress actions or unresolved board/cursor evidence stop the input.
2. **Source cursor:** Settle for 33 ALE frames and verify the cursor is on the source with the expected board.
3. **Source selection:** Press FIRE once for 1 ALE frame, release with NOOP for 1 frame, and observe the selected-piece blink in a 33-frame window under frameskip 1. When frameskip is greater than 1, the runner uses a 66-frame observation window. If selection is not visible, stop before target movement.
4. **Selected-target navigation:** Send one directional action at a time, each using the calibrated 33-frame hold followed by 1 NOOP release. Observe the blinking selected piece at its intended target. A failed preview stops before the next action; it does not retry the direction blindly.
5. **Target confirmation:** Only after source selection and target preview are both verified, press FIRE for the calibrated 16 ALE frames and release with 1 NOOP frame.
6. **Player transition verification:** Observe a complete candidate board. If the selected-piece preview remains at source and target, classify target confirmation as uncertain and do not press FIRE again. If no legal candidate transition appears or RGB is contradictory, stop without advancing the shadow.
7. **Atari handoff:** Wait within the configured opponent-frame bound. Infer a legal one-move candidate from stable RGB, require the expected Atari cursor at the move source and a repeated stable candidate, then gather full-board evidence with cursor coverage at a second square. Only then commit the player move and Atari reply atomically to the shadow.

The phase/state trace is implemented in [episode.py](../../videochess_rl/episode.py). The shadow commit boundary is in [shadow.py](../../videochess_rl/shadow.py); occupancy parsing is in [vision.py](../../videochess_rl/vision.py).

## Current calibrated timing and profile effects

| Control item | Current recorded setting | Meaning and limit |
|---|---:|---|
| Direction hold | 33 ALE frames | One-square movement calibrated in deterministic-dev. |
| Source FIRE | 1 ALE frame | Short source-selection pulse, followed by RGB blink verification. |
| Target FIRE | 16 ALE frames | Measured target-confirmation profile used by the final long run and terminal replay. It is not proven universally optimal. |
| FIRE/direction release | 1 ALE frame NOOP | Creates an explicit button/action release boundary. |
| Pre-source settle | 33 ALE frames | Allows stable cursor/board observation before source press. |
| Selection/target observation | 33 ALE frames at frameskip 1; 66 requested frames when frameskip >1 | Temporal RGB sampling advances ALE and is part of episode cost. |

With frameskip 4, requested ALE-frame durations are rounded to environment steps; a configured hold is not a promise of exact single-frame button timing. Sticky-action probability 0.25 in v5 defaults can repeat a prior action. The M1 terminal replay used deterministic-dev with frameskip 1 and stickiness 0. It does not demonstrate that the same timing has identical reliability in every profile, mode or seed.

Earlier controlled observations showed that very short target FIRE holds often failed at target confirmation, while longer holds improved observed progress in those trials. That is timing correlation, not proof of ROM polling/debounce internals. The final M1 evidence uses 16 frames; no claim is made that 16 is universally optimal.

## Uncertainty, recovery and special moves

- Never equate sending FIRE with selecting or completing a move. Use the source blink, target preview and resulting board as distinct evidence.
- Never repeat a potentially accepted action while the board is unknown. Stop and retain the last verified state unless a tested observation proves a retry safe.
- If the cursor is displaced, derive a new route from the measured RGB cursor rather than continuing the stale route.
- If the legal shadow transition disagrees with RGB, raise desynchronization and preserve the prior board.
- Opponent reply time is a bounded ALE-frame wait; host computation time and ALE frame advancement are recorded separately.
- M1 demonstrates ordinary moves and captures on the cited runs. It does not establish robust castling, en passant, promotion, all Atari animation states, or standard-chess draw-rule parity. Those require separate real ALE evidence before M6 relies on them.
- ALE termination during any action or opponent thinking is captured from the actual step return; no further input is sent. The terminal RGB may not contain a parseable board.

## M6 integration contract

The learned policy must provide a semantic legal chess move from an ALE-derived, validated state. The adapter accepts that move only when it remains legal in the current validated state, runs the observed control phases, and returns one of: fully RGB-verified transition, genuine ALE terminated/truncated result, or a typed uncertain/desynchronized stop with the last verified board and input phase. It must not advance state from model output, simulator state or diagnostic RAM.

This proposed contract calls the M1 controller; it does not add the M6 policy interface or change current code.

## References

- [controller.py](../../videochess_rl/controller.py), [episode.py](../../videochess_rl/episode.py)
- [Controller tests](../../tests/test_m1_control.py), [episode tests](../../tests/test_m1_episode.py), [ALE integration tests](../../tests/test_m1_ale_integration.py)
- [M1 timing and runtime evidence](../../.agents/evidence/M1-G2-final-verification-20261016.md)
- [M1 environment specification](ALE_ENVIRONMENT.md), [board extraction specification](BOARD_EXTRACTION.md)
