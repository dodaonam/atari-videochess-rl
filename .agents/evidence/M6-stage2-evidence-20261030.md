# M6 Stage 2 — Consecutive ALE Closed-Loop Diagnostics

**Status:** Stage 2 diagnostics completed; they do not establish complete-game performance.
**Latest diagnostic source:** `b393b5180b45af8b9f701272d93a6d5452bb96b8`.
**Evaluation configuration:** `ALE/VideoChess-v5`, White, mode 4, difficulty 0.
**ROM SHA-256:** `d44f2a115393b0a6cbcd5398d62369e652f3670a9ee585883d183e740edad0f7`.
**M5 root manifest SHA-256:** `a201a254671ad59ae1fecb402abf994d5bf523097f1c3010b5c7fa237ae6dd4c`.
**Dependency lock SHA-256:** `60b55b57bd89c08274b470ea5c525f60037e893194e5815feeeaccf98b23df1a`.

The checks below used real ALE RGB frames, the fixed 33-frame direction hold, 1-frame source FIRE, 16-frame target FIRE, and 1-frame release. The later debug run also used three passive 33-frame settle/observation windows after target FIRE. No FIRE action was retried. Each run was bounded by its configured per-policy player-move cap, so these are diagnostic episodes, not completed games or Atari outcomes.

## Debug profile

Profile `development-debug`: frameskip 1, sticky-action probability 0.0. Run `m6-stage2-debug-development-debug-b393b5180b45` contains five separately seeded attempts (one per frozen policy). Its run manifest SHA-256 is `42044f6a18d6a65d07b84392811d3eca3a42a2c3bcd2ce4380800066b7a1dc18`; the 225,413-record append-only ledger SHA-256 is `ec1583b68a6daafcfe10c8a0e1eadf6274972098611336472fa265155e803865`; its artifact manifest SHA-256 is `443c1f546bc3ee82963cfd046a69fb0efba2459729151d62e5cadd1e9a7bda01`.

| Policy | Attempted episodes | Player moves attempted / RGB verified | Verified Atari replies | Board desynchronizations | Frames | Wall seconds | Stop |
|---|---:|---:|---:|---:|---:|---:|---|
| M5 Warm | 1 | 10 / 10 | 10 | 0 | 28,868 | 147.154 | 10-move diagnostic cap |
| M5 Scratch | 1 | 10 / 10 | 10 | 0 | 40,882 | 215.662 | 10-move diagnostic cap |
| M4 behavior-only | 1 | 10 / 10 | 10 | 0 | 24,891 | 128.455 | 10-move diagnostic cap |
| SimpleMaterialHeuristic | 1 | 5 / 4 | 4 | 0 | 7,418 | 35.902 | `CONTROLLER_TARGET_CONFIRMATION_UNCERTAIN` |
| RandomLegal | 1 | 7 / 6 | 6 | 0 | 10,659 | 53.993 | `CONTROLLER_TARGET_CONFIRMATION_UNCERTAIN` |

For the two policy safe stops, the Atari target-square preview remained visible after the single target FIRE and all three passive settle windows. The runner stopped with the last RGB-confirmed board/history, and did not issue a second FIRE. Thus 40 of 42 initiated player moves were RGB verified across this five-episode diagnostic set (95.2% raw; mixed policies and same-process diagnostic evidence, not an evaluation estimate). None was an ALE-terminated game; the three cap stops are runner truncations, and the two uncertainty stops are incomplete episodes. All counts are retained in the raw traces.

## Limited default-v5 profile

Profile `ale-v5-default`: frameskip 4, sticky-action probability 0.25. Run `m6-stage2-default-ale-v5-default-b393b5180b45` contains one bounded one-move attempt per M5 policy. Run manifest SHA-256 is `3d31aef9473836561dcdb07de344f03e7bf2093dad4cf3a31e583f8d91b22fec`; ledger SHA-256 is `f1645e99585e59e9b11a7aa6c8fe1d5f9f8a223c7f64cad3defec9d92789c165`; artifact manifest SHA-256 is `52a3dffcbb136061304f15ff0d1862c5ddf39e1e363ec92f2da6526a36ac93c4`.

| Policy | Moves attempted / RGB verified | Replies | Board desynchronizations | Safely corrected cursor displacements | Frames | Wall seconds |
|---|---:|---:|---:|---:|---:|---:|
| M5 Warm | 1 / 1 | 1 | 0 | 4 | 1,748 | 2.764 |
| M5 Scratch | 1 / 1 | 1 | 0 | 4 | 1,676 | 2.726 |

Both checks stopped at their one-move diagnostic cap. Post-hoc verification with the current trace summarizer checked the trace payload hashes, event chains, attempt manifests, screenshot hashes, and ledger chain. It confirmed that the four cursor-route displacements in each attempt were corrected before execution and were **not board desynchronizations**. Earlier stored summary records classified these cursor corrections as desynchronizations; the current source preserves the old recorded count as `recorded_desynchronization_count`, derives board desynchronization from the raw trace, and reports cursor corrections separately. No game completed.

## Interpretation and disposition

- The actual M5 Warm and Scratch policies both completed ten consecutive verified player moves and ten genuine Atari replies in the debug profile.
- Both M5 policies completed one observed player move/reply cycle in the default-v5 profile. This is limited controller/configuration evidence, not default-profile reliability or full-game evidence.
- The two non-neural controls demonstrated a safe uncertainty stop after target FIRE. The controller did not retry or advance its shadow history. This operational limitation is preserved for the official campaign's failure accounting.
- All episode attempts in this record are incomplete by game-result semantics. Runner caps and uncertainty stops are not draws, wins, or losses.
- The debug run used seed IDs 20261210–20261214 and the default check used 20261220–20261221. These are diagnostic seeds, separate from the predeclared Stage 3 seeds.
- The post-hoc verification command was an in-process call to `videochess_rl.m6.campaign.summarize_run` over each run's `events.jsonl`; it completed successfully on 2026-10-30. This call verified the existing manifests and did not alter traces or summaries.

Full local traces and RGB evidence remain in the ignored directory `artifacts/m6/`; they are not included in Git or uploaded. The report is a sanitized pointer and summary, not a replacement for those local evidence artifacts.
