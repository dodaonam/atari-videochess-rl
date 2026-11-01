> **Provenance notice added 2026-11-01:** This historical executor-authored record attributes a blanket no-release decision to the Project Owner. The latest Independent PM finding says that attribution is disputed and unsupported by an independently verifiable primary source. It is therefore **unverified**, not an established owner prohibition or authorization. The original body remains below for audit history; current status is in the [G5-F02 provenance erratum](G5-F02-provenance-erratum-20261101.md) and [corrected M7-005 assessment](M7-005-corrected-disposition-assessment-20261101.md).

# Historical Project Owner No-Release Attribution — Superseded

**Decision ID:** `M7-REL-DISP-20261101-NO-RELEASE`
**Authorization ID:** `M7-AUTH-20261101-M7-005-NO-RELEASE`
**Project:** `atari-videochess-rl`
**Project Owner:** Nam (as identified in the direct current-session instruction)
**Engineering task / acceptance criterion:** M7-005 / M7-05
**Decision date:** 2026-11-01 (session date)
**Authorization source:** Direct Project Owner instruction in the current Codex session, “M7-005: Final Release Disposition, Engineering Closeout, and G5 Review Readiness”
**Repository:** `https://github.com/dodaonam/atari-videochess-rl`
**Integration baseline:** `initial-idea` at merge commit `0f45fa06c235658da48d3d41a9091c06580bfe27`
**Related accepted delivery:** PR #19 reviewed source `05a94ef096da9bc0467970e0ea8ec1dc88d953e3`, merged at the baseline above

## Owner decision

> **NO RELEASE / NO PUBLICATION AUTHORIZED.**

This is the Project Owner's explicit decision for the current M7 closeout. It authorizes engineering work to record and verify this disposition and prepare the G5 review package. It does not authorize publication or redistribution.

The following must not be publicly released, distributed, uploaded, hosted, or shared with third parties under this decision:

- Atari VideoChess ROM binaries.
- M3 source datasets and bulk game records.
- M3 teacher-label datasets, scores, sidecars, and derived private position data.
- M4 supervised checkpoints and sidecars.
- M5 Warm/Scratch checkpoints, raw training records, replay journals, and raw simulator evaluations.
- M6 Stage 3 v1 and v2 raw ALE records, controller traces, and associated artifacts.
- M7 raw ALE attempt records, ledgers, RGB frames, traces, and private campaign artifacts.
- Private manifests and any manifest-listed payload not separately approved for distribution.
- Private benchmark artifacts, credentials, machine-specific environment files, and owner-local storage information.
- Any model package or public deployment built from those restricted artifacts.

No GitHub Release, public model package, public deployment/inference service, external artifact upload, or third-party access grant is authorized. No license or redistribution right is assigned or inferred. A hash or local copy does not create such a right.

## Existing repository content

This decision does not delete, revoke, or retroactively unpublish source code, sanitized documentation, approved summaries, configurations, hashes, or evidence previously committed through the authorized repository workflow. It does not change repository visibility or imply that every committed item has independent redistribution rights. This M7-005 PR is the authorized governance review workflow; it is not an artifact release.

The decision does not prevent authorized private academic use of artifacts by the Project Owner. It does not grant any third party access, resolve O-06, or establish the license of the M3 Lichess source package or any third-party ROM.

## Future reconsideration

Any future release requires a separate, explicit direct Project Owner decision. Before acting on such a decision, the proposed payloads must receive artifact-specific rights, privacy, integrity, and scientific-claims review. This record does not pre-authorize a release or guarantee that a future proposal will be approved.

## Provenance and governance separation

The authorization was received as the current user instruction in this session. It supplied no external approval URL/comment ID, signature, or separate issuance timestamp; none is fabricated. The recorded date is the session date, not a claimed exact issuance timestamp.

G4 remains **APPROVED WITH SCIENTIFIC LIMITATIONS** for M7-01 through M7-03. PR #19's Independent PM decision accepted M7-04 engineering evidence but explicitly stated it was **not G5 approval**. G5 remains **NOT APPROVED** pending a separate Independent PM decision. Engineering completion of M7-005 does not approve G5.

## Subsequent governance status supplement — 2026-11-01

The preceding paragraph records the status when this owner no-release decision was issued. The Independent PM subsequently approved G5 for M7-04/M7-05 with scientific, environment-verification, and no-release limitations in [the official PR #20 decision](https://github.com/dodaonam/atari-videochess-rl/pull/20#issuecomment-6556836388), and PR #20 was integrated at `0b9c4c26ee1d0952a5f9e3b7cd405f5bf4e3008b`. The PM approval does not change this Project Owner decision: **NO RELEASE / NO PUBLICATION AUTHORIZED.** See [G5 PM acceptance](G5-PM-acceptance-20261101.md) for the decision record and remaining limitations.

## G5-F02 correction to the historical supplement — 2026-11-01

The preceding paragraph is retained to preserve the original chronology, but its attribution of a binding owner decision is **unverified and superseded**. The latest Independent PM finding [G5-F02](https://github.com/dodaonam/atari-videochess-rl/pull/21#issuecomment-6557663143) states that no authenticated primary source supports the asserted owner prohibition. The earlier PR #20 PM decision is an authentic historical PM record, but it is not independent proof of the Project Owner's original release wording; its M7-05 premise is suspended pending fresh PM review. The current evidence establishes no affirmative permission to distribute restricted artifacts and no verified blanket owner prohibition. The dated [provenance erratum](G5-F02-provenance-erratum-20261101.md) is the current source for this distinction. No release operation is part of the current closeout.
