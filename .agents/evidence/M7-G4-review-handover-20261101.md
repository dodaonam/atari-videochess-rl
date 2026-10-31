# M7 Phase I — G4 Independent PM Review Handover

## A. Executive verdict

**Ready for independent PM review with documented scientific limitations.** M7-001, M7-002, and M7-003 are complete with raw-derived evidence, verified hashes, reproducible analysis, and passing tests. The campaign's scientific result is negative/inconclusive: it produced 60 terminal losses and 30 incomplete attempts, with no wins or draws. G4 remains **HOLD / NOT APPROVED** until the independent PM decides it. No M7-004/005 work has started.

## B. Repository identity

- Repository: [`dodaonam/atari-videochess-rl`](https://github.com/dodaonam/atari-videochess-rl).
- Feature branch: `feature/m7-option-b`.
- PR base: `initial-idea`, established from the verified PR #16 merge `257fff94c64bc584797e0d191920a57befcae62c`.
- Final full-suite and preflight source revision: `cbf4b27d4c9eb65108ee17c3138cf020c8c8ade9`.
- M7 run source revision/tree: `58a604f2bd4bcd9113a047ee709a80ee97bd02a6` / `18d4d93270665a1c2e90eb459381958e407c441f`.
- Authoritative analysis source revision/tree: `fe2cc4cc5e477841ffbc9368235eb9c5675f2f74` / `94f37d775b5a62f09c2502fcfd8caf58622397bf`.
- The open PR's exact HEAD, PR URL, base SHA, and CI status are recorded in GitHub review metadata and the executor's final report. The PR is to remain open, non-draft, and unmerged for the PM decision.

## C. Engineering completion

| Task | Status | Acceptance | Evidence and limitation |
|---|---|---|---|
| M7-001 | Done | `M7-01` | [Population/campaign acceptance](M7-001-acceptance-20261101.md); exact 90-cell raw ledger, manifests, resource accounting, and sanitized run log. |
| M7-002 | Done | `M7-02` | [Analysis acceptance](M7-002-acceptance-20261101.md); [authoritative report](M7-analysis-final-r2-20261101/M7_ANALYSIS.md), machine-readable output, plots, manifests, and uncertainty limitations. |
| M7-003 | Done | `M7-03` | [Elo disposition](M7-003-acceptance-20261101.md): Elo not reported because a calibrated pool/design is not approved or available. |
| M7-004 | Pending G4 | `M7-04` | Not started. Begin only after the independent PM approves G4 and canonical state records that decision. |
| M7-005 | Pending G4/G5 | `M7-05` | Not started. Current release/publication status is no authorization; do not publish or upload restricted artifacts. |

The package contains the versioned M7 config and implementation, governance and backlog updates, verified input/preflight/smoke records, analysis code and tests, three explicitly ordered analysis reconstructions, acceptance evidence, and a preserved failure/remediation history.

## D. Experimental evidence

- Protocol: `M7-Option-B/1.0.0`; scientific basis `M7-EVAL/1.0.0`.
- Run: `m7-option-b-20261031-v1-8387b289432f`; config SHA-256 `8ec8a42a808f4ffc410c938b4400d02461f96823eb5ac1b16cbd6e0d5e35f255`; schedule SHA-256 `c479e65f944224ffbc584e15f43086e881e9df1a10c009c478be8ce5119e67d9`.
- Policy population: six accepted M5 post-RL checkpoints (Warm/Scratch × seeds `20261104`–`20261106`), accepted M4 r4 behavior-only, RandomLegal, and SimpleHeuristic. No pre-RL checkpoints were included.
- ALE seeds: `20261201`–`20261210`, shared across all nine groups; exactly 90 unique scheduled cells.
- Environment: White, `ALE/VideoChess-v5`, mode 4, difficulty 0, RGB, frameskip 4, repeat-action probability 0.25, effective horizon 500,000 frames / runner limit 432,000 post-reset frames. ROM SHA-256 `d44f2a115393b0a6cbcd5398d62369e652f3670a9ee585883d183e740edad0f7`.
- Schedule accounting: 90 scheduled, 90 started, 90 reset-observed, zero not started; outcomes 60 terminal losses and 30 incomplete. No attempt was replaced. Incomplete attempts are not draws.
- Raw files are owner-local and excluded from Git at `artifacts/m7-option-b/m7-option-b-20261031-v1-8387b289432f`. Artifact manifest SHA-256 `25a8b6bcfbf1d948bed886a0a4964cf48210fb1be12809c72bf122157b8d05e4`; run manifest `93d941f5b1c4f876ea66c62d30f66b873b61e59acbacd25534d66920bbbb3431`; event ledger `3b0ee6a76031abead00aa474ab782503eee661ad6d560728a5d0a2120251e948`; summary `81d605372a4eca2dcf10d701374cd41bb90015d6b30ef6ee8625eaa7ba6e0f57`.
- Finalized artifact-parent size 2,463,748,628 bytes, below the 8 GiB cap. Free disk was 50,056,785,920 bytes at first attempt and 47,532,662,784 bytes afterward. Peak RSS 368,812,032 bytes; aggregate attempt wall 10,393.16 seconds; CPU 6,519.45 seconds; no resource stop.
- Private checkpoints, ROM, raw RGB traces, and source datasets were not included in the PR or uploaded.

## E. Verification

- Focused M7 suite: 29 tests passed; see the source-identified [focused test record](M7-focused-final-clean-20261101.json) and log.
- Relevant M1/M4/M5/M6 regressions: discovery run passed 230 tests with one opt-in private-roster test skipped; that test passed separately. The final full suite below then enabled all private artifact tests.
- Full local repository suite on `cbf4b27d4c9eb65108ee17c3138cf020c8c8ade9`: **492 passed, zero skipped, zero failed**, including bounded real-ALE regressions, M4/M5/M6 compatibility, all six accepted private M5 snapshots, clean-clone recovery, context/preflight contracts, and M7 tests. The Stockfish test performed UCI startup/ping only; no search was requested.
- Final canonical preflight on the same source revision: PASS; only `ARTIFACT_MANIFEST_REQUIRED` remains because raw artifacts are intentionally local. The portable Git manifest matches the expected commit transition.
- The eight Pre-M7/M7 governance-contract tests passed after the G4 handover was written, including all new local Markdown links, canonical gate mapping, privacy, and Phase I/Phase II boundary; see [the test record](M7-G4-contract-tests-final-20261101.json).
- The full suite includes the test that reconstructs the current committed state in a clean clone without local artifacts. All M7 raw-to-report and manifest checks passed in the independent analysis run.
- Exact sanitized logs and command metadata are under `.agents/evidence/logs/` and linked from task evidence. Earlier failed invocations and their fixes remain in [the failure history](M7-engineering-failure-history-20261031.md).
- GitHub CI is checked against the exact PR HEAD after the PR is opened; it does not replace the local suite or local raw-artifact checks.

## F. Scientific conclusions and limitations

- All 60 known terminal M7 games were White losses; 30 cells remain incomplete. The Warm 20261105 post-RL group has no terminal games, so its terminal-only score is undefined.
- Warm/Scratch post-RL has 9/30 terminal paired training-seed × ALE-seed cells and 21 censored/unknown cells. Its complete-pair point difference is 0.000; a valid 95% interval is unavailable. All 18 RL-versus-baseline comparisons contain censored blocks; superiority or equivalence is unsupported.
- The run demonstrates bounded closed-loop operation of the frozen policy/controller integration without recorded board desynchronization, not stronger chess play or RL improvement. The M4 fivefold shadow-history stop is retained as incomplete because ALE did not terminate.
- M7 is White-only against one built-in Atari opponent, with three training-seed pairs and ten shared evaluation seeds. M4 imitation, M5 simulator results, M6 v1/v2, and M7 remain separate. RSK-014 and PM6-F06 remain disclosed historical limitations.
- Elo is not reported: the calibrated pool, anchor, diversity, terminal match schedule, color balance, and Elo-specific uncertainty design are absent or unapproved.

## G. Governance and next action

- Governance state: G3 approved; next gate G4; G4 and G5 remain unapproved. G4's prior PM disposition was HOLD / NOT APPROVED.
- Direct owner authorization `M7-AUTH-20261031-OPTION-B` is recorded in [the authorization evidence](M7-001-authorization-20261031.md) and ADR-0004. It authorized Phase I and made Phase II conditional on independent G4 approval.
- M7-001, M7-002, M7-003 are done. M7-004 and M7-005 remain pending; M7-004 is the canonical next task, not started.
- Release/publication authorization: **none**. Do not publish a release, distribute the ROM/checkpoints/data, or upload raw artifacts.
- **Required external action:** independent PM reviews the G4 evaluation package, resolves/records findings, and enters an actual G4 decision in canonical state. Do not begin M7-004/005 until approval is verified. The executor does not self-approve or merge.
