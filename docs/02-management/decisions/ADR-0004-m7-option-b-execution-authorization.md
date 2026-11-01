# ADR-0004: M7 Option B Execution Authorization and Gate Boundary

- **Status:** Accepted by direct project-owner instruction for this M7 scope
- **Date:** 2026-10-31
- **Decision owner:** Project owner
- **Scope:** M7-001 through M7-003 execution and the conditional M7-004/M7-005 boundary
- **Evidence:** `.agents/evidence/M7-001-authorization-20261031.md`

## Context

The merged Pre-M7 plan and `M7_EVALUATION_PROTOCOL.md` described the optional 90-attempt Option B ALE branch as a proposal requiring later owner approval. The plan also stated that M7 work should wait for an applicable G4 PM decision. The independent PM's current G4 disposition is HOLD / NOT APPROVED. The project owner has since issued a direct master execution order selecting Option B and explicitly authorizing M7-001–003 immediately, while conditioning M7-004–005 on independent G4 approval.

This is a subsequent owner decision. It does not retroactively change the proposal's earlier status or imply that G4 was approved.

## Decision

1. Execute Phase I now: M7-001, M7-002, and M7-003, subject to their acceptance criteria and the fixed Option B scope in the separately versioned execution configuration.
2. Use the six accepted M5 post-RL checkpoints, accepted M4 r4 policy, RandomLegal, and SimpleHeuristic; evaluate each on the same ten newly frozen ALE seeds for exactly 90 scheduled cells.
3. Use local CPU, one ALE process, the exact accepted VideoChess ROM, and the M6 v2 extended-horizon profile. Do not exceed 1,800 seconds per attempt, 8 GiB of campaign artifacts, or use the campaign unless at least 12 GiB remains free before execution.
4. Preserve all M4/M5/M6 inputs and results. Do not train, fine-tune, replace checkpoints, add simulator games, use Stockfish as an opponent/evaluator, or transfer private artifacts.
5. Keep G4 unapproved until an independent PM decision is received and recorded. Do not begin M7-004 or M7-005 before that decision is verified in canonical state.
6. Record Elo as not reported absent an approved calibrated pool and design. Do not publish or release artifacts; M7-005's current disposition is no release.
7. Submit Phase I as an open, non-draft feature-branch PR to `initial-idea`; the executor does not self-approve or merge it.

## Resolution of the prior proposal

The prior proposal remains a historical record of what was not authorized at PR #16. This later direct owner instruction supersedes its authorization condition for M7-001–003 only. The earlier proposal's scientific cautions and acceptance rules remain in force. Its G4/G5 ownership split is unchanged. The M6 v2 configuration remains an immutable 20-attempt historical configuration; M7 uses its runtime profile only through a distinct M7 configuration and run identity.

## Consequences

Canonical state records M7 as authorized and M7-001 active. G3 remains approved; G4 and G5 remain unapproved. The six accepted checkpoint identities and all historical M4/M5/M6 evidence remain immutable. Any inability to verify an input or execute within the stated resource envelope is reported as a blocker or partial schedule, not bypassed.


## Current-scope supplement — 2026-11-01

The Project Owner has since recorded the accepted research results as final and authorized no further research campaign or new milestone. This closes research execution; it does not authorize publication. The earlier M7-005 blanket no-release attribution referred to by this ADR was later identified as unverified under [G5-F02](../../../.agents/evidence/G5-F02-provenance-erratum-20261101.md); it is not treated as a current owner prohibition. No affirmative authorization to distribute restricted artifacts is established. G5's M7-05 premise requires fresh Independent PM review. The M7-001–003 Option B authorization above remains historical and unchanged.
