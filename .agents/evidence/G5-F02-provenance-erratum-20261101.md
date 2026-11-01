# G5-F02 — Owner Release-Disposition Provenance Erratum

**Recorded:** 2026-11-01. No separate issue timestamp or signed owner record is asserted.
**Finding:** G5-F02 — unsupported attribution of an explicit owner no-release decision
**Independent PM source:** [PR #21 review comment 6557663143](https://github.com/dodaonam/atari-videochess-rl/pull/21#issuecomment-6557663143)
**Reviewed PR #21 HEAD:** `fc51b724d6a812ec648aaeb3ba26b8371b8d1989`
**Current purpose:** Correct the provenance record and request fresh Independent PM review. This is not a PM finding disposition or G5 approval.

## What was claimed

Earlier executor-authored M7-005 records represented **“NO RELEASE / NO PUBLICATION AUTHORIZED”** as an explicit Project Owner decision. The claim appears in the initial sections of [the M7-005 authorization record](M7-005-authorization-20261101.md), [the owner no-release decision record](M7-005-owner-no-release-decision-20261101.md), [the M7-005 acceptance record](M7-005-acceptance-20261101.md), the initial [release disposition](../../docs/07-delivery/RELEASE_DISPOSITION.md), and later G5/delivery summaries. Those records cite a direct instruction in a Codex session, but they do not contain a primary-source permalink, signed record, or other independently verifiable locator for that alleged release choice.

The latest Independent PM review states that the Project Owner disputed having made the alleged prohibition and that the executor-authored summaries are insufficient primary evidence. The original wording is retained in its dated records for auditability; the notices added to those records and this erratum supersede the attribution. The old wording must not be treated as proof of an owner prohibition.

| Record | Earlier attribution | Source now established | Current evidentiary status |
|---|---|---|---|
| `M7-005-authorization-20261101.md` | The owner selected a binding no-release option as part of M7-005 authorization. | The file itself is executor-authored; it has no external source locator. The latest PM finding disputes the attribution. | Historical claim retained; explicit owner prohibition is **unverified**. The M7-005 engineering authorization remains evidence of the bounded engineering work only, subject to this provenance caveat. |
| `M7-001-authorization-20261031.md` | The owner had not authorized release and M7-005's required disposition was no release unless later changed. | The repository record cites a direct instruction but has no externally verifiable primary-source locator for this release boundary; the later owner/PM correction requires the assertion to be treated as unverified. | Historical M7-001–003 experimental authorization remains unchanged; this sentence is not current blanket release authorization or prohibition evidence. |
| `G4-PM-acceptance-20261101.md` | The owner had not authorized public model/data/ROM publication as of G4 review. | Historical PM status assessment, not a primary owner authorization; no separate owner decision is linked there. | G4 acceptance remains valid; its historical distribution statement does not establish a current blanket owner prohibition. |
| `M7-005-failure-history-20261101.md` | Earlier remediation wrote that a direct owner no-release decision was recorded. | Executor-authored retrospective pointing to the now-disputed records. | Retained as failure/remediation chronology only; not primary authorization evidence. |
| `M7-005-owner-no-release-decision-20261101.md` | The owner explicitly prohibited public release and publication. | The file itself is executor-authored; no independently verifiable primary source was supplied with it. | Historical claim retained; do not treat as an authenticated release decision. |
| `M7-005-acceptance-20261101.md` | M7-05 was satisfied by an explicit owner no-release decision. | The acceptance table points back to the same executor-authored records. | Historical engineering assessment; the owner-decision premise is superseded. Fresh PM consideration of M7-05 is required. |
| `G5-PM-acceptance-20261101.md` and `.json` | The earlier PM G5 approval accepted M7-05 on the no-release premise. | The original PM decision is authentic at [PR #20 comment 6556836388](https://github.com/dodaonam/atari-videochess-rl/pull/20#issuecomment-6556836388). The later PM finding is authentic at the PR #21 link above. | Preserve the historical decision. Per the later PM finding, its M7-05 release-disposition premise is suspended pending correction and fresh review; M7-04 acceptance and G5-F01 resolution remain intact. |
| `RELEASE_DISPOSITION.md`, delivery documents, and G5 handovers | Repeated the owner prohibition as current fact. | These are derivative summaries, not independent authorization sources. | Updated to distinguish no affirmative permission established from an explicit prohibition. |

## Verified facts and corrected interpretation

1. The current Project Owner instruction says that the accepted research results are final, prohibits additional research campaigns, and states that this decision does not authorize publication. It does **not** supply an artifact-release authorization or a blanket owner-issued release prohibition. Its provenance is the direct user instruction in this execution context; no separate issue, signature, or exact issuance timestamp is asserted. See [Project Owner final research-scope decision](PROJECT-OWNER-final-research-scope-decision-20261101.md).
2. No affirmative Project Owner authorization to release restricted model, dataset, ROM, checkpoint, raw-record, or private artifacts has been established in the evidence reviewed for this closeout.
3. No independently verifiable Project Owner blanket prohibition on all release/publication has been established. The earlier executor attribution is unverified and is not relied upon.
4. No release or publication operation is part of this remediation. The repository's current release/tag/deployment state is checked separately in the retained verification evidence. This statement does not make a claim about every external service or every previously visible repository commit.
5. A lack of affirmative authorization is not permission. Any future distribution remains a separate owner-controlled decision and must also satisfy applicable third-party rights, privacy, artifact-integrity, and scientific-claims requirements.
6. The newly recorded final research-scope decision closes further research execution; it does not authorize or prohibit artifact publication.

## Acceptance and governance implications

- M7-04 delivery acceptance remains independently accepted and is not reopened by G5-F02.
- G5-F01 remains resolved; its M3 final-versus-historical identity mapping and regression tests are preserved.
- The accepted M3–M7 scientific evidence and conclusions remain unchanged.
- M7-005 engineering work remains complete as an engineering task. The corrected evidence describes the observable disposition without attributing an unverified owner prohibition.
- G5 is **NOT APPROVED in current canonical state pending fresh Independent PM review**. The prior PR #20 G5 decision is retained as historical, but its M7-05 premise is suspended as directed by the later PM review.
- This erratum does not close G5-F02 on behalf of the Independent PM, authorize merge, or authorize release.

## Superseding current records

Use the following records for current status:

- [Machine-readable G5-F02 status](G5-F02-provenance-status-20261101.json)
- [Corrected M7-005 engineering assessment](M7-005-corrected-disposition-assessment-20261101.md)
- [Project Owner final research-scope decision](PROJECT-OWNER-final-research-scope-decision-20261101.md)
- [M0–M7 project closure and PM handover](M0-M7-final-project-closure-20261101.md)
- Canonical state and backlog on the amended PR #21 branch

**Current release status:** No affirmative authorization for restricted artifact publication is established; no release is performed by this task. This is not an authenticated owner prohibition.

**Current governance status:** G5-F02 remediation is submitted for fresh Independent PM review; G5 remains unapproved pending that decision.
