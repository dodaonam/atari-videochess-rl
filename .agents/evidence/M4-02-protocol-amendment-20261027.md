# M4-02 deterministic input-distinct sample amendment — 2026-10-27

**Protocol revision:** `M4-02-distinct-effective-inputs/1.0`
**Decision authority:** Project PM, exercising the project owner's explicit delegation for this mission.
**Effective/recorded at:** 2026-10-27T15:06:58Z.
**Scope:** M4-02 sample-selection rule only. This record does not authorize a change to ADR-0003, M3 data, labels, model, objective, numeric thresholds, or resource limits.

## Decision

For the 128-example M4-02 overfit sanity test, select exactly 128 training examples whose **complete effective `videochess-model-input/1.0` values are pairwise distinct**. The accepted M3 release, `played_move_uci` labels, architecture, seed, AdamW settings, 500-update cap, and thresholds remain unchanged: cross-entropy at most 0.05 and legal top-1 at least 99%.

## Original protocol and observed failure

The original `M4-02-fixed-128/1.0` rule selected the 128 lexicographically smallest training `sample_id` records. Its selected-ID SHA-256 was `cc7c30b0fb6c676ad4bf8b8e9b535af2c8a14a9b302949ac2c375defe4541634`. The preserved run `m4-behavior-20261027-r2`, at source revision `4562dddd80d302bdbb49e1191c97bd71ac7e9938`, exhausted 500 updates with CE `0.02195480228497465` and top-1 `126/128` (98.4375%); its CLI exit code was 2. The run and its original metrics remain failed historical evidence.

The read-only diagnostic at `e5e42f703bfd3386c94de17b607aa5102b60201f` verified two pairs of exactly equal complete input tensors and ordered UCI candidate identities with conflicting played-move targets. Since the deterministic scorer receives identical inputs for each member of a pair, at most one label per pair can be top-1 correct. The original sample's ceiling was therefore `126/128`, below the required `127/128`. The observed CE was also close to the two balanced conflicting pairs' empirical lower bound, `4 * ln(2) / 128 = 0.02166084939249829`. This is an acceptance-sample feasibility defect, not evidence that the accepted M3 release is corrupt.

The supporting immutable evidence is `.agents/evidence/M4-02-sanity-gate-blocker-20261027.md`, `.agents/evidence/logs/M4-02-sanity-gate-diagnostic-20261027.json`, and the original run under `/home/dodaonam/Projects/atari-videochess-rl-m4/artifacts/m4/m4-behavior-20261027-r2`.

## Revised deterministic selection rule

The executor shall:

1. Read the independently verified accepted M3 train partition only.
2. Order rows by ascending `sample_id`.
3. Encode each row using the existing `videochess-model-input/1.0` encoder.
4. Canonically serialize the **effective unpadded model inputs**, including explicit field names, schema, dtypes, shapes, bytes, history length/mask semantics, candidate count/mask semantics, and ordered semantic UCI strings.
5. Exclude `sample_id`, game/split/provenance fields, target indices/labels, PGN result/player data, future moves, and teacher values from identity.
6. Retain the first row for each previously unseen complete-input identity, irrespective of its target; skip subsequent exact-identity duplicates.
7. Continue until exactly 128 examples have been selected, retaining their ascending ID order.
8. Verify a matching digest against canonical bytes and verify that the selected identities match the unpadded values actually passed through the batch collator. A digest collision or insufficient distinct train inputs is an error.
9. Persist the rule/version, selected IDs and ordering, ID-list digest, all 128 input digests and their aggregate digest in the new run evidence.

The selector is deterministic, label-independent, train-only, and independent of source iteration order. It has no special cases for the two known conflicting groups.

## New-run acceptance and unchanged boundaries

The revised sanity run must initialize fresh weights with seed `20261022`, use the original authorized AdamW configuration, and pass both original thresholds within 500 optimizer updates. No weights from `r2` may be reused. The revised run is separate evidence; it does not convert the original failed run to PASS. Full training remains prohibited until the revised gate passes.

The following are unchanged: the exact accepted M3 release and split, all target labels, ADR-0003 input/model architecture, legal-candidate behavior cross-entropy, seed, update cap, numeric thresholds, 45-minute per-seed and 3-hour aggregate CPU budgets, 2 GiB RSS cap, parameter cap, validation-only selection, and all M4/M5 boundaries. No test data, new supervision, Stockfish score, or added feature may be used to choose the sanity sample.

## Authorization and state consequence

This dated mission decision authorizes implementation and execution of the revised selection protocol. It supersedes only the original fixed-128 sample-selection rule; it does not rewrite the historical rule or its failure. BLK-002 is resolved as a protocol blocker when this amendment is incorporated into canonical state. M4-001 returns to `in_progress` for the revised gate and subsequent authorized M4 work. M4-02 remains pending until the new run passes. M4-03/M4-04 and milestone completion still require their own measured evidence. G3 remains unapproved; M5/M6 remain out of scope.
