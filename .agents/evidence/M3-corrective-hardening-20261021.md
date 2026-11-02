# M3 corrective hardening and acceptance readiness

**Status:** Engineering complete; ready for independent Project Manager review. M3 is not formally accepted, PR #3 remains open and unmerged, and G3 remains unapproved.

**Authorization:** The owner's direct corrective-hardening instruction on 2026-10-21 authorized work on existing M3-001 and PR #3 within the already approved local source and bounded Stockfish scope. The initial M3 authorization is `.agents/evidence/M3-authorization-20261020.md`; corrective scope is `.agents/evidence/M3-corrective-authorization-20261021.md`.

**Deadline:** Presentation is Tuesday, 2026-11-03. At this execution's date, 2026-10-21, 13 calendar days remained.

## 1. Revision and artifact lineage

- Existing reviewed PR head: `ab73663dceb0bdb102be9d03ac76b484cdf64ee6`.
- Corrected artifact-producing revision: `fbdd14d6bed487e5b1388034048eccdbe952ab48`.
- Corrected release r4 and independent repeat r5 were both built from that clean revision, source, configuration, and seeds.
- Final documentation/evidence commits may advance PR HEAD. They do not change artifact-producing code or configuration. Their relationship will be recorded in the final delivery entry and PR description.
- Historical releases r3/r4 at `29c411bfd48dca8f1d463c758078175092639ccb`, corrected-but-pre-hardening releases r2/r3 at `9c8cff4...`, and historical teacher-r2 remain intact. New run directories were used; no prior artifact was overwritten.

## 2. Finding disposition

| Finding | Disposition | Correction and evidence |
|---|---|---|
| F-01 terminal result consistency | Confirmed, P1; fixed | PGN ingestion, independent game validation, and release verification compare automatic `board.outcome(claim_draw=False)` against the declared result and termination metadata, and reject moves after automatic termination. External resignation/timeout results on nonterminal boards remain valid. Regression coverage: `test_automatic_terminal_results_match_board_outcome_but_external_results_remain_valid`, `test_game_validator_checks_result_and_board_termination_independently`, `test_illegal_move_and_automatic_terminal_trailing_moves_are_quarantined`, and release tamper checks. |
| F-02 result perspective labels | Confirmed, P1; fixed | All position labels are derived independently from the validated parent game and reconstructed side to move. Regression coverage: `test_position_result_perspectives_are_derived_from_parent_game_and_board`, including mutually consistent corrupt aliases. |
| F-03 teacher deadlines/watchdog | Confirmed, P2; fixed | Monotonic per-search deadlines now govern watchdog scheduling; teacher command wall budget includes release validation and sample selection as implemented/documented. Timeout, hung engine, missing bestmove, partial results, not-attempted rows, invalid timing inputs, and process cleanup are exercised by fake-UCI tests. A final timing correction was frozen at `fbdd14d`; the corrected real command completed within its 1,800-second budget. |
| F-04 global conflict audit/bottom-K | Confirmed, P2; fixed | A complete bounded source audit indexes normalized-game result sets and source-reference conflicts before deterministic selection. Global bottom-K is applied to eligible non-conflicting groups, with replacement vacancies filled correctly. A full-information oracle compares multiple source-order permutations and late conflicts; production peak RSS was 340.75 MiB against the configured 1 GiB cap. |
| F-05 overwrite regression | Confirmed, P3; fixed | The regression invokes the actual build/release operation against an existing destination, verifies refusal and unchanged prior bytes, covers ordinary retry/resume, and confirms legitimate new-output behavior. |
| F-06 machine-specific teacher path | Confirmed, P2/P3; fixed | Absolute paths, repository-relative paths, and unambiguous executable names on PATH resolve by documented rules; user-home fallback was removed. SHA-256, executable, Stockfish 19, and license checks remain enforced. |
| F-07 holdout/statistics contract | Confirmed, P2/P3; fixed | Minimum holdout and retention failure thresholds are enforced; the 50–80% retention band is retained as a warning without rejecting an otherwise valid release. Before/after quality distributions, result/perspective, ply, rating, time control, candidate count, repetition context, overlap, and history-state metrics are emitted; unavailable clock data is explicitly reported. |
| F-08 provenance/revision integrity | Cross-cutting risk confirmed; resolved | Historical authorization, source terms, r3/r4 releases, and teacher-r2 evidence were preserved. Corrected builds and teacher outputs have new paths/IDs and bind to `fbdd14d`; source, config, release, sample, and sidecar hashes reconcile. No bulk source or derived dataset was added to Git. |
| F-09 global hash-tie ordering | Confirmed adjacent defect; fixed | Bottom-K ties use a global lexical identity tie-break and have a direct regression test (`test_bottom_k_tie_break_is_globally_lexicographic`). |
| F-10 source-prefix ordering determinism | Confirmed adjacent defect; fixed | Selection uses the specified order-independent ranking semantics across source permutations; regression coverage is in `test_source_order_independent_bottom_k_group_selection` and the full-information late-conflict oracle. |
| F-11 zero-count rating categories | Confirmed adjacent reporting defect; fixed | Quality reports preserve zero-count categories rather than omitting them (`test_rating_metadata_reports_zero_count_categories`). |

No known M3 acceptance-blocking correctness defect remains. Full details and test code are in `videochess_rl/data/` and `tests/test_m3_data.py`.

## 3. Source and rights record (M3-01)

The owner-selected source is Lichess Elite Database May 2022, retrieved from `https://database.nikonoel.fr/lichess_elite_2022-05.zip` after the decision and terms record. Archive size: 97,163,552 bytes; SHA-256 `ad374c8fd9fb2fe5f03c1297aa1d47cbbce5caedf6e6e2d387ee816930afdb11`. The sole selected PGN member is 326,476,031 bytes; CRC32 `eaf7e457`; SHA-256 `0f88f18836be7e321aa1e0211b618e78d4e92065c126c45c95a6a55c1500a8e6`. The source manifest SHA-256 is `f2ff571ce81a47b1191f7b57c2f2d16c48ebde6b334aeb6e82d7b173dc2b2935`.

The owner authorized bounded local/internal academic processing, with no source-archive or bulk-record upload/redistribution. The curated third-party package does not state its own license. Official upstream Lichess database terms are documented separately and do not prove the third-party curation package's terms. This uncertainty remains explicit; no CC0 claim is made for the package. Source decision, terms, and authorization records are immutable historical evidence.

## 4. Corrected source-backed releases (M3-03/M3-04)

Profile: `configs/data/m3-training-support.toml`; game/position/split seeds 20261020/20261022/20261023; 1,000 selected games, 20,000 pre-purge positions, at most 32 positions/game, one worker, 1 GiB configured memory, 2 GiB output, 7,200-second build ceiling.

The corrected full-source audit saw 355,535 records, accepted 355,353 before deduplication, quarantined 182 empty games, rejected zero, and selected 1,000 games. It identified 134 duplicate normalized groups / 411 duplicate observations, 33 normalized groups with conflicting results, and zero conflicting source references. All 33 conflicted groups were excluded. The complete identity index estimate was 275,087,884 bytes; measured build peak RSS was 340.75 MiB. Both audit and selection passes read the same 326,476,031-byte member stream hash.

Release r4 (`m3-training-support-corrective-20261021-r4`) and repeat r5 (`...-r5`) have release ID `7b51ec3761ad28aa7a2882691b3c314d35115ab339769251ff2556e706a5b1d9`, manifest SHA-256 `77e217423e187278c584b8f566a846fd606bddaadad19179b7bef63959bd5abe`, code-tree SHA-256 `218a8940dccedf434a4364239f780c680c7fd24f73cb4f5c8eaf57712ebe4d04`, config SHA-256 `fe9543ff65b3953b5a719abf7fd3d6d441886879d30c94ffc747840798ea951a`, and split assignment SHA-256 `84efed824e57de45c0058b73818bb7a9d740201ead38e9171308cee43bc0934e`. Seven manifest-listed data outputs total 39,994,522 bytes; including manifest and checksum, the release directory is 39,996,578 bytes.

The build times were 3,658.404 seconds (r4; peak RSS 340.75 MiB) and 3,544.770 seconds (r5; peak RSS 340.83 MiB). Both exited 0. A separate comparison confirms all nine files are byte-identical. The standalone r4 release/source verifier exited 0 in 112.752 seconds and verified archive/member hash, ZIP CRC, all output hashes, and record reconstruction. r5's internal release verification passed; byte identity links every file to the independently verified r4 bytes.

| Split | Games | Positions before purge | Positions retained | Retention |
|---|---:|---:|---:|---:|
| Train | 795 | 15,727 | 15,196 | 96.62% |
| Validation | 102 | 2,122 | 2,015 | 94.96% |
| Test | 103 | 2,151 | 2,057 | 95.63% |
| **Total** | **1,000** | **20,000** | **19,268** | **96.34%** |

The split purged 732 samples (18,813 candidate rows). Board signatures overlapped across partitions 142 times before purge and zero times after; 18,667 distinct board signatures remain. Distinct replay-history states changed from 18,809 before purge to 18,765 after. Holdout requirements pass without warnings. Candidate rows retained: 578,351 (before purge: 597,164). All 1,000 selected games have both player ratings; date/time-control/player-rating missingness is zero. Source documentation says clock times are omitted; clock information is reported as unavailable. The retained dataset includes rating, time-control, ply-band, side-to-move, final result, side-to-move result, candidate-count, and repetition-context distributions before/after purge, plus distribution shifts.

Selected game-record bytes and normalized selection match historical r3/r4 exactly. Position sample IDs are the same set; the only changed per-position fields are their config-bound `sampling_id` and `sampling_config_sha256`. Release identity and stats/split encodings changed as expected from corrected code revision and expanded conflict/quality reporting. Historical r3 had reported zero normalized result conflicts because its audit was incomplete; corrected r4 reports 33 across the full source, none selected. The old output data remain unchanged.

## 5. Corrected Stockfish teacher evidence (M3-02)

The corrected teacher run `teacher-corrective-20261021-r2` is linked to release `7b51ec...b1d9` and release manifest hash `77e217...d5abe`. It ran the existing verified Stockfish 19 host binary, SHA-256 `0f83d24cc46d2c66c60f16001af5444873bc112b7d028594513426894c12da19`; the retained GPL-3.0 license text hash is `3972dc9744f6499f0f9b2dbf76696f2ae7ad8af9b23dde66d6af86c9dfb36986`. Neither binary nor license is redistributed.

Configuration: 128 deterministic positions (seed 20261025), 5,000 nodes/root, MultiPV 3, one thread, Hash 64 MiB, 30 seconds maximum search cap/root, two-second watchdog grace, and 1,800 seconds total wall budget. Effective options included Threads=1, Hash=64, MultiPV=3, `UCI_ShowWDL=true`, `UCI_Chess960=false`. Scores preserve root/side-to-move perspective and separate White perspective conversion; centipawns use `tanh(cp / 400.0)` rounded to eight decimals, while signed mate distance is typed and not scalar-normalized. The output has 377 cp and 3 mate MultiPV rows, 128/128 positions analyzed, zero failed/unattempted, and 640,363 reported nodes. Engine search elapsed 2.985 seconds; the full command including release verification and sample selection elapsed 114.243 seconds. Teacher run ID `ba4a109064e05ac5d0ec966892745f04fefea014faa8287d977e94fc5f685826`; sample-ID list hash `c4e7423e5b2c1955f45ac930bf9c7f33792da9d9eab4cfb1faf1a9dd68b0b20f`.

Teacher sidecar SHA-256 `bfda27465cee467d0c961fc16cc41aa1177397069f966fef33bd67fd1a405b29` (327,952 bytes); teacher manifest hash `b784da3e56b7f2176698d282f5c82ebc37ef6f8e7ef144eeebabdae44de18dd8`. A standalone verifier bound the sidecar to the corrected release, archive/member identity, all 128 samples, and score-type totals; it exited 0 in 223.937 seconds. The historical teacher-r2 remains linked only to historical release r3/r4; it was not relabeled. A prior timing record that omitted post-finalization validation is retained as historical evidence; the corrected implementation measures that phase inside the total command budget.

## 6. Verification record

On frozen artifact code revision `fbdd14d6bed487e5b1388034048eccdbe952ab48`:

- Focused M3 suite: PASS, 26 tests, 14.129 seconds, 2026-10-21 02:21:21–02:21:35 UTC.
- Pre-M3 contract suite: PASS, 8 tests, 0.098 seconds, 2026-10-21 02:21:35 UTC.
- Full repository suite after checkpoint synchronization: `python -m unittest discover -s tests -v` using the existing project environment and pinned Stockfish on PATH — PASS, 218 tests in 52.275 seconds (52.865 seconds command wall time), exit 0, 2026-10-21 02:25:46–02:26:39 UTC.
- `uv lock --check`: PASS, 18 locked packages, no lock changes; compile check, `git diff --check HEAD`, and `python3 scripts/agent_preflight.py` also passed. Preflight's only warning is the expected independent-manifest requirement for ignored artifacts.
- The first attempt used system Python and failed before test execution because `python-chess` is not installed system-wide. A later test sequence ran after modifying tracked evidence logs and correctly found a stale workspace checkpoint in one context-recovery test. No project-code defect was found: after synchronizing evidence/checkpoint state and capturing suite output outside the repository, the full suite passed all 218 tests. An earlier full-suite run with the pinned engine also passed 218 tests on the same frozen code revision before the current evidence update.
- Synthetic integration, recovery/resume, tamper detection, fake-UCI timeout/cleanup, terminal-result, perspective-label, bottom-K oracle, overwrite refusal, path portability, retention-warning, and quality-statistics regressions are included in the 218-test suite.

Exact successful command timestamps, exit codes, and sanitized test logs are indexed in `.agents/evidence/M3-final-verification-20261021.json` and `.agents/evidence/logs/`. Dataset/teacher run metadata and logs are in the adjacent corrective records. Ignored local artifact paths under `artifacts/m3/` contain source and bulk records and are intentionally not in Git. A clean clone can run code/tests and inspect portable evidence but cannot recompute local source-backed artifacts without the source archive and local run directories.

## 7. M3 acceptance matrix and boundaries

| Criterion | Engineering evidence | Limitation / status |
|---|---|---|
| M3-01 | Owner authorization; exact source/archive/member hashes and CRC; source decision and terms; local corrected release verifier. | Curated third-party package license remains unstated. Owner-authorized local/internal use only; no bulk redistribution. Ready for PM review. |
| M3-02 | Real Stockfish 19 run, pinned binary/license hashes, effective search options, typed score semantics, complete 128-position sidecar and independent release-bound verification. | MultiPV is top three lines, not exhaustive candidate evaluation. Stockfish is offline teacher only, not inference/opponent/benchmark. Ready for PM review. |
| M3-03 | Source-backed r4; 19,268 reconstructed positions; two identical independently generated releases; source/config/code/output hashes and verifier logs. | Raw files remain local ignored artifacts. Ready for PM review. |
| M3-04 | Global conflict audit/bottom-K oracle; game-level split; zero cross-split board overlap after purge; 94.96%/95.63% validation/test retention; complete quality reports and purge ledger. | Board-signature isolation does not rule out all chess-domain similarity. Ready for PM review. |

M4/M5/M6/M7 were not implemented or started. No model training or GPU/Colab/cloud/paid resource was used. The dataset is immediately reconstructible as legal state + UCI action for a small supervised baseline; teacher values remain separate from PGN outcomes, simulator rewards, and Double DQN Q-values. The next research priority is independent PyTorch Double DQN with genuine simulator interaction, subject to its own authorization and readiness checks.

The corrective-evidence checkpoint `cp-fbdd14d6-20261021T022727431901Z` preserved all prior history; at that checkpoint, `PROJECT_STATE.yaml` measured 3,862,087 bytes with 124 entries, close to but below the documented 4 MiB/128-entry follow-up triggers. The later documentation-only sync also preserves checkpoint history. No history migration or truncation was performed.

## 8. Project Manager review checklist

1. Confirm commits and the final branch head on PR #3, target `initial-idea`, open and unmerged.
2. Review the F-01..F-11 regression tests in `tests/test_m3_data.py` and the implementation diff in `videochess_rl/data/`.
3. Inspect this report, `.agents/evidence/M3-corrective-release-manifest-r4-20261021.json`, reproducibility JSON, teacher manifest, sanitized logs, source decision/terms, and canonical state/backlog.
4. Independently check corrected r4/r5 file hashes and release/source verification evidence against locally retained ignored artifacts if those artifacts are available.
5. Review source-license uncertainty and the owner's internal-only scope; do not infer redistribution rights.
6. Confirm reported tests and GitHub Actions scope; CI checks context/preflight and standard-library coverage only, not the large local data build or real Stockfish sidecar.
7. Record formal M3 acceptance separately. Do not infer G3 approval from this PR review.
