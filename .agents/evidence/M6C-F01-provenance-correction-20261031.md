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

The first consolidated audit covered 20 M6-001 evidence entries introduced or modified by PR #15: four file identities, fourteen verified command/test records, and two prior diagnostic records explicitly classified historical/unverified. It additionally checked the eight command logs referenced by the machine-readable post-merge report. Two of the fourteen verified execution records were failed diagnostics (the earlier system-Python/setup attempt and the synthetic one-commit clone fixture); both were explicitly distinguished from passing checks. The later clean-checkout run added four retained failed diagnostic records and three successful post-append records; final audit coverage therefore includes 35 scoped entries (four file identities, 29 verified command/test executions, and two historical/unverified diagnostics) plus the eight machine-report log references. Existing M6 experiment and training evidence outside those closeout entries was not rewritten or reclassified.

### Clean-checkout correction discovered during final verification

A subsequent clean detached checkout at `f9622885f7b4ca750fac4ab7a1d99bed808d1386` exposed a gap in the first audit implementation: `.agents/evidence/logs/M6C-F01-consolidated-audit-20261031.log` existed in the original workspace but was ignored by Git (`*.log`) and therefore absent from the committed tree. The 08:47 audit had read the local file and returned exit 0, but that run did not establish that the cited log was committed or available to reviewers. The clean checkout correctly failed six context tests and preflight because the referenced log was absent; the full suite had those same six failures plus one Stockfish smoke-test failure because the isolated command omitted the existing readiness binary from `PATH`.

The correction now makes the provenance auditor require every verified, historical, and machine-report log to exist in `HEAD` (`git cat-file -e HEAD:<path>`), in addition to checking the working bytes and SHA-256. A regression test simulates a log that exists in the filesystem but is absent from `HEAD` and requires rejection. The previously ignored 08:47 audit log and the four clean-checkout failure diagnostics are retained as tracked evidence; they are explicitly not passing checks. The final rerun uses the pre-existing project Stockfish readiness directory in `PATH`. This is an audit-hardening issue in the closeout evidence path; it does not affect M6 gameplay results or prior PM acceptance.

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
| First final clean-checkout verification | FAIL diagnostic; audit/preflight and six focused tests found the referenced audit log was ignored/uncommitted; full suite had those six failures plus missing Stockfish `PATH` | 08:52:00.916–08:55:27.909 | Logs are retained as tracked clean-checkout diagnostics; exact SHA-256 values are in the companion machine report and backlog entries. |
| Corrected clean-checkout focused suite | PASS; 110 passed, zero failures/errors/skips | 08:58:23.557–08:59:20.283 | `d67ecfeb96b200a82b228439d20feaee971b7100a9030c22898a01b1f55e33fb` |
| Corrected clean-checkout full suite | PASS; 454 passed, zero failures/errors/skips; 168.898 seconds unittest time | 08:59:20.283–09:02:11.277 | `05cf4f776cdd2168255c28c6634ad01b432518d4d146b3a3114d9352fa53a251` |
| Corrected committed-tree provenance audit | PASS; at that revision, four file identities, 22 verified command/test logs, eight machine-report log references, two historical diagnostics, zero errors | 09:02:11.277–09:02:11.491 | `e4ee0d551c47c7aad9eebcd993dbe2db4fb9268a48f00499db9dbfb2858b0960` |
| Corrected clean-checkout canonical preflight | PASS; zero validation errors; expected local artifact-manifest warning | 09:02:11.491–09:02:12.933 | `4344a020f7ea9d3d009a3e4d03a0c85bd056e26b9e15d4b839a2641b6995a708` |
| Post-append provenance audit | PASS; four file identities, 26 verified command/test logs, eight machine-report logs, two historical diagnostics, zero errors | 09:04:36.086–09:04:36.317 | `bb5e64d9be722b1431b8fa52d643f535bdd6b7cb756fedfa0bf28ec0f3e6d11e` |
| Post-append focused suite | PASS; 110 passed, zero failures/errors/skips | 09:04:37.702–09:05:34.021 | `80d7dd77c11e87a151cf8704bf4d11083ca1fe6b5cdc2c717ca407540e46ff4d` |
| Post-append canonical preflight | PASS; zero validation errors; expected local artifact-manifest warning | 09:04:36.317–09:04:37.702 | `e7fd76fe163b25d94aa27e1c8f4e39e5ac020898cd211cab5c709086c856355e` |

The corrected clean-checkout suite ran on commit `2050db70894f40b8ca4e4b6ebdc7715f1664f3bc`, tree `deb4fcb0395632deebd48e0bab67a70e8fe7d828`. Its four successful logs and the four preceding failed diagnostic logs are preserved as tracked files and recorded with exact source revisions and hashes in `BACKLOG.yaml`. A clean checkout at `d20b8b7942fdd5be77541d5605cabc5bebfde432` then passed a post-append audit of the 26 records committed at that point, the focused suite (110/110), and preflight. Those three execution records bring the scoped evidence to 35 entries: four file identities, 29 verified command/test executions, and two historical/unverified diagnostics. A final audit after those records are committed is still required. The earlier synthetic-clone diagnostic remains preserved at [its log](logs/M6C-F01-focused-tests-fixture-diagnostic-20261031.log), SHA-256 `3c230c633f36583893e1afda8ed4ce275789b860749c8ff4f7faa97f8d5c6a2c`; it is not counted as a passing result.

The full suite used local CPU, the pre-existing Python 3.12.3 project environment, accepted M5 root manifest `a201a254671ad59ae1fecb402abf994d5bf523097f1c3010b5c7fa237ae6dd4c`, the pinned Warm checkpoint `0b2405017a8e1d539851f0cd278883d3fd23936fb5c2f7962c813590a6fd1767`, and accepted M4 r4 manifest `f00fde1c59325105e0ffd45bb45eb269dfa303416010c9a0b6c6be47bd9a9921`. No dependencies were installed. The Stockfish binary was used only by the existing UCI-readiness smoke test. No ALE campaign, training, fine-tuning, or artifact mutation occurred.

An earlier focused run at `29b3dcdfcdd21a454e4faa3778336249e76b92e6` exposed that the nested synthetic one-commit clone cannot resolve the historical M6 commits. The regression now skips only in that explicitly flagged synthetic clone. The final clean-checkout focused suite and full suite above pass with the audit enabled.

## Preserved decisions and experiment

PR #14's independent M6 acceptance remains intact. M6-001 remains `done`; G3 remains approved; G4 remains unapproved; M7 remains not started and unauthorized. Warm/Scratch outcomes, V1/V2 separation, PM6-F06 erratum, private model files, ROM, raw ALE traces, manifests, and every accepted M6 experimental result are unchanged. No Atari gameplay was rerun.

The corrected implementation and regression tests passed the clean-checkout focused and full suites on commit `2050db70894f40b8ca4e4b6ebdc7715f1664f3bc`; a further post-append focused/audit/preflight set also passed at `d20b8b7942fdd5be77541d5605cabc5bebfde432`. The final audit after those records are committed and a fresh PR CI result remain required before handover. PR #15 remains open and unmerged for fresh independent PM review. The companion [machine-readable audit](M6C-F01-provenance-audit-20261031.json) records the source/tree, file and log hashes, execution counts, and preserved governance state.
