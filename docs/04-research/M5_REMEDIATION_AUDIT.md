# M5 Post-Review Remediation Audit

**Recorded:** 2026-10-30 UTC
**PR:** [#11](https://github.com/dodaonam/atari-videochess-rl/pull/11), base `initial-idea`
**Status:** forensic remediation complete and ready for independent PM review. Formal M5 acceptance, G3 approval, and merge remain pending and are not claimed here.

## Executive result

The reported 28 GitHub preflight failures were reproduced in a clean clone of PR head `575dce5978567417d2915d5dd36a47873293b607`. Each failure was a verified M5 command/test evidence entry whose referenced `.log` file was missing from that clone. All 28 source logs existed in the local project worktree, matched their recorded checksum when present, and contained the recorded command, result, and exit code. The root cause was `.gitignore` rule `*.log`; Git treated all 28 logs as ignored/untracked. They were force-added by exact evidence-reference list, totaling 778,449 bytes. A preflight regression check now rejects a locally present but untracked M5 evidence log. No log content was replaced or backdated.

The private artifact root manifest verifies 7 manifests and 6,544,747,450 bytes. A read-only cross-check verified six run summaries/attempts, all replay chain counts, 15 per-policy raw schedules, 3,385 event records, 1,500 unique scenarios, the exact 6 truncations, and the ledger arithmetic. See `.agents/evidence/M5-remediation-log-inventory-20261030.json` and the retained verifier logs.

The initial remediation finding was that a training-source difference could not be excluded: four runs record source SHA `093992c50e893a7fdd92f2f95faafe28d4f1e73c7351a4a8179a3056c4e63b00`, and two record `cdcc1fdc0ca0b324e49cfb8b0ff571496a554e9892dfb3620d6454a65ee16da0`. That was the evidence state before the owner supplied the complete continuation-session transcript. The transcript-based recovery and subsequent semantic assessment below supersede the initial interpretation while preserving it as the original audit finding.

## Initial-state inventory

| Evidence/resource | Path | Initial status at review | Verification |
|---|---|---|---|
| Canonical repository | `/home/dodaonam/Projects/atari-videochess-rl-m5` | Git worktree, feature branch | HEAD `575dce5`; PR #11 OPEN; no training/evaluation process running. |
| M5 implementation/config/docs/tests | tracked PR branch | Tracked in Git | Config SHA `84d305084397ad18397dfe395fab58de824fa056729675d0d1cd9ca8bdd06d8d`; changes are reviewed on this branch only. |
| 28 verified M5 command/test logs | `.agents/evidence/logs/M5-*.log` (see table below) | Present locally; ignored by `*.log`; absent from remote clean clone | Each path/hash/size/command-result-exit verified; secret-pattern scan reported no matches; exact files force-added. |
| M5 run/evaluation source manifests and campaign evidence | `.agents/evidence/M5-*-20261029.*` | Tracked evidence; large model/replay/game data not Git tracked | Report hashes and run/source identity groups reconciled with local artifacts. |
| M5 private artifacts | `artifacts/m5/` | Ignored/private local files | Root artifact manifest verified; 6.544 GB of 8 GiB. No artifact was edited. |
| Accepted M4/M3 inputs | `/home/dodaonam/Projects/atari-videochess-rl-m4/...` and `/home/dodaonam/Projects/atari-videochess-rl-m3/...` | Private paths outside Git | M5 accepted-input evidence pins M4 checkpoint SHA and M3 release manifest; this remediation did not transfer or publish their contents. |
| Historical training-source evidence | Recovered `checkpoint.py` and `replay.py`; CLI excerpts/patches; transcript outside Git | Checkpoint/replay source bytes are exact SHA-256 matches; full historical CLI files remain unavailable | See `.agents/evidence/M5-source-recovery-20261030.json` and `.agents/evidence/M5-source-semantics-20261030.json`; the raw transcript remains at the owner-supplied local path and is not committed. |

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

At the initial audit, the transcript and source bytes had not yet been supplied, so a line-level comparison could not be made. The original assessment and scanned Git-object findings remain in the preceding record and in `.agents/evidence/M5-source-reconciliation-20261030.json`; the forensic addendum below supersedes the then-current uncertainty about replay behavior. No campaign rerun has been started.

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

The follow-up audit/state/evidence commit `026d41b7cb275affef5cffc27747449da7e045a3` was independently verified: local full suite **368 PASS** in 142.808 seconds; clean-clone canonical preflight **PASS** with only the expected private-artifact warning; clean-clone suite **368 tests with one private M4 transfer test skipped** because the checkpoint is not in Git; and GitHub workflow run `41006965692` **PASS** on that exact head. The local M4 transfer test passed in the local suite. The read-only campaign verifier and artifact inventory also pass.

At exact candidate `57c8bce28b151b3f30b03b3b972561e142d18b16`, a fresh local run passed all 368 tests in 145.322 seconds (peak RSS 357,588 KiB). A remote clean clone at the same SHA passed canonical preflight and all 368 tests in 144.747 seconds, with one skip for the private M4 transfer test; the local run executed it. Local and clean-clone preflight had zero errors and only the expected independent artifact-manifest warning. GitHub run `41007586702` passed on that exact head; the workflow's scope was canonical preflight and standard-library context/bundle/M5 oracle tests, not full PyTorch regression. Artifact, campaign-chain, and source-identity checks also passed read-only. Full local and clone suite logs were retained at `/tmp/M5-final-suite-57c8bce.log` and `/tmp/M5-clean-suite-57c8bce.log` (SHA-256 `63175d718fdf936119a775519ef90951cd4c5f41cbefb569fb7f0580d85f3f99` and `598b20d4af96353d4f5d034291c156fb8e28db17aca9d988518b1b1480fb19a1` respectively).

The initial audit's missing-source finding is superseded by the forensic addendum below. Independent PM review remains required; this report does not grant M5 acceptance, approve G3, or authorize M6.

The post-recovery local full repository suite passed **383/383 tests** on the staged candidate diff `da696d5515f3dfe2ec53d8137914d444ffc4c73eb61a8679212b1d85455ec2ab`: unittest time 164.146 seconds, wall time 166.59 seconds, peak RSS 360,172 KiB. Its retained output is `.agents/evidence/logs/M5-full-suite-forensic-20261030.log`. Exact final-commit clean-clone and GitHub CI verification is still required before PR handoff.

## Forensic source recovery and semantic assessment — 2026-10-30

### Transcript provenance and recovered files

The owner supplied `/home/dodaonam/Downloads/Pasted text(20261030-060523).txt`, 3,655,066 bytes, SHA-256 `c5d8706cff0f7634620b835d1a8063ac43f8bd8eec277995ed09f3b00a693e8f`. The UTF-8 text has 22,750 logical lines (22,749 newline delimiters). The transcript itself remains outside Git; only the transcript identity and narrowly extracted source/diff evidence are committed. The sensitive-pattern scan found no credential values in the recovered source excerpts.

| File | Historical expected SHA-256 | Recovered SHA-256 | Result |
|---|---|---|---|
| `videochess_rl/rl/checkpoint.py` | `19ab713b5a1450c2e4506d9d761768317e0b48fb96a3cb0083965d6a037bc410` | Same | Exact UTF-8 byte-preserving transcript extraction, lines 1647–1873; 12,167 bytes. |
| `videochess_rl/rl/replay.py` | `5ae4d3d928c524539bcf6b29f4102f09b246d5703b66539f2fad4aa7e2aaa278` | Same | Exact UTF-8 byte-preserving transcript extraction, lines 1874–2017; 6,732 bytes. |
| `videochess_rl/rl/cli.py` | Earlier `795ca9865da80bf982480b25d97367c846255e167d9c64320a73030106c2efe3`; later `3f966fffa3a31ed9330004448ca84bc86a4fd6446764d3184e248cff978b60b7` | Not reconstructed | Whole-file hashes remain unavailable in Git objects. The old resume-selector excerpt and its recorded patch sequence were recovered and checked; no full-file byte-match claim is made. |

The extraction procedure, source bytes, retained diffs/fragments, checkpoint-history identities, and execution result are indexed by `.agents/evidence/M5-source-recovery-20261030.json` and `.agents/evidence/M5-source-recovery-verification-20261030.json`. The machine-readable function/change analysis is `.agents/evidence/M5-source-semantics-20261030.json`.

The original object-database availability table in `.agents/evidence/M5-source-reconciliation-20261030.json` records what was present before transcript recovery. The recovered `checkpoint.py` and `replay.py` evidence files now create matching Git blob objects when staged/committed; this new availability is not evidence that those source bytes were preserved in Git during the original training session. The full historical CLI hashes remain unmatched.

For future owner-authorized M5 runs, the CLI now captures a content-addressed ZIP containing runnable `videochess_rl` Python files, canonical M5 configuration, dependency/lock inputs, and the declared runtime provenance inputs before training. Attempt/run records and the artifact manifest reference the archive identity; verification checks each member hash, source/config hash, and private artifact-root boundary. The runner refuses to write into a finalized artifact root. This safeguard was unit-tested and was not invoked on the completed campaign, so it created no official source bundle and changed no training artifacts.

### Exact runtime differences

Checkpoint-history snapshots `cp-08f98f9d-20261029T043013180672Z` and `cp-08f98f9d-20261029T143803674896Z` differ in 15 paths. Exactly three are runtime Python files: `checkpoint.py`, `replay.py`, and `cli.py`. The other 12 are authorization/evidence, plans/state, the episode-checkpoint verifier, and tests. The configuration and training-critical `training.py`, `transition.py`, `network.py`, `targets.py`, and seed-derivation implementation did not change in that interval.

- **Replay:** `ReplayBuffer` construction, length, iteration order, insertion/eviction, sampling, state serialization, and restoration are AST-identical between authentic old source and later source. `ReplayJournal.append` is also identical. Only `ReplayJournal.__init__` and `verify` changed. The later verifier streams and hashes the full requested journal prefix while reconstructing only the bounded replay tail; it still validates retained transitions. It does not change journal rows or sampler RNG consumption.
- **Checkpoint:** Serialization/save functions are unchanged. Only `verify_training_checkpoint` and `restore_training_checkpoint` changed. The later path verifies the full journal chain once, reconstructs only the buffer-capacity suffix, checks counters/RNG and payload mappings before mutating the learner, then restores the same online/target/optimizer/replay/counters/RNG state.
- **CLI:** The full earlier/later file bytes are unavailable, but the complete transcript records four pre-final-run edits: adding `093992…` to the compatible initialization/recovery source-hash set; changing resume candidate verification to newest-first with fallback; ordering candidates using episode/decision counters in checkpoint filenames; and importing the verifier used by that path. The selector excerpt and reconstructed final function are retained with a fragment diff. These edits affect checkpoint compatibility/selection, not the policy/update algorithm.

The final seed-20261106 Warm-start and Scratch attempts are each `attempt-0000`, each has `resume_parent_checkpoint_sha256: null`, and each completed 50,000 decisions. Therefore neither run restored a prior checkpoint; the changed resume selector/restore path was not exercised by either final-seed training run. Within all seeds, Warm-start and Scratch run records remain source-matched. The aggregate source digest is still correlated with seed `20261106`, but no observed change to reward, transition, legal UCI, replay insertion/sampling, optimizer, target arithmetic, initialization weights, or episode semantics is associated with that digest change.

### Checkpoint restoration verification and cost

Previously retained, read-only restoration checks against authentic episode-boundary checkpoints passed:

| Seed / arm | Checkpoint decisions | Replay rows | Online / target / optimizer / counters / RNG | Time / peak RSS |
|---|---:|---:|---|---|
| 20261105 Scratch | 49,967 | 16,384 | Exact PASS; full prefix chain verified | 194.32 s / 766,320,640 bytes |
| 20261106 Scratch | 49,833 | 16,384 | Exact PASS; full prefix chain verified | 202.83 s / 779,337,728 bytes |

The independent source unit suite compares historical and later restore behavior on a deterministic checkpoint fixture, including optimizer, replay order/RNG, global RNG states, counters, and the next sampled minibatch. The initial 14 source-recovery/source-snapshot tests passed in 4.36 wall seconds; after adding a deterministic latest-well-formed-CLI-checkpoint selection test, the focused suite passed 15 tests in 3.48 wall seconds. The final focused log is `.agents/evidence/logs/M5-source-focused-tests-20261030-r2.log`.

An optional differential verifier attempted to restore two authentic checkpoints through both historical and later full-object implementations. The historical path repeatedly validates the journal and reconstructs complete history-bearing transitions; after 20:16.95 wall time and 1,804,152 KiB peak RSS, it remained CPU-bound before emitting a result and was stopped. Its log has exit code 143 and is explicitly **INCOMPLETE**, not PASS. This diagnostic did not mutate training artifacts. The successful later-path artifact restorations and deterministic historical/current fixture remain the positive recovery evidence; the expensive historical replay reconstruction is the measured reason not to use that optional procedure as a campaign verifier.

### Disposition and remaining limits

The original hypothesis that the replay sampler might have changed is not supported by recovered code: insertion, eviction, sampling, replay state methods, and journal append are identical; checkpoint changes are limited to verification/restoration; and the two final runs were fresh attempts. No evidence indicates a learning-distribution change. No training or evaluation was repeated, and no official artifact was changed.

The full historical CLI files remain unavailable, so source bytes are not wholly reconstructed and byte-identical execution is not claimed. This residual auditability limitation is disclosed for PM review. The campaign still has only three independent training-seed clusters, and every conclusion remains about the M2 chess simulator, not Atari ALE VideoChess. Additional training is not currently supported as technically necessary and has not been started; any supplemental experiment would require separate PM authorization.

Engineering evidence supports review of M5-03/M5-04 with the limitations above. Independent PM disposition/acceptance remains pending. G3 remains unapproved; M6 has not started; PR #11 remains open and unmerged.
