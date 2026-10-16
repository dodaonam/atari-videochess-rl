# Pre-M3 Repository Readiness and Research Audit

- **Scope:** Complete Pre-M3 readiness mission; no M3 production implementation or dataset generation.
- **Repository:** https://github.com/dodaonam/atari-videochess-rl
- **Starting integration baseline:** 27dd9f73d2bf7545e194fe40391d0cae5f9b9003 on origin/initial-idea.
- **Feature branch:** feature/pre-m3-readiness.
- **PM3 acceptance IDs:** Mission-level criteria supplied in the Pre-M3 directive; they do not replace or modify canonical M3-01 through M3-04.
- **Final verification and delivery fields:** Updated after local verification, push, clean-clone check, and PR creation.

> **Corrective-hardening addendum (2026-10-17):** The original readiness report below preserves findings and verification from the first PR review. Its statements that G3 approval is required before M3 work and that behavior cloning is the first M4 objective are superseded by this addendum and the current canonical plan/research contracts. G3 is the closure gate for M2–M5, not an M3 start prerequisite; M3 still requires separate explicit authorization and source-specific approvals. Double DQN is the principal academic objective; behavior cloning is optional and time-boxed. See [RL-First Alignment](../../docs/04-research/RL_FIRST_ALIGNMENT.md), [M03 plan](../plans/M03-expert-dataset.md), and [PLANS.md](../PLANS.md). Historical test/CI statements below refer to their named revisions only and are not claims about the final corrective-hardening HEAD.

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
| B02 — Tests and CI | All test modules and resource requirements; existing workflow tree. | Added a bounded read-only Python 3.12 PR workflow with pinned actions; documented its deliberately narrow coverage. | No workflow existed. CI runs preflight plus standard-library context/export tests only; it installs no project packages, runs no ALE, and uses no Stockfish. Remote runs exposed shallow history and a stale checkpoint; both were corrected without changing tests. Final PR run 38944551579 passed on 843a0bc. | Complete |
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

At the original readiness checkpoint, STOCKFISH_TEACHER.md recommended played-move behavior cloning as the first M4 baseline. Corrective hardening supersedes that priority: behavior cloning is optional and time-boxed, while Double DQN from simulator reward is central. The teacher contract still distinguishes played behavior, final result, Stockfish MultiPV, raw evaluation, normalization, RL reward/return, and learned Q. It records the verified M0 Stockfish 19 host hash and proposes a one-thread bounded MultiPV pilot only after approval. No Stockfish search was run.

EXPERIMENT_PROTOCOL.md separates M3 data quality, M4 supervised prediction, M5 simulator RL, M6 real ALE, and M7 integrated reporting. REPRODUCIBILITY.md specifies configs, seeds, artifact manifests, checkpoint recovery, CPU/GPU boundaries, and storage safety.

The illustrative 80 plies/game and 30 candidates/position calculations are explicitly assumptions, not measured throughput. Proposed pilot/medium/full ceilings are planning tiers only. Actual archive expansion, record sizes, CPU throughput, and engine p95 time remain unverified pending an authorized sample.

## Owner decisions and governance

The concise alternatives, verified facts, uncertainties, trade-offs, authority, recommendation, and M3 effect are in [DECISION_REGISTER.md](../../docs/04-research/DECISION_REGISTER.md).

- O-01: assignment/instructor permission for extraction, custom RL, Stockfish labels, and offline engine use.
- O-06: source, license, transformation, retention, publication, and redistribution policy.
- O-07: Stockfish role/version/search budget.
- O-04: storage, cloud/GPU entitlement, and paid-resource permission.
- Repository owner: default branch main vs initial-idea and no top-level code license.
- Owner/instructor: confirm assignment constraints; RL-first policy keeps behavior cloning optional and time-boxed, with outcome/teacher targets separate.

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
| PM3-13 | PASS | Corrective RL-first analysis makes behavior cloning optional/time-boxed and compares it with the Double DQN objective in RL_FIRST_ALIGNMENT.md. |
| PM3-14 | PASS | Teacher protocol specified; no labels/search executed. |
| PM3-15 | PASS as planning model | Formulas, assumptions, ceilings, and stop conditions documented; actual throughput awaits pilot. |
| PM3-16 | PASS with transfer risks open | Compatibility assessed; Atari transfer not claimed. |
| PM3-17 | PASS | EXPERIMENT_PROTOCOL.md defines staged provenance and metrics. |
| PM3-18 | PASS | M03 plan maps canonical M3-01 through M3-04 to modules/tests/evidence. |
| PM3-19 | PASS | Decision register keeps O-01/O-04/O-06/O-07 and owner choices unresolved. |
| PM3-20 | PASS at original PR head only | Historical checks at 843a0bc are not the final corrective verification. The H09 section below records the corrective suite, checkpoint, clean-clone recovery, and SHA-specific CI result as they complete. |
| PM3-21 | PASS | Feature branch was pushed without force; see PR #2 for its live head. |
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
| D01 — Supervised targets | Compared behavior cloning, result/value, candidate ranking, and teacher guidance; corrective hardening makes behavior cloning optional under RL-first staging. | Owner/instructor confirmation and final loss/architecture remain open. | Complete as recommendation. |
| D02 — Stockfish contract | Verified local Stockfish 19 provenance from M0 records and specified raw scores, perspective, MultiPV limits, node/watchdog protocol, and run identity. | No search or labels; O-01/O-07 restrict engine use until approved. | Complete as proposed protocol. |
| D03 — Resource budget | Added formulas, assumptions, pilot/medium/larger caps, memory/output safeguards, and source-specific storage caveat. | Throughput, expansion, and p95 engine time await an authorized pilot. | Complete as planning model. |
| D04 — Downstream compatibility | Mapped history/UCI/result perspective and terminal semantics to M4/M5; kept ALE RGB as M6 authority. | Atari transfer, feature planes, and final model architecture remain unresolved risks. | Complete as interface assessment. |
| D05 — Experiment methodology | Separated M3 data, M4 supervised, M5 simulator RL, M6 ALE, and M7 reporting metrics and provenance. | Final M4–M7 specifications remain deferred to their milestones. | Complete. |
| E01 — M3 architecture and plan | Added M03 plan with packages, CLI boundaries, streaming, resume, tests, caps, evidence, and M3-01–04 mapping. | Implementation and data generation require separate explicit M3 authorization and applicable source/teacher/storage approvals; G3 is not a start prerequisite. | Complete; plan is review-ready, not authorizing. |
| E02 — Documentation/governance | Added dataset, teacher, experiment, reproducibility, decision, inventory, integration, and README material; synchronized canonical records. | Owner decisions and deferred M4–M7 documents remain open by design. | Complete. |
| F01 — Verification and delivery | Full 180-test local suite, clean-clone recovery tests, final checkpoint/preflight, and bounded PR CI passed. | Two earlier remote failures were diagnosed: missing G1 history in shallow checkout, then portable-manifest drift after a post-checkpoint commit. | Complete; no test was weakened. |

## Local verification evidence

- Full suite command: PYTHONDONTWRITEBYTECODE=1 PATH=/home/dodaonam/Projects/atari-videochess-rl/.venv/bin:$PATH /home/dodaonam/Projects/atari-videochess-rl/.venv/bin/python -m unittest discover -s tests -v. Completed 2026-10-16 17:52:53 UTC at baseline revision 27dd9f73d2bf7545e194fe40391d0cae5f9b9003; exit 0, 180 tests, 81.805 seconds. Retained log: logs/pre-m3-full-suite-20261017.log; SHA-256 fc4110f3300648159b67753ddd1acc254224379d878200752151394dfdde5923.
- Initial diagnostic run before refreshing the workspace checkpoint exited 1 because test_project_context_can_be_recovered_without_chat_history asserted git_snapshot_matches while the current work had not yet been checkpointed. The subsequent checkpoint recorded the workspace; preflight then reported both Git and workspace snapshots matching, and the full rerun passed. The initial output was streamed rather than retained as a separate complete log; this note preserves the observed failure and resolution.
- Offline lock consistency: uv offline lock check, exit 0; retained log logs/pre-m3-lock-check-20261017.log; SHA-256 37b9dfa14552b2a07b105bb86de755cbfa1d0b3419166fb16bd389e74341608c.
- Checkpoint preflight: agent_checkpoint.py wrote cp-27dd9f73-20261016T175118702486Z; subsequent agent_preflight.py passed. It reported the expected separately manifested local artifacts directory and ordinary tracked changes since the portable baseline. Retained preflight log logs/pre-m3-final-preflight-20261017.log; SHA-256 c5cee9294b6fad016dbab627c2d37761befe20d76c0a822155a81f48018ad419.
- Workflow YAML parse and permission, pinned-action, branch, timeout, and test-scope assertions passed; retained log logs/pre-m3-workflow-static-20261017.log; SHA-256 756e2e1138ad3ec7de05ab54210838a214dc67741e131a89da627bcb4897e6ce. Two earlier custom-checker assertions were corrected because the checker expected test filenames where the workflow uses module names and counted steps without an action as action references; the workflow YAML itself parsed successfully.

No production dataset or model artifact was created.


## Clean-clone and remote workflow findings

- A fresh clone of feature commit b86c894f6009556a6c116f222ecf31999d90ff00 was created at /tmp/atari-videochess-rl-pre-m3-cleanclone. Agent preflight passed with only ARTIFACT_MANIFEST_REQUIRED for absent ignored artifacts. The standard-library context and review-bundle test modules passed: 57 tests, one expected skip, 67.670 seconds. Logs: logs/pre-m3-cleanclone-preflight-20261017.log (SHA-256 6b497ebb2d4a248941c23b276df882d861ad24bccac60d9332b8bfd5c58e2009) and logs/pre-m3-cleanclone-tests-20261017.log (SHA-256 79106c757a217e69fb074cd7ad442cf6c63abd940ffedfd96edc8fc710b5d1d0).
- A fresh clone of checkpointed feature commit 843a0bc728370ff9bc8e7a21884c7e05b82eb7c1 passed preflight with its portable manifest matching; only ARTIFACT_MANIFEST_REQUIRED remained. Retained log: logs/pre-m3-final-tip-cleanclone-preflight-20261017.log; SHA-256 89c6df8481f4f030935331617e2a2d3499851c53eebd5135b5013742adf05d0b.
- PR #2 was opened against initial-idea at feature commit b86c894f6009556a6c116f222ecf31999d90ff00. First remote run 38943663614 failed because default shallow checkout did not contain the G1 baseline tree used by a recovery test. Workflow now sets checkout fetch-depth to 0; tests were not weakened.
- Second remote run 38943914513 reached the historical fixture but failed clean-clone snapshot assertions because the branch had changes after its previous checkpoint. Resolved by staging the complete tree, refreshing the checkpoint as cp-c158ee6e-20261016T180408298721Z, and committing it as 843a0bc; no test was changed. That run's job log is available at https://github.com/dodaonam/atari-videochess-rl/actions/runs/38943914513/job/117118125083.
- Final remote PR run 38944551579 completed successfully on checkpointed head 843a0bc728370ff9bc8e7a21884c7e05b82eb7c1: https://github.com/dodaonam/atari-videochess-rl/actions/runs/38944551579. The workflow performed preflight and all 57 standard-library tests (one expected skip). A closeout report/checkpoint commit will trigger another check; the completion report cites that live result.

## State growth disposition

After three readiness checkpoints and before the closeout report checkpoint, PROJECT_STATE.yaml was 2,180,216 bytes with 95 checkpoint-history entries, above 2 MiB. Its semantic checksum and portable Git manifest validated. Historical records were preserved. RSK-010 now requires a reviewed migration design before sustained further growth; this is an operational follow-up, not a pretext to truncate history.

## Corrective hardening H01–H10

| Package | Finding and action | Evidence / status |
|---|---|---|
| H01 — Governance | Separated G3/G4 closure from milestone entry; M3 remains pending and requires a direct authorization evidence record. Preflight reads ADR-0001 coverage and guards the split M7 G4/G5 acceptance ownership. | `scripts/agent_preflight.py`; focused governance tests in `tests/test_agent_context.py`; FND-030. Verified. |
| H02 — Chess identity and split | Specified board signature, replay-history state, source-game identity, normalized-game hash, sample ID, and materialized candidate ID separately. Added deterministic fixtures for clocks, repetition, castling, en passant, transpositions, changed headers, promotion, candidate inheritance/purge, and holdout collapse. | `docs/04-research/DATASET_SPEC.md`; `tests/fixtures/pre_m3_identity_vectors.json`; `tests/test_pre_m3_contracts.py`; FND-031. Verified as contract tests only. |
| H03 — Teacher acceptance | PGN-only output is an intermediate; canonical M3-02 requires an authorized real bounded Stockfish 19 run. Mock tests/protocol prose cannot pass it; formal acceptance change is required if teacher use is prohibited. | `docs/04-research/STOCKFISH_TEACHER.md`; M03 plan; acceptance criteria; FND-032. Verified by cross-document audit; no search ran. |
| H04 — RL-first alignment | Double DQN from simulator reward is central. M5 core and first sanity run need not wait for M4, but current M5-04 still requires a small pretraining-only checkpoint for final paired comparison. The compact behavior baseline is optional to DDQN startup and cannot substitute for RL. | `docs/04-research/RL_FIRST_ALIGNMENT.md`; `docs/04-research/EXPERIMENT_PROTOCOL.md`; `docs/02-management/EXECUTION_PLAN.md`; RSK-012; FND-033. Planning contract verified. |
| H05 — Deterministic identities | Defined canonical JSON encoding, domain-separated SHA-256 inputs, normalization, split ownership, config/teacher/release IDs, and exact reference vectors. Candidate identity now binds parent sample plus UCI action. | Dataset spec and synthetic vector test above. Included in full-suite run below. |
| H06 — Storage and bounded processing | Position rows refer to immutable game history rather than repeating it. Proposed compressed/decompressed/member/game/header/comment, RSS, disk, time, worker, engine, output, resume, and atomic-release controls fail closed pending source-specific measurement. | Dataset spec sections 8–9; teacher resource tiers; M03 plan. Design reviewed; no source acquired or processed. |
| H07 — Checkpoint growth | Preserved all checkpoint history. The first four corrective snapshots measured +206,375 bytes across 4 entries (about 51.6 kB per entry in this limited sample); no general growth forecast is claimed. RSK-010 assigns lossless migration design before sustained M3 checkpoints, with 4 MiB / 128-entry / 5-second earlier triggers and clean-clone/historical-recovery requirements. | `docs/02-management/RISK_REGISTER.md`; `docs/05-operations/REPRODUCIBILITY.md`; FND-035. No migration performed. |
| H08 — Reconciliation | Corrected historical G3/M3 and supervised-first statements via a dated addendum; synchronized M03 plan, state, backlog, findings, research documents, risk register, test strategy, and decision priorities. Lichess source facts remain publisher-reported; O-06 remains open. | This record; canonical state/backlog; DATASET_SPEC and DECISION_REGISTER. Original roadmap and accepted ADRs unchanged. |
| H09 — Verification | Full local suite, offline lock check, checkpoint, and preflight passed on the corrective working tree. Final clean-clone verification and remote PR CI remain pending at this report revision. | Full suite: 192 tests, 82.988 s, exit 0, 2026-10-16T19:36:03.491912526Z–19:37:26.922435254Z; HEAD `bd84973436ab6d71ccb927cb16f16f357041399e`; test checkpoint `cp-bd849734-20261016T193559973241Z`. The immediately preceding checkpoint `cp-bd849734-20261016T193837211396Z` and standalone preflight passed with only `ARTIFACT_MANIFEST_REQUIRED` for ignored artifacts; the current report/evidence update is followed by another checkpoint. Full-suite log SHA-256 `01072d409e623c5b09918062e154c098e3f3d71e57e3db2359a39e3ed0203517`; lock log SHA-256 `fe2f95342cce279d247b0950802b85b99b2f4a5c1d99d7bb116782a9ece0c833`; preflight log SHA-256 `e387e03f557180b7fb080f90310cb5ac438771e7a70c40a92f0132b0acb245eb`. |
| H10 — Existing PR delivery | Continue on `feature/pre-m3-readiness`; update PR #2 targeting `initial-idea`; do not create another PR, force-push, change defaults, or merge. | Delivery remains pending final commit/push, clean-clone verification, PR description update, and final SHA-specific Actions check. |

### Corrective local verification

The exact full-suite command was `PYTHONDONTWRITEBYTECODE=1 PATH=<existing-project-venv>/bin:$PATH <existing-project-venv>/bin/python -m unittest discover -s tests -v` (environment paths sanitized). It ran against HEAD `bd84973436ab6d71ccb927cb16f16f357041399e` with corrective code/docs/tests staged and checkpointed; it completed with 192 tests and `OK` in 82.988 seconds. The output is retained at `.agents/evidence/logs/pre-m3-corrective-full-suite-20261017.log` (SHA-256 above). Offline dependency validation used uv 0.9.26 / CPython 3.12.3 with `uv lock --check --offline`, resolved 18 packages, exit 0, no installation. The initial attempt to call `uv` by PATH failed because the executable was outside PATH; rerunning the same check through the existing user-local executable succeeded. No lockfile or dependency changed. Standalone agent preflight passed with only the expected ignored-artifact manifest warning; its sanitized output is also retained above.

The first M7-ownership regression-test iteration failed because its minimal synthetic repository had no canonical M7 G4/G5 allocation paragraph. The fixture root was corrected to use the canonical acceptance document; the subsequent focused run passed all 11 selected governance and data-contract tests. The later full-suite run passed all 192 tests, including the corrected fixture. No test was weakened. This initial diagnostic output was streamed rather than retained separately.

No M1/M2 source module or dependency lock was modified. No archive download/ingestion, Stockfish position search, supervised model training, Double DQN training, cloud allocation, release/publication, G3 approval, M3 authorization, default-branch change, or PR merge occurred.

### HC-01–HC-16 corrective acceptance checks

| Check | Status at this report revision | Evidence / limitation |
|---|---|---|
| HC-01 | PASS | G3/M3, G4/M6, and partial M7 gate-coverage checks are exercised against the canonical ADR/acceptance allocation. |
| HC-02 | PASS | Synthetic M3 direct authorization succeeds while G3 remains unapproved; Boolean-only and plan-only authorization fail. |
| HC-03 | PASS | State/backlog/ADR/M03 plan/acceptance references agree; G3 remains open and M3 pending. |
| HC-04 | PASS | Board-position signature is separate from replay/history-state identity. |
| HC-05 | PASS | Synthetic clock, repetition, castling, en-passant, and transposition vectors pass. |
| HC-06 | PASS | Candidate inheritance/purge and holdout-collapse failure test pass; release policy reports retention/distortion and fails below thresholds. |
| HC-07 | PASS | PGN-only and fake-teacher paths cannot satisfy current M3-02; real authorized Stockfish run remains required. |
| HC-08 | PASS | Played moves, teacher scores, simulator returns, and Q-values have separate types/meaning in research contracts. |
| HC-09 | PASS | RL-first Double DQN requirements, baselines, ablation and transfer criteria are documented; no training was run. |
| HC-10 | PASS | Source/game/fallback/sample/candidate/config/teacher/split/release identifiers have canonical SHA-256 vectors. |
| HC-11 | PASS | Archive/resource/resume/atomic-release design is documented; source-specific caps remain proposals pending a permitted profile. |
| HC-12 | PASS | No M1/M2 production code, dependency lock, accepted ADR, original roadmap, repository setting, or external service was changed. |
| HC-13 | PASS | Final local preflight and checkpoint pass; only the ignored-artifact manifest warning remains. |
| HC-14 | NOT VERIFIED | Full local suite passes; final pushed clean-clone recovery is pending. |
| HC-15 | NOT VERIFIED | Final pushed-HEAD GitHub Actions result is pending. Historical PR run 38944551579 is not evidence for this corrective HEAD. |
| HC-16 | PASS | No source acquisition, Stockfish search, training, paid/cloud use, release, G3 approval, M3 authorization, default-branch change, or merge occurred. |
