# System Architecture

**Status:** M1/ALE slice is implemented and verified as cited. M2 implementation and M2-01 through M2-04 are verified in [the M2 acceptance record](../../.agents/evidence/M2-acceptance-20261016.md); M3–M7 remain unstarted. This document describes boundaries, not a claim that unimplemented components exist.

**Purpose:** Explain how the verified Atari interface and proposed later chess learning pipeline fit together while preserving separate sources of truth.

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

| Milestone | Proposed component and output | Maturity |
|---|---|---|
| M2 | Standard-chess simulator, explicit MDP, stable UCI identities for legal moves, random-legal and heuristic baselines, seeded simulator records. | Implemented and verified under M2-001; G3 remains unapproved. |
| M3 | Provenance-aware PGN parsing and separately identified Stockfish teacher labels, with leakage-safe splits. | Proposed; no data downloaded; O-01, O-06 and O-07 remain open. |
| M4 | Supervised pretraining from explicitly selected behavior or teacher targets; saved pretraining checkpoint and evaluation. | Proposed; no model or training code exists. |
| M5 | Direct PyTorch Double DQN in the chess simulator with legal-move selection, replay/target networks and separately configured curriculum. | Proposed; no RL training code exists. |
| M6 | Inference adapter that observes real ALE RGB, obtains validated chess state, selects a legal move, calls the existing Atari controller and verifies the resulting real transition. | Proposed; M1 controls exist, learned-agent integration does not. |
| M7 | Controlled evaluation, comparison, report and handover under approved conditions. | Proposed; no delivery artifacts exist. |

Engineering order and fixed-file inventory remain owned by [EXECUTION_PLAN.md](../02-management/EXECUTION_PLAN.md). G/M governance mapping remains owned by [ADR-0001](../02-management/decisions/ADR-0001-governance-crosswalk-and-file-priorities.md).

## Responsibility boundaries

| Concern | Canonical responsibility | Shared interface or required separation |
|---|---|---|
| Chess rules and legal transitions | `python-chess` in the implemented M2 simulator; M1 shadow uses it only for candidate validation. | Reuse stable UCI serialization of `python-chess.Move` where useful. The simulator owns simulated transitions; ALE RGB owns Atari state. |
| Simulated episode | Implemented M2 simulator and configured opponent policy. | Has no dependency on ALE frames, cursor positions, FIRE timing or RAM. |
| ALE observation/control | Existing M1 environment, vision, controller and episode modules. | Accepts move intent only after an ALE-derived state is validated. |
| Offline PGN/teacher data | Proposed M3 data tooling. | Preserve source game, position, played move, teacher output, score perspective and license/provenance as separate fields. |
| Model inference | Proposed M4/M5 learned policy. | Selects from semantic legal moves; action-conditioned scoring is a proposal for later review, not an M2 component. No Stockfish process in deployed inference. |
| Supervised learning | Proposed M4. | Keep played-move behavior targets separate from Stockfish-derived evaluations or rankings. |
| Simulator RL | Proposed M5. | Use simulator rewards/transitions; report as simulator RL. |
| Atari evaluation | Proposed M6/M7. | Use actual ALE RGB, actions, reward and flags; report separately from simulator results. |
| Artifacts and provenance | Existing trace conventions plus future run manifests. | Each run must identify revision, config, seed, versions, dataset/checkpoint hashes, opponent and metric source. |

## Information flow and conversions

1. M3 may parse a PGN into a source game, legal Board positions and actual played Move keys. Those moves are behavior observations, not automatically best moves.
2. If separately authorized, Stockfish may evaluate a position or candidates offline. Its score source, search config and White/Black sign must remain explicit. An engine score is not an ALE reward or an RL return.
3. M4 may train from separately tagged behavior targets and/or teacher-derived targets after the target protocol is approved. The resulting checkpoint does not establish RL performance.
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
- The M2 foundational action and perspective contract is accepted in [ADR-0002](../02-management/decisions/ADR-0002-chess-mdp-action-and-perspective.md). M4/M5 neural scoring remains undecided; M2 authorization and task progress are recorded in canonical project state.
