# Pre-M2 Preparation Verification

**Scope:** Documentation, proposed architecture, task discoverability, and context recovery only. This record does not complete M2, approve G3, or authorize implementation.

**Source revision reviewed:** `0f4c49f322115194f0146fe7719c5447da996fc6` on `initial-idea`.

## Preparation outcome

The six required Pre-M2 documents and proposed [ADR-0002](../../docs/02-management/decisions/ADR-0002-chess-mdp-action-and-perspective.md) were prepared from the current source, tests, M1/G2 evidence, acceptance criteria, requirements, execution plan, and locked dependency metadata. The full M1 implementation remains the only implemented Atari component. M2–M7 implementation remains out of scope.

The MDP recommendation is deliberately provisional: retain full python-chess history; represent legal moves by stable semantic keys; expose current-position and announced-move draw claims as typed actions; keep one fixed agent color per episode; define rewards from that agent's perspective; and use one agent move plus at most one opponent reply per decision transition. The action-conditioned legal-candidate scorer is proposed because a variable legal list index cannot serve as a stable global Double DQN action ID. User review of ADR-0002 and separate M2 authorization remain required.

The May 2022 Lichess Elite third-party archive is recorded in [REQUIREMENTS.md](../../docs/01-foundation/REQUIREMENTS.md) as a source-reported candidate only. It was not downloaded or ingested. O-06, O-01 and O-07 remain unresolved.

## Files prepared

New technical and plan documents:

- [M02-chess-foundation.md](../plans/M02-chess-foundation.md)
- [ARCHITECTURE.md](../../docs/03-technical/ARCHITECTURE.md)
- [MDP_SPEC.md](../../docs/03-technical/MDP_SPEC.md)
- [ALE_ENVIRONMENT.md](../../docs/03-technical/ALE_ENVIRONMENT.md)
- [BOARD_EXTRACTION.md](../../docs/03-technical/BOARD_EXTRACTION.md)
- [ACTION_ADAPTER.md](../../docs/03-technical/ACTION_ADAPTER.md)

The proposed ADR is linked above. Existing-document changes update the provisional Lichess source direction, M1/G2 evidence references, M2 verification design, and relevant risk descriptions. Canonical state, backlog, and handoff point to pending M2-001 and preserve the user-authorization boundary. No Python source, tests, README, roadmap, or acceptance criteria were changed.

## Validation

The final context/export test run used the repository's Python 3 environment and the exact command below. The retained log includes start/end UTC, elapsed time, full output, and exit status:

| Command | Executed (UTC) | Result | Retained log | SHA-256 |
|---|---|---|---|---|
| `python3 -m unittest tests.test_agent_context tests.test_export_review_bundle -v` | 2026-10-15 19:42:12–19:43:17 | PASS, 57 tests, exit 0, 65.11 seconds wall time (64.738 seconds reported by unittest) | `logs/PRE-M2-context-export-final-20261016.log` | `750fea11c16ff4dc849b913a1ce3ce4b6798cb94cee0e878f13b5cf621445529` |
| `python3 scripts/agent_preflight.py` | 2026-10-15 19:45:55 | PASS, exit 0, 0.39 seconds | `logs/PRE-M2-preflight-final2-20261016.log` | `0641512be6308b9cb483a3013a0802008d3ed72f45b1a36b30dfc55ac837723e` |

An earlier pre-checkpoint invocation ran the same 57 tests and had one failure: `test_project_context_can_be_recovered_without_chat_history` observed that the current worktree had not yet been captured by the portable Git snapshot. That was a checkpoint-ordering issue: the documentation edits were intentionally present after the baseline checkpoint. The edits were preserved, the repository checkpoint was refreshed, and the timestamped rerun above passed. The first-run log is retained at `logs/PRE-M2-context-export-20261016.log` (SHA-256 `6a62716eeb520b14c21e07b2ac8b2fce1c05ac0c18a02b6fbe26e95483256f54`); it did not contain an exact start timestamp.

The final preflight reported PASS after a refreshed checkpoint. Its expected warnings were pending authorized worktree edits and the ignored `artifacts/` directory's independent-manifest advisory; there were no schema, task, dependency, blocker, or Markdown-link errors. The live checkpoint ID is maintained only in [PROJECT_STATE.yaml](../state/PROJECT_STATE.yaml).

The pre-existing untracked local `main.py` was not modified or staged. The pre-existing local terminal evidence ZIP was not modified or staged; observed SHA-256: `340ba2da7ff6eeea4fc71e8769c3eb5e32b2039997870d61f8a42290c1c8f81a`. The `main.py` SHA-256 remained `c101b2abfee28217d24a7c550eda37cffe548adfc9149244646199108361c0fe`.

No full ALE runtime suite was run because this task prohibits new gameplay experiments and made no M1 code changes. No M2 implementation tests, full test suite, dependency installation, dataset download, or Stockfish operation was run.

## Governance and readiness

- G0, G1, G2 remain approved; M0 and M1 remain complete; BLK-001 remains historically resolved for its recorded scope.
- G3 is upcoming and not approved. M2 remains `pending_user_approval`; M2-001 remains pending and M2-01 through M2-04 remain unverified.
- M3–M7 remain not started. O-01 through O-08 remain unresolved.
- ADR-0002 remains proposed, not accepted. Its action representation, fixed agent perspective, opponent transition boundary, and draw-claim contract should be reviewed before M2 implementation.
- Dataset licensing/provenance for the third-party Lichess archive remains unresolved; no dataset has been downloaded or ingested.

## External technical references

- [python-chess 1.11.2 Core API](https://python-chess.readthedocs.io/en/latest/core.html), including claimable and automatic draw behavior.
- [FIDE Laws of Chess, Articles 9.2–9.5](https://handbook.fide.com/chapter/e012023), including current-position and announced-move draw claims.
- [Third-party Lichess Elite Database listing](https://database.nikonoel.fr/) and [official Lichess database terms](https://database.lichess.org/); terms for the filtered third-party archive are not established by the official database page.
