# M5 Post-Review Remediation Audit

**Recorded:** 2026-10-30 UTC
**PR:** [#11](https://github.com/dodaonam/atari-videochess-rl/pull/11), base `initial-idea`
**Status:** remediation in progress; no merge or PM acceptance claimed.

## Executive result

The reported 28 GitHub preflight failures were reproduced in a clean clone of PR head `575dce5978567417d2915d5dd36a47873293b607`. Each failure was a verified M5 command/test evidence entry whose referenced `.log` file was missing from that clone. All 28 source logs existed in the local project worktree, matched their recorded checksum when present, and contained the recorded command, result, and exit code. The root cause was `.gitignore` rule `*.log`; Git treated all 28 logs as ignored/untracked. They were force-added by exact evidence-reference list, totaling 778,449 bytes. A preflight regression check now rejects a locally present but untracked M5 evidence log. No log content was replaced or backdated.

The private artifact root manifest verifies 7 manifests and 6,544,747,450 bytes. A read-only cross-check verified six run summaries/attempts, all replay chain counts, 15 per-policy raw schedules, 3,385 event records, 1,500 unique scenarios, the exact 6 truncations, and the ledger arithmetic. See `.agents/evidence/M5-remediation-log-inventory-20261030.json` and the retained verifier logs.

A training source-version blocker remains. The first four runs use source SHA `093992c50e893a7fdd92f2f95faafe28d4f1e73c7351a4a8179a3056c4e63b00`; the last two use `cdcc1fdc0ca0b324e49cfb8b0ff571496a554e9892dfb3620d6454a65ee16da0`. Checkpoint history identifies three Python files changed between the relevant snapshots, but their old bytes are absent from the available Git objects and local backups. Because `replay.py` changed and its old sampling implementation cannot be compared, the possibility of a training-distribution change cannot be ruled out. Do not silently treat the pooled three-seed result as source-homogeneous or start extra training without PM disposition.

## Initial-state inventory

| Evidence/resource | Path | Initial status at review | Verification |
|---|---|---|---|
| Canonical repository | `/home/dodaonam/Projects/atari-videochess-rl-m5` | Git worktree, feature branch | HEAD `575dce5`; PR #11 OPEN; no training/evaluation process running. |
| M5 implementation/config/docs/tests | tracked PR branch | Tracked in Git | Config SHA `84d305084397ad18397dfe395fab58de824fa056729675d0d1cd9ca8bdd06d8d`; changes are reviewed on this branch only. |
| 28 verified M5 command/test logs | `.agents/evidence/logs/M5-*.log` (see table below) | Present locally; ignored by `*.log`; absent from remote clean clone | Each path/hash/size/command-result-exit verified; secret-pattern scan reported no matches; exact files force-added. |
| M5 run/evaluation source manifests and campaign evidence | `.agents/evidence/M5-*-20261029.*` | Tracked evidence; large model/replay/game data not Git tracked | Report hashes and run/source identity groups reconciled with local artifacts. |
| M5 private artifacts | `artifacts/m5/` | Ignored/private local files | Root artifact manifest verified; 6.544 GB of 8 GiB. No artifact was edited. |
| Accepted M4/M3 inputs | `/home/dodaonam/Projects/atari-videochess-rl-m4/...` and `/home/dodaonam/Projects/atari-videochess-rl-m3/...` | Private paths outside Git | M5 accepted-input evidence pins M4 checkpoint SHA and M3 release manifest; this remediation did not transfer or publish their contents. |
| Historical seed-20261106 predecessor source blobs | Old `checkpoint.py`, `cli.py`, `replay.py` contents | **Missing/unrecoverable from inspected Git objects and local source backups** | Only checkpoint-history SHA-256 values remain; this is the unresolved scientific-provenance issue. |

## The 28 provenance logs

All 28 log references were present locally. A declared log checksum, when present, matched the actual bytes. Every log contained the evidence entry's command and result plus `Exit code: N`. No token, private-key, bearer-token, AWS-key, password, API-key, or secret pattern matched. Initially all 28 were ignored and not in the Git index; they are now included by exact path.

| Evidence index | Repository-relative log path | Size bytes | SHA-256 |
|---:|---|---:|---|
| 4 | `.agents/evidence/logs/M5-focused-suite-final-20261028-command.log` | 6125 | `fdbee71364c1eea58a599d1b9600303d0886d490faf3d64d7005028cc93ed01d` |
| 5 | `.agents/evidence/logs/M5-full-suite-final-20261028.log` | 60516 | `378eb2d19514887d7369af9c17828571e6fd9ab571efe12157807e9681dd6be5` |
| 6 | `.agents/evidence/logs/M5-real-replay-profile-attempt-0005.log` | 4944 | `c7fed31748ffaab466a51313d33f037c68375c33aeb510063b27634b4e6c21b8` |
| 7 | `.agents/evidence/logs/M5-focused-suite-final-20261028-r2-command.log` | 6889 | `3f3c1d71ba91a4e739410c2a607cada1e953b52c1ce781c73029d238e420ac6f` |
| 8 | `.agents/evidence/logs/M5-full-suite-final-20261028-r2.log` | 61827 | `9e82650b1178abb5e4b9600e2d5fe4e7354d2d7ae37b8b28a24d23557dccfa33` |
| 9 | `.agents/evidence/logs/M5-full-suite-final-20261028-r3.log` | 61111 | `828a3def4d95fe62729af8ed66823d04bf7cec1fa9fbd47847b26dbed19a5f70` |
| 10 | `.agents/evidence/logs/M5-full-suite-final-20261028-r4.log` | 61165 | `118c2472a97e274fbf7aa95a942282dc5b551df4162680e81458cb443ddadafb` |
| 12 | `.agents/evidence/logs/M5-train-initial-attempt-failure-20261028.log` | 3833 | `328d03fbb062c57fc0f656ef9092ce3869d89576c2c99b07fee7eb8f22fe6135` |
| 13 | `.agents/evidence/logs/M5-focused-suite-after-recovery-fix-20261028-command.log` | 6955 | `235dfa44faddb18f4581457282379e987cf78e67684f9c765cfd207dc830686e` |
| 14 | `.agents/evidence/logs/M5-checkpoint-restore-validation-20261028.log` | 2256 | `4c264ca3c59ec81a84d2b77cd48771ccb728536e3a9489fe91addee80438fb9c` |
| 15 | `.agents/evidence/logs/M5-full-suite-after-recovery-fix-20261028.log` | 61237 | `90a1208252c22b2cd896272e6b76d33f2ea96a37c970ff20b9858140ebb8a82c` |
| 16 | `.agents/evidence/logs/M5-train-attempt1-snapshot-metadata-failure-20261028.log` | 1921 | `397622ce79e72b6d38bbb12edc9d239f266064b1b0aaedb70e83c8f7525ea4e1` |
| 17 | `.agents/evidence/logs/M5-focused-suite-snapshot-compat-20261028-command.log` | 7193 | `9c3ac4b2f80f78f0bd4596f629063f8cc70392ec37c42adee638f59a9a0faf5f` |
| 18 | `.agents/evidence/logs/M5-initialization-snapshot-compat-validation-20261028.log` | 3652 | `edc36781ae49bd81d415534414bc1af7be2a5d96d79caadc4e1cce993af177cc` |
| 19 | `.agents/evidence/logs/M5-full-suite-snapshot-compat-20261028.log` | 61476 | `e70852899f1fe6280493875609f9a678066bb1ad595b5ca486a0b154e3c46813` |
| 24 | `.agents/evidence/logs/M5-checkpoint-restore-verification-20261106-command.log` | 3934 | `5e3e540878bea4feb403eed39a5b636cdf5ea17ada8316fd461bb5661a2dfd95` |
| 25 | `.agents/evidence/logs/M5-focused-final-discovery-20261029.command.log` | 8423 | `8663798649515e35f1c3826085f72a6418019e83cf6377989f4427a6c0455267` |
| 26 | `.agents/evidence/logs/M5-full-suite-final-20261029.command.log` | 63324 | `89c305a3f2c5d8b23e9cdfe8c37762a4c98a8fbb6641e043bf93e3f46e9d4ab7` |
| 27 | `.agents/evidence/logs/M5-full-suite-environment-failure-20261029.command.log` | 64708 | `479a2b5e183ce94dfd02c69496fe716c596b8757580b55c68b4dba14e9b00cd5` |
| 28 | `.agents/evidence/logs/M5-focused-direct-module-path-failure-20261029.command.log` | 10199 | `ab5ed637cc89582ea644b7352e0e26a1378d032cce21e5fb880acd144de954f5` |
| 29 | `.agents/evidence/logs/M5-full-suite-final-evaluation-journal-20261029.command.log` | 63318 | `b3c1093993f5f848f140f8cf2626fe5d2cfe9c3ebec8e0fcdca1093e70787ae9` |
| 30 | `.agents/evidence/logs/M5-focused-post-identity-check-20261029.command.log` | 7590 | `fa825558a09628cd7c4f1868719c617f0425a275b1d9047efd3b5fdffd37891d` |
| 33 | `.agents/evidence/logs/M5-evaluation-official-20261029.command.log` | 79035 | `09df63d5fb9fe1b287008de9a0c92ef2e7f0253e6c5fd85ed59e300d4f8af3c9` |
| 34 | `.agents/evidence/logs/M5-evaluation-capped-sensitivity-import-failure-20261029.command.log` | 1733 | `f87dd9c4e1e0b0b4b500c70233345b25cced3318c685ca7774486a90e324c997` |
| 35 | `.agents/evidence/logs/M5-evaluation-capped-sensitivity-20261029.command.log` | 1785 | `90a1f89e2af3e70c518495353859812be3681f2ccb1bd1787e0a0df55424ccac` |
| 36 | `.agents/evidence/logs/M5-final-report-hash-20261029.log` | 188 | `8ca488dc06e2224541c3b0ed1b533e7e1d55ecc30e09a4df49a7c9e5ac526754` |
| 37 | `.agents/evidence/logs/M5-full-suite-final-closeout-r2.log` | 62342 | `7c452634e0241695bc7a9570fa72ecbafd317086bc06d14ae52d48557289bd7e` |
| 38 | `.agents/evidence/logs/M5-PR-11-verification-20261029.log` | 770 | `a87152496dd14bcde49af6fb52e46337994dd104cb889f32eeb975e48a38c993` |


The clean-clone failure reproduction is retained at `.agents/evidence/logs/M5-pre-fix-clean-clone-preflight-575dce-20261030.log`: a clean clone at the failing remote head returned exactly 28 `TASK_EVIDENCE_PROVENANCE` failures for `BACKLOG.yaml:tasks[13]`, exit code 1. The later tracked-log guard has a regression test in `tests/test_agent_context.py`.


### Detailed log inventory

The initial Git state was `ignored/untracked`; remediation force-added these exact paths. Local existence and file hashes were verified before staging.

| Evidence index | Path | Type | Present | Initial Git state | SHA-256 |
|---:|---|---|---|---|---|
| 4 | `.agents/evidence/logs/M5-focused-suite-final-20261028-command.log` | verified command/test log | yes | ignored, untracked | `fdbee71364c1eea58a599d1b9600303d0886d490faf3d64d7005028cc93ed01d` |
| 5 | `.agents/evidence/logs/M5-full-suite-final-20261028.log` | verified command/test log | yes | ignored, untracked | `378eb2d19514887d7369af9c17828571e6fd9ab571efe12157807e9681dd6be5` |
| 6 | `.agents/evidence/logs/M5-real-replay-profile-attempt-0005.log` | verified command/test log | yes | ignored, untracked | `c7fed31748ffaab466a51313d33f037c68375c33aeb510063b27634b4e6c21b8` |
| 7 | `.agents/evidence/logs/M5-focused-suite-final-20261028-r2-command.log` | verified command/test log | yes | ignored, untracked | `3f3c1d71ba91a4e739410c2a607cada1e953b52c1ce781c73029d238e420ac6f` |
| 8 | `.agents/evidence/logs/M5-full-suite-final-20261028-r2.log` | verified command/test log | yes | ignored, untracked | `9e82650b1178abb5e4b9600e2d5fe4e7354d2d7ae37b8b28a24d23557dccfa33` |
| 9 | `.agents/evidence/logs/M5-full-suite-final-20261028-r3.log` | verified command/test log | yes | ignored, untracked | `828a3def4d95fe62729af8ed66823d04bf7cec1fa9fbd47847b26dbed19a5f70` |
| 10 | `.agents/evidence/logs/M5-full-suite-final-20261028-r4.log` | verified command/test log | yes | ignored, untracked | `118c2472a97e274fbf7aa95a942282dc5b551df4162680e81458cb443ddadafb` |
| 12 | `.agents/evidence/logs/M5-train-initial-attempt-failure-20261028.log` | verified command/test log | yes | ignored, untracked | `328d03fbb062c57fc0f656ef9092ce3869d89576c2c99b07fee7eb8f22fe6135` |
| 13 | `.agents/evidence/logs/M5-focused-suite-after-recovery-fix-20261028-command.log` | verified command/test log | yes | ignored, untracked | `235dfa44faddb18f4581457282379e987cf78e67684f9c765cfd207dc830686e` |
| 14 | `.agents/evidence/logs/M5-checkpoint-restore-validation-20261028.log` | verified command/test log | yes | ignored, untracked | `4c264ca3c59ec81a84d2b77cd48771ccb728536e3a9489fe91addee80438fb9c` |
| 15 | `.agents/evidence/logs/M5-full-suite-after-recovery-fix-20261028.log` | verified command/test log | yes | ignored, untracked | `90a1208252c22b2cd896272e6b76d33f2ea96a37c970ff20b9858140ebb8a82c` |
| 16 | `.agents/evidence/logs/M5-train-attempt1-snapshot-metadata-failure-20261028.log` | verified command/test log | yes | ignored, untracked | `397622ce79e72b6d38bbb12edc9d239f266064b1b0aaedb70e83c8f7525ea4e1` |
| 17 | `.agents/evidence/logs/M5-focused-suite-snapshot-compat-20261028-command.log` | verified command/test log | yes | ignored, untracked | `9c3ac4b2f80f78f0bd4596f629063f8cc70392ec37c42adee638f59a9a0faf5f` |
| 18 | `.agents/evidence/logs/M5-initialization-snapshot-compat-validation-20261028.log` | verified command/test log | yes | ignored, untracked | `edc36781ae49bd81d415534414bc1af7be2a5d96d79caadc4e1cce993af177cc` |
| 19 | `.agents/evidence/logs/M5-full-suite-snapshot-compat-20261028.log` | verified command/test log | yes | ignored, untracked | `e70852899f1fe6280493875609f9a678066bb1ad595b5ca486a0b154e3c46813` |
| 24 | `.agents/evidence/logs/M5-checkpoint-restore-verification-20261106-command.log` | verified command/test log | yes | ignored, untracked | `5e3e540878bea4feb403eed39a5b636cdf5ea17ada8316fd461bb5661a2dfd95` |
| 25 | `.agents/evidence/logs/M5-focused-final-discovery-20261029.command.log` | verified command/test log | yes | ignored, untracked | `8663798649515e35f1c3826085f72a6418019e83cf6377989f4427a6c0455267` |
| 26 | `.agents/evidence/logs/M5-full-suite-final-20261029.command.log` | verified command/test log | yes | ignored, untracked | `89c305a3f2c5d8b23e9cdfe8c37762a4c98a8fbb6641e043bf93e3f46e9d4ab7` |
| 27 | `.agents/evidence/logs/M5-full-suite-environment-failure-20261029.command.log` | verified command/test log | yes | ignored, untracked | `479a2b5e183ce94dfd02c69496fe716c596b8757580b55c68b4dba14e9b00cd5` |
| 28 | `.agents/evidence/logs/M5-focused-direct-module-path-failure-20261029.command.log` | verified command/test log | yes | ignored, untracked | `ab5ed637cc89582ea644b7352e0e26a1378d032cce21e5fb880acd144de954f5` |
| 29 | `.agents/evidence/logs/M5-full-suite-final-evaluation-journal-20261029.command.log` | verified command/test log | yes | ignored, untracked | `b3c1093993f5f848f140f8cf2626fe5d2cfe9c3ebec8e0fcdca1093e70787ae9` |
| 30 | `.agents/evidence/logs/M5-focused-post-identity-check-20261029.command.log` | verified command/test log | yes | ignored, untracked | `fa825558a09628cd7c4f1868719c617f0425a275b1d9047efd3b5fdffd37891d` |
| 33 | `.agents/evidence/logs/M5-evaluation-official-20261029.command.log` | verified command/test log | yes | ignored, untracked | `09df63d5fb9fe1b287008de9a0c92ef2e7f0253e6c5fd85ed59e300d4f8af3c9` |
| 34 | `.agents/evidence/logs/M5-evaluation-capped-sensitivity-import-failure-20261029.command.log` | verified command/test log | yes | ignored, untracked | `f87dd9c4e1e0b0b4b500c70233345b25cced3318c685ca7774486a90e324c997` |
| 35 | `.agents/evidence/logs/M5-evaluation-capped-sensitivity-20261029.command.log` | verified command/test log | yes | ignored, untracked | `90a1f89e2af3e70c518495353859812be3681f2ccb1bd1787e0a0df55424ccac` |
| 36 | `.agents/evidence/logs/M5-final-report-hash-20261029.log` | verified command/test log | yes | ignored, untracked | `8ca488dc06e2224541c3b0ed1b533e7e1d55ecc30e09a4df49a7c9e5ac526754` |
| 37 | `.agents/evidence/logs/M5-full-suite-final-closeout-r2.log` | verified command/test log | yes | ignored, untracked | `7c452634e0241695bc7a9570fa72ecbafd317086bc06d14ae52d48557289bd7e` |
| 38 | `.agents/evidence/logs/M5-PR-11-verification-20261029.log` | verified command/test log | yes | ignored, untracked | `a87152496dd14bcde49af6fb52e46337994dd104cb889f32eeb975e48a38c993` |

## Source-identity reconciliation

### Frozen evaluation source

`M5-evaluation-source-identity-20261029.json` lists 42 Python file hashes and aggregate `ccb7d76be64c55ae4c4519da3a5647a5a2da86924a00d9490a7e807cc7497848`. At the PR source snapshot, 39 files match directly. The remaining three reconstruct byte-for-byte:

| File | Recorded evaluation identity | Later PR source | Exact delta |
|---|---|---|---|
| `videochess_rl/rl/evaluate.py` | `694415d51bdc316648c30124d3d4df36b970484c2ce3bb04cdc0ae7a615652c8`, 14,853 bytes | `00eaa86c9da75606bab3f108ec00906f86db89b7407224e859913c7467f4e4d9`, 17,009 bytes | The post-evaluation supplementary helper begins at byte 14,854; the first 14,853 bytes match the recorded hash. |
| `videochess_rl/rl/training.py` | `eca25d8b692ce77e07a3be4736eabbb71ed629d69717259de258905fa72fe90a`, 12,356 bytes | `053e95db5357a8b68215e9ff00feda53000783ca327efe7596f694cb0a010af6`, 12,355 bytes | Only a terminal LF was later removed; appending that LF reproduces the recorded hash. |
| `videochess_rl/rl/transition.py` | `df60fee8bf908e8d96901937dfc120d7e5a8f8e06a0119040e61356014aa645d`, 13,950 bytes | `c10821bc0b74d30acf66d582e9e9ed7148149469bb56213b25373c730ab3e09d`, 13,949 bytes | Only a terminal LF was later removed; appending that LF reproduces the recorded hash. |

`scripts/verify_m5_source_identity.py` rebuilds the evaluation aggregate exactly as `ccb7d76…`. The evaluation identity corresponds to the official evaluation code, not the current post-review source.

### Training source groups

The campaign verification and each run manifest agree on source group: four runs at `093992…`, two at `cdcc1f…`. The two seed-20261106 arms are mutually matched, but the source version changes at the same point as the third training-seed cluster. Workspace checkpoint-history indicates these path hashes changed between the last pre-resumption and pre-seed-20261106 checkpoints:

| File | Earlier SHA-256 | Later SHA-256 | Later Git blob |
|---|---|---|---|
| `videochess_rl/rl/checkpoint.py` | `19ab713b5a1450c2e4506d9d761768317e0b48fb96a3cb0083965d6a037bc410` (not found) | `924a95e6accb04c727e2858dbcd6cbda84b970750decc27fd09621bdc61821aa` | `bc1494666d3234c82ff82f2fb8ee851d9558c24b` |
| `videochess_rl/rl/cli.py` | `795ca9865da80bf982480b25d97367c846255e167d9c64320a73030106c2efe3` (not found) | `3f966fffa3a31ed9330004448ca84bc86a4fd6446764d3184e248cff978b60b7` (not found) | unavailable |
| `videochess_rl/rl/replay.py` | `5ae4d3d928c524539bcf6b29f4102f09b246d5703b66539f2fad4aa7e2aaa278` (not found) | `21845b0755809d07d480da821c2e809540a0ca4b8e1eddc5785ebdec5cf59b7f` | `355f8f0868152815debce129cc327d8bcecef970` |

The resumption record describes a checkpoint/replay recovery optimization. A full Git-blob scan found the later checkpoint/replay blobs shown above, but not their earlier hashes or either CLI snapshot used in the training source groups. Local source-worktree/backup searches found no extra copies. The named operational intent is corroborated, but no exact patch or line-by-line semantic comparison exists. `replay.py` is on the sampling path; without its old contents we cannot rule out a learning-distribution change. The paired seed-20261106 comparison is matched internally, while pooled cross-seed inference is confounded with this implementation-version change. No campaign rerun has been started.

## Remediations applied

| Finding | Root cause / impact | Change | Verification/status |
|---|---|---|---|
| CI provenance failures (P0) | `*.log` ignored the 28 referenced logs, so clean clones lacked required evidence | Force-add exactly the 28 referenced logs; add `TASK_EVIDENCE_LOG_UNTRACKED` for verified M5 log references and regression coverage | Clean clone at failing head reproduced 28 errors. Local preflight, clean-clone preflight, and GitHub CI passed at candidate `063c24c`; a docs/governance follow-up commit requires exact-head verification again. |
| Aggregate campaign stop guard | Stop guard added whole-invocation elapsed time to a committed ledger already updated between runs; could conservatively double-count prior runs | Count committed seconds plus only active-run elapsed seconds | Added `_campaign_usage_with_active_run` and a regression test. Historical ledger itself used committed run deltas and remains unchanged; all runs completed well below caps. |
| Unreachable transition check | Dead validation statement appeared after `return` in `_identity_document`; actual schedule equality validation was before this call | Removed unreachable statement; retained/reinforced invalid schedule validation test | M5 focused tests pass. No transition semantics changed. |
| Private input portability | M3/M4 directories were hard-coded to one workstation | Added `VIDEOCHESS_M5_M3_RELEASE_DIR` and `VIDEOCHESS_M5_M4_DIR` overrides; pinned hashes still required | Added override test; defaults still resolve to the authorized local artifacts. |
| README maturity | README described pre-M5 implementation | Updated to describe PR #11 implementation, actual simulator results, pending review, and M2/ALE boundary | README diff reviewed; exact candidate tests passed; final follow-up head still requires recheck. |

## Verification and remaining disposition

The M5 focused suite passed 48 tests. The complete local suite passed 368 tests in 138.487 seconds at `063c24cc9ab221e264bf06aadc6f57f7b45c7017`, with the authorized local M4 artifact available. A clean clone at that SHA passed canonical preflight and ran 368 tests in 136.734 seconds with one documented skip: the accepted M4 transfer test requires the private checkpoint absent from the clone. The same test ran in the local suite. GitHub run `41006247210` passed at that exact SHA; it ran canonical preflight plus the standard-library context/bundle/M5 oracle tests, not the full PyTorch suite.

The follow-up audit/state/evidence commit `026d41b7cb275affef5cffc27747449da7e045a3` was independently verified: local full suite **368 PASS** in 142.808 seconds; clean-clone canonical preflight **PASS** with only the expected private-artifact warning; clean-clone suite **368 tests with one private M4 transfer test skipped** because the checkpoint is not in Git; and GitHub workflow run `41006965692` **PASS** on that exact head. The local M4 transfer test passed in the local suite. The read-only campaign verifier and artifact inventory also pass. This follow-up report/state update is documentation/evidence-only; its final closure commit must receive a fresh exact-head clone/preflight and CI check.

The only known acceptance blocker is the irrecoverable line-level source provenance for the `093992…` versus `cdcc1f…` training code groups. PM disposition is required before M5-03/M5-04 can be marked complete. No training/evaluation process is active, no artifact was changed, G3 remains unapproved, and M6 has not started.
