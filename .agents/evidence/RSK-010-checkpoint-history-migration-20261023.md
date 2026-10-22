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

Detailed exact-revision commands, test totals, final state/archive hashes, preflight result, clean-clone output, and CI status are appended after the implementation commit and final review. Earlier migration/test iterations are not substituted for those final results. The accepted M3 evidence and its historical test totals remain unchanged.
