# M1 ALE Feasibility and Reproduction

**Historical scope:** M1 under G2. This guide covers real ALE reset/observation/control checks only; its scope statement records what that M1 work authorized and does not grant new M2+ work. At the time it was written, O-01 through O-08 were open. O-01 is now closed for internal planning/execution by the 2026-10-27 owner decision, without claiming instructor approval; see `REQUIREMENTS.md`.

## Runtime and profiles

The verified local runtime is Python 3.12.3, Gymnasium 1.4.0, and ALE-Py 0.11.2. The packaged `video_chess.bin` ROM SHA-256 is `d44f2a115393b0a6cbcd5398d62369e652f3670a9ee585883d183e740edad0f7`.

The runner keeps two configurations distinct:

| Profile | Frameskip | Sticky action probability | Use |
|---|---:|---:|---|
| `deterministic-dev` | 1 | 0.0 | Calibrate controls and reproduce exact frame timing. |
| `v5-default` | 4 | 0.25 | Preserve registered `ALE/VideoChess-v5` behavior. |

The registered environment returns RGB `(210,160,3)` `uint8`, diagnostic RAM `(128,)` `uint8`, and `Discrete(10)`. Supported modes are 0–4; supported difficulties are `[0]`. Mode 0 displays skill level 1. The [original Atari manual](https://atariage.com/manual_html_page.php?SoftwareLabelID=581) documents cursor, FIRE, player-side, and reset-switch behavior. The environment documentation lists actions 0–9 as NOOP, FIRE, UP, RIGHT, LEFT, DOWN, UPRIGHT, UPLEFT, DOWNRIGHT, and DOWNLEFT. See the [official VideoChess environment page](https://ale.farama.org/environments/video_chess/) and [ALE environments guide](https://ale.farama.org/environments/).

## RGB parser and control findings

The calibrated board occupies screen coordinates x=44–107 and y=36–171. Each square is 8 by 17 pixels. The observed piece colors are gold `(180,122,48)` and blue `(132,144,252)`. The reset cursor is at d4. The parser reports per-square color counts and treats the 19-pixel gold cursor glyph as ambiguous rather than as a chess piece. Sprite counts identify pawns, bishops, knights, and queens in the observed start layout; a 26-pixel major sprite remains ambiguous between rook and king. It does not invent a FEN when the visible occupancy disagrees with the shadow board.

Under deterministic development settings, holding a direction for 33 ALE frames moves the cursor one square. The controller now separates source selection from target confirmation: it sends a one-frame source FIRE pulse, observes the selected-piece blink, moves one square at a time, verifies each selected-piece preview at the intended target, then holds target FIRE for 16 frames and releases with NOOP. It stops if source selection or target position cannot be established from RGB, or if the selected-piece preview remains after target FIRE. It never retries an ambiguous FIRE or direction input. The shadow advances only after the existing complete RGB board checks pass.

The 16-frame target FIRE setting was selected from controlled genuine-ALE comparisons: one and four frames failed the reproduced later-turn `a2a3`; six frames completed that move but failed on a later `b2b3`; eight frames completed `b2b3` but failed on `g2g3`; 12 frames completed `g2g3` and a nine-cycle run; 16 frames completed 20 consecutive player/Atari cycles. This identifies a target-confirmation timing sensitivity but does not prove whether the ROM polls FIRE intermittently, debounces the input, or has another internal readiness condition. The full evidence and limits are recorded in `.agents/evidence/BLK-001-diagnostic-20261015.md` and its ZIP bundle.

Diagnostic RAM is kept separate. The optional diagnostic reads only selected bytes at the addresses identified in the versioned ALE wrapper; the controller and shadow-board move inference do not consume RAM. The [ALE-Py 0.11.2 VideoChess wrapper](https://github.com/Farama-Foundation/Arcade-Learning-Environment/blob/v0.11.2/src/ale/games/supported/VideoChess.cpp) maps checkmate to a white-centric reward (`+1` for black checkmate, `-1` for white checkmate). The final deterministic mode-4 campaign observed a real ALE reward of `-1.0` with `terminated=true` and `truncated=false`, reproduced from a fresh reset with the same seed. That directly verifies a white-loss terminal and its reward sign; the complementary positive reward is documented by the pinned wrapper but was not observed live.

## Real closed-loop trace

From the RGB-verified standard start, the controller navigated the cursor with Atari actions, executed `e2e3`, and observed the blue pawn on e3 with e2 empty. It then observed the gold Atari response `c7c5`; the c7 square contains the cursor overlay and c5 contains the moved pawn. A shadow `python-chess` board accepted both transitions as legal, and the resulting board occupancy matched the RGB window.

The same sequence completed under both deterministic development settings and registered v5 defaults (frameskip 4, sticky action probability 0.25), including two fresh default-profile seeds. Compact traces, frame SHA-256 values, and the full M1 verdict matrix are retained in `.agents/evidence/M1-feasibility-verification.md`. Raw PNG frames stay in the ignored `artifacts/m1/` directory and are not committed.

## Reproduction

Run inside the already-created locked project environment:

```bash
uv run --locked python scripts/run_m1_demo.py --profile deterministic-dev --seed 20261015 --max-opponent-wait-frames 10000
uv run --locked python scripts/run_m1_demo.py --profile v5-default --seed 20261016 --max-opponent-wait-frames 10000
uv run --locked python -m unittest tests.test_m1_vision tests.test_m1_control tests.test_m1_shadow tests.test_m1_environment tests.test_m1_ale_integration -v
```

The runner writes a JSON trace and its local RGB frames under `artifacts/m1/`. It uses actual environment observations to validate each move and returns a partial result if it cannot establish a stable legal transition before the frame bound. RAM diagnostics are listed separately from policy evidence.

## Stop reasons, modes, and current M1 gate

Episode traces distinguish ALE termination/truncation from runner move, frame, environment-step, wall-clock, and artifact caps, controller uncertainty at source selection/target navigation/target confirmation, board desynchronization, opponent-response timeout, rule incompatibility, and exceptions. A `runner_stopped` result is not a chess-game ending. The former 20-cycle trace reached its explicit `max_player_moves=20` limit with `terminated=false` and `truncated=false`. The former 18-cycle trace stopped safely at target confirmation on `a2a1`, also without an ALE ending. Neither reflects an Atari chess clock. The manual documents opponent thinking time and skill settings but no player move clock; emulator frames advance only when ALE is stepped. Python decision/vision processing consumes host wall time counted by the runner's wall cap, but does not itself advance emulated game frames.

The phase-confirmed 16-frame target FIRE completed 20 consecutive deterministic player/Atari cycles, including prior failing move categories; targeted traces also verified `e2e4`, `g1f3`, `f1b5`, pawn moves, and the `d3d4` / Atari `c5d4` / `d1d4` capture line. One separate v5-default run completed two cycles. The newly authorized five-episode campaign included mode 0 (12 verified cycles, runner move cap) and mode 4. In mode 4, removing an early ten-mismatch stop and requiring a legal candidate reply's source cursor allowed replies after as many as 1,221 ALE frames. A legal cooperative-loss line in mode 4 reached the authentic ALE terminal twice from fresh deterministic resets. The controller stops on uncertain transitions and never advances the shadow without full RGB board evidence.

Mode configuration was checked by resetting each supported mode 0–4 and reading the configured mode byte only as a separately labeled diagnostic. Complete gameplay and terminal behavior were observed in modes 0 and 4; modes 1–3 were reset-tested but not played through a complete reply. Difficulty is limited to 0 in the installed ALE-Py release. The terminal RGB screen is a uniform transition/game-over screen without a parseable final board. The trace records the last independently verified FEN before the unconfirmed terminal player move; the inferred `d8h4#` is disclosed as chess-rule analysis, not direct visual evidence.

The M1-04 terminal result, complete campaign accounting, evidence bundle, SHA-256 values, and final acceptance matrix are in `.agents/evidence/M1-04-terminal-verification.md` and `.agents/evidence/M1-04-experiment-campaign-20261016.md`. M1-01 through M1-06 pass and G2 is approved. M2 authorization was subsequently recorded in `.agents/evidence/M2-authorization-20261016.md`; G3 is not approved. At the time of this M1 acceptance record, O-01 through O-08 were open; current O-01 disposition is in `REQUIREMENTS.md`.

## Multi-turn reproduction and safety tests

Reproduce the verified terminal using a new, unused output path inside the locked environment:

```bash
uv run --locked --no-sync python scripts/run_m1_terminal_experiment.py --profile deterministic-dev --mode 4 --policy cooperative-loss --seed 20261017 --max-player-moves 8 --max-opponent-wait-frames 20000 --max-episode-frames 54000 --max-episode-seconds 600 --target-fire-press-frames 16 --trace artifacts/m1/m1-04/reproduction-new-path/trace.json
```

The cooperative-loss selector uses only legal `python-chess` moves and no Stockfish, model, or search engine. Each move is checked against the current legal board; the shadow advances only after RGB evidence covers the full resulting board. A failed or ambiguous control stops the episode and retains the last verified board. `tests/test_m1_episode.py` covers bounded failures, cursor displacement, terminal/truncation bookkeeping, no stepping after termination, and reward perspective with synthetic environment doubles; the independent live terminal traces establish ALE termination and reward behavior.

The M1-04 result is **PASS**: two real ALE episodes returned reward `−1.0`, `terminated=true`, `truncated=false` in mode 4. The positive reward sign was not observed live. Full RGB parsing of the final board is unavailable because the terminal transition clears the board; the runner preserves the last verified FEN and does not infer a shadow transition. G2 is **approved** after all M1 acceptance evidence and verification passed. M2 was subsequently authorized; G3 is not approved. At the time this M1 acceptance record was written, O-01 through O-08 were unresolved; see `REQUIREMENTS.md` for current approvals and the 2026-10-27 internal O-01 closure.
