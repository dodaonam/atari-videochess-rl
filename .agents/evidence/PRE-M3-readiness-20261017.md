# Pre-M3 Repository Readiness and Research Audit

- **Scope:** Complete Pre-M3 readiness mission; no M3 production implementation or dataset generation.
- **Repository:** https://github.com/dodaonam/atari-videochess-rl
- **Starting integration baseline:** 27dd9f73d2bf7545e194fe40391d0cae5f9b9003 on origin/initial-idea.
- **Feature branch:** feature/pre-m3-readiness.
- **PM3 acceptance IDs:** Mission-level criteria supplied in the Pre-M3 directive; they do not replace or modify canonical M3-01 through M3-04.
- **Final verification and delivery fields:** Updated after local verification, push, clean-clone check, and PR creation.

## Executive status

The clean feature worktree was created from the verified post-M2 squash merge. M2-001 and M2-01 through M2-04 remain complete; G2 remains approved; G3 is unapproved; M3 remains pending separate owner authorization. No source archive was downloaded, parsed, or ingested. No Stockfish search, model training, Colab session, paid compute, or ALE gameplay campaign was started.

The work corrects repository readiness gaps through documentation, canonical state reconciliation, and a bounded pull-request workflow. It adds no production M3 code and no third-party dataset artifacts.

## A01–A04 and B01–B05 repository audit

| Package | Investigated | Implemented or updated | Main finding and evidence | Status |
|---|---|---|---|---|
| A01 — Integration reconciliation | GitHub PR #1, remote refs, branch ancestry, old local checkpoint, and clean-clone portability. | Added [post-M2 integration verification](POST-M2-INTEGRATION-VERIFICATION-20261017.md); state/backlog/handoff synchronized. | PR #1 merged to initial-idea at 27dd9f73 on 2026-10-16. G2 and M2 acceptance stay complete; G3/M3 authorization stay open. | Complete |
| A02 — Branch strategy | Default branch, integration history, existing local/remote branches, open PR overlap. | Added owner decision in [DECISION_REGISTER.md](../../docs/04-research/DECISION_REGISTER.md). | main at c410173 is an ancestor and 26 commits behind initial-idea. GitHub defaults to main. No setting or branch history changed. | Complete; owner decision open |
| A03 — Full inventory | Tracked tree, source/tests/scripts/docs/agent state, lock/config, CI, ignore rules, artifact manifests, and local-only user files. | Added the inventory/gap matrix below. Added M3 plan and source/teacher contracts. | No M3 parser/generator or M4/M5 training code exists. Raw/local artifacts are excluded by design and require independent manifests. | Complete |
| A04 — Documentation synchronization | README, overview, requirements, architecture, execution plan, risk register, test strategy, and original roadmap. | Replaced minimal README; updated stale M2 and operations wording; linked M3 contracts; expanded risks and test layers. | The roadmap remains unchanged. Current project status remains in canonical state/backlog, not README. | Complete |
| B01 — Dependency/runtime audit | Python version, pyproject, lock, local venv packages, CPU PyTorch index, Stockfish setup/provenance. | Documented CPU/teacher boundary and no-new-dependency recommendation. | Python 3.12.3; chess 1.11.2; Gymnasium 1.4.0; ALE-Py 0.11.2; PyTorch 2.14.1+cpu. Offline lock check passed. Stockfish 19 executable/license hashes match M0 evidence. No Colab entitlement is established. | Complete |
| B02 — Tests and CI | All test modules and resource requirements; existing workflow tree. | Added a bounded read-only Python 3.12 PR workflow with pinned actions; documented its deliberately narrow coverage. | No workflow existed. CI runs preflight plus standard-library context/export tests only; it installs no project packages, runs no ALE, and uses no Stockfish. Remote result is recorded after PR creation. | Complete; remote check pending |
| B03 — M1/M2 compatibility | Environment, vision, controller, shadow, episode, simulator, baselines, benchmark, and tests. | No implementation code changed. Added explicit M3 handoff references to architecture and contracts. | Stable UCI identity and full Board history are preserved; agent color/reward perspective, terminal/truncation and opponent identity are represented. ALE RGB remains authoritative. Main future risk is history loss if a future model consumes FEN alone. | Complete; future risks retained |
| B04 — Security/privacy/licensing | Tracked path names, ignore patterns, large files, license files, Stockfish binary handling, dataset/ROM exposure, local user artifacts. | Added clear repository/source license decisions and data handling rules. | No top-level LICENSE; no raw PGN/model files tracked. Stockfish remains local with GPL text, not in Git. The Elite archive has no stated license on its publisher page. | Complete; owner decisions open |
| B05 — Evidence/artifact lifecycle | Portable checkpoint rules, artifact hashes, local/clean-clone distinction, state growth, review bundles. | Documented run manifests, local/external evidence classes, and safe future state migration. | Dated local M1 manifests verified 1,214 and 1,388 files. Legacy unversioned manifest lists 327 missing historical paths and is not a current inventory. PROJECT_STATE.yaml is about 2.04 MB with 92 checkpoint-history entries. | Complete; state migration deferred |

### Full repository inventory and gap matrix

| Area / component | Purpose and maturity | M3 relevance | Disposition |
|---|---|---|---|
| AGENTS.md and .agents/PLANS.md | Canonical operating/source hierarchy, safety boundaries, plan and recovery rules. | Controls approvals, evidence, and future task selection. | Reviewed; current direct instruction governs Pre-M3 and no durable contradiction required an edit. |
| .agents/state/PROJECT_STATE.yaml | Current gate/milestone/task pointer, checkpoint, portable and local snapshots. | Must keep M2 integration and M3 authorization distinct. | Reconciled; history preserved. Monitor growth; do not truncate without migration. |
| .agents/tasks/BACKLOG.yaml | Stable tasks, dependencies, statuses, acceptance IDs, evidence. | M3 task remains pending with M3-01 through M3-04 only. | Added pending M3-001 and integration evidence to M2-001; no acceptance status was inferred. |
| BLOCKERS.md / VERIFIED_FINDINGS.md / SESSION_HANDOFF.md | Blocker ownership, append-only findings, recovery pointers. | Handoff must point to Pre-M3 material without duplicating live state. | No new technical blocker. Added verified findings and refreshed handoff pointer. |
| .agents/plans/M00, M01, M02 | Existing bootstrap, ALE, and chess plans. | M2 remains the completed prerequisite. | Audited; preserved. New M03 plan follows naming/format and remains non-authorizing. |
| README.md | One-line heading before this task. | Missing a practical entrypoint for a future dataset executor. | Expanded with architecture, clone/setup/test commands, navigation, maturity and limitations. |
| .python-version, pyproject.toml, uv.lock | Python 3.12, bounded runtime dependency ranges, CPU Torch index, committed exact lock. | Existing python-chess supports planned PGN replay; ZIP/JSON/hash needs no new dependency. | Offline locked check passed; no dependency changed. Zstandard is a future explicit decision if selected source requires it. |
| .gitignore | Ignores environment/secrets, generated data, model/checkpoint/run directories, caches. | Prevents accidental raw PGN/model commits. | Reviewed; existing rules adequate. Artifact contents need separate manifests. |
| LICENSE | No top-level project code license. | Dataset rights and code reuse are distinct. | No license added; owner decision recorded. |
| .github/workflows | No workflow at baseline. | Context/schema errors can be caught on PR without data or model dependencies. | Added read-only standard-library preflight workflow. No branch protection configured. |
| videochess_rl/environment.py | Gymnasium/ALE lifecycle, RGB frames, flags/reward and runtime metadata. | ALE is later integration boundary, not dataset source. | Existing M1 implementation retained; real ALE tests remain separate from CI. |
| videochess_rl/vision.py | RGB square occupancy/cursor/temporal parsing. | Future M6 state source. | No direct M3 dependency; preserve as observation authority. |
| videochess_rl/controller.py | UCI move intent to calibrated joystick/FIRE plan. | Future inference integration. | No M3 changes; special-move and broader profile risks deferred to M6. |
| videochess_rl/shadow.py | python-chess candidate transition checked against RGB. | M3 Board history concepts must not be confused with Atari truth. | No changes; shadow commits only after verified RGB. |
| videochess_rl/episode.py and demo.py | Bounded ALE episode/control runner and diagnostics. | Future M6 only. | No gameplay or code changes in Pre-M3. |
| videochess_rl/simulator.py | Standard chess rules/history, legal UCI moves, agent/opponent transition, reward/outcomes/truncation. | M3 rows can reconstruct positions through initial FEN plus UCI history. | Reviewed; no defect requiring a fix. Never assume FEN restores repetition history. |
| videochess_rl/baselines.py | Seeded random-legal and transparent heuristic policies. | M4/M5 comparison baselines. | Existing engine-free baselines retained. |
| videochess_rl/benchmark.py | Seeded simulator benchmark with per-game status and metric-source labels. | Methodology precedent for reproducible runs. | Existing simulator-only reporting retained; not relabeled as ALE. |
| tests/test_agent_context.py / test_export_review_bundle.py | Standard-library schemas, links, checkpoint, clone, bundle safety and provenance. | Suitable low-cost PR CI. | Included in CI; local final suite rerun recorded separately. |
| tests/test_m0_smoke.py | Locked dependency, ROM registration/construction, Stockfish UCI ping. | Environment readiness, not dataset labeling permission. | Full local suite covers; CI excludes because dependencies/manual engine are intentionally absent. |
| tests/test_m1_* | Synthetic controller/vision/shadow plus real packaged-ALE reset/gameplay integration. | Demonstrates observation boundary; must not run large campaigns in CI. | Full local regression suite covers; no new campaign. |
| tests/test_m2_* | Simulator rules/history, baselines, seeded benchmark and metric separation. | Confirms stable UCI/history contract used by M3. | Full local suite and focused suite cover. |
| scripts/agent_preflight.py / agent_checkpoint.py | State validation, links, task graph, Git snapshots, recovery/checkpoint. | Canonical handoff reliability. | No code change; final preflight and clone recovery required. |
| scripts/export_review_bundle.py | Safe manifest-based review archive export. | Portable evidence, no source data. | Existing safety retained and tested. |
| scripts/run_m1_demo.py / run_m1_terminal_experiment.py | Bounded ALE diagnostic tools. | No M3 dependency. | Not run in this mission; real run artifacts are local and independently hashed. |
| docs/01-foundation | Project overview, requirements, verbatim original roadmap. | Owns constraints and approvals; source candidate factual notes. | Overview and M2 status wording synchronized; roadmap hash/content unchanged. |
| docs/02-management | Execution order, risks, ADR-0001/0002. | M3 sequence and durable technical contract. | Risk register updated. No ADR changed because open choices need owner/instructor approval. |
| docs/03-technical | ALE, board extraction, action adapter, architecture, MDP. | M1/M2 compatibility boundary. | Architecture links M3 data contract; accepted ADR-0002 retained. |
| docs/04-research | Empty before this task. | Needed dataset/teacher/experiment contracts and decisions. | Added DATASET_SPEC, STOCKFISH_TEACHER, EXPERIMENT_PROTOCOL, DECISION_REGISTER. |
| docs/05-operations | Setup and M1 reproducibility. | Local CPU/engine/data/artifact lifecycle. | Added REPRODUCIBILITY; existing setup retained. |
| docs/06-quality | Canonical acceptance and test strategy. | M3 tests map to existing M3-01 through M3-04. | Acceptance criteria unchanged; test strategy documents CI and future M3 tests. |
| artifacts/ and evidence archives | Ignored local RGB/run data plus tracked manifests and selected sanitized bundles. | No M3 dataset artifacts exist. | Dated manifests checked separately; no dataset/model artifact added. Clean clones cannot verify absent local data. |
| Local-only primary-checkout files | Deleted tracked HTML and untracked main.py / terminal-success ZIP in the pre-existing checkout. | Not part of clean remote baseline. | Preserved untouched outside the new feature worktree; hashes and sizes are in the post-M2 verification record. |

## C01–C05 and D01–D05 research decisions

### Source and profile

The live [Lichess Elite Database listing](https://database.nikonoel.fr/) reports the May 2022 package as 355,535 games and 93 MB, describes standard Lichess games, excludes bullet, and says the threshold since December 2021 is 2500+ vs 2300+. Its FAQ says clock times are omitted and URLs are carried under LichessURL from June 2020. The publisher page does not give this filtered archive a license or the May archive checksum. Those archive/header facts remain source-reported, not locally measured.

The [official Lichess database](https://database.lichess.org/) states that its database exports are CC0. The official page separately identifies broadcast PGNs under CC BY-SA 4.0 and lists May 2022 as 5,695 games/3.55 MB. Recent official rated-standard months are about 28–31 GB compressed with an approximately 7.1x uncompressed expectation. These sources differ in rights evidence, size, and distribution. Recommendation: obtain explicit terms for the third-party Elite archive; otherwise prefer filtering an official CC0 source and budget its larger stream. Keep official broadcasts as the small licensed fallback if share-alike and distribution differences are accepted. O-06 remains open.

No archive was downloaded. The first M3 profile must bound sample size and report actual PGN tags, malformed/illegal games, variants, results, ratings, time control, termination, annotations, URLs, names, move counts, and source hashes.

### Data/teacher/research contract

DATASET_SPEC.md defines versioned source, game, position, teacher, split, and release manifests; full history replay; FEN limits; UCI candidates; game-level deterministic sampling; reason-coded quarantine; deduplication; and split-level canonical position purge with residual leakage measurements.

STOCKFISH_TEACHER.md recommends played-move behavior cloning as the first M4 baseline. It distinguishes played behavior, final result, Stockfish MultiPV, raw evaluation, normalization, RL reward/return, and learned Q. It records the verified M0 Stockfish 19 host hash and proposes a one-thread bounded MultiPV pilot only after approval. No Stockfish search was run.

EXPERIMENT_PROTOCOL.md separates M3 data quality, M4 supervised prediction, M5 simulator RL, M6 real ALE, and M7 integrated reporting. REPRODUCIBILITY.md specifies configs, seeds, artifact manifests, checkpoint recovery, CPU/GPU boundaries, and storage safety.

The illustrative 80 plies/game and 30 candidates/position calculations are explicitly assumptions, not measured throughput. Proposed pilot/medium/full ceilings are planning tiers only. Actual archive expansion, record sizes, CPU throughput, and engine p95 time remain unverified pending an authorized sample.

## Owner decisions and governance

The concise alternatives, verified facts, uncertainties, trade-offs, authority, recommendation, and M3 effect are in [DECISION_REGISTER.md](../../docs/04-research/DECISION_REGISTER.md).

- O-01: assignment/instructor permission for extraction, custom RL, Stockfish labels, and offline engine use.
- O-06: source, license, transformation, retention, publication, and redistribution policy.
- O-07: Stockfish role/version/search budget.
- O-04: storage, cloud/GPU entitlement, and paid-resource permission.
- Repository owner: default branch main vs initial-idea and no top-level code license.
- Owner/instructor: played-move behavior cloning as first M4 objective, with outcome/teacher targets kept as separate experiments.

These remain pending. G2 is approved, M2 is integrated, G3 is not approved, and M3 is not authorized. A recommendation does not resolve an approval.

## M03 plan and architecture

[M03-expert-dataset.md](../plans/M03-expert-dataset.md) is review-ready but non-authorizing. It maps M3-01 through M3-04 to future package boundaries, synthetic tests, source/teacher evidence, resource caps, staging/recovery, manifest validation, and a single PR against initial-idea. Planned modules cover contracts, source/archive checks, streaming PGN, sampling, dedup, splitting, optional teacher process, export, statistics, and bounded CLI. No module was created or executed in this mission.

## Verification record

Verified baseline checks:

- Clean worktree agent preflight at 27dd9f73: PASS, expected commit/checkout transition; ARTIFACT_MANIFEST_REQUIRED reviewed.
- Offline dependency lock consistency: PASS; no package installation.
- Runtime inspection: Python 3.12.3, chess 1.11.2, Gymnasium 1.4.0, ALE-Py 0.11.2, PyTorch 2.14.1+cpu.
- Stockfish provenance: local UCI binary identifies Stockfish 19; executable hash 0f83d24cc46d2c66c60f16001af5444873bc112b7d028594513426894c12da19; GPL text hash 3972dc9744f6499f0f9b2dbf76696f2ae7ad8af9b23dde66d6af86c9dfb36986. No search issued.
- Local M1 dated manifest verification: 1,214 and 1,388 entries matched. Legacy unversioned list has 327 absent paths and remains untouched.
- Existing repository evidence records a 180-test complete M0/M1/M2 suite at M2 review. This is historical baseline, not the Pre-M3 final run.

Local verification and delivery evidence is recorded in the sections below; each remote check status is tied to its actual branch SHA and run URL.

## Mission acceptance matrix

| ID | Status at this report draft | Evidence / remaining condition |
|---|---|---|
| PM3-01 | PASS | Remote refs, PR #1 merge commit and GitHub metadata in POST-M2-INTEGRATION-VERIFICATION-20261017.md. |
| PM3-02 | PASS after canonical synchronization | State/backlog/handoff updated and preflight rerun before delivery. |
| PM3-03 | PASS | Inventory/gap matrix in this record. |
| PM3-04 | PASS | README, research, operations, and M03 documents navigable. |
| PM3-05 | PASS | README expanded as project entrypoint. |
| PM3-06 | PASS | main/initial-idea relationship and owner strategy recorded; no settings changed. |
| PM3-07 | PASS | Lock/runtime and test classification reviewed; bounded CI added; remote result noted separately. |
| PM3-08 | PASS | Security, data/code license, and artifact handling dispositions recorded; license choices remain pending. |
| PM3-09 | PASS | M1/M2 interfaces reviewed; no behavior defect requiring a fix. |
| PM3-10 | PASS with source decision open | Candidate/fallback terms and risks documented; no archive download. |
| PM3-11 | PASS | DATASET_SPEC.md contracts versioned. |
| PM3-12 | PASS | Validation, sampling, deduplication, and split policies are testable in DATASET_SPEC.md. |
| PM3-13 | PASS | Behavior cloning recommendation and alternatives in STOCKFISH_TEACHER.md. |
| PM3-14 | PASS | Teacher protocol specified; no labels/search executed. |
| PM3-15 | PASS as planning model | Formulas, assumptions, ceilings, and stop conditions documented; actual throughput awaits pilot. |
| PM3-16 | PASS with transfer risks open | Compatibility assessed; Atari transfer not claimed. |
| PM3-17 | PASS | EXPERIMENT_PROTOCOL.md defines staged provenance and metrics. |
| PM3-18 | PASS | M03 plan maps canonical M3-01 through M3-04 to modules/tests/evidence. |
| PM3-19 | PASS | Decision register keeps O-01/O-04/O-06/O-07 and owner choices unresolved. |
| PM3-20 | PASS locally; final remote check pending | Full local suite, checkpoint preflight, and clean-clone context/export tests have passed; final PR check will verify the final tree after the last checkpoint. |
| PM3-21 | PASS | Feature branch was pushed without force; final checkpoint/report commit is still being prepared. |
| PM3-22 | PASS | PR #2 is open against initial-idea and remains unmerged. |

## Explicit non-work

No production data code, full archive download, PGN ingestion, bulk Stockfish labeling, supervised or RL training, Colab/GPU allocation, paid compute, repository-license selection, branch setting change, G3 approval, M3 authorization, PR merge, release, or publication occurred.


## C01–C05, D01–D05, E01–E02 and F01 work-package status

| Package | Investigated and delivered | Deliberately deferred / limitation | Status |
|---|---|---|---|
| C01 — Source due diligence | Compared the Elite listing with official Lichess database terms and reported metadata; alternatives and reuse uncertainty are in DATASET_SPEC.md and DECISION_REGISTER.md. | No archive download; Elite package terms/checksum remain unverified. | Complete for Pre-M3; O-06 open. |
| C02 — Data profiling feasibility | Listed source-reported PGN fields and first-sample profile measurements. | Actual header and quality distributions require an approved bounded sample. | Complete as design. |
| C03 — Schema and lineage | Defined versioned source, game, position, teacher, split, and release records with hashes, history, FEN, UCI, perspective, and split lineage. | No production writer or schema implementation created. | Complete as contract. |
| C04 — Validation and sampling | Specified streaming validation, quarantine codes, deterministic caps, deduplication, coverage summaries, and test cases. | Filter thresholds remain proposals pending source profile and owner decisions. | Complete as design. |
| C05 — Leakage-safe split | Specified normalized-game grouping, deterministic split seed, canonical exact-position ownership/purge, and residual-overlap reporting. | Near-position, player, and opening-concept overlap cannot be eliminated by this policy. | Complete as testable policy. |
| D01 — Supervised targets | Compared behavior cloning, result/value, candidate ranking, and teacher guidance; recommended played-move behavior cloning as the first M4 baseline. | Owner/instructor confirmation and final loss/architecture remain open. | Complete as recommendation. |
| D02 — Stockfish contract | Verified local Stockfish 19 provenance from M0 records and specified raw scores, perspective, MultiPV limits, node/watchdog protocol, and run identity. | No search or labels; O-01/O-07 restrict engine use until approved. | Complete as proposed protocol. |
| D03 — Resource budget | Added formulas, assumptions, pilot/medium/larger caps, memory/output safeguards, and source-specific storage caveat. | Throughput, expansion, and p95 engine time await an authorized pilot. | Complete as planning model. |
| D04 — Downstream compatibility | Mapped history/UCI/result perspective and terminal semantics to M4/M5; kept ALE RGB as M6 authority. | Atari transfer, feature planes, and final model architecture remain unresolved risks. | Complete as interface assessment. |
| D05 — Experiment methodology | Separated M3 data, M4 supervised, M5 simulator RL, M6 ALE, and M7 reporting metrics and provenance. | Final M4–M7 specifications remain deferred to their milestones. | Complete. |
| E01 — M3 architecture and plan | Added M03 plan with packages, CLI boundaries, streaming, resume, tests, caps, evidence, and M3-01–04 mapping. | Implementation and data generation await G3 plus explicit M3 authorization. | Complete; plan is review-ready, not authorizing. |
| E02 — Documentation/governance | Added dataset, teacher, experiment, reproducibility, decision, inventory, integration, and README material; synchronized canonical records. | Owner decisions and deferred M4–M7 documents remain open by design. | Complete. |
| F01 — Verification and delivery | Full 180-test local suite, 57-test clean-clone subset, checkpoint preflight, lock check, and workflow assertions passed. | Remote CI has had two diagnosed failures; final checkpoint and final PR run remain pending. | In progress; no test was weakened. |

## Local verification evidence

- Full suite command: PYTHONDONTWRITEBYTECODE=1 PATH=/home/dodaonam/Projects/atari-videochess-rl/.venv/bin:$PATH /home/dodaonam/Projects/atari-videochess-rl/.venv/bin/python -m unittest discover -s tests -v. Completed 2026-10-16 17:52:53 UTC at baseline revision 27dd9f73d2bf7545e194fe40391d0cae5f9b9003; exit 0, 180 tests, 81.805 seconds. Retained log: logs/pre-m3-full-suite-20261017.log; SHA-256 fc4110f3300648159b67753ddd1acc254224379d878200752151394dfdde5923.
- Initial diagnostic run before refreshing the workspace checkpoint exited 1 because test_project_context_can_be_recovered_without_chat_history asserted git_snapshot_matches while the current work had not yet been checkpointed. The subsequent checkpoint recorded the workspace; preflight then reported both Git and workspace snapshots matching, and the full rerun passed. The initial output was streamed rather than retained as a separate complete log; this note preserves the observed failure and resolution.
- Offline lock consistency: uv offline lock check, exit 0; retained log logs/pre-m3-lock-check-20261017.log; SHA-256 37b9dfa14552b2a07b105bb86de755cbfa1d0b3419166fb16bd389e74341608c.
- Checkpoint preflight: agent_checkpoint.py wrote cp-27dd9f73-20261016T175118702486Z; subsequent agent_preflight.py passed. It reported the expected separately manifested local artifacts directory and ordinary tracked changes since the portable baseline. Retained preflight log logs/pre-m3-final-preflight-20261017.log; SHA-256 c5cee9294b6fad016dbab627c2d37761befe20d76c0a822155a81f48018ad419.
- Workflow YAML parse and permission, pinned-action, branch, timeout, and test-scope assertions passed; retained log logs/pre-m3-workflow-static-20261017.log; SHA-256 756e2e1138ad3ec7de05ab54210838a214dc67741e131a89da627bcb4897e6ce. Two earlier custom-checker assertions were corrected because the checker expected test filenames where the workflow uses module names and counted steps without an action as action references; the workflow YAML itself parsed successfully.

No production dataset or model artifact was created.


## Clean-clone and remote workflow findings

- A fresh clone of feature commit b86c894f6009556a6c116f222ecf31999d90ff00 was created at /tmp/atari-videochess-rl-pre-m3-cleanclone. Agent preflight passed with only ARTIFACT_MANIFEST_REQUIRED for absent ignored artifacts. The standard-library context and review-bundle test modules passed: 57 tests, one expected skip, 67.670 seconds. Logs: logs/pre-m3-cleanclone-preflight-20261017.log (SHA-256 6b497ebb2d4a248941c23b276df882d861ad24bccac60d9332b8bfd5c58e2009) and logs/pre-m3-cleanclone-tests-20261017.log (SHA-256 79106c757a217e69fb074cd7ad442cf6c63abd940ffedfd96edc8fc710b5d1d0).
- PR #2 was opened against initial-idea at feature commit b86c894f6009556a6c116f222ecf31999d90ff00. First remote run 38943663614 failed because default shallow checkout did not contain the G1 baseline tree used by a recovery test. Workflow now sets checkout fetch-depth to 0; tests were not weakened.
- Second remote run 38943914513 reached the historical fixture but failed clean-clone snapshot assertions because the branch had changes after its previous checkpoint. The final checkpoint must be refreshed after all tracked work is staged and must be the last ordinary-content mutation before final push. That run's job log is available at https://github.com/dodaonam/atari-videochess-rl/actions/runs/38943914513/job/117118125083.
- A new final PR run after the checkpoint commit is required; status and run URL are added here only after GitHub reports its actual conclusion.

## State growth disposition

After the two readiness checkpoints, PROJECT_STATE.yaml was 2,130,794 bytes with 94 checkpoint-history entries, above 2 MiB. Its semantic checksum and portable Git manifest validated. Historical records were preserved. RSK-010 now requires a reviewed migration design before sustained further growth; this is an operational follow-up, not a pretext to truncate history.
