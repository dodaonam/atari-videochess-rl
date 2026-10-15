# ALE VideoChess Environment

**Status:** M1 environment behavior is implemented and verified on the cited profiles. This is a record of measured M1 behavior, not a claim that every mode, special move or configuration has been evaluated.

**Purpose:** Record the real ALE/Gymnasium interface and its limits for future integration. Chess simulator contracts are in [MDP_SPEC.md](MDP_SPEC.md).

## Environment identity and wrapper

- **Registered ID:** ALE/VideoChess-v5.
- **Gymnasium:** constructs/resets/steps the environment and exposes the Gymnasium observation/action spaces and returned reward, terminated, truncated and info values.
- **ALE-Py:** registers the ALE environments, provides the Atari emulator and runtime accessors for frame number, mode/difficulty, RAM and packaged ROM.
- **ROM:** video_chess.bin, SHA-256 d44f2a115393b0a6cbcd5398d62369e652f3670a9ee585883d183e740edad0f7.
- **Verified M1 runtime:** Python 3.12.3, Gymnasium 1.4.0, ALE-Py 0.11.2.
- **RGB observation:** NumPy uint8, shape (210, 160, 3).
- **Diagnostic RAM:** NumPy uint8, shape (128,). The wrapper exposes selected reads through diagnostic_ram(); they are separately labeled and do not drive controller actions, move inference or shadow updates.
- **Action space:** Discrete(10). IDs are 0 NOOP, 1 FIRE, 2 UP, 3 RIGHT, 4 LEFT, 5 DOWN, 6 UPRIGHT, 7 UPLEFT, 8 DOWNRIGHT and 9 DOWNLEFT.

The current wrapper is [environment.py](../../videochess_rl/environment.py). It copies returned RGB, preserves ALE reward and flags, records episode frame number and gathers runtime metadata including package versions, ROM hash, registered defaults and available mode/difficulty values.

## Profiles and runtime settings

| Profile | Frameskip | Sticky-action probability | Use and evidence |
|---|---:|---:|---|
| deterministic-dev | 1 | 0.0 | Low-variability calibration and replay. Development evidence only. |
| Registered v5 defaults | 4 | 0.25 | Actual registered profile; M1 reset and short gameplay observations exist. No claim of default-profile terminal verification. |

The wrapper accepts mode 0–4 and difficulty 0 under the pinned ALE-Py version. The environment reports mode values [0,1,2,3,4] and difficulty [0]. A valid mode is selected through environment construction/reset options; no RAM or hidden-state change is used. Mode 4 produced the M1 terminal evidence. Modes 0–4 were reset/configuration checked; the terminal campaign did not test all modes to completion.

## Frames, steps and time

- An ALE frame is an emulated Atari video frame. The wrapper’s frame_number comes from ALE getEpisodeFrameNumber().
- An environment step is one Gymnasium env.step(action) call. With frameskip 1, one step advances one emulated frame. With frameskip 4, one chosen action is applied for the configured repeated frame interval; sticky actions may repeat a prior action according to the probability.
- The M1 runner converts requested ALE-frame durations to environment steps using the configured frameskip and records actual ALE frame deltas and environment steps separately.
- Wall-clock time includes Python vision, chess selection, trace serialization and all other host-side work measured by the runner. Python computation without env.step does not itself advance ALE frames. Host wall time is not an Atari chess clock.

The deterministic M1 terminal runs recorded frame number 4,613 and environment step 4,609, showing why the two counters must be retained independently. The runner has explicit per-episode wall, frame, step, move, opponent-wait and artifact limits. Reaching a runner limit is not an ALE game ending.

## Reset, step and terminal lifecycle

VideoChessEnv.reset(seed=...) returns the actual RGB observation, reset info, frame number, reward 0 and false ALE flags. A stable standard start and cursor are checked against RGB before a game proceeds. Each VideoChessEnv.step(action) returns ALE’s actual observation, reward, terminated and truncated values without chess-side substitution.

episode.py captures every step reward and both flags before continuing its control logic. A real terminal/truncation stops further input. The trace records the terminal phase, last frame, environment step, actual reward event, RGB hash, terminal RGB and pre-terminal RGB where available. The M1 tests cover termination during input/Atari thinking and no stepping after terminal. Runner stops carry their own category and reason.

## Mode, turn and opponent readiness

M1 experiments used White as the controlled player. The runner establishes the turn from stable RGB occupancy, cursor and the last verified shadow state. It detects an opponent response by matching the observed screen to a unique legal one-move transition, requiring a stable repeated candidate and RGB cursor evidence at the inferred source, then uses full-board coverage with the cursor at multiple positions.

Atari thinking can take many emulated frames. In M1 mode 4, observed replies took hundreds to over a thousand frames in the recorded runs; the corrected bounded wait allows up to the configured limit. These observations do not establish a general upper bound for every mode or seed. Diagnostic RAM can be sampled for investigation, but turn detection and action selection remain RGB-driven.

The original 1979 manual and versioned ALE wrapper are linked from the [M1 reproduction guide](../05-operations/M1-ALE-REPRODUCIBILITY.md). Do not infer a human move clock from a runner stop or from Python wall time. Record actual API flags and stop category for each episode.

## Reward perspective and terminal evidence

The pinned ALE VideoChess wrapper defines rewards from White’s perspective: positive when Black is checkmated and negative when White is checkmated. M1 implemented agent-color conversion separately. The final M1 campaign produced two fresh deterministic mode-4 terminal observations with reward −1.0, terminated=true, truncated=false, seed 20261017, difficulty 0, frameskip 1 and sticky-action probability 0.0. Both occurred at ALE frame 4,613 / environment step 4,609 and shared terminal-screen RGB hash 024b23b1c9295ba28cf1c8dd716934262a5d5eabade513eaf96a95c03cd4809c.

This directly verifies a White-perspective loss reward and genuine ALE termination for that recorded scenario. The +1 reward sign is documented by the versioned wrapper but was not observed live. The final transition screen clears the board; the final board is not RGB-parseable. The runner retains the last independently verified FEN and does not advance its shadow for the attempted, unconfirmed move. See the [M1/G2 final verification](../../.agents/evidence/M1-G2-final-verification-20261016.md) and [terminal evidence README](../../.agents/evidence/M1-04-terminal-success-20261016-README.md).

Gymnasium terminated means the ALE environment reported its game-ending condition. Truncated is an environment time-limit or other external wrapper truncation signal. A project runner limit, controller uncertainty or user interruption is a separate stop, even when both ALE flags are false. Never replace these flags with python-chess outcome.

## Limitations and M6 boundary

- The live terminal replay is deterministic-dev only and confirms only the negative White-perspective reward sign.
- No terminal event was verified under registered v5 defaults; default-profile evidence is short gameplay only.
- Mode 4 terminal behavior has two same-seed replays, not broad seed/mode robustness.
- The terminal board image is not parseable; the last pre-terminal FEN is the last verified chess state.
- The controller was exercised on ordinary moves and captures; M1 does not establish castling, en passant, promotion, or parity for all chess draw rules.
- The package’s mode/difficulty restrictions reflect ALE-Py 0.11.2 and must be recorded if versions change.

For M6, retain this real environment as the execution backend. A learned policy may propose a semantic legal chess move from an ALE-validated state; the existing controller converts it to actions, and RGB must confirm the result. Simulator reward or termination must never be passed off as an ALE event.

## References

- [M1 reproduction guide](../05-operations/M1-ALE-REPRODUCIBILITY.md)
- [M1 acceptance and terminal report](../../.agents/evidence/M1-G2-final-verification-20261016.md)
- [ALE VideoChess wrapper at ALE-Py 0.11.2](https://github.com/Farama-Foundation/Arcade-Learning-Environment/blob/v0.11.2/src/ale/games/supported/VideoChess.cpp)
- [Official ALE VideoChess page](https://ale.farama.org/environments/video_chess/)
