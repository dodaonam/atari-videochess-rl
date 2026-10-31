# PRE-M7 Readiness Evidence and Handover

**Assessment:** preparation package for independent PM review; this is not G4 approval.
**Repository baseline:** `initial-idea` / `fa7683822c436f3e9d6c3455a24cd1f4a6cbb463` (PR #15 merge).
**PR #14:** merged at `509f9f83f9249208fd5adba572efed2d2f0f82ff`; M6 accepted.
**PR #15:** merged at `fa7683822c436f3e9d6c3455a24cd1f4a6cbb463`; PM6C-F01 provenance closeout accepted.
**Current governance:** G0–G3 approved; initial independent PM G4 assessment is HOLD for incomplete evaluation evidence; G4/G5 unapproved. M6-001 is done. M7 is not started or authorized; its authorization record remains null.

## 1. Baseline and source verification

Live GitHub PR metadata and local merge objects verified both merges, merge parents, trees, PR states, and the exact requested baseline. The dedicated branch `feature/pre-m7-readiness` was created in a separate clean worktree from `fa7683822c436f3e9d6c3455a24cd1f4a6cbb463`. The pre-existing workspace's deleted tracked file and untracked files were left untouched.

PR #14 accepted M6-01–M6-05 at feature head `e919ee3ad039c9d2de3ebdf6b82704ecd61c0a6f` (tree `7eb06fd9c0e0b363ca324d203e1debf26f233c08`) and merged at `509f9f83f9249208fd5adba572efed2d2f0f82ff`. PR #15 was accepted at `b0d4a1303d2a639e164a9b9fb103bb442d366f1d` and merged at `fa7683822c436f3e9d6c3455a24cd1f4a6cbb463`. The current feature branch's parent is the exact PR #15 merge commit.

At baseline, canonical preflight passed with one expected warning that ignored artifact directories require independent manifests. Canonical state reported G3 approved, M6 done, G4 unapproved, M7 pending owner authorization, no active task, and no M7 authorization record. The PR must preserve those conditions.

## 2. Read-only artifact integrity verification

The run records contain UTC start/end, exit code, source revision, sanitized command, and sanitized log path. The immutable private roots themselves were read only and were not copied into this branch.

| Input | Session verification | Reconciled identity |
|---|---|---|
| M4 r4 | `python -m videochess_rl.model.cli verify-artifacts <accepted-m4-r4-root>`; exit 0; 19 manifest-listed files. | Checkpoint `724ac730f3c5f2d01b48b26eb7670a3c764978a3dd4d6702b3057a99ab1a90a4`; sidecar `63615d8d0ed27900fdf86d3f3084ca95cd562f9ec2f9a7e94bca4b0f6301e0c8`; artifact manifest `f00fde1c59325105e0ffd45bb45eb269dfa303416010c9a0b6c6be47bd9a9921`. |
| M5 root | `python3 scripts/m5_artifact_manifests.py --root <accepted-m5-root> --verify`; exit 0. | 7 manifests / 6,544,747,450 bytes; root manifest `a201a254671ad59ae1fecb402abf994d5bf523097f1c3010b5c7fa237ae6dd4c`; all listed run inventories verified. |
| M6 v1 and v2 raw roots | `python3 scripts/audit_m6_v2_artifacts.py --root <local-preserved-v2-root> --v1-root <local-preserved-v1-root>`; exit 0; read-only standard-library audit at source `fa7683822c436f3e9d6c3455a24cd1f4a6cbb463`. | V1: 4,540 files / 616,539,017 bytes, root manifest `22ac6ec7e0f4a48f52b2452654d4adecaf111f38ea37f5d9517f173c838716d7`, 35 starts/resets/finishes. V2: 4,159 files / 728,148,524 bytes, root manifest `bc0068aa2254e4c15165247ee299f48940cca9b7c21f6a288fd13812631ea2b2`, 20 attempts/traces/manifests. |

Exact machine summaries and retained logs:

- [M4/M5 input integrity report](PRE-M7-input-integrity-20261031.json), [sanitized verifier log](logs/PRE-M7-input-artifact-verification-20261031.log), log SHA-256 `83c41b29497a1ae373ef34f8a41188fc735164a9fffcd125e3ec41ea3bde1412`.
- [M6 read-only audit report](PRE-M7-M6-readonly-audit-20261031.json), [audit provenance log](logs/PRE-M7-M6-readonly-audit-20261031.log), stdout SHA-256 `467788cdc5ec5b291bd0d7aa66c987f9beac14c2b51395b1101f0963fadd5197`.
- [Current local resource snapshot](PRE-M7-resource-snapshot-20261031.json): 8 logical CPUs, 24.91 GB available RAM, 50.71 GB available filesystem at `2026-10-31T14:22:18Z`. This is a point-in-time host observation, not a future resource reservation.

M6 v2 raw outcomes were independently reconstructed: 11 ALE-terminal losses, zero terminal wins/draws, 9 incomplete attempts (5 opponent-response timeouts, 2 source-selection uncertainty stops, 2 target-navigation uncertainty stops), 385/405 RGB-verified initiated moves, 385 verified replies, zero board desynchronizations, 1,871 corrected cursor displacements, and zero resource stops. V1 and v2 remain separate protocol identities; v2 reused v1 seeds under an extended horizon. PM6-F06's original manifest discrepancy remains immutable and paired with its erratum. RSK-014 remains the accepted M5 historical source-reconstruction limitation.

The preserved M6 trees were present in the original local workspace at `artifacts/m6-preserved-20261031/{v1,v2}/...`. The clean feature worktree did not contain those local artifacts; the audit accessed the existing preserved paths read only. No ROM, private checkpoint, raw RGB, dataset, credential, or artifact payload was staged or uploaded.

## 3. Deliverables and governance preservation

The package adds the readiness assessment/owner decision register, M7 work plan, proposed versioned evaluation protocol, canonical pending task records, provenance summaries, resource snapshot, and focused standard-library contract tests. M7 task IDs `M7-001`–`M7-005` map one-to-one to M7-01–M7-05. M7-001–003 are G4 evaluation work; M7-004–005 require G4 completion and are G5 delivery work. All five remain pending; state keeps `start_authorized=false`, the authorization record null, active task null, and next task `M7-001`.

No M4/M5/M6 acceptance report, result, configuration, checkpoint, raw evidence, or frozen manifest was modified. No official new simulator/ALE campaign, training, fine-tuning, cloud allocation, or Stockfish evaluation/opponent use occurred. This report, the candidate PR, and passing CI do not grant M7 authorization or G4/G5 approval.

## 4. Verification record

| Check | Source / tree | UTC / exit | Retained evidence |
|---|---|---|---|
| Canonical preflight | Candidate tree `65aafcb957a18b1012e019a03453f1ff8609830f`; source base `fa7683822c436f3e9d6c3455a24cd1f4a6cbb463`. | PASS, exit 0, 2026-10-31T14:48:16–14:48:17Z; expected ignored-artifact manifest warning only. A post-checkpoint standalone rerun also passed with exit 0. | [Retained preflight log](logs/PRE-M7-final-preflight-20261031.log), SHA-256 `bf349866395cc3b36ae4237327c429958a5a829bf19233fc05813960aa8e9bae`. Latest summary: 15 tasks done, five M7 tasks pending, no active task/blocker, G3 approved, G4/G5 unapproved, M7 unauthorized. |
| Focused Pre-M7 contracts | Candidate tree `fc33fc660ec2d87fcbc3606c9531550feb1f9d61`, source base `fa7683822c436f3e9d6c3455a24cd1f4a6cbb463`; Python 3.12.3. | 8 tests passed, exit 0, 0.012 seconds, 2026-10-31T14:31:27Z. | [Focused contract log](logs/PRE-M7-focused-contract-tests-20261031.log), SHA-256 `d2015772953bbcfc5e1db245c27d5b14dce36dd0af461d9445497fd84f431769`. |
| Committed-link contract | Commit `74132316b31f39c1ab638404cdee72d9cf86d9c6`, source tree `98de51af2710038cc5b55e7a98cbdbcbf09d6392`; Python 3.12.3. | 8 tests passed, exit 0, 0.082 seconds, 2026-10-31T14:58:47Z. | [HEAD-link contract log](logs/PRE-M7-head-links-contract-tests-20261031.log), SHA-256 `10eddad002d62db3d53a20b2a5fd5dc0ee4bca7c123591349bf522f78ca60ba7`. The test requires every local Markdown target in committed `HEAD`, covering the clean-clone failure. |
| Full local repository suite | Candidate tree `9891c8a28edb46ffbbb0ba493e421f3c615558a8`, source base `fa7683822c436f3e9d6c3455a24cd1f4a6cbb463`; Python 3.12.3, local CPU, accepted M4 r4/M5 roots and M5 Warm checkpoint re-resolved by manifest SHA. | 462 tests passed, exit 0, 166.905 seconds, 2026-10-31T14:43:16–14:46:05Z. | [Full-suite log](logs/PRE-M7-full-suite-pass2-20261031.log), SHA-256 `175391408d1a659923a953763a740cf23866c69bf13eacc09e326f6b3cc8ea05`. The only Stockfish invocation was the existing UCI readiness `ping` smoke test; no search, inference, opponent, or benchmark role. |
| Final full repository suite on committed link fix | Commit `74132316b31f39c1ab638404cdee72d9cf86d9c6`, source tree `98de51af2710038cc5b55e7a98cbdbcbf09d6392`; Python 3.12.3, local CPU, M4/M5 private roots verified, M5 Warm checkpoint re-resolved from manifest SHA. | 462 tests passed, exit 0, 190.985 seconds, 2026-10-31T14:58:56–15:02:09Z. | [Final full-suite log](logs/PRE-M7-full-suite-final-20261031.log), SHA-256 `8ad166fe7574a699623fce19e53d338efbe2bff30775466e2daa13565a610a0b`. Includes clean-clone recovery and committed-link regression. |
| Frozen artifact identity audit | `fa7683822c436f3e9d6c3455a24cd1f4a6cbb463`; read-only. | M4 0; M5 0; M6 v1/v2 0. | Links above. |
| Git diff / accepted-file preservation | Audited against `origin/initial-idea` at `fa7683822c436f3e9d6c3455a24cd1f4a6cbb463` before commit. | `git diff --cached --check` and `git diff --check` pass. No M4/M5/M6 acceptance reports, configs, run logs, checkpoints, private data, or raw artifact paths are modified or staged. Changes are limited to Pre-M7 plans/protocol/evidence, five pending M7 task records and state/handoff/checkpoint pointers, and two focused governance test updates/additions. | Dedicated feature worktree is clean before commit; the original dirty workspace was not modified. |
| GitHub PR checks | PR #16 initial head `a40588bc8a6fed81d1cb99c64035d1b7e09d7bc3`, base `initial-idea` at `fa7683822c436f3e9d6c3455a24cd1f4a6cbb463`. | Initial Repository preflight CI failed in `Validate canonical context` at 2026-10-31T14:51:51Z due two report links to ignored local audit logs omitted from the commit. A later 462-test run caught the same clean-clone defect because the logs were staged but absent from `HEAD`. | [CI diagnostic](logs/PRE-M7-CI-preflight-diagnostic-20261031.log), SHA-256 `616507e6ada4a71a756482717015dd326e7a35e4c834b753be4da442df3016d0`. Commit `7413231` commits both logs and makes the link contract require each local target in `HEAD`; the final 462-test suite now passes on that commit. Fresh CI on the next pushed PR head remains required. PR #16 is open, non-draft, and unmerged. |

### Retained diagnostics and remediation

- The first focused Pre-M7 contract run (8 tests, exit 1) found three incorrect assumptions in the new assertions: it treated the existing tracked M1 checksum manifest as a private payload, searched for an unnegated strength claim by substring, and set a higher link-count expectation than the package needed. The test now permits checksum manifests while rejecting private binary payloads, checks the negated claim in context, and verifies every actual local link. The log is [initial focused diagnostic](logs/PRE-M7-focused-contract-tests-initial-diagnostic-20261031.log), SHA-256 `c86fc43b3c47fd73d1266ca38e6418599ef7ed078a6f7ebb8ee93fab0525e673`.
- The second focused run (8 tests, exit 1) left one assertion searching for a sentence the readiness plan expressed as a no-upload rule in the M7 plan. The test now asserts the explicit `do not upload` handling. The log is [focused remediation diagnostic](logs/PRE-M7-focused-contract-tests-remediation-diagnostic-20261031.log), SHA-256 `0b83903c8be2c16d619d73c99fb9c1a17dd4a642fba4699974a3bc610d5b348e`.
- A 63-test context/protocol focused run at candidate tree `e3ff015afd07bec80e1401e0cee84099deab3d6d` failed one recovery assertion because changes since the previous checkpoint made its saved Git snapshot stale. The checkpoint was refreshed at `cp-fa768382-20261031T144244123215Z`; preflight passed, and the final 462-test suite passed the same recovery test. See [focused context diagnostic](logs/PRE-M7-focused-context-contract-tests-20261031.log), SHA-256 `7382c279ff245779234aa41b7e2bac471a201db89041a02233c1242d497f073a`.
- The first 462-test full-suite run found that the accepted-M6 state regression still expected `next_task_id=null` after future pending M7 tasks were added. The regression now asserts `next_task_id=M7-001` while preserving `active_task_id=null`, G4 unapproved, and no M7 authorization. See [full-suite diagnostic](logs/PRE-M7-full-suite-diagnostic-failure-20261031.log), SHA-256 `b6015e3faac45ec3a779ea4dbbfa64be7b4b617eae777f8d862e02594f4b654e`.
- The second 462-test run found a harness-only typo in the private Warm checkpoint path. The expected checkpoint was re-resolved from the verified M5 manifest and its SHA-256 rechecked before the final run; no test assertion or artifact was changed. See [checkpoint-path diagnostic](logs/PRE-M7-full-suite-diagnostic-checkpoint-path-20261031.log), SHA-256 `433f8d5161381d80b915d116ed77956e5e241fbf613cb407c3141a3ca3c337b4`.

The final full suite includes the pre-existing M4/M5/M6 regression tests plus eight Pre-M7 contracts. Both full-suite diagnostics and both focused-test diagnostics remain distinct from the passing records; none is relabeled as a pass.

The initial PR CI failure was a clean-checkout portability defect: the input verifier logs existed in the executor worktree but were ignored by Git, so this report's links resolved locally and failed in CI. The corrective changes stage those two sanitized logs and make the focused link check reject untracked local targets across the report, plans, and protocol. This is an engineering correction, not an evaluation or authorization change.

A local clean-clone regression showed that `git ls-files` can see a staged file even when the commit/clone lacks it. The focused test now requires local link targets in committed `HEAD`; both verifier logs are committed at `7413231`. The final full suite reran against that commit and passed 462 tests.

## 5. PM review checklist and next action

1. Review the exact baseline/merge identities and M6 acceptance qualifications.
2. Inspect the M4/M5/M6 manifest identities, session read-only audit results, and local-private boundaries.
3. Review simulator-vs-ALE separation, v1/v2 non-pooling, incomplete/truncation handling, seed clustering, and Elo restrictions in the proposed protocol.
4. Review the pending M7 task graph and G4/G5 criterion allocation; confirm the task records do not imply start authorization.
5. Decide G4 independently. G5 remains a later delivery decision.

The project owner must separately authorize M7-001 after the applicable G4 decision and approve any new evaluation population/resource envelope. No decision in this evidence report is represented as already approved.
