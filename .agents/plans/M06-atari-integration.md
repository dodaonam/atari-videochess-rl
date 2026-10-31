# M06 — Atari Integration and Evaluation

**Task:** M6-001
**Status:** authorized and in progress; acceptance remains with the independent PM.
**Baseline:** `initial-idea` at `e6d444e475e447e9f37951f16585bf496f804c9d`.
**Authorization:** [M6-001 owner authorization](../evidence/M6-001-authorization-20261030.md).

## Objective and fixed scope

Connect the accepted frozen M5 Double DQN policy to the existing M1 real-ALE VideoChess path. Preserve RGB as the authority for every Atari position; the complete UCI history and `python-chess` board track only verified moves and validate candidates. The initial v1 execution used the original bounded local CPU diagnostics and 35-attempt maximum Stage 3 roster. After the v1 review, the separately authorized v2 continuation ran a 20-attempt M5-only extended-horizon schedule; its distinct protocol and actual outcomes are recorded below and in the final v2 report.

No training, fine-tuning, model selection from Atari outcomes, Stockfish use, cloud compute, uploads, G4 approval, release, self-acceptance, or merge is in scope. Preserve accepted M4/M5 artifacts and results. The original 35-attempt Stage 3 plan describes v1; the separately authorized v2 addendum supersedes only the follow-on corrective schedule, which contains 20 frozen M5 attempts and does not rerun controls.

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

Use one local CPU ALE process. Cap each game at 900 seconds and 54,000 ALE frames; cap cumulative M6 gameplay across Stages 1–3 at 10 hours and compact M6 outputs at 2 GiB. The 10-hour clock includes diagnostic gameplay and is enforced cumulatively across run manifests. Monitor wall time, frames, process RSS, inference/decision latency, trace writes, and artifact growth. Only a startup failure before an ALE action may be retried once. Once any action was executed, preserve that attempt and never retry/replace it. Stop the current attempt on mismatched artifacts, stale/ambiguous RGB, history/FEN/candidate mismatch, uncertain controller action, trace failure, ALE terminal, runner limits, or external interruption. Keep the last RGB-verified board/history; classify unknown/incomplete outcomes separately.

## Handover state

This plan does not itself satisfy M6 criteria. On engineering completion, submit raw and summarized evidence for independent PM review, update the task with actual evidence, and retain M6 authorization until the PM decides acceptance. G4 is not part of this transition.

## Owner-authorized corrective continuation — Stage 3 v2

The owner issued a separate bounded continuation after the v1 review. Its direct authorization is recorded in [M6-001-v2-corrective-authorization-20261031.md](../evidence/M6-001-v2-corrective-authorization-20261031.md). It supplements the initial M6 authorization and does not change v1 records or claim PM acceptance. The executable contract and frozen values are owned by [`m6-stage3-v2.json`](../../configs/m6/m6-stage3-v2.json) and the v2 addendum in [`M6_ALE_EXPERIMENT_PROTOCOL.md`](../../docs/04-research/M6_ALE_EXPERIMENT_PROTOCOL.md).

### Corrective execution order

1. Resolve PM findings against code and immutable v1 traces: separate the runner frame cap from ALE's registered/native horizon; distinguish budget-censored, controller-uncertain, ALE-terminal and unknown final moves; classify cursor displacement correction and board disagreement separately; name validation, policy selection and adapter-total latency independently; and reject nonfinite/unsupported terminal rewards as unknown.
2. Add v2-only configuration/runner limits and tests. Keep v1's config, 54,000 action-frame cap, 108,000 registration default and source/run identities unchanged. Load only the two pinned M5 policies for v2.
3. Verify the installed constructor and emulator report the requested 500,000 `max_num_frames_per_episode`; assert all runtime profile fields and ROM. Verify all selected checkpoint/sidecar/root hashes, CPU deterministic inference, frozen weights, dependency-lock match, schedule hash, v1 artifact integrity, ≥12 GiB free storage, and RSS monitoring.
4. Run focused M1/M6 tests and the complete test suite. Run canonical preflight and inspect task/archive state. Commit the exact code, tests, config, plan, and authorization evidence before writing the v2 run manifest.
5. Freeze a deterministic run identity derived from source commit/tree, config SHA-256 and 20-row schedule SHA-256. The manifest records the 500,000 ALE ceiling, 432,000 post-reset action-frame runner cap and reset counter origin before the first official outcome.
6. Execute every scheduled pair serially under the extended-horizon profile. Continue after ordinary incomplete attempts; never retry a reset attempt or replay uncertain input. Respect 1,800 seconds, 432,000 action frames, 200 player moves, 40,000 reply frames, 12-hour campaign, 8 GiB new v2 output, 128 MiB finalization reserve, 12 GiB entry free-space threshold, 6 GiB process RSS, and one pre-action retry.
7. Stream-verify the ledger; validate per-attempt traces/RGB/manifests; rederive outcomes, move censoring, cursor diagnostics, replies, and runtime metrics; verify v1 remains unchanged; report each policy and seed separately. V1/v2 are not pooled, and reused ALE seeds are not independent held-out evidence.
8. Update M6-001 evidence and PR #14, keeping M6 in progress pending PM review and leaving G4 unapproved. If the resource ceiling or safe-stop conditions leave either M5 arm without ALE-terminal evidence, report M6-04 as partial.

### Corrective verification/acceptance evidence

| Concern | Required software evidence | Required v2 runtime evidence |
|---|---|---|
| F01/F02 horizon | V1/v2 limit-separation tests; environment wrapper passes configured horizon; runtime check reads the effective ALE integer | Constructor/runtime record shows registration 108,000 and actual instance 500,000; each attempt reports reset frame and post-reset action frames; no inherited 108,000 truncation |
| F03 move censoring | Disjoint final-move category accounting; attempted/verified numerator/denominator invariants; Wilson dependence note | Per-attempt and per-policy counts for each category, including unknowns |
| F04 cursor motion | Tests for overshoot/replan, no progress, ambiguous/unlocated observations, and stable board mismatch stop | Raw cursor events and aggregate corrected/unresolved/ambiguous/mismatch counts; board desync remains separate |
| F05 timing/outcomes | Latency field tests; positive/negative/zero/NaN/infinite/unsupported reward tests | Separate policy chooser, input validation, adapter total, and end-to-end decision latency; ALE terminal flags/reward verified against trace |
| Fixed roster/schedule | Exact hash/config/schedule and uniqueness tests | One manifest before first result; two policies × ten seeds, all scheduled slots accounted |
| Reproducibility/resources | Streaming hash-chain/summary regression, duplicate IDs, interruption, cap handling | Hash-verified attempt artifacts, run summary, free space/RSS/wall/frame/resource observations |

### Recorded v2 execution outcome

Stage 3 v2 executed all 20 scheduled resets with no startup retry, omitted slot, or resource stop. The raw trace/manifest reconstruction passed on the frozen source identity. Eleven attempts reached ALE termination and were losses (Warm 4, Scratch 7); nine remain incomplete (five reply timeouts, two source-selection stops, two target-navigation stops). Both policies therefore have genuine full-game terminal evidence, while incomplete outcomes remain outside W/D/L. The primary RGB-verified move rates were 222/232 for Warm and 163/173 for Scratch. See the [final engineering report](../evidence/M6-001-final-report-v2-20261031.md), [execution record](../evidence/M6-stage3-v2-execution-record-20261031.json), and [post-run verification](../evidence/M6-stage3-v2-postrun-verification-20261031.json). M6-001 remains in progress pending independent PM acceptance; G4 remains unapproved.

## Final corrective closeout — PM6-F06 and raw-evidence audit

The independent PM's PM6-F06 finding identified an incorrect v2 metadata boolean: the frozen v2 scope excludes diagnostics, while the original manifest records `gameplay_wall_budget_includes_diagnostics=true`. The original raw manifest and its sanitized derived copies remain unchanged. The schema-aware source correction and immutable-evidence erratum are recorded in [PM6-F06 erratum](../evidence/M6-PM6-F06-erratum-20261031.md); v1 continues to record its diagnostic-inclusive semantics.

The read-only independent audit is documented in [the r3 human report](../evidence/M6-stage3-v2-independent-raw-audit-20261031-r3.md) and [machine report](../evidence/M6-stage3-v2-independent-raw-audit-20261031-r3.json). It independently verified all v1/v2 artifact paths and hashes, the complete v2 ledger/trace chains, 20 unique schedule slots and resets, policy/checkpoint identity, reward/terminal evidence, per-attempt move/reply/history/censor records, cursor diagnostics, frame origins and resource ceilings. The reconstructed outcomes remain 11 ALE-terminal losses and nine incomplete attempts; no incomplete attempt is a draw. V1 and v2 remain separate datasets.

The original raw roots under `the isolated execution worktree at repository-relative `artifacts/m6/`` were preserved in place. A second local copy was verified under the repository's ignored artifact store at `artifacts/m6-preserved-20261031/{v1,v2}/`; no raw bytes, private model, or ROM were added to Git or uploaded. The M5 root inventory was reverified read-only. Details and exact hashes are in the audit record.

The correction does not change the v2 config, schedule, enforcement arithmetic, checkpoint roster, or any gameplay result. No Stage 3 attempt, ALE reset, training run, or fine-tuning was performed during this closeout. M6-001 remains `in_progress` pending separate independent PM acceptance; G4 remains unapproved and M7 remains unauthorized.
