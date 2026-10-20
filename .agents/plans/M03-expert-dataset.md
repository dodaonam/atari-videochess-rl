# M03 — Expert Dataset Plan

- **Plan ID:** M03
- **Milestone:** M3 — Expert dataset, within the engineering sequence owned by **EXECUTION_PLAN.md**
- **Plan status:** in progress under direct owner authorization recorded in the M3-001 authorization evidence
- **Canonical task:** M3-001 in **BACKLOG.yaml**, in progress under direct owner authorization
- **Dependencies:** M2-001 complete and G2 approved; retain G3 unapproved until its closure review. G3 covers M2–M5 and is not a prerequisite to start M3.
- **Acceptance:** M3-01 through M3-04 in **docs/06-quality/ACCEPTANCE_CRITERIA.md**
- **Requirements:** B-04, B-05, B-07; see scoped owner decisions in REQUIREMENTS.md and DECISION_REGISTER.md
- **Relevant decision:** accepted **ADR-0002** for stable UCI action identity, Board history, and color perspective; it does not approve data, Stockfish, or neural architecture
- **Contracts:** [DATASET_SPEC.md](../../docs/04-research/DATASET_SPEC.md), [STOCKFISH_TEACHER.md](../../docs/04-research/STOCKFISH_TEACHER.md), [EXPERIMENT_PROTOCOL.md](../../docs/04-research/EXPERIMENT_PROTOCOL.md), [RL_FIRST_ALIGNMENT.md](../../docs/04-research/RL_FIRST_ALIGNMENT.md), [REPRODUCIBILITY.md](../../docs/05-operations/REPRODUCIBILITY.md)

## Objective

Create the smallest reproducible, provenance-preserving, leakage-audited expert artifact that supports the later RL experiment. Keep expert played moves, game outcomes, and Stockfish annotations as distinct signals. Dataset size and teacher coverage must be justified by M4/M5 value and hard resource caps; maximizing data volume is not an objective. M3 does not train a model, claim playing strength, change the M2 simulator, run reinforcement learning, or evaluate ALE gameplay. The central course deliverable remains independently implemented Double DQN in M5; see [RL-First Alignment](../../docs/04-research/RL_FIRST_ALIGNMENT.md).

## Authorization gates and source prerequisites

Before any source retrieval or processing:

1. Direct M3-001 authorization is recorded in the task evidence and project state. G3 approval is not a start prerequisite and remains unapproved.
2. The owner approved bounded local/internal use of the exact source; the decision and third-party rights uncertainty are recorded before retrieval. No redistribution is authorized.
3. The owner confirmed bounded Stockfish 19 offline teacher use for this project. This does not authorize engine inference, an engine opponent, or offline benchmark evaluation. PGN-only output is an intermediate and cannot pass M3-02.
4. This mission uses local CPU/storage only. Colab, cloud storage, and paid compute remain unauthorized and are not needed.
5. A bounded source profile must confirm actual archive/member sizes and header behavior before full processing. Publisher counts/sizes are not local measurements.

The owner selected and authorized bounded internal academic use of the May 2022 Lichess Elite package. The source/use decision and rights limitation are recorded in .agents/evidence/M3-source-decision-20261020.md. The publisher listing reports 355,535 games and 93 MB but states no package license; official Lichess CC0 terms apply to official exports and do not establish terms for this third-party package. Keep the archive and bulk derived records local and do not redistribute them. Stop if an explicit conflicting restriction is found.

## Scope

- immutable source/archive manifest and permitted local retention;
- streaming PGN parsing, validation, and reason-coded quarantine;
- game-level records and deterministic position extraction/sampling;
- legal UCI candidate sets and played-move/result labels with explicit perspective;
- normalized-game grouped, deterministic splits plus explicit board-overlap ownership/purge, history-state distinction, holdout-retention gates, and candidate inheritance;
- a separately authorized, bounded, versioned Stockfish teacher run required by current M3-02 acceptance; teacher rows remain a sidecar and may be omitted from a particular PGN dataset release;
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
| **contracts.py** | Versioned source/game/position/teacher/split/release validation and canonical domain-separated IDs, including separate board, history, game, and sample identities. | No training/model dependency. |
| **source.py** | Source manifest, archive/member/path/symlink/ratio/decompressed-size checks, streaming SHA-256, ZIP CRC, and bounded input validation. | Never decides source rights; requires recorded source approval. Never extracts arbitrary member paths. |
| **pgn.py** | One-game-at-a-time parsing, raw/normalized headers, UCI replay, structured diagnostics. | Uses python-chess Board/history; never repairs illegal moves silently. |
| **sampling.py** | Deterministic source-order-independent game bottom-k and bounded per-game ply sampling. | Seed/config are required and recorded. |
| **dedup.py** | Source ID, normalized game sequence, conflict/quarantine counts, and separate board-overlap/replay-state reports. | Does not silently collapse history-distinct states or conflicting results. |
| **split.py** | Stable normalized-game hash assignment; explicit board-signature owner, purge ledger, and holdout retention/distribution checks. | Candidate/teacher rows inherit sample split; board overlap is not rules-state identity. |
| **teacher.py** | Stockfish 19 UCI identity and separately authorized bounded search; typed raw score/MultiPV capture, transform provenance, and failure records. | Separate process; never part of inference. Fake UCI tests do not satisfy M3-02. |
| **export.py** | Reference-based game/position JSON Lines, atomic batch segments/staging, row counts, hashes, and verified immutable release manifest. | No data-frame/database requirement; history is stored once per game, not copied into each position. |
| **stats.py** | Quality, label, coverage, split, and resource summaries. | Reports measured values only. |
| **cli.py** | Profile, validate, build, and optionally label subcommands with explicit caps. | No implicit unbounded or online-download mode. |

Use standard library file/JSON/ZIP/gzip/hash/statistics interfaces and the already locked python-chess dependency. If an approved source is Zstandard-compressed, make a separate dependency decision and pin any new package. Do not quietly assume a host decompressor is installed.

## Configuration and command interface

Store human-readable TOML configuration under **configs/data/** and hash its canonical normalized content. Separate source, parsing/filter, sampling, split, teacher, and resource settings. Configuration must include schema versions, deterministic seed, source archive/member hash, start-position and variant policy, minimum/maximum plies where approved, max games, max positions, max teacher positions, max archive/member/output bytes, max per-game/header/comment bytes, max elapsed time, max worker count, memory/hash limits, and output directory.

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
6. Generate game rows and deterministic bounded position samples. Store initial FEN and full UCI move sequence once per game; each position references `game_id` plus `ply_index`, current FEN, `history_state_id`, legal UCI moves, played UCI move, and White/side-to-move result. This stage may produce a validated PGN-only intermediate, not a completed M3 release.
7. Deduplicate normalized game sequences while retaining source aliases. Assign normalized-game groups using the versioned hash rule. Choose a board-signature owner only among partitions where it occurs; purge other partition rows and every candidate/teacher record attached to them without moving groups, retain an audit ledger, report coverage distortion, and fail/warn on configured holdout thresholds.
8. Validate the PGN-only intermediate before teacher analysis. Then, only with O-01/O-07 and explicit bounded-run authorization, run deterministic limited Stockfish 19 analysis. Record actual binary/license hashes/UCI identity/options, node limit, MultiPV, root perspective, raw cp/mate/WDL types, normalization, elapsed time, and per-position errors. MultiPV is not exhaustive. This real run is required for canonical M3-02; fake-engine tests do not pass the criterion.
9. Read the approved PGN member directly as a bounded stream. Reject path traversal, absolute/backslash/symlink/duplicate members, encrypted data, corrupt CRC, unsupported encoding, configured compressed/decompressed/member/game/ratio excesses, and output collisions. Never extract arbitrary archive paths. Apply per-tier compressed/decompressed ceilings, a per-member ceiling, a proposed 200:1 early compression-ratio stop, fixed-chunk streaming byte enforcement, single-game/comment bounds, disk reserve, and OS-enforced memory limits. These initial ceilings are proposals and must be confirmed against a permitted source profile before acquisition.
10. Write atomic run-specific batch segments and a monotonic journal. Resume only when source/member/schema/config/code/parser identities and every committed segment hash match; reject gaps, overlaps, and duplicate sample IDs. A mismatch preserves the staging artifact and requires a new run ID.
11. Validate foreign keys, legal candidates, replay-state IDs, split/holdout invariants, counts, and hashes. Atomically finalize on the same filesystem to a previously nonexistent release path. Interrupted or PGN-only runs remain staging/intermediate and are not reported as completed M3.

## Resource safeguards

Use the proposed M03 tiers in **STOCKFISH_TEACHER.md** as planning ceilings only. Before execution measure a small approved sample for compressed/uncompressed bytes, average bytes per game/position/teacher record, parse throughput, legal candidates per position, and teacher p50/p95 nodes and wall time. Then compute projected CPU-hours and peak storage from the formulas in that contract.

Require explicit max-games, max-positions, max-teacher-positions, max-output-bytes, max-wall-time, max-workers, and memory/hash limits. Check free disk against the estimated peak plus 20% reserve. Default teacher workers to one. Stop on mismatched hashes, source change, corrupt archive, resource-cap exhaustion, repeated parser/engine failures over configured thresholds, unexpected variant rate, or any unapproved use. Record the stop reason and keep staging clearly marked incomplete.

## M3 test and acceptance mapping

| Criterion | Modules / tests | Required evidence |
|---|---|---|
| **M3-01** — Source data and licenses are documented before ingestion. | Source-manifest schema validation; tests reject build without source approval/rights evidence and reject hash/size mismatch. | Approved source decision, terms/provenance snapshot, retrieval manifest, actual archive/member SHA-256 and size before parsing. |
| **M3-02** — Stockfish version, search settings, score perspective, normalization, and mate handling are recorded. | Teacher config/UCI tests plus an authorized bounded real Stockfish 19 run on a deterministic subset. Fake-engine tests cover parser/transform/failure semantics but cannot pass M3-02 alone. | Actual binary/license hash, UCI identification, effective options, search limit, raw cp/mate/WDL values, perspective/transform metadata, run/sample/config hashes, per-position statuses, and sanitized log. Without an authorized real run, M3-02 remains pending and M3 is not complete. If restrictions prohibit the run, a formal canonical acceptance-scope change is required. |
| **M3-03** — Generation is reproducible and every sample has provenance. | PGN parser, stable IDs, sampling, resume, output exporter, per-row provenance and hash tests. | Source/code/config revision, command, seeds, counts, diagnostics, data manifests/hashes, resumed-run check, and sanitized log. |
| **M3-04** — Splits prevent leakage between related positions/candidates; statistics and hashes are recorded. | Normalized-game grouping, candidate/teacher inheritance, board-signature owner/purge, history-state identity, transposition/opening/clock/repetition/castling/en-passant cases, and holdout-collapse failure test. | Frozen seed/config hash, game and board overlap before/after, history-state counts, owner/purge ledger, per-split pre/post counts and distribution shifts, holdout minimum/retention results, and file hashes. |

Synthetic deterministic identity and split vectors are in `tests/fixtures/pre_m3_identity_vectors.json` and `tests/test_pre_m3_contracts.py`; they are contract checks, not a production pipeline. PGN parser fixtures must be tiny, authored for tests, and contain no downloaded public records/player identities. Fake UCI tests verify semantics only. The real bounded teacher run required by M3-02 is separate and may occur only after permission.

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

