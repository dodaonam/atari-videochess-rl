# M5 Double DQN Verification Matrix

**Status:** Pre-M5 test design, revision `m5-tests/1.2`, 2026-10-28. No M5 learner tests have run because no M5 learner exists. Fixture validation in the current branch is strictly a reusable test oracle and does not pass any M5 acceptance criterion. The PM remediation adds schedule/pairing and seed-derivation checks and separates evaluation snapshots from resumable checkpoints.

## Required executable coverage

| Area | Required cases | Expected result/evidence |
|---|---|---|
| DDQN target | Online/target rank disagreement using exact fixture values; online chooses legal UCI; target evaluates the identical semantic UCI; terminal reward only; valid truncated bootstrap; invalid transition rejected. | Hand-calculated target matches within a specified floating-point tolerance; no use of candidate offset as identity. |
| Candidate semantics | Lexical and shuffled candidate input, UCI lookup, promotion UCI, missing/duplicate/stale action, same candidate identity across online/target. | Candidate permutation leaves semantic selection and target unchanged; mismatch fails closed. |
| Legal masks | Illegal/padded entries, different variable candidate counts, checkmate terminal, and an automatic-draw terminal whose reconstructed Board still has syntactically legal moves. | Illegal entries cannot be explored, selected, gathered, or normalized; every terminal is represented with an empty MDP bootstrap candidate set and never calls argmax, while raw Board legality is still verified independently. |
| Simulator boundary | White and Black reward perspective, Black opening in reset, fixed color, exactly one agent move + at most one opponent reply, automatic outcomes and 400-decision truncation. | Transition contains exact before/after histories, outcome reason and action; reward agrees with `StepResult`. |
| Truncation and errors | Valid max-decision final state; termination; opponent exception/illegal move; interruption; history mismatch; impossible flags. | Valid nonterminal truncation bootstraps; true terminal does not; invalid/incomplete events do not enter replay or become draws. |
| Replay | Deterministic insertion/sample, capacity/eviction, seeded sampling, unique transition identity, opponent/color/seed preservation, illegal action rejection, recovery from journal corruption. | Same config/seed recreates sampled IDs; invalid records are excluded and diagnosed. |
| Learner update | Hand-computed Q gather/target/loss, Huber loss, exact update counter, zero-grad behavior, finite values/gradients, clipping, optimizer update. | One step changes only permitted online parameters; target remains fixed until sync. |
| Target network | Initial equality; hard synchronization cadence; target eval/no-grad; online-target disagreement fixture. | Equality only at declared synchronization; counters align with the configured gradient-step count. |
| Exploration | Epsilon endpoints/interpolation, RNG reproducibility, uniform legal random branch, greedy UCI tie-break. | Every sampled action is legal; evaluation is epsilon zero and separate from training RNG. |
| M4 warm start | Real checkpoint SHA/metadata, shared-weight equality, paired Q head initialized from a dedicated generator, target copied after transfer, no optimizer-state import. Scratch shared representation uses its own named domain. | Source artifact unchanged; behavior output absent from Q model; clean-process legal inference has no Stockfish dependency; q-head initialization is reproducible independent of global RNG consumption order. |
| Scratch comparison | Same architecture/config, deterministic independent initialization, equal budgets, and matched pair-level RNG seed schedule. | Architecture/state keys match; initialization provenance differs only as declared; per-arm RNG states/replay contents may diverge; no trajectory equivalence is claimed. |
| Paired seed derivation | Canonical experiment/pair identity, exact encoding and SHA-256 known-answer vectors, all named domains, zero-based episode indexing, run-ID exclusion, restart derivation. | Same training seed pair derives equal shared-domain initial seeds across distinct warm/scratch run IDs; different pairs/domains/episode indices separate streams; deterministic subprocess restart reproduces the same schedule. |
| Simulator RNG-domain boundary | Reset M2 with distinct episode and opponent seeds; resettable opponent hook and action RNG receive only the opponent seed. Omitted opponent seed retains historical behavior. | Pair-derived episode identity and opponent stream are independently recorded and reproducible without changing existing M2 callers. |
| Evaluation snapshot versus resume checkpoint | Snapshot after exact decision transition/replay insertion/due update/target sync; distinct schema, filename suffix, and non-resumable classification; 0/2,500/5,000/7,500/10,000 stage identity; a periodic mid-episode snapshot continues the live episode. | An evaluation snapshot contains a frozen online policy and provenance, but no optimizer/replay/RNG restoration claim; a resumable checkpoint is accepted only at a verified completed-episode boundary. |
| Decision-cap interruption | Run cap reached on the 10,000th step mid-episode, cap reached at an environment truncation boundary, process/resource interruption before endpoint, restore from older episode checkpoint. | Last valid transition is kept; no synthetic reward/terminal/truncation/reset; exact 10,000 snapshot is evaluable but non-resumable; recovery restores committed counters and RNG and accounts for abandoned wall time without duplicate logical work. |
| Checkpoint/resume | Online/target/optimizer/replay/RNG/counter round trip at episode boundary; deterministic next episode seed; hashes; schema mismatch; missing/truncated/tampered checkpoint; interrupted temp write; previous-good retention. | Restored counters/RNG/replay behavior match the documented boundary contract; corrupt candidate is rejected without destroying previous-good checkpoint. |
| Deterministic smoke | Small fixed transitions and a few CPU updates. | Finite, reproducible targets/loss/action mapping. This is a correctness smoke test, not evidence of useful learning. |
| Evaluation | Frozen checkpoint, epsilon zero, no replay writes/gradients, paired seed/color/opponent identity, truncation vs terminal accounting, cluster-aware paired interval; 10 evaluation seeds × 2 opponents × 2 colors × 1 game = 40 games per snapshot, 15 snapshots total. Warm/scratch keys include `(training_seed, stage, evaluation_seed, opponent_id, agent_color)`; before/after keys include the arm. | Same checkpoint/config reproduces records; all failures/exclusions remain visible; 3 warm pre/post and 3 scratch pre/post pairs exist; warm/scratch and pre/post pairing keys match; config/protocol/matrix game-count consistency test derives 600 games. |
| Comparison controls | Matched protocol, budgets, named RNG stream derivations, Q-head seed, opponents, colors, and evaluation scenarios; divergent policy actions may create divergent data. | Tests/docs do not claim independently trained arms receive identical realized transitions or share identical trajectories. |
| Provenance and policy | Artifact/config hashes, run IDs, compute counters, Stockfish absence, no Stable-Baselines/RLlib, simulator/ALE labeling. | Manifest verifies; forbidden dependencies/claims are absent. |

## Exact target oracle

`tests/fixtures/m5_double_dqn_targets.json` defines the intentional ranking disagreement and arithmetic. Current `tests/test_m5_contract_fixtures.py` checks only that this fixed vector remains internally consistent and that the online-selected UCI differs from the target-network preferred UCI. In M5, `tests/test_m5_targets.py` must drive the actual target calculator with the same case and compare its value to `0.07`; a passing fixture test is not a substitute.

## Test modules and commands for M5

M5 must create implementation modules before claiming their tests ran. Expected focused command:

```bash
uv run --locked --no-sync --project . python -m unittest \
  tests.test_m5_transition tests.test_m5_targets tests.test_m5_replay \
  tests.test_m5_training tests.test_m5_checkpoint tests.test_m5_evaluation \
  tests.test_m2_simulator tests.test_m4_checkpoint -v
```

Then run the complete locked suite:

```bash
uv run --locked --no-sync --project . python -m unittest discover -s tests -v
```

Where `uv` is unavailable, use the repository's already verified locked project interpreter and record exact path, versions, command, timestamp, SHA, exit code, and sanitized log. Do not install dependencies solely to report a passing test. Run preflight, checkpoint-history verifier, compilation, docs-link checks, `git diff --check`, and clean-clone tests on the exact PR revision.

## CI scope

`.github/workflows/preflight.yml` is intentionally a bounded standard-library job. It validates canonical context and context/bundle fixtures; it does **not** install or run PyTorch, the M2/M3/M4 suite, or a Double DQN learner. This Pre-M5 change adds only the pure-standard-library hand-target fixture test to that workflow. No new package installation or broad runtime is justified before an M5 implementation exists. Every future M5 PR must attach exact clean-clone focused and full-suite results; whether a pinned CPU PyTorch job is added should be decided against actual CI runtime/storage once M5 tests exist, without mislabeling this preflight workflow.

## Acceptance ownership

M5-01 owns target/action/terminal/truncation correctness; M5-02 owns simulator reward perspective and transition integrity; M5-03 owns replay/target/exploration/checkpoint-resume; M5-04 owns matched evaluation and comparison; M5-05 owns separation of shaping/curriculum/auxiliary experiments. Synthetic fixtures are preparatory evidence only. The actual learner's tests, outputs, and PR revision are required to pass these criteria.
