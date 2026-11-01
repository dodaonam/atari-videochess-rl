# Project Owner Final Research-Scope Decision — M0–M7

**Decision date:** 2026-11-01 (session date; no exact issuance time asserted)
**Authority:** Project Owner, direct user instruction in the current execution context
**Project:** `atari-videochess-rl`
**Scope:** Research execution and experimental results across M0–M7
**Repository context:** PR #21 governance-closeout remediation; prior integrated baseline `0b9c4c26ee1d0952a5f9e3b7cd405f5bf4e3008b`

## Decision

The Project Owner states that **the currently accepted research and experimental results are the final results of this project**. Existing negative and inconclusive findings are accepted as the project's final research evidence.

No further supervised pretraining, behavior-cloning training, Double DQN training, fine-tuning, simulator evaluation, ALE evaluation, training-seed expansion, opponent campaign, Elo-calibration campaign, model-selection campaign, or new research milestone is requested or authorized by this decision. Existing accepted experimental artifacts are not to be regenerated, overwritten, or replaced.

The decision closes the future research-execution scope. It preserves the accepted results and all recorded limitations. It does not claim that the model plays strong chess, that RL or Warm-start is superior, that compared policies are equivalent, that results generalize broadly, that Elo is established, or that external course requirements are satisfied.

## Evidence scope and limitations

This decision accepts the existing accepted evidence tracks as final without changing them:

- M3 source, final r6/r7 dataset, and teacher evidence.
- M4 supervised behavior-model evidence.
- M5 simulator Double DQN evidence.
- M6 Stage 3 v1 and v2 as distinct Atari profiles.
- M7 Option B Atari campaign and raw-derived analysis.

M7 remains 90 scheduled and started/reset-observed attempts, 60 terminal White losses, 30 incomplete attempts, zero observed wins, and zero observed draws. Only 9/30 Warm/Scratch matched cells had terminal observations; no valid paired confidence interval was available. Incomplete attempts are not terminal outcomes. Existing limitations including O-02, O-06, RSK-014, PM6-F06, limited training-seed replication, controller uncertainty, White-only evaluation, and the single Atari opponent configuration remain disclosed.

The decision does not retroactively change experimental records, artifact identities, metrics, analysis, or Independent PM acceptance scope.

## Publication and release boundary

This research-scope decision **does not authorize publication or distribution** of ROMs, models, checkpoints, datasets, raw records, private manifests, RGB frames/traces, or other restricted artifacts. It also does not state a blanket owner prohibition on all publication. The separate status is: no affirmative authorization to publish restricted artifacts is established in the reviewed evidence, and no release is part of this closeout task. Any future publication/distribution requires a separate, explicit, scope-specific owner decision and applicable rights, privacy, integrity, and scientific-claims review.

The provenance correction for the earlier unsupported no-release attribution is recorded in [G5-F02 provenance erratum](G5-F02-provenance-erratum-20261101.md).

## Provenance

This decision is recorded from the direct Project Owner instruction in the current user message for the final M0–M7 closeout assignment. The instruction is available in the current execution context, but it does not provide a separate GitHub issue/comment URL, signed decision artifact, or exact issuance timestamp. None is invented here. The recording date is the execution environment's session date only.
