# M03 — Expert Dataset Plan

- **Plan ID:** M03
- **Milestone:** M3 — Expert dataset, within the engineering sequence owned by **EXECUTION_PLAN.md**
- **Plan status:** ready for independent review; this plan is not authorization to execute M3
- **Canonical task:** M3-001 in **BACKLOG.yaml**, pending owner/instructor prerequisites and separate M3 authorization
- **Dependencies:** M2-001 complete and G2 approved; retain G3 unapproved until its owner review
- **Acceptance:** M3-01 through M3-04 in **docs/06-quality/ACCEPTANCE_CRITERIA.md**
- **Requirements:** B-04, B-05, B-07; O-01, O-04, O-06, and O-07 remain open
- **Relevant decision:** accepted **ADR-0002** for stable UCI action identity, Board history, and color perspective; it does not approve data, Stockfish, or neural architecture
- **Contracts:** [DATASET_SPEC.md](../../docs/04-research/DATASET_SPEC.md), [STOCKFISH_TEACHER.md](../../docs/04-research/STOCKFISH_TEACHER.md), [EXPERIMENT_PROTOCOL.md](../../docs/04-research/EXPERIMENT_PROTOCOL.md), [REPRODUCIBILITY.md](../../docs/05-operations/REPRODUCIBILITY.md)

## Objective

Create a reproducible, provenance-preserving, leakage-audited expert dataset for later supervised work. Keep expert played moves, game outcomes, and optional Stockfish annotations as distinct signals. M3 does not train a model, claim playing strength, change the M2 simulator, run reinforcement learning, or evaluate ALE gameplay.

## Authorization gates and source prerequisites

Before any source retrieval or processing:

1. The owner reviews this plan and explicitly authorizes M3 separately from Pre-M3 review.
2. The source and use decision O-06 is resolved for a specific archive, terms, retention, transformation, and any intended distribution.
3. O-01/O-07 are resolved before Stockfish searches, labels, engine-opponent use, or offline engine evaluation. A PGN-only behavior dataset may proceed if the approved source scope allows it and M3-02 is recorded honestly.
4. O-04 is resolved before external storage, Colab, paid compute, or limits beyond verified local resources.
5. A source profile confirms archive size, PGN member/header behavior, and parser feasibility. Do not use the publisher's game-count/size listing as measured local evidence.

The May 2022 Lichess Elite package remains a candidate, not an approved source. Its publisher listing reports 355,535 games and 93 MB but does not state a license. The official Lichess rated-standard export and official broadcast data are alternatives with different sizes, distributions, and terms. Never ingest a source until the decision is recorded.

## Scope

- immutable source/archive manifest and permitted local retention;
- streaming PGN parsing, validation, and reason-coded quarantine;
- game-level records and deterministic position extraction/sampling;
- legal UCI candidate sets and played-move/result labels with explicit perspective;
- exact game and position deduplication;
- game-grouped, deterministic splits plus cross-split position-purge audit;
- optional, separately authorized, versioned Stockfish teacher annotations;
- bounded CLI, output manifests/hashes, statistics, interruption recovery, and focused tests;
- M3-01 through M3-04 evidence and one implementation PR against **initial-idea**.

## Exclusions

- No data download, ingestion, or production dataset generation until the source gate is approved.
- No bulk Stockfish labels or engine opponent/evaluation until O-01/O-07 permit that role.
- No neural model, supervised training, checkpoint, simulator RL, M6/ALE play, or M7 evaluation.
- No fixed model architecture, feature planes, global action vocabulary, loss weighting, or Q-value initialization.
- No Colab/GPU or paid storage/compute without separate approval.
- No public dataset release or repository LICENSE decision.
- No additional data platform, server database, workflow orchestrator, or distributed framework without measured need.

## Proposed module boundaries

Add the smallest package under **videochess_rl/data/**:

| Planned module | Responsibility | Boundary |
|---|---|---|
| **contracts.py** | Versioned source/game/position/teacher/split/release record validation and stable IDs. | No training/model dependency. |
| **source.py** | Source manifest, archive/member checks, SHA-256, ZIP CRC, bounded input validation. | Never decides source rights; requires a recorded approved decision. |
| **pgn.py** | One-game-at-a-time parsing, raw/normalized headers, UCI replay, structured diagnostics. | Uses python-chess Board/history; never repairs illegal moves silently. |
| **sampling.py** | Deterministic source-order-independent game bottom-k and bounded per-game ply sampling. | Seed/config are required and recorded. |
| **dedup.py** | Source ID, normalized game, repeated canonical-position identity, conflict/quarantine counts. | Does not drop conflicting results silently. |
| **split.py** | Stable game-hash assignment and deterministic cross-split canonical-position purge. | Candidate/teacher rows inherit the position's split. |
| **teacher.py** | Optional UCI engine identity, bounded searches, raw score/MultiPV capture, failure records. | Separate process; absent/disabled by default; no inference integration. |
| **export.py** | JSON Lines/gzip outputs, atomic staging, row counts, hashes, release manifest. | No data-frame/database requirement. |
| **stats.py** | Quality, label, coverage, split, and resource summaries. | Reports measured values only. |
| **cli.py** | Profile, validate, build, and optionally label subcommands with explicit caps. | No implicit unbounded or online-download mode. |

Use standard library file/JSON/ZIP/gzip/hash/statistics interfaces and the already locked python-chess dependency. If an approved source is Zstandard-compressed, make a separate dependency decision and pin any new package. Do not quietly assume a host decompressor is installed.

## Configuration and command interface

Store human-readable TOML configuration under **configs/data/** and hash its canonical normalized content. Separate source, parsing/filter, sampling, split, teacher, and resource settings. Configuration must include schema versions, deterministic seed, source archive/member hash, start-position and variant policy, minimum/maximum plies where approved, max games, max positions, max teacher positions, max bytes, max elapsed time, max worker count, and output directory.

Planned CLI shape:

- profile an already authorized source with a maximum archive-byte, game, and header-sample limit;
- validate a source manifest and PGN stream without writing a release;
- build a dataset from an approved local archive with required explicit caps;
- optionally label a deterministic capped position list only when teacher config and O-01/O-07 approval IDs are supplied;
- verify an existing release manifest and report all mismatches.

No default command downloads a URL or processes all input. CLI output states the exact source/config hashes and planned limits before any write. A separate affirmative option is required to start each write-producing command.

## Processing and recovery sequence

1. Re-read state/backlog and inspect explicit M3 authorization, O-01/O-04/O-06/O-07, plan, ADR-0002, and acceptance criteria.
2. Confirm source approval and capture terms/provenance; measure actual archive byte ceiling and expected disk use.
3. Download only within approved scope to a staging path; retain original bytes read-only, verify SHA-256/ZIP CRC/member size, and record retrieval facts. If source has no published checksum, record that fact and compute a local digest after retrieval.
4. Run a no-output profile on a capped game/header sample. Review observed header, variant, result, rating, time-control, comments/variation, parse-error, and player-identifier statistics.
5. Validate/replay games one at a time. Quarantine errors with stable reason codes and source ordinals; never discard silently.
6. Generate game rows and deterministic bounded position samples. Store initial FEN plus complete UCI replay path, current FEN, side to move, legal UCI moves, played UCI move, and White/side-to-move result.
7. Deduplicate exact game identity, report conflicts, then assign whole normalized games to splits with a frozen hash seed. Purge repeated canonical position fingerprints from other rows and retain before/after leakage counts.
8. If authorized, run a separate bounded teacher pass after the PGN-only dataset is valid. Record actual engine binary/hash/UCI identity/options, node/depth limit, MultiPV, root perspective, raw cp/mate/WDL types, elapsed time, and per-position errors. Never treat MultiPV as exhaustive.
9. Write to a new run-specific staging directory. Checkpoint every fixed completed game batch with source/config hashes and output offsets/hashes. On interruption, resume only if every source/schema/config/code hash and output digest matches.
10. Validate all cross-references, legal candidates, split invariants, release counts, and output hashes. Atomically finalize to a new immutable release directory; never overwrite an earlier release.
11. Run focused and full applicable tests, M3 preflight/recovery checks, compare statistics, and prepare evidence. Stop rather than publish a partial release if any invariant fails.

## Resource safeguards

Use the proposed M03 tiers in **STOCKFISH_TEACHER.md** as planning ceilings only. Before execution measure a small approved sample for compressed/uncompressed bytes, average bytes per game/position/teacher record, parse throughput, legal candidates per position, and teacher p50/p95 nodes and wall time. Then compute projected CPU-hours and peak storage from the formulas in that contract.

Require explicit max-games, max-positions, max-teacher-positions, max-output-bytes, max-wall-time, max-workers, and memory/hash limits. Check free disk against the estimated peak plus 20% reserve. Default teacher workers to one. Stop on mismatched hashes, source change, corrupt archive, resource-cap exhaustion, repeated parser/engine failures over configured thresholds, unexpected variant rate, or any unapproved use. Record the stop reason and keep staging clearly marked incomplete.

## M3 test and acceptance mapping

| Criterion | Modules / tests | Required evidence |
|---|---|---|
| **M3-01** — Source data and licenses are documented before ingestion. | Source-manifest schema validation; tests reject build without source approval/rights evidence and reject hash/size mismatch. | Approved source decision, terms/provenance snapshot, retrieval manifest, actual archive/member SHA-256 and size before parsing. |
| **M3-02** — Stockfish version, search settings, score perspective, normalization, and mate handling are recorded. | Teacher config/UCI tests; fake-engine tests cover MultiPV ordering, cp/mate separation, perspective conversion, terminal state, missing score, and resource cap. | If used: binary/license hash, UCI identification, config hash, raw teacher sample and run manifest. If not authorized: precise non-use status and unresolved approval; do not claim this criterion passed. |
| **M3-03** — Generation is reproducible and every sample has provenance. | PGN parser, stable IDs, sampling, resume, output exporter, per-row provenance and hash tests. | Source/code/config revision, command, seeds, counts, diagnostics, data manifests/hashes, resumed-run check, and sanitized log. |
| **M3-04** — Splits prevent leakage between related positions/candidates; statistics and hashes are recorded. | Grouped split, canonical position dedup/purge, candidate inheritance, overlap and determinism tests. | Frozen split seed/config hash, game and position overlap before/after, duplicate purge counts, per-split stats, and file hashes. |

Test fixtures must be synthetic, tiny, and authored for the tests. Do not commit downloaded public PGNs or player identities. Teacher tests use a fake UCI executable; a separate explicit smoke check may handshake with the approved host binary but must not search without permission.

## Verification and Git workflow

Before implementation, verify clean worktree, locked environment, source approval, and M2 baseline. Use a new branch **feature/m3-expert-dataset** from current **initial-idea**, with small commits for source contracts, parser/split pipeline, optional teacher support, and verification evidence. Run preflight before and after checkpointing; record command timestamps, exit status, full revision, and sanitized logs. Run tests in the locked environment and verify in a clean clone after push.

Create one PR targeting **initial-idea**. Keep it unmerged pending independent PM review. Do not change the default branch or release data/models.

## Recovery procedure

On restart, read **AGENTS.md**, **REQUIREMENTS.md**, project state, handoff, backlog, this plan, dataset/teacher contracts, ADR-0002, acceptance criteria, blockers, and verified findings. Run preflight. Confirm that M3 is explicitly authorized and all source/engine/storage decisions still apply. Verify source/config/code hashes and the latest completed batch journal. If any mismatch occurs, do not resume over the old output; preserve it and start a new run ID after review.

After interruption, validate every completed output row and its partial manifest before continuing. A partial dataset remains staging-only and is never a release. Refresh the agent checkpoint only after state/backlog/evidence are consistent; checkpointing does not mark M3 criteria complete.

## Definition of Done

- M3-01 through M3-04 each have an evidence-backed pass result under their canonical acceptance wording, with any unresolved prerequisite honestly marked not passed.
- Source, teacher, schema, sampling, filtering, deduplication, split, resource, and release manifests are reproducible and independently verifiable.
- Every accepted game/position/teacher row can be traced to source/config/code and reconstructed; every rejected/quarantined row has a reason.
- Leakage summary, dataset statistics, SHA-256 manifest, tests, logs, and artifact location are retained.
- Canonical state/backlog reflect only evidence that exists; M3 completion is not inferred from a plan.
- A reviewable M3 implementation PR is pushed against **initial-idea**, remains open/unmerged, and documents limitations and negative results.

