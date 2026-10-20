# M3 execution evidence — 2026-10-20 (in progress)

This record captures completed work and the remaining verification at the current checkpoint. It is not a final M3 acceptance decision. The May 2022 source is used only for the owner-authorized bounded local academic work; no archive or bulk game records are included in Git.

## Authorization and source

- M3-001 direct authorization: [M3-authorization-20261020.md](M3-authorization-20261020.md), recorded at 2026-10-20T14:34:24Z. G3 remains unapproved.
- Source/use decision and terms: [M3-source-decision-20261020.md](M3-source-decision-20261020.md) and [M3-source-terms-20261020.md](M3-source-terms-20261020.md). The third-party package license remains unstated. Official Lichess CC0 language is not attributed to the curated package. Owner authorization covers bounded local/internal use only; it does not establish redistribution rights.
- Retrieval followed the source decision. At 2026-10-20T15:25:10Z the bounded fetch received HTTP 200 and downloaded 97,163,552 bytes. Archive SHA-256: `ad374c8fd9fb2fe5f03c1297aa1d47cbbce5caedf6e6e2d387ee816930afdb11`.
- The ZIP has one approved PGN member, `lichess_elite_2022-05.pgn`: 326,476,031 uncompressed bytes, CRC32 `eaf7e457`, compression ratio 3.360. Streaming SHA-256: `0f88f18836be7e321aa1e0211b618e78d4e92065c126c45c95a6a55c1500a8e6`. The archive has no publisher-provided checksum or package license.
- Retrieval caps were 150 MiB compressed, 512 MiB/member, 512 MiB total decompressed, 200:1 ratio, two retries, and 45-second network timeout. The actual source was smaller than the configured limits. The original archive is read-only under ignored `artifacts/m3/source/`.
- Portable source manifest: [M3-source-manifest-20261020.json](M3-source-manifest-20261020.json), SHA-256 `f2ff571ce81a47b1191f7b57c2f2d16c48ebde6b334aeb6e82d7b173dc2b2935`.

## Dataset runs

### Initial pilot

- Profile: `configs/data/m3-pilot.toml`; requested ceilings 200 games and 10,000 positions.
- 200 games accepted; no rejects, quarantines, or duplicates. 9,682 positions selected; 9,285 retained after purge. This is a bounded source window, not the training-support release.
- Cross-split board signatures: 91 before purge, zero after. Validation/test retained 95.17%/95.80%. Legal candidates per position: min 1, median 32, max 64.
- Release ID `24bb40a33f4dfbc024ac8dc3a670d67b6c19841295d964226bfc6b1d14e2887e`; output bytes 18,492,851. CLI release verification passed at 2026-10-20T15:27:40Z–15:28:04Z.
- Portable pilot manifest: [M3-pilot-manifest-20261020.json](M3-pilot-manifest-20261020.json), SHA-256 `3490154dc158e19039b1a77d94248e0387393de88fe490483d35d3eeed88cbc4`.

### Initial training-support release (r1)

- Profile: `configs/data/m3-training-support.toml`; game seed 20261020, position seed 20261022, split seed 20261023; bottom-K game selection; maximum 1,000 games, 20,000 positions, 32 positions/game; one worker; 2 GiB output cap; 7,200-second wall cap; 1 GiB configured memory limit.
- The full 326,476,031-byte member stream was read and its hash matched the source manifest. 355,535 games seen; 355,353 accepted before deduplication; zero rejected; 182 quarantined as `empty_game`. No source-reference duplicate observations. Normalized duplicate observations: 411 in 134 groups; no conflicting normalized groups.
- Selected 1,000 unique games (795 train, 102 validation, 103 test). Selected 20,000 position rows; 19,268 retained after purge. Pre/post split counts: train 15,727/15,196; validation 2,122/2,015; test 2,151/2,057. Retention was 96.62%, 94.96%, and 95.63%, respectively.
- Cross-split board signatures: 142 before purge, zero after. Distinct replay-history states: 18,809 before and 18,765 after. Purged 732 samples and their 18,813 legal candidates. The zero board-signature overlap is limited to this signature definition and does not eliminate other statistical similarity.
- All 1,000 selected games had rating/date/time-control metadata. Game plies: min 8, median 79, p90 131, max 517. Opening prefixes: 755 unique; HHI 0.003114; maximum prefix count 34. Candidate counts: min 1, median 32, max 64.
- Build ran 2026-10-20T15:28:49Z–16:03:27Z: 2,077.366 seconds wall time, 288.71 MiB peak RSS. It wrote 39,868,538 listed output bytes (39,870,594 bytes on disk). Release ID `7addd66c554cdf34fbfff99799d5c9edcc611dcff5387d1d0d6d5dfa5ef33efb`; release-manifest SHA-256 `ed3dc7d545e1859a48813f64e2f546e3bd7b0b0f2e573d2672c9f489ad03f551`; config SHA-256 `f02e680188662b7cba2238f45ff2727ff2729a30ef3cda62c79f1665f9e81d3d`; split SHA-256 `84efed824e57de45c0058b73818bb7a9d740201ead38e9171308cee43bc0934e`.
- CLI verification of the source, archive, and release passed at 2026-10-20T16:04:17Z–16:05:10Z. Bulk JSONL and statistics remain only in ignored `artifacts/m3/training-support/release-r1/`.
- Portable release manifest: [M3-release-manifest-r1-20261020.json](M3-release-manifest-r1-20261020.json), SHA-256 `ed3dc7d545e1859a48813f64e2f546e3bd7b0b0f2e573d2672c9f489ad03f551`.

### Rebuild attempt and reproducibility status

- A second full source scan began at 2026-10-20T16:11:35Z at revision `45f068e39a2d516cf5a6a4ed3c9f53671ca5d776`, while tracked documentation and tests had become dirty. It was stopped at 130,000/355,535 games after 628.28 seconds elapsed (669.63 CPU seconds) because its automatically captured dirty-worktree/code identity could not support the required identical-config release comparison. Exit code was -15. Its run journal and partial quarantine output remain preserved under ignored `artifacts/m3/runs/m3-training-support-20261020-r2.staging/`; no r2 release was finalized.
- This interrupted run is not a determinism result. A full source rebuild and repeat will be performed from the same clean committed revision/config, compared by release identity and all semantic output hashes, before M3-03 is marked passed.

## Stockfish teacher evidence to date

- Existing host Stockfish 19 binary SHA-256 `0f83d24cc46d2c66c60f16001af5444873bc112b7d028594513426894c12da19` (103,153,472 bytes). Retained GPL text SHA-256 `3972dc9744f6499f0f9b2dbf76696f2ae7ad8af9b23dde66d6af86c9dfb36986` (35,149 bytes). Neither is included in Git.
- A real bounded run analyzed 128 of 128 selected training-support positions: 5,000 nodes/root, MultiPV 3, one thread, 64 MiB Hash, 30-second protocol timeout, 1,800-second total wall cap; seed 20261025. It reported 640,363 nodes, 2.612 seconds search elapsed, 49.0046 positions/second, zero row failures, 377 centipawn and 3 mate MultiPV lines. CP transform was `tanh(cp/400)`, rounded to 8 decimals. Mate distances remained typed and unnormalized. The output sidecar hash was `734db32074930bc4a4645f46f63b173677d60c5502645ce6e0b6b3ca4556704b`.
- This run predates a hard-timeout regression fix. Tests showed the earlier python-chess protocol timeout did not itself impose a search deadline. The runner now combines a node cap with UCI `movetime`, has an external process-kill watchdog, records per-root limits, enforces `Clear Hash`, rejects missing/invalid root PVs, and preserves failure rows. Re-run the real teacher after the correction; do not use the earlier run as final M3-02 evidence.
- Earlier real-run manifest: [M3-teacher-manifest-r1-20261020.json](M3-teacher-manifest-r1-20261020.json), SHA-256 `81c76de2d9b18e908cb7a6c873175f42b50e69a78fbe629e82fc68ba44f88cc9`.

## Verification and current acceptance status

- The 211-test repository suite passed at revision `45f068e39a2d516cf5a6a4ed3c9f53671ca5d776` before the timeout hardening. The focused M3 module passed 19 tests after the hardening; the full suite is being rerun at the clean fix commit.
- `uv lock --check --python /usr/bin/python3` passed at fix commit `953c1924372ee5a153c78308c4fab44e0d104ebf`. No dependency was added or installed.
- M3-01: source identification, owner scope, rights uncertainty, retrieval order, archive/member hashes, and local-only boundary are documented. The package's public redistribution rights remain unverified and are not used for public distribution.
- M3-02: a real run exists, but final evidence is pending a repeat with the corrected search time cap and process watchdog.
- M3-03: the first source-backed artifact and its provenance verify; criterion remains pending the clean deterministic full repeat and recovery/reconstruction verification.
- M3-04: the initial split satisfies the configured retention and exact board-signature purge checks; final confirmation will use the clean repeated release and retained report.

The source archive, full `games.jsonl`, `positions.jsonl`, split ledger, statistics, PGN-derived bulk records, and teacher sidecar are not tracked. Their current local locations are below ignored `artifacts/m3/`. No Colab, GPU, cloud storage, or paid resource was used.
