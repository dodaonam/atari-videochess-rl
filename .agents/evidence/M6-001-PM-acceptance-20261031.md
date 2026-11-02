# M6-001 — Independent PM acceptance and merge record

**Decision date:** 2026-10-31
**Decision authority:** Independent Project Manager, recorded on GitHub PR #14
**Decision comment:** [PR #14 comment 6539798992](https://github.com/dodaonam/atari-videochess-rl/pull/14#issuecomment-6539798992)
**Decision:** M6-01 through M6-05 accepted for the M6 engineering acceptance scope, with the qualifications below.
**Repository integration:** PR #14 merged by the project owner into `initial-idea`.

## Accepted identities

| Identity | Value |
|---|---|
| Accepted feature HEAD | `e919ee3ad039c9d2de3ebdf6b82704ecd61c0a6f` |
| Accepted feature tree | `7eb06fd9c0e0b363ca324d203e1debf26f233c08` |
| Merge commit | `509f9f83f9249208fd5adba572efed2d2f0f82ff` |
| Merge parent 1 (`initial-idea` before PR) | `e6d444e475e447e9f37951f16585bf496f804c9d` |
| Merge parent 2 (accepted feature HEAD) | `e919ee3ad039c9d2de3ebdf6b82704ecd61c0a6f` |
| Integrated tree | `7eb06fd9c0e0b363ca324d203e1debf26f233c08` |
| PR state | #14 merged into `initial-idea` at 2026-10-31T05:55:49Z |
| M6 v2 execution source | `91f51b14690eba12e9e4fd25a4fc1671801fac0d`, tree `4d6ed616971c8f5606a0a7250fe68fa2eea40949` |

The PM decision was verified from the live PR and the original GitHub comment. A separate [post-merge identity verification log](logs/M6-postmerge-identity-verification-20261031.log) records the PR state, remote branch, both merge parents, tree equality, comment URL, timestamp, and comment-body SHA-256.

## PM decision and review scope

The PM stated: “M6 ACCEPTED for the M6-01–M6-05 engineering acceptance scope.” The PM approved merge at the exact accepted feature HEAD above. This record captures that existing decision; it is not a new approval issued by the engineering executor.

The PM reviewed the source, tests, configuration/policy identities, independent audit implementation and reports, and recorded verification logs. The PM explicitly stated that they **did not personally access, rehash, or rerun the private original raw ALE artifacts or the 452 Python tests on the owner's host**. The local audit and test runs remain engineering-executor evidence; they are not represented as PM-executed checks.

## Accepted evidence and preserved limitations

- **M6-01–M6-03:** The frozen M5 policies used ALE RGB-derived observations through the validated adapter and controller loop. Inference remained frozen and engine-free; recorded evidence reports zero board desynchronizations.
- **M6-04:** The separately authorized 20-attempt v2 campaign produced 11 ALE-terminated games, all losses, and 9 incomplete attempts. Warm: 4 losses / 6 incomplete from 10; Scratch: 7 losses / 3 incomplete from 10. Incomplete categories were five reply timeouts, two source-selection uncertainty stops, and two target-navigation uncertainty stops. Incomplete attempts were not counted as draws.
- **M6-05:** Stage 3 v2 is an explicitly identified extended-horizon v5 profile: 500,000 ALE episode-frame horizon and 432,000 post-reset runner limit, distinct from the 108,000 registered default and from debug runs.
- **Operational counts:** 385/405 RGB-verified initiated player moves, 385 verified Atari replies, and zero recorded board desynchronizations. Cursor corrections and censor categories remain separate.
- **Scientific interpretation:** V1 and v2 remain separate protocols. V2 reuses v1 seeds under an extended horizon, so it is not an independent held-out replication. The observed losses do not support Warm/Scratch superiority, Elo, strong-playing-performance, or generalization claims.
- **PM6-F06:** The original v2 run manifest remains immutable; the corrected future metadata behavior and historical discrepancy are documented in the [separate erratum](M6-PM6-F06-erratum-20261031.md).
- **Artifacts:** Raw ALE evidence and private M4/M5 checkpoints remain local-only and unpublished. The PM reviewed tracked audit reports and logs, but did not personally re-run the raw audit.

The detailed pre-acceptance engineering and experiment record is in the [M6 corrective closeout report](M6-final-corrective-closeout-20261031.md), the [human-readable r3 raw audit](M6-stage3-v2-independent-raw-audit-20261031-r3.md), and its linked machine reports. This acceptance record does not change those reports or any experiment bytes.

## Governance after acceptance

- **G3:** approved.
- **M6 / M6-001:** accepted and complete; PR #14 integrated at `509f9f83f9249208fd5adba572efed2d2f0f82ff`.
- **G4:** not approved; its separate PM decision remains pending.
- **M7:** not started and not authorized. It requires a separate direct owner authorization and applicable G4 decision.
