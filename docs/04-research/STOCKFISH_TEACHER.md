# Stockfish Teacher and Supervised Targets

**Status:** The owner authorized bounded Stockfish 19 teacher labeling for M3 on 2026-10-20. A real run on 128 deterministic positions completed on 2026-10-20 using the existing verified host binary; all positions produced records, including 377 centipawn and 3 mate MultiPV lines. The broader O-01/O-07 instructor and non-teacher role questions remain open. The manifest and sanitized execution evidence are under `.agents/evidence/`.
**Related records:** [M03 plan](../../.agents/plans/M03-expert-dataset.md), [dataset contract](DATASET_SPEC.md), [experiment protocol](EXPERIMENT_PROTOCOL.md), and [owner decision register](DECISION_REGISTER.md).

## 1. Keep target meanings separate

| Signal | What it records | Perspective / limitation |
|---|---|---|
| Played PGN move | The action a player chose in that recorded game. | Behavior evidence, not proof that the move is optimal. |
| Game result | Final win/draw/loss for a named color or the side to move. | Noisy delayed outcome affected by both players and the rest of the game. |
| Stockfish MultiPV move | One of the engine's top principal variations for a root position under one search configuration. | A bounded engine search result; it does not score every legal move. |
| Stockfish position score | Engine evaluation of a root position with explicit score perspective, depth/nodes, and engine identity. | Not a calibrated probability, discounted return, or learned Q-value. |
| Normalized supervised target | A named deterministic transformation of a raw label. | Must retain transform ID, parameters, and source raw value. |
| Simulator reward / return | Reward and discounted future reward from simulator transitions. | M5 RL evidence; do not substitute engine centipawns. |
| Learned Q-value | Model estimate for a legal action and simulator return under a stated policy/training setup. | M5/M6 model output; not a teacher score by definition. |

## 2. Optional M4 target recommendation

**RL-first priority:** the project must reserve its principal time and compute for independently implemented Double DQN trained from M2 simulator transitions. A small behavior-cloning model is an optional supervised-only baseline if it can be built without delaying the core M5 implementation or learning experiment. It is not a prerequisite to M5, the primary project result, or evidence of reinforcement learning.

If retained, train on a selected position's actually played UCI move using a policy loss restricted to that position's recorded legal moves. This needs no Stockfish labels. Report held-out legal top-1/top-k move accuracy and ranking metrics as behavior-prediction measures, not Elo, Q-value quality, simulator return, or Atari strength.

Keep game-result prediction as an optional separate auxiliary experiment. Its target is the final result from a stated color/side perspective; it is not an immediate reward or a Q-target. Compare it independently and retain a behavior-only checkpoint.

At least one simpler baseline is legal random selection or a fixed transparent heuristic. A model may also predict result from a position, but must not train on future post-position moves as if they were labels for the current move.

| Objective | Benefit | Main cost or risk | Disposition |
|---|---|---|---|
| Played-move behavior cloning | Lowest data and compute complexity; target exists in each accepted PGN position. | Expert actions are demonstrations, not optimality certificates; game context and time controls affect behavior. | Optional, small, and time-boxed baseline only if it does not delay Double DQN. |
| Position outcome prediction | Uses game result without engine; provides a distinct outcome baseline. | Outcome is noisy and highly dependent on both players and later moves. | Optional multi-task experiment, not merged into move labels. |
| Teacher top-k ranking | Adds engine-preferred candidates and interpretable ranking signal. | MultiPV covers only its returned lines; it is not a label for every legal move. | Bounded M3 teacher labeling is authorized; any expanded ranking experiment is optional and must not delay Double DQN. |
| Every-legal-move candidate scores | Provides broad candidate supervision. | Approximately one restricted-root search per legal move, often dozens of searches per position. | Defer unless a measured pilot and assignment value justify the cost. |
| Value regression from Stockfish | Dense board signal and simple storage. | Score scale, mate discontinuity, search noise, and perspective can be mistaken for probability or RL return. | Store raw data separately; transform only in a named M4 experiment. |

This recommendation does not freeze the neural architecture, legal-action scorer, loss weighting, feature representation, or Double DQN initialization.

Behavior cloning remains a supporting baseline, not the project's academic result. An imitation policy's logits are not Q-values. A future shared encoder/action-conditioned scorer may be initialized from behavior cloning only as a measured transfer experiment; initialize or recalibrate the Q output semantics and compare against a random-initialized Double DQN control where feasible. Teacher evaluations are also not Bellman-consistent Q-values. M5 must be able to train from random initialization; supervised work cannot block that path.

## 3. Existing engine baseline and provenance

The repository's M0 evidence records a manual host prerequisite of Stockfish 19, not a Python dependency. The recorded Linux x86-64 archive SHA-256 is 9defc0d4e55d49c65a6d042f3e571a39fcea499ade6dbe741b53b8c65e03611f; the executable SHA-256 is 0f83d24cc46d2c66c60f16001af5444873bc112b7d028594513426894c12da19. The pinned GPL-3.0 license copy and its digest are documented in [SETUP.md](../05-operations/SETUP.md) and **.agents/evidence/M0-final-technical-verification.md**.

Pre-M3 did not install, upgrade, or run a search with Stockfish. The M3 run used the existing host executable and license copy, rechecking their hashes. It used one thread, Hash 64 MiB, MultiPV 3, one UCI node cap of 5,000 shared across the returned lines and a 30-second UCI movetime cap per root. A separate process watchdog enforced the cap plus a recorded two-second maximum grace. The root score is stored from side-to-move perspective with a separate White conversion. Centipawns use `tanh(cp / 400.0)` rounded to eight decimals; signed mate distance remains typed and has no scalar normalization. The exact engine identity, effective options, per-position limits, sample identity, and hashes are in [the M3 teacher manifest](../../.agents/evidence/M3-teacher-manifest-r2-20261020.json). The historic M0 hash alone is not proof that another host has the same executable.

Do not copy the GPL engine binary into Git, a dataset release, or a model package. Keep its license with the host binary. The inference path must remain engine-free.

## 4. Proposed teacher run contract

Every teacher run has an immutable config and run ID. Record:

- engine name, UCI name/author, version/release, operating system and CPU architecture;
- binary relative provenance, binary SHA-256, release/archive checksum, license identifier and retained license-text hash;
- UCI handshake transcript with paths and environment details sanitized;
- Threads, Hash MiB, MultiPV, Chess960 setting, tablebase setting, and any other non-default UCI option;
- search limits and values, including the node cap and a per-root `movetime` cap; also record the separate process watchdog/grace;
- root board FEN, side to move, history replay hash, candidate list, and root-move restriction if used;
- raw best-move/PV UCI strings, score type, raw value, engine-reported perspective, depth, seldepth, nodes, and elapsed time;
- teacher configuration hash, code revision, dataset/source hash, per-position status, and failure reason.

Use one engine thread for the first pilot and a fixed, bounded hash allocation. The M3 runner applies both a node cap and a per-root `movetime` cap. The per-root search cap is the smaller of the configured cap and the remaining total budget after reserving 2 seconds for final manifest/checksum publication and file-inventory/hash closure, plus a 50 ms response/cleanup margin. The external process watchdog uses that actual cap plus `min(2 seconds, 10% of the cap, remaining total budget after the cap and finalization reserve)`; it never uses the original configured timeout after a smaller cap has been selected. python-chess's protocol timeout is separately recorded 250 ms after that process-kill deadline so process termination and timeout cancellation do not race. The monotonic total command budget starts before release verification and sample selection and covers UCI startup/options, hash clearing, searches, engine shutdown, sidecar writing, semantic verification, and finalized-file checks. Engine blocking calls have watchdogs; bounded local file phases are checked on completion and any overrun is marked partial. Process kill/reap can add at most two seconds of cleanup tolerance. The manifest's elapsed measurement ends after semantic verification and before its final publication; it records the fixed reserve and conservative return-time upper bound. The runner measures elapsed again after manifest/checksum and result-file closure. If that observation crosses the budget or leaves less than the 50 ms margin, the run is finalized as `partial` (with `overrun` or `finalization_reserve_exhausted` as applicable), never as an in-budget complete success. Each row and manifest retains the applied limits and statuses. A node limit does not promise bit-for-bit identical results across engine builds, CPU instruction sets, transposition-table state, or library versions. Clear the hash between root positions unless a documented experiment deliberately carries search state between positions.

The runner fully verifies the dataset release once before selecting samples. Its in-run teacher-sidecar semantic verification then rechecks the verified release manifest and output hashes, and validates the teacher rows, legal PVs, score perspectives, and transforms before finalizing `command_elapsed_seconds`. Final manifest publication uses a bounded checksum, result-hash, and file-inventory closure check. A separate `videochess-data verify --release ... --teacher-run ...` invocation performs an independent full verification after the teacher command; that follow-up audit is recorded separately from the teacher command wall time.

Teacher CLI engine-path resolution is deterministic: an absolute path is used explicitly; a relative path with a directory component is rooted at the repository and may not escape it; a bare executable name is resolved only from `PATH` and must identify exactly one executable. SHA-256 and executable checks still apply after resolution. There is no developer-machine path fallback. Timeout inputs are stored and applied at millisecond precision; values that round below one millisecond are rejected.

The teacher CLI uses automation-safe exit codes: a verified `complete` manifest returns 0, a verified `partial` manifest returns 3, and a fatal run error returns 2. Partial rows and their manifest remain available for diagnosis; callers must not treat a nonzero partial status as a completed labeling job. A partial manifest is never rewritten as complete.

Initial candidate protocol proposal, not a measured run setting: one thread, Hash at most 256 MiB, MultiPV at most 3, and a starting cap of 50,000 nodes per root in the tiny timing pilot. The M3 mission authorizes a bounded run below these ceilings; select actual limits from measured throughput and record them in run evidence. Any expanded role or label campaign needs separate review and must protect the Double DQN schedule.

### M3 completion pathway (mandatory acceptance alignment)

M3 has two technically distinct stages and one formal acceptance condition:

1. **PGN data engineering:** once M3, source, and applicable storage permissions are explicitly authorized, profile and process a bounded approved source, create game/position records, validate lineage, and produce leakage statistics. This can create a valid intermediate PGN-only artifact.
2. **Teacher interface and contract tests:** typed score records and fake-UCI tests verify parser behavior, perspective conversion, MultiPV rank, mate typing, failure paths, and config serialization. These tests do not establish an engine version or actual search setting.
3. **Authorized bounded real teacher run:** the historical r2 run analyzed 128 deterministic positions for its historical release. Corrective hardening creates a separately identified teacher run for the corrected release; its actual counts and hashes are reported in the corrective M3 evidence. The teacher sidecar remains separate from PGN behavior/result rows. Future expanded label coverage is optional and must not delay Double DQN.

The real-run evidence satisfies the technical evidence listed by unchanged canonical [M3-02](../06-quality/ACCEPTANCE_CRITERIA.md); independent PM review remains required before the milestone can be accepted. If an authoritative assignment rule contradicts the owner-scoped project permission, stop any affected future operation and follow that rule. The default reference remains the recorded Stockfish 19 host build; no upgrade is proposed. Stockfish remains excluded from learned-agent inference in every path.

### Score conventions

- Preserve raw engine centipawns as an integer when present, and record the root side whose perspective was requested from the engine API.
- Preserve mate distance as a separate signed integer with perspective; do not replace it with an arbitrary large centipawn score.
- WDL is optional. When Stockfish returns it, schema `videochess-teacher/1.1` stores both side-to-move and White perspectives as integer `wins`, `draws`, and `losses` per-mille counts in 0–1000 whose sum is exactly 1000, with perspective, scale (`permille-total-1000/v1`), and source method (`UCI_ShowWDL`). Validate the White values by inverting wins/losses when Black is to move. Missing WDL remains valid; malformed or semantically inconsistent WDL is rejected. Legacy teacher schema 1.0 remains verifiable under its original optional-field contract. Do not infer WDL from centipawns without a named model.
- A normalized field is optional and carries a transform ID, exact formula/parameters, input type, perspective, and code version. Keep it beside, not instead of, the raw score.
- Store a MultiPV row for each returned line with its rank and first UCI move. A PV can be longer than the root move; only the first move is the candidate.
- Store missing, illegal, failed, or aborted analyses with explicit status. Never impute a teacher score silently.
- Terminal positions have no legal candidate to search; record terminal status and outcome separately.

Teacher schema 1.1 also requires contiguous unique MultiPV ranks beginning at 1, unique root moves across returned lines, legal candidate identities, and legal full PVs. This checks the returned alternatives without assuming that MultiPV covers every legal move. Schema 1.0 sidecars remain readable under their original manifest/row identity versions; verifiers do not reinterpret their old run IDs as 1.1 identities. The historical 1.0 manifest contract did not require a run-level `status`; outcome counts and per-position statuses remain authoritative for those records. New 1.1 manifests require explicit final `complete`/`partial` status and wall-budget evidence.

## 5. MultiPV versus exhaustive candidate scoring

One search with MultiPV=k returns at most the engine's top k principal variations under that search. It is not an exhaustive independent evaluation of all legal moves, and returned lines can vary with search configuration. If the played move is not returned, it has no teacher rank in that run.

To score every legal candidate, restrict root moves and analyze each candidate under a defined protocol, or use another validated method. If a position has L legal moves, full candidate labeling requires up to L candidate-restricted analyses per position. By contrast, one MultiPV search gives a bounded top-k list in one analysis invocation, with search time often higher than a single-PV run. Measure actual wall time and node counts on a small authorized sample; do not extrapolate from archive size alone.

Recommended staged use after authorization:

1. record played move and outcome only for the full chosen dataset;
2. analyze a capped, deterministic subset of positions with MultiPV=3;
3. report the fraction of played moves found in top-k, engine failures, nodes, and timing;
4. compare behavior-only against teacher-assisted training separately;
5. consider every-legal-candidate scoring only if M4 evaluation shows a specific need.

## 6. Resource model and stop conditions

Let G be accepted games, p the observed average plies per game, f the sampled-position fraction, cᵢ the legal candidate count at position i, and tₚ₉₅ the measured 95th-percentile wall time for the selected teacher query. Then:

- sampled positions: N = G × p × f;
- top-k teacher analyses: at most N analysis requests;
- every-candidate analyses: Σ cᵢ requests, approximately N × average(cᵢ);
- projected teacher wall hours: requests × tₚ₉₅ / 3600 / concurrent workers, as a rough estimate only;
- projected teacher CPU hours: requests × measured CPU-seconds per query / 3600; do not infer CPU time by dividing wall time by thread count;
- working disk: archive bytes + extracted/stream buffer + output rows + teacher rows + manifest/log reserve.

For scale illustration only, the publisher reports 355,535 games. If an unverified planning assumption of 80 plies per game were used, processing every ply would create about 28.4 million positions. If an illustrative, unmeasured average of 30 legal candidates were then exhaustively scored, that would be about 851 million candidate analyses. These assumptions are not source statistics or throughput claims; M3 must measure actual game lengths, candidate counts, and engine timing before projection.

Planning tiers only; they grant no execution authority:

| Tier | Input/game ceiling | Position ceiling | Teacher ceiling | Resource guard |
|---|---:|---:|---:|---|
| Minimal pilot | 200 games | 10,000 rows | 1,000 positions, MultiPV up to 3 | Elite-candidate archive ceiling 150 MiB; one process/thread; RSS 1 GiB; Hash up to 128 MiB; 2 GiB output cap. |
| Medium validation | 10,000 games | 250,000 rows | 25,000 positions | Elite-candidate archive ceiling 150 MiB; one process/thread; RSS 2 GiB; Hash up to 256 MiB; 5 GiB output cap. |
| Larger authorized run | At most source-reported 355,535 games | 2,000,000 rows by default | 100,000 positions by default | Elite-candidate archive ceiling 150 MiB; one engine worker unless separately approved; RSS 4 GiB; Hash up to 256 MiB; 20 GiB output cap. Any higher cap needs a new measured budget. |

The archive ceiling applies only to the publisher-reported 93 MB Elite candidate. Choosing an official monthly rated export, whose current-month files are about 28–31 GB compressed, requires a new source-specific download and storage budget; these tiers do not authorize or bound that source. Actual compressed/extracted size, record size, CPU throughput, and output size remain unknown until a permitted pilot. Stop before processing if a configured game/position/teacher/output cap is reached, source/config hashes differ on resume, available disk is below the projected peak plus a 20% reserve, memory exceeds the configured cap, engine identity differs, errors exceed a configured threshold, or elapsed CPU time reaches the approved budget. Checkpoint only at completed game/position batches and never present a partial dataset as a release.

## 7. Dependency and authority boundary

The current project already locks python-chess. PGN parsing, ZIP access, JSON Lines, gzip, SHA-256, and manifests can use the existing package and Python standard library. Do not add a data-frame/database dependency for M3. If the approved source is a Zstandard stream, decide separately whether to add a pinned Zstandard Python package or require a documented host utility; do not hide that dependency.

The project owner’s 2026-10-20 mission authorizes this M3 task's bounded Stockfish 19 offline teacher labels. The older proposed authority boundary above is superseded only for that exact scope. Stockfish remains excluded from inference, opponent, and offline benchmark roles. O-01/O-07 retain broader instructor and role questions; if authoritative course rules contradict this scoped project direction, stop the affected operation and record the evidence.

The corrective M3 run on 2026-10-21 analyzed 128 deterministic positions from corrected release `7b51ec3761ad28aa7a2882691b3c314d35115ab339769251ff2556e706a5b1d9`, at 5,000 nodes/root, MultiPV 3, one thread, 64 MiB hash, and a 1,800-second total command budget. It produced 377 centipawn and 3 typed mate rows with no failures or unattempted positions. The full command, including release validation and sample selection, took 114.243 seconds; engine search time was 2.985 seconds. Binary, license, release, run, sidecar, score, and independent verification identities are in [the corrective hardening evidence](../../.agents/evidence/M3-corrective-hardening-20261021.md). The earlier M3 teacher record is historical and remains linked to its original release.

