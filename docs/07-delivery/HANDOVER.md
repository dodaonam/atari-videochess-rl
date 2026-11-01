# Technical and Research Handover

**Repository:** https://github.com/dodaonam/atari-videochess-rl

**Integration branch:** initial-idea

**M7-004 integration:** 0f45fa06c235658da48d3d41a9091c06580bfe27 (PR #19 merge)

**Current status:** M7-001 through M7-005 are complete as engineering tasks on the M7-005 submission branch. G4 is approved with scientific limitations; G5 remains NOT APPROVED pending Independent PM review. The owner disposition is NO RELEASE / NO PUBLICATION AUTHORIZED.


## Project overview and governance

The project built a legal-action-conditioned supervised behavior model (M4), trained custom Double DQN policies in the M2 chess simulator (M5), integrated frozen policies with ALE RGB and cursor control (M6), then ran and analyzed the frozen Option B ALE comparison (M7 Phase I). The evidence does not establish strong chess play, Atari RL superiority, equivalence, broad generalization, Elo, or satisfaction of academic requirement O-02.

The canonical status is in .agents/state/PROJECT_STATE.yaml and .agents/tasks/BACKLOG.yaml. The M7-004 submission snapshot recorded M7-005 as pending and unstarted; that point-in-time statement is superseded by the M7-005 closeout update below. G0–G4 are approved in canonical state; G4 is specifically APPROVED WITH SCIENTIFIC LIMITATIONS for M7-01 through M7-03. G5 is NOT APPROVED. The original owner authorization M7-AUTH-20261031-OPTION-B remains unchanged and is retained separately from the new M7-005-only authorization.

## M7-005 closeout update — 2026-11-01

The Project Owner directly authorized M7-005 and selected **NO RELEASE / NO PUBLICATION AUTHORIZED**. The decision, artifact-by-artifact disposition, acceptance evidence, verification record, and G5 review request are linked from [M7-005 acceptance](../../.agents/evidence/M7-005-acceptance-20261101.md), [release disposition](RELEASE_DISPOSITION.md), and [G5 review handover](../../.agents/evidence/M7-G5-review-handover-20261101.md). M7-005 is complete at the engineering level on its feature branch. This does not approve G5, merge the PR, or authorize a release. The next action is Independent PM review of the M7-005 PR and an explicit G5 decision.

Independent PM source: [G4 acceptance record](../../.agents/evidence/G4-PM-acceptance-20261101.md), [source decision comment on PR #17](https://github.com/dodaonam/atari-videochess-rl/pull/17#issuecomment-6552570969), and [PR #17 merge](https://github.com/dodaonam/atari-videochess-rl/pull/17) at 2bca79001ed94324b725dce2dfdc485e3a51ad3e. PR #18 integrated that decision and canonical closeout at d7332b91128d3daf919421db2e71a9f2ee4b48ec.

## Canonical sources of truth

| Information | Canonical source |
|---|---|
| Requirements and unresolved owner/course questions | docs/01-foundation/REQUIREMENTS.md |
| Research/engineering roadmap | docs/01-foundation/ROADMAP.md |
| G/M crosswalk and engineering sequence | ADR-0001 and docs/02-management/EXECUTION_PLAN.md |
| Acceptance conditions | docs/06-quality/ACCEPTANCE_CRITERIA.md |
| Current gate, milestone, task pointer, checkpoint | .agents/state/PROJECT_STATE.yaml |
| Task IDs, dependencies, status, evidence | .agents/tasks/BACKLOG.yaml |
| Blockers and verified findings | .agents/state/BLOCKERS.md and VERIFIED_FINDINGS.md |
| Session recovery pointer | .agents/state/SESSION_HANDOFF.md |
| Accepted experimental results | Dated M3–M7 acceptance/evidence records and accepted reports linked below |
| Frozen M7 execution configuration | configs/m7/m7-option-b-1.0.0.json |
| Private artifact payloads | Owner-controlled local artifact stores; hashes/manifests in evidence |

Older narrative documents can preserve point-in-time status. Resolve current status through canonical state and its provenance, not by editing historical acceptance records.

## Evidence and artifact inventory

| Identity | Purpose | Visibility and owner | Integrity / access |
|---|---|---|---|
| M3 accepted final dataset r6/r7, release f10a679deddf06f3e1e3c39cf58db4e21176629c26c09034a271bf278189e890 | Accepted final source-derived positions | Private local data; Project Owner controls access | Matching manifest SHA-256 be1e1f9316fac01be893774cfe09a313de193fbd1a12ab2d219ff5c041104a12; [final-closure record](../../.agents/evidence/M3-final-closure-record-20261021.json) and [M3 acceptance](../../.agents/evidence/M3-acceptance-20261021.md); source license unverified; no redistribution |
| M3 accepted final teacher-r1, run 58febd814bb6bdd6fa67b990a1e4906ada14c31fafa265829fb49b7d3c203272 | Accepted final teacher labels for the r6/r7 dataset | Private local data/sidecars; Project Owner controls access | Bound to release f10a679deddf06f3e1e3c39cf58db4e21176629c26c09034a271bf278189e890 and dataset manifest be1e1f9316fac01be893774cfe09a313de193fbd1a12ab2d219ff5c041104a12; [final-closure record](../../.agents/evidence/M3-final-closure-record-20261021.json); no redistribution |
| M3 historical corrective r4/r5 and teacher-r2 | Superseded provenance generation; not the accepted final dataset or teacher | Private historical artifacts; Project Owner controls access | Dataset release 7b51ec3761ad28aa7a2882691b3c314d35115ab339769251ff2556e706a5b1d9 / manifest 77e217423e187278c584b8f566a846fd606bddaadad19179b7bef63959bd5abe; teacher run ba4a109064e05ac5d0ec966892745f04fefea014faa8287d977e94fc5f685826; [corrective release and teacher evidence](../../.agents/evidence/M3-corrective-hardening-20261021.md); no redistribution |
| M4 run m4-behavior-20261027-r4 | Accepted behavior-only checkpoint | Private checkpoint/sidecar; Project Owner | Checkpoint 724ac730f3c5f2d01b48b26eb7670a3c764978a3dd4d6702b3057a99ab1a90a4; root f00fde1c59325105e0ffd45bb45eb269dfa303416010c9a0b6c6be47bd9a9921 |
| M5 six paired runs | Warm/Scratch post-RL checkpoints and simulator rows | Private; Project Owner | Root manifest a201a254671ad59ae1fecb402abf994d5bf523097f1c3010b5c7fa237ae6dd4c; per-checkpoint hashes in MODEL_CARD.md and M7-001 evidence |
| M6 v1 | Stage 3 integration evidence | Private raw traces; committed report/hash summaries | Run m6-stage3-ad3998200e31-c5ff389dc4fe; root 22ac6ec7e0f4a48f52b2452654d4adecaf111f38ea37f5d9517f173c838716d7 |
| M6 v2 | Separate extended-horizon integration evidence | Private raw traces; committed report/hash summaries | Run m6-stage3-v2-91f51b14690e-d05d42400cfc; root bc0068aa2254e4c15165247ee299f48940cca9b7c21f6a288fd13812631ea2b2; PM6-F06 erratum retained |
| M7 Option B | Nine policies × ten shared ALE seeds | Private ROM, checkpoints, raw RGB, ledgers; owner-local | Run m7-option-b-20261031-v1-8387b289432f; config 8ec8a42a808f4ffc410c938b4400d02461f96823eb5ac1b16cbd6e0d5e35f255; raw root 25a8b6bcfbf1d948bed886a0a4964cf48210fb1be12809c72bf122157b8d05e4 |
| M7 analysis bundle | Committed report, tables, plots, manifest | In repository; sanitized derived output | Bundle manifest SHA-256 af084e1cd99a6541c19cad2a1dfa163129a3cb873c393ec3669711e5d7b4ffa1; based on analysis source fe2cc4cc5e477841ffbc9368235eb9c5675f2f74 |
| M7-004 evidence inventory | Claim-to-source map, committed-source hashes, private manifest-verification identities | In repository; sanitized metadata only | [Inventory JSON](../../.agents/evidence/M7-004-evidence-inventory-20261101.json); failure history preserved separately |

Committed hash identities do not mean payloads are included in Git. Do not copy private artifact paths into public discussions or attempt to obtain artifacts from unapproved sources.

## Completed research and engineering

The canonical backlog records M0 through M6 and M7-001/002/003 engineering tasks as done. Gate approvals are separate: only G0–G4 are approved in current state; do not infer that every milestone has a separate PM gate approval.

- **M3:** accepted bounded source/release and teacher-provenance work; third-party dataset license remains unstated/unverified.
- **M4:** accepted supervised imitation model; 29.8979% legal top-1 and 54.3996% legal top-3 on 2,057 test positions. These are not game-strength metrics.
- **M5:** six Double DQN simulator runs and 1,500-row evaluation; three paired training seeds; RSK-014 remains.
- **M6:** separate v1 and v2 ALE records. V2 had 11 terminal losses and nine incomplete attempts; PM6-F06 remains an immutable metadata erratum.
- **M7-001/002/003:** accepted Option B schedule, raw-derived analysis, and formal Elo non-reportability. G4 acceptance is bounded and does not validate strong gameplay.
- **M7-004:** engineering deliverables for M7-04 are complete and mapped in the [acceptance record](../../.agents/evidence/M7-004-acceptance-20261101.md). Independent PM review remains pending.

## M7 result summary and limitations

M7 scheduled, started, and reset-observed all 90 policy × evaluation-seed cells. Outcomes: 60 terminal White losses, 30 incomplete, zero wins, draws, terminal-unknown, ALE truncations, and not-started attempts. One policy had no terminal outcomes; its terminal-only score is undefined. Incomplete attempts are not draws.

There were 1,670/1,670 valid legal selections, 1,581/1,670 RGB-verified initiated moves, 1,581 verified replies, zero recorded board desynchronizations, and 7,225 cursor corrections. Only 9/30 Warm/Scratch matched cells had terminal outcomes; paired confidence interval unavailable. M7 used White only, one built-in ALE opponent, and an extended horizon rather than ALE's registered default. No Elo is reported.

## Open risks and decisions

| Item | Current disposition |
|---|---|
| O-02 | Open: whether full-game ALE performance is a hard submission criterion or a research target with an accepted fallback |
| O-05 | Open: ALE/ROM behavior, mode/difficulty semantics, and official evaluation settings beyond verified runtime evidence |
| O-06 | Open: broader redistribution rights; M3 source license remains unverified |
| O-07 | Open: Stockfish roles beyond the already bounded teacher-label scope |
| O-08 | Open: opponent pool and rating method for any future Elo |
| RSK-014 | Accepted M5 residual provenance limitation; byte-identical source across all historical runs is not established |
| PM6-F06 | Accepted M6 v2 metadata erratum; original evidence remains immutable |
| M7 limitations | Censoring, one opponent, White-only, three training-seed pairs, controller uncertainty, and private raw artifacts |
| G5 / M7-005 | M7-005 engineering complete; G5 not approved and pending Independent PM review; no release/publication authorization |

O-03 and O-04 are also tracked in canonical requirements/state. Course expectations and resource authorization must not be inferred from prior experiment settings.

## Reproduction and handover checklist

- [ ] Read AGENTS.md, REQUIREMENTS.md, current PROJECT_STATE.yaml and BACKLOG.yaml.
- [ ] Run scripts/agent_preflight.py and review warnings as well as errors.
- [ ] Verify the branch/commit and inspect the complete diff before changes.
- [ ] Review M7-001/002/003 acceptance records, G4 acceptance, frozen config and analysis manifest.
- [ ] Obtain explicit Project Owner access before reading private checkpoints, ROM, raw RGB, datasets, or ledgers.
- [ ] Run only read-only manifest tools for integrity checks; do not invoke manifest-creation mode on frozen roots.
- [ ] Treat M7 campaign and M5 simulator evaluation commands as experiment runners, not setup commands.
- [ ] Stop on any identity mismatch. Preserve the log and request owner/PM disposition; do not regenerate artifacts.
- [ ] Keep private data outside Git and do not publish model/data/ROM artifacts.

## Roles, next action, and release boundary

- **Engineering Executor:** Codex; responsible for traceable implementation and verification.
- **Independent Project Manager:** ChatGPT; responsible for independent review and gate disposition.
- **Project Owner:** Nam; owns scope, artifact access, and any future release authorization.

G5 is not approved. M7-005 is complete as engineering work and awaits Independent PM review. No public model, dataset, ROM, raw trace, or private artifact release is authorized. The next action is Independent PM review of the M7-005/G5 package and exact PR HEAD. Do not treat this handover as G5 approval or permission to publish.

## Delivery revision

The M7-004 delivery snapshot was submitted in PR #19 and merged at `0f45fa06c235658da48d3d41a9091c06580bfe27`. The current M7-005 PR metadata and acceptance record identify the separate feature HEAD, base revision, checks, and CI result. The M7-005 PR remains open and unmerged pending Independent PM review.
