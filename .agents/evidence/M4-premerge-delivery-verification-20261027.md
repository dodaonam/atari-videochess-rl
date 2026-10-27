# M4 Pre-merge Delivery Verification — 2026-10-27

## Scope

This report verifies the proposed M4 PR delivery before merge. It does not claim that PR #8 is merged or that post-merge verification has run.

- Repository: dodaonam/atari-videochess-rl
- PR: https://github.com/dodaonam/atari-videochess-rl/pull/8
- Base: initial-idea
- Branch: feature/m4-supervised-pretraining
- Exact clean-clone PR head: f17933b12ce5cbc0b1b8bb9b0be71961caab6d37
- Clean-clone worktree: clean before and after verification.
- Clean-clone path used: /tmp/atari-m4-pr-clean-d67f833 (detached at the exact SHA above).

## Clean-clone results

| Check | Command or method | Result |
|---|---|---|
| Canonical context | python3 scripts/agent_preflight.py --json | PASS; zero errors; only ARTIFACT_MANIFEST_REQUIRED for ignored local artifacts; portable manifest matches. |
| RSK-010 archive | python3 scripts/migrate_checkpoint_history.py verify | PASS; 182 records; logical SHA-256 8a3f6454029557185d42dd2f6d585ea73970c716c73dd36f1d15fb363590aab0. |
| Checkpoint artifacts | python -m videochess_rl.model.cli verify-artifacts /home/dodaonam/Projects/atari-videochess-rl-m4/artifacts/m4/m4-behavior-20261027-r4 | PASS; 19 files; 121,897 parameters; checkpoint SHA-256 724ac730f3c5f2d01b48b26eb7670a3c764978a3dd4d6702b3057a99ab1a90a4. |
| Focused suite | Pinned Python 3.12 interpreter; tests.test_m4_model, tests.test_m4_data, tests.test_m4_training, tests.test_m4_checkpoint, tests.test_pre_m4_contracts, tests.test_m2_simulator, tests.test_m3_data | PASS; 124 tests; 45.891 s; exit 0. |
| Full suite | Pinned Python 3.12 interpreter; python -m unittest discover -s tests -v | PASS; 313 tests; 99.289 s; exit 0. |
| Compile/diff | compileall and git diff --check were run on the source revision before this documentation-only delivery commit. | PASS on M4 source revision 7b3c9074a2d932fec6d7732ee08e99b9de10a135. |

The focused and full test logs record the exact shell commands, timestamps, summaries, and exit codes:

- .agents/evidence/logs/M4-premerge-clean-clone-focused-f17933b-20261027.txt — SHA-256 dbcd2c8aa7e5bdb1d01885bab81cdcd863b264f798df328ca1953f88c0beb50e
- .agents/evidence/logs/M4-premerge-clean-clone-full-f17933b-20261027.txt — SHA-256 672aef1dd02f9e1ae130ad67cd609ad2d3d49c789c6437cb52f001c0f0a9ec30
- .agents/evidence/logs/M4-premerge-clean-clone-integrity-f17933b-20261027.txt — SHA-256 bc9fff7380b327bb095595e1dd8df8b188a0054d46dec3dcfc2a193a72423979

The shared local M3 release remained outside Git. Its post-run fresh verifier passed on the source revision and is recorded in .agents/evidence/logs/M4-final-m3-verification-20261027.txt. The frozen checkpoint remains outside Git and was verified from the clean clone against its manifest.

## GitHub check

On exact PR head f17933b12ce5cbc0b1b8bb9b0be71961caab6d37, the Repository preflight workflow passed:

- Run: https://github.com/dodaonam/atari-videochess-rl/actions/runs/40545335450/job/122334308375
- Check: context — SUCCESS.

This workflow is a context/preflight check; the separate 124 focused and 313 full Python tests above provide regression coverage. An earlier PR-head check failed because five verified backlog log paths referenced ignored, uncommitted files. Those sanitized logs are now tracked; local and clean-clone preflight pass on the corrected head.

At report time PR #8 is open and draft, merge state clean, and no required review decision is reported. The authorized executor may remove draft status and merge only after confirming the live head, status checks, and repository protections again. Post-merge integration and clean-clone verification remain required.

Overall result: PASS — exact PR head f17933b12ce5cbc0b1b8bb9b0be71961caab6d37 passed clean-clone preflight, archive verification, artifact verification, 124 focused tests, and 313 full regression tests; the GitHub context check succeeded. PR merge remains pending.

## M4 status and boundaries

M4-01 through M4-04 technical acceptance is recorded in .agents/evidence/M4-final-acceptance-20261027.md and its machine-readable companion. O-01 remains closed internally; no instructor approval is claimed. G3 remains unapproved. M5/M6 are not started or authorized. The accepted M3 package's broader redistribution license remains unstated; dataset and model artifacts remain local and outside Git.
