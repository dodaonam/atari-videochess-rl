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

- **Terminal-seeking episodes:** 7 of 8 maximum; seeds `20261015`, `20261016`, `20261017`, `20261018`, `20261019`, `20261015` (repeat), and `20261022`.
- **Additional bounded probes:** one one-move `e2e4` attempt and four targeted control probes. All used real mode-0 ALE actions; no injected position or RAM modification.
- **Elapsed wall time:** 60.583 seconds across all 12 retained traces, including terminal-seeking episodes and probes (42.870 seconds for the seven terminal-seeking episodes).
- **ALE frames:** 26,161 summed across all 12 traces. The longest terminal-seeking episode used 3,922 frames and 9.039 seconds.
- **Artifacts:** 1,384,023 bytes under `artifacts/m1/m1-04/`, below the 250 MiB limit. The pre-existing `artifacts/m1/MANIFEST.sha256` was not changed.
- **Caps reached:** none. No episode reached 15 minutes or 54,000 frames; the experiment stopped at seven terminal-seeking episodes because additional runs repeated the same unresolved input failure and were unlikely to add evidence.
- **Outcome:** no episode terminated or truncated; the sum of ALE rewards was 0.0. M1-04 remains unverified. See `.agents/evidence/M1-04-terminal-verification.md` for the attempt table and diagnosis.
