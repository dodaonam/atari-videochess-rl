# Pre-M3 Owner Decision Register

This register summarizes remaining owner/instructor decisions and scoped confirmations. A scoped owner decision does not resolve broader assignment or external-rights questions. Current M3 confirmations are recorded in .agents/evidence/M3-authorization-20261020.md and .agents/evidence/M3-source-decision-20261020.md; live requirements retain unresolved portions.

## Approval priority for future work

The open items have different timing. This table classifies the first activity each one gates; it does not approve any activity.

| ID | Needed before | Can proceed while unresolved |
|---|---|---|
| **O-06** | Retrieving or ingesting any PGN/tactical source; retention or public release of its derived records. | Synthetic schemas, parser tests, and local design. This is the first required M3 source decision. |
| **O-01** | Any Stockfish training/search role, M4/M5 custom training if assignment rules are not already explicit, and M6 observation/action-wrapper work. | Source-free design; approved PGN-only data engineering if assignment scope permits; existing accepted M0–M2 work remains historical. |
| **O-07** | Any Stockfish label/analysis, engine opponent, or offline engine evaluation. It directly gates the real teacher run required to pass current M3-02. | PGN-only intermediate pipeline and fake-engine contract tests. |
| **O-03** | Choosing a feasible M3/M4/M5 scope, duration, and experiment priority. Resolve before selecting a larger tier; exact remaining deadline is not in evidence. | Small, bounded local preparation once other required permissions exist. |
| **O-04** | Paid/cloud compute or external storage; any processing/training exceeding verified local resource limits. GPU training needs a fresh entitlement/storage check. | Work within confirmed local disk/RAM/CPU caps; no paid or cloud allocation. |
| **O-02** | Final M6/ALE acceptance plan and fallback claim. | M3–M5 simulator experiments and ALE technical preparation that does not assert assignment acceptance. |
| **O-05** | M6 reported ALE configuration, mode/RAM assumptions, and gameplay/evaluation claims. | M3 data and M5 simulator tests; do not use unverified mappings for ALE actions. |
| **O-08** | Any Elo claim or calibrated rating comparison in M7. | Raw W/D/L and clearly named random/heuristic simulator comparisons without Elo. |

For the current M3 scope, the owner authorized bounded local/internal use of the selected source and bounded Stockfish 19 teacher analysis; the presentation date is 2026-11-03. Third-party package rights remain uncertain, and broader Stockfish roles, instructor-specific rules, cloud/paid resources, and unrelated future decisions remain open. The M3 authorization defines the exact limits. O-02/O-05/O-08 are later integration/reporting gates, not blanket blockers for M3 design.

## O-01 — Assignment and instructor permissions

**Owner-confirmed M3 scope:** The owner authorized bounded Stockfish teacher labeling for offline training in M3 and reiterates that Stockfish is forbidden in learned-agent inference. This does not establish instructor rules for all other activities.

**Remaining decision:** Confirm assignment/instructor rules for ALE observation extraction/action wrappers, custom PyTorch RL, and any offline engine evaluation. No authoritative course rule contradicting the M3 scope has been supplied in this session.

**Authority:** Instructor for assignment rules; project owner authorizes the scoped M3 project activity. **M3 impact:** The bounded M3 teacher operation is authorized by the owner record; follow any authoritative course rule if one is supplied that contradicts it. Other roles remain out of scope.

## O-06 — Data source, license, and use policy

**Owner decision:** The owner selected the Lichess Elite May 2022 package and authorized bounded internal academic research use with local retention and no redistribution. The exact decision is in .agents/evidence/M3-source-decision-20261020.md; this is not a public-rights grant or a legal determination.

**Verified source-page evidence (rechecked 2026-10-20):** The publisher describes standard games, excludes bullet, and says that from December 2021 it selected 2500+ versus 2300+ rated players. It lists May 2022 at 355,535 games/93 MB. The page links the zip but states no package license or checksum. The official Lichess database page states CC0 for official database exports; that statement does not establish terms for this third-party filtered package. These are publisher-reported figures, not local archive measurements.

**Remaining uncertainty:** The third-party package license and redistribution rights remain unstated/unverified. Actual bytes, PGN member, header distribution, and sample quality are unknown until bounded retrieval/profile.

**Boundary:** Process only within the owner-authorized local/internal research scope. Keep the original archive and bulk derived game records out of Git and do not upload or redistribute them. Stop if an explicit conflicting restriction is found. Seek separate evidence/authorization for public release or any new source/use. Official Lichess exports and CC BY-SA broadcast data are not selected; do not switch to the 28.8 GB official monthly archive without a new source-specific budget.

## O-07 — Stockfish version and role

**Owner-confirmed scope:** Stockfish 19 is selected and bounded offline teacher labeling is authorized for this M3 run. Engine use in inference is forbidden. Benchmark-opponent use and offline engine evaluation require separate authorization.

**Verified facts:** M0 recorded a manual Stockfish 19 Linux x86-64 executable SHA-256 of 0f83d24cc46d2c66c60f16001af5444873bc112b7d028594513426894c12da19 and GPL text SHA-256 of 3972dc9744f6499f0f9b2dbf76696f2ae7ad8af9b23dde66d6af86c9dfb36986. Both hashes were rechecked on the current host before analysis. Search caps and sample size are selected under this mission's measured local resource limits.

**Remaining uncertainty:** No instructor-specific course rule was supplied. Future host availability, opponent use, and offline benchmark use remain separate questions.

## O-04 — Compute and storage permissions

**Owner-confirmed M3 scope:** Use local CPU and local storage only. No Colab allocation, cloud upload/storage, or paid compute is used or authorized by this mission.

**Verified facts:** Before source retrieval, the host reported 40,886,706,176 bytes available on the repository filesystem, 31 GiB physical RAM, and 21 GiB available RAM. Workloads still require hard process and output caps. Colab quota/GPU availability and paid-compute entitlement are not verified.

**Remaining decision:** Recheck Colab quota and obtain separate authorization if a later milestone requires external resources; paid use remains a separate approval.

## O-03 — Remaining deadline and schedule

**Owner-confirmed deadline:** The presentation date is Tuesday, 2026-11-03, recorded in the M3 authorization evidence. As of 2026-10-20, 14 calendar days remain.

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

