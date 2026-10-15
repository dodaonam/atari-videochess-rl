# Project Requirements and Decision Register

**Status:** G0, G1 and G2 are approved. Live gate/task status and milestone authorization are owned by [project state](../../.agents/state/PROJECT_STATE.yaml).
**Purpose:** Consolidate the project baseline from [`ROADMAP.md`](ROADMAP.md) and `chat_history.md` while distinguishing source-stated constraints, proposed choices, and open approvals.

## 1. Status labels and authority

- **Source-stated baseline:** stated as a requirement or objective in project materials. It records what the project currently says; it does not prove an instructor, assignment brief, external service, or runtime has confirmed it.
- **Proposed design:** a recommended implementation or experiment. It remains adjustable based on tests and evidence.
- **Open confirmation:** a policy, permission, deadline, or runtime fact that needs user/instructor confirmation or direct verification.

The roadmap is preserved verbatim and remains the source for original research direction. This file is the concise register of current project constraints and unresolved approvals. Detailed gate criteria are canonical in [`docs/06-quality/ACCEPTANCE_CRITERIA.md`](../06-quality/ACCEPTANCE_CRITERIA.md). The G/M crosswalk and its rationale are owned only by [`ADR-0001`](../02-management/decisions/ADR-0001-governance-crosswalk-and-file-priorities.md); milestone order, dependencies, deliverables, and the fixed-file inventory are owned by [`EXECUTION_PLAN.md`](../02-management/EXECUTION_PLAN.md). If sources conflict, preserve both claims and resolve the conflict explicitly before dependent work.

## 2. Project objective

Design, implement, train, and evaluate a chess-playing reinforcement-learning agent whose target environment is ALE `VideoChess-v5`. The roadmap's research direction is Stockfish-assisted supervised pretraining followed by a separately measured reinforcement-learning stage and evaluation on Atari Video Chess.

Keep three evidence tracks distinct:

1. **Supervised pretraining:** the model learns from expert/Stockfish-derived labels. This is not, by itself, reinforcement learning.
2. **Simulator RL:** the agent learns from rewards/transitions in a `python-chess`-based simulator. This demonstrates simulator learning, not Atari interaction.
3. **Atari evaluation or fine-tuning:** observations and outcomes come from ALE/VideoChess. A `python-chess` shadow board may track history or cross-check state, but must not replace the Atari observation as the source of truth.

The primary academic goal is a technically sound, reproducible result that measures pretraining and RL separately. Competitive strength near 1500 Elo is aspirational, not promised.

## 3. Source-stated baseline requirements

The following is the current baseline **as stated by the roadmap and chat history**. Assignment-specific permissions remain open under §6.

| ID | Baseline | Required interpretation | Source basis |
|---|---|---|---|
| B-01 | Target environment is ALE `VideoChess-v5`. | Verify the installed environment's observations, actions, rewards, and termination behavior before relying on source-described details. | Roadmap §§ I, III, XII. |
| B-02 | Atari board-state extraction and an action wrapper are allowed by the project plan. | Use extracted state for chess-level decisions and translate moves into Atari actions; verify both against the emulator. | Roadmap §§ I, III–IV, XII. |
| B-03 | The RL algorithm is to be implemented directly with PyTorch; Stable-Baselines and Ray RLlib are excluded by the roadmap. | Do not substitute an RL framework unless the user explicitly changes this constraint. | Roadmap § I. |
| B-04 | Stockfish may provide training labels/opponents but must not be part of the agent's inference path. | The deployed policy selects moves without calling Stockfish. Offline engine evaluation still needs the assignment-policy confirmation in §6. | Roadmap §§ I, VIII, XI–XIII; chat history. |
| B-05 | Simulator and Atari evidence are distinct. | Identify the environment and method alongside every result; never label simulator results as Atari performance. | Roadmap §§ II, IX–XIII; chat history. |
| B-06 | The roadmap reports ALE terminal reward from White's perspective. | Verify the installed environment's behavior and convert reward consistently to the acting agent's perspective, including when playing Black. | Roadmap §§ III, V, XII. |
| B-07 | Experiments must be reproducible and evidence-backed. | Record source revision, config, seed, runtime/dependency versions, dataset identity, metrics, and checkpoint/artifact references. Do not invent or extrapolate results. | Roadmap §§ I, IV, XV, XVIII; chat history. |
| B-08 | Evaluation includes baselines and comparison of pretraining-only and post-RL models. | Preserve separate checkpoints and use the same stated conditions; report lack of improvement honestly. | Roadmap §§ VI, IX–XIII. |
| B-09 | The roadmap's technical target includes a functioning Atari interface and full-game evaluation. | A simulator fallback is a disclosed contingency, not an approved waiver of the Atari objective. | Roadmap §§ I, XII, XVI, XVIII–XIX. |

## 4. Proposed design choices (not frozen requirements)

These are starting points to test, not decisions proven optimal:

- An action-conditioned afterstate Q-network that scores legal chess moves, with Double DQN fine-tuning.
- `python-chess` as simulator/rule implementation, with a separate ALE adapter.
- Terminal-outcome reward as the initial simulator baseline; potential-based shaping only as a separate experiment.
- A small CNN and proposed feature planes; network size, channels, optimizer, and learning rates are initial values only.
- Stockfish evaluation transformed into supervised targets, including candidate `tanh` normalization. Teacher scores are not automatically calibrated Q-values or win probabilities. Verify perspective, sign, scale, and relationship to RL rewards before TD updates.
- PGN, tactical-position, and agent-generated examples. Suggested dataset sizes are trial scales, not strength guarantees; split by source game/position group to avoid leakage.
- **Proposed M3 primary PGN candidate:** the third-party Lichess Elite Database monthly archive for May 2022. Its listing describes a filtered collection of standard Lichess games, excluding bullet and, since December 2021, using a 2500+ versus 2300+ rating filter; it reports 355,535 games and 93 MB for May 2022. These are source-reported listing values, not locally confirmed archive metadata. The archive has not been downloaded, ingested, or approved. The third-party listing does not state a dataset license; the CC0 terms published for Lichess’s official database exports do not by themselves establish the terms for this filtered third-party package. Preserve O-06 until source identity, provenance, license, permitted use, and expected scope are verified and approved. See the [candidate listing](https://database.nikonoel.fr/) and [official Lichess open database terms](https://database.lichess.org/).
- Opponent pool/curriculum; Atari fine-tuning only after stable integration and throughput evidence.
- Local CPU for environment/preprocessing and Colab GPU for workloads that benefit. Free T4 availability depends on current entitlement, quota, and capacity.
- Separate low-variability development settings from ALE evaluation. The roadmap's cited `frameskip=4` and sticky-action probability `0.25` must be checked against the installed ALE version; debug settings are not default-environment results.
- `uv`, a dependency lockfile, CI, experiment registry, and persistent artifact storage are operational recommendations to audit during M0, not G1 commitments.

## 5. Governance and acceptance status

### G0 — Documentation Foundation Bootstrap

The user reviewed and approved `AGENTS.md`, `ROADMAP.md`, and this `REQUIREMENTS.md` on 2026-10-14. The roadmap extraction and G0 criteria are retained as historical evidence; this approval does not close the open confirmations in §6.

### G1 — Persistent Agent Context and Governance Bootstrap

G1 was authorized, its hardening and independent-session acceptance were completed, and the user approved the gate on 2026-10-14. Verification is retained in `.agents/evidence/G1-hardening-verification.md` and `.agents/evidence/G1-10-recovery-verification.md`. Read `.agents/state/PROJECT_STATE.yaml` and the latest direct user instructions for live task scope and authorization. M0 follows G1 in the engineering sequence; gate approval alone does not resolve assignment, runtime, data-use, or compute approvals. Open approvals O-01 through O-08 remain unresolved.

### G2 — Technical Feasibility

The M1-01 through M1-06 acceptance and G2 approval are recorded in [M1/G2 final verification](../../.agents/evidence/M1-G2-final-verification-20261016.md). This does not authorize M2; the current state and M2-001 task record its separate user-authorization requirement. O-01 through O-08 remain unresolved.

### Engineering milestones

Detailed acceptance criteria for M0–M7 are maintained only in [`ACCEPTANCE_CRITERIA.md`](../06-quality/ACCEPTANCE_CRITERIA.md). The engineering sequence and dependencies are maintained only in [`EXECUTION_PLAN.md`](../02-management/EXECUTION_PLAN.md). Read `.agents/state/PROJECT_STATE.yaml` for the current milestone and authorization status. G1 authorization does not resolve any open academic or external-service questions.

## 6. Open approvals and evidence needed

These items remain unresolved. Do not present them as approved until the user/instructor or primary evidence resolves them.

| ID | Open item | Resolution path | Why it matters |
|---|---|---|---|
| O-01 | Assignment/instructor rules for ALE observation extraction, action wrappers, custom PyTorch RL, Stockfish training use, and any engine use in offline evaluation. | User/instructor confirmation. | Establish permitted project scope. |
| O-02 | Whether full-game performance on actual ALE is a hard submission requirement or a research target with an accepted fallback. | User/instructor confirmation. | The roadmap calls Atari technical play mandatory but describes a simulator fallback if integration fails. Until clarified, retain full-game Atari as the target and fallback only as a disclosed limitation. |
| O-03 | Whether the approximate three-week estimate is still the project deadline. | User confirmation. | The roadmap gives no fixed dates. |
| O-04 | Actual Colab entitlement/quota, GPU availability, storage, and whether paid compute is allowed. | Verify free quota in M0; user approval for paid compute. | Free T4 availability is not guaranteed. |
| O-05 | ALE/ROM runtime behavior, RAM mapping, game modes, difficulty behavior, and official evaluation settings. | Verify against permitted primary sources and authorized runtime work; user confirms assignment constraints. | The installed ALE-Py 0.11.2 package's `video_chess.bin` ROM is locally present and accessible (M0 evidence). This does not establish assignment permission or the remaining runtime/evaluation details. Do not infer RAM offsets or mode meanings without evidence. |
| O-06 | PGN/tactical data sources, licenses, permitted use, and expected scale. | User approves source/use policy; verify license/provenance before ingestion. | Needed for a valid and shareable dataset. |
| O-07 | Stockfish version/search limits and whether it may be a benchmark opponent or offline evaluator. | Verify current version at setup; user/instructor confirms allowed roles. | Versions change and assignment rules may restrict evaluation use. |
| O-08 | Opponent pool and rating method for any Elo claim. | User approval in the evaluation plan. | Elo is meaningful only relative to defined, calibrated conditions. |

## 7. G1 decisions resolved under the user's authorization

The chat history's G/M mapping and plan-priority inconsistencies were resolved for project governance in [`ADR-0001`](../02-management/decisions/ADR-0001-governance-crosswalk-and-file-priorities.md). [`EXECUTION_PLAN.md`](../02-management/EXECUTION_PLAN.md) is the canonical fixed-file inventory. Earlier classifications remain in `chat_history.md` as historical records and are superseded for future planning. This does not resolve O-01 through O-08.

## 8. Current scope boundary

Current task scope is defined by the latest direct user instructions and canonical project state. Do not start M0/M1, install dependencies, run RL, or allocate Colab resources unless the current request and state authorize them. Preserve the README and existing user files. Commit or push only when directly authorized by the user.
