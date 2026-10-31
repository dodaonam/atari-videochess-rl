# PM6C-F01 — M6 closeout evidence provenance correction

**Review finding:** [Independent PM comment 6541119468 on PR #15](https://github.com/dodaonam/atari-videochess-rl/pull/15#issuecomment-6541119468)
**Finding:** PM6C-F01 — unresolved false verification provenance in M6-001 backlog
**Scope:** Correct evidence identity records and add a regression audit. No accepted M6 gameplay, results, checkpoints, manifests, raw artifacts, or PM decision are changed.

## Finding and cause

The PM found that the M6-001 backlog entry for `.agents/evidence/M6-post-merge-verification-20261031.json` was still `status=verified` with Git revision `5d4cfd93a3895e5a4c2d68eb485379c25639f403`. GitHub returned HTTP 422 for that SHA; it does not resolve in this repository. That revision also cannot contain the JSON report because the report was added later.

A read-only audit of the PR #15 additions and modifications found three related file-record errors that the earlier review had not listed:

| Evidence path | Previous recorded revision | Finding |
|---|---|---|
| `.agents/evidence/M6-PR-handover-20261031.md` | `0eddd06932de06d4651f7e6dc4c99e54db719ddd` | Commit resolves, but does not contain this report file. |
| `.agents/evidence/M6-001-PM-acceptance-20261031.md` | `509f9f83f9249208fd5adba572efed2d2f0f82ff` | Merge commit resolves, but predates and does not contain the acceptance record. |
| `.agents/evidence/M6-post-merge-verification-20261031.md` | `509f9f83f9249208fd5adba572efed2d2f0f82ff` | Merge commit resolves, but predates and does not contain this report. |
| `.agents/evidence/M6-post-merge-verification-20261031.json` | `5d4cfd93a3895e5a4c2d68eb485379c25639f403` | SHA is non-resolving and does not identify a commit containing the report. |

The cause was a provenance convention error: several `kind=file` records used an experiment/integration or earlier verification revision rather than a commit that actually contains the evidence file. The backlog schema checked that the SHA looked syntactically valid but did not check object resolution or file membership. The earlier report had already identified the invalid `5d4cfd93…` log header, but the backlog's `verified` file record was not corrected.

## Correction

All four file records now point to existing commit `94635ad871fd0853fc0c5b1024d8963ced864300`, which contains the exact files. A timestamped, read-only `git show <commit>:<path>` comparison verified each committed blob against the working bytes at `2026-10-31T08:30:39Z`. The backlog stores each verified file SHA-256, the prior revision, and a note that the prior reference was unsupported. No file bytes were edited to make the new hashes pass.

For these four paths, the verified SHA-256 values are:

- M6 PR handover: `f9dfe3aeb3e4658eaf9896d077c93b68c5412db0e97cb10cfde2115543f80670`
- PM acceptance record: `f890126a6259e5c19e5314ca2376cf310afc52e4d256e8597c98df762bf38f6d`
- Human post-merge report: `e7b5b9c0238802879e23728753c556f011508ba621fb5b5324d4a93d90be5d6f`
- Machine post-merge report: `46c2c41a14b6f33c3c55c7bddac6dea32bdd1b45887b1498e9f6857ed61d2ea4`

The old focused/full-suite diagnostic records remain explicitly `historical_unverified`, with their unavailable execution metadata null and their original logs preserved. They are not relabeled as passes. The new `scripts/audit_m6_closeout_provenance.py` audits the scoped file identities, command/test logs, timestamps, log hashes, result text, source revisions, machine-report references, and historical diagnostic classification. `tests/test_agent_context.py` now exercises that audit. The synthetic one-commit portability fixture skips only this history-dependent audit; normal full-history checkouts and CI execute it.

## Scope of the audit

The consolidated audit covered 20 M6-001 evidence entries introduced or modified by PR #15: four file identities, fourteen verified command/test records, and two prior diagnostic records explicitly classified historical/unverified. It additionally checked the eight command logs referenced by the machine-readable post-merge report. Two of the fourteen verified execution records are failed diagnostics (the earlier system-Python/setup attempt and the synthetic one-commit clone fixture); both are explicitly distinguished from passing checks. The audit found no further errors in this bounded scope. Existing M6 experiment and training evidence outside those closeout entries was not rewritten or reclassified.

## Verification

All checks below ran in a clean detached worktree at source revision `fc34f34d850e2830cbc0d9a14d331a197d6ae062`, tree `c933d33a0da149f81b1557a677411a601990e1d3`:

| Check | Result | UTC execution window | Log SHA-256 |
|---|---|---|---|
| Synthetic-clone focused diagnostic | FAIL diagnostic; nested one-commit fixture did not contain historical M6 commit objects | 08:35:51.806–08:36:47.269 | `3c230c633f36583893e1afda8ed4ce275789b860749c8ff4f7faa97f8d5c6a2c` |
| Canonical preflight | PASS; zero validation errors; expected local artifact-manifest warning | 08:37:25.002–08:37:26.779 | `ec0fc87560b72873f3dd85a1ed93ff739b240122c1a6bf842c50126553d1aa23` |
| Initial read-only provenance audit | PASS; four file identities, eight command/test logs, eight machine-report log references; zero errors | 08:37:31.405–08:37:31.532 | `dbf16a6e1f244daba57d80b01c60de40bf5e8db2268c74549939c7a866874d76` |
| Focused context/checkpoint/M6 regression suite | PASS; 109 passed, zero failures/errors/skips | 08:37:38.415–08:38:49.730 | `c4ecd6ee2bb55d8f1b689b20a40f3fe0bdfc9fa700296e6d08d696297aac8528` |
| Full repository suite | PASS; 453 passed, zero failures/errors/skips; 187.326 seconds unittest time | 08:38:56.914–08:42:06.729 | `7a7e0b86630fece97a7c913ec1c298b84448ca85a6706546743319a7ce28f629` |
| Consolidated provenance audit after recording corrective-run logs | PASS; four file identities, fourteen execution logs, eight machine-report logs, two historical diagnostics; zero errors | 08:48:13.005–08:48:13.165 | `381a2f90051c9640612c9a2959e7e23d33d0130e7b98e633125e922488d1148f` |

The first focused attempt at `29b3dcdfcdd21a454e4faa3778336249e76b92e6` failed because the new provenance audit ran inside the test suite's synthetic one-commit portability clone, which intentionally omits earlier M6 commits. The test was corrected to skip only this history-dependent audit when `ATARI_VIDEOCHESS_SKIP_CLONE_RECOVERY_TEST=1` is set by that fixture. The normal clean-checkout focused/full suites still run the audit. The diagnostic log is [retained here](logs/M6C-F01-focused-tests-fixture-diagnostic-20261031.log), SHA-256 `3c230c633f36583893e1afda8ed4ce275789b860749c8ff4f7faa97f8d5c6a2c`; it is not counted as a passing result.

The full suite used local CPU, the pre-existing Python 3.12.3 project environment, accepted M5 root manifest `a201a254671ad59ae1fecb402abf994d5bf523097f1c3010b5c7fa237ae6dd4c`, the pinned Warm checkpoint `0b2405017a8e1d539851f0cd278883d3fd23936fb5c2f7962c813590a6fd1767`, and accepted M4 r4 manifest `f00fde1c59325105e0ffd45bb45eb269dfa303416010c9a0b6c6be47bd9a9921`. No dependencies were installed. The Stockfish binary was used only by the existing UCI-readiness smoke test. No ALE campaign, training, fine-tuning, or artifact mutation occurred.

An earlier focused run at `29b3dcdfcdd21a454e4faa3778336249e76b92e6` exposed that the nested synthetic one-commit clone cannot resolve the historical M6 commits. The regression now skips only in that explicitly flagged synthetic clone. The final clean-checkout focused suite and full suite above pass with the audit enabled.

## Preserved decisions and experiment

PR #14's independent M6 acceptance remains intact. M6-001 remains `done`; G3 remains approved; G4 remains unapproved; M7 remains not started and unauthorized. Warm/Scratch outcomes, V1/V2 separation, PM6-F06 erratum, private model files, ROM, raw ALE traces, manifests, and every accepted M6 experimental result are unchanged. No Atari gameplay was rerun.

PR #15 remains open and unmerged for a fresh independent PM review and CI check at the updated HEAD. The companion [machine-readable audit](M6C-F01-provenance-audit-20261031.json) records the exact source/tree, file and log hashes, execution counts, and preserved governance state.
