# RSK-010 Lossless Checkpoint-History Migration — 2026-10-23

**Status:** Migration applied and independently reconstructed on `feature/rsk010-lossless-checkpoint-history`. The branch is not merged into `initial-idea`; RSK-010 remains open for integration until owner review, merge, and post-merge clean-clone verification.

## Baseline and scope

- PR #4 is merged into `initial-idea` at `16fc01a3fe731c0a0be127026cc64d049c0cf550`; the feature branch starts at that exact commit.
- The source state was 3,919,833 bytes, with 139 inline records and current checkpoint `cp-181d6b2e-20261022T162716612501Z` not present in that inline list.
- The original state SHA-256 was `33d995ee1f1e86a9f07da5ec339e3c55b062ede8491a2ad70eeafa12b9dd0ef1`.
- The original worktree's pre-existing deletion and untracked user files were not modified; migration was performed in the separate clean worktree `/tmp/atari-rsk010-20261023`.
- The migration did not touch M3 release evidence, dataset manifests, ADR-0001/0002, the roadmap, acceptance criteria, or M4 authorization fields.

## Versioned storage result

`PROJECT_STATE.yaml` now stores an empty inline history plus a version 1 archive pointer. The archive is `.agents/state/checkpoint-history/` and must be committed with the pointer. The manifest verifies the backup, each compressed segment, each segment's uncompressed bytes, record boundaries, and the ordered logical history. Initial segments contain at most 16 records; future appends add one immutable record segment and replace the manifest. Archive files are excluded from per-checkpoint workspace hashing and portable manifests, then independently verified through the pointer/manifest hashes and clean-clone preflight.

| Measure | Before | After initial migration |
|---|---:|---:|
| Canonical state bytes | 3,919,833 | 65,811 |
| Inline history rows | 139 | 0 |
| Reconstructed logical records | 139 inline + current checkpoint | 140 |
| Archive file count | 0 | 11 |
| Archive total bytes | 0 | 1,741,856 |

The 140 IDs are unique and ordered. An independent verification loaded the byte-exact source-state backup, reconstructed the expected ordered history from its 139 records plus the historical current checkpoint, and compared every logical record to the archive: exact match. Ordered-ID digest: `f57cd6ad8d3876bd3d537ef6def4ed20139b96aa2e90e52c1be575bedb56f786`. Aggregate logical-history SHA-256: `c4461ec1c59a6748fd113e581c8f4eb38234d7245d917078ae019ae6f43717b4`. Manifest SHA-256: `bc7c9527dbc964300a3247530b69f572e438a86166eb561f389148cb5675ddf4`. The original source state was restored byte-for-byte from the gzip backup and its SHA rechecked.

The first migration checkpoint is `cp-16fc01a3-20261022T173302624409Z`. That new checkpoint is not yet in the 140-row archive; the next changed checkpoint will append it once. This is the normal append contract, not missing source history.

## Failure and recovery boundary

The code and synthetic fixtures cover deterministic migration, exact preservation, source backup, segmentation boundaries, repeat invocation, archive append/no-op, duplicate prevention, missing/corrupt/unreferenced archive files, malformed legacy records, partial migration resume, a failure after an archive file's atomic replacement, canonical-state write failure, caught append rollback, both pending-append forms, stale-handoff repair, migration-finalization retry, and clean-clone recovery. Caught checkpoint failures roll back state, handoff and new append files. A power loss across multiple replacements is not transactional; preflight detects the resulting recoverable pending append or invalid archive. Operators must follow [`CHECKPOINT_HISTORY.md`](../../docs/05-operations/CHECKPOINT_HISTORY.md), not edit hashes or delete files.

The archive removes the single-file state growth limit but is intentionally lossless: total retained bytes and manifest entries continue to grow linearly. Review separately authorized persistent-storage options before 64 MiB; do not truncate records. Until this branch is merged, `initial-idea` remains on the legacy 4 MiB state guard.

## M4 entry audit

- M0–M3 accepted status and M3 release identity remain as recorded in the accepted closure evidence.
- Exact release files are absent from both documented `artifacts/m3/` locations in the original checkout and this worktree. The accepted release ID, manifest identity and split identity are known, but none of the nine release files could be rehashed here. No dataset was fetched or rebuilt.
- O-01 remains open in `REQUIREMENTS.md`; no assignment, syllabus, or instructor-policy evidence was found in the repository.
- ADR-0003 remains **Proposed**. Its recommendation is technically consistent with M2/M3 semantic UCI actions, full history, candidate masks, and a distinct M5 Q head; an owner decision is still required before it is treated as accepted.
- The owner issued direct conditional authorization for M4-001, recorded in `.agents/evidence/M4-001-authorization-conditional-20261023.md`; it is not operational until all entry conditions are verified and required owner decisions are recorded. `M4-001` remains pending, `engineering.active_milestone` and active task remain `null`, `start_authorized` remains `false`, and G3 remains unapproved. No model, data loader, training, or M4 acceptance result was created.

## Verification record

### Final implementation-code verification — revision `71c623cb31cee9b476d679a870aa5765d05e12ef`

This is the final tested code revision before the evidence/PR delivery-only updates. The branch was clean at the tested revision. Test output is retained in `logs/RSK010-final-*-71c623c.log`; paths are sanitized and no credentials or full environment dump are present.

| Check | Command | UTC | Result | Scope |
|---|---|---|---|---|
| Checkpoint/archive + governance/context regression | `<project-venv>/python -m unittest tests.test_checkpoint_history tests.test_agent_context -v` | 2026-10-22 18:04:14–18:04:49 | exit 0; 75/75 passed | Archive migration, corruption/failure recovery, no-op, clean clone, preflight/context and governance tests. |
| GitHub Actions Python-test-step equivalent | `<project-venv>/python -m unittest tests.test_agent_context tests.test_export_review_bundle -v` | 2026-10-22 18:08:24–18:08:54 | exit 0; 66/66 passed | Same two unittest modules as the repository workflow; this is a local run, not a GitHub Actions result. |
| Full repository suite | `<project-venv>/python -m unittest discover -s tests -v` | 2026-10-22 18:02:21–18:03:56 | exit 1; 268/269 passed | Sole failure: `test_stockfish_answers_uci_readiness_without_searching`; no Stockfish executable exists in this environment's PATH. The test's original semantics were preserved; no engine was installed. |
| Local canonical preflight | `python3 scripts/agent_preflight.py --json` | 2026-10-22 18:05:06–18:05:07 | exit 0; no errors; `ARTIFACT_MANIFEST_REQUIRED` warning only | Portable/index/workspace snapshot matched; M4 pending and unauthorized. |
| Archive integrity | `python3 scripts/migrate_checkpoint_history.py verify` | 2026-10-22 18:05:07 | exit 0; 143 archive records verified | Archive-only count; the live `last_checkpoint` is a separate, unique 144th checkpoint identity. Logical archive SHA-256: `5e322d43cc168bc1b15f0c16d1f39e61da458a876c84970441e9e80ae79f753d`. |
| Clean-clone recovery | `python3 scripts/migrate_checkpoint_history.py verify`; `python3 scripts/agent_preflight.py --json` | 2026-10-22 18:05:26–18:05:27 | both exit 0; no errors; artifact-manifest warning only | New local clone at the tested branch revision; archive count/hash match; Git snapshot and portable index match; M4 unauthorized. |
| Syntax and whitespace | `python3 -m py_compile scripts/agent_checkpoint.py scripts/agent_preflight.py scripts/checkpoint_history.py scripts/migrate_checkpoint_history.py tests/test_checkpoint_history.py`; `git diff --check` | 2026-10-22 18:05:07 | both exit 0 | Migration/checkpoint implementation and tests. |

The test runner used Python 3.12.3 and the repository's existing local `.venv`. GitHub Actions run [39828940452](https://github.com/dodaonam/atari-videochess-rl/actions/runs/39828940452) passed on code head `71c623cb31cee9b476d679a870aa5765d05e12ef`; its `context` workflow runs preflight plus `tests.test_agent_context` and `tests.test_export_review_bundle`, not the full repository suite. After the first evidence commit, run [39829310570](https://github.com/dodaonam/atari-videochess-rl/actions/runs/39829310570) also passed on `e8966cb9272261b5d9beac1518f0fe77c433045d`. A final evidence-only change will advance the PR again; verify the live final-head status before merge. The local workflow-equivalent test result is kept separate from GitHub's result. The full-suite result is **not** described as all passing.

### Final archive measurement at the tested code revision

- `PROJECT_STATE.yaml`: 67,156 bytes; SHA-256 `be1708759a8965f56447ab547c7a23a6c0969b59dac8461ccce388e75a9c8b23`.
- Archive: 14 files totaling 1,808,362 bytes; manifest SHA-256 `27981a5c441becafd6e3bc96ea58e5de1d1acd6414ffdb383f33cdf28f44ef79`.
- The archive contains 143 unique ordered records. Current `last_checkpoint.id` is `cp-0d6ce072-20261022T175917693718Z`, is not duplicated in the archive, and remains canonical in the state; archive plus current state therefore represents 144 distinct checkpoint identities.
- Relative to the 3,919,833-byte merged baseline, the current canonical state is 98.29% smaller. The archive remains lossless and grows with each retained checkpoint; 64 MiB is a review threshold, not a hard storage cap or a claim of indefinite capacity.
- The original 140-record baseline prefix is preserved; prior inline records and the source current checkpoint remain in order. The added branch checkpoints are appended as immutable segments. No historical record was deleted.

### Committed delivery-state verification — `e8966cb9272261b5d9beac1518f0fe77c433045d`

The evidence/checkpoint commit following the tested implementation code passed a clean-clone check: archive verification returned 145 ordered records with logical SHA-256 `5c8f80bf604df89a40694e330d5bcf7745b2bf6b3ae56e4ec4282068008ac4d7`; preflight returned exit 0 with no errors, `ARTIFACT_MANIFEST_REQUIRED` as its only warning, matching Git/portable snapshots, and `start_authorized=false`. At this commit, `PROJECT_STATE.yaml` was 69,139 bytes (SHA-256 `49729111e9facb93702132ffe39a8ef94edc90684643d971c8e0cf1338499e28`); 16 archive files totaled 1,853,658 bytes; manifest SHA-256 was `804c30f495ea70dd29f72c94a2f35043b12abecad202c73e65770a6e8ac2dc1b`. The separate live checkpoint was `cp-71c623cb-20261022T181105110634Z`, not duplicated in the archive, so 146 checkpoint identities were represented. Clean-clone output is retained in [`RSK010-clean-clone-e8966cb.log`](logs/RSK010-clean-clone-e8966cb.log). GitHub Actions run 39829310570 passed on this exact SHA; its workflow scope and result are retained in [`RSK010-github-check-e8966cb.log`](logs/RSK010-github-check-e8966cb.log). The final evidence-only PR commit must still be checked at its own head.

### Entry conditions and delivery boundary

- Accepted M3 release identity and historical closure evidence are present, but all nine raw release files are absent from the documented `artifacts/m3/` paths and current worktrees; their file hashes and split separation could not be rechecked here. No download, rebuild, or substitute release was made.
- O-01 remains unresolved because no authoritative course/instructor policy is present in the repository. ADR-0003 remains Proposed pending owner decision. The owner’s direct M4-001 authorization remains conditional and non-operational.
- G3 remains unapproved. `M4-001` remains pending; `engineering.active_milestone=null`, active task is `null`, and `start_authorized=false`. No model, loader, training, Stockfish evaluation, M5/M6, ROM, Colab, or paid compute work was started.
- Migration PR [#5](https://github.com/dodaonam/atari-videochess-rl/pull/5) is open as a draft at this evidence revision; Actions passed at the exact `e8966cb` head. The final evidence-only PR head must still be checked. RSK-010 remains open in `initial-idea` until owner review/merge and post-merge clean-clone verification; on the feature branch the migration itself is verified.

### Pull request delivery

- Migration PR: [#5](https://github.com/dodaonam/atari-videochess-rl/pull/5), targeting `initial-idea`; it was opened as a draft from code revision `71c623cb31cee9b476d679a870aa5765d05e12ef` while the final evidence update was still local.
- At draft creation, GitHub's `context` workflow was pending at [run 39828940452](https://github.com/dodaonam/atari-videochess-rl/actions/runs/39828940452); it later passed on the initial draft head, not the later evidence-only final head. The PR body and owner handoff will carry final-head check status after the evidence commit is pushed.
- The PR is not merged and no auto-merge is enabled. RSK-010 stays open on `initial-idea` until owner merge decision and a clean clone of the resulting integration commit passes both archive verification and preflight.

Earlier migration/test iterations are historical evidence and are not substituted for the exact-revision results above. Accepted M3 evidence and its historical test totals remain unchanged.
