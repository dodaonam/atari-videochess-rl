# Project Owner and External Decision Register

This register distinguishes project-owner technical decisions from external course policy, third-party rights, and operational availability. Owner decisions do not establish instructor rules or third-party rights. M3 source/teacher scope remains in `.agents/evidence/M3-authorization-20261020.md` and `.agents/evidence/M3-source-decision-20261020.md`; the 2026-10-23 ADR decision and 2026-10-27 O-01 decision are recorded in their dated evidence records.

M3-001 was accepted and merged in PR #3 on 2026-10-21. The exact accepted release is outside Git, available at the owner's specified sibling M3 worktree path, and was independently reverified read-only during Pre-M4 on 2026-10-27; see [the current local verification](../../.agents/evidence/M3-release-local-verification-20261027.md). Its exact identity and local-only/no-redistribution boundary remain unchanged; reverify all nine files before future use.

For M4, [ADR-0003](../02-management/decisions/ADR-0003-pretraining-model-interface.md) is Accepted as the action-conditioned legal-candidate scorer and M5 shared-representation/Q-head interface. The owner directly authorized M4-001 on 2026-10-27. The implementation measured 121,897 parameters. The exact release was verified and tensorized without modification. The original lexical-128 gate failed because identical inputs had conflicting labels, structurally capping legal top-1 below its threshold; that failed result remains historical. The dated PM amendment changed only the deterministic selector to distinct complete effective train inputs. The revised gate passed, all three bounded seeds completed, and validation NLL selected seed 20261024/epoch 11. The frozen test split was evaluated once; the checkpoint was reloaded with Stockfish absent; and the 40-game simulator protocol completed. M4-01–M4-04 and M4-001 are complete as recorded in the [M4 final acceptance report](../../.agents/evidence/M4-final-acceptance-20261027.md). G3 is not approved, and this evidence does not start or authorize M5.

## O-01 — Project-owner decision closed; external-policy status informational

**Decision authority and date:** Project owner, direct decision dated 2026-10-27.

**Decision:** O-01 is closed for internal project planning and execution authorization. The owner confirms the final project direction: ALE/VideoChess-v5 with the documented wrappers; independently implemented PyTorch Double DQN as the principal RL algorithm; bounded supporting behavior cloning; Stockfish 19 only within previously approved bounded offline teacher/pretraining assistance; no Stockfish inference. The initial M4 run remains behavior-only and excludes Stockfish scores and teacher targets. Stable-Baselines and Ray RLlib remain excluded.

**Supersession:** This decision supersedes the earlier O-01-specific requirement for another instructor/assignment response before M4-001 activation. The full historical authorization remains in [.agents/evidence/M4-001-authorization-conditional-20261023.md](../../.agents/evidence/M4-001-authorization-conditional-20261023.md), with a dated supersession addendum. No separate authoritative instructor-policy approval was found in the reviewed repository materials; this is an informational residual, not a readiness blocker or a claim of formal academic approval. If an actual authoritative course instruction explicitly contradicts an owner-selected activity, stop only the affected activity and record the concrete rule. See [owner decision evidence](../../.agents/evidence/O-01-owner-decision-20261027.md).

## Approval priority for future work

The open items have different timing. This table classifies the first activity each one gates; it does not approve any activity.

| ID | Needed before | Can proceed while unresolved |
|---|---|---|
| **O-06** | Any new source, public release, or use beyond the exact owner-authorized local/internal May 2022 package. | Synthetic schemas and the already authorized bounded local dataset run. Third-party package rights remain unverified; do not upload or redistribute bulk records. |
| **O-07** | Stockfish inference, engine-opponent use, offline engine evaluation, or teacher labeling beyond the bounded M3 run. | The owner-authorized 128-position Stockfish 19 M3 teacher run. |
| **O-03** | Any expansion of M4/M5 scope or duration that could displace Double DQN implementation and interaction. | The confirmed 2026-11-03 presentation date and bounded M3 implementation. Recalculate the remaining schedule before later work. |
| **O-04** | Paid/cloud compute or external storage; any processing/training exceeding verified local resource limits. GPU training needs a fresh entitlement/storage check. | Work within confirmed local disk/RAM/CPU caps; no paid or cloud allocation. |
| **O-02** | Final M6/ALE acceptance plan and fallback claim. | M3–M5 simulator experiments and ALE technical preparation that does not assert assignment acceptance. |
| **O-05** | M6 reported ALE configuration, mode/RAM assumptions, and gameplay/evaluation claims. | M3 data and M5 simulator tests; do not use unverified mappings for ALE actions. |
| **O-08** | Any Elo claim or calibrated rating comparison in M7. | Raw W/D/L and clearly named random/heuristic simulator comparisons without Elo. |

For the current M3 scope, the owner authorized bounded local/internal use of the selected source and bounded Stockfish 19 teacher analysis; the presentation date is 2026-11-03. The source-backed dataset and 128-position teacher sidecar were generated and verified on local CPU. The third-party package license remains unstated, so the archive and bulk derived records remain local and non-redistributable. Broader Stockfish roles, instructor-specific requirements, cloud/paid resources, and unrelated future decisions remain open. O-02/O-05/O-08 are later integration/reporting gates, not blanket blockers for M3 design.

## O-01 historical policy context (superseded for internal activation status)

**OWNER-CONFIRMED:** The owner selected `ALE/VideoChess-v5`, custom PyTorch, Double DQN as the principal RL algorithm, a supporting M4 behavior-cloning stage, and bounded offline Stockfish teacher assistance. Stable-Baselines and Ray RLlib are excluded. Stockfish is not part of the learned-agent inference path. ADR-0003 was accepted by direct owner decision on 2026-10-23. These are project choices, not proof of course permission.

**EXTERNALLY VERIFIED:** No separate authoritative assignment/instructor document establishing or restricting wrappers, custom PyTorch, behavior cloning, or engine-assisted training was found among the repository's course/assignment materials. The project roadmap and owner decision ledger establish project intent only. Absence from this repository is neither approval nor prohibition.

**Historical status through 2026-10-26:** The earlier conditional M4-001 authorization required external course-policy evidence and O-01 remained open at that time. The owner’s 2026-10-27 decision supersedes that internal activation condition; retain this text as decision history, not as an operative prerequisite. The external policy evidence remains unverified, and no formal instructor approval is claimed.

## O-06 — Data source, license, and use policy

**Owner decision:** The owner selected the Lichess Elite May 2022 package and authorized bounded internal academic research use with local retention and no redistribution. The exact decision is in .agents/evidence/M3-source-decision-20261020.md; this is not a public-rights grant or a legal determination.

**Verified source-page evidence (rechecked 2026-10-20):** The publisher describes standard games, excludes bullet, and says that from December 2021 it selected 2500+ versus 2300+ rated players. It lists May 2022 at 355,535 games/93 MB. The page links the zip but states no package license or checksum. The official Lichess database page states CC0 for official database exports; that statement does not establish terms for this third-party filtered package. These are publisher-reported figures, not local archive measurements.

**Remaining uncertainty:** The third-party package license and redistribution rights remain unstated/unverified. Retrieval facts, PGN member hash, source-scan counts, metadata coverage, sample quality, and holdout behavior are measured in [M3 execution evidence](../../.agents/evidence/M3-execution-20261020.md); those measurements do not resolve package rights.

**Boundary:** Process only within the owner-authorized local/internal research scope. Keep the original archive and bulk derived game records out of Git and do not upload or redistribute them. Stop if an explicit conflicting restriction is found. Seek separate evidence/authorization for public release or any new source/use. Official Lichess exports and CC BY-SA broadcast data are not selected; do not switch to the 28.8 GB official monthly archive without a new source-specific budget.

## O-07 — Stockfish version and role

**Owner-confirmed scope:** Stockfish 19 is selected and bounded offline teacher labeling is authorized for this M3 run. Engine use in inference is forbidden. Benchmark-opponent use and offline engine evaluation require separate authorization.

**Verified facts:** M0 recorded a manual Stockfish 19 Linux x86-64 executable SHA-256 of 0f83d24cc46d2c66c60f16001af5444873bc112b7d028594513426894c12da19 and GPL text SHA-256 of 3972dc9744f6499f0f9b2dbf76696f2ae7ad8af9b23dde66d6af86c9dfb36986. Both hashes were rechecked on the host. The bounded M3 run analyzed 128/128 selected positions with one thread, Hash 64 MiB, MultiPV 3, 5,000 nodes and 30 seconds maximum UCI movetime per root; it produced 377 centipawn and 3 mate lines with no failed positions. Full run identity and score semantics are in [M3 teacher evidence](../../.agents/evidence/M3-teacher-manifest-r2-20261020.json).

**Remaining uncertainty:** No instructor-specific course rule was supplied. Future host availability, opponent use, and offline benchmark use remain separate questions.

## O-04 — Compute and storage permissions

**Owner-confirmed M3 scope:** Use local CPU and local storage only. No Colab allocation, cloud upload/storage, or paid compute is used or authorized by this mission.

**Verified facts:** Before source retrieval, the host reported 40,886,706,176 bytes available on the repository filesystem, 31 GiB physical RAM, and 21 GiB available RAM. Workloads still require hard process and output caps. Colab quota/GPU availability and paid-compute entitlement are not verified.

**Remaining decision:** Recheck Colab quota and obtain separate authorization if a later milestone requires external resources; paid use remains a separate approval.

## O-03 — Remaining deadline and schedule

**Owner-confirmed deadline:** The presentation date is Tuesday, 2026-11-03, recorded in the M3 authorization evidence. Fourteen calendar days remained on 2026-10-20; thirteen remain as of 2026-10-21. M3 was kept to a 1,000-game / 20,000-position support dataset and a 128-position teacher subset so M5 can start promptly.

**Remaining uncertainty:** Any earlier course checkpoint or reporting deadline is not separately recorded. Keep M3 data and teacher scope small so M5 Double DQN receives priority; reconfirm only if the owner or instructor changes the date.

## O-02 — Actual ALE performance requirement and fallback

**Decision needed:** Confirm whether full-game performance on actual ALE is a hard submission requirement or whether a documented integration/throughput failure can be an accepted research fallback.

**Verified facts:** The roadmap targets actual Atari Video Chess behavior and describes a simulator fallback if integration fails. M1 has real RGB/control and terminal evidence, but no learned policy has been integrated or evaluated.

**Uncertainty:** The instructor's acceptance threshold, required game-completion rate, and fallback criteria are not recorded.

**Options / recommendation:** Preserve complete-game ALE evaluation as the target. Ask the instructor to define the minimum acceptable real-ALE evidence and fallback claim; report a fallback only as a limitation and never relabel simulator results as Atari performance.

**Authority:** Instructor for grading requirements; project owner records the decision. **M3 impact:** None for bounded source/data design; this constrains M6 and final claims.

## Repository strategy — default branch and integration

**Decision needed:** Decide whether GitHub's default branch should move from main to initial-idea after this readiness review.

**Verified facts:** main is at the original commit c410173; it is an ancestor of initial-idea and 26 commits behind the merged M2 integration tip. PR #1 merged into initial-idea. GitHub currently defaults to main. No open PR overlaps this mission.

**Options:** Keep main intentionally reserved and require explicit initial-idea clone/PR instructions; or make initial-idea the default integration branch and later promote reviewed releases into main.

**Recommendation / trade-off:** If initial-idea is the active integration branch, set it as default after PM review so the landing page, default clone, and new PR discovery expose the maintained code. Retaining main as default avoids a repository setting change but creates a stale first impression and requires branch-explicit instructions.

**Authority:** Repository owner. **M3 impact:** Does not block code work if all PRs explicitly target initial-idea. No branch setting or merge was changed.

## Repository licensing — no top-level LICENSE

**Decision needed:** Select a public license for project-authored code and determine whether any course/instructor requirements apply.

**Verified facts:** The repository is public and has no top-level LICENSE. Stockfish is GPL-3.0 and is intentionally kept outside Git. Dataset source terms are a separate decision and must not be conflated with a code license.

**Uncertainty:** Owner intent for code reuse, course constraints, and whether all repository material can be licensed uniformly.

**Options:** Add a permissive license, use a copyleft license, or leave the repository without a public code license until a decision is made.

**Recommendation / trade-off:** Keep the current no-license state until the owner confirms intent and instructor requirements. This avoids making an unauthorized grant but means the repository should not imply unrestricted code reuse.

**Authority:** Project owner, with instructor confirmation if the assignment has a required license. **M3 impact:** Does not block private/local experimentation; publication/reuse notices remain unresolved. No LICENSE file was added.

## PM-directed research alignment — RL-first hybrid

**Decision status:** The current PM instruction sets Double DQN as the principal course objective and explicitly subordinates PGN/Stockfish work to RL. That technical priority is applied in [RL_FIRST_ALIGNMENT.md](RL_FIRST_ALIGNMENT.md); it does not resolve instructor permissions or authorize future milestones.

**Resolved for planning:** If M4 is authorized and time permits, use a small played-move behavior-cloning baseline with its own checkpoint. Keep policy logits distinct from Q-values. Transfer only compatible shared layers as a measured hypothesis, retain random-initialized Double DQN where feasible, and reserve the main experiment budget for simulator reward-interaction training and a controlled RL ablation. Do not add outcome auxiliary tasks, broad PGN expansion, or exhaustive teacher labels without evidence of benefit.

**Sequencing refinement:** The original [ROADMAP.md](../01-foundation/ROADMAP.md) remains unchanged. M5 core implementation/training depends on M3 and M2 interfaces, not on completing M4 first; this prevents a supervised-only checkpoint from delaying the course's central RL work. A small pretraining-only checkpoint remains required by current M5-04 for the final paired comparison. It can follow DDQN implementation and its first sanity run. If project constraints make that baseline infeasible, revise the canonical acceptance criterion before claiming M5 complete. This planning refinement is directed by the PM and does not authorize either milestone.

**Informational external-policy uncertainty after internal closure:** No authoritative course rule establishing or prohibiting the selected custom PyTorch RL, behavior-cloning, or wrapper scope was found in reviewed repository materials. The owner closed O-01 for internal execution; this absence is not a readiness blocker and is not formal course approval. O-07 continues to govern engine roles outside the previously authorized bounded M3 teacher run and initial M4 behavior-only protocol. Follow any actual explicit prohibition and report its effect; do not replace RL with imitation while claiming the assignment's central objective is met.

