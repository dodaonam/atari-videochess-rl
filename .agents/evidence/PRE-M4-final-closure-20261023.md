# Final Pre-M4 Closure and M4 Execution Readiness — 2026-10-23

## Verdict

**PRE-M4 COMPLETE — GO WITH LIMITS.** The integration, lossless checkpoint archive, accepted M3 release, accepted ADR-0003, semantic readiness, and bounded training protocol are verified and documented. **M4-001 is not activated:** the only remaining entry condition in its conditional authorization is authoritative external O-01 course-policy evidence. The project-owner technical choices are settled; no instructor permission is inferred. M4 training and model implementation have not started, no M4 acceptance criterion is passed, and G3 remains unapproved.

## Verified baseline

- Integration branch: `initial-idea`, merge commit `d9f0872c120fb2408343859c938257e3962f2e09`.
- PR #5 is merged at that commit; the migration files and canonical state pointer are on the integration branch.
- PR #4 remains in its historical ancestry; no merge or branch rewrite was performed in this mission.
- M3-001 remains `done` and accepted. M4-001 remains `pending`, `engineering.active_milestone` is `null`, `start_authorized` is `false`, and no active task exists. G3 is absent from approved gates.
- The baseline in the operator's original worktree had a user-owned HTML deletion plus untracked `main.py` and an M1 evidence ZIP. That worktree was left untouched; all changes were made in a clean worktree based on the latest fetched `origin/initial-idea`.

## R01–R08 readiness matrix

| Check | Status | Evidence and scope | Remaining condition |
|---|---|---|---|
| **R01 — Baseline and governance integrity** | **PASS** | Current integration ancestry and state/backlog verified. M3 remains accepted; M4 pending; `start_authorized=false`; no active task; G3 unapproved. `python3 scripts/agent_preflight.py --json` passed on the clean integration worktree. | None for the readiness check. Do not activate M4 until the conditional authorization is satisfied. |
| **R02 — M3 data readiness** | **PASS** | Exact local release verified read-only by the full project verifier and supplementary structural/hash checks. Release ID, manifest/split identities, all nine file hashes, schemas, 1,000 games, 19,268 rows, split counts, 732 purges, 182 rejections and zero post-purge board-signature overlap match accepted evidence. See [M3 verification](M3-release-local-verification-20261023.md). | Re-run verification immediately before each future use. Keep raw/release data local and non-redistributed; third-party package license remains unstated. |
| **R03 — M2/M3/M4 boundary** | **PASS, scoped** | Existing synthetic model-boundary tests cover FEN semantics, deterministic legal UCI candidates, perspective, special moves, terminal sets and history cases; M2/M3 reconstruction fixtures pass. The full M3 verifier replayed real release records and the supplementary pass confirmed each played target is exactly once in its legal list. | PASS covers semantic state/action boundaries only. No tensor encoder, M4 loader or neural feature-parity integration exists yet. |
| **R04 — M4 model design** | **PASS, design only** | ADR-0003 accepted by the owner; `MODEL_DESIGN.md` gives input/output, canonicalization, candidate identity, masks, history and model interface. Parameter count ~121,897 is explicitly a design estimate against a 250,000 cap. | Implementation and actual parameter count remain M4 work. |
| **R05 — M5 compatibility** | **PASS, interface only** | Accepted design transfers compatible state/history/candidate representations and initializes a separate Q head. Policy logits are not Q-values; target/online selection uses semantic UCI actions. | No M5 code or transfer execution is claimed. M5 parity tests remain future work. |
| **R06 — Training/evaluation protocol** | **PASS, protocol only** | `TRAINING_PROTOCOL.md` and the M4 plan specify accepted split use, behavior target, leakage exclusions, baselines, seeds, validation-only selection, one frozen test evaluation, stop rules and CPU/time/memory caps. RL remains the principal objective. | No M4 runtime, neural throughput, or experiment result is measured. Recheck local resources and schedule before authorized execution. |
| **R07 — Checkpoint history/recovery** | **PASS, integrated with limits** | PR #5 is merged. At the integration baseline: 148 archived records plus the separate current checkpoint (149 represented identities), logical SHA-256 `da88335f4091c2b8a95c15d70e7cd7951c3705d47a7dd921aa2cfc0ff803302a`; state 70,382 bytes; archive 1,924,692 bytes. `verify` and clean-clone preflight both passed on the integration commit; PR #5's 75/75 focused tests are retained. See [integration clean-clone log](logs/RSK010-integrated-clean-clone-20261023.log). | Archive grows linearly; all segments are rehashed/decompressed; multiple file replacements are not crash-atomic. Review storage/latency before 64 MiB and follow the documented roll-forward/recovery rules. No history deletion. |
| **R08 — Verification and handoff** | **CONDITIONAL pending final test/PR-head verification** | Integration clean-clone archive verification and preflight are logged; the local M3 verifier is logged. Focused/full repository tests and final closure PR-head CI have not yet completed. | Convert to PASS only after relevant tests, final-HEAD preflight, clean-clone recovery and exact PR-head CI results are recorded. GitHub context workflow is not the full Python suite. |

## Owner decisions and O-01

On 2026-10-23 the owner accepted ADR-0003 according to the proposed design. The owner-confirmed technical direction includes custom PyTorch RL, Double DQN as the main RL method, `ALE/VideoChess-v5`, bounded supporting behavior cloning, and the scoped offline Stockfish teacher role; Stockfish is excluded from inference and from the initial behavior-only M4 run. These are not instructor-policy evidence.

The repository review found no separate authoritative assignment brief or instructor response establishing or restricting wrappers, custom PyTorch, behavior cloning, or relevant engine roles. O-01 remains open only to that extent; it is neither permission nor a prohibition. The existing conditional M4-001 authorization expressly requires authoritative external O-01 evidence before activation. This mission does not waive that condition.

## M4 entry boundary and next action

The migration, M3 release, ADR, data-use boundary, and protocol have been checked. Before M4-001 can become active, provide or locate the authoritative course/assignment rule or instructor response required by O-01. Then record the applicable policy, recheck the current local M3 release and resource caps, and perform the repository's direct authorization activation in state/backlog. Until those steps are recorded, M4 remains pending and no training or implementation begins. G3 closure is not an M4 start prerequisite; G3 remains unapproved.

## Historical corrections

The 2026-10-22 Pre-M4 evidence correctly marked R07 conditional before migration and reported the accepted release unavailable from the checkout paths then inspected. Those were historical observations. PR #5's subsequent integration and this mission's sibling-worktree release verification supersede them for current readiness without rewriting their original dated findings. See the dated addendum in [the original readiness record](PRE-M4-readiness-20261022.md).
