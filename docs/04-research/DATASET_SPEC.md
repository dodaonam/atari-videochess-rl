# M3 Dataset and Provenance Contract

**Status:** Proposed Pre-M3 contract; no source has been approved or ingested.  
**Owner:** Dataset shape, lineage, validation, sampling, and split semantics for M3.  
**Related records:** [REQUIREMENTS.md](../01-foundation/REQUIREMENTS.md) owns O-06; [M03 plan](../../.agents/plans/M03-expert-dataset.md) owns execution order; [decision register](DECISION_REGISTER.md) records owner choices.

## 1. Source recommendation and due diligence

The leading candidate remains the Lichess Elite Database, May 2022 package published at [database.nikonoel.fr](https://database.nikonoel.fr/). The publisher currently describes the collection as standard Lichess games filtered to exclude bullet. It says the filter changed in December 2021 to games rated 2500+ versus 2300+. The listing reports 355,535 games and 93 MB for May 2022. These are publisher-reported values; the archive has not been downloaded, hashed, or sampled here.

The publisher identifies Lichess Open Database exports as its source and says URLs were removed from the PGN Site header before June 2020; from June 2020 it retained URLs under a LichessURL header. It says clock times are omitted to save space. The page does not state a license for this filtered package, a checksum for the May 2022 archive, or the exact remaining header schema. The official Lichess database page separately states that its own database exports are CC0. That statement does not establish the license or reuse terms of the third-party filtered package.

**Recommendation:** Treat the May 2022 package as the research-preferred candidate only if the publisher or another authoritative record confirms reuse terms suitable for the assignment, retained processing, and intended release. Keep O-06 open until the owner approves the source and use. If that confirmation is not obtained, prefer the official rated standard Lichess database exports, filter them locally under the published CC0 terms, and choose a bounded historical month only after measuring its actual size. The current official listing shows recent monthly standard exports around 28–31 GB compressed and says uncompressed data is about 7.1 times larger; those current-month values do not establish the size of a May 2022 export. For a smaller licensed fallback or parser pilot, official Lichess broadcast PGNs are explicitly CC BY-SA 4.0; the official page lists May 2022 as 3.55 MB and 5,695 games. This has a different tournament-centered distribution and share-alike obligations, so it is not a silent substitute for the Elite source.

No archive was downloaded during Pre-M3. The direct archive link was not fetchable through the read-only page inspection used for this audit; this does not establish that the publisher's download is unavailable. No archive integrity value or sample-derived distribution statistic is claimed.

### Facts and unknowns to carry into M3

| Topic | Verified from current source listing | Must be measured from an authorized sample |
|---|---|---|
| Identity | Third-party Lichess Elite Database; May 2022 listing; 355,535 games and 93 MB reported. | Exact archive bytes, hash, member name, file encoding, PGN parseability, game count, and source endpoint response. |
| Filtering | Standard games; bullet excluded; since December 2021, stated threshold is 2500+ versus 2300+. | Whether the ratings refer to both players in every record, edge cases, exact time-control categories, and filter implementation. |
| Metadata | Publisher says clock times are omitted; LichessURL was used for URL retention from June 2020. | Actual headers, missing-value rates, nonstandard tags, annotations, variations, URLs, player identifier exposure, and result/termination coverage. |
| Legal basis | Official Lichess exports state CC0; the third-party filtered page does not state a license. | Written or authoritative confirmation covering this archive and the intended research, derivative records, and redistribution. |
| Availability | Listing and month link are present on the source page. | Stable access, HTTP metadata, checksum availability, archive integrity, and long-term retrieval path. |

The first authorized profile must read a bounded sample, preserve the original archive unchanged, and report counts rather than assuming the listing is exact. Capture the source page and terms URL, retrieval timestamp, HTTP ETag/Last-Modified where available, downloaded-byte count, SHA-256, ZIP member names/sizes/CRC status, and a sample PGN header summary. Do not store account names in a public report.

## 2. Data layers and file formats

Use versioned, streaming JSON Lines for the initial implementation. Each row is UTF-8 JSON with one trailing newline. Gzip may be used for output with the standard library. Keep source PGN immutable and outside Git. Do not add a database service, pandas, or a distributed processing framework for M3.

One dataset release has these independently hashed layers:

1. **Source manifest:** source and rights evidence, retrieval facts, raw file hash/size, archive members, and approving decision ID.
2. **Game records:** validated game headers and the exact standard-chess initial state and main-line UCI sequence.
3. **Position records:** a sampled decision state, its full replay path, board serialization, legal UCI candidates, played move, and game result.
4. **Teacher records, optional:** raw engine outputs and separately versioned transforms. Absence of teacher rows is explicit.
5. **Split manifest:** deterministic seed, split rule, duplicate purge counts, and split hash.
6. **Release manifest:** schema versions, source/config/code hashes, row counts, rejection counts, output file sizes and SHA-256 hashes, and validation summary.

Never combine teacher annotations into the expert game row or overwrite played-move labels with engine-preferred moves.

## 3. Versioned row contracts

The initial contract label is videochess-dataset/1.0. A schema change that alters meaning increments the major version; additive optional fields increment the minor version. All record types include schema_version and deterministic record_id.

### Source manifest

Required fields: schema_version; source_id; canonical_source_url; publisher; original_data_provenance; license_name; license_url; rights_evidence_path; approval_id; retrieved_at_utc; source_page_sha256; archive_filename; archive_bytes; archive_sha256; HTTP metadata when available; archive_member; member_bytes; member_crc; parser_name/version; filter_config_sha256; code_revision; and source_notes. Unknown values are null with an explicit reason, never inferred.

### Game record

| Field | Type / requiredness | Contract |
|---|---|---|
| schema_version | string, required | videochess-game/1.0 |
| game_id | 64-hex string, required, unique | SHA-256 of the source-stable identity; prefer a public source game ID/URL, otherwise hash normalized standard-chess headers plus initial FEN and main-line UCI. |
| source_id | string, required | Key into the source manifest. |
| source_member / source_game_ordinal | string / integer, required | Exact member and 1-based parser ordinal for audit; not the identity by itself. |
| event_date / event / round | nullable string | Preserve raw PGN value and a normalized date separately if parsed. |
| white_rating / black_rating | nullable integer | Raw PGN rating values; do not imply a rating system beyond source metadata. |
| white_player_ref / black_player_ref | nullable string | By default omit display names; store a source-stable opaque reference only if needed and permitted. |
| time_control / termination | nullable string | Preserve raw values; missing stays null. |
| variant | string, required | normalized standard; explicit nonstandard variants are rejected from this dataset. |
| initial_fen | string, required | Canonical FEN used to reconstruct the initial Board. Standard start is required for the first M3 release unless a separate approved policy says otherwise. |
| result | enum, required | 1-0, 0-1, or 1/2-1/2; preserve raw result separately if invalid. |
| moves_uci | array[string], required | Main-line moves in order, with promotion choice; no list index is a persistent action ID. |
| ply_count | integer, required | Must equal the length of moves_uci. |
| validation_status / diagnostics | enum / array, required | accepted or quarantined, with stable reason codes. |
| normalized_game_sha256 | 64-hex string, required | Hash of variant, initial state, and full UCI main line, independent of display names and event metadata. |

### Position record

| Field | Type / requiredness | Contract |
|---|---|---|
| schema_version / position_id | string / 64-hex, required | videochess-position/1.0; deterministic hash of game_id and ply_index. |
| game_id / source_id / split_id | required strings | Foreign keys to the game and release/split manifests. |
| ply_index | nonnegative integer, required | Number of moves already applied; zero-based decision boundary. |
| initial_fen / history_uci | string / array[string], required | Replay from this initial FEN to reconstruct rules state and repetition history. |
| fen | string, required | Position serialization with the chosen python-chess FEN convention; not a substitute for history_uci. |
| side_to_move | white or black, required | Absolute board color at the decision. |
| legal_moves_uci | sorted array[string], required | Complete legal set at extraction time; unique and independently recomputed by python-chess in validation. |
| played_move_uci | string, required | The expert's observed main-line move and a member of legal_moves_uci. |
| result_white | enum, required | Original game result in White's perspective. |
| result_to_move | -1, 0, or +1, required | Final result from side_to_move's perspective; not an engine evaluation or RL return. |
| position_fingerprint | 64-hex string, required | Hash of placement, active color, castling rights, and en-passant square for transposition/leakage audits. Keep halfmove/fullmove counters in FEN and report clock-context overlap separately. |
| sampling_id / sampling_config_sha256 | required strings | Identifies deterministic game/ply sampling rule. |

Candidate labels are keyed by UCI string, not an array ordinal. Sorting legal_moves_uci is for stable serialization only; it does not establish a fixed model output head.

### Teacher and target records

Teacher rows use a distinct schema and include teacher_run_id, teacher_config_sha256, position_id, raw UCI MultiPV line, first_move_uci, raw score type and value, score perspective, depth/nodes, engine build/version/hash, and optional transformed_target with transform_id and parameters. Keep centipawn, mate, and WDL outputs as separate typed values. Do not serialize a mate result as an arbitrary large centipawn integer.

An engine score must name whose perspective it uses. If a White-perspective score is converted to side-to-move perspective, store both raw score and conversion field. A transformed scalar is not a raw engine result, win probability, discounted return, or learned Q-value.

## 4. Parsing and validation policy

Stream one PGN game at a time. Record every source game as accepted, rejected, or quarantined with a stable reason code and source ordinal. Do not silently skip parser errors.

Required checks:

- source archive/member size and checksum match its manifest; ZIP CRC passes;
- valid PGN parse with a result token matching the replayed main line where the library can establish it;
- standard chess only, with no unsupported variant or unapproved custom initial position;
- legal replay of every move from the recorded initial Board; an illegal move quarantines the whole game with ply and parser diagnostics;
- game is not already terminal before a candidate decision; do not emit positions with an empty legal set;
- every position FEN, side-to-move, legal UCI set, played move, history replay, and result perspective recompute consistently;
- values with missing or malformed ratings/time controls remain available unless a separately approved filter uses those fields;
- aborted, unfinished, unknown-result, and conflicting-header games are quarantined or excluded from supervised result targets, with counts retained;
- preserve raw header strings and separately normalized fields; recognize unknown header names without crashing.

Do not discard unusual games merely because they are short, have unusual results, or lack optional metadata. If an approved training filter excludes them, retain a count and reason and include a sensitivity comparison where feasible. A game that is syntactically parseable but semantically inconsistent is quarantined rather than repaired silently.

## 5. Deterministic sampling and deduplication

Use a seed plus stable source identity for every sample choice. For file-order-independent game caps, retain the games with the lowest SHA-256 ranks over seed and normalized_game_sha256 (bounded bottom-k reservoir). For positions, use deterministic per-game ply selection and record the selected-ply rule. A first pilot should include an unfiltered profile; do not let a rating threshold hide source defects.

Proposed coverage view: report all candidate positions by ply bands such as opening (plies 0–20), middlegame (21–80), and later play (81+), plus side to move, result, rating presence/bands, time control, and legal-move count. These are reporting bins, not removal rules. Later use stratified sampling only after measured distributions exist. Cap positions per game so long games cannot dominate.

Deduplication stages:

1. exact source ID/URL duplicates;
2. normalized full-game duplicates using variant, initial state, and UCI move sequence, independent of player/event headers;
3. repeated canonical position fingerprints across a game, keeping one deterministic occurrence for a position-level objective;
4. cross-game position overlap audit, with split-level purge described below.

If duplicate records disagree on result, variant, or moves, quarantine the conflict for review; do not choose a preferred copy silently. Store raw duplicate counts and retained identities in the release summary.

## 6. Leakage-safe split policy

Assign whole normalized games to train/validation/test using a stable hash of split_seed and normalized_game_sha256, with proposed 80/10/10 proportions. Candidate rows inherit their game's split. Persist the seed, hash rule/version, source manifest hash, and exact assignment counts. Re-running a release with the same immutable source and configuration must reproduce assignments.

Game-level separation alone does not prevent repeated openings, transpositions, or duplicate positions from appearing across partitions. After game assignment, build canonical position fingerprints across all splits and keep each fingerprint in only one split. For each fingerprint, choose the occurrence with the lowest SHA-256 rank over split_seed, fingerprint, normalized_game_sha256, and ply_index; remove all other position rows from the position-level objective. This gives an explicit deterministic owner while retaining whole-game split assignment for every remaining row. Do not move individual candidate actions to another split. Keep game records and full move histories for audit; report purged rows and games by split. Candidate/teacher records remain attached to their position and therefore cannot cross splits independently.

Measure exact normalized-game overlap and canonical-position fingerprint overlap before and after purging. Also report opening-prefix overlap and repeated-position rates by ply band. The policy prevents exact duplicate normalized games and exact canonical board-position overlap in the position tables, including common transpositions represented by the same canonical fingerprint. It does not eliminate near-position similarity, shared opening concepts, shared players, temporal correlation, or leakage through external public chess knowledge. Do not claim absolute leakage elimination.

The holdout is stable only for a frozen source manifest, split-rule version, and seed. A new month or revised source archive is a new dataset version; do not append to an existing split and call it comparable.

## 7. M3 testable invariants

The future M3 suite must include synthetic PGNs for standard and malformed headers, comments/variations, missing ratings/time control, nonstandard variant, custom initial FEN, unfinished result, illegal move, checkmate terminal, duplicate game with changed headers, transposition duplicates, and cross-split overlap. No user names or downloaded third-party game records belong in fixtures.

Tests must verify:

- bounded streaming and explicit max-games/max-positions/max-output-bytes safeguards;
- deterministic game and ply sampling under changed file order;
- replayed history restores automatic repetition context where applicable;
- stable unique UCI action IDs including castling, en passant, and promotion;
- game-level split assignment, candidate inheritance, deterministic duplicate-position purge, and leakage statistics;
- White/Black result perspective conversion;
- teacher raw score, mate, MultiPV, and transform fields do not collapse into one unlabeled scalar;
- interruption/resume validates source/config hashes and does not duplicate rows;
- output manifests match every completed data file and every failure is represented in quarantine/report counts.

