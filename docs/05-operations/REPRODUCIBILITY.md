# Reproducibility and Artifact Lifecycle

**Status:** M3 was accepted and merged on 2026-10-21. The exact source-backed release and bounded teacher run are recorded in portable manifests, but raw artifacts are absent from this checkout. No model was trained; M4 remains pending owner authorization.
**Canonical ownership:** [PROJECT_STATE.yaml](../../.agents/state/PROJECT_STATE.yaml) owns current phase and checkpoint; [BACKLOG.yaml](../../.agents/tasks/BACKLOG.yaml) owns task evidence; per-run manifests own experiment config and metrics.

## 1. Local development environment

The project targets Python 3.12, declares runtime dependencies in **pyproject.toml**, and commits **uv.lock**. Use the lock without changing it for routine setup and checks:

    uv sync --locked
    uv run --locked python -m unittest discover -s tests -v
    python3 scripts/agent_preflight.py

The dependency lock currently contains ALE-Py, Gymnasium, python-chess, and CPU-index PyTorch. The CPU local environment supports parsing, data checks, M0/M1/M2 verification, and small simulator experiments. PGN parsing and split creation are primarily CPU and disk work. Stockfish analysis is CPU work whose cost must be measured. GPU use belongs to later model training and needs separate entitlement/resource approval; no Colab or paid compute is authorized by this document.

Stockfish 19 is a separately provisioned host executable and is not part of uv sync. Follow **SETUP.md** to verify the pinned host installation. The M3 owner authorization separately permits the bounded teacher run recorded in [STOCKFISH_TEACHER.md](../04-research/STOCKFISH_TEACHER.md); the setup procedure itself grants no search permission. Do not use an unpinned system engine and claim reproducibility.

## 2. Source acquisition and dataset storage

Before an archive is downloaded, retain the approved source decision, source page and terms references, canonical URL, retrieval timestamp, HTTP metadata where available, expected byte ceiling, license/provenance notes, and intended use. After authorized retrieval, calculate SHA-256 on the exact archive and each extracted member. Keep originals read-only.

Store large source archives, derived datasets, run logs, and checkpoints under a project-approved persistent data location outside Git, such as the ignored data, datasets, artifacts, runs, or checkpoints directories. Confirm the actual storage owner, backup policy, quota, retention period, and access permissions before production output. Colab's ephemeral disk is not the sole retained copy. Never commit raw PGN archives, private player metadata, model weights, or secrets.

Every derived dataset release has a manifest listing its schema and code/config revisions, source archive/member hashes, parser and filter settings, game/position/teacher counts, split rules and seed, duplicate/leakage counts, and SHA-256/byte-size for each output. A separate release manifest hashes itself only through an external signed or recorded digest; avoid a self-hash cycle.

## 3. Run manifests, logs, and checkpoints

Each run directory is immutable and named by a unique run ID. Keep:

- config and config SHA-256;
- source revision and dirty-state record;
- command, UTC timestamps, environment/library/engine versions, seeds/RNG state, hardware and resource limits;
- raw result tables, summary code revision, failure/stop reasons, and full artifact hashes;
- checkpoint role, path, SHA-256, and resume parent/run ID.

Keep logs sanitized. Do not store full environment dumps, usernames beyond an approved need, credentials, tokens, local absolute machine paths, or copied chat transcripts. In canonical context state, use repository-relative paths only. For experiment artifacts in external storage, record a non-sensitive URI or storage key and manifest digest.

For resumable data processing, checkpoint only at completed game/position batches. A resume must match source archive/member hashes, schema versions, code revision, all sampling/split/teacher config hashes, and completed-output hashes. Write outputs to a new staging directory and publish a release directory only after validation and manifest checks pass. Never overwrite an existing run or release.

## 4. Artifact verification and retention

The agent preflight excludes artifact/data directories from ordinary file hashing and warns that they need independent manifests. Verify each referenced manifest separately; a clean clone can verify tracked manifests and evidence descriptions but cannot recompute hashes for ignored local artifacts it does not contain.

Use these evidence categories distinctly:

1. **Git-tracked only:** code, plans, sanitized reports, lock/config files, and manifests that exist in the checkout.
2. **Git plus local ignored artifacts:** M1 RGB traces, M3 source archives and data releases, teacher outputs, environment logs, simulator outputs, or temporary pilot data present on one host and independently hashed.
3. **External source/storage:** source archives, future datasets, models, or CI output that needs separate access and is identified by URL/storage reference and digest.

Record retention, backup owner, access control, and deletion date for each large release before collecting it. Keep raw public-game data only as needed and only under the approved source terms. Prefer transformed records with opaque source IDs and no player display names in published outputs.

At corrective-hardening recovery, **PROJECT_STATE.yaml** was 2,229,784 bytes with 96 retained checkpoint-history entries, above the 2 MiB ordinary-file hash boundary. Preflight validated the semantic state checksum and portable tracked manifest; a clean clone had previously accepted the portable snapshot. This size is a scale/maintenance risk, not evidence of corruption. Preserve all historical entries; do not truncate or migrate in the corrective PR.

The first four corrective mission checkpoints grew the file to 2,436,159 bytes and 100 entries, an observed increase of 206,375 bytes (about 51.6 kB per added entry in this small sample). This is not a long-term growth forecast. M3 recorded one pre-source checkpoint before its full archive scans rather than checkpointing every batch; after the final M3 checkpoint, recheck the actual size/count and checkpoint duration. Keep a lossless migration design as follow-up before any future checkpoint-heavy workload.

The ordinary-file size trigger has fired: the state measured 2,810,555 bytes and 107 retained checkpoint-history entries before final M3 handoff. This run did not demonstrate that migration is required: it used only a small number of meaningful checkpoints, and the 4 MiB, 128-entry, and measured 5-second write thresholds have not been reached. Preserve all history and avoid a risky migration in M3; revisit a lossless design before future checkpoint-heavy work. If a migration is later approved, preserve every checkpoint ID/timestamp, workspace snapshot, portable Git path/mode/blob manifest, semantic-state checksum, and handoff checksum; test old/new record equivalence, a fresh clean clone, and recovery from historical checkpoints before switching.

After the 2026-10-21 corrective-evidence checkpoint (`cp-fbdd14d6-20261021T022727431901Z`), `PROJECT_STATE.yaml` measures 3,862,087 bytes with 124 retained entries. The configured 4 MiB and 128-entry triggers have not fired, but both are near. The checkpoint completed normally and preserved the prior history; no migration was attempted. Avoid unnecessary further checkpoints and design/test a lossless migration before any checkpoint-heavy follow-on work.

M3 source acquisition must use the exact approved archive/member identity and bounded streaming. The official Lichess database uses `.pgn.zst` files; do not assume the Python environment has a Zstandard decoder. Confirm the selected source's actual format before retrieval and make any pinned dependency/host-tool choice separately. ZIP safety requirements, decompressed limits, and staging behavior are specified in [DATASET_SPEC.md](../04-research/DATASET_SPEC.md).

### Current Pre-M4 checkpoint disposition — 2026-10-22

At the verified `initial-idea` baseline `aba04d7b30fa614e2e7e74789dd610a162dd2cf0`, `PROJECT_STATE.yaml` was 3,431,959 bytes with 131 checkpoint-history entries. A historical pre-merge state at `e32e1e63` was 4,205,298 bytes with 129 entries; the post-merge compact JSON-compatible YAML representation measured 3,372,345 bytes with 130 entries, then 3,431,959 bytes with 131 entries. The full state and its history are preserved; formatting compaction explains the size decrease and is not a history migration.

`agent_checkpoint.py` now writes compact JSON-compatible YAML, detects an unchanged state/handoff/index/workspace and avoids appending a duplicate history entry, and refuses a projected write above 4 MiB with a 64 KiB reserve before touching state, handoff, or local workspace identity. It does not truncate or alter existing history records. Regression tests cover semantic history preservation, repeated no-op behavior, and size-guard non-mutation. A clean base worktree probe preserved all 131 prior records in the first checkpoint (3,490,091 bytes, a 58,132-byte increase, 0.905 seconds); the immediate repeat changed neither state nor handoff and added no entry (0.400 seconds). Preflight passed in that probe, with only the expected uncommitted-script drift and artifact-manifest warnings. Meaningful future checkpoints still grow the history; perform and verify a lossless history migration before the fail-safe size guard is reached during a checkpoint-heavy task.

The first Pre-M4 feature checkpoint took 0.809 seconds and produced 3,551,699 bytes with 133 history-array entries; the prior record remains preserved. Its post-checkpoint preflight passed with only the expected artifact-manifest warning. The current retained-history count remains a bounded capacity, not a long-term solution; see RSK-010 and the Pre-M4 evidence.

The accepted M3 release ID and manifest SHA are `f10a679deddf06f3e1e3c39cf58db4e21176629c26c09034a271bf278189e890` and `be1e1f9316fac01be893774cfe09a313de193fbd1a12ab2d219ff5c041104a12`. `artifacts/m3/` is absent from this checkout. Use only the exact retained release after independently verifying its nine files against the accepted manifest. Historical build/reproduction commands below do not authorize downloading or rebuilding the source; if the exact accepted artifact cannot be located, stop and ask the owner for a permitted recovery path.

## 5. Safe execution defaults

No production command should infer an unlimited run from omitted options. Future M3 commands must require explicit game, position, teacher, output-byte, wall-time, and worker limits. Check free disk and memory before source acquisition and processing. Stop with a durable reason when a cap is reached, the source/config changes, the engine identity differs, or repeated parse/label errors exceed the configured threshold.

The planned limits in [STOCKFISH_TEACHER.md](../04-research/STOCKFISH_TEACHER.md) are review proposals except for the exact bounded M3 run that the owner authorized. They do not authorize expanded labeling, Stockfish inference/opponent/evaluation use, Colab, paid compute, or model training.

## 6. M3 execution record and reproduction

The exact owner-authorized source was the Lichess Elite May 2022 package. Retrieval returned HTTP 200 on 2026-10-20, downloaded 97,163,552 bytes, and produced archive SHA-256 `ad374c8fd9fb2fe5f03c1297aa1d47cbbce5caedf6e6e2d387ee816930afdb11`. Its single `lichess_elite_2022-05.pgn` member was 326,476,031 bytes, CRC-verified, with SHA-256 `0f88f18836be7e321aa1e0211b618e78d4e92065c126c45c95a6a55c1500a8e6`. The source manifest and rights boundary are in `.agents/evidence/M3-source-manifest-20261020.json` and `.agents/evidence/M3-source-decision-20261020.md`. The package license remains unstated; the owner authorized local/internal academic use only, with no upload or redistribution.

The training-support profile is `configs/data/m3-training-support.toml`. It fixes the game/position/split seeds at 20261020/20261022/20261023, caps the full scan at 400,000 games, selection at 1,000 games and 20,000 positions, 32 positions per game, workers at one, output at 2 GiB, elapsed time at 7,200 seconds, and configured memory at 1 GiB. On revision `29c411bfd48dca8f1d463c758078175092639ccb`, independent r3 and r4 runs produced identical bytes and release identity `9e3944e1e35ca0d774e479a49d9b93eb769d14e52ffec4bc6f886bd4695b8991`. The config SHA-256 is `33186c332a956e006da473b4e37046e3cb953fd775d67be1906050ea4ed6a69f`; the split assignment SHA-256 is `84efed824e57de45c0058b73818bb7a9d740201ead38e9171308cee43bc0934e`. The seven manifest-listed outputs total 39,868,538 bytes; including the manifest and its checksum file, the release directory contains 39,870,594 bytes. The full metrics, timestamps, and per-file hashes are in `.agents/evidence/M3-reproducibility-r3-r4-20261020.json` and `.agents/evidence/M3-release-manifest-r3-20261020.json`.

With an existing Python 3.12 environment containing the locked project dependencies and the verified local archive, regenerate into a new output/run ID:

```bash
python -m videochess_rl.data build \
  --archive artifacts/m3/source/lichess_elite_2022-05.zip \
  --source-manifest artifacts/m3/source/source-manifest.json \
  --config configs/data/m3-training-support.toml \
  --output artifacts/m3/training-support/release-repro \
  --run-id m3-training-support-repro \
  --confirm-write
```

For an interrupted staging run, repeat the same command, output path, run ID, source, and config with `--resume`. Resume validates code/source/config identity, journal continuity, and completed segment hashes; a mismatch must fail and retain the partial artifacts. Never reuse an existing completed release path. Verify a finalized release and its source with:

```bash
python -m videochess_rl.data verify \
  --release artifacts/m3/training-support/release-repro \
  --source-manifest artifacts/m3/source/source-manifest.json \
  --archive artifacts/m3/source/lichess_elite_2022-05.zip
```

The real teacher subset used the same release, 128 positions, sample seed 20261025, 5,000 nodes per root, MultiPV 3, one thread, Hash 64 MiB, 30 seconds maximum UCI movetime per root, 30-second protocol deadline, two-second maximum process-watchdog grace, 1,800-second total wall limit, and 64 MiB output cap. It completed all 128 positions with 377 centipawn and 3 mate MultiPV rows. The exact teacher manifest SHA-256 is `4a2cb32ed163a215b661dc9b3801a4cb17f20a408dd5aab9e3219456d36d7891`; the sidecar SHA-256 is `d1f0620beb6eb985ec36c85a5eb6846917656221f3c5a2171e4eecc38c879d6f`. Centipawns use `tanh(cp / 400.0)`, rounded to eight decimals; signed mate distances remain typed and unnormalized. Stockfish is not part of inference.

### Corrective-hardened release and teacher (2026-10-21)

The corrective revision `fbdd14d6bed487e5b1388034048eccdbe952ab48` supersedes the historical release for M3 review; it does not rewrite it. Two new source-backed builds, r4 and r5, used the same immutable archive/member, `m3-training-support.toml`, and fixed seeds. Both generated release ID `7b51ec3761ad28aa7a2882691b3c314d35115ab339769251ff2556e706a5b1d9`; the independent file comparison found all nine release files byte-identical. The r4 manifest SHA-256 is `77e217423e187278c584b8f566a846fd606bddaadad19179b7bef63959bd5abe`. Seven manifest outputs total 39,994,522 bytes. The release retained 19,268 of 20,000 selected positions after 732 board-overlap purges, with zero cross-split board signatures and validation/test retention of 94.96%/95.63%. All 33 full-source normalized-result conflict groups were excluded before bottom-K selection. Full run identities, hashes, statistics, comparison, and sanitized logs are linked from `.agents/evidence/M3-corrective-hardening-20261021.md`.

The corrected source/release verification rechecked the archive SHA-256 `ad374c8fd9fb2fe5f03c1297aa1d47cbbce5caedf6e6e2d387ee816930afdb11`, PGN-member SHA-256 `0f88f18836be7e321aa1e0211b618e78d4e92065c126c45c95a6a55c1500a8e6`, and ZIP CRC. Its bounded Stockfish teacher run is separately bound to the corrected release and is documented in `.agents/evidence/M3-corrective-hardening-20261021.md`; the historical teacher-r2 above remains bound only to historical r3/r4. Source and bulk-derived artifacts remain local ignored files and are not in Git.

Teacher reproduction requires the existing Stockfish 19 executable and retained GPL text to match the recorded hashes. With `SF19` and `SF19_LICENSE` set to those verified local paths:

```bash
python -m videochess_rl.data teacher \
  --release artifacts/m3/training-support/release-repro \
  --output artifacts/m3/teacher-training-support/teacher-repro \
  --engine "$SF19" \
  --engine-sha256 0f83d24cc46d2c66c60f16001af5444873bc112b7d028594513426894c12da19 \
  --license "$SF19_LICENSE" \
  --license-sha256 3972dc9744f6499f0f9b2dbf76696f2ae7ad8af9b23dde66d6af86c9dfb36986 \
  --max-positions 128 --seed 20261025 --nodes 5000 --multipv 3 \
  --threads 1 --hash-mib 64 --timeout-seconds 30 \
  --max-wall-seconds 1800 --max-output-bytes 67108864 --confirm-write
```

Both full rebuilds took about 31 minutes wall time and 30.6 CPU minutes, with roughly 289 MiB peak RSS and about 39.9 MB of release output. The verified run paths are local ignored artifacts under `artifacts/m3/`; they are not present in GitHub and cannot be reverified from a clean clone without the source archive and host engine. Only manifests, sanitized logs, code, tests, and reproduction instructions are portable. No Colab, GPU, cloud storage, or paid compute was used.

### Final corrective closure regeneration (2026-10-21)

The final closure hardening changed artifact-producing code identity, so two new immutable releases, `release-final-closure-r6` and `release-final-closure-r7`, were built from code revision `40cd4e88bcaf987033a27f5f73995c5f44f21fb5` using the exact same authorized archive, member, training-support TOML, and fixed seeds. Both runs scanned 355,535 games and selected 1,000 games/20,000 positions. Their shared release ID is `f10a679deddf06f3e1e3c39cf58db4e21176629c26c09034a271bf278189e890`; manifest SHA-256 is `be1e1f9316fac01be893774cfe09a313de193fbd1a12ab2d219ff5c041104a12`. All nine release files match byte-for-byte. A source-bound independent verifier passed each release. Full per-file identities, measurements, and command records are in `.agents/evidence/M3-final-closure-record-20261021.json` and `.agents/evidence/M3-final-closure-20261021.md`.

The closure release preserves the same selected games, split assignments, and position semantics as corrective r4; every position row differs only in the code/config-bound `sampling_config_sha256` and `sampling_id`. The release/config/statistics hashes and release ID changed because the artifact-producing revision and code-tree identity changed. Historical releases and teacher runs were not modified. A new 128-position real Stockfish 19 run (`teacher-final-closure-r1`) is bound to the final release ID and independently verifies: 128 analyzed, zero failed/unattempted, 377 centipawn and 3 mate MultiPV rows, with WDL semantics validated. It took 135.54 seconds. The source package rights caveat remains: upstream Lichess data is CC0, while the third-party curated package license is unstated; source and bulk outputs remain local and are not redistributed.

### Final pre-merge verification contract (2026-10-21)

The current release verifier recomputes every normalized-game split using the versioned split rule and the immutable configured seed. It also validates the per-position sampling config/run identities and independently recreates the bottom-K selected `(game_id, ply_index)` set from released game histories and configured caps. Retained positions plus the purge ledger must exactly reconcile with that set. These checks validate selection among the selected game rows; they do not replace the immutable source scan evidence for source-wide game selection. They do not alter identity algorithms or previously produced release bytes. Historical release producer revisions remain attached to their own manifests.

Teacher manifest schema 1.2 uses `command_elapsed_projection_seconds` and states that it is an estimate, not a guaranteed elapsed-time upper bound. The runner still checks actual monotonic elapsed after final output closure and records an overrun as partial. Historical schema 1.1's `command_elapsed_upper_bound_seconds` is accepted as the legacy reserve projection only, and schema 1.0 remains supported. The R-01–R-03 findings, exact commands, artifact identity impact, and final verifier outputs are documented in `.agents/evidence/M3-premerge-final-verification-20261021.md`.

