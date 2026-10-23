# Project Owner and External Decision Register

This register distinguishes project-owner technical decisions from external course policy, third-party rights, and operational availability. Owner decisions do not establish instructor rules or third-party rights. M3 source/teacher scope remains in `.agents/evidence/M3-authorization-20261020.md` and `.agents/evidence/M3-source-decision-20261020.md`; the 2026-10-23 owner decisions are recorded in the accepted ADR and [closure evidence](../../.agents/evidence/PRE-M4-final-closure-20261023.md).

M3-001 was accepted and merged in PR #3 on 2026-10-21. The accepted release is available in the owner's sibling M3 worktree and was read-only verified; see [M3 release verification](../../.agents/evidence/M3-release-local-verification-20261023.md). Its exact identity and local-only/no-redistribution boundary remain unchanged.

For M4, [ADR-0003](../02-management/decisions/ADR-0003-pretraining-model-interface.md) is accepted as the action-conditioned legal-candidate scorer and M5 shared-representation/Q-head interface. Acceptance does not approve G3, start M4, or establish implementation or performance. `M4-001` remains pending under its conditional authorization because external O-01 evidence is not in the repository.

## Approval priority for future work

The open items have different timing. This table classifies the first activity each one gates; it does not approve any activity.

| ID | Needed before | Can proceed while unresolved |
|---|---|---|
| **O-06** | Any new source, public release, or use beyond the exact owner-authorized local/internal May 2022 package. | Synthetic schemas and the already authorized bounded local dataset run. Third-party package rights remain unverified; do not upload or redistribute bulk records. |
| **O-01** | External course-policy evidence about the owner-selected ALE observation/action wrappers, custom PyTorch RL, behavior cloning, and any applicable teacher role. The owner’s technical choices are settled; no authoritative assignment brief or instructor response was found in this repository review. | Repository/readiness documentation, synthetic contract tests, and local read-only M3 verification. The conditional M4-001 record still requires external policy evidence before activation; no M4 training is authorized by this register. |
| **O-07** | Stockfish inference, engine-opponent use, offline engine evaluation, or teacher labeling beyond the bounded M3 run. | The owner-authorized 128-position Stockfish 19 M3 teacher run. |
| **O-03** | Any expansion of M4/M5 scope or duration that could displace Double DQN implementation and interaction. | The confirmed 2026-11-03 presentation date and bounded M3 implementation. Recalculate the remaining schedule before later work. |
| **O-04** | Paid/cloud compute or external storage; any processing/training exceeding verified local resource limits. GPU training needs a fresh entitlement/storage check. | Work within confirmed local disk/RAM/CPU caps; no paid or cloud allocation. |
| **O-02** | Final M6/ALE acceptance plan and fallback claim. | M3–M5 simulator experiments and ALE technical preparation that does not assert assignment acceptance. |
| **O-05** | M6 reported ALE configuration, mode/RAM assumptions, and gameplay/evaluation claims. | M3 data and M5 simulator tests; do not use unverified mappings for ALE actions. |
| **O-08** | Any Elo claim or calibrated rating comparison in M7. | Raw W/D/L and clearly named random/heuristic simulator comparisons without Elo. |

For the current M3 scope, the owner authorized bounded local/internal use of the selected source and bounded Stockfish 19 teacher analysis; the presentation date is 2026-11-03. The source-backed dataset and 128-position teacher sidecar were generated and verified on local CPU. The third-party package license remains unstated, so the archive and bulk derived records remain local and non-redistributable. Broader Stockfish roles, instructor-specific requirements, cloud/paid resources, and unrelated future decisions remain open. O-02/O-05/O-08 are later integration/reporting gates, not blanket blockers for M3 design.

## O-01 — External assignment and instructor policy

**OWNER-CONFIRMED:** The owner selected `ALE/VideoChess-v5`, custom PyTorch, Double DQN as the principal RL algorithm, a supporting M4 behavior-cloning stage, and bounded offline Stockfish teacher assistance. Stable-Baselines and Ray RLlib are excluded. Stockfish is not part of the learned-agent inference path. ADR-0003 was accepted by direct owner decision on 2026-10-23. These are project choices, not proof of course permission.

**EXTERNALLY VERIFIED:** No separate authoritative assignment/instructor document establishing or restricting wrappers, custom PyTorch, behavior cloning, or engine-assisted training was found among the repository's course/assignment materials. The project roadmap and owner decision ledger establish project intent only. Absence from this repository is neither approval nor prohibition.

**EXTERNAL CONFIRMATION PENDING:** The conditional M4-001 authorization requires an authoritative course brief or instructor response that addresses restrictions relevant to custom PyTorch RL, wrappers, behavior cloning, and any teacher role that will actually be used. The initial M4 behavior-only run excludes Stockfish; no inference, opponent, or offline engine benchmark is in scope. O-01 remains formally open until applicable external rules are evidenced. Do not ask the owner to reconfirm settled technical choices.

**Owner/action:** Provide the authoritative course/assignment policy source or an instructor response, then record only its actual restrictions. If the rules are silent, record that fact with the source and authority; do not infer a blanket permission beyond the documented scope.

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

**Remaining external fact:** O-01 determines whether the course permits custom PyTorch RL, behavior cloning, and engine-derived training/search roles. O-07 separately determines engine use limits. If those rules restrict a role, follow the restriction and report its effect; do not replace RL with imitation while claiming the assignment's central objective is met.

