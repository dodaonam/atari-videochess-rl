# M2 Post-Review Hardening — 2026-10-16

## Scope and revisions

This record resolves PM findings F-01 through F-08 against the completed M2 implementation. The reviewed feature baseline was `cedd14c59eaa9a7bc682d2ffc78527098b4497a9`; the base remained `origin/initial-idea` at `11b6dfe67c961bca3d5d693d87a1f27448983487`. The hardening source and test changes are in `94d11a36c507aae970590c8013bd210c110fc9ff` and `b3fc8105a5dbf543267a77be77f6a8c6c76ab8e2`; the latter extends Board rollback across the entire attempted decision when an exception or interruption occurs after the agent move.

The historical M2 delivery record is preserved as written. At `2026-10-16T15:44:46Z`, GitHub still reported PR #1 open, unmerged, based on `initial-idea`, and headed at `cedd14c59eaa9a7bc682d2ffc78527098b4497a9`; this is the pre-hardening remote snapshot, not the final delivery revision. The feature had advanced legitimately from the earlier `10d11dcc...` delivery snapshot. No branch history was rewritten. See the preflight snapshot in `logs/M2-post-review-github-preflight-20261016.log`; final delivery is verified from PR #1 metadata after push.

ADR-0002 remains accepted and unchanged. No neural architecture, action encoder, training, dataset, Stockfish search, or ALE behavior was added to M2.

## Finding dispositions

| Finding | Classification | Resolution | Evidence and status |
|---|---|---|---|
| F-01 | Confirmed reproducibility contract gap for mutable policies. | Policies without `reset_episode(seed=...)` are documented as stateless across episodes. Stateful policies can reset through the optional hook. The simulator checks that policy identity/configuration remain stable, rejects drift, and resets policy-local state before each episode. | Fresh and reused simulator episodes, repeat reset after opponent failure, and descriptor drift are covered in `tests/test_m2_simulator.py`. PASS. |
| F-02 | Confirmed heuristic scoring defect. | Removed the extra promotion bonus because the successor material delta already includes pawn-to-piece value. Capture preference remains a separate, documented 5% bonus. Immediate mate retains priority. | Deterministic scores cover quiet queen/rook/bishop/knight promotions, capture promotion, queen capture versus promotion, and existing immediate-mate tests in `tests/test_m2_baselines.py`. PASS. |
| F-03 | Confirmed interruption rollback defect and stale-record risk. | Opponent failure or interruption now restores the Board snapshot for the whole attempted decision. Benchmark metadata is derived from the simulator's actual final Board and counters rather than the previous `StepResult`. Chess Board rollback is guaranteed; policy-local state and consumed RNG are not. | Fault injection covers reset failure, agent failure after two completed decisions for both colors, opponent failure after two completed decisions for both colors, and opponent interruption after two completed decisions. Tests assert history/ply/decision alignment and no W/D/L for failures. PASS. |
| F-04 | Confirmed custom-position validation gap. | `reset(initial_board=...)` now rejects `Board.is_valid() == False` before replacing a live episode or resetting the policy. The error includes the `python-chess` status value. | Tests cover missing/multiple kings, a pawn on the back rank, invalid castling rights, and a side-to-move/check inconsistency; valid special-move fixtures still pass. Rejected resets preserve the prior episode. PASS. |
| F-05 | Acceptable baseline-quality limitation, not a simulator rules defect. | The one-ply heuristic evaluates candidate boards reconstructed from FEN and does not use repetition history. The limitation is documented. The authoritative simulator Board continues to determine automatic outcomes; no mutable Board is exposed to the policy. | `test_fen_only_heuristic_observation_does_not_override_history_authority` demonstrates the distinction and fivefold termination. PASS with limitation retained. |
| F-06 | Serialization/history test coverage gap. | Added direct position-field round-trip and UCI replay assertions. Observation FEN uses `en_passant="fen"`; tests do not claim FEN restores history. Standard and custom starts are replayed from their respective initial positions. | Tests cover placement, side, castling, en passant, half/fullmove counters, legal UCI identities, standard/custom replay, fivefold history replay, and FEN-only loss of repetition history in `tests/test_m2_simulator.py`. PASS. |
| F-07 | Historical provenance snapshot, not Git corruption. | Preserved the older `10d11dcc...` snapshot and distinguished it from the live `cedd14c...` remote state at the start of this cycle. Recorded a timestamped preflight snapshot and verified the final pushed branch/PR through GitHub API metadata. No self-referential final-HEAD field is used. | Historical `.agents/evidence/M2-github-delivery-20261016.md` and its log remain unchanged; current preflight log plus final PR metadata provide the new anchors. PASS. |
| F-08 | Stale implementation wording in current technical docs. | Updated the completed M2 plan and architecture references to describe implemented modules. Kept future M3-M7 proposals and historical pre-M2 readiness notes labeled as such. | `.agents/plans/M02-chess-foundation.md`, `docs/03-technical/ARCHITECTURE.md`, `docs/03-technical/MDP_SPEC.md`, and `docs/06-quality/TEST_STRATEGY.md`; focused/full suite and preflight pass. PASS. |

## Test and consistency verification

All commands used the existing locked environment; no dependency was installed.

| Check | Command | Result | Provenance |
|---|---|---|---|
| Focused M2 suite | `/home/dodaonam/Projects/atari-videochess-rl/.venv/bin/python -m unittest tests.test_m2_simulator tests.test_m2_baselines tests.test_m2_benchmark -v` | PASS; 58 tests, 0.160 s, exit 0. | `logs/M2-post-review-focused-suite-20261016.log`; revision `b3fc8105a5dbf543267a77be77f6a8c6c76ab8e2`; started `2026-10-16T15:49:29Z`. |
| Full repository suite | `PATH=/home/dodaonam/Projects/atari-videochess-rl/.venv/bin:$PATH /home/dodaonam/Projects/atari-videochess-rl/.venv/bin/python -m unittest discover -s tests -v` | PASS; 180 tests, 80.286 s, exit 0 on a clean committed snapshot. This includes clean-clone recovery, M0 smoke, M1/ALE, and M2. The earlier dirty-checkpoint run is retained as a diagnostic and was resolved by checkpointing/committing the records before rerun. | `logs/M2-post-review-full-suite-20261016.log`; verification snapshot `57c6bde8f3cd9fdaf0a6fe4ec283c93fb8cf037a` (implementation `b3fc8105a5dbf543267a77be77f6a8c6c76ab8e2`); `2026-10-16T15:54:51Z`–`15:56:29Z`. |
| Benchmark integrity/replay | Locked Python validator compared official/repeat records, historical move/outcome semantics, and replayed all UCI histories with `python-chess`. | PASS; official/repeat semantic match; all 8 games replay legally and result, WDL perspective, termination reason, plies, and stop flags agree. Historical moves/outcomes also match after excluding run metadata and documented policy configuration. | `logs/M2-post-review-benchmark-verification-20261016.log`; source `b3fc8105a5dbf543267a77be77f6a8c6c76ab8e2`; worktree was dirty only from evidence/governance assembly. |
| GitHub preflight | `git fetch origin`; `gh pr view 1 --json number,url,state,isDraft,mergedAt,headRefName,headRefOid,baseRefName,changedFiles,autoMergeRequest`; `gh pr checks 1` | PASS for PR state and refs; GitHub reported no checks. `gh pr checks` returns 1 when none are reported; no CI success is claimed. | `logs/M2-post-review-github-preflight-20261016.log`; verified `2026-10-16T15:44:46Z`. |
| Context consistency | `python3 scripts/agent_checkpoint.py`, then `python3 scripts/agent_preflight.py` | Checkpoint and direct preflight return PASS; the generic `ARTIFACT_MANIFEST_REQUIRED` notice remains and is covered by the M2 manifest. | Direct preflight `2026-10-16T15:58:29Z`, revision `959cf48bbeb83ef8191c2433d78bf6e37c20a1ef`; `logs/M2-post-review-final-preflight-20261016.log`. The final evidence checkpoint is refreshed immediately before delivery. |

During development, one focused run exposed a mismatch in the newly added descriptor-drift assertion: the test expected an episode to remain readable after policy configuration changed, while the chosen contract invalidates that episode. The test was corrected to assert invalidation and preservation of the last Board snapshot. The diagnostic is retained at `logs/M2-post-review-development-diagnostic-failure-20261016.log`; it is not counted as a verification pass. A separate one-off validator invocation with system Python lacked `python-chess`; it was rerun successfully with the project virtual environment.

## Corrected baseline benchmark

The exact prior configuration was retained: standard initial position; base seeds `20261016`, `20261017`; both agent colors; Random Legal versus Simple Material Heuristic in both pairings; maximum 400 agent decisions; Python 3.12.3; python-chess 1.11.2; Linux x86_64; 8 CPUs. Both regenerated runs used source revision `b3fc8105a5dbf543267a77be77f6a8c6c76ab8e2`; the recorded worktree was dirty due to documentation/evidence assembly, while implementation files were clean. The simulator and baseline code were unchanged after that revision.

| Agent | Color | W/D/L | Completed | Truncated | Failures/interruptions | Mean decisions |
|---|---|---:|---:|---:|---:|---:|
| Random Legal | White | 0/1/1 | 2 | 0 | 0 | — |
| Random Legal | Black | 0/1/1 | 2 | 0 | 0 | — |
| Random Legal | Both | 0/2/2 | 4 | 0 | 0 | 90.5 |
| Simple Material Heuristic | White | 1/1/0 | 2 | 0 | 0 | — |
| Simple Material Heuristic | Black | 2/0/0 | 2 | 0 | 0 | — |
| Simple Material Heuristic | Both | 3/1/0 | 4 | 0 | 0 | 51.0 |

All 8 games completed as chess games: 5 checkmates and 3 insufficient-material draws. There were no truncations, failures, or interruptions. Official run `m2-baseline-20261016T155117Z` and repeat `m2-baseline-20261016T155121Z` matched semantically. Their move histories and outcomes also match the earlier benchmark; the corrected heuristic descriptor/configuration and source revision differ as expected. No Elo, statistical significance, Atari strength, or learned competence is inferred.

Tracked structured outputs:

- `M2-post-review-hardening-benchmark-20261016.json` — current b3 run; SHA-256 recorded in the adjacent manifest.
- `M2-post-review-hardening-benchmark-repeat-20261016.json` — independent b3 repeat; SHA-256 recorded in the adjacent manifest.
- `M2-post-review-hardening-manifest-20261016.sha256` records those files, the verification logs, and the ignored raw artifacts. The raw `artifacts/m2/` files are local-only; the tracked JSON copies and their hashes are available to PR reviewers.

## Acceptance and governance

| ID | Status | Evidence |
|---|---|---|
| HC-01 | PASS | The table above gives evidence-backed dispositions for F-01–F-08. |
| HC-02 | PASS | F-02, F-03, and F-04 defects corrected and regression-tested. |
| HC-03 | PASS | Stateful/stateless lifecycle, descriptor stability, reset reproducibility, and failure reset are specified and tested. |
| HC-04 | PASS | Promotion and capture scores are explicit, correct, and covered, with mate priority preserved. |
| HC-05 | PASS | Failure/interruption records use final valid Board state; rollback boundary is documented and fault-injected. |
| HC-06 | PASS | Invalid custom positions are rejected before episode mutation. |
| HC-07 | PASS | FEN and replay invariants are tested without claiming FEN contains move history. |
| HC-08 | PASS | F-05 is retained as a baseline-quality limitation; simulator rules remain authoritative. |
| HC-09 | PASS | M2-01 through M2-04 remain satisfied; see the updated M2 acceptance record and this verification. |
| HC-10 | PASS | 58 focused M2 tests and all 180 repository tests pass. The clean full-suite run includes the clean-clone context assertion; the earlier dirty-checkpoint diagnostic is preserved. |
| HC-11 | PASS | The prior 8-game benchmark configuration was rerun and semantically repeated; all records were checked. |
| HC-12 | PASS after final checkpoint/preflight | Canonical records retain M2-001 done, G3 unapproved, M3 pending authorization, and O-01–O-08 open. Final checkpoint and preflight are part of delivery verification. |
| HC-13 | PASS after final push verification | The existing feature branch is updated through ordinary push; live remote HEAD is recorded in the PR description and final delivery response. |
| HC-14 | PASS after PR #1 API verification | The existing PR is updated, open, unmerged, and has auto-merge disabled; live head/base are confirmed in GitHub metadata. |

M2-001 remains `done`; G3 remains unapproved; M3–M7 remain unstarted; M3 still requires separate authorization and prerequisite review. No blocker or open approval was closed by this cycle. M1/ALE source files were not changed. The existing `ARTIFACT_MANIFEST_REQUIRED` preflight notice remains generic and is satisfied for M2 by the tracked manifest; ignored raw benchmark files are not promised to clean clones.

## Reviewer focus

Review `videochess_rl/simulator.py` for policy reset, descriptor stability, Board validation, and rollback boundaries, including interruptions between agent and opponent move; `videochess_rl/baselines.py` for score accounting; `videochess_rl/benchmark.py` for final-snapshot records; the three `tests/test_m2_*.py` files for the new regressions; and the MDP/architecture/plan changes for contract wording. Then compare the two tracked benchmark JSON files and the manifest. PR #1 remains the sole review and integration path.
