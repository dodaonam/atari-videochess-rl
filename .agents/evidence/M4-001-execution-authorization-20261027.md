# M4-001 Direct Execution Authorization — 2026-10-27

- **Authority:** Project owner, direct mission issued 2026-10-27.
- **Recorded at:** 2026-10-27T12:22:34Z.
- **Task:** M4-001, supervised behavior pretraining.
- **Baseline:** `94220870c3abc9e8aa725db85fb0c6cebebdbb48` (`initial-idea` reviewed integration baseline).
- **Authorization:** The project owner directly authorized full M4-001 execution, verification, local CPU training/evaluation within the existing caps, and a reviewable PR merge into initial-idea when all checks pass and repository protections permit; M5/M6, G3 approval, external compute, new data, Stockfish-assisted initial training, and resource-limit expansion remain excluded.
- **Fixed constraints:** Follow accepted ADR-0003 and the M04 plan/protocol. Use the exact accepted M3 release and only `played_move_uci` labels. Keep Stockfish out of initial training and inference. Use local CPU within the existing 45-minute-per-seed, three-hour aggregate, 2 GiB RSS, and 250,000-parameter caps. Do not acquire/upload data, allocate cloud/GPU/paid compute, start M5/M6, or claim G3 approval.
- **Integration boundary:** Branch/commit/PR/merge and clean-clone post-merge verification are authorized after acceptance evidence and required checks pass; do not bypass branch protection or required review.
- **Historical decision:** The 2026-10-23 conditional authorization and the 2026-10-27 O-01 supersession remain preserved in their original records. This addendum records the current direct mission's broader delivery authority; it does not claim instructor approval.
