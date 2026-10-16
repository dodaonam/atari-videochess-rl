# Pre-M3 Owner Decision Register

This register summarizes decisions still owned by the project owner or instructor. A recommendation does not change the canonical approval status. O-01 through O-08 remain open in [REQUIREMENTS.md](../01-foundation/REQUIREMENTS.md). Independent design and repository work may continue where stated below.

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

O-06 and the applicable portion of O-01/O-07 are the direct M3 gates. O-03 should be resolved early to keep the dataset and teacher scope proportionate. O-04 is conditional on storage/compute tier. O-02/O-05/O-08 are later integration/reporting gates, not blanket blockers for M3 design.

## O-01 — Assignment and instructor permissions

**Decision needed:** Confirm whether the assignment permits ALE observation extraction/action wrappers, custom PyTorch RL, Stockfish-derived training labels, and offline engine evaluation.

**Verified facts:** The roadmap proposes ALE extraction, direct PyTorch RL, and optional Stockfish supervision; Stockfish is excluded from inference. M0/M1/M2 are already accepted, but that does not establish instructor policy for future supervised/engine use.

**Uncertainty:** Assignment rules and the instructor's interpretation have not been provided in canonical records.

**Options:** Approve the planned scope; allow only a subset such as a small behavior-only baseline without engine use; or restrict the work further. A PGN-only artifact remains an intermediate if real teacher use is prohibited under the current M3-02 criterion.

**Recommendation / trade-off:** Ask the instructor for a written scope answer before any teacher search or training. Keep the Double DQN simulator experiment central. A narrower permission may allow source-approved PGN engineering or an optional behavior-only baseline, but it does not satisfy M3-02; if teacher use is prohibited, formally revise canonical M3 acceptance before claiming M3 complete.

**Authority:** Instructor for assignment rules; project owner records the decision. **M3 impact:** M3 parsing and provenance design can continue, but any restricted label/training operation must wait. Independent repository and source-documentation work can continue.

## O-06 — Data source, license, and use policy

**Decision needed:** Select the source and approve permitted retrieval, transformation, retention, publication, and any redistribution of derived records.

**Verified facts:** The publisher's listing rechecked 2026-10-17 reports the May 2022 Elite package as 355,535 games/93 MB, standard games with bullet excluded, and a 2500+ versus 2300+ filter since December 2021. It identifies Lichess Open Database as origin but provides no license/checksum for its filtered package. The official Lichess page states its own exports are CC0, publishes SHA-256 checksums, and lists May 2022 rated-standard as 28.8 GB/89,300,578 games; it also reports embedded White-perspective Stockfish comments in about 6% of standard games without a uniform teacher protocol. The official broadcast archive is separate CC BY-SA 4.0 (May 2022: 5,695 games/3.55 MB). These are publisher-reported values; no archive was downloaded or locally measured. See [Elite listing](https://database.nikonoel.fr/) and [official Lichess database](https://database.lichess.org/).

**Uncertainty:** The Elite archive's license, May archive checksum, exact PGN header distribution, sample quality, and source retention/redistribution terms are unverified. Official-source month size and profile for the intended 2022 subset also need confirmation.

**Options:** (1) obtain authoritative terms for the Elite package; (2) use an official CC0 rated-standard export and filter locally, accepting a larger source; (3) use smaller official broadcast PGNs under CC BY-SA 4.0, accepting share-alike obligations and a different data distribution.

**Recommendation / trade-off:** Keep Elite as a candidate only if an authoritative rights statement suitable for the intended use is obtained. If not, the PM-directed fallback is an official CC0 source, but its 2022 rated-standard archive is 28.8 GB compressed and requires a source-specific budget, streaming design, and reduced bounded sample plan. Official broadcasts are smaller but tournament-centered and share-alike. Do not download any source until O-06 and explicit M3 authorization are recorded.

**Authority:** Project owner, with instructor/legal policy confirmation as required by the assignment. **M3 impact:** O-06 blocks acquisition/ingestion and any public release decision. Schema, synthetic tests, and parser design can continue independently.

## O-07 — Stockfish version and role

**Decision needed:** Approve the engine version, search budget, MultiPV coverage, and whether Stockfish may label data, serve as a benchmark opponent, or evaluate offline.

**Verified facts:** M0 recorded a manual Stockfish 19 Linux x86-64 binary, archive/executable hashes, and GPL-3.0 license. The project does not install the engine through Python dependencies. M0 used only a UCI readiness handshake; no position search, label, opponent, evaluator, or inference use was approved there.

**Uncertainty:** Assignment permission, approved search limits, how much of the dataset should be labeled, and future host binary availability are unresolved.

**Options:** No engine use; bounded top-3 MultiPV labels on a deterministic sample; or exhaustive legal-candidate evaluations with much higher CPU cost.

**Recommendation / trade-off:** Preserve Stockfish 19 until an explicit version decision; if allowed, start with one thread, a measured node cap, MultiPV=3, a strict sample ceiling, and no inference/opponent use. This bounds cost and preserves raw provenance but does not provide exhaustive candidate labels.

**Authority:** Instructor for allowed role; project owner for version/budget. **M3 impact:** Teacher labels and M3-02 details requiring an active analysis config wait. PGN-only parsing and played-move targets can continue.

## O-04 — Compute and storage permissions

**Decision needed:** Confirm local disk/storage quota, whether persistent external storage is approved, Colab entitlement/quota, and whether paid compute is allowed.

**Verified facts:** PGN parsing/splitting is primarily CPU/IO. Stockfish labeling is CPU-bound. GPU demand belongs to later M4 training, not M3 ingestion. No current Colab quota, GPU, storage, or paid-compute entitlement is verified.

**Uncertainty:** Available free capacity, retention/backup location, and any paid-resource approval.

**Options:** Keep M3 to a local bounded pilot; use approved external persistent storage for larger artifacts; or use a later approved cloud environment. Paid compute remains a separate choice.

**Recommendation / trade-off:** Start with a small local pilot and measure bytes/throughput before requesting more resources. This reduces risk but may constrain the dataset scale.

**Authority:** Project owner for storage/paid compute; account owner for provider entitlement. **M3 impact:** Numeric caps must fit verified local capacity. Independent schema and synthetic validation work can continue.

## O-03 — Remaining deadline and schedule

**Decision needed:** Confirm the actual submission deadline and remaining time available for M3, M4, simulator Double DQN, and ALE integration.

**Verified facts:** The original roadmap gives only an approximate three-week estimate; no current dated deadline or instructor calendar is recorded in canonical evidence. M1/M2 are complete, but source, teacher, compute, and instructor approvals remain open.

**Uncertainty:** Calendar time, expected reporting time, and any course checkpoints are unknown.

**Options / recommendation:** Confirm the final due date and major required review dates before selecting a medium/larger data tier. If the remaining window is short, use the smallest source-approved M3 sample that meets M3-01–04 and protect the Double DQN implementation, learning run, and paired comparison budget first.

**Authority:** Project owner, with instructor dates where applicable. **M3 impact:** Does not block source-free contracts or a minimal authorized pilot; it blocks defensible larger workload and seed-count choices.

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

