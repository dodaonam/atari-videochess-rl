# PRE-M6 Engineering Readiness Report

**Mission:** Pre-M6 Atari Integration Readiness, Remediation, and Handover. **Role:** engineering executor; independent PM decision remains pending. **Report date:** 2026-10-30. **Conclusion:** readiness work is prepared for independent PM review with explicitly documented limitations; this is not PM acceptance or authorization to start M6.

## Baseline and governance

- Repository: `dodaonam/atari-videochess-rl`; remote `origin` resolves to the authorized GitHub repository.
- Integration branch: `initial-idea`; fetched baseline HEAD `07d476989f9300ff7639c2bf3476959298947553`; tree `4bc476ad011e388a40a16ed099dd2118275d9115`.
- PR #11 merged at `e0b434530df51b08595e3896c175f81b4a8f8c64`; PR #12 merged at the baseline. GitHub reports both PRs targeting `initial-idea` and merged. G3 evidence records PM approval; M2–M5 are complete/accepted as stated in canonical state and acceptance records.
- M6 is next, `pending_user_approval`, `start_authorized=false`, with no active milestone/task and no M6 task in backlog. G4 is not approved. This branch does not alter these fields or any M5 scientific outcome.
- The original checkout contained user-owned changes (`D atari-videochess-rl-roadmap.html`, `?? main.py`, `?? .agents/evidence/M1-04-terminal-success-20261016.zip`). They were left untouched; all mission edits are isolated in the feature worktree.

## Recovery and prior-closeout findings

The clean integration worktree preflight passed on baseline, reporting only the expected `ARTIFACT_MANIFEST_REQUIRED` warning because private artifacts are external to Git. The older original user worktree's preflight is not a valid baseline check: it is on `feature/pre-m4-readiness`, has different historical canonical state, and reports the owner's existing roadmap deletion as drift. It was not modified by mission work.

`BLOCKERS.md` had stale current-status text that simultaneously said G3 was approved and unapproved, and still summarized only G0–G2. Its current-status paragraph now states G0–G3 approved, M0–M5 complete, M6 unauthorized/not started, and no active blocker. Historical approval narratives elsewhere remain unchanged. BLK-003/RSK-014 remain resolved/accepted as previously decided; the report retains the limitation that complete historical M5 `cli.py` bytes are unavailable and no retraining is warranted.

PR #12's description states that final feature HEAD `0f5ecaa8e52e37c4f81eccd8d090eda633f0d77a` ran 384 tests with one expected private-M4 skip and cites log SHA-256 `be29f51b...e828c`, but the named log was in a temporary `/tmp` path and is not version-controlled at the merged baseline. The tracked `.agents/evidence/logs/G3-postmerge-suite-e0b.log` is for the PR #11 integration commit and 383 tests, not that later PR #12 run. The PR #12 statement is therefore preserved as a historical claim with cited hash, not represented as a retained log. New verification below is a fresh Pre-M6 result at the final feature HEAD.

## M1/M5 inventory and compatibility boundary

- M1 is RGB-driven. `ShadowBoard` advances only when evidence matches; unique RGB Atari replies are inferred and ambiguity/desynchronization fails closed. `run_episode` has typed stop categories, bounded frame/time/action limits, captures controller phases and preserves last verified state. It explicitly requires the shadow turn to be White and traces `player_color: white`. Atari Black-side play is unsupported. M1's terminal screen may not show a parseable board; retain last RGB-verified FEN and use ALE flags/reward, never fabricate a final state.
- Existing calibrated settings: direction hold 33 frames, source FIRE 1 frame, target FIRE 16 frames, release 1 frame. Direction holds quantize under frameskip 4. Existing default-profile evidence is a small number of cycles, not a reliability estimate. Uncertain FIRE is not retried. Mode 4, difficulty 0 has repeated terminal traces under deterministic settings; no human-readable mode label is asserted.
- M5 `QPolicy` is action-conditioned scalar Q inference reusing the accepted M4 representation, not M4 behavior logits. It requires complete ordered UCI history, verifies reconstructed FEN/turn/legal candidates, loads a `videochess-ddqn-evaluation-snapshot/2.0`, runs CPU eval/inference mode and selects a legal semantic move. It does not need an optimizer/replay/Stockfish path. `run_episode` currently passes only a board to its selector, so an explicit verified-history adapter is missing and is deferred to M6. The full contract is [M5_ALE_INTEGRATION_CONTRACT.md](../../docs/03-technical/M5_ALE_INTEGRATION_CONTRACT.md).
- Python 3.12.3, Gymnasium 1.4.0, ALE-Py 0.11.2, PyTorch 2.14.1+cpu, python-chess 1.11.2 were available through the existing local environment. No dependency or lockfile changed. M1 evidence records VideoChess ROM SHA-256 `d44f2a115393b0a6cbcd5398d62369e652f3670a9ee585883d183e740edad0f7`, registered RGB, action space 10, modes 0–4 and difficulty 0. The v5 profile reports frameskip 4 and repeat probability 0.25; debug is 1/0. The values are pinned project evidence and must be reasserted by M6 runtime capture.

## Open confirmation audit for M6 relevance

- O-02 (full-game ALE requirement versus fallback) remains open; this proposal keeps real-ALE full games as the target and claims no fallback waiver.
- O-03 presentation date remains owner-confirmed as Tuesday 2026-11-03; this mission does not change schedule or milestones.
- O-04 Colab quota/GPU/cloud storage/payment status remains unverified. No external compute or storage is needed for readiness; M6 starts with measured local CPU unless separately authorized otherwise.
- O-05 installed ALE/ROM facts and existing modes/profile values are evidenced by M1. Formal assignment-level official settings and human-readable difficulty semantics remain open. The protocol uses numeric mode 4/difficulty 0 and asserts actual runtime values during M6.
- O-06 source redistribution uncertainty concerns the M3 third-party dataset; M6 consumes only private model weights locally. No data/checkpoint upload or redistribution is proposed.
- O-07 Stockfish opponent/benchmark/other evaluation roles remain unauthorized; it is excluded from M6 inference and policy comparison.
- O-08 opponent pool and rating method remain open; no Elo claim is proposed.

## Private artifacts and frozen roster

Private artifacts were present in their documented local sibling workspaces and were read-only verified; they are not added to Git. M4 root inventory SHA-256 is `f00fde1c59325105e0ffd45bb45eb269dfa303416010c9a0b6c6be47bd9a9921` (19 entries). The selected M4 checkpoint loads on CPU with schema `videochess-m4-checkpoint/1.0`, input `videochess-model-input/1.0`, model `videochess-behavior-scorer/1.0`, 121,897 parameters, checkpoint SHA-256 `724ac730f3c5f2d01b48b26eb7670a3c764978a3dd4d6702b3057a99ab1a90a4`.

The M5 root artifact-manifest SHA-256 is `a201a254671ad59ae1fecb402abf994d5bf523097f1c3010b5c7fa237ae6dd4c`; its seven run manifests and root inventory cover 6,544,747,450 bytes. All six accepted post-RL Warm/Scratch snapshots (three paired seeds, with Warm 20261104 attempt 1) are present in the root inventory and each passed CPU load/inference smoke with deterministic output and unchanged weights. Selected fixed roster:

| Policy ID | Arm / seed / stage / attempt | Checkpoint SHA-256 | Sidecar SHA-256 | Manifest identity / schema | Availability and inference |
|---|---|---|---|---|---|
| `m5-warm-seed-20261104-post-rl` | Warm / 20261104 / post_rl / 1 | `0b2405017a8e1d539851f0cd278883d3fd23936fb5c2f7962c813590a6fd1767` | `80d8689e4b349576c5708bb4dce3451e5a8c64d81470cd6f4273a4746844b682` | Root manifest `a201a254…dd4c`; evaluation snapshot 2.0 | Present; manifest and checkpoint verified; frozen inference smoke passed. |
| `m5-scratch-seed-20261104-post-rl` | Scratch / 20261104 / post_rl / 0 | `3749b0c0b6ae44d3ad5d6bf0863b60937a59fbe881e0bdf4932bdce6033ca400` | `1c15e5bc4ba2437df113671dc316accbdfe6d8b59069ed29ed187daebf4fff1e` | Same root manifest; evaluation snapshot 2.0 | Present; manifest/checkpoint verified; offline inference smoke passed. |
| `m5-warm-seed-20261105-post-rl` | Warm / 20261105 / post_rl / 0 | `e864d8351cb03b7e671e7a061226711b2d33b23bbaca97e899c09f1d2eb59670` | `dceb8c11c3ebd239048ba6e51bb8fd1ea26d72f9129ec6e4ed3bc4847cffabf0` | Same root manifest; evaluation snapshot 2.0 | Present; manifest/checkpoint verified; offline inference smoke passed. |
| `m5-scratch-seed-20261105-post-rl` | Scratch / 20261105 / post_rl / 0 | `e63ab18289135e411fb4c00a025d2985446475e5b70881ca7e9190559c20b3f8` | `d0bc5b1e08ede42282a9c921b4da6181341f9c7c4d633454642e7fe9312cc2e6` | Same root manifest; evaluation snapshot 2.0 | Present; manifest/checkpoint verified; offline inference smoke passed. |
| `m5-warm-seed-20261106-post-rl` | Warm / 20261106 / post_rl / 0 | `c037adc652a00ea131366c5f15ac78811a223459312f9bac5f676f267cf36bcd` | `cf52cc191543ddcdfa460b1a1a07c6e9d941d09eee69fb673b09c18f97037b8d` | Same root manifest; evaluation snapshot 2.0 | Present; manifest/checkpoint verified; offline inference smoke passed. |
| `m5-scratch-seed-20261106-post-rl` | Scratch / 20261106 / post_rl / 0 | `94838bc8c3547a5b8ce9e1d8c1dde66b86163defb868b18be6185895acf9663c` | `7335dce64b7d070271ed490828022851f42232c1aacc7eed9014e360cd7e6779` | Same root manifest; evaluation snapshot 2.0 | Present; manifest/checkpoint verified; offline inference smoke passed. |
| `m4-behavior-only-seed-20261024` | M4 supervised / seed 20261024 / selected validation-best | `724ac730f3c5f2d01b48b26eb7670a3c764978a3dd4d6702b3057a99ab1a90a4` | `cc0af4694e45fc23acb740c652dd9a62e1bcaf7851815d179693d09539f0f606` | M4 artifact manifest `f00fde1c…9921`; M4 checkpoint 1.0 | Present; root inventory and CPU checkpoint loader/schema passed. Not an RL policy. |

M5 root manifest is the immutable manifest identity for the six candidate snapshots; selection uses the lowest training seed, not M5 evaluation rank. Warm-start superiority over Scratch was not established in M5. Exact paths and predeclared policy rationale are in [M6_ALE_EXPERIMENT_PROTOCOL.md](../../docs/04-research/M6_ALE_EXPERIMENT_PROTOCOL.md). M3 dataset bytes are not an M6 inference dependency and were not opened or copied.

## Changes and verification

Changes are limited to: current-status correction in `BLOCKERS.md`; portable reporting of external roots in `scripts/m5_artifact_manifests.py` plus regression tests; a private-snapshot offline policy compatibility test; and this report plus the linked M6 technical contract, experiment protocol, and execution plan. No accepted M4/M5 checkpoint, M5 manifest, metric, evaluation record, source snapshot, or campaign artifact was modified. No training, new Atari evaluation campaign, Colab allocation, Stockfish search/evaluation, upload, or release occurred. The required full regression suite exercises the repository’s already-authorized bounded M1 ALE integration tests; those regression cases are not presented as new M6 gameplay results.

Execution evidence below is retained as sanitized logs with metadata after final verification. Every final command records the tested feature HEAD, UTC timestamp, command, environment, exit code, count, and log hash. The exact tested feature HEAD is the final commit shown in the accompanying handover/PR; values are filled after commit and clean-checkout verification.

## PM6-R readiness dispositions

| Criterion | Disposition | Evidence / limitation |
|---|---|---|
| PM6-R01 Governance correctness | PASS | G3 approved, M6 unauthorized/not started, no M6 task, no M5 result edits; preflight and final state check. |
| PM6-R02 Prior closeout consistency | PASS WITH DOCUMENTED LIMITATION | `BLOCKERS.md` fixed. PR #12 historical 384-test claim/hash is distinguishable from tracked PR #11 383-test log; the PR #12 temporary log itself is unavailable and is not reconstructed. |
| PM6-R03 Artifact readiness | PASS | M4 19-entry and M5 7-run artifact manifests, selected checkpoints/schema/hash/load/inference verified. All six candidates available; private files remain outside Git. |
| PM6-R04 Policy/ALE technical contract | PASS WITH DOCUMENTED LIMITATION | Existing M5 policy contract passed offline selected-snapshot inference and new guard tests. Atari adapter is specified but not integrated or real-ALE verified; that is M6 work. |
| PM6-R05 Atari execution readiness | PASS WITH DOCUMENTED LIMITATION | Profiles, White-only support, calibration, timeouts, terminal limitations and genuine M6 evidence are explicit. No new ALE gameplay evidence was produced in Pre-M6. |
| PM6-R06 Scientific protocol readiness | PASS | Frozen seed-based roster, exploratory comparison, explicit denominators, incomplete accounting and separation of M2/M4/M6 evidence are documented. |
| PM6-R07 Reproducibility | PASS | Per-game source/lock/ROM/checkpoint/config/trace identities and replay limits are predeclared. |
| PM6-R08 Regression safety | **PENDING FINAL VERIFICATION** | Targeted policy/path tests and precommit preflight passed; full suite is being rerun after correcting worktree checkpoint and PATH setup. Final M1/M4/M5, preflight, hash and clean-checkout evidence must be added after execution. |
| PM6-R09 M6 implementation handover | PASS | Bounded sequence, criterion mapping, hard entry conditions, resources, stops and M7-only questions are in the plan/protocol. |
| PM6-R10 Final delivery quality | **PENDING PR** | Requires final feature commit, clean feature worktree, pushed branch and one open non-draft PR targeting `initial-idea`; no merge/self-approval. |

## Independent PM checklist

1. Confirm G3 and PR #11/#12 merge identities against GitHub and canonical state; confirm M6 remains unauthorized and G4 not approved.
2. Inspect current-status correction and confirm historical G3/M5 closeout narratives were not rewritten.
3. Verify M4/M5 manifest and snapshot hashes in the private stores if independent artifact access is available; do not interpret absence in a clean clone as corruption.
4. Review seed-20261104 selection rule and confirm M5's inconclusive Warm/Scratch comparison is not presented as superiority.
5. Review that the M6 adapter is specified but not implemented/run, Atari White-only limitation is explicit, and no debug profile is reported as evaluation.
6. Review final verification log metadata, CI, branch target and exact PR head; make the PM's own acceptance/merge decision separately. Any M6 start authorization remains a distinct direct decision.
