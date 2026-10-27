# Checkpoint History Archive and Recovery

**Status:** Version 1 was integrated by PR #5 at `d9f0872c120fb2408343859c938257e3962f2e09`. On the PR #6 Pre-M4 candidate `7ba2a21d2436941c5a57bad41628738149a8ea1d`, a clean clone verified the archive and passed canonical preflight; post-merge verification remains pending. The archive is committed project state; it is not an ignored cache.

## Storage contract

Before migration, `PROJECT_STATE.yaml` stores prior checkpoint records in `checkpoint_history`. After migration, that list is empty and `checkpoint_history_archive` points to the versioned archive at `.agents/state/checkpoint-history/`.

The archive contains:

- `manifest.json`, which declares the format/schema versions, source checkpoint identity, record counts/order, segment boundaries, compressed and uncompressed SHA-256 values, and a canonical logical-history SHA-256;
- `segments/segment-NNNNNN.jsonl.gz`, each containing at most 16 newline-delimited logical records in the initial migration; future appends create a new immutable one-record segment and update the manifest;
- `backups/source-state-<sha-prefix>.json.gz`, a compressed, byte-exact copy of the pre-migration canonical state.

Migration preserves the inline records in order and appends the source state's current `last_checkpoint` unless that exact ID and record are already present. Each history row retains its ID, timestamp, complete workspace Git snapshot, portable tracked-file manifest, workspace UUID when present, and any additional legacy fields. The original state remains independently recoverable from the verified backup. The manifest and state pointer authenticate the archive; preflight checks all referenced files and rejects missing, modified, extra, or incomplete archive data.

Checkpoint archives are excluded from the ordinary workspace hash inventory, portable Git manifest, and status comparison to avoid hashing their full contents on each checkpoint. Their integrity is instead checked using the canonical state pointer, the manifest digest, per-file hashes, and the aggregate logical-history digest. **All files under `.agents/state/checkpoint-history/` must be committed together with `PROJECT_STATE.yaml`** so clean clones can verify and recover the archive.

The checkpoint command verifies the archive even when the ordinary snapshot is unchanged and it would otherwise return through the no-op path. A missing, corrupt, or pending archive therefore prevents a successful no-op result; inspect preflight and use only a documented recovery path.

The canonical state remains small and no longer embeds the full history at each append. History is lossless, so total archive storage and the manifest still grow with the number of changed checkpoints. Appends are immutable and bounded per segment; they do not rewrite the historical records. Review repository/storage policy before the archive approaches 64 MiB. Do not delete or truncate records to meet that review threshold.

Integrity verification currently reads and hashes the byte-exact source backup and every referenced segment on preflight and before archive appends. Verification I/O and decompression therefore grow with total archive size; no latency benchmark has been run near the 64 MiB review threshold. Include preflight/checkpoint latency and memory in that review before increasing the threshold or continuing a high-frequency checkpoint workload.

## Migration and verification

From the repository root, preview without writing:

```bash
python3 scripts/migrate_checkpoint_history.py migrate
```

Apply the idempotent migration only on a cleanly reviewed branch/worktree:

```bash
python3 scripts/migrate_checkpoint_history.py migrate --apply
python3 scripts/migrate_checkpoint_history.py verify
python3 scripts/agent_preflight.py --json
```

The migration writes and verifies the compressed original-state backup and all archive segments before atomically replacing the canonical state pointer. It then uses the regular checkpoint command to refresh portable state/handoff metadata. The archive segment/manifest/state sequence is **not** one filesystem transaction; the recovery cases below are part of the format contract.

`restore-original` writes the byte-exact pre-migration state to a separate output file and refuses to overwrite different existing bytes:

```bash
python3 scripts/migrate_checkpoint_history.py restore-original --output /tmp/PROJECT_STATE.pre-migration.yaml
```

This is an archival recovery copy, not a rollback of later checkpoint history. Do not replace live canonical state with this old snapshot after archive appends unless an owner-approved recovery explicitly requires it.

## Interrupted operation and recovery

1. **Archive files written, canonical state still legacy:** preflight reports `CHECKPOINT_HISTORY_UNREFERENCED`. Preserve the files. `migrate --apply` resumes only if every existing file matches the deterministic expected output; an unexpected or different file is rejected.
2. **State pointer switched, final checkpoint refresh interrupted:** verify the archive first. Re-run `migrate --apply`; it detects stale portable state/handoff checksums and completes the regular checkpoint refresh. A normal `python3 scripts/agent_checkpoint.py` is also valid after state/backlog inspection.
3. **One immutable segment written before its manifest:** preflight reports `CHECKPOINT_HISTORY_PENDING_APPEND` only when the segment bytes exactly encode the current `last_checkpoint`. Run `python3 scripts/migrate_checkpoint_history.py recover-pending`; it verifies the segment, advances the manifest and pointer, then refreshes the checkpoint. If only a noncanonical or unrelated orphan exists, recovery refuses it.
4. **Manifest advanced before the canonical pointer:** preflight reports `CHECKPOINT_HISTORY_PENDING_APPEND` only when the manifest is exactly one record ahead, the prior logical digest matches the old pointer, and the new final record equals the canonical `last_checkpoint`. Use `recover-pending` to roll forward. Repeated recovery after success is rejected as “no pending append”; ordinary checkpointing remains safe.
5. **Missing, corrupt, or mismatched archive:** stop ordinary checkpointing. Do not edit hashes or discard files. Preserve the directory and inspect preflight output. The byte-exact source-state backup can be exported to another path, but it cannot reconstruct post-migration records absent from the archive.

Each canonical file is replaced atomically with file and directory synchronization where supported. The set of segment, manifest, state, and handoff replacements is not crash-atomic. Caught checkpoint exceptions roll back the prior canonical state/handoff bytes and archive files; a process or power loss can leave a detectable pending append or stale handoff. If rollback itself fails, stop and inspect preflight before continuing.

## Current migration evidence

The merged baseline was `16fc01a3fe731c0a0be127026cc64d049c0cf550`. At that baseline, `PROJECT_STATE.yaml` was 3,919,833 bytes with 139 inline history rows and one current checkpoint. The lossless migration produced 140 ordered logical records, including that current checkpoint, and a verified source-state backup. The first post-migration state was 65,811 bytes. See `.agents/evidence/RSK-010-checkpoint-history-migration-20261023.md` for the independent inventories, hashes, tests, exact revision, and current integration/PR status.
