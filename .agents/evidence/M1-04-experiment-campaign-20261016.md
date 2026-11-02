# M1-04 terminal-seeking campaign authorization and budget

- **Authorized by:** direct user instruction in the one-shot M1/G2 mission received 2026-10-16 local time.
- **Campaign recorded:** 2026-10-15T17:49:17Z, before terminal-seeking experiments.
- **Source revision at authorization:** `f2f2065c5da991394eba9204cb481daceeeba904` on `initial-idea`; `origin/initial-idea` matched this revision.
- **New ceilings:** 12 hours cumulative local gameplay/diagnostic experiment wall time; 200 additional real terminal-seeking episodes; 2 GiB newly generated experimental artifacts; local CPU only; no paid/cloud/GPU/Colab resources.
- **Per-episode limits:** 15 minutes wall time; 54,000 ALE frames; 20,000 ALE frames waiting for one opponent reply; at most 40 attempted player moves; at most 32 MiB written RGB artifacts. Stop on any real ALE terminal/truncation, unverified controller phase, or exhausted episode limit. No action retry after an uncertain transition.
- **Selector restrictions:** legal `python-chess` move selection only for transparent M1 diagnostics; no Stockfish, pretrained model, RL policy, RAM injection, position injection, ROM patching, or altered ALE reward.
- **Strategy order:** begin with short controlled timing comparisons on genuine reset games; then prioritize an adaptive cooperative-loss line at the fastest safe skill mode; compare a small number of other supported skill modes only when reply latency permits; use transparent immediate-mate/check-seeking as the alternative policy if loss-seeking does not progress. Do not repeat a strategy after evidence shows no useful progress.
- **Stop criteria:** terminate a batch after an authentic ALE terminal; after two equivalent no-progress outcomes; when a controller stop prevents further meaningful play; or when cumulative budget is reached. These are ceilings, not targets.

## Budget accounting

| Measure | Before first terminal-seeking run in this campaign |
|---|---:|
| New terminal-seeking episodes | 0 |
| New terminal-seeking ALE frames | 0 |
| New terminal-seeking wall time | 0 seconds |
| New experimental artifact bytes | 0 |
| Baseline full-suite verification charged conservatively to diagnostic budget | 75.620 seconds |

The earlier eight-episode budget in `M1-04-experiment-budget.md` remains exhausted historical evidence and is not reopened or rewritten. The 75.620-second charge is the complete baseline test command duration, including its real-ALE integration tests; it is counted conservatively against this campaign's cumulative time. Preflight and lock validation are not gameplay experiments.

## Stop-reason investigation before this campaign

The retained 20-cycle trace records `max_player_moves=20`, `status=complete`, `terminated=false`, and `truncated=false`; the runner loop ended at its configured player-move count. It was a runner cap, not an Atari ending. The retained 18-cycle terminal-seeking trace recorded 18 fully verified cycles and then failed safely during player input `a2a1` because target FIRE left the selected-piece preview visible; it also had `terminated=false` and `truncated=false`. The seven earlier short episodes stopped on controller/RGB uncertainty, not on Atari time expiry. These runs are not counted as part of this new campaign.

The existing CLI defaults are 40 player moves, 10,000 opponent-wait frames, 54,000 total ALE frames, and 900 seconds wall time; the runner's `complete` status currently conflates reaching the player-move cap with a completed game. This mission will replace that ambiguity with a machine-readable stop category before terminal-seeking runs.

The AtariAge-hosted 1979 Video Chess manual describes skill levels with average opponent thinking times from 10–15 seconds at the easiest levels to hours at the hardest, but describes no player game clock. ALE's pinned VideoChess wrapper limits exposed game modes to 0–4 because higher levels have documented multi-move bugs; modes are level settings, not different chess games. ALE progresses only while `env.step()` advances emulated frames; Python-side selector/vision computation consumes host wall time but does not itself advance ALE. Exact runner and wrapper behavior will be recorded with the implementation and runtime evidence.

## Initial controlled batch plan

1. Compare target FIRE durations 12, 16, 20, 24, 32, and 48 on the same legal opening move and deterministic mode-0 reset where prior data does not already provide an equivalent observation. The 12- and 16-frame prior outcomes are treated as prior evidence, not repeated experiments. Stop a duration comparison if a safe stop occurs or a hold creates an unexpected transition.
2. Test one cooperative-loss line (White `f2f3`, then `g2g4` when still legal) against actual observed Atari replies in mode 0, with an episode cap of 12 player moves. Record whether the opponent accepts a mating opportunity; do not claim checkmate from shadow state alone.
3. If mode 0 does not terminate after two materially different legal blunder lines, assess one stronger supported mode with sufficient per-reply waiting. Do not spend a full long episode on each mode.
4. If loss-seeking has no progress, switch to a transparent win-seeking selector that prefers immediate legal mate/check and material captures, then record that as a different strategy.

## Actual campaign results and accounting

The new authorization was used for five real terminal-seeking episodes. All began from a fresh ALE reset; no position, RAM, ROM, or reward was injected or modified. The deterministic profile used frameskip 1, sticky-action probability 0, difficulty 0, RGB observations, the packaged `video_chess.bin`, and local CPU execution.

| Run | Mode / policy | Seed | Verified player moves / Atari replies | ALE frames / environment steps | Wall seconds | Stop / result |
|---|---|---:|---:|---:|---:|---|
| `campaign1-mode0-loss-seed20261016` | 0 / cooperative-loss v1 | 20261016 | 12 / 12 | 8,916 / 8,916 | 16.477 | Runner move cap; no reward or ALE ending. The opening blunders did not preserve a mating trap, and later play repeated a rook route. |
| `campaign2-mode4-loss-seed20261016` | 4 / cooperative-loss v1 | 20261016 | 0 / 0 (1 player input attempted) | 732 / 728 | 2.046 | Safely stopped during Atari thinking. The prior runner stopped after ten transient RGB mismatches at about 330 wait frames, far before its configured 20,000-frame opponent wait. It misclassified this as an opponent timeout; no ALE termination occurred. |
| `campaign3-mode4-wait-seed20261016` | 4 / cooperative-loss v1 | 20261016 | 4 / 4 | 5,029 / 5,025 | 10.058 | Runner move cap; no ALE ending. With the early mismatch stop removed and a legal-reply source-cursor readiness check, the Atari replies arrived after 594, 660, 858, and 1,221 frames. |
| `campaign4-mode4-queenmate-seed20261017` | 4 / cooperative-loss Fool's Mate trap | 20261017 | 3 / 3; fourth player move attempted but not RGB-confirmed | 4,613 / 4,609 | 9.883 | Genuine ALE terminal: reward −1.0, `terminated=true`, `truncated=false`; terminal during Atari thinking/reply observation. |
| `campaign5-terminal-replay-seed20261017` | Same as campaign 4 | 20261017 | 3 / 3; fourth player move attempted but not RGB-confirmed | 4,613 / 4,609 | 9.711 | Same terminal outcome and ending RGB hash as campaign 4 from a fresh reset. |

The final policy used legal moves `f2f3`, `g2g4`, `a2a3`, then attempted `b2b3`, adapting only after each actual RGB-verified Atari reply: `c7c5`, `b8c6`, and `e7e5`. The last verified FEN, immediately before the unconfirmed `b2b3`, was `r1bqkbnr/pp1p1ppp/2n5/2p1p3/6P1/P4P2/1PPPP2P/RNBQKBNR w KQkq - 0 4`. ALE ended on an Atari thinking observation at frame 4,613 / environment step 4,609. The terminal RGB is a uniform purple game-over screen and the preceding saved frame is a uniform gray transition; neither shows a parseable final board. `b2b3` is therefore retained as an attempted legal controller input, not as a verified shadow transition. From the candidate board after `b2b3`, `d8h4#` is the unique legal mating move; that is a chess-rule inference consistent with the real ALE terminal and white-loss signal, not a visually observed final move.

Campaigns 4 and 5 reproduced the same three verified Atari replies, 4,613 frame number, 4,609 environment steps, reward event `−1.0`, terminal flags, terminal RGB pixel hash `024b23b1c9295ba28cf1c8dd716934262a5d5eabade513eaf96a95c03cd4809c`, and final screen. The new experiment paths total 1,517,440 bytes across 173 files before the portable bundle and manifest. Five episodes consumed 23,903 ALE frames and 48.175 seconds of episode wall time. The conservative campaign clock also includes the 75.620-second baseline full suite 43.657 seconds across focused regression runs (including the corrected first-run assertion failure), the final 65-test M0/M1 suite (15.142 seconds), and the final full suite (80.413 seconds), for 263.007 seconds total charged. This remains below 12 hours, 200 episodes, and 2 GiB by wide margins; no cloud, GPU, paid service, Stockfish gameplay, or training was used.

Target FIRE durations above 16 frames (20, 24, 32, and 48) were not run: once the same authentic terminal event had been observed twice under the 16-frame profile, further timing sweeps would not improve the M1-04 evidence. The earlier controlled comparisons at 1, 4, 6, 8, 12, and 16 frames remain historical evidence in `.agents/evidence/BLK-001-diagnostic-20261015.md`; they support timing sensitivity but do not identify the ROM's internal polling mechanism.

The real runtime confirmed only the negative white-perspective reward sign (`−1.0`, white loss). The positive sign was not observed live; ALE-Py 0.11.2 source documents the complementary `+1` case for black checkmated. The M1-04 criterion is supported by an actual nonzero reward and terminal event, separate terminated/truncated flags, RGB turn/readiness evidence, mode resets for 0–4, and actual gameplay/termination in mode 4. No claim is made that both reward signs were observed.
