# Reproducibility and Artifact Lifecycle

**Status:** Proposed operations contract for M3 and later; no dataset/model artifacts were generated during Pre-M3.  
**Canonical ownership:** [PROJECT_STATE.yaml](../../.agents/state/PROJECT_STATE.yaml) owns current phase and checkpoint; [BACKLOG.yaml](../../.agents/tasks/BACKLOG.yaml) owns task evidence; per-run manifests own experiment config and metrics.

## 1. Local development environment

The project targets Python 3.12, declares runtime dependencies in **pyproject.toml**, and commits **uv.lock**. Use the lock without changing it for routine setup and checks:

    uv sync --locked
    uv run --locked python -m unittest discover -s tests -v
    python3 scripts/agent_preflight.py

The dependency lock currently contains ALE-Py, Gymnasium, python-chess, and CPU-index PyTorch. The CPU local environment supports parsing, data checks, M0/M1/M2 verification, and small simulator experiments. PGN parsing and split creation are primarily CPU and disk work. Stockfish analysis is CPU work whose cost must be measured. GPU use belongs to later model training and needs separate entitlement/resource approval; no Colab or paid compute is authorized by this document.

Stockfish 19 is a separately provisioned host executable and is not part of uv sync. Follow **SETUP.md** only for the recorded UCI readiness setup. That setup is not permission to analyze positions. Do not use an unpinned system engine and claim reproducibility.

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
2. **Git plus local ignored artifacts:** M1 RGB traces, environment logs, simulator outputs, or temporary pilot data present on one host and independently hashed.
3. **External source/storage:** source archives, future datasets, models, or CI output that needs separate access and is identified by URL/storage reference and digest.

Record retention, backup owner, access control, and deletion date for each large release before collecting it. Keep raw public-game data only as needed and only under the approved source terms. Prefer transformed records with opaque source IDs and no player display names in published outputs.

At corrective-hardening recovery, **PROJECT_STATE.yaml** was 2,229,784 bytes with 96 retained checkpoint-history entries, above the 2 MiB ordinary-file hash boundary. Preflight validated the semantic state checksum and portable tracked manifest; a clean clone had previously accepted the portable snapshot. This size is a scale/maintenance risk, not evidence of corruption. Preserve all historical entries; do not truncate or migrate in the corrective PR.

The first four corrective mission checkpoints grew the file to 2,436,159 bytes and 100 entries, an observed increase of 206,375 bytes (about 51.6 kB per added entry in this small sample). This is not a long-term growth forecast. Limit checkpoints to meaningful state changes and complete a lossless migration design before sustained M3 batch processing. Recheck the actual size/count after the final readiness checkpoint.

The migration trigger has already fired. During M3 run preparation, before the first sustained checkpoint-heavy processing run, prepare and review a lossless migration design. Start earlier if the file exceeds 4 MiB, history exceeds 128 entries, or a measured checkpoint write exceeds 5 seconds. Preserve every checkpoint ID/timestamp, workspace snapshot, portable Git path/mode/blob manifest, semantic-state checksum, and handoff checksum; maintain historical lookup without duplicating canonical live status. Before switching, test old/new record equivalence, a fresh clean clone, and recovery from historical checkpoints. Record actual state size and checkpoint timing before claiming the thresholds were reached. The migration is assigned to M3 operational preparation; there is no new state file or migration implementation in this mission.

M3 source acquisition must use the exact approved archive/member identity and bounded streaming. The official Lichess database uses `.pgn.zst` files; do not assume the Python environment has a Zstandard decoder. Confirm the selected source's actual format before retrieval and make any pinned dependency/host-tool choice separately. ZIP safety requirements, decompressed limits, and staging behavior are specified in [DATASET_SPEC.md](../04-research/DATASET_SPEC.md).

## 5. Safe execution defaults

No production command should infer an unlimited run from omitted options. Future M3 commands must require explicit game, position, teacher, output-byte, wall-time, and worker limits. Check free disk and memory before source acquisition and processing. Stop with a durable reason when a cap is reached, the source/config changes, the engine identity differs, or repeated parse/label errors exceed the configured threshold.

The planned limits in [STOCKFISH_TEACHER.md](../04-research/STOCKFISH_TEACHER.md) are review proposals only. Their existence is not authorization to download data, use Stockfish, run Colab, train a model, or incur costs.

