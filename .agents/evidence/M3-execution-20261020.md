# M3 engineering execution and acceptance evidence — 2026-10-20/21

## A. Executive outcome

**M3 IMPLEMENTATION COMPLETE — READY FOR PM REVIEW.** The source-backed dataset, hardened real Stockfish teacher sidecar, synthetic recovery tests, independent repeat build, validation evidence, and implementation are ready for independent Project Manager review. The PR must remain open and unmerged until that review. This executor does not self-approve M3. G3 remains unapproved.

The third-party May 2022 package has no stated license. The owner authorized bounded local/internal academic research use; that project decision is not a grant of third-party rights. The source archive and bulk derived records remain on the local host and are not included in GitHub.

## B. Git state and delivery

- Integration baseline: `initial-idea` at `2271b836f4dcf52e62e84413a4c456899138e953`.
- Feature branch: `feature/m3-expert-dataset`, created from the verified integration baseline. Existing local work in the original checkout was preserved.
- Data and teacher runs used clean committed implementation revision `29c411bfd48dca8f1d463c758078175092639ccb`.
- Implementation commits before final evidence refresh: `94b20f0`, `8faf3ba`, `7195b2a`, `45f068e`, `953c192`, `29c411b`.
- Exactly one M3 PR is open: [PR #3](https://github.com/dodaonam/atari-videochess-rl/pull/3), targeting `initial-idea`. It remains unmerged for PM review; the current head and final GitHub check are recorded in PR metadata.
- The archive, PGN, release JSONL, full split ledger/statistics, engine binary, credentials, and model artifacts are not tracked. Portable manifests and sanitized evidence logs are tracked.
- M0–M2 history remains intact. No README change, dependency install, model training, M4–M7 implementation, commit-history rewrite, merge, or G3 approval was performed.

## C. Authorization and decision reconciliation

- Direct M3-001 authorization: `.agents/evidence/M3-authorization-20261020.md`, recorded at 2026-10-20T14:34:24Z. It covers this implementation, bounded local/internal source processing, the bounded Stockfish 19 offline teacher, commits/push, and one open PR. G3 is not a prerequisite and remains unapproved.
- Presentation date: Tuesday, 2026-11-03. Thirteen calendar days remained on 2026-10-21. M3 was deliberately capped to leave the schedule for Double DQN.
- Source: Lichess Elite Database, May 2022, archive URL `https://database.nikonoel.fr/lichess_elite_2022-05.zip`. The publisher reports 355,535 games / 93 MB; these are publisher figures. Actual retrieval was 97,163,552 bytes, SHA-256 `ad374c8fd9fb2fe5f03c1297aa1d47cbbce5caedf6e6e2d387ee816930afdb11`. The single PGN member was 326,476,031 bytes, CRC32 `eaf7e457`, SHA-256 `0f88f18836be7e321aa1e0211b618e78d4e92065c126c45c95a6a55c1500a8e6`.
- Rights: the publisher page provides no package license/checksum. Official Lichess CC0 terms apply to official exports and are not attributed to the curated package. Owner authorization is bounded to local/internal academic use and local retention; no upload or redistribution of the archive or bulk derived game records is authorized. No conflicting restriction was found in the recorded terms review; the package-rights uncertainty remains explicit.
- Stockfish: existing M0 Stockfish 19 only. Binary SHA-256 `0f83d24cc46d2c66c60f16001af5444873bc112b7d028594513426894c12da19`; retained GPL text SHA-256 `3972dc9744f6499f0f9b2dbf76696f2ae7ad8af9b23dde66d6af86c9dfb36986`. Authorized use here was bounded offline teacher labeling only; no inference, opponent, or offline benchmark role.
- Compute: local CPU and local storage only. No Colab, GPU, cloud upload, paid compute, or new Python dependency. Before the final repeat, free disk was 41,225,904,128 bytes against a calculated 5,662,328,254-byte reserve requirement.

## D. Dataset summary

### Initial source pilot

- Profile: `configs/data/m3-pilot.toml`; independent ceilings of 200 games / 10,000 positions.
- 200 games accepted; zero rejected, quarantined, or duplicate. 9,682 positions selected; 9,285 retained.
- Cross-split board signatures: 91 before purge, zero after. Validation/test retention: 95.17% / 95.80%. Legal candidates per position: min 1, median 32, max 64.
- Release ID `24bb40a33f4dfbc024ac8dc3a670d67b6c19841295d964226bfc6b1d14e2887e`; 18,492,851 output bytes. Source/archive/release verification passed.

### Final training-support release (canonical local artifact: r3; identical repeat: r4)

- Profile: `configs/data/m3-training-support.toml`; game/position/split seeds `20261020 / 20261022 / 20261023`; bottom-K grouped game selection; at most 1,000 games, 20,000 positions, 32 positions/game; one worker; 2 GiB output cap; 7,200-second wall cap; configured memory cap 1 GiB.
- Full scan: 355,535 games seen; 355,353 accepted before normalized dedup; 182 quarantined as `empty_game`; zero rejected. Source-reference duplicate observations: 0. Normalized duplicate observations: 411 in 134 groups; no conflicting normalized groups.
- Selected 1,000 games: train 795, validation 102, test 103. Selected positions before purge: 20,000. Post-purge positions: train 15,196, validation 2,015, test 2,057; total 19,268.
- Retention: train 96.62%, validation 94.96%, test 95.63%. Cross-split board signatures: 142 before purge, zero after. Distinct replay-history states: 18,809 before and 18,765 after. Purged 732 samples and 18,813 associated candidate rows. Candidate rows: 597,164 before and 578,351 after purge; per-position legal candidates min 1, median 32, max 64.
- Required rating/date/time-control metadata was present for all 1,000 selected games. Game plies min 8, median 79, p90 131, max 517. The selected sample had 755 distinct first-eight-ply opening prefixes; HHI 0.003114; the largest prefix occurred in 34 games. The purge changed opening/ply-band/result proportions; measured shifts are in the release stats and reproducibility JSON. Zero exact board-signature overlap does not establish statistical independence.
- Release ID `9e3944e1e35ca0d774e479a49d9b93eb769d14e52ffec4bc6f886bd4695b8991`; manifest SHA-256 `574bcc52c3b6ad91c64c283a8f93ab05eb5a7e07ca138fa5d3e2da26edb09ada`; config SHA-256 `33186c332a956e006da473b4e37046e3cb953fd775d67be1906050ea4ed6a69f`; split assignment SHA-256 `84efed824e57de45c0058b73818bb7a9d740201ead38e9171308cee43bc0934e`.
- Seven manifest-listed outputs total 39,868,538 bytes; complete release directory including `manifest.json` and `manifest.sha256` totals 39,870,594 bytes. The output hashes are in `.agents/evidence/M3-release-manifest-r3-20261020.json`.
- r3 build: 2026-10-20T16:29:13Z–17:00:10Z; 1,852.28 user CPU seconds; 1,856.379 seconds pipeline wall time; peak RSS 288.96 MiB. r4 repeat: 17:06:04Z–17:36:45Z; 1,836.481 user CPU seconds; 1,840.553 seconds pipeline wall time; peak RSS 289.04 MiB. Both had a 20% disk reserve in the preflight calculation and exited 0.
- Independent r3/r4 comparison found all nine files byte-identical, including the manifest and checksum file; source, config, schema, split, output hashes, and release ID matched. Both releases passed source/archive/release verification; the same teacher run also verified against both identical releases.

## E. Stockfish teacher summary

- Engine: Stockfish 19; verified binary and GPL text hashes are in section C and the portable teacher manifest.
- Settings: Threads 1, Hash 64 MiB, MultiPV 3, `UCI_ShowWDL=true`, Chess960 false, one shared 5,000-node cap per root search, UCI `movetime` cap and protocol deadline 30 seconds, external process watchdog with maximum two-second grace, 1,800-second total wall cap, and 64 MiB output cap. Hash is cleared between root positions.
- Deterministic sample: 128 positions, seed `20261025`; 128 analyzed, 128 with rows, zero failures/timeouts/unattempted. Reported total engine nodes 640,363; teacher search elapsed 2.768 seconds; throughput 46.2428 positions/second. The outer command took 105.722 user CPU seconds including release validation.
- Score semantics: raw scores carry side-to-move perspective with a separate White conversion. The 380 returned MultiPV lines comprise 377 typed centipawn and 3 signed mate scores. Centipawn transform is `tanh(cp / 400.0)`, rounded to eight decimals; mate distances stay typed and have no normalized scalar. WDL is retained when returned. MultiPV covers only returned lines, not every legal action. Teacher rows are separate from played-move labels and are not RL Q-values.
- Teacher run ID `e431381ddcf7f62e89d2a82cca55dff916c3823d2928995c0c08370e477116e3`; manifest SHA-256 `4a2cb32ed163a215b661dc9b3801a4cb17f20a408dd5aab9e3219456d36d7891` (portable file hash should be checked against `.agents/evidence/M3-teacher-manifest-r2-20261020.json`); sidecar SHA-256 `d1f0620beb6eb985ec36c85a5eb6846917656221f3c5a2171e4eecc38c879d6f`.

## F. Acceptance matrix

| Criterion | Result | Evidence and limitation |
|---|---|---|
| M3-01 source/provenance | PASS | Owner authorization, source decision/terms, retrieval timestamp, archive/member identity and hashes, CRC, package license uncertainty, and non-redistribution boundary are recorded. Rights uncertainty for the third-party package remains; no public/bulk distribution is claimed. |
| M3-02 Stockfish teacher | PASS | Real bounded Stockfish 19 analysis, actual binary/license hashes, requested/effective settings, typed raw scores/perspectives, normalization, mate handling, sample/run identities, and sidecar verification. 128-position coverage only; no inference use. |
| M3-03 reproducibility/provenance | PASS | Source-backed r3 release, per-row game/ply lineage and reconstruction checks, complete manifest, r3/r4 exact file-byte repeat, and repeated source/release verification. Raw release remains local because the owner decision prohibits redistribution. |
| M3-04 leakage/quality | PASS | Game-grouped splits, candidate inheritance, 142-to-0 cross-split board signatures, distinct history-state counts, purge ledger, per-split counts, 94.96% validation / 95.63% test retention, distortion statistics, and hashes. Board-signature purge does not remove every possible statistical similarity. |

These are implementation evidence results. Independent PM review is still required for milestone acceptance.

## G. Test and verification matrix

- Focused M3 unit/integration suite: **19 tests passed** after hard-timeout and invalid-PV regressions were fixed.
- Full local repository suite: **211 tests passed** at revision `29c411bfd48dca8f1d463c758078175092639ccb`. An initial attempt failed one M0 smoke test because the isolated worktree PATH omitted the existing host Stockfish binary; rerun with the verified host binary directory on PATH passed all 211 without code changes. Both runs are retained in the sanitized final verification log.
- Synthetic end-to-end build, replay reconstruction, journal/recovery, and fake-UCI timeout/failure cases: passed within the focused M3 suite.
- Real source pilot: 200-game/9,682-position selection completed and verified.
- Final source dataset: r3 and r4 full scans exited 0; exact release file comparison passed; source/release/teacher verification passed for both.
- Real Stockfish 19 teacher: 128/128 positions; zero errors/timeouts; sidecar verification passed.
- Lock check: `uv lock --check --python /usr/bin/python3` passed; no dependency installation or lock change.
- Compile check: `python -m compileall -q videochess_rl/data tests/test_m3_data.py` passed.
- Agent preflight: passed at `29c411b`, zero errors and one expected `ARTIFACT_MANIFEST_REQUIRED` warning reviewed against the source/release/teacher manifests. The execution log records checkpoint `cp-29c411bf-20261020T174944823949Z`; a final checkpoint and post-checkpoint preflight are part of delivery verification.
- Clean-clone recovery, preflight, and all 211 repository tests also passed on the final evidence-only PR head; the latest head SHA, UTC execution record, and raw-log hashes are in PR #3 delivery metadata. GitHub Actions context/preflight passed on the final head; it does not cover source-backed M3 data or real Stockfish execution. The detailed earlier clean-clone record at `472005991f35580b7df4e3e2b5a2876798ae1ae6` is retained in `.agents/evidence/logs/M3-clean-clone-final-4720059.log`; full local test logs are in `.agents/evidence/logs/M3-final-verification-20261020.log`.

## H. Engineering audit

- A regression test showed python-chess's engine protocol timeout does not cap a search when only a node limit is set. The runner now combines `nodes` and `movetime`, applies an external process-kill watchdog/grace, records per-root caps, clears hash state between roots, rejects missing/invalid root PV moves, and preserves error records. Tests cover valid MultiPV, bad PV, a process that ignores time limits, and missing engine binaries.
- A first hardened teacher launch used the wrong filename capitalization for the retained license and failed before the engine started. The path was corrected; the actual 128-position run then passed. No search occurred during the failed launch.
- An early repeated full scan was stopped at 130,000/355,535 because the working tree became dirty; it was not treated as determinism evidence. Two fresh runs were then executed from the same clean committed revision/config and matched exactly.
- The first post-hardening full suite exposed four context failures because final evidence/checkpoint state had not yet been refreshed. After the evidence and checkpoint synchronization, the suite passed; preserve that failed log as process history, not as a product acceptance result.
- `PROJECT_STATE.yaml` exceeded the ordinary 2 MiB content-hash boundary. It measured 2,810,555 bytes / 107 retained history entries before final handoff. No history was truncated. M3 used a small number of meaningful checkpoints and did not demonstrate that migration was needed; preserve RSK-010 as a follow-up before future checkpoint-heavy work.
- No schema/hash semantics were changed. Existing synthetic reference vectors remain unchanged. No new third-party dependency was added.

## I. RL-first readiness assessment

1. **Can M4 load the data?** Yes. The JSONL games and positions provide a directly loadable local artifact with source game references, `ply_index`, reconstructible history, legal UCI candidates, played move, side to move, and result perspective. A fresh clone must reacquire/regenerate from the authorized source because the bulk data is intentionally not committed.
2. **Can M5 reconstruct legal-action states?** Yes. Position rows reference immutable game history and exact decision ply; the synthetic and release verification paths replay those states and validate legal candidates.
3. **Are teacher scores separate from Q-values?** Yes. Teacher scores are typed offline annotations in a sidecar; played moves/outcomes remain separate, and no M5 return or Q-value is inferred from centipawns.
4. **Smallest useful M4 baseline:** a time-boxed played-move behavior-cloning baseline over the training split, with logits masked to recorded legal UCI candidates and held-out legal top-k accuracy. Keep a separate checkpoint and report it as imitation, not RL.
5. **Main risks before Double DQN:** define legal-move action scoring against the existing M2 interface; verify reward perspective and terminal/truncation semantics; keep `python-chess` history Markov-correct; treat holdout similarity honestly; respect third-party source restrictions; prevent M4 from taking the M5 schedule.
6. **Must M5 wait for more data?** No. This bounded dataset is sufficient to begin interface work and a small optional baseline. M5 core Double DQN and its first simulator interaction run should begin promptly; M4 should not block them.
7. **Measured M3 cost:** local storage under ignored `artifacts/m3/` is about 346 MiB at this checkpoint (including source, pilot, multiple releases, teacher runs, and interrupted-run staging). The two deterministic full builds used 3,688.761 user CPU seconds; the final teacher wrapper used 105.722 user CPU seconds. An earlier interrupted scan used 669.63 CPU seconds; other parser, verification, and tests add unaccounted CPU time. No GPU/cloud/paid compute was used. The main two builds consumed about 62 minutes wall time; M3 remained bounded to these runs and did not train a neural model.

## J. PM review checklist

Review the implementation commit series and final diff; verify `videochess_rl/data/`, `tests/test_m3_data.py`, `configs/data/`, `docs/04-research/`, `docs/05-operations/`, the M3 authorization/source/release/teacher/reproducibility evidence, and the sanitized M3 logs. Independently inspect the source rights boundary, local-only artifact note, release and split hashes, purge ledger summary, teacher binary/settings/typed score semantics, focused/full test logs, preflight/checkpoint result, clean-clone result, and GitHub check run on the final PR head. Confirm the PR targets `initial-idea`, remains open/unmerged, G3 is still unapproved, and M4–M7 are not marked started.
