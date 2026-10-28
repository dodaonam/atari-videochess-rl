# System Architecture

**Status (2026-10-28):** M1/ALE, M2 simulator, M3 data pipeline, and M4 behavior-cloning milestone are implemented and accepted. M4-01 through M4-04 passed; the original fixed M4-02 failure remains preserved as historical evidence. The accepted M3 release and M4 checkpoint are local artifacts outside Git. PRs #8 and #9 are integrated; M4 post-merge clean-clone verification is recorded in the [delivery report](../../.agents/evidence/M4-postmerge-delivery-verification-20261027.md). ADR-0003 is Accepted. M5 algorithm and execution preparation are specified in [RL_ALGORITHM.md](RL_ALGORITHM.md) and the [M05 plan](../../.agents/plans/M05-double-dqn.md); no Double DQN learner or training exists. M5 is not active or authorized, and G3 remains unapproved. Current live authorization belongs to `.agents/state/PROJECT_STATE.yaml`.

**Purpose:** Explain how the verified Atari interface and accepted chess-learning contracts fit together while preserving separate sources of truth.

## Existing implementation: M1 under G2

The M1 implementation comprises the following modules and implements the observation-driven ALE feasibility layer:

1. [environment.py](../../videochess_rl/environment.py) owns Gymnasium/ALE construction, explicit runtime profiles, reset/step lifecycle, copied RGB frames, ALE flags/reward, frame numbers, selected-byte diagnostic RAM reads, versions and ROM hash.
2. [vision.py](../../videochess_rl/vision.py) counts calibrated gold/blue pixels in each board square and creates single-frame observations and temporal windows. It recognizes cursor and selected-piece visual states, infers side/occupancy and rejects ambiguous windows.
3. [controller.py](../../videochess_rl/controller.py) converts a legal UCI chess move and an observed cursor square into joystick/FIRE frame plans with separate source and target timing.
4. [shadow.py](../../videochess_rl/shadow.py) uses python-chess to propose legal transitions and only commits a transition when RGB occupancy evidence matches. Ambiguous or contradictory evidence raises a desynchronization error.
5. [episode.py](../../videochess_rl/episode.py) runs a bounded real-ALE episode, verifies player input phases, observes Atari replies, retains reward/termination events, distinguishes ALE endings from runner stops and preserves the last verified FEN.
6. [demo.py](../../videochess_rl/demo.py) provides the one-cycle demo entry point and writes structured traces and selected PNG frames.

The M1 closed loop is: reset the real environment → validate the actual RGB start and cursor → select a legal diagnostic move from the shadow position → translate it into verified Atari input phases → confirm candidate occupancy from RGB → detect one legal Atari reply from RGB → obtain full-board coverage at multiple cursor positions → atomically advance the shadow → stop safely on ambiguity or a real ALE terminal.

The shadow board assists legal-transition checking; it does not create an Atari observation. Diagnostic RAM is retained separately and does not choose actions. The current episode controller is a diagnostic white-player path, not a learned policy or general production engine.

M1-01 through M1-06 are accepted and G2 is approved in the [final verification record](../../.agents/evidence/M1-G2-final-verification-20261016.md). The local terminal bundle and ignored raw RGB traces remain separate from ordinary Git contents. The real terminal evidence and limits are documented in [ALE_ENVIRONMENT.md](ALE_ENVIRONMENT.md).

## Milestone implementation and future flow

| Milestone | Component and output | Maturity |
|---|---|---|
| M2 | Standard-chess simulator, explicit MDP, stable UCI identities for legal moves, random-legal and heuristic baselines, seeded simulator records. | Implemented and verified under M2-001; G3 remains unapproved. |
| M3 | Provenance-aware PGN parsing, bounded Stockfish teacher subset, and leakage-safe train/validation/test release. | Implemented and accepted in M3-001; source package license remains unstated. Artifacts are outside Git; the exact local release was reverified before M4 use and its nine files remained unchanged. Reverify before future use. |
| M4 | Supervised behavior-cloning baseline from M3 played-move labels; saved pretraining-only checkpoint and evaluation. | M4-01 through M4-04 passed with evidence; the behavior-only checkpoint is retained outside Git. The original fixed gate failure and revised PM-approved gate are both preserved. PR #8 is merged and the actual integration commit passed clean-clone post-merge verification; see the [delivery report](../../.agents/evidence/M4-postmerge-delivery-verification-20261027.md). |
| M5 | Direct PyTorch Double DQN in the chess simulator with legal-move selection, replay/target networks and separately configured curriculum. | Algorithm/experiment/plan are specified for PM review; no RL training code exists. A separate direct authorization is required. |
| M6 | Inference adapter that observes real ALE RGB, obtains validated chess state, selects a legal move, calls the existing Atari controller and verifies the resulting real transition. | Proposed; M1 controls exist, learned-agent integration does not. |
| M7 | Controlled evaluation, comparison, report and handover under approved conditions. | Proposed; no delivery artifacts exist. |

Engineering order and fixed-file inventory remain owned by [EXECUTION_PLAN.md](../02-management/EXECUTION_PLAN.md). G/M governance mapping remains owned by [ADR-0001](../02-management/decisions/ADR-0001-governance-crosswalk-and-file-priorities.md).

## Responsibility boundaries

| Concern | Canonical responsibility | Shared interface or required separation |
|---|---|---|
| Chess rules and legal transitions | `python-chess` in the implemented M2 simulator; M1 shadow uses it only for candidate validation. | Reuse stable UCI serialization of `python-chess.Move` where useful. The simulator owns simulated transitions; ALE RGB owns Atari state. |
| Simulated episode | Implemented M2 simulator and configured opponent policy. | Has no dependency on ALE frames, cursor positions, FIRE timing or RAM. |
| ALE observation/control | Existing M1 environment, vision, controller and episode modules. | Accepts move intent only after an ALE-derived state is validated. |
| Offline PGN/teacher data | Implemented M3 data tooling and accepted release manifests. | Preserve source game, position, played move, teacher output, score perspective and license/provenance as separate fields; the exact accepted local release was independently verified, but ignored artifacts are not included in a clean checkout and must be reverified before use. |
| Model inference | Accepted ADR-0003 architecture; M4 inference implementation is complete and integrated. | Selects from semantic legal moves under the action-conditioned scorer; this is an M4/M5 interface, not an M2 component. The M4 adapter contains no Stockfish import or inference call. |
| Supervised learning | Accepted M4 behavior-cloning design; the bounded M4 experiment passed technical acceptance. | The run used only the played PGN move; behavior logits remain separate from Stockfish evaluations and from RL rewards/Q-values. |
| Simulator RL | Proposed M5. | Use simulator rewards/transitions; report as simulator RL. |
| Atari evaluation | Proposed M6/M7. | Use actual ALE RGB, actions, reward and flags; report separately from simulator results. |
| Artifacts and provenance | Existing trace conventions plus future run manifests. | Each run must identify revision, config, seed, versions, dataset/checkpoint hashes, opponent and metric source. |

## Information flow and conversions

1. M3 may parse a PGN into a source game, legal Board positions and actual played Move keys. Those moves are behavior observations, not automatically best moves.
2. If separately authorized, Stockfish may evaluate a position or candidates offline. Its score source, search config and White/Black sign must remain explicit. An engine score is not an ALE reward or an RL return.
3. The accepted initial M4 protocol trains only from played PGN moves. A separate teacher-supervision experiment would need its own approved target protocol and authorization. The resulting behavior checkpoint does not establish RL performance.
4. M5 may use a future model to score legal semantic moves and learn from simulator transitions. Its metrics remain simulator-only; candidate-list offsets are not action identities.
5. In M6, the policy receives a state derived from current ALE RGB plus a validated move history. It proposes a chess move; the existing adapter translates that move to joystick/FIRE actions.
6. The ALE RGB board and returned ALE reward/terminated/truncated values are observed after control. Only validated RGB transitions update the M1 shadow. Model predictions, simulator state and diagnostic RAM cannot be substituted for the observed Atari result.

Not every legal python-chess position or move is known to be representable or controllable in VideoChess. Castling, en passant, promotion, rule differences, transient sprites, Atari readiness and input failure remain compatibility risks for M6.

## Sources of truth

| State or value | Source of truth | Permitted use |
|---|---|---|
| Simulated chess state | M2 simulator’s python-chess Board and retained move history. | Simulator transitions and simulator metrics only. |
| Current Atari occupancy/cursor | Actual ALE RGB parsed by the M1 vision pipeline. | Control readiness and real-game observation. |
| M1 shadow board | Only a legal history hypothesis cross-checked against complete RGB evidence. | Detect/infer a candidate legal transition; never silently repair RGB. |
| Diagnostic RAM | Selected ALE memory bytes recorded separately. | Runtime investigation only; not controller decisions. |
| PGN positions and played moves | Identified source PGN and parser output. | Offline examples with source provenance. |
| Teacher evaluation | Explicit offline engine/version/search output, if permitted. | Supervision or analysis only; not deployed inference. |
| Model output | Agent prediction for legal candidates. | Candidate selection; never proof that the Atari accepted a move. |
| ALE outcome/reward | Values returned by the real Gymnasium/ALE step call. | Atari evaluation after preserving actual flags and settings. |

## Quality requirements

- Keep modules small; stable UCI conversion can remain at the simulator boundary unless implementation evidence justifies a separate helper.
- Use deterministic state/action mappings and seeded randomness where possible.
- Make configuration explicit and record both registered defaults and effective settings.
- Reuse the locked dependencies before proposing additions; do not add an RL framework contrary to the project requirements.
- Generate or select only legal moves at the boundary. Treat invalid actions as errors, not hidden state transitions.
- Preserve failure phase and last verified state. No blind Atari retry or inferred simulator outcome may overwrite a real observation.
- Keep metrics and artifacts labeled by environment, source, policy, seed and revision.
- Prefer ordinary Python interfaces and focused tests over new infrastructure that does not serve the project’s limited time and compute.

## References and maturity

- Current interfaces: [environment.py](../../videochess_rl/environment.py), [vision.py](../../videochess_rl/vision.py), [controller.py](../../videochess_rl/controller.py), [shadow.py](../../videochess_rl/shadow.py), [episode.py](../../videochess_rl/episode.py), [demo.py](../../videochess_rl/demo.py).
- Current tests: [M1 vision](../../tests/test_m1_vision.py), [control](../../tests/test_m1_control.py), [shadow](../../tests/test_m1_shadow.py), [episode](../../tests/test_m1_episode.py), [ALE integration](../../tests/test_m1_ale_integration.py).
- Accepted M2 MDP: [MDP_SPEC.md](MDP_SPEC.md); completed implementation record: [.agents/plans/M02-chess-foundation.md](../../.agents/plans/M02-chess-foundation.md).
- The M2 foundational action and perspective contract is accepted in [ADR-0002](../02-management/decisions/ADR-0002-chess-mdp-action-and-perspective.md). The M4/M5 neural scoring architecture is Accepted in [ADR-0003](../02-management/decisions/ADR-0003-pretraining-model-interface.md); M4 implementation and measured behavior-cloning results are documented in the acceptance report. Current milestone state and authorization are recorded in canonical project state.
- The Pre-M4 model/action interface is accepted in [ADR-0003](../02-management/decisions/ADR-0003-pretraining-model-interface.md). The owner has separately authorized M4-001; see canonical state and the dated authorization addendum.
