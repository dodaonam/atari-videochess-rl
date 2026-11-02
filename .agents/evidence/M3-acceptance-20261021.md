# M3-001 — Formal PM acceptance (2026-10-21)

## Decision and authority

**Status:** ACCEPTED, based on the independent PM technical audit and the project owner's explicit authorization in this conversation to complete all remaining M3 closure and integration tasks.

**Accepted engineering PR HEAD:** `e32e1e63ab5ee9078a51f9214698f28174565a09`
**PR:** https://github.com/dodaonam/atari-videochess-rl/pull/3
**Formal decision record:** https://github.com/dodaonam/atari-videochess-rl/pull/3#issuecomment-6320815831
**Integration target:** `initial-idea` (not `main`).

## Acceptance criteria

- **M3-01 — PASS:** Curated Lichess Elite May 2022 source recorded and verified before ingestion, including archive/member hashes, publisher terms snapshot and scoped owner internal academic-use authorization. The package's separate license remains unverified; raw and bulk derived data must not be redistributed.
- **M3-02 — PASS:** Real, bounded Stockfish 19 teacher evidence, 128/128 positions, 377 centipawn and 3 mate MultiPV rows, typed perspective/WDL/score normalization, verified sidecar. Teacher run ID `58febd814bb6bdd6fa67b990a1e4906ada14c31fafa265829fb49b7d3c203272`.
- **M3-03 — PASS:** Source-backed deterministic release and repeated build r6/r7, identical nine-file outputs with individual SHA-256, reconstructed sampling provenance and hash-consistent tamper-negative tests (R-02).
- **M3-04 — PASS:** Explicit game-group deterministic split assignment, before/after split and retention statistics, board-overlap purge with 0 remaining exact cross-split signatures, independent semantic verifier and tamper tests (R-01).

**Evidence:** `.agents/evidence/M3-final-closure-20261021.md`, `.agents/evidence/M3-final-closure-record-20261021.json`, `.agents/evidence/M3-premerge-final-verification-20261021.md`, and https://github.com/dodaonam/atari-videochess-rl/pull/3#issuecomment-6320480151 .

**Tests:** Final clean-clone 224/224 reported PASS at exact accepted code SHA; focused M3 32/32, Pre-M3 8/8, compile/uv lock/context preflight/diff passed. GitHub Actions tested context/preflight only. Independent PM examined source/commit/manifest evidence and final test logs but did **not** rerun local-only raw artifact verification or the full Python suite on the executor host.

**Immutable source-backed release:** `f10a679deddf06f3e1e3c39cf58db4e21176629c26c09034a271bf278189e890`, manifest SHA-256 `be1e1f9316fac01be893774cfe09a313de193fbd1a12ab2d219ff5c041104a12`, producing revision `40cd4e88bcaf987033a27f5f73995c5f44f21fb5`. No change to historical release/teacher run IDs or raw artifact files is authorized by acceptance.

## Boundaries / next phase

This decision closes **M3 only**. **G3 is NOT approved**; **M4–M7 are NOT authorized** and require separate owner direction. Do not begin new model training, Stockfish roles, cloud/paid compute, public dataset release or ROM/license actions based on M3 acceptance.

RSK-010 remains open: canonical checkpoint history exceeded 128 entries and 4 MiB by this review; preserve all history, plan and test lossless migration before a checkpoint-heavy follow-on task.

Acceptance and merge are distinct operations. After integrating PR #3 into `initial-idea`, independently verify branch lineage, exact accepted source, canonical status, portable checkpoint and CI. Do not claim a fresh local checkpoint, full test execution or hash of ignored raw files if only remote GitHub state was verified.
