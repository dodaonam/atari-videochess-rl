# Pre-M2 architecture refinement verification

- **Scope:** Documentation-only simplification of the proposed M2 simulator contract. No M2 implementation, gameplay, dataset work, model work, or training was started.
- **Base revision:** `6457955db8d75c45a503d1f534c1367dbd17481d` on `initial-idea`.
- **Governance:** G2/M1 remain approved/complete; G3 remains unapproved; M2-001 remains pending explicit authorization; M2-01 through M2-04 remain unverified; O-01 through O-08 remain open.

## Recorded scope decision

The active M2 action contract is legal `python-chess.Move` values only, recorded by stable UCI identity. Voluntary draw-claim actions and their interfaces, encodings, policy outputs, supervision and tests are excluded from active scope and are not planned as an extension. Automatic outcomes remain delegated to the locked rules library through `Board.outcome(claim_draw=False)`; simulator limits remain truncation.

## Source inspection

The existing project environment reports `chess` package version 1.11.2. Inspection of its `Board.outcome` signature and implementation confirms `claim_draw=False` as the default and automatic handling for checkmate, stalemate, insufficient material, the seventy-five-move rule and fivefold repetition. This was source inspection only, not an M2 runtime or acceptance test. M2 must still verify the locked API through implementation tests.

## Validation

| Check | Started (UTC) | Revision | Result |
|---|---|---|---|
| `python3 scripts/agent_preflight.py` | 2026-10-16 05:40:26 | `6457955db8d75c45a503d1f534c1367dbd17481d` plus staged documentation | Exit 0; context/governance and links pass. Advisory `ARTIFACT_MANIFEST_REQUIRED` remains for ignored raw `artifacts/`. |
| `python3 -m unittest tests.test_agent_context tests.test_export_review_bundle -v` | 2026-10-16 05:40:26 | `6457955db8d75c45a503d1f534c1367dbd17481d` plus staged documentation | Exit 0; 57 tests passed in 66.139 seconds. |
| `git diff --cached --check` | During final staged review | `6457955db8d75c45a503d1f534c1367dbd17481d` | Exit 0. |
| Configured credential-pattern scan over seven changed design files | During final staged review | `6457955db8d75c45a503d1f534c1367dbd17481d` | No configured token/private-key patterns found. |
| Active action-ID scan (`CLAIM_DRAW_NOW`, `CLAIM_DRAW_AFTER`, `claim-after`, `claim-now`) | During final staged review | `6457955db8d75c45a503d1f534c1367dbd17481d` | No active action IDs or interfaces found. The specifications contain only a short explanatory scope exclusion and the required library API parameter. |

Sanitized retained logs:

- [Preflight log](logs/PRE-M2-refinement-preflight-20261016.log) — SHA-256 `5ea3e5ffeae0c6f8e177dc2ca31af976a136e2f7e2db77d6f392892e810c68c1`.
- [Context/export test log](logs/PRE-M2-refinement-tests-20261016.log) — SHA-256 `6d75fb862e012a0c0fdcdba7e94bc5cb2795611b12c2236e1ffde0dfa262b90d`.

An earlier pre-checkpoint run of the same 57-test command had one failure in `test_project_context_can_be_recovered_without_chat_history`: it observed the expected mismatch between the old portable snapshot and uncheckpointed document edits. After refreshing the checkpoint for the staged documentation, the full command passed. The initial run was a transient recovery diagnostic, not acceptance evidence; its console output was not retained.

No M1/G2 evidence or acceptance decision was changed. The earlier Pre-M2 readiness record remains historical evidence of the prior proposal; this refinement and the updated [ADR-0002](../../docs/02-management/decisions/ADR-0002-chess-mdp-action-and-perspective.md) supersede its MDP recommendation for active planning.
