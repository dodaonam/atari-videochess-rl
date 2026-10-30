# M06 — Atari Integration and Evaluation

**Task:** M6-001
**Status:** authorized and in progress; acceptance remains with the independent PM.
**Baseline:** `initial-idea` at `e6d444e475e447e9f37951f16585bf496f804c9d`.
**Authorization:** [M6-001 owner authorization](../evidence/M6-001-authorization-20261030.md).

## Objective and fixed scope

Connect the accepted frozen M5 Double DQN policy to the existing M1 real-ALE VideoChess path. Preserve RGB as the authority for every Atari position; the complete UCI history and `python-chess` board track only verified moves and validate candidates. Run the approved bounded local CPU diagnostics and 35-attempt maximum Stage 3 roster, then retain hash-verifiable traces and a scientifically cautious report for independent PM review.

No training, fine-tuning, model selection from Atari outcomes, Stockfish use, cloud compute, uploads, G4 approval, release, self-acceptance, or merge is in scope. Preserve accepted M4/M5 artifacts and results.

## Dependencies and frozen roster

Dependencies are accepted M1 (`M1-001`), M4 (`M4-001`), and M5 (`M5-001`). Reverify the private M4/M5 stores and checkpoint bytes on the execution host before gameplay. The roster is fixed by the accepted Pre-M6 protocol and this owner's instruction:

- Primary: `m5-warm-seed-20261104-post-rl`, checkpoint SHA-256 `0b2405017a8e1d539851f0cd278883d3fd23936fb5c2f7962c813590a6fd1767`.
- Paired: `m5-scratch-seed-20261104-post-rl`, checkpoint SHA-256 `3749b0c0b6ae44d3ad5d6bf0863b60937a59fbe881e0bdf4932bdce6033ca400`.
- Frozen supervised control: `m4-behavior-only-seed-20261024`, checkpoint SHA-256 `724ac730f3c5f2d01b48b26eb7670a3c764978a3dd4d6702b3057a99ab1a90a4`.
- Existing baselines: `simple-material-heuristic`, `random-legal`.

M5 selection uses the lowest predeclared paired training seed, not M5 evaluation rank or M6 results. The paired M5 comparison is exploratory; it does not presume Warm-start superiority.

## Implementation order

1. Reverify authorization, artifacts, dependency lock, ROM, runtime versions, environment settings, frame/reward behavior, and resource budget.
2. Add an immutable verified-ALE decision context and a narrow adapter that rebuilds the board from the full verified history, validates RGB/shadow/FEN/side/legal candidates, and invokes existing frozen policy interfaces.
3. Extend the existing episode runner at the selector boundary only; independently revalidate the selected UCI move before `plan_move` and retain decision/RGB/controller evidence. Preserve existing selector API behavior for M1 callers.
4. Implement an append-only M6 attempt ledger, atomic trace/event hash chain, manifest verification, resource guards, raw-trace aggregation, Wilson interval for the primary move endpoint, and censored/incomplete accounting.
5. Cover the M5-to-ALE contract, profile/roster/seed immutability, ledger/summary integrity, stale/ambiguous/desynchronized states, terminal/reward/truncation, checkpoint errors, frozen inference, and unsafe-interruption paths.
6. Stage 1: one genuine frozen-Warm policy decision and RGB/controller verification under debug settings. Record any incomplete attempt; do not retry an uncertain action.
7. Stage 2: up to ten consecutive RGB-verified player moves and genuine Atari replies for Warm and Scratch under debug settings, then a bounded default-v5 reliability check only if debug is safe. A safe stop ends that attempt; preserve last verified state.
8. Freeze Stage 3 source commit, lock/ROM/artifact identities, config, roster, seeds/order, and run manifest before inspecting Stage 3 outcomes. Run all declared attempts serially under default-v5, within the 35-attempt, 10-hour, per-game time/frame, and 2-GiB artifact ceilings. Retry only pre-action process-start failure, with a distinct ledger identity.
9. Verify every raw trace/hash and rebuild summaries from attempt records. Run focused, M1, M4/M5, and full regression tests, preflight, archive checks, and diff/privacy review at the exact final feature HEAD.
10. Commit/push the feature branch and open one PR against `initial-idea`; leave M6-001 in progress pending PM acceptance. Do not merge or mark G4 approved.

## Acceptance mapping

| Criterion | Required implementation/tests | Required real-ALE evidence |
|---|---|---|
| M6-01 | Adapter validates stable RGB context, standard-start full history, reconstructed FEN/turn/candidates, and shadow agreement; rejection tests for invalid/stale evidence. | Decision records bind frame/hash to verified board, UCI history, legal candidates, and checkpoint identity. |
| M6-02 | Existing runner executes observe → validate → decide → act → verify; no state advancement on uncertain actions; interruption/reply-timeout/desync tests. | Stage 1 and Stage 2 show genuine policy decisions, confirmed input, multiple real Atari replies, and safe stops. |
| M6-03 | Frozen M5 loader/QPolicy only; tests ensure eval mode, no gradients/mutation/replay/optimizer/Stockfish. | Runtime process/package and policy provenance in each attempt; no engine process. |
| M6-04 | Ledger, hash-chain trace, aggregation, W/D/L/unknown/incomplete, Wilson move rate and denominator tests. | Every one of at most 35 Stage 3 reset attempts retained, including failures; completed games require supported ALE terminal/reward evidence. |
| M6-05 | Immutable debug/default profiles and runtime assertions. | Actual Gymnasium/ALE/ROM/settings captured per run; Stage 3 default-v5 only and never pooled with debug diagnostics. |

## Resource and stop conditions

Use one local CPU ALE process. Cap each Stage 3 game at 900 seconds and 54,000 ALE frames; cap aggregate Stage 3 wall time at 10 hours and compact M6 outputs at 2 GiB. Monitor wall time, frames, process RSS, inference/decision latency, trace writes, and artifact growth. Only a startup failure before an ALE action may be retried once. Once any action was executed, preserve that attempt and never retry/replace it. Stop the current attempt on mismatched artifacts, stale/ambiguous RGB, history/FEN/candidate mismatch, uncertain controller action, trace failure, ALE terminal, runner limits, or external interruption. Keep the last RGB-verified board/history; classify unknown/incomplete outcomes separately.

## Handover state

This plan does not itself satisfy M6 criteria. On engineering completion, submit raw and summarized evidence for independent PM review, update the task with actual evidence, and retain M6 authorization until the PM decides acceptance. G4 is not part of this transition.
