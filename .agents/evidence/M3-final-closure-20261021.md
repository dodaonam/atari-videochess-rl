# M3 final closure engineering record — 2026-10-21

## Outcome and authority

Engineering corrections NEW-01 through NEW-04 are implemented and verified. The final source-backed release was built twice from the same frozen implementation and the nine files match byte-for-byte. A bounded real Stockfish 19 run is linked to that release and passes independent verification. M3-01 through M3-04 are technically supported for PM review; M3-001 remains `in_progress` until independent acceptance. PR #3 must remain open and unmerged. G3 remains unapproved. No M4–M7 work was started.

The source remains the owner-authorized Lichess Elite May 2022 package for local internal academic processing. The owner authorization, source decision, and terms review are in `M3-authorization-20261020.md`, `M3-source-decision-20261020.md`, and `M3-source-terms-20261020.md`. The upstream Lichess database is CC0; the third-party curated package's own license is unstated/unverified. This work did not redistribute the archive, bulk PGN, or bulk derived records. Stockfish use was limited to the already-authorized offline teacher role. Local CPU only; no paid, Colab, GPU, cloud-storage, opponent, benchmark, or inference-engine use.

## Revision and artifact impact

- Starting reviewed PR HEAD: `1af13b8b20715d3705c932012465d31c0d05a0a4`.
- Artifact-producing code revision: `40cd4e88bcaf987033a27f5f73995c5f44f21fb5`.
- Dataset code-tree SHA-256: `18defa5183708e68ac4e78d43e4618618b5b6640761b20b677153a614fd5966c`.
- Dataset config identity: `c65a489ddafc964383613f1641599f1a1b660a244bcacc4da67b9bd4ed5c9e57`.
- Teacher's separately computed code-tree SHA-256: `9f614140d8703d3e1bbe4d8c33e902c01ca541a7df9e1abe726fcd071e96edbb`. This is the teacher identity algorithm's value; it is not interchangeable with the dataset code-tree digest.

Changes in `videochess_rl/data/`, including holdout enforcement and teacher semantics, changed the dataset code-tree/config-bound identities. Therefore r6/r7 and a new teacher run were generated. Historical releases r3/r4 and corrective r4/r5, and historical teacher runs, remain unmodified.

## Finding dispositions

| ID | Result and correction | Verification |
|---|---|---|
| NEW-01 | Confirmed. Configurable retention below 50% could weaken the accepted holdout contract. New builds reject non-integer/bool thresholds below 5000 bp or above 10000 bp; split and release verification independently enforce the 50% floor. Higher thresholds remain supported; missing values default to 5000 bp. Minimum holdout position count remains independent. The below-80% warning is retained without rejecting otherwise-valid releases. Historical split schema 1.0 remains readable. | `test_holdout_retention_policy_cannot_be_lowered_by_config_or_split_call`, `test_holdout_retention_warning_is_retained_without_rejecting_a_valid_release`, hash-consistent tampered-release tests; current release verifier; historical schema 1.0 and corrective schema 1.1 release verification both exit 0. |
| NEW-02 | Confirmed. Partial teacher output could be returned as CLI success. CLI now exits 0 only for complete output, 3 for valid partial output, and nonzero for fatal errors; partial artifacts remain available and retain their accurate status. | CLI regression covers successful rows followed by timeout/error, not-attempted rows, overrun/status, and preserved partial output. M3 tests pass. |
| NEW-03 | Confirmed. Prior elapsed reporting ended before final publication/verification. Teacher run now reserves finalization time, records the measurement boundary and conservative upper bound, measures actual elapsed after closure, and downgrades deadline crossings to partial/overrun. Process cleanup has documented tolerance; no hard real-time guarantee is claimed. | Controlled-delay/finalization-overrun tests and manifest-integrity verification; actual complete real run stayed inside budget. |
| NEW-04 | Confirmed. WDL fields and duplicate MultiPV roots/ranks were not all semantically checked. Verifier now validates typed nonnegative per-mille WDL triples summing to 1000, perspective conversion, optional absence, unique valid ranks/root moves, candidate identity, and PV legality. | Hash-consistent tampered sidecars cover malformed WDL, perspective, duplicate roots/ranks, ordering, and missing optional WDL. The real Stockfish sidecar passes. |
| E-01 | Final exact-SHA clean-clone test is recorded in the PR description to avoid the commit/test-log SHA circularity. The PR description will identify clone SHA, environment, commands, timestamps, exit codes and counts; no source commit is created after that test. | Clean-clone recovery/full test suite is the final delivery check and remains pending until the final pushed PR HEAD is known. |

Additional compatibility correction: the original teacher schema 1.0 manifest legitimately lacks run-level `status`. The verifier requires that field for schema 1.1 but accepts schema 1.0 using its legacy row/count semantics. A hash-consistent synthetic v1.0 conversion test passes, and the historical real v1.0 teacher run verifies against the historical schema 1.0 release.

## Source-backed release and repeat

Source archive: `artifacts/m3/source/lichess_elite_2022-05.zip`, 97,163,552 bytes, SHA-256 `ad374c8fd9fb2fe5f03c1297aa1d47cbbce5caedf6e6e2d387ee816930afdb11`.

PGN member: `lichess_elite_2022-05.pgn`, 326,476,031 decompressed bytes, CRC verified, SHA-256 `0f88f18836be7e321aa1e0211b618e78d4e92065c126c45c95a6a55c1500a8e6`.

Both runs used `configs/data/m3-training-support.toml`, seeds 20261020/20261022/20261023, one worker, max 1,000 selected games, 20,000 positions, 32 positions/game, 1 GiB configured memory, 2 GiB output, and 7,200-second wall limit.

| Run | UTC interval | Wall | Peak RSS | Exit | Estimated disk used |
|---|---|---:|---:|---:|---:|
| `m3-training-support-final-closure-r6` | 2026-10-21 11:54:57–13:02:08 | 4,031.665 s | 367.3 MiB | 0 | 109,400,064 bytes |
| `m3-training-support-final-closure-r7` | 2026-10-21 13:02:19–14:13:19 | 4,259.546 s | 340.7 MiB | 0 | 94,953,472 bytes |

Both release IDs are `f10a679deddf06f3e1e3c39cf58db4e21176629c26c09034a271bf278189e890`. Manifest SHA-256 is `be1e1f9316fac01be893774cfe09a313de193fbd1a12ab2d219ff5c041104a12`; total output bytes are 39,994,522. All nine files are byte-identical between r6 and r7. The per-file hashes, byte sizes, commands, timestamps, resource measurements, and raw log hashes are in `M3-final-closure-record-20261021.json`; sanitized portable logs are in `logs/`.

Actual data quality:

- 355,535 games seen; 355,353 accepted observations; 182 quarantined empty records; zero other rejected games.
- 354,942 full-source normalized groups; 134 normalized duplicate groups (411 duplicate observations); 33 normalized-result conflict groups, none selected; zero conflicting source references; zero source-level duplicates.
- 1,000 selected games; 20,000 sampled positions before purge; 732 purged; 19,268 retained.
- Split game counts: train 795, validation 102, test 103.
- Positions before purge: train 15,727, validation 2,122, test 2,151. After purge: 15,196 / 2,015 / 2,057.
- Retention: train 96.62%, validation 94.96%, test 95.63%. The 50% mandatory threshold passes, no 80% warning is needed, and minimum holdout counts pass.
- Cross-split exact board signatures: 142 before purge, 0 after. Distinct replay-history states: 18,809 before, 18,765 after. Candidate rows: 597,164 before, 578,351 after; 18,813 candidate rows purged with their 732 parent positions.
- Legal candidates per position: 597,164 before purge; 578,351 retained. Rating/date/time-control metadata are present for the selected games. Clock values are unavailable in the source and are explicitly reported as such.
- Source-wide audit-index estimate: 275,087,884 bytes. Observed process peak RSS remained below 368 MiB against the 1 GiB limit. No GPU or cloud compute was used.

External `verify` commands independently checked each corrected release against the archive and source manifest. Both exited 0. The release contents and statistics are unchanged from corrective r4 except for code/config-bound position `sampling_config_sha256` and `sampling_id`; all 19,268 positions were compared and no other position fields differed. Games, rejection ledger, source manifest, and split are byte-identical. The release/config/stat/manifest hashes and release ID changed as expected because the frozen code revision and code-tree identity changed.

## Real Stockfish 19 teacher

Teacher run ID: `58febd814bb6bdd6fa67b990a1e4906ada14c31fafa265829fb49b7d3c203272`; schema `videochess-teacher-run-manifest/1.1`; release ID and dataset manifest SHA bind to r6/r7 (`f10a679…e890`, `be1e1f…a12`).

- Stockfish 19 binary SHA-256: `0f83d24cc46d2c66c60f16001af5444873bc112b7d028594513426894c12da19`; GPL license text SHA-256: `3972dc9744f6499f0f9b2dbf76696f2ae7ad8af9b23dde66d6af86c9dfb36986`.
- 128 deterministic samples, seed 20261025; one thread; 5,000 nodes/root; MultiPV 3; 64 MiB hash; hash cleared between roots; 30-second per-root cap; 1,800-second total wall cap; 2-second finalization reserve.
- 128 analyzed, 0 failed/unattempted; status `complete`; command exit 0; measured 135.54 seconds and about 318 MiB peak RSS.
- 380 MultiPV lines: 377 centipawn and 3 mate. Raw score perspective is side-to-move with White perspective recorded separately. Centipawn transform is `tanh(cp / 400)`, rounded to 8 decimal places; mate distance remains a separate typed value without scalar normalization.
- All 380 output lines contain WDL in `UCI_ShowWDL` per-mille-total-1000 format, side-to-move perspective plus consistent White perspective. All roots/PVs and candidate identities pass verification.
- `teacher.jsonl` SHA-256 `9add961adc73013776d96c8b84467b0f73a8edd310c13b0f55b0cfc9c5f70d65`; manifest JSON SHA-256 `71429e0f5993aed968454b1a94f3abba6a5c7d602ea698439495c59402b6c584`; manifest checksum file SHA-256 `b5d6f29218b87c4ec877c752ff037c6efa97cf007949ec6ae9547905b33951df`.
- Independent `verify --release ...r6 --teacher-run ...r1` passed, confirming release/sample binding and all 128 sidecar records.

Historical original teacher schema 1.0 run was separately reverified at current code. Its original release and teacher evidence remain unchanged; the compatibility verifier passed without adding or inventing a run-level status.

## Historical comparison and evidence integrity

- Original release r4 remains release ID `9e3944e1…b8991`, artifact revision `29c411b…9ccb`; its schema 1.0 release verification passes.
- Corrective r4/r5 remain release ID `7b51ec37…b1d9`, artifact revision `fbdd14d…ab48`; those two historical runs remain byte-identical and current schema 1.1 verification passes.
- New r6/r7 are immutable local artifacts with new release ID `f10a679…e890`, artifact revision `40cd4e8…fb5`; both repeat files match exactly and verify.
- Historical teacher-r2 and new teacher-r1 are separate runs. New teacher-r1 was executed and verified against r6/r7's shared final release ID; no old manifest was relabeled.
- Raw source, games, positions, and teacher rows remain ignored local artifacts. Only portable implementation, tests, hashes, manifests/evidence summaries, and sanitized logs are committed.

## Tests and checks at artifact-producing revision

All were executed against `40cd4e88bcaf987033a27f5f73995c5f44f21fb5` with the pinned project environment:

| Command | Interval UTC | Result |
|---|---|---|
| `python -m unittest discover -s tests -p test_m3_data.py -v` | 11:51:46–11:52:15 | 28 PASS |
| `python -m unittest discover -s tests -p test_pre_m3_contracts.py -v` | 11:52:15 (completed 11:52:15) | 8 PASS |
| `python -m unittest discover -s tests -v` | 11:52:15–11:53:21 | 220 PASS |
| `python -m compileall -q videochess_rl tests` | 14:15:59 | exit 0 |
| `uv lock --check` | 14:15:59 | exit 0 |
| `git diff --check` | 14:15:59 | exit 0 |
| `python3 scripts/agent_preflight.py` | 14:15:59 | exit 0; expected ignored-artifact manifest warning only |
| Release verification r6 / r7 | 13:03:21–13:05:30 / 14:13:38–14:15:36 | both exit 0 |
| Teacher-linked release verification | 13:08:26–13:13:10 | exit 0; 128/128 |
| Historical release schema 1.0 verification | 14:16:39–14:18:04 | exit 0 |
| Corrective release schema 1.1 verification | 14:18:04–14:20:03 | exit 0 |

The first full suite attempt on a dirty, not-yet-checkpointed workspace had 219/220 tests pass; the only failure was the fresh-context recovery test against the stale checkpoint. The workspace was checkpointed, and the full suite passed 220/220 on a clean checkpointed state. This does not weaken or skip the test.

The exact final PR HEAD clean-clone run is intentionally reported in the PR description, not committed into that same tested tree. It must record the tested SHA and actual command counts/exit codes to avoid a self-referential commit loop.

## Acceptance and PM review boundary

| Criterion | Engineering disposition | Limitation / review |
|---|---|---|
| M3-01 | Technically verified | The curated-package license remains unverified; local scoped academic use was owner-authorized, and no redistribution occurred. PM checks provenance/terms evidence. |
| M3-02 | Technically verified | Real Stockfish 19 run is complete and release-bound; review the binary/license hashes, settings, typed scores, WDL and sidecar. |
| M3-03 | Technically verified | r6/r7 are byte-identical and source-bound; raw data remains available only on the authorized host. |
| M3-04 | Technically verified | 50% retention floor is enforced; exact board overlap is zero after purge. This does not eliminate all statistical similarity between chess states. |

The PM/owner must independently inspect PR #3 targeting `initial-idea`, the corrective diff/tests, `.agents/evidence/M3-final-closure-record-20261021.json`, the per-file repeat table, source/terms evidence, final clean-clone record in the PR description, and final GitHub check scope. Only the PM/owner may record formal M3 acceptance and authorize integration. G3 approval remains separate.

## Reproduction

With the authorized archive and manifest locally available, on the pinned Python 3.12 environment:

```bash
python -m videochess_rl.data build --archive artifacts/m3/source/lichess_elite_2022-05.zip --source-manifest artifacts/m3/source/source-manifest.json --config configs/data/m3-training-support.toml --output artifacts/m3/training-support/<new-unique-run> --run-id <new-unique-run-id> --confirm-write
python -m videochess_rl.data verify --release artifacts/m3/training-support/<new-unique-run> --source-manifest artifacts/m3/source/source-manifest.json --archive artifacts/m3/source/lichess_elite_2022-05.zip
```

For the already-created local releases use `release-final-closure-r6` and `release-final-closure-r7`. Do not reuse their output paths; normal publication refuses overwrite. To reproduce the bounded teacher, use the command recorded in the machine-readable evidence and the existing pinned Stockfish 19 binary/license on PATH or at the explicit absolute paths; do not raise the 128-position/5,000-node limits. Restart and atomic finalization behavior are covered by synthetic interruption/resume tests. The source archive and bulk outputs are not present in GitHub.
