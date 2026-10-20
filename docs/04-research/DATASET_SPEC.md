# M3 Dataset and Provenance Contract

**Status:** M3 implementation contract. The May 2022 Lichess Elite source was selected and bounded internal use authorized on 2026-10-20. The archive was retrieved and hash-verified, and a 355,535-game source scan produced a reproducible 1,000-game / 20,000-requested-position training-support release on 2026-10-20. Portable source, release, and teacher manifests are under `.agents/evidence/`; bulk archive and records remain in ignored local artifact storage. The third-party package license remains unstated/unverified.
**Owner:** Dataset shape, lineage, validation, sampling, and split semantics for M3.
**Related records:** [REQUIREMENTS.md](../01-foundation/REQUIREMENTS.md) owns O-06; [M03 plan](../../.agents/plans/M03-expert-dataset.md) owns execution order; [decision register](DECISION_REGISTER.md) records owner choices.

## 1. Source recommendation and due diligence

The selected M3 source is the Lichess Elite Database, May 2022 package published at [database.nikonoel.fr](https://database.nikonoel.fr/), under the scoped owner decision in [M3-source-decision-20261020.md](../../.agents/evidence/M3-source-decision-20261020.md). The publisher describes the collection as standard Lichess games filtered to exclude bullet. It says the filter changed in December 2021 to games rated 2500+ versus 2300+. The listing reports 355,535 games and 93 MB for May 2022. These are publisher-reported values, not local archive measurements.

The publisher identifies Lichess Open Database exports as its source and says URLs were removed from the PGN Site header before June 2020; from June 2020 it retained URLs under a LichessURL header. It says clock times are omitted to save space. The page does not state a license for this filtered package, a checksum for the May 2022 archive, or the exact remaining header schema. The official Lichess database page separately states that its own database exports are CC0. That statement does not establish the license or reuse terms of the third-party filtered package.

The publisher page and official terms page were fetched again on 2026-10-20; the observed facts and page-body hashes are captured in [M3-source-terms-20261020.md](../../.agents/evidence/M3-source-terms-20261020.md). The publisher page does not state a license for this filtered package or provide a checksum. The official Lichess page states CC0 for official Lichess database exports only. That statement does not establish terms for the third-party Elite package. Publisher-reported counts and sizes are not locally verified archive measurements.

The official rated-standard fallback is published as monthly `.pgn.zst` archives; its May 2022 listing includes a downloadable SHA-256 checksum list and reports the archive as 28.8 GB / 89,300,578 games. The official page says uncompressed exports are about 7.1 times larger and notes that about 6% of games include embedded Stockfish evaluation comments, always from White's point of view, without a uniform engine/search contract for those annotations. This is a legally clearer but operationally much larger source, and its embedded evaluations must not be silently treated as labels from the proposed Stockfish 19 teacher run. Profile annotations and clocks separately; ignore them as targets unless the PM/instructor explicitly approves a distinct source-annotation study.

**Decision and boundary:** The owner authorized bounded internal academic research and local derived-dataset generation from this exact package despite its unstated third-party license. This is project-scope authorization, not a public-rights grant or legal determination. Keep the archive and bulk derived records in ignored local storage; do not upload or redistribute them. Preserve remaining license uncertainty and stop if an explicit conflicting restriction is found. Official Lichess rated-standard and broadcast exports are not substitute sources under this decision.

At M3 initiation, no archive had been downloaded. The bounded retrieval completed after the source decision was recorded. Actual archive/member measurements and the full source-backed dataset statistics are recorded in [M3 execution evidence](../../.agents/evidence/M3-execution-20261020.md); publisher-reported values remain separately identified.

### Facts and unknowns to carry into M3

| Topic | Verified from current source listing | Must be measured from an authorized sample |
|---|---|---|
| Identity | Third-party Lichess Elite Database; May 2022 listing; 355,535 games and 93 MB reported. | Exact archive bytes, hash, member name, file encoding, PGN parseability, game count, and source endpoint response. |
| Filtering | Standard games; bullet excluded; since December 2021, stated threshold is 2500+ versus 2300+. | Whether the ratings refer to both players in every record, edge cases, exact time-control categories, and filter implementation. |
| Metadata | Elite publisher says clock times are omitted; LichessURL was used for URL retention from June 2020. Official rated-standard PGNs include standard PGN metadata and may contain clock/evaluation comments. | Actual headers, missing-value rates, nonstandard tags, annotations, variations, URLs, player identifier exposure, and result/termination coverage in the selected source. |
| Legal basis | Official Lichess exports state CC0; the third-party filtered page does not state a license. | Written or authoritative confirmation covering this archive and the intended research, derivative records, and redistribution. |
| Availability | Listing and month link are present on the source page. | Stable access, HTTP metadata, checksum availability, archive integrity, and long-term retrieval path. |

The first authorized profile must read a bounded sample, preserve the original archive unchanged, and report counts rather than assuming the listing is exact. Capture the source page and terms URL, retrieval timestamp, HTTP ETag/Last-Modified where available, downloaded-byte count, SHA-256, ZIP member names/sizes/CRC status, and a sample PGN header summary. Do not store account names in a public report.

## 2. Data layers and file formats

Use versioned, streaming JSON Lines for the initial implementation. Each row is UTF-8 JSON with one trailing newline. Gzip may be used for output with the standard library. Keep source PGN immutable and outside Git. Do not add a database service, pandas, or a distributed processing framework for M3.

One dataset release has these independently hashed layers:

1. **Source manifest:** source and rights evidence, retrieval facts, raw file hash/size, archive members, and approving decision ID.
2. **Game records:** validated game headers and the exact standard-chess initial state and main-line UCI sequence.
3. **Position records:** a sampled decision state referencing its immutable game row by `game_id` plus `ply_index`, with current FEN, replay-state identity, board-position signature, legal UCI candidates, played move, and game result. Full move history is stored once on the game row.
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
| game_id | 64-hex string, required, unique within source | Source-game identity hash. Use a source-provided stable game ID/URL when available; otherwise bind a fallback identity to immutable archive SHA-256, member name, normalized game hash, and an occurrence ordinal. Do not use display headers alone. |
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
| normalized_game_sha256 | 64-hex string, required | Hash of standard variant, canonical six-field initial FEN, and full main-line UCI array, independent of headers. Games with different headers but identical normalized content share this value. |

### Position record

| Field | Type / requiredness | Contract |
|---|---|---|
| schema_version / sample_id | string / 64-hex, required | `videochess-position/1.0`; deterministic sample identity from schema version, `source_id`, `game_id`, `normalized_game_sha256`, and zero-based `ply_index`. The normalized hash prevents a source correction under a reused game ID from silently reusing a sample ID. |
| game_id / source_id / split_id | required strings | Foreign keys to the game and release/split manifests. |
| ply_index | nonnegative integer, required | Number of moves already applied; zero-based decision boundary. |
| reconstruction_path | derived from game row + ply, required | Load `initial_fen` and `moves_uci` once from `game_id`, then replay `moves_uci[:ply_index]`. Do not repeat an O(ply) history array in every position row. |
| fen | string, required | Six-field `Board.fen(en_passant="legal")` FEN at this boundary, including halfmove/fullmove counters and only a legally capturable en-passant square. FEN alone does not restore repetition history. |
| history_state_id | 64-hex string, required | Replay-path identity from canonical initial FEN plus the exact UCI prefix through this decision boundary; it is a conservative reconstruction identity, not a minimal equivalence class of all chess histories. |
| side_to_move | white or black, required | Absolute board color at the decision. |
| legal_moves_uci | sorted array[string], required | Complete legal set at extraction time; unique and independently recomputed by python-chess in validation. |
| played_move_uci | string, required | The expert's observed main-line move and a member of legal_moves_uci. |
| result_white | enum, required | Original game result in White's perspective. |
| result_to_move | -1, 0, or +1, required | Final result from side_to_move's perspective; not an engine evaluation or RL return. |
| board_position_signature | 64-hex string, required | Board-only leakage-audit signature from standard variant, piece placement, side to move, castling rights, and only a legally capturable en-passant square. Excludes halfmove/fullmove counters and repetition history. It is not sample identity or simulator-state identity. |
| sampling_id / sampling_config_sha256 | required strings | Identifies deterministic game/ply sampling rule. |

Candidate labels are keyed by UCI string, not an array ordinal. Sorting legal_moves_uci is for stable serialization only; it does not establish a fixed model output head.

### Optional materialized candidate record

The complete legal candidate set may remain the sorted `legal_moves_uci` array in a position record. If candidates are materialized as rows for training/export, each row uses schema `videochess-candidate/1.0` and includes `candidate_id` (64-hex), `sample_id`, inherited `split_id`, `action_uci`, and `is_played_move`. `candidate_id` is SHA-256 of canonical JSON `{"domain":"videochess-candidate/v1","schema_version":"videochess-candidate/1.0","sample_id":<sample_id>,"action_uci":<lowercase UCI>}`. Each materialized candidate must be legal in its parent position; there is exactly one per legal UCI action, and exactly one marked played for a nonterminal PGN decision. Teacher output remains a separate sidecar keyed by candidate/sample and teacher run. Candidate rows inherit the parent sample's split and are all removed if that parent sample is purged. A reference vector for `synthetic-position-1` / `e2e4` is `48e6e3e68e5344f47c0ec794e5495141489e64858d65bc5c373a993f677021de`.

### Teacher and target records

Teacher rows use a distinct schema and include teacher_run_id, teacher_config_sha256, `sample_id`, raw UCI MultiPV line, first_move_uci, raw score type and value, score perspective, depth/nodes, engine build/version/binary hash/license hash, and optional transformed_target with transform_id and parameters. Keep centipawn, mate, and WDL outputs as separate typed values. Do not serialize a mate result as an arbitrary large centipawn integer.

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

## 5. Deterministic identifiers, sampling, and deduplication

All hashes use SHA-256 over UTF-8 bytes of canonical JSON: object keys sorted lexicographically, compact separators `,` and `:`, `ensure_ascii=false`, no BOM, and no trailing newline. IDs include an explicit ASCII domain string and schema version. Integers are JSON integers; null is JSON `null`; booleans are lowercase JSON; external ID strings are Unicode NFC and otherwise preserve source text. Identity-bearing UCI strings are lowercase standard UCI with promotion suffix. Binary floats are forbidden in identity/config objects: use integer units (for example basis points) or canonical decimal strings. UTC timestamps use RFC 3339 with `Z`; unknown optional fields are explicit null plus a reason outside the identity object. Player names, ratings, event labels, source order, and parser display formatting never enter normalized game or board-position identity.

| Identifier | Canonical input and stability |
|---|---|
| `source_id` | `{"domain":"videochess-source/v1","publisher_key":...,"canonical_source_url":...,"collection_key":...}`. Trim and NFC-normalize these strings; URL/collection values are approved once and URL equivalence is never guessed. Stable across archive revisions; archive hash is separate source-version data. |
| `game_id` | `{"domain":"videochess-source-game/v1","source_id":...,"source_game_ref":...}` using a source-provided stable ID/URL normalized to NFC. If unavailable: `{"domain":"videochess-source-game-fallback/v1","source_id":...,"archive_sha256":...,"member_name":...,"normalized_game_sha256":...,"duplicate_occurrence_ordinal":...}`. This fallback intentionally changes if archive bytes/order change. |
| `normalized_game_sha256` | `{"domain":"videochess-normalized-game/v1","variant":"standard","initial_fen":six_field_canonical_fen,"moves_uci":[...]}`. Canonical FEN is the exact six-field ASCII string returned by `Board.fen(en_passant="legal")`, with one U+0020 between fields and no surrounding whitespace; the standard initial board uses `chess.STARTING_FEN`. Header changes do not change it; a move, initial FEN/counters, variant, or schema-domain change does. |
| `board_position_signature` | `{"domain":"videochess-board-position/v1","variant":"standard","placement":...,"side_to_move":...,"castling":...,"legal_ep":...}` from fields 1–4 of `Board.fen(en_passant="legal")`. Halfmove/fullmove clocks and history are excluded by design. |
| `history_state_id` | `{"domain":"videochess-replay-state/v1","initial_fen":six_field_canonical_fen,"moves_uci_prefix":[...]}`. This is a replay-path key: start from the recorded initial FEN and replay the exact prefix, letting python-chess reconstruct counters and repetition history. Different paths remain distinct even if they reach identical board fields and counters. It is not a minimal equivalence class. If a nonstandard/custom initial FEN is later approved, any repetition history before that FEN is unknowable and the record must declare that limitation; the first release requires the standard initial position. |
| `sample_id` | `{"domain":"videochess-sample/v1","schema_version":"videochess-position/1.0","source_id":...,"game_id":...,"normalized_game_sha256":...,"ply_index":...}`. Stable for the same source game content and decision boundary; changes with source identity, game content, ply, or schema version. |
| `candidate_id` | `{"domain":"videochess-candidate/v1","schema_version":"videochess-candidate/1.0","sample_id":...,"action_uci":...}`. Unique per legal UCI action within a sample; candidate ordering and temporary array positions do not affect identity. |
| `config_sha256` | `{"domain":"videochess-config/v1","schema_version":"videochess-config/1.0","config":<fully-expanded-normalized-object>}` including defaults, caps, seed, schema/split/teacher settings, and parser/library versions. Missing and explicit-default values canonicalize identically after validation. |
| `sample_ids_sha256` | `{"domain":"videochess-sample-set/v1","sample_ids":[...]}` with unique sample IDs sorted lexicographically. This removes input ordering and duplicate references from a teacher job's identity. |
| `teacher_run_id` | `{"domain":"videochess-teacher-run/v1","teacher_schema_version":"videochess-teacher/1.0","dataset_release_id":...,"teacher_config_sha256":...,"engine_sha256":...,"engine_license_sha256":...,"code_revision":...,"sample_ids_sha256":...}`. Raw engine lines and transformed targets remain separate. |
| `split_assignment_sha256` | `{"domain":"videochess-split-manifest/v1","split_seed":...,"game_group_assignments":[[group_sha256,split],...],"board_signature_owners":[[signature,split],...],"purged_sample_partitions":[[sample_id,original_split,owner_split],...]}`. Sort each array lexicographically before hashing; this covers both original game groups and the board-overlap purge ledger. |
| `release_id` | `{"domain":"videochess-release/v1","source_archive_sha256":...,"schema_versions":[...],"config_sha256":...,"code_revision":...,"split_assignment_sha256":...,"outputs":[[path,bytes,sha256],...]}` with schema versions and output tuples sorted. A changed source/config/code/output creates a different release. Record the manifest digest externally to avoid a self-hash cycle. |

Sample identity is neither board signature nor replay-state identity. Source-game identity is distinct from normalized move-sequence identity. A duplicate game with changed headers retains source provenance as an alias/duplicate observation but belongs to the same normalized-game group; a distinct source `game_id` does not make the move sequence independent for splitting. Reference serialization vectors cover source, source-game, normalized-game, sample, config, sample-set, teacher-run, split-manifest, and release hashes in `tests/fixtures/pre_m3_identity_vectors.json`.

For file-order-independent game caps, rank each normalized-game group by SHA-256 of canonical JSON `{"domain":"videochess-game-sample/v1","seed":<integer>,"normalized_game_sha256":<hex>}` and retain the lowest ranks (bounded bottom-k reservoir). Rank a candidate ply by SHA-256 of `{"domain":"videochess-ply-sample/v1","seed":<integer>,"source_id":<id>,"game_id":<id>,"ply_index":<integer>}`; select the lowest configured K per game or a configured fraction against the full 256-bit rank space. Record which method and threshold were used. These keys are independent of source file order; changing source identity, seed, or rule version changes selection. The first pilot profiles an unfiltered sample; do not let a rating threshold hide source defects. Cap positions per game so long games cannot dominate. Ply bands, side/result, rating/time-control availability, and legal-move counts are reporting bins until measured distributions justify stratification.

Deduplication stages:

1. exact source ID/URL duplicates;
2. normalized full-game duplicates using standard variant, canonical initial FEN, and UCI move sequence, independent of headers;
3. exact repeated `sample_id` records;
4. repeated board signatures are measured but not silently collapsed as equivalent rules states. Different `history_state_id` values remain distinct. Any cross-split removal is counted as a board-overlap purge, not identity deduplication.

If duplicate records disagree on result, variant, or moves, quarantine the conflict; do not choose a preferred copy silently. Store raw duplicate counts, aliases, and retained identities in the release summary.

## 6. Leakage-safe split policy

Assign whole `normalized_game_sha256` groups to train/validation/test by hashing canonical JSON `{"domain":"videochess-game-split/v1","split_seed":<integer>,"normalized_game_sha256":<hex>}`. Interpret the first four lowercase hex digits as an integer from 0–65535: `<52429` is train, `<58983` is validation, and the rest is test. All source-game copies with the same normalized move sequence share the group and partition. Candidate and optional teacher rows inherit their `sample_id` partition; never split candidates from one decision state. Do not move a game or individual row to another partition after initial assignment.

After game assignment, find `board_position_signature` values appearing in multiple partitions. Choose an explicit owner among only the partitions in which that signature occurs: hash canonical JSON `{"domain":"videochess-board-owner/v1","split_seed":<integer>,"board_position_signature":<hex>,"candidate_split_name":<name>}` for each present split and select the smallest full digest, using lexical split name as the final tie-breaker. Keep all rows in the owner partition and purge rows with that signature from other partitions, along with every candidate/teacher row attached to those samples. This is a conservative board-overlap purge: board-identical but history-distinct rows are reported as board overlap, not asserted to be the same rules state. Preserve game rows and an audit ledger of purged sample IDs and original partitions. Within one split, keep history-distinct samples; exact duplicate normalized games use one deterministic canonical game plus source aliases.

Report counts before/after purge, per-ply/side/result/rating/time-control/clock/repetition-context distributions before/after, retention fraction, distinct board signatures and history-state IDs, and candidate/teacher rows removed. A configured `min_holdout_positions` is mandatory for a release; fail validation if validation or test is below that configured minimum or either retains less than 50% of its pre-purge examples. Warn when retention is below 80%. The initial small pilot may use a lower explicit minimum, but it must be fixed in config before observing holdout results. If a purge materially changes the intended distribution, revise the split design in a new version or collect another approved sample; never refill a holdout by moving rows across game partitions.

This policy preserves game-level assignment, prevents cross-partition normalized duplicate games and exact board-position overlap after explicit purge, and keeps candidates together. It can remove a large fraction of held-out rows; M3 must report and gate this loss. It does not eliminate near-position similarity, shared opening concepts, player/event correlations, temporal correlations, or leakage through public chess knowledge. Do not claim absolute leakage elimination. A holdout is stable only for a frozen source manifest, split-rule version, and seed; a new archive is a new dataset version.

## 7. M3 testable invariants

The future M3 suite must include synthetic PGNs for standard and malformed headers, comments/variations, missing ratings/time control, nonstandard variant, custom initial FEN, unfinished result, illegal move, checkmate terminal, duplicate game with changed headers, transposition duplicates, and cross-split overlap. No user names or downloaded third-party game records belong in fixtures.

Tests must verify:

- bounded streaming and explicit max-games/max-positions/max-output-bytes safeguards;
- deterministic game and ply sampling under changed file order;
- replayed history restores automatic repetition context where applicable;
- stable unique UCI action IDs including castling, en passant, and promotion;
- deterministic identifier vectors, game-level split assignment, candidate inheritance, board-signature owner/purge, distinct history states, and leakage/holdout statistics;
- White/Black result perspective conversion;
- teacher raw score, mate, MultiPV, and transform fields do not collapse into one unlabeled scalar;
- interruption/resume validates source/config hashes and does not duplicate rows;
- output manifests match every completed data file and every failure is represented in quarantine/report counts.

The concrete synthetic identity/split vectors—including different clocks and repetition histories, castling, en passant, transpositions, changed duplicate-game headers, candidate inheritance, promotions, and a holdout-collapse case—are retained in `tests/fixtures/pre_m3_identity_vectors.json` and exercised by `tests/test_pre_m3_contracts.py`. These are contract tests, not a production parser/exporter.

## 8. Storage-efficient rows and archive safety

Store each immutable game's initial FEN and full main-line UCI list once in the game table. A position row stores `game_id`, `ply_index`, current six-field FEN, `history_state_id`, `board_position_signature`, and labels. Reconstruct its exact simulator rules state by loading the referenced game and replaying the prefix. This uses O(total game plies + sampled positions) storage instead of repeating O(ply) histories in every row. A missing game reference or replay/hash mismatch invalidates the release. A later encoded-observation cache is disposable and must name its encoder/schema hash. A FEN-only M4 feature view may omit repetition context; M5 must test or encode the state needed for the simulator's automatic outcomes.

The future source reader must fail closed before parsing and must not extract arbitrary ZIP paths to disk:

- require the exact approved archive hash/byte count and exact approved PGN member name; reject duplicate member names, unlisted data members, encrypted members, absolute paths, drive prefixes, `..`, backslashes, and symlink entries;
- require configured compressed-byte and total declared decompressed-byte ceilings, per-member ceiling, member-count ceiling, and compression-ratio ceiling; enforce the decompressed-byte cap again while streaming fixed-size chunks because ZIP metadata is untrusted;
- read only the selected PGN member through `ZipFile.open`, so CRC is checked at EOF; corrupt/truncated stream, CRC, encoding, and parser errors stop the run rather than look like an empty dataset;
- use proposed initial parser limits of 8 MiB per game block, 256 KiB total headers, 64 KiB per header value, and 1 MiB per comment token; exceeding a per-game limit quarantines that game with a stable reason code, while repeated exceedances stop the run for review. These values must be checked against an authorized source profile before acquisition;
- run an OS-limited worker, monitor total RSS, and refuse a larger run on hosts without an enforceable memory ceiling; the selected tier's RSS cap applies to the whole parser process, with Stockfish Hash separately bounded inside its own process;
- estimate peak disk as compressed input + staging segments + final output + manifests/log reserve + 20% free-space reserve; do not write if the approved output cap or projected free-space check fails;
- reject unsupported encodings instead of lossy replacement, and keep bounded quarantine diagnostics without unnecessary player identifiers;
- refuse an existing run/release path. Use a new immutable run ID and same-filesystem staging directory; atomic segment rename and a committed batch journal prevent partial writes from appearing complete.

For an approved official `.pgn.zst` source, treat the archive as one compressed stream rather than a ZIP member: bind the exact downloaded bytes to the official SHA-256 and approved compressed-byte cap, feed the decoder in fixed-size chunks, enforce a hard decompressed-byte and process-RSS ceiling during streaming, verify any available frame checksum, and stop on decoder/truncation errors or unexpected trailing/additional frame data outside the approved source-format policy. Do not decompress to an unbounded temporary PGN. The decoder must be a separately pinned dependency or explicitly verified host utility; record its version and limits in the config. ZIP member/path checks do not apply to this format, but output-path, disk, memory, time, and atomic-release safeguards still do.

Initial Elite-candidate archive ceilings are proposals and must be confirmed against a permitted source profile before retrieval. The compressed archive cap is 150 MiB for all tiers; the approved PGN member cap is 512 MiB for the minimal pilot, 2 GiB for medium validation, and 8 GiB for a larger authorized run. All tiers permit one explicitly named PGN data member only. A proposed compression-ratio ceiling of 200:1 is an early stop/review signal, never a replacement for absolute compressed and decompressed byte caps; measured source behavior may require a reviewed config change before acquisition. A source whose declared values exceed the selected tier requires a new budget. Game, position, output, RSS, worker, hash, and wall-time caps are also mandatory and are enumerated in the teacher/resource plan.

## 9. Atomic release and resume invariants

Every run identity binds the exact source archive/member digest, schema versions, expanded config hash, code revision, parser/rules-library versions, and authorization record. Batch IDs are monotonic; each atomically committed batch carries source-ordinal bounds, row counts, ID-set digest, and file SHA-256. Resume verifies every prior batch, rejects gaps/overlaps or duplicate `sample_id`s, checks immutable source/config/code identities, and resumes only after the last committed batch. A mismatch preserves the staging tree and requires a new run ID; it never silently skips or regenerates rows in place.

Build release outputs from verified batches into a new staging release. Run foreign-key, legal-move, replay/history, split, holdout-size, counts, and hash validation before an atomic same-filesystem rename to a previously nonexistent release path. A crash before rename leaves only a clearly marked staging artifact. A partial or PGN-only dataset remains intermediate until every mandatory canonical M3 criterion has evidence; mock engines, a protocol document, and teacher-disabled runs cannot satisfy M3-02.

