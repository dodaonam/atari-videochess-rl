# PRE-M6 — Atari Integration Readiness and Handover

**Status:** Engineering readiness plan/evidence only. M6 is pending separate authorization, has no active task, and has not started. **Baseline:** `initial-idea` HEAD `07d476989f9300ff7639c2bf3476959298947553`, tree `4bc476ad011e388a40a16ed099dd2118275d9115`. PR #11 merged at `e0b434530df51b08595e3896c175f81b4a8f8c64`; PR #12 merged at the baseline and records G3 approval.

## 1. Bounded readiness scope

Audit accepted M2–M5 inputs, validate available private artifacts read-only, repair current-status and verification provenance, establish the M5/ALE contract, run offline frozen-policy compatibility and regression checks, and hand off an executable M6 plan. Do not run ALE gameplay, change accepted experiment data/results, train, tune, or activate an M6 task. Canonical state/backlog remain authoritative; current schema has no readiness task type, so this plan/evidence carry the readiness work without inventing a task ID.

## 2. Audited dependency matrix

| Dependency/capability | Status | Evidence / consequence |
|---|---|---|
| G3 approval and M2–M5 acceptance | Complete/approved | `.agents/evidence/G3-final-approval-20261030.md`, `.agents/evidence/M5-PM-acceptance-20261030.md`; PR #11/#12 merged into baseline. |
| M1 ALE environment, RGB parser, cursor/controller, shadow and bounded runner | Implemented and previously real-ALE tested | `environment.py`, `vision.py`, `controller.py`, `shadow.py`, `episode.py`; M1 evidence. Runner is White-side only; terminal screen may not parse. |
| M5 Double DQN frozen snapshot loader and Q policy | Implemented; offline compatibility verified in this mission | `rl/checkpoint.py`, `rl/network.py`, `rl/evaluate.py`; private selected snapshot and manifest. Q values are not M4 behavior logits. |
| Atari RGB observation + full-history M5 policy invocation | Missing integration adapter | M1's selector receives a `chess.Board`; M5 policy requires an observation with complete `history_uci`, FEN, side, and exact candidates. Specify here; wire/test in M6. |
| Default v5 profile | Prior configuration and small real-ALE evidence | frameskip 4, sticky probability 0.25. Existing tests show only limited cycles; M6 must verify runtime profile and reliability. |
| Human-readable mode/difficulty semantics | Open | use raw mode 4/difficulty 0, no skill label. O-05 runtime/assignment setting details remain for M6 entry verification. |
| Atari Black-side play | Not implemented | M1 code enforces White turns. Start M6 White only; do not claim both-color Atari evaluation. |
| Complete-game policy outcomes | Not established for accepted RL policy | M1 has terminal traces for diagnostics; no M6 M5-policy games exist. |
| Private accepted M3/M4/M5 bytes | Available locally and independently hash checked this session | Details in readiness report; keep external/private. Clean clones cannot inspect them. |
| G4/M7 evaluation or release | Not approved/started | M6 evidence may inform later G4/M7 review; no G4 approval or publication. |

## 3. M6 implementation order

1. Verify current direct M6 authorization, G3 state, approved M5 identities, source baseline and local artifact manifests. Copy—not edit—the frozen policies into a locked read-only evaluation roster.
2. Implement a narrow M6 adapter around `load_evaluation_snapshot`, existing `QPolicy`, `ShadowBoard`, RGB evidence and `run_episode`. Use complete verified move-stack UCI history and exact legal candidates; do not create a second vision/model/rules implementation.
3. Add pure tests for full-history observation contracts, candidate/action validation, stale or ambiguous RGB, shadow non-mutation on failure, terminal/truncation/incomplete accounting, checkpoint mismatch/corruption, deterministic inference and weight immutability.
4. Run Stage 1 with deterministic debug profile only after confirming it is within M6 authorization. A genuine ALE observation and verified action is required; a mock is not acceptance evidence.
5. Run Stage 2 bounded consecutive turns and genuine Atari replies; establish timing and reliability. Stop on ambiguity, desynchronization, uncertain FIRE, or timeout; no retry after action.
6. Run the bounded full-game roster and both declared profiles in separate result groups; verify outcomes from ALE flags/reward and preserve incomplete games.
7. Verify source/config/checkpoint/ROM/trace manifests, summarization denominators and hashes. Re-run tests and preflight at exact final M6 HEAD.
8. Submit evidence for independent PM acceptance against M6-01–05; no executor self-approval or implicit G4/G5 closure.

Detailed schemas and failures are in [`M5_ALE_INTEGRATION_CONTRACT.md`](../../docs/03-technical/M5_ALE_INTEGRATION_CONTRACT.md); roster, metrics, runtime profiles, stages and resource caps are in [`M6_ALE_EXPERIMENT_PROTOCOL.md`](../../docs/04-research/M6_ALE_EXPERIMENT_PROTOCOL.md).

## 4. M6 criterion evidence map (criteria are NOT passed by this readiness plan)

| Criterion | Components / prerequisites | Required tests | Required genuine ALE evidence / artifacts | Pass and failure conditions | Phase / principal risk |
|---|---|---|---|---|---|
| M6-01 | M1 RGB/vision/shadow + full-history M5 adapter + frozen snapshot | Reject incomplete history, FEN/side/candidate mismatch; model called only after stable RGB validation | Decision trace ties observation frame/hash to verified board/history and selected snapshot; raw/compact RGB evidence | Pass when every inference input derives from ALE RGB-verified state and shadow only validates/tracks. Fail on simulator/shadow-only decision, guessed history, or mismatched evidence. | Stages 1–3; RGB cannot establish all chess metadata alone, so preserve full verified history. |
| M6-02 | `run_episode`, controller, typed stop outcomes and per-turn trace | Happy path plus stale/ambiguous evidence, desync, interrupted control, timeout, illegal output, truncation, terminal-screen clearing | Multiple consecutive player moves and actual Atari replies, with all phases/frame numbers and preserved last verified state | Pass when observe→validate→decide→execute→verify repeats and every uncertain path stops without advancing. Fail on unverified advancement/retry or missing stop trace. | Stages 1–3; sticky inputs/controller timing. |
| M6-03 | Frozen `QPolicy`; M5 loader; inference dependency review | Check no Stockfish/optimizer/replay path; model immutable and deterministic for identical validated input | Policy/config/code identity in actual ALE traces; no engine process in runtime record | Pass when inference is frozen Q scoring, no Stockfish/training. Fail if any engine or optimizer affects a choice. | Every stage; M4 behavior policy remains separate control. |
| M6-04 | Game ledger, ALE flags/reward conversion, trace writer and hash manifest | Denominator/unit tests, unknown-terminal and incomplete accounting, hash-chain tamper test | Bounded completed games plus incomplete attempts with W/D/L, moves, desync, settings, trace/hash and reward flags | Pass when every attempt is accounted for, raw evidence retained, no incomplete counted as draw. Fail on inferred outcome or missing required provenance. | Stage 3; terminal RGB may be unreadable and reward perspective must remain explicit. |
| M6-05 | Immutable profile config and ALE runtime capture | Config validation, actual runtime values match requested values | Debug and default-v5 runs stored in separate groups; `ALE/VideoChess-v5`, ROM, mode/difficulty and actual ALE settings recorded | Pass when settings are asserted and results not pooled across profiles. Fail on assumed defaults or debug results reported as evaluation. | Stages 1–3; default-v5 population reliability not yet known. |

## 5. M6 entry conditions

### Hard entry conditions

- Separate direct owner/PM authorization to start M6; this readiness work does not grant it.
- Independent PM review/acceptance of this preparation PR and explicit decision about merge; no self-approval.
- Clean, known M6 base/branch and canonical state still showing no active M6 task until authorization.
- Reverify required Warm/Scratch/M4 artifacts, schemas, sidecars and SHA-256 immediately before M6; the selected warm and paired scratch hashes in the companion protocol must match.
- Freeze the roster/config/code/seed plan before any M6 result; verify the installed ROM/runtime/profile and ensure M6 task-specific Atari runtime execution is authorized.
- Confirm there is no external authoritative assignment restriction contradicting the planned ALE control/observation path. No external service, paid compute, upload, training, or Stockfish use is implied.

### Acceptable with explicit PM acknowledgement

- RSK-014: M5 source aggregates differ and complete historical `cli.py` bytes remain unavailable; the independent PM accepted M5-03/M5-04 with limitations. Use new M6 source bundle/config/checkpoint/runtime provenance.
- No default-v5 full-game M5 policy result or Atari Black-side path exists before M6; these are objectives of M6, not circular entry requirements.
- O-02 full-game submission/fallback and O-05 exact official mode/profile assignment details remain open. The target stays Atari full-game evaluation, use raw evidenced mode and settings, and do not claim a fallback waiver.
- Colab availability/quota is owner-reported only. Begin locally; external runtime/cost/storage requires its own authorization.

### M6 internal validation (not pre-entry blockers)

Single-decision genuine ALE check, consecutive reply cycles, controller reliability under sticky actions, bounded full games, mode/profile sensitivity, trace replayability, and terminal/reward accounting are required inside M6. Requiring these before M6 would be circular.

### Deferred beyond M6 / M7-only

Calibrated opponent pool and Elo (O-08); formal comparative-strength claims; delivery/report/model card/publication and any artifact redistribution; Atari fine-tuning or new M5 campaigns; broad Black-side support unless separately scoped.

## 6. PRE-M6 acceptance mapping

PM6-R01 through PM6-R10 are adjudicated in [`PRE-M6-readiness-report-20261030.md`](../evidence/PRE-M6-readiness-report-20261030.md). They are readiness dispositions, not PM acceptance and not M6 criteria. Independent reviewer should verify the exact branch head, artifact identities, test logs, residual RSK-014 wording, PR-only workflow, and canonical state. M6 remains pending authorization irrespective of readiness disposition.
