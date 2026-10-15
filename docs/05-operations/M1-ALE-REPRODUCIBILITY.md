# M1 ALE Feasibility and Reproduction

**Scope:** M1 under G2. This guide covers real ALE reset/observation/control checks only. It does not authorize M2+, RL training, datasets, Stockfish search, Colab access, or GPU use. O-01 through O-08 remain open.

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

Under deterministic development settings, holding a direction for 33 ALE frames moves the cursor one square. The measured move plan uses a one-frame FIRE pulse after a 33-frame neutral settle, releases FIRE with NOOP, then moves the selected pawn and uses another settled one-frame FIRE pulse. The controller checks RGB before advancing `python-chess` state. Directional input that produces no RGB change stops the planned sequence.

Diagnostic RAM is kept separate. The optional diagnostic reads only selected bytes at the addresses identified in the versioned ALE wrapper; the controller and shadow-board move inference do not consume RAM. The [ALE-Py 0.11.2 VideoChess wrapper](https://github.com/Farama-Foundation/Arcade-Learning-Environment/blob/v0.11.2/src/ale/games/supported/VideoChess.cpp) maps checkmate to a white-centric reward (`+1` for black checkmate, `-1` for white checkmate). The bounded real runs observed only zero reward and no termination/truncation, so this reward sign and terminal outcome were not independently demonstrated in live play.

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

## Limitations and M1 gate

The two-ply interaction verifies reset, RGB geometry, cursor movement, FIRE timing, a player move, an Atari reply, and RGB-to-shadow synchronization. The observed games did not end, so live checkmate reward perspective and terminal/truncation behavior remain unverified. M1-04 therefore remains **UNVERIFIED**, G2 stays **in progress**, and the conditional G2 approval is not exercised. M1 status remains in progress until terminal/reward evidence is available or the acceptance record explicitly retains this limitation.
