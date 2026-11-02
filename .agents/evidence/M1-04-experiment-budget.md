# M1-04 bounded real-ALE experiment budget

- **Budget set at:** 2026-10-15T09:05:09Z
- **Scope:** Mode 0 (`ALE/VideoChess-v5`), real Atari actions and RGB verification only.
- **Total new gameplay budget:** At most 180 minutes of local wall-clock time.
- **Per-episode cap:** 15 minutes and 54,000 ALE frames, whichever occurs first.
- **Attempt cap:** Eight terminal-seeking episodes; stop sooner after a reproducible terminal result or when further runs are unlikely to add evidence.
- **Artifact cap:** 250 MiB for new traces and selected RGB frames under `artifacts/m1/m1-04/`.
- **Move selection:** Transparent legal-move heuristic only; no Stockfish, model, or search engine.
- **State policy:** Do not inject positions or modify RAM. Retain every observed mismatch and stop the episode when the controller cannot re-establish a verified cursor/board state within bounded retries.

The two short baseline reproductions recorded before this budget are not terminal-seeking episodes.

## Actual use

- **Terminal-seeking episodes:** 8 of 8 maximum. The original seven used seeds `20261015`, `20261016`, `20261017`, `20261018`, `20261019`, `20261015` (repeat), and `20261022`. The eighth used seed `20261015` with the phase-verified controller and 12-frame target FIRE.
- **Eighth result:** 18 complete RGB-verified player/Atari cycles, then a safe stop on `a2a1` when the selected-piece preview remained after FIRE; 14,081 ALE frames and 37.973 seconds. It returned reward 0.0, `terminated=false`, `truncated=false`.
- **Additional bounded probes:** 17 retained `blk001` traces cover same-seed failure reproduction, 4/6/8/12/16-frame target FIRE comparisons, 20-cycle deterministic control, pawn/knight/diagonal/straight/capture categories, and v5-default gameplay. All used genuine mode-0 ALE actions from reset; no injected position or RAM modification.
- **Elapsed wall time:** 188.307 seconds across 18 `blk001` traces in the current diagnostic continuation (including the eighth terminal attempt); 80.843 seconds across all eight terminal-seeking episodes, combining the original 42.870 seconds and the new 37.973-second episode.
- **ALE frames:** 72,901 summed across the 18 current-continuation traces (replays included); 32,754 across the eight terminal-seeking episodes, combining 18,673 original frames and 14,081 new frames. The longest terminal-seeking episode remains below the 54,000-frame/15-minute cap.
- **Artifacts:** 1,214 entries and 7,444,452 bytes were covered by the new local `artifacts/m1/MANIFEST-20261015.sha256`; it lists every file under `artifacts/m1/` except itself and verifies with zero missing paths or hash mismatches. The older `MANIFEST.sha256` was preserved unchanged; it still covers its original 327 entries and does not cover 872 current content files.
- **Caps reached:** the eight-episode terminal-attempt cap is reached. No episode reached 15 minutes or 54,000 ALE frames. Stop terminal-seeking runs; the observable target-confirmation failure is diagnosed and the 16-frame correction completed 20 cycles, but no terminal evidence was obtained.
- **Outcome:** no terminal or truncation was observed; all eight terminal-seeking episodes returned cumulative reward 0.0. M1-04 remains UNVERIFIED. See `.agents/evidence/M1-04-terminal-verification.md` and `.agents/evidence/BLK-001-diagnostic-20261015.md` for results.
