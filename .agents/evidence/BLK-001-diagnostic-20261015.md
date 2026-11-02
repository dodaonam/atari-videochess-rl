# BLK-001 diagnosis and controller follow-up

> Historical diagnosis as of 2026-10-15 before the additional authorized campaign. Its input-stage findings remain valid; current terminal, runner-readiness, and blocker-resolution evidence is in [M1/G2 final mission verification](M1-G2-final-verification-20261016.md).

- **Recorded:** 2026-10-15T16:17:05Z UTC; final test and archive-integrity addenda recorded after verification.
- **Repository revision used by the experiments:** `ef86ba18fa9cd594ae419fa99b2ad191b75a49a8` on `initial-idea`; the worktree contained the authorized controller/test changes. No remote history was changed during experimentation.
- **Runtime:** Python 3.12.3, Gymnasium 1.4.0, ALE-Py 0.11.2, `ALE/VideoChess-v5`, packaged `video_chess.bin` SHA-256 `d44f2a115393b0a6cbcd5398d62369e652f3670a9ee585883d183e740edad0f7`.
- **Evidence bundle:** [BLK-001-diagnostic-20261015-r2.zip](BLK-001-diagnostic-20261015-r2.zip), 211,538 bytes, SHA-256 `91b0d03907b1b6764f18991880596f9c09b90986ad982b05f106bed948f96a32`.

## Assessment

The reproducible failure is localized to target confirmation. In the same-seed later-turn replay, the cursor reached `a2`, source FIRE was followed by the selected-piece blink, and the selected pawn preview appeared on `a3`. A one-frame target FIRE did not change the board through frame 2279, including 132 subsequent no-op frames. The trace’s final board and the last verified shadow board remained identical. This rules out source selection, selected-target navigation, and a parser-only false negative for that reproduced `a2a3` failure.

Target-FIRE duration changed the result in controlled replays. One and four frames failed on `a2a3`; six frames completed `a2a3` but failed later on `b2b3`; eight frames completed `b2b3` but failed on `g2g3`; 12 frames completed `g2g3` and nine full cycles but later stopped on `a2a1`; 16 frames completed 20 consecutive full cycles. These results support a phase-sensitive FIRE timing problem and justify a 16-frame target-confirmation default. They do not establish the exact ROM-level cause. Intermittent CPU polling, button debouncing, or a readiness condition remain possible explanations.

The 12-frame terminal-seeking run that stopped on `a2a1` is preserved as a limitation. The controller observed source selection and target preview, requested target FIRE, then observed the preview again. It stopped without retrying because repeating FIRE could duplicate a move if the first press had taken effect during an unobserved animation.

## Hypothesis assessment

| Hypothesis | Observable signature | Result | Evidence |
|---|---|---|---|
| H1 source selection failure | No selected-piece blink after source FIRE | **REJECTED for the reproduced `a2a3` failure.** The selected-piece blink appeared after stable source cursor confirmation. | Baseline frame trace and `source_selection_evidence` in the bundle. |
| H2 selected-target navigation failure | Intended target preview absent before target FIRE | **REJECTED for that replay.** The pawn preview was visible at `a3`. | Per-frame `a2`/`a3` changes and RGB hashes around frames 2092–2111. |
| H3 target confirmation failure | Target preview remains; candidate board never appears after target FIRE | **CONFIRMED as the observable failure stage.** | One-frame target FIRE at frame 2146; unchanged RGB through frame 2279. Later duration-controlled stops also occurred at this stage. |
| H4 turn readiness | Stable RGB board/cursor may still be rejected internally by the game | **UNRESOLVED internally.** Each move followed a verified Atari reply and the source/target signatures were visible, but RGB does not expose all ROM CPU state. | Real ALE traces; RAM is recorded only as diagnostic. |
| H5 timing / release / input repeat | Different target FIRE duration changes acceptance | **SUPPORTED.** Six, eight, 12, and 16 frames resolved progressively later examples; 16 completed 20 cycles. Exact poll/debounce behavior is unproven. | Timing comparison JSON and replay traces in the ZIP. |
| H6 visual interpretation failure | Accepted board transition is present but parser misses it | **REJECTED for baseline.** Board occupancy remained unchanged during the bounded stabilization period. | Baseline per-frame RGB counts/hashes. |
| H7 VideoChess rule incompatibility | Legal shadow move is rejected consistently by Atari | **REJECTED as a general explanation.** Atari accepted `a2a3`, `e2e4`, `g1f3`, `f1b5`, `d3d4`, `c5d4`, and `d1d4` in real runs. A later isolated stop does not prove every Atari rule is identical to `python-chess`. | Move-category traces in the ZIP. |

## Controller changes

`ControllerTiming` now separates source and target FIRE durations. Source selection remains a one-frame pulse. Target confirmation defaults to 16 frames. The plan inserts RGB observation windows after source FIRE and after each one-square selected-target direction. The episode runner records the source cursor, selection request, selected-piece blink evidence, selected-target requests and previews, target-confirmation request, transition observation, Atari reply, and verified move phases.

The selected-piece blink detector requires multiple visible and absent source samples, no cursor overlay, and a stable board match outside the cursor mask. The selected-target detector requires the moving piece at both source and requested target during the flashing preview while unrelated squares match the prior verified board. The terminal CLI also refuses to reuse an existing trace path, `frames/` directory, or symlink, so reruns cannot silently replace prior outputs. FIRE is withheld if either check fails. After target FIRE, a remaining source/target preview causes a safe stop without a retry. Shadow state still advances only after complete RGB evidence validates the candidate player move and Atari reply.

The final two-cycle trace at `artifacts/m1/blk001-final-instrumented-20261015/trace.json` records action name/index, requested frames, actual ALE frame boundaries, environment-step boundaries, pixel changes, reward sum, terminal/truncation flags, and ending RGB hash. Its selected RGB frames' decoded raw hashes match the trace. Diagnostic RAM remains outside the decision path.

## Real ALE regression results

All of these were genuine actions from fresh reset; no FEN or RAM injection was used.

| Run | Profile / seed | Target FIRE | Result |
|---|---|---:|---|
| Original later-turn `a2a3` replay | mode 0, frameskip 1, sticky 0; `20261022` | 1 frame | Three verified cycles; `a2a3` preview remained after FIRE and the board stayed unchanged through frame 2279. |
| Controlled short-pulse comparison | same seed and opening sequence | 4 / 6 / 8 frames | Four frames failed on `a2a3`; six frames completed `a2a3` but stopped on `b2b3`; eight frames completed six cycles and later stopped on `g2g3`. |
| Longer-pulse deterministic run | mode 0, frameskip 1, sticky 0; `20261022` | 12 frames | Nine complete cycles, including `g2g3` and `h2h3`; stopped before terminal seeking resumed. |
| Controlled move-category trace | mode 0, frameskip 1, sticky 0; `20261022` | 12 frames | `e2e3`, `e3e4`, `d2d3`, `d3d4`; Atari replies included `c5d4`; `d1d4` then captured that pawn. All five cycles were RGB-verified. |
| Pawn / knight trace | mode 0, frameskip 1, sticky 0; `20261015` | 12 frames | `e2e4` and `g1f3` each completed with Atari replies `e7e5` and `b8c6`. |
| Diagonal trace | mode 0, frameskip 1, sticky 0; `20261015` | 12 frames | `e2e4`, `g1f3`, `f1b5`; all replies and resulting boards were RGB-verified. |
| Registered v5 defaults | mode 0, frameskip 4, sticky 0.25; `20261016` | 12 frames | Two complete player/Atari cycles. The real integration suite also passed its v5-default check with the final 16-frame default. |
| Final action-boundary trace | mode 0, frameskip 1, sticky 0; `20261022` | 16 frames | Two complete cycles; 1,332 ALE frames and 3.822 wall seconds. Every action record includes ALE-frame and environment-step start/end values. |
| Terminal-seeking attempt 8 | mode 0, frameskip 1, sticky 0; `20261015` | 12 frames | 18 complete cycles; safe stop on `a2a1` with target preview still visible. 14,081 ALE frames, 37.973 wall seconds. |
| Corrected reliability replay | mode 0, frameskip 1, sticky 0; `20261015` | 16 frames | 20 player moves and 20 Atari replies completed from reset; 15,356 ALE frames and 41.255 wall seconds. |

Across the 20-cycle run, the mean was 383.9 ALE frames per chess ply and 1.03 wall seconds per ply (2.06 seconds per player/Atari cycle). The run had no uncertain input or shadow advancement without complete RGB evidence. The v5-default run required 1,888 ALE frames across four plies (472 ALE frames per ply) and 2.129 wall seconds.

The eighth terminal-seeking attempt used 14,081 frames and 37.973 seconds. ALE reported cumulative reward `0.0`, `terminated=false`, and `truncated=false`. Its final frame and environment step were both 14,081. The last verified FEN was `r2r2k1/3n1ppp/2nbb3/ppp1p3/8/PqPp1PPP/R7/1NBQKBNR w K - 0 19`. No live terminal or nonzero reward was observed. The official ALE-Py 0.11.2 wrapper source describes white-perspective checkmate rewards (`+1` for black checkmate, `-1` for white checkmate); this source behavior is not treated as a live demonstration.

The eight-episode terminal-seeking cap is exhausted. Across the 18 retained `blk001` traces in this continuation, elapsed runtime sums to 188.307 seconds and recorded frame counts sum to 72,901 (replays are included). Across all eight terminal-seeking episodes, the recorded total is 32,754 frames and 80.843 seconds. All execution remained on local CPU; no paid service, GPU, Colab, Stockfish search, model, or supervised training was used.

## Artifact and archive integrity

- `artifacts/m1/MANIFEST-20261015.sha256` contains 1,214 SHA-256 entries for the files present under `artifacts/m1/` when generated; all listed paths existed and all hashes matched. It excludes itself. Its SHA-256 is `bb32697b43deea7094f86e834fd2dfe0a5b7edfaa063dc8d48e5c947490fd80a`.
- The earlier `artifacts/m1/MANIFEST.sha256` was preserved unchanged. Its 327 entries still exist and hash correctly; it leaves 886 current content files unlisted.
- The diagnostic ZIP contains 59 members. ZIP CRC, member SHA-256 coverage, 30 trace-linked decoded RGB hashes, and sensitive-pattern scanning passed. Its manifest covers every member except the manifest itself. It includes the full baseline replay trace so each selected baseline PNG can be checked independently.
- The full archived `artifacts.zip` referenced in earlier task context was not available in this workspace. The smaller prior `m1-04-evidence-20261015.zip` was present and was not misrepresented as the full archive.
- The diagnostic ZIP contains selected small traces and RGB frames. Raw larger traces remain in ignored `artifacts/m1/`, outside Git history.

## Tests and governance

The final expanded M1-focused command `./.venv/bin/python -m unittest tests.test_m1_control tests.test_m1_episode tests.test_m1_ale_integration tests.test_m1_environment tests.test_m1_shadow tests.test_m1_vision tests.test_m1_terminal_cli -v` passed all 54 tests in 14.383 seconds (exit 0), including four CLI output-collision tests and the real ALE integration checks. The prior 50-test run also passed before the CLI guard was added. The latest checkpointed full command `./.venv/bin/python -m unittest discover -s tests -v` ran 117 tests in 64.894 seconds (exit 1): 116 passed, and the sole failure was `test_stockfish_answers_uci_readiness_without_searching` because the executable is absent from the local PATH. The checkpoint-related context recovery test passed. The earlier 113-test run had the same sole Stockfish failure. Sanitized logs are retained at `logs/BLK-001-m1-suite-final2-20261015.log`, `logs/BLK-001-m1-suite-20261015.log`, `logs/BLK-001-full-suite-20261015.log`, and `logs/BLK-001-full-suite-final2-20261015.log`.

`uv` is unavailable, so the locked dependency check could not run. The project venv has no `pip` module, so `pip check` could not run either. No dependency was installed. `git diff --check` passed. No full archived `artifacts.zip` was available in this workspace.

Current acceptance: M1-01 **PASS**, M1-02 **PASS**, M1-03 **PASS**, M1-04 **UNVERIFIED**, M1-05 **PASS**, M1-06 **PASS**. M1-001 remains blocked by BLK-001; G2 remains in progress; O-01 through O-08 remain unresolved; M2 remains unauthorized. A new terminal-seeking budget must be authorized before another terminal-seeking episode because the existing eight-attempt cap has been reached.

- M1-focused log SHA-256: `76625627dad842447ca42ae9a4d3717b5a9a6bde6d37ea4f4ee4bd37a7150f87`.
- Full-suite log SHA-256: `b85c0d3902d3ee25d64b1e80ab14338672b9d84eb503e37835463ef63670703d`.

- Refreshed diagnostic ZIP SHA-256: `91b0d03907b1b6764f18991880596f9c09b90986ad982b05f106bed948f96a32` (59 members, 30 trace-linked decoded RGB checks).

- Final expanded M1-focused log SHA-256: `d4d4499d6a7efa47de9ed5dd8912b33e95c55bac3e8e9c839ad616f09ade0523`.

- Latest full-suite log SHA-256: `d5dd4c9d45ed313f9cfbb74a2bee92631ccbf51661dfa3e27e1356a6bf4b6a59`.
