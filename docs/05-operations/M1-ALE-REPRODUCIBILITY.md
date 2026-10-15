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

Under deterministic development settings, holding a direction for 33 ALE frames moves the cursor one square. The controller now separates source selection from target confirmation: it sends a one-frame source FIRE pulse, observes the selected-piece blink, moves one square at a time, verifies each selected-piece preview at the intended target, then holds target FIRE for 16 frames and releases with NOOP. It stops if source selection or target position cannot be established from RGB, or if the selected-piece preview remains after target FIRE. It never retries an ambiguous FIRE or direction input. The shadow advances only after the existing complete RGB board checks pass.

The 16-frame target FIRE setting was selected from controlled genuine-ALE comparisons: one and four frames failed the reproduced later-turn `a2a3`; six frames completed that move but failed on a later `b2b3`; eight frames completed `b2b3` but failed on `g2g3`; 12 frames completed `g2g3` and a nine-cycle run; 16 frames completed 20 consecutive player/Atari cycles. This identifies a target-confirmation timing sensitivity but does not prove whether the ROM polls FIRE intermittently, debounces the input, or has another internal readiness condition. The full evidence and limits are recorded in `.agents/evidence/BLK-001-diagnostic-20261015.md` and its ZIP bundle.

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

The multi-turn runner verifies consecutive player moves and Atari replies from an evolving RGB-checked shadow board. A 16-frame deterministic replay completed 20 complete player/Atari cycles; a separate registered v5-default run completed two cycles. Targeted real-ALE regressions accepted `e2e4`, `g1f3`, `f1b5`, the `d3d4` / `c5d4` / `d1d4` capture sequence, and one-square pawn moves including `h2h3`. A bounded 12-frame terminal-seeking run completed 18 cycles before the next target preview remained after FIRE and the runner stopped safely. The observable failure stage is target confirmation; exact ROM-level cause remains unresolved. No real run observed termination, truncation, or nonzero reward. See `.agents/evidence/BLK-001-diagnostic-20261015.md` and `.agents/evidence/M1-04-terminal-verification.md` for the current diagnosis, attempt accounting, and verdict.

Mode configuration was checked by resetting each supported mode 0–4 and reading the configured mode byte only as a diagnostic. Only mode 0 received gameplay testing; higher modes were not evaluated for turn behavior or terminal reliability. Difficulty is limited to 0 in the installed ALE-Py release.

## Multi-turn reproduction and safety tests

Run one bounded terminal-feasibility episode inside the locked environment:

```bash
uv run --locked python scripts/run_m1_terminal_experiment.py --profile deterministic-dev --seed 20261015 --max-player-moves 40 --max-opponent-wait-frames 10000 --max-episode-frames 54000 --max-episode-seconds 900 --target-fire-press-frames 16 --trace artifacts/m1/m1-04/attempt.json
```

The selector is a disclosed, one-ply diagnostic heuristic. It uses no Stockfish, model, or search engine. Every player move is checked against the current legal `python-chess` board; the shadow advances only after RGB evidence covers the full resulting board. A failed or ambiguous control stops the episode and retains the last verified board. `tests/test_m1_episode.py` covers bounded failures, cursor displacement, terminal/truncation bookkeeping, and reward perspective with synthetic environment doubles; those tests do not establish ALE terminal behavior.

The current M1-04 result is **UNVERIFIED** because the bounded terminal-seeking run observed no game-ending event or nonzero reward. The controller now completes longer verified runs, but a later target-confirmation stop remains possible and exact ROM-level input timing remains unresolved. G2 remains **in progress**; conditional G2 approval is not exercised. M1 remains incomplete, and M2 requires separate explicit authorization.
