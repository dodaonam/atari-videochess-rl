# Pre-M7 Engineering Readiness Plan and Assessment

**Status:** Pre-M7 preparation only; G4 remains unapproved and M7 remains unauthorized.
**Reviewed source baseline:** `fa7683822c436f3e9d6c3455a24cd1f4a6cbb463` (`initial-idea`, PR #15 merge).
**Assessment date:** 2026-10-31.
**Purpose:** prepare a reproducible evaluation and handover package for independent PM review. This document does not approve G4/G5 or authorize M7.

## 1. Verified baseline and governance

The live GitHub records and local merge graph agree:

| Item | Verified identity / status |
|---|---|
| PR #14 | Merged 2026-10-31 05:55:49Z; merge `509f9f83f9249208fd5adba572efed2d2f0f82ff`; accepted feature head `e919ee3ad039c9d2de3ebdf6b82704ecd61c0a6f`; merge tree equals accepted tree `7eb06fd9c0e0b363ca324d203e1debf26f233c08`. |
| PR #15 | Merged 2026-10-31 11:18:30Z; exact reviewed branch head `b0d4a1303d2a639e164a9b9fb103bb442d366f1d`; merge `fa7683822c436f3e9d6c3455a24cd1f4a6cbb463`. |
| Current base | `initial-idea` at `fa7683822c436f3e9d6c3455a24cd1f4a6cbb463`, the requested baseline. |
| Governance | G0–G3 approved. The initial independent PM G4 assessment is HOLD because evaluation evidence is incomplete. G4 and G5 are not approved. |
| Engineering | M6 and M6-001 are done and PM-accepted. M7 is not started; `start_authorized=false`; authorization record is null. |

PR #14 acceptance is recorded in [M6 PM acceptance](../evidence/M6-001-PM-acceptance-20261031.md). PR #15's PM6C-F01 provenance correction and exact review are in [the M6C-F01 record](../evidence/M6C-F01-provenance-correction-20261031.md). The final PM review accepted PR #15 at `b0d4a130…`; the merge is `fa768382…`. Historical PR #15 review-stage failures remain documented and superseded by the successful final audit, focused/full suites, preflight, and exact-head CI cited in the closeout record.

The initial working directory was an older, dirty Pre-M4 checkout. It was not changed. Preparation uses a separate clean worktree and branch created at the verified PR #15 merge baseline.

## 2. Evidence audit summary

The read-only machine record is [the input integrity audit](../evidence/PRE-M7-input-integrity-20261031.json). The new M6 raw audit report is [PRE-M7 M6 audit](../evidence/PRE-M7-M6-readonly-audit-20261031.json). Local-only artifact bytes remain outside Git and this PR.

### M4 supervised pretraining

- Accepted run: `m4-behavior-20261027-r4`; source `7b3c9074a2d932fec6d7732ee08e99b9de10a135`.
- Accepted M3 release ID `f10a679deddf06f3e1e3c39cf58db4e21176629c26c09034a271bf278189e890`; release manifest SHA-256 `be1e1f9316fac01be893774cfe09a313de193fbd1a12ab2d219ff5c041104a12`.
- M4 artifact manifest SHA-256 `f00fde1c59325105e0ffd45bb45eb269dfa303416010c9a0b6c6be47bd9a9921`; selected `pretrained-behavior-only.pt` SHA-256 `724ac730f3c5f2d01b48b26eb7670a3c764978a3dd4d6702b3057a99ab1a90a4`; metadata SHA-256 `63615d8d0ed27900fdf86d3f3084ca95cd562f9ec2f9a7e94bca4b0f6301e0c8`. The selected checkpoint is from training seed `20261024`, epoch 11, selected by validation NLL across three training seeds.
- The r4 private run directory and all 19 files passed `verify-artifacts` read-only in this session. The recorded checkpoint and manifest hashes match.
- Frozen held-out test: 2,057 positions, legal top-1 `29.8979%`, legal top-3 `54.3996%`, MRR `0.46437`. This is historical-move imitation agreement, **not** game score, win rate, chess strength, RL improvement, or ALE performance.
- Dataset/model contracts: `videochess-model-input/1.0`, `videochess-behavior-scorer/1.0`; 121,897 trainable parameters. The output is a behavior logit, not a Q value.

### M5 simulator Double DQN

- Six accepted runs: Warm-start and architecture-matched Scratch, three paired training seeds (`20261104`, `20261105`, `20261106`), 50,000 valid decisions per run (300,000 total), 12,245 updates and 24 target synchronizations per run.
- The accepted configuration SHA-256 is `84d305084397ad18397dfe395fab58de824fa056729675d0d1cd9ca8bdd06d8d`; the accepted root artifact manifest is `a201a254671ad59ae1fecb402abf994d5bf523097f1c3010b5c7fa237ae6dd4c`. The seven run manifests and 6,544,747,450 listed bytes passed the read-only M5 verifier in this session.
- Warm/Scratch final snapshots, one pair per training seed, are identified in the M5 training verifier and root manifest. The v2 ALE roster selected only the predeclared seed-20261104 pair: Warm `0b2405017a8e1d539851f0cd278883d3fd23936fb5c2f7962c813590a6fd1767`; Scratch `3749b0c0b6ae44d3ad5d6bf0863b60937a59fbe881e0bdf4932bdce6033ca400`.
- The frozen simulator evaluation covered 15 policy groups and 1,500 scheduled rows: 25 evaluation seeds (`20261130`–`20261154`), two non-engine opponents (RandomLegal and SimpleHeuristic), and both agent colors. There were 1,494 terminal games and six 400-decision time-limit truncations. Truncations are not terminal draws.
- The accepted report found Warm-start post-minus-pre terminal score `+0.296` and Scratch `+0.185`; the primary terminal-only matched estimates for Warm-minus-Scratch were `−0.056` pre-RL and `+0.062` post-RL. The four campaign-level primary comparisons have no bootstrap interval because censoring leaves unmatched pairs. A clearly post-hoc capped-reward sensitivity reported intervals, including Warm-minus-Scratch post-RL `95% CI [−0.003, 0.118]`; it is not the primary analysis. Three training-seed pairs limit precision. The 1,500 game rows are not 1,500 independent training replications.
- **RSK-014 remains a PM-accepted historical source limitation:** complete historical `cli.py` bytes and byte-identical whole-campaign source reproduction are not established. The recovered `checkpoint.py` and `replay.py` evidence narrows the risk but does not erase it or prove source homogeneity.
- M5 evidence is exclusively M2 simulator evidence. It does not establish Atari performance.

### M6 Atari integration and evaluation

- M6-01–M6-05 were accepted by the independent PM. The PM reviewed reports/logs but did not personally rehash the raw private ALE trees or rerun the Python suite; those are executor verification records, not PM-executed checks.
- Stage 3 v1 and v2 are separate immutable protocols. V1 used config schema `videochess-m6-stage3-config/1.0`, five frozen policy groups, 35 scheduled attempts, a 54,000 ALE-frame episode limit, 900 seconds per attempt, and a 36,000 second shared diagnostic/evaluation budget. V2 uses config SHA-256 `663651050db80ab027b452241c7d39837ec7986927c0aefc7c7be631f459a49b`, protocol `M6-Stage3-v2-extended-horizon-frozen-m5`, two frozen policies, 20 attempts, 500,000 ALE frames, 432,000 post-reset runner frames, 1,800 seconds per attempt, and a separate 43,200 second v2-only budget. Both used `ALE/VideoChess-v5`, White, mode 4, difficulty 0, RGB, frameskip 4, and repeat-action probability 0.25.
- The read-only audit in this session verified the preserved v1 and v2 raw trees. V1: 4,540 files / 616,539,017 manifest bytes; run `m6-stage3-ad3998200e31-c5ff389dc4fe`; root artifact-manifest SHA-256 `22ac6ec7e0f4a48f52b2452654d4adecaf111f38ea37f5d9517f173c838716d7`. V2: 4,159 files / 728,148,524 bytes; run `m6-stage3-v2-91f51b14690e-d05d42400cfc`; root manifest SHA-256 `bc0068aa2254e4c15165247ee299f48940cca9b7c21f6a288fd13812631ea2b2`.
- V2 reuses v1's ten ALE seeds (`20261130`–`20261139`) with an extended horizon. Its paired frozen M5 policies are the seed-20261104 post-RL Warm/Scratch snapshots above. This is not a new held-out ALE seed set or evidence across independent training seeds.
- The audit rederived 20 scheduled attempts: 11 ALE-terminal White losses, zero terminal wins/draws, and 9 incomplete attempts (5 opponent-response timeouts, 2 source-selection uncertainty stops, 2 target-navigation uncertainty stops). Incomplete attempts are not draws. The primary move result is 385 RGB-verified initiated moves / 405 initiated moves (95.06%); 385 Atari replies; zero board desynchronizations; 1,871 unexpected cursor displacements, all corrected; zero resource stops. These are closed-loop/controller observations, not demonstrated strong Atari chess skill or Warm/Scratch superiority.
- The immutable PM6-F06 metadata inconsistency remains documented with its erratum. The raw v2 manifest and historical result were not rewritten. The separate PM6C-F01 closeout correction binds the final report/log provenance to committed files.
- The verified raw M6 roots are local-only under `artifacts/m6-preserved-20261031/{v1,v2}/...` in the original workspace. The clean Pre-M7 worktree does not contain them; the read-only verifier accessed the preserved roots directly. No raw RGB, ROM, checkpoint, data, or credential was copied into this branch, Git, or a remote.

## 3. Readiness assessment

This is an engineering readiness assessment, not G4 approval. The findings above support reuse of accepted records without rerunning an official campaign. G4 remains on HOLD until the independent PM decides whether the bounded accepted evidence plus the limitations and proposed additional-evaluation branch are sufficient for the academic conclusion. G5 remains out of scope.

| PM7 acceptance | Assessment at preparation close |
|---|---|
| R01 source and PR integration identities | Verified against local Git objects and live GitHub PR #14/#15 records. |
| R02 accepted and unauthorized states | Preserved: G0–G3 approved, M6 done, G4/G5 unapproved, M7 pending and unauthorized. |
| R03 M4/M5/M6 inventory and provenance | Reconciled; M4/M5 private manifests and M6 v1/v2 raw trees passed read-only integrity checks. RSK-014 and PM6-F06 remain explicit historical qualifications. |
| R04 evidence tracks | Protocol and assessment distinguish supervised imitation, M2 simulator RL, and ALE closed-loop results. |
| R05 valid comparisons | Environment, checkpoint, protocol, opponent, seed, color, and denominator rules are specified; v1/v2 and simulator/ALE are not pooled. |
| R06 uncertainty and incomplete data | Paired design, training/evaluation seed clustering, terminal/truncated/incomplete status, censoring, runtime, and controller denominators are defined. |
| R07 Elo | Optional only under a calibrated, owner-approved opponent pool and explicit uncertainty requirements; otherwise prohibited. |
| R08 resources, privacy, and owner decisions | Bounded proposal and local capacity snapshot are recorded. No cloud or paid resources were allocated. |
| R09 plan and backlog | Five pending M7 task records map to M7-01–M7-05 and keep G4/G5 ownership distinct. |
| R10 tests and preflight | Final run identities/results are in the verification section of the companion evidence report. |
| R11 experiment immutability | No accepted run, checkpoint, raw evidence, config, or frozen manifest was modified. Only new Pre-M7 documents, tests, state pointers, and audit records are proposed. |
| R12 PM review handoff | One open Pre-M7 PR will target `initial-idea`; no self-approval or merge. |

The exact execution times, exit codes, source revisions, sanitized logs, and manifest checksums are recorded in [the readiness evidence](../evidence/PRE-M7-readiness-20261031.md) and linked machine records. Any test failure is retained with its remediation rather than removed or relabeled.

## 4. Owner decisions that remain

These are decisions of project owner/instructor or independent PM authority. Recommendations below are proposals, not approvals.

| Decision | Proposed default | Tradeoff / reason |
|---|---|---|
| Independent PM G4 disposition | Review this package and explicitly decide G4; leave it unapproved until that review. | Accepted evidence is real but bounded; ALE outcomes are 11 losses and 9 incomplete attempts. This review cannot be inferred from this PR or its CI. |
| Direct M7 start authorization and final protocol approval | Require a separate direct owner record after G4 disposition; authorize only the reviewed evaluation scope. | Prevents preparation or PM readiness review from starting M7. |
| O-02 full-game ALE requirement vs disclosed fallback | Keep ALE as the stated target; if infeasible, report the accepted M6 operational evidence and explicit performance limitation rather than silently waive the target. | Requires owner/instructor direction for any academic fallback. |
| O-04 compute and storage | Prefer local CPU for any authorized bounded evaluation; use no Colab or paid resources unless entitlement, quota, privacy, and a new resource envelope are separately verified and approved. | ALE is serial and controller/CPU-bound in prior measurements; current Colab entitlement is unknown. |
| O-05 official ALE settings | Reuse the precisely identified M6 v2 profile only after the owner confirms it is the accepted evaluation profile; do not interpret v2 as registered-default ALE settings. | V2 intentionally used a 500,000-frame horizon vs the registered 108,000-frame default. |
| O-08 Elo opponent pool and rating | Do not report Elo unless a calibrated pool and rating plan are explicitly approved; never assume 1500 Elo. | Current RandomLegal/SimpleHeuristic simulator opponents and one ALE built-in opponent are not a calibrated rating pool. |
| G5 delivery/release scope | Prepare private, evidence-linked draft artifacts only after G4; publish or distribute nothing without separate owner authorization. Keep source data, ROM, raw RGB, and private checkpoints local. | Existing dataset redistribution rights are unresolved; report/model-card delivery does not itself authorize asset distribution. |
| Delivery date | Preserve the recorded 2026-11-03 presentation date unless the owner/instructor changes it. | A new 90-attempt ALE block has a 45-hour worst-case allowance and is not a safe deadline assumption. |

## 5. Review path

Independent PM: review the evidence matrix, protocol and G4/G5 mapping; decide whether G4 readiness is sufficient or identify a specific evidence gap. The PR is not an M7 authorization request. Project owner: after PM disposition, separately authorize or decline M7-001, approve or revise the protocol/resource envelope, and resolve only the decisions above that affect the selected scope. No M7 task starts from this package alone.
