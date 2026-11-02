# G3 Independent PM Approval and Post-Merge Verification

**Decision authority:** Independent Project Manager decision recorded in [PR #11 comment 6519216543](https://github.com/dodaonam/atari-videochess-rl/pull/11#issuecomment-6519216543).
**Decision timestamp:** 2026-10-30T09:13:07Z.
**Decision:** **G3 APPROVED**, covering the M2–M5 engineering scope defined by ADR-0001.
**Recorded:** 2026-10-30.

## PR #11 integration identity

GitHub records PR #11 merged into `initial-idea` at 2026-10-30T09:11:08Z. The merge commit is `e0b434530df51b08595e3896c175f81b4a8f8c64`; its first parent is base `08f98f9dfc58fbf54e29afabb009020b787f2718` and its second parent is reviewed M5 feature HEAD `c9df9db36c6146a34ef301052a206fe8a3512ffc`. The merge tree and reviewed feature tree are both `793c3e9268d188a7673feb0b680554f94b902fd9`. The remote `initial-idea` ref was independently fetched and resolves to the merge commit.

## G3 prerequisite evidence reviewed by the PM

| Engineering scope | Canonical status | Evidence reviewed |
|---|---|---|
| M2 chess foundation | Complete | `.agents/evidence/M2-acceptance-20261016.md`, `.agents/evidence/M2-github-delivery-20261016.md`, and `.agents/evidence/POST-M2-INTEGRATION-VERIFICATION-20261017.md`. |
| M3 expert dataset | Complete and accepted/integrated | `.agents/evidence/M3-acceptance-20261021.md`, M3 release/teacher manifests and integration evidence. Private data artifacts remain local and are not redistributed. |
| M4 behavior pretraining | Complete and accepted/integrated | `.agents/evidence/M4-final-acceptance-20261027.md` and `.agents/evidence/M4-postmerge-delivery-verification-20261027.md`. The private accepted M3/M4 model artifacts are outside Git. |
| M5 Double DQN simulator experiment | Complete and accepted, with documented M5-03/M5-04 limitations | `.agents/evidence/M5-PM-acceptance-20261030.md`, `.agents/evidence/M5-training-campaign-verification-20261029.json`, `.agents/evidence/M5-evaluation-campaign-verification-20261029.json`, `.agents/evidence/M5-source-semantics-20261030.json`, and `docs/04-research/M5_FINAL_REPORT.md`. |

The PM’s decision accepts the four completed engineering prerequisites and the M5 scientific record. The PM’s review of the campaign relies on recorded local evidence; the PM did not claim to execute Codex’s tests or to rehash the private multi-gigabyte artifact files personally.

## M5 scientific and provenance qualifications retained

M5 is a Double DQN experiment in the M2 chess simulator. Its six runs comprise Warm-start and Scratch for seeds `20261104`, `20261105`, and `20261106`, each with 50,000 valid decisions: 300,000 decisions total, 73,470 optimizer updates, and 144 target synchronizations. The frozen evaluation comprised 1,500 games: 1,494 terminal results and six valid time-limit truncations.

Both trained arms improved from their initialization conditions in the reported benchmark. Warm-start superiority over Scratch was not established conclusively; Frozen M4 and SimpleHeuristic were stronger overall. Only three paired training-seed clusters are available. These are M2 simulator results, not Atari ALE VideoChess performance.

M5-03/M5-04 remain accepted with documented limitations. BLK-003 was resolved by explicit PM risk acceptance. RSK-014 remains accepted residual risk: source aggregate hashes differ between run groups; historical `replay.py` and `checkpoint.py` were recovered byte-for-byte and replay learning operations audited as unchanged; complete historical `cli.py` bytes remain unavailable. Strict source homogeneity and byte-identical full-campaign reproduction are not claimed.

## Codex post-merge verification of the integrated tree

Codex created a network clean clone, detached at merge commit `e0b434530df51b08595e3896c175f81b4a8f8c64`, with tree `793c3e9268d188a7673feb0b680554f94b902fd9` and a clean checkout. The checkout used the repository’s Python 3.12.3 environment and explicitly unavailable private M3/M4 paths.

- `python3 scripts/agent_preflight.py --json`: exit 0, `ok=true`, zero errors; the only warning was `ARTIFACT_MANIFEST_REQUIRED`, expected because private artifact directories are not in Git. JSON SHA-256: `8b30cd68088580cb836f6787e9d371827928dec4557031bd30bf08ef97eddf9e`.
- `python3 scripts/migrate_checkpoint_history.py verify`: exit 0; archive status verified, 246 records, logical SHA-256 `aecc5a44e1ed72f8c161233f4c773d97b14fe39935a8fbd427403eb6fb89b550`.
- `python -m unittest discover -s tests -v`: exit 0; 383 tests passed with one expected skip because the private M4 artifact is unavailable in a clean clone. No other tests failed or skipped. Full log SHA-256: `ab4af149132c9c93982b45e58f2087dbe53ef8e10db74c8d562ee610cf169e67`.

The PM reported no separate GitHub Actions run on the merge commit. The checks above are Codex-run local clean-clone verification and are not represented as a PM-executed suite or merge-commit CI.

In a separate read-only verification against the local private M5 artifact tree (not the clean clone), the artifact manifest verifier passed for seven manifests and 6,544,747,450 inventoried payload bytes; manifest SHA-256 is `a201a254671ad59ae1fecb402abf994d5bf523097f1c3010b5c7fa237ae6dd4c`. The campaign verifier reported six runs, 300,000 decisions, 73,470 updates, 144 synchronizations, and 1,500 evaluation rows; source identity verification returned an exact match. Combined local verifier log SHA-256: `91290e590437bf7d3b47f7be5f8215bbe766b69be20c448578400151694589e0`. These private files are absent from Git and cannot be independently checked from a clean clone. No official training, evaluation, or artifact mutation occurred during this G3 closeout.

## Governance boundary

G3 approval records completion and acceptance of the M2–M5 governance scope only. It **does not authorize M6**. No M6 task was created; M6 is not started and remains pending separate direct owner/PM authorization and its own entry-condition review. G4 remains the next governance gate. No G4 approval is claimed.
