# Double DQN Algorithm Contract for M5

**Status:** Pre-M5 engineering specification, 2026-10-28. M5 implementation and training are not authorized or started by this document. The project owner selected independently implemented PyTorch Double DQN as the principal RL algorithm. This specification fixes the initial simulator baseline under ADR-0002, ADR-0003, and the current M2/M4 interfaces; it does not approve G3 or constitute experimental evidence.

**Scope owner:** This file owns M5 algorithm and transition semantics. The M5 comparison protocol owns arm pairing, evaluation, and run budgets. The M05 plan owns sequencing and acceptance evidence. The M2 simulator remains the source of transition truth.

## 1. Model interface and action identity

The initial M5 model is the ADR-0003 action-conditioned scorer with the accepted `videochess-model-input/1.0` input. For state `s`, pass the mover-oriented board planes, six state scalars, complete validated standard-start UCI history, history mask, and the complete current legal candidate set. The online and target networks each emit one finite scalar per supplied legal candidate. During M5 training those outputs are Q estimates trained from simulator rewards; this interpretation belongs to the RL objective and must not be retroactively applied to M4 behavior logits.

Candidate lists are sorted by semantic UCI solely for deterministic batching. A temporary row offset is never persisted as an action ID. A replay record stores the selected UCI string. Before either network scores a state, validate candidate uniqueness, legal membership, turn, and state/history consistency. A terminal state has no candidates and is never passed to an argmax. For a bootstrapped state, the next candidate list must be nonempty.

The initial contract accepts only standard-start games with full history. Custom roots without a versioned root-state representation and complete compatible history are rejected before replay insertion. FEN alone is insufficient for repetition and other history-dependent rules.

## 2. Transition schema and simulator boundary

One transition is one agent move followed by at most one opponent reply, matching one `ChessSimulator.step()` call. The opponent reply is environment transition work, not an agent action, and does not add a second discount step.

Versioned replay record `videochess-ddqn-transition/1.0`:

| Field | Meaning / validation |
|---|---|
| `episode_id`, `decision_index` | Stable run-local transition identity; unique within a run. |
| `seed`, `agent_color` | Episode seed and fixed White/Black perspective. |
| `opponent_id`, `opponent_config` | Exact opponent identity/configuration; invariant within the episode. |
| `state_root`, `history_uci` | Standard root and complete history before agent action; replayed and cross-checked against the observation. |
| `legal_uci` | Unique, sorted, authoritative legal candidates at `state`; nonempty for a live decision. |
| `action_uci` | Exactly one member of `legal_uci`, parsed and revalidated at `step()`. |
| `reward_agent` | `+1` win, `-1` loss, `0` automatic draw or nonterminal transition. |
| `terminated`, `truncated` | Mutually exclusive simulator stop flags. |
| `next_history_uci`, `next_legal_uci` | Complete final history and the model-boundary candidate set after the action/reply. For a live nonterminal state, including a valid time-limit truncation, `next_legal_uci` is the exact sorted authoritative Board legal set. For a true terminal, it is explicitly empty because no bootstrap action exists, even if an automatic draw leaves syntactically legal chess moves on the final Board. |
| `outcome_reason`, `truncation_reason` | Preserve the simulator's explicit termination/truncation reason. |
| `bootstrap_valid` | True only when a verified final nonterminal state and legal candidate set exist. |

`state_root` is the standard initial chess position for version 1. Reconstruct both states by legal replay and check FEN, side-to-move, legal UCI set, agent color, and complete move history. Store opponent identity/config and seed with each episode, not only in a mutable global setting.

Reject the transition if the agent action is illegal/stale, the next state cannot be reconstructed, legal candidates disagree with the Board, history crosses a terminal state, flags conflict, reward perspective is invalid, episode/opponent identity changes, or the opponent policy raises/returns an illegal action. The simulator rolls back failed agent+opponent steps; such failures are logged as invalid episodes and never synthesized into draws, terminals, or replay rows. A pre-step record is committed to replay only after a complete `StepResult` and all checks pass.

## 3. Reward, discount, termination and truncation

Use the existing unshaped M2 reward from the fixed agent-color perspective:

| Result | `reward_agent` |
|---|---:|
| Agent wins | `+1` |
| Agent loses | `-1` |
| Automatic draw | `0` |
| Nonterminal step | `0` |

Do not negate rewards by side-to-move; the agent color stays fixed for an episode. A reward is credited on the transition that produces the chess outcome. Nonterminal `StepResult.reward` must be zero. The initial baseline uses no shaping and no Stockfish-derived reward or target.

The discount is per agent decision, including the opponent reply in that simulator step. Proposed starting `gamma = 0.99`; it is a versioned experiment configuration value, not a claim of optimality.

For a true chess terminal (`terminated=true`), the bootstrap mask is zero even if the terminal Board has syntactically legal moves (for example, an automatic draw). Replay validation still reconstructs the complete final Board/history and verifies `Board.outcome(claim_draw=False)` and the simulator's outcome reason. It must not require the raw Board legal set to be empty for such a draw. The MDP/model-boundary `next_legal_uci` candidate set is empty because the state is terminal, and no model call, max, or argmax is evaluated. For a nonterminal transition or a valid time-limit truncation, `next_legal_uci` must exactly match the sorted Board legal UCI set and must be nonempty.

For the existing M2 `max_agent_decisions` time-limit truncation, if `StepResult.observation` and its complete history/legal set are valid and the Board has no automatic terminal outcome, set `bootstrap_mask=1` and bootstrap from that final observation. This is a continuing-task time limit; do not convert it into a terminal draw. `terminated` and `truncated` must not both be true. A runner interruption, process crash, failed opponent action, missing/invalid final observation, or unverifiable state is an invalid incomplete transition and is discarded, not bootstrapped and not converted into a synthetic terminal.

## 4. Double DQN update

For transition `i`, derive the legal next UCI set from its verified next state. If bootstrapping is valid, the online network selects the next semantic action:

```text
a_star = argmax over legal_uci(next_state)
         Q_online(next_state, action)

target = reward_agent
       + gamma * bootstrap_mask
         * Q_target(next_state, a_star)
```

`bootstrap_mask` is `0` for true chess termination and `1` for a valid nonterminal transition, including a valid time-limit truncation. It is not inferred from an empty or nonempty tensor alone.

The online and target networks may independently return candidate scores, but the selected action is carried as UCI. Find that same UCI in the target result and evaluate its target score. Fail loudly if the UCI candidate sets differ. Never select an online array offset and apply the same offset to the target candidate list; list order is not action identity. For `Q(s,a)`, similarly map the recorded `action_uci` to exactly one current legal candidate and gather its online scalar.

Tie-breaking for exact finite equal scores chooses the lexically first UCI string. Reject NaN/Inf legal scores before argmax; padded entries are excluded before both selection and loss. Do not use an arbitrary large finite padding score that could win. Reject a bootstrapped transition with no valid legal next action.

### Hand-calculated required test vector

With legal next actions `[b1c3, g1f3]`, online values `{b1c3: 0.4, g1f3: 0.8}`, target values `{b1c3: 1.7, g1f3: -0.2}`, reward `0.25`, and `gamma=0.9`, online selects `g1f3` and the target must evaluate `g1f3`, producing `0.25 + 0.9*(-0.2) = 0.07`. Evaluating the target's own preferred `b1c3` would be the wrong algorithm. A reusable fixture is `tests/fixtures/m5_double_dqn_targets.json`; it is a future implementation oracle, not evidence that the learner exists.

For a terminal reward `-1`, target is `-1` regardless of any target-network values. For a valid truncated final state, use the same legal UCI selection/evaluation rule as any other valid nonterminal state. Invalid transitions are excluded before this calculation.

## 5. Replay, optimization and target schedule

Replay stores validated versioned semantic transitions, not position-specific candidate indexes. The initial proposed configuration is in `configs/rl/m5-double-dqn-v1.json`; it proposes capacity 4,096, batch size 32, warmup 512 valid transitions, one gradient update per four agent decisions, AdamW, learning rate `1e-4`, gradient norm clipping `1.0`, and hard target synchronization every 500 gradient updates. These are bounded starting defaults to validate, not accepted performance-optimal hyperparameters.

Sample transitions deterministically from an explicitly seeded replay RNG. The run manifest records insertion and sample counts, episode and transition IDs, and RNG states. Build batches from validated current and next states; group/pad variable histories and candidates with boolean prefix masks. The loss is mean Huber (Smooth L1) loss between gathered online `Q(s, action_uci)` and detached Double DQN targets. Zero gradients once per optimizer update, check finite targets/loss/gradients/parameters, clip gradients before the step, then increment the gradient-update counter exactly once. No gradient accumulation is used in the baseline.

The target network starts as an exact copy of the post-initialization online network. It is held in evaluation mode and receives no gradients. Hard synchronization copies the complete online Q network after the configured number of completed gradient updates. Record the sync counter. If a future soft update is tested, it is a separate configuration and experiment.

Exploration is epsilon-greedy over sorted legal UCI actions: with probability epsilon choose uniformly from that current legal set using the run RNG; otherwise select the online argmax with the deterministic UCI tie rule. The starting schedule is linear from `1.0` to `0.05` over the first 7,500 agent decisions and then fixed. The decision counter, epsilon value, and RNG state are checkpointed. Evaluation always uses epsilon `0` and separate deterministic seeds.

## 6. M4 initialization and independent baseline

Warm-start initialization uses the accepted M4 behavior-only checkpoint only after its SHA-256, sidecar, schema, and dataset provenance pass verification. Copy the board encoder, history embeddings/GRU, metadata projection, candidate encoder, and shared hidden scorer. Do not copy the `behavior_head`, M4 optimizer state, or behavior probabilities as Q values. Initialize a new scalar Q head using the configured seed. Initialize the target network from the fully transferred online Q network after the Q head has been initialized.

The random-initialized DDQN control uses the same M5 scorer architecture, initializes its representation independently, and uses the same paired-seed-derived Q-head initialization seed as the warm arm. Preserve both arms' exact pre-RL initialization snapshots before any RL optimizer update. Within a warm/scratch pair, match the simulator/reward contract, episode-seed, opponent-RNG, exploration-RNG and replay-sampling seed streams, colors, opponent mixture, replay/update protocol, and decision/update budgets. The policies will generally visit different states and generate different transitions because their actions can differ; **do not claim identical realized trajectories or transition contents**. A shared random stream means the same stream derivation and initial seed, not the same sequence of observed states or replay rows. Record actual transitions independently for each arm. M4 behavior-only stays a frozen policy arm, not a Q network. Do not derive Q initialization from Stockfish centipawn scores or M4 logits.

## 7. Training counters, evaluation and reproducibility

Maintain monotonic committed counters for completed episodes, valid/invalid transitions, agent decisions, optimizer updates, and target syncs. Also record attempted and abandoned work separately; abandoned work is not included in committed learning counters. Exploration and learning schedules use their own documented counters. Every evaluation episode uses the frozen policy, `epsilon=0`, no replay insertion, and no optimizer changes.

The primary controlled endpoint is a predeclared fixed number of valid agent decisions for each paired DDQN arm. Do not select the primary model by held-out test results or selectively stop a poor seed. Safety hard stops (nonfinite state/target/gradient, invalid state, resource cap, or persistent transition failure) preserve the last valid episode-boundary checkpoint and mark the run incomplete. A failed paired arm makes that paired comparison incomplete; never present unequal actual budgets as a controlled initialization comparison.

Every run records code/config hashes, source revision/dirty status, environment/library versions, hardware, fixed agent colors, seeds/RNG state, exact opponent identities/configurations, state/action/transition counts, replay and update schedules, evaluation identity, artifact hashes, wall time, memory, stop reasons, and all excluded/error rows. Simulator outcomes remain separate from ALE metrics. No Stockfish engine is imported or invoked for inference, opponent play, or reward generation.

## 8. M5 checkpoint and resume contract

M5 defines two distinct artifact classes. Neither may be described as the other. Filenames follow `configs/rl/m5-double-dqn-v1.json` and include run, arm, seed, attempt, stage/counters, and an explicit `eval-snapshot-v1` or `resume-v1` suffix. The schemas, names, purposes, and validators are distinct. Attempt-segment records use the `incomplete.json` suffix and never masquerade as a transition or checkpoint.

### 8.1 Evaluation/model snapshots

`videochess-ddqn-evaluation-snapshot/1.0` is a frozen, **non-resumable** policy artifact. Capture it at exactly 2,500, 5,000, 7,500, and 10,000 committed valid agent decisions. The decision counter increments only after a complete simulator step has been validated and its transition inserted into replay. At that same decision, first perform the configured gradient update if due and the target synchronization if that update reaches a sync boundary; then capture the snapshot. Thus the snapshot describes the online model after all work scheduled by that decision. It records online weights and their hash, target-network hash and target-sync counter as provenance, run/arm/paired-seed/init/checkpoint IDs, config/code hashes, model/input/transition schema, decision/transition/update/episode counters, and capture order. Evaluation uses only the frozen online weights with epsilon zero; it performs no updates. The target hash identifies the training state but is not used by policy evaluation. A snapshot omits optimizer, replay, and RNG restoration state and **must never be advertised as resumable**. In particular, the exact 10,000-decision primary policy is an evaluation snapshot, not a training checkpoint.

Capture initialization snapshots for all three warm and all three scratch seeds after their complete initialization procedure (including fresh Q-head initialization and target copy) and before the first RL gradient update. These are evaluation-valid policy snapshots at decision zero. Pair them with the post-RL policy using the stable `(arm, training_seed, stage)` identity. The frozen M4 behavior policy is a separate baseline and is not a DDQN initialization snapshot.

### 8.2 Resumable training checkpoints

Future `videochess-ddqn-checkpoint/1.0` bundles are full training-state artifacts. They must preserve:

- schema and model/input/transition/replay schema versions;
- online and target state dictionaries;
- optimizer state and any scheduler state;
- replay contents or an integrity-verifiable append-only replay journal;
- completed episode, valid transition, agent decision, gradient update, and target-sync counters;
- epsilon schedule/configuration and its counter;
- Python, NumPy, PyTorch CPU/CUDA and replay RNG states;
- run seed, fixed agent color, opponent ID/config, and episode boundary;
- M4 source artifact hash and dataset/model identity for warm-start runs, or explicit random-init identity;
- code revision, canonical configuration/hash, runtime provenance, and artifact checksums.

Write a resumable checkpoint after every completed episode, after the final transition, due optimizer update, and any target synchronization. Resume only from such a verified episode boundary. Derive each episode seed deterministically from the run master seed, stable run ID, and next completed-episode index using the versioned config rule; restore RNG and committed counters before starting that episode. Do not promise exact mid-episode recovery: simulator state, board, opponent-private state, and all episode-local RNG continuation are not currently serialized.

Name every artifact immutably with the configured run/arm/seed/attempt identity. Write a new data bundle to a unique temporary sibling, flush and `fsync`, then atomically rename it to its final versioned path. Write the manifest through its own temporary sibling and atomic rename, verify all hashes/schema/counters, and only then atomically update the `latest-resume.json` pointer. Never overwrite or remove the prior verified checkpoint; a crash before pointer publication leaves the previous pointer usable and the unreferenced candidate diagnosable. Evaluation snapshots are likewise immutable data-plus-manifest artifacts but never update the resume pointer. Reject missing, truncated, incompatible, nonfinite, or hash-mismatched artifacts before mutating a live run.

At every configured 2,500-decision milestone, finish and validate that one `ChessSimulator.step()` call, insert its real transition, increment the committed decision counter, perform any due update and target sync, then write the frozen evaluation-valid snapshot. If the episode is still live, continue the same training episode from its actual simulator state; the snapshot itself does not contain state needed to resume training. If the milestone coincides with a true simulator terminal/truncation boundary, preserve those flags and write the separate full resumable checkpoint. Only the final 10,000-decision endpoint stops the run. If that final step is still in a live episode, preserve its valid transition and snapshot, stop before another agent action, and record an incomplete-episode run-end event with the last committed transition ID. Do **not** set `terminated` or `truncated`, add a reward, synthesize an outcome, or reset the simulator. The latest resumable checkpoint remains the latest completed-episode checkpoint, which may have a lower committed counter than the evaluation snapshot. At the exact 10,000 endpoint, the run is complete at its authorized decision cap; the snapshot is the primary evaluation model and no resume is required.

If a process interruption occurs mid-episode before a hard cumulative resource cap is exhausted, preserve a distinct attempt-segment record with attempted decisions, last complete step, wall time, and incomplete episode status. Recover only from the latest verified episode-boundary checkpoint. Restore its model, target, optimizer, replay/journal, RNG, exploration state, and committed counters; deterministically replay work since that checkpoint. Do not count abandoned/replayed work twice in logical training counters. Keep physical time from every attempt in the cumulative per-run and campaign budgets. If a wall-time or memory cap is exhausted, stop and mark the run incomplete; do not resume by exceeding the cap. Snapshots from an abandoned attempt remain immutable evidence but are marked superseded and cannot be selected as the final policy. Never advance from snapshot counters while restoring older replay/optimizer state.

Save each new bundle to a temporary sibling, flush/fsync, atomically rename, write and verify an integrity manifest, then retain the previous good checkpoint until the new one verifies. Reject missing, truncated, incompatible, nonfinite, or hash-mismatched bundles before mutating a live run. A wall-time guard is checked before beginning every new simulator decision; if an active episode is abandoned for resource limits, it follows the same incomplete-attempt recovery rule. A failed opponent/simulator step is not a valid decision and yields no replay transition. Actual M5 serialization/recovery implementation and tests belong to M5.

## 9. Failures and non-goals

Invalid candidate/action identity, a malformed history, inconsistent observation, impossible `terminated/truncated` flags, nonfinite Q values/targets/loss/gradients, stale episode identity, or corrupted checkpoint is a hard error with the offending transition/run retained in sanitized diagnostics. Do not turn those cases into reward zero, an automatic draw, a terminal mask, or a successful transition.

This contract does not implement a learner, train a Q network, authorize M5, approve G3, evaluate ALE, introduce reward shaping/curriculum/auxiliary losses, or claim that behavior imitation proves RL gains. Any such change requires an explicit separately named and authorized experiment.
