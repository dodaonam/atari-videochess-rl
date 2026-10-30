# Frozen M5 Policy to ALE Integration Contract

**Status:** Pre-M6 interface specification; runtime adapter and all Atari gameplay remain M6 work. This document does not pass M6-01 through M6-05.

## Authority and components

ALE `VideoChess-v5` RGB and returned reward/termination flags are authoritative for Atari. The M1 code in `videochess_rl/environment.py`, `vision.py`, `shadow.py`, `controller.py`, and `episode.py` owns environment interaction, image evidence, observed move tracking, joystick/FIRE actions, reply detection, and stop traces. M2's `ChessSimulator` remains a separate simulator. M5's `QPolicy` in `videochess_rl/rl/evaluate.py` owns frozen legal-candidate Q inference. `load_evaluation_snapshot` in `videochess_rl/rl/checkpoint.py` validates and loads an immutable evaluation snapshot. The M6 adapter should be a narrow bridge; it must not reimplement board vision, legal action enumeration, model scoring, checkpoint loading, or controller planning.

## Decision input

The adapter calls the policy only after all preconditions below pass. The conceptual immutable input is:

```text
AtariDecisionObservation/1.0 {
  policy_id: non-empty stable string,
  checkpoint_sha256: 64 lowercase hex characters,
  agent_color: "white",
  history_uci: ordered array of every RGB-verified move since standard reset,
  observed_rgb_sha256: SHA-256 of the stable RGB evidence window,
  expected_fen: FEN reconstructed from the verified history,
  side_to_move: "white",
  legal_moves_uci: complete sorted unique UCI list derived from that history,
  observation_frame: non-negative ALE frame number
}
```

This is a design schema, not a new runtime class. FEN is a cross-check and is never accepted as a replacement for history. The only current Atari-supported agent color is White. The M6 entry procedure must verify a stable initial RGB board against the standard initial position before treating history as empty.

Before policy inference, reconstruct a fresh `python-chess.Board` by replaying `history_uci` from the standard start. Reject malformed, illegal, incomplete, or unsupported history; require its FEN, side-to-move, and sorted complete legal UCI set to match the stable RGB-derived state and the maintained shadow. Require the agent turn, a nonterminal board, a nonempty candidate set, and unique valid UCI identities. If any square is ambiguous, evidence is unstable, the shadow is desynchronized, or Atari shows a state that cannot be represented by the supported chess rules, stop before scoring. Do not infer a missing move.

`history_uci` advances only after the player's move is independently confirmed by stable RGB and after the Atari reply is uniquely inferred from RGB and applied to the shadow. The move stack must retain castling, en-passant, promotion, repetition, halfmove, and fullmove information. Until special-move and draw-rule parity has real-ALE evidence, a detected divergence is a stop condition, not a reason to adjust the shadow.

## Policy output and execution

The existing M5 API is `QPolicy.choose_move(observation, legal_moves, rng) -> chess.Move`. It replays complete history, checks FEN/turn/legal candidates, encodes using the accepted M4/M5 feature schema, scores only legal candidates, uses CPU evaluation mode and `torch.inference_mode()`, and returns one semantic UCI move as a `chess.Move`. M5 policy inference does not require training, optimizer, replay, or Stockfish code.

The M6 adapter must bind the selected output to the same `policy_id` and checkpoint hash used to load the verified snapshot. It must require the returned UCI to be exactly one member of the current validated candidate set. Before sending input, `run_episode`/controller independently checks legality again against its last verified board and plans the existing cursor route. Inference must not mutate weights, attach gradients, write transitions, advance a board, or retry a controller action.

The control protocol is:

```text
stable ALE RGB -> parse/stability check -> verify against complete history/shadow
 -> construct complete legal observation -> frozen QPolicy -> validate returned UCI
 -> controller plan/execute -> stable RGB confirmation of player move
 -> bounded wait for unique RGB-verified Atari reply -> advance history
 -> next decision, actual ALE terminal/truncation, or typed safe stop
```

Every boundary records the last verified FEN/history length, RGB evidence hash/frame, selected UCI if any, control phase, and reason. A controller interruption, uncertain FIRE, stale evidence, reply timeout, ambiguity, or mismatch stops without guessing or re-sending input. Existing code explicitly avoids retrying uncertain FIRE. If ALE terminates before the board becomes parseable, preserve the last verified FEN; use ALE reward and flags as outcome evidence and label the final board unavailable. Never convert an incomplete runner stop into a draw.

## Terminal and truncation semantics

ALE reward is documented by the pinned VideoChess wrapper from White's perspective. Convert to agent perspective only for a supported agent color and preserve the raw reward. ALE `terminated` and `truncated` remain separate. Runner budget stops, runtime interruptions, controller uncertainty, reply timeouts, unsupported rule states, and desynchronization are incomplete attempts, not game draws or Atari losses. A stable, verified chess board is not required to invent a terminal board when the screen clears; retain the last actually RGB-verified state.

## Supported versus deferred

- **Implemented and tested in M1/M5:** RGB board extraction, stable evidence windows, unique legal reply inference, shadow advancement only on matching RGB evidence, bounded controller actions and wait, typed stop categories, White-side move loop, complete-history M5 policy input for simulator observations, CPU frozen Q-policy, candidate validation, checkpoint schema/hash validation.
- **Implemented but unverified as an integrated path:** passing an M1 verified full-history board into M5 `QPolicy`; checkpointed M5 policy used by the M1 selector; full-game reward perspective and final-board accounting.
- **Not established:** Atari Black-side control; robust real-ALE special moves/draw rules across modes; terminal board parsing; default-profile population reliability; complete games for the accepted M5 policy.
- **Deferred to M6:** adapter and runner wiring, actual ALE decision/reply loops, special-case stop/recovery tests against genuine RGB and ALE flags, bounded complete games, default-v5 repeatability.

## Required contract tests

| # | Required case | Expected behavior | Pre-M6 evidence / M6 ownership |
|---:|---|---|---|
| 1 | Valid verified chess state | Construct only from stable RGB plus matching shadow/history | Offline M2 fixture only; real RGB proof is M6 Stage 1. |
| 2 | Valid ordered history | Reconstruct board and retain repetition-relevant move stack | Offline M2 policy test uses the actual complete initial history; multi-ply ALE history is M6. |
| 3 | Invalid/missing history | Reject non-initial states with absent, malformed or illegal history | M6 adapter test. Empty history is valid only for verified initial reset. |
| 4 | FEN/history mismatch | Reject before scoring | Existing M5 policy has a guard; M6 test must exercise through adapter. |
| 5 | Side-to-move mismatch | Reject before scoring/controller | M5 policy guard plus M6 adapter test. |
| 6 | Legal candidate mismatch | Reject any incomplete, stale or extra candidate set | Existing M5 policy has a guard; M6 adapter test. |
| 7 | Duplicate/malformed UCI actions | Reject duplicate identities or parse failures | Existing candidate selection checks uniqueness/order; M6 boundary test. |
| 8 | Illegal policy output | Controller independently rejects before input | M6 adapter/controller test. |
| 9 | Stale observation | Stop when frame/evidence identity is no longer current | M6 real-loop test. |
| 10 | Ambiguous RGB evidence | Stop without policy call or advancement | Existing vision/shadow tests cover ambiguity; genuine RGB case is M6. |
| 11 | Desynchronized shadow | Raise typed stop, preserve previous board/history | Existing `ShadowBoard` tests cover non-advancement; M6 integration regression. |
| 12 | Interrupted controller execution | Stop, preserve action phase and last verified state; never retry uncertain FIRE | Existing controller/episode tests; M6 adapter trace test. |
| 13 | Atari reply timeout | Incomplete stop, not loss/draw; preserve last verified state | Existing bounded runner; genuine policy loop is M6. |
| 14 | Terminal without parseable final board | Use ALE reward/flags, retain last verified FEN, label final board unavailable | Existing M1 terminal evidence; M6 policy terminal accounting. |
| 15 | Valid runner truncation | Distinguish ALE truncation and runner budget stop from termination | Existing runner/episode tests; M6 ledger test. |
| 16 | Missing/corrupt checkpoint | Reject before any action | Existing immutable loader; M6 entry/adapter negative test. |
| 17 | Incompatible checkpoint schema | Reject before model creation/action | Existing loader schema validation; M6 adapter test. |
| 18 | Inference unexpectedly requires training or Stockfish | Inference path remains frozen and engine-free | Pre-M6 actual snapshot test checks CPU eval, no optimizer/replay, and declared engine-free policy config; M6 dependency/runtime review remains required. |
| 19 | Repeated invocation without intended stochasticity | Same verified input returns same legal UCI action | Pre-M6 actual snapshot test passed for repeated initial-state inference. |
| 20 | Frozen model weights mutate | No state tensor changes and no gradients appear | Pre-M6 actual snapshot test passed; M6 repeat in integration suite. |

These cases define M6 tests; this table does not claim all adapter/integration cases passed in Pre-M6. Mock/offline tests establish only software behavior. M6 must separately produce genuine ALE evidence for real-runtime criteria.
