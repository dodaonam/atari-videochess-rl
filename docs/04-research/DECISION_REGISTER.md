# Pre-M3 Owner Decision Register

This register summarizes decisions still owned by the project owner or instructor. A recommendation does not change the canonical approval status. O-01 through O-08 remain open in [REQUIREMENTS.md](../01-foundation/REQUIREMENTS.md). Independent design and repository work may continue where stated below.

## O-01 — Assignment and instructor permissions

**Decision needed:** Confirm whether the assignment permits ALE observation extraction/action wrappers, custom PyTorch RL, Stockfish-derived training labels, and offline engine evaluation.

**Verified facts:** The roadmap proposes ALE extraction, direct PyTorch RL, and optional Stockfish supervision; Stockfish is excluded from inference. M0/M1/M2 are already accepted, but that does not establish instructor policy for future supervised/engine use.

**Uncertainty:** Assignment rules and the instructor's interpretation have not been provided in canonical records.

**Options:** Approve the planned scope; allow only a subset such as behavior cloning without engine use; or restrict the work further.

**Recommendation / trade-off:** Ask the instructor for a written scope answer before any teacher search or training. A narrower approval can still allow PGN-only behavior cloning; waiting avoids spending effort on disallowed labels.

**Authority:** Instructor for assignment rules; project owner records the decision. **M3 impact:** M3 parsing and provenance design can continue, but any restricted label/training operation must wait. Independent repository and source-documentation work can continue.

## O-06 — Data source, license, and use policy

**Decision needed:** Select the source and approve permitted retrieval, transformation, retention, publication, and any redistribution of derived records.

**Verified facts:** The May 2022 Elite listing reports 355,535 games/93 MB, standard games, bullet excluded, and since December 2021 a 2500+ vs 2300+ rating filter. The publisher links Lichess as origin but states no license for its filtered package. Official Lichess database exports state CC0. Official broadcast PGNs state CC BY-SA 4.0; the official listing shows May 2022 as 5,695 games/3.55 MB. The full official rated-standard monthly files are large; recent 2026 listings are around 28–31 GB compressed.

**Uncertainty:** The Elite archive's license, May archive checksum, exact PGN header distribution, sample quality, and source retention/redistribution terms are unverified. Official-source month size and profile for the intended 2022 subset also need confirmation.

**Options:** (1) obtain authoritative terms for the Elite package; (2) use an official CC0 rated-standard export and filter locally, accepting a larger source; (3) use smaller official broadcast PGNs under CC BY-SA 4.0, accepting share-alike obligations and a different data distribution.

**Recommendation / trade-off:** First request an explicit license/provenance statement for Elite. If unavailable, select the official CC0 source and budget a measured bounded streaming workflow; use official broadcasts only if the owner/instructor accepts CC BY-SA terms and the tournament-centered distribution. Do not download the full dataset until the source and scope are approved.

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

## Research choice — first supervised objective

**Decision needed:** Confirm whether M4 should begin with played-move behavior cloning, and whether result prediction or teacher ranking is an approved separate experiment.

**Verified facts:** PGN played moves are observed behavior, not optimality proofs. Teacher top-k and every-legal-action scores have different meaning and cost. Q-values and discounted simulator returns belong to the RL track.

**Options:** Behavior cloning only; behavior cloning plus an outcome auxiliary task; or behavior plus bounded teacher-ranking labels.

**Recommendation / trade-off:** Begin M4 with behavior cloning over legal candidates and retain a behavior-only checkpoint. Add outcome prediction or teacher labels only as separately named experiments after approvals. This gives a clean baseline but may inherit player mistakes and rating/time-control biases.

**Authority:** Project owner/instructor for research scope. **M3 impact:** Store raw played moves and result with separate fields so all options remain available. Final loss, architecture, and teacher scope stay open.

