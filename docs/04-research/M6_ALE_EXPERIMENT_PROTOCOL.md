# M6 ALE Integration and Evaluation Protocol Proposal

**Status:** Frozen protocol for the owner-authorized M6-001 execution. Actual runs and deviations are recorded in the M6 final report. M4 supervised behavior cloning, M5 M2-simulator Double DQN, and M6 real ALE evidence remain separate.

## Question and claims

M6 establishes whether a frozen policy can interact through the existing RGB/controller path and characterizes closed-loop reliability and complete-game outcomes. It does not train in ALE. Operational success (verified moves and games) is the primary endpoint. Policy-strength differences are exploratory; M5's three paired training seeds do not establish Warm-start superiority over Scratch, and a small Atari sample cannot support a strong superiority claim or an Elo claim.

## Frozen roster and selection

Select the lowest training seed (20261104) before observing Atari outcomes, using the accepted final `post_rl`, 50,000-valid-decision snapshot for each arm. The selection rule is based only on seed identity and completed stage, not any M5 or M6 evaluation score. Pair Warm and Scratch at that seed for an exploratory paired comparison. Lock policy IDs, sidecar, checkpoint and artifact hashes in a signed/committed run manifest before the first ALE result. Never substitute a seed/stage/checkpoint after observing results; a replacement is a new, explicitly exploratory protocol version.

| Policy ID | Role | Frozen source / identity |
|---|---|---|
| `m5-warm-seed-20261104-post-rl` | Primary M5 RL integration policy | run `m5-e072011a58411f4ff26040013ba2e8c71212e6c83acf755337c2d7e1e01378d7__warm__attempt-0001`; checkpoint SHA-256 `0b2405017a8e1d539851f0cd278883d3fd23936fb5c2f7962c813590a6fd1767`; snapshot schema `videochess-ddqn-evaluation-snapshot/2.0`; M5 config SHA-256 `84d305084397ad18397dfe395fab58de824fa056729675d0d1cd9ca8bdd06d8d`. |
| `m5-scratch-seed-20261104-post-rl` | Paired exploratory RL comparison | run `m5-e072011a58411f4ff26040013ba2e8c71212e6c83acf755337c2d7e1e01378d7__scratch__attempt-0000`; checkpoint SHA-256 `3749b0c0b6ae44d3ad5d6bf0863b60937a59fbe881e0bdf4932bdce6033ca400`; same snapshot schema/config. |
| `m4-behavior-only-seed-20261024` | Supervised-only diagnostic control; not an RL policy | accepted M4 checkpoint SHA-256 `724ac730f3c5f2d01b48b26eb7670a3c764978a3dd4d6702b3057a99ab1a90a4`; schema `videochess-m4-checkpoint/1.0`. |
| `simple-material-heuristic` | Transparent one-ply non-neural diagnostic control | existing `SimpleHeuristicAgent`; code identity bound to M6 source commit. |
| `random-legal` | Controller/observation integration diagnostic, not a strength comparator | existing `RandomLegalAgent`; code identity bound to M6 source commit. |

Warm-start and Scratch policies use paired M5 training seed 20261104. M5 evaluation did not select them by score. M4 selection remains the previously accepted validation-NLL rule; it is a different training track. Heuristic and random policies are controls, not engine assistance. Stockfish is excluded from inference and M6 opponent/evaluation use unless a separate decision authorizes it.

## Scenarios and stage budgets

Use ALE `VideoChess-v5`, raw numeric `mode=4`, `difficulty=0`, and White agent side initially. Mode 4 has repeated same-seed deterministic terminal evidence, but no verified human-readable difficulty name. The current runner supports White only. Black-side ALE play is outside this protocol until its controls and full loop are independently implemented and verified.

1. **Stage 1 — interface integration:** one frozen-policy decision from a fresh, RGB-verified start; retain the observation, legal set, inference output, controller phases and RGB confirmation. This is a software integration check, not a gameplay score.
2. **Stage 2 — closed-loop reliability:** up to 10 consecutive verified player moves and genuine Atari replies per policy under debug settings first, then a small default-v5 profile check only after the debug path passes. This is a reliability diagnostic.
3. **Stage 3 — bounded complete-game evaluation:** after Stages 1–2 pass, attempt 10 games each for Warm and paired Scratch, and 5 each for Frozen M4, SimpleHeuristic, and RandomLegal under the ALE v5 default profile and White side. Use the fixed ALE seed list `20261130` through `20261139` for the paired RL policies; controls use the first five seeds. Warm/Scratch share each seed; use Warm-first for even seeds and Scratch-first for odd seeds. This is at most 35 reset/game attempts and at most 8.75 hours at the 15-minute per-game wall cap, within the 10-hour total campaign ceiling. A 54,000-ALE-frame cap is also enforced. Censored games remain incomplete, not draws. One process-start retry is permitted only before any ALE action and receives a distinct identity; the failed process remains in the ledger. No attempt is silently replaced.

The primary endpoint is per-policy verified player-move execution rate, with numerator and denominator as defined below. Complete-game W/D/L and match score are secondary. Comparisons are exploratory and reported raw with uncertainty; no winner-selection or Elo claim follows from this sample.

## Immutable ALE profiles

| Profile | frameskip | repeat_action_probability | Use |
|---|---:|---:|---|
| Development/debug | 1 | 0.0 | Interface diagnosis and low-variance controller debugging only; never pool with reported evaluation. |
| ALE v5 default evaluation | 4 | 0.25 | M6 evaluation profile; report the actual wrapper/runtime values for every game. |

M1's pinned ALE-Py 0.11.2 records the v5 defaults as RGB, frameskip 4, sticky probability 0.25 and reduced action space. Every run must assert returned registration/runtime values instead of assuming they remain unchanged. Both profiles retain RGB authority. Do not alter RAM or inject positions.

M1 calibrated 33-frame direction holds, one-frame source FIRE, 16-frame target FIRE, and one-frame releases, using 33-frame direction repeats at deterministic settings; at frameskip four, action frame requests quantize to ALE steps. Existing v5 evidence is only a small number of successful cycles. Sticky actions can alter cursor/action sequences. Record each phase and RGB confirmation; never retry uncertain FIRE or resume an interrupted action from memory. Recalibrate within M6 before broad execution if default-profile evidence fails.

## Resource envelope proposal

Use local CPU first; available laptop/Colab capacities are owner-reported and not runtime guarantees. No Colab session or paid compute is required for Pre-M6, and the neural model is small enough for CPU inference. Measure M6 inference latency and full decision time on the selected machine before expanding Stage 3. Initial ceilings: 35 game attempts, 54,000 ALE frames and 900 wall seconds per game, 10 hours total game wall budget, one serialized ALE process, 2 GiB artifact budget for compact traces/screenshots, and one retry only for a process-start failure before any ALE action. A retry after an action is a separate incomplete attempt with a new run/game attempt ID; do not silently replace it. Stop at repeated uncertainty/desynchronization, any policy/checkpoint mismatch, trace write failure, artifact cap, memory pressure, or resource ceiling. These are proposed caps, not measured full-game forecasts.

M1 measured roughly 38–41 seconds for 12–20 player/reply cycles on specific seeds/configurations, plus reply waits reaching hundreds or over one thousand ALE frames in mode 4. That is preliminary engineering evidence only; it does not guarantee complete-game duration or default-profile reliability.

## Metrics and denominators

- **Attempted games:** every reset assigned a `game_id`, including failures before the first move.
- **Completed games:** ALE-terminated attempts with a supported W/D/L classification. Report all `ale_terminated_games`, including `terminal_unknown`, separately. Terminal-unknown games are not incomplete and do not enter the W/D/L score denominator.
- **Atari win/draw/loss:** classify only from authoritative ALE terminal flags/reward, preserving raw White-perspective reward and converted agent perspective. If terminal reward semantics are ambiguous, report `terminal_unknown`; do not infer from a cleared screen or shadow checkmate.
- **Runner-truncated/incomplete:** all ALE truncations, runner budgets, controller uncertainty, reply timeout, desynchronization, unsupported rule divergence and external interruption. Never count these as draws.
- **Attempted player moves:** policy outputs for which input execution was initiated.
- **RGB-verified player moves:** initiated moves whose stable RGB observation matches the predicted legal transition.
- **Verified Atari replies:** unique legal opponent transitions confirmed by stable RGB.
- **Move execution success rate:** RGB-verified player moves / attempted player moves; also report the denominator and Wilson interval. It is undefined when denominator is zero.
- **Desynchronization rate:** desynchronization stops / attempted player moves, with absolute count. Also report ambiguous/unstable observation stops, uncertain controller actions, and opponent timeouts separately.
- **Runtime:** ALE frames, environment steps, wall time; per-decision distribution (median, IQR, p95, max); frozen-policy inference latency distribution; peak RSS; retries and stop reason.
- **Outcome summary:** raw W/D/L/terminal-unknown/incomplete counts, ALE-terminated count, supported completed-game match score `(wins + 0.5*draws)/completed_games`, and incomplete fraction. Unknown or incomplete outcomes are never silently added to the score denominator.

## Trace and replay provenance

Each attempt records `run_id`, `game_id`, `attempt_id`, policy ID, arm/seed/stage, checkpoint SHA-256, checkpoint sidecar SHA-256, policy root artifact-manifest SHA-256, Git commit, source-bundle SHA-256, dependency-lock SHA-256, Python/Gymnasium/ALE-Py/PyTorch/python-chess versions, ROM SHA-256, ALE environment ID, mode, difficulty, frameskip, sticky probability, action set, observation type, controller timing, ALE seed, agent color, UTC start/end, stop/terminal reason, raw reward, converted agent reward, terminal/truncated flags, W/D/L/unknown/incomplete result, verified UCI history, last verified FEN, attempted/verified move counts, ALE frames, environment steps, trace path/hash, and per-attempt artifact-manifest path/hash. Unknown metrics after interruption remain null and are counted explicitly; they are never imputed as zero.

Retain compact RGB evidence for reset, decision boundaries, controller phases, confirmed move/reply, terminal, and stop. Hash-chain structured trace events and verify the chain before summarizing. Run IDs bind the clean source commit and schedule; the run manifest binds config, selected artifact manifests, and roster. A seed alone does not guarantee replay: reproduction additionally requires identical code, lock/runtime, ROM, environment ID, mode, ALE profile, controller timings, policy bytes, observation timing, and compatible hardware/runtime behavior; sticky actions may still prevent bit-identical trajectories. Stage 1–2 debug-profile outcomes remain diagnostics and are stored separately; Stage 3 full games use default v5 only. Report re-execution as a replay attempt and compare verified histories/configuration.

## Stop and reporting rules

Stop safely on any stale/ambiguous RGB evidence, history/FEN/legal mismatch, illegal or stale policy action, uncertain FIRE/cursor phase, unrecognized transition, reply timeout, ALE termination during input, trace/hash failure, checkpoint drift, or resource limit. Preserve last verified history and position; no speculative advancement or retry.

Report simulator M5 numbers only as M2 simulator results. M6 describes frozen inference in real ALE, not Atari learning. Statistical reporting includes raw counts and intervals and labels comparisons exploratory. Elo is excluded unless O-08 is resolved and an approved calibrated opponent pool is established.
