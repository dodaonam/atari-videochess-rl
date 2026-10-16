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

At the Pre-M3 starting checkpoint, **PROJECT_STATE.yaml** was 2,035,944 bytes and had 92 retained checkpoint-history entries. Its history preserves full workspace snapshots and continues to grow. Do not truncate history or rewrite it without a schema migration and independent recovery tests. Track growth; if it approaches the 2 MiB ordinary-hash boundary, prepare a reviewed migration that externalizes immutable checkpoint details while keeping the current canonical snapshot and portable manifest verifiable.

## 5. Safe execution defaults

No production command should infer an unlimited run from omitted options. Future M3 commands must require explicit game, position, teacher, output-byte, wall-time, and worker limits. Check free disk and memory before source acquisition and processing. Stop with a durable reason when a cap is reached, the source/config changes, the engine identity differs, or repeated parse/label errors exceed the configured threshold.

The planned limits in [STOCKFISH_TEACHER.md](../04-research/STOCKFISH_TEACHER.md) are review proposals only. Their existence is not authorization to download data, use Stockfish, run Colab, train a model, or incur costs.

