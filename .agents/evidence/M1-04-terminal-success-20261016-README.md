# M1-04 genuine ALE terminal evidence

Recorded 2026-10-15 UTC (2026-10-16 local). This compact bundle contains complete raw traces for five newly authorized terminal-seeking episodes, the earlier frame-level target-confirmation failure replay, and selected genuine ALE RGB frames.

## Verified terminal outcome

Two fresh deterministic resets in `ALE/VideoChess-v5`, mode 4, difficulty 0, frameskip 1, sticky-action probability 0.0, seed `20261017`, reproduced ALE reward `-1.0`, `terminated=true`, `truncated=false`, environment step 4609, ALE frame number 4613, and wall times 9.883 s and 9.711 s. Both produced terminal-screen pixel SHA-256 `024b23b1c9295ba28cf1c8dd716934262a5d5eabade513eaf96a95c03cd4809c`. The negative sign indicates a White loss under the pinned ALE VideoChess wrapper. The positive reward sign was not observed in live play.

ROM `video_chess.bin`, SHA-256 `d44f2a115393b0a6cbcd5398d62369e652f3670a9ee585883d183e740edad0f7`; Python 3.12.3; Gymnasium 1.4.0; ALE-Py 0.11.2. Runtime observation: RGB `(210,160,3)` `uint8`; diagnostic RAM `(128,)` `uint8`; action space `Discrete(10)`. RAM values are evidence only and did not drive the controller.

## Recorded gameplay and limits

From reset, White moves `f2f3`, `g2g4`, and `a2a3` were confirmed against RGB; Atari replies `c7c5`, `b8c6`, and `e7e5` were independently confirmed. White then submitted legal move `b2b3`. That move did not receive RGB confirmation before the genuine ALE terminal occurred during Atari thinking. The runner preserved the last independently verified position (`r1bqkbnr/pp1p1ppp/2n5/2p1p3/6P1/P4P2/1PPPP2P/RNBQKBNR w KQkq - 0 4`) and did not advance the shadow board. Both terminal RGB frames are transition screens without a parseable chessboard. After candidate `b2b3`, `d8h4#` is the unique legal checkmate according to `python-chess`; this is a chess-rule inference consistent with the ALE loss signal, not a visually observed final move or a verified shadow transition.

Policy: transparent legal cooperative-loss diagnostic (Fool's Mate trap), no Stockfish, model, training, RAM-based decisions, state injection, ROM changes, or reward override. Source FIRE 1 frame; target FIRE 16 frames; direction holds 33 frames; 1 frame release; stable RGB observation windows. Per-episode limits were 8 player moves, 20,000 opponent-wait frames, 54,000 ALE frames, 600 seconds wall time, and 32 MiB of RGB artifacts. No limit was reached in the terminal episodes.

The earlier 20-cycle episode stopped at its configured `max_player_moves=20` with both ALE flags false; it was not a game ending. The earlier 18-cycle attempt safely stopped on target-confirmation uncertainty with both ALE flags false. Mode 4 first exposed a runner defect: ten transient visual mismatches caused an early stop after about 330 wait frames, although the configured opponent wait was 20,000. Removing that mismatch-count stop and requiring a legal Atari reply's source cursor allowed observed replies after up to 1,221 frames. The included campaign traces retain the failure and corrected run.

## Reproduction

Use the locked local environment and a new, unused trace path:

```bash
uv run --locked --no-sync python scripts/run_m1_terminal_experiment.py \
  --profile deterministic-dev --mode 4 --policy cooperative-loss --seed 20261017 \
  --max-player-moves 8 --max-opponent-wait-frames 20000 --max-episode-frames 54000 \
  --max-episode-seconds 600 --target-fire-press-frames 16 \
  --trace artifacts/m1/m1-04/reproduction-new-path/trace.json
```

The portable archive is retained locally at `.agents/evidence/M1-04-terminal-success-20261016.zip` and is intentionally not committed. The committed report, this README, the trace hashes, and local raw-artifact manifest provide its independent identity and scope. Original traces are under `artifacts/m1/m1-04/campaign4-mode4-queenmate-seed20261017/` and `campaign5-terminal-replay-seed20261017/`. The full local raw artifact inventory is `artifacts/m1/MANIFEST-20261016.sha256`. ZIP CRC and all member SHA-256 values were checked; trace-linked RGB pixel hashes were decoded and verified.

## Contents

- `traces/`: full JSON traces from campaign 1–5 plus the original target-confirmation failure replay.
- `frames/`: selected source/target confirmation, Atari thinking, verified-board, pre-terminal, terminal, and prior failure frames.
- `SHA256SUMS`: SHA-256 of every bundle member except this manifest.

The actual terminal screen does not reveal a parseable final board. The runner records ALE reward and flags directly and retains the last RGB-verified chess position. The traces record source revision `f2f2065c5da991394eba9204cb481daceeeba904` with dirty-path provenance; implementation hashes are in the final verification report.
