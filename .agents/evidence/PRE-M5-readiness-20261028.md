# Pre-M5 Readiness Engineering Report — 2026-10-28

**Scope:** Engineering preparation for M5 only. This is not M5 authorization, M5 implementation/training, PM acceptance, G3 approval, or permission to merge. The PR author must stop at the PM review handoff under [PR_REVIEW_AND_INTEGRATION.md](../../docs/02-management/PR_REVIEW_AND_INTEGRATION.md). **Report finalized:** 2026-10-28 (UTC evidence timestamps are in the JSON record and command logs).

## 1. Executive result

Pre-M5 engineering deliverables are ready for independent PM review. The source baseline was `initial-idea` `906178775d48e98e64c709673bfe73177dd15c02`, matching the verified integration head at mission start. PRs #8 and #9 are merged there; this work is on a dedicated `feature/pre-m5-readiness` branch and does not write to `initial-idea` or `main`. PR #10 is open, non-draft, and unmerged. A fresh GitHub clone of code/test revision `0011a1c07e047cedf9394d70b2413cea74ba1437` passed the full 319-test suite, focused/context tests, artifact checks and preflight. This revision includes test-only robustness corrections described in §7. The report/checkpoint commit that follows contains evidence and governance-state updates; it does not alter M2–M5 implementation or test code. Exact PR and CI status at the verified source snapshot are recorded in the accompanying JSON and this handoff.

The exact M3 release and M4 checkpoint were found at the recorded local-only paths and independently verified. The M4-to-M5 representation-transfer dry-run used the real checkpoint and passed without Stockfish. Local CPU profiling stayed within its 15-minute and 2-GiB allowances. The algorithm, transition, experiment, checkpoint, test, resource, and future execution contracts are documented. No Double DQN learner, RL training, ALE learning, M5 authorization, PM acceptance, or G3 approval is claimed.

The PM review handoff, PR URL, source revision, and CI run are recorded in §8 and the JSON companion. The PR remains open and unmerged for independent PM review.

## 2. Starting repository and retrospective M4 audit (PM5-R01)

- Canonical remote at inspection: `origin/initial-idea` = `906178775d48e98e64c709673bfe73177dd15c02`; feature worktree `/tmp/atari-pre-m5-work`, branch `feature/pre-m5-readiness`.
- PR #8: [M4 implementation](https://github.com/dodaonam/atari-videochess-rl/pull/8), merged at `c0a284304d602817922772d08f0ff7904af7ae20`, implementation head `1f8f7db986f613818c7f70770d08c2c3a460a1cb`.
- PR #9: [M4 post-merge closeout](https://github.com/dodaonam/atari-videochess-rl/pull/9), merged at `906178775d48e98e64c709673bfe73177dd15c02`, head `19629ad3eecc4f16ccf5921ad28566a9b26e1744`.
- Read-only GitHub inspection reported no review submissions for PRs #8 or #9. Thus their merge is an integration fact, not evidence of the intended independent PM review. Record this as a **retrospective review-process exception**. This engineering audit is not independent PM approval; PM review of the historical implementation remains available and separate.
- Code was reviewed directly in `videochess_rl/model/{dataset,features,network,inference,checkpoint,training,cli}.py`, `simulator.py`, `action_contract.py`, `baselines.py`, and `benchmark.py`. Relevant focused tests and the full suite are rerun in this mission; earlier M4 test counts below are clearly labeled historical.
- Historical M4 records remain immutable, including the original 126/128 conflicting-input failure and diagnosis, the revised PM-approved selector and passing run, the r3 safe-load failure and fix, and the accepted final r4 run. M4 acceptance and post-merge records remain `.agents/evidence/M4-final-acceptance-20261027.md` and `.agents/evidence/M4-postmerge-delivery-verification-20261027.md`.

## 3. M3/M4 artifacts and transfer (PM5-R06)

Accepted M3 release: `/home/dodaonam/Projects/atari-videochess-rl-m3/artifacts/m3/training-support/release-final-closure-r6`.

- Release ID `f10a679deddf06f3e1e3c39cf58db4e21176629c26c09034a271bf278189e890`.
- Manifest SHA-256 `be1e1f9316fac01be893774cfe09a313de193fbd1a12ab2d219ff5c041104a12`.
- Split assignment SHA-256 `84efed824e57de45c0058b73818bb7a9d740201ead38e9171308cee43bc0934e`.
- 1,000 games; 19,268 retained positions; 15,196/2,015/2,057 train/validation/test; 732 purged positions; 182 rejected records. Exact identity was reverified on clean-clone revision `0011a1c`; all nine file hashes before/after are retained in `logs/PRE-M5-final-prhead-0011a1c-m3-release-immutable.log`.
- The accepted curated source's broader redistribution license remains unstated. Data and derived records stay local/outside Git; no regeneration, resplitting, upload, or redistribution occurred.

Accepted M4 checkpoint: `/home/dodaonam/Projects/atari-videochess-rl-m4/artifacts/m4/m4-behavior-20261027-r4/pretrained-behavior-only.pt`, SHA-256 `724ac730f3c5f2d01b48b26eb7670a3c764978a3dd4d6702b3057a99ab1a90a4`, 1,520,046 bytes. The read-only M4 artifact verifier accepted all 19 files; the run artifact inventory SHA-256 is `f00fde1c59325105e0ffd45bb45eb269dfa303416010c9a0b6c6be47bd9a9921`. Model/input schemas are `videochess-behavior-scorer/1.0` and `videochess-model-input/1.0`; the historical accepted parameter count is 121,897.

The transfer verifier was run in a separate process with `PATH=/usr/bin:/bin`. It loaded the real artifact through the safe loader, checked all 19 artifact files, transferred only shared representation weights, initialized a new Q head with seed `20261028`, copied the resulting online network to the target network, and scored representative legal UCI candidates through both the frozen behavior policy and untrained Q scorer. Both chosen moves were legal (`g1f3` and `a2a4`); `stockfish_path` was null and `chess.engine` was absent. The Q scorer is random-initialized and is not claimed as trained Q-values. Checkpoint and run bundle were verified unchanged before/after. See `scripts/verify_m5_transfer.py` and `logs/PRE-M5-transfer-verification-20261028.log`.

## 4. PM5 readiness matrix

| ID | Status | Work/evidence | Limitations / PM distinction |
|---|---|---|---|
| PM5-R01 | PASS | PR #8/#9 identities, source audit, M4 final/post-merge reports, and fresh clean-clone M2–M4 and full regression evidence; see §7. | No historical PR review submissions were found. The retrospective engineering record is not PM acceptance; PM may review M4 evidence independently. |
| PM5-R02 | PASS | `docs/02-management/PR_REVIEW_AND_INTEGRATION.md`, `AGENTS.md`, requirements, test, and handoff define implement → verify → PR → independent PM decision → authorized human/operator merge. | Branch protection and repository settings are not modified. GitHub reported `initial-idea` unprotected and no rulesets; documentation/tests cannot enforce API permission. |
| PM5-R03 | PASS | M4-001 stale `next_action` cleared; preflight now rejects nonempty `next_action` on done/cancelled tasks with regression coverage. M5-001 is pending and references only M5-01–05. State remains inactive/unauthorized, G3 unapproved. | M5 direct authorization remains a future decision. |
| PM5-R04 | PASS | `docs/03-technical/RL_ALGORITHM.md` specifies input/output, semantic UCI, target equation, terminal/truncation, reward, replay, exploration, updates, numerical failures, transfer, and checkpoint contract; exact online/target disagreement fixture supplied. Automatic-draw terminal semantics distinguish raw Board moves from the empty bootstrap candidate set. | No Double DQN implementation or learner test is claimed. |
| PM5-R05 | PASS | M2 source and tests verify fixed agent color, Black reset opening, action+reply boundary, agent-perspective reward, terminal priority, valid truncation next state, failure rollback, history and legal UCI. The seventy-five-move test confirms a draw Board may still have legal chess moves. | Actual Double DQN bootstrap implementation remains untested until M5. |
| PM5-R06 | PASS | Real checkpoint manifest/load/transfer/inference dry-run; exact hash and unchanged bundle; engine-free child process. | Local external artifact paths are not available from repository-only clean clones; no artifacts were copied to Git. |
| PM5-R07 | PASS | The config/protocol define one game per `(evaluation seed, opponent, agent color)`: 10 × 2 × 2 = 40 games per frozen policy checkpoint. Nine checkpoints yield 360 planned games, with 20 minutes per checkpoint and three hours aggregate. The schedule consistency fixture passed in the exact-head 127-test focused suite at `0011a1c`; see §7. | Proposed schedule only; no M5 benchmark has run. |
| PM5-R08 | PASS | `scripts/profile_m5_feasibility.py` and final JSON log provide bounded local CPU measurements. | 32-transition/profile sample and synthetic backward only; replay size is JSON wire estimate, not heap measurement. The proposed budget includes explicit hard stops and uncertainty. |
| PM5-R09 | PASS | `RL_ALGORITHM.md` defines `videochess-ddqn-checkpoint/1.0`, episode-boundary resume, state ownership, atomic update, integrity and previous-good retention. | Actual M5 serialization/resume code remains M5 work. |
| PM5-R10 | PASS | `docs/06-quality/M5_TEST_MATRIX.md` maps the requested future cases to fixtures, commands, outcomes and evidence. The exact-head 127-test focused suite includes all three M5 contract fixtures; PR CI also passed. | No DDQN learner exists yet. CI checks context and standard-library contract fixtures, not PyTorch/DDQN learning correctness. |
| PM5-R11 | PASS | `.agents/plans/M05-double-dqn.md` has prerequisites, baseline, modules, sequence, resources, tests, acceptance, recovery and stop conditions. | Plan is not authorization. |
| PM5-R12 | PASS | Fresh clean GitHub clone at exact pushed code/test revision `0011a1c07e047cedf9394d70b2413cea74ba1437`: preflight, archive, compile, 79 context/history tests, 127 focused tests, 319 full tests, M3/M4 artifact verification, engine-free transfer, diff and clean-status checks all passed. GitHub `context` CI passed on the same revision. Exact commands/times and logs are indexed by [the machine-readable clean-clone record](PRE-M5-final-clean-clone-0011a1c.json). | Full Python coverage used the existing locked Python 3.12.3 venv because `uv` is unavailable; no dependencies were installed. CI itself is not the full regression suite. |

## 5. Resource feasibility profile (PM5-R08)

Command: `PATH=/home/dodaonam/Projects/atari-videochess-rl/.venv/bin:/usr/bin:/bin PYTHONPATH=. /home/dodaonam/Projects/atari-videochess-rl/.venv/bin/python scripts/profile_m5_feasibility.py --checkpoint /home/dodaonam/Projects/atari-videochess-rl-m4/artifacts/m4/m4-behavior-20261027-r4/pretrained-behavior-only.pt --max-seconds 300`.

On baseline source SHA `906178775d48e98e64c709673bfe73177dd15c02`, profile script SHA-256 `c7dab9b842e138f657424064dc375bfdf68b3a21b84d45ff61f9b380f5381e97`; executed 2026-10-28 03:47:05–03:47:08 UTC, exit 0. Python 3.12.3, PyTorch 2.14.1+cpu, NumPy 2.5.4, python-chess 1.11.2, Linux x86_64, CPU and one intra/inter-op thread.

- 32 verified simulator transitions: 1,418.23 steps/s for `ChessSimulator.step()` only (not end-to-end learned-policy throughput).
- Full-history replay p50/p95/max 0.438/0.970/1.141 ms; feature encode p50/p95/max 0.616/0.746/0.863 ms.
- Sampled history plies min/p50/max 0/15/38; legal candidate count 4/37/51. These are a short random-play sample, not M3 corpus percentiles.
- Batch 8 online+target forward p50/p95/max 3.981/5.257/8.054 ms; 82,166 legal candidate scores/s for the sampled batch; one synthetic AdamW backward/clip/update 12.435 ms.
- Online tensor state 487,588 bytes; online+target tensors 975,176 bytes; temporary online+target state serialization 997,385 bytes in 2.81 ms (excludes optimizer and replay).
- Sampled compact transition JSON wire size p50/max 744/1,121 bytes; 4,096 × max = 4,591,616 wire bytes only, not Python heap or encoded tensor cache.
- The final profile used 1.144 s and peaked at 333,541,376 bytes RSS. Including the earlier instrumentation iteration (1.139 s; 333,582,336 bytes peak), total active profiling time was 2.284 s and the overall observed peak was 333,582,336 bytes, below the 900 s mission cap and 2 GiB RSS limit. Neither run created a persistent replay artifact or performed RL training. Both logs are retained locally; the final measurements are in `logs/PRE-M5-feasibility-profile-final-20261028.log`.

These measurements support a conservative CPU-first starting proposal; they do not guarantee useful learning or completion of paired training. The protocol proposes 10,000 valid decisions per arm/seed, 45 minutes per run, 6 hours aggregate, 2 GiB RSS, 4,096 replay transitions, three paired seeds; recheck feasibility after M5 authorization and stop symmetrically when a hard cap applies.

## 6. Governance, state and integration boundary

- `G0/G1/G2` remain approved; `G3` remains unapproved. M4 is complete. M5-001 is pending, `next_milestone_status: pending_user_approval`, `start_authorized: false`, and no active milestone/task exists. M5 has not started.
- The stale completed M4 task action is cleared; its evidence is retained. M5-001 is not marked in progress and does not create a new PRE-M5 criterion ID.
- GitHub reported no `initial-idea` branch protection (`404: Branch not protected`) and an empty repository ruleset list. This mission changes no GitHub settings. The PR-only governance is explicit but not an administrative branch rule.
- The read-only policy query and PR #8/#9 review/integration metadata are retained in `.agents/evidence/logs/PRE-M5-github-governance-readonly-20261028.log`.
- This work is not merged. The PM independently reviews the PR and decides; only an authorized human/operator performs any merge. Do not enable auto-merge.

## 7. Verification results

Verification was performed in the fresh GitHub clone `/tmp/atari-pre-m5-final-pr-10-0011a1c` at code/test SHA `0011a1c07e047cedf9394d70b2413cea74ba1437`, with a clean tree. Exact UTC times, commands, exit codes and logs are indexed in [`PRE-M5-final-clean-clone-0011a1c.json`](PRE-M5-final-clean-clone-0011a1c.json).

| Check | Command / method | Result | Evidence |
|---|---|---|---|
| Preflight and links | `python3 scripts/agent_preflight.py --json` | PASS at `0011a1c`; zero errors, one expected `ARTIFACT_MANIFEST_REQUIRED` warning; canonical state says G3 unapproved and M5 pending/unauthorized. | `logs/PRE-M5-final-prhead-0011a1c-preflight.log` (sanitized summary) |
| Checkpoint archive | `python3 scripts/migrate_checkpoint_history.py verify` | PASS; 197 archived records, logical SHA-256 `9b2cdb9d897399fafa47ef6a86ca265924e23e44cab268715136dc771c72ac6a`. | `logs/PRE-M5-final-prhead-0011a1c-archive.log` |
| Compile and cleanliness | `python -m compileall -q videochess_rl scripts tests`; `git diff --check`; `git status --short --branch` | PASS; compile and whitespace checks exit 0; clean branch clone. | `logs/PRE-M5-final-prhead-0011a1c-compile.log`, `...-diff_check.log`, `...-clean_status.log` |
| Context/recovery | `python -m unittest tests.test_agent_context tests.test_checkpoint_history -v` | PASS; 79 tests in 105.594 s. Includes completed-task action invariant, PR separation, clean-clone recovery and archive cases. | `logs/PRE-M5-final-prhead-0011a1c-context_tests.log` |
| Focused M2–M5 contract suite | `python -m unittest tests.test_m4_model tests.test_m4_data tests.test_m4_training tests.test_m4_checkpoint tests.test_pre_m4_contracts tests.test_m2_simulator tests.test_m3_data tests.test_m5_contract_fixtures -v` | PASS; 127 tests in 69.143 s. Evaluation-schedule fixture passed. | `logs/PRE-M5-final-prhead-0011a1c-focused_tests.log` |
| Full Python regression | `PATH=/home/dodaonam/Projects/atari-videochess-rl/.venv/share/stockfish:$PATH PYTHONPATH=. /home/dodaonam/Projects/atari-videochess-rl/.venv/bin/python -m unittest discover -s tests -v` | PASS; 319/319 in 187.650 s, exit 0. Completed 2026-10-28T05:25:22.237844Z on clean clone at `0011a1c`. Existing Stockfish was on PATH solely for the configured UCI readiness smoke test; no engine-based M5 use occurred. | `logs/PRE-M5-final-prhead-0011a1c-full_tests.log` |
| Preserved failures and test-harness corrections | The clean-clone full suite at `e102bd0` exposed an undersized synthetic four-second setup budget; a later focused run at `dc678a1` exposed a one-second fixture expiring during source parsing; an isolated diagnostic also reached a valid deadline before UCI startup. The final fixture uses bounded phase-aware deadlines and retains the intended overrun, status, elapsed-time and cleanup assertions. | All failed attempts remain separate and are not counted as passes. The corrected isolated test passed; then the 127-test focused and 319-test full suites passed at `0011a1c`. A dirty-worktree run remains classified as diagnostics only. | `logs/PRE-M5-final-prhead-e102-full-tests-failed.log` and `.meta`; `logs/PRE-M5-final-prhead-dc678a1-focused-tests-failed.log` and `.meta`; `logs/PRE-M5-m3-timing-diagnostic-dc678a1-isolated-failed.log` and `.meta`; corrected isolated pass log/meta; dirty diagnostic log/meta |
| M3 release identity and immutability | Existing pinned Python 3.12 CLI verifier with before/after SHA-256 inventory of all nine files | PASS 2026-10-28T05:25:47.740813Z–05:27:43.896968Z; expected release/manifest/split/counts; nine files unchanged. | `logs/PRE-M5-final-prhead-0011a1c-m3-release-immutable.log` |
| M4 bundle and engine-free transfer | `python -m videochess_rl.model.cli verify-artifacts <r4 dir>` and `PATH=/usr/bin:/bin ... scripts/verify_m5_transfer.py <checkpoint>` | PASS; 19 bundle files, SHA `724ac…90a4`, 121,897 parameters; representation copied, behavior head excluded, fresh seeded Q head and target copy, legal UCI inference, no `chess.engine` import/Stockfish, source artifacts unchanged. | `logs/PRE-M5-final-prhead-0011a1c-m4_bundle.log`; `...-transfer_engine_free.log` |
| GitHub CI | PR #10 `context` workflow | PASS on `0011a1c07e047cedf9394d70b2413cea74ba1437`; completed 2026-10-28T05:19:34Z. Run: [Repository preflight](https://github.com/dodaonam/atari-videochess-rl/actions/runs/40637273930/job/122647025278). CI is context/preflight and standard-library contract coverage, not the full Python suite. | Exact PR check URL above. |
| Dependency lock | Existing venv versions matched the direct `pyproject.toml` and `uv.lock` entries; `uv` is not installed. | PASS; Python 3.12.3; ale-py 0.11.2, chess 1.11.2, gymnasium 1.4.0, torch 2.14.1+cpu; no install/change. | `logs/PRE-M5-toolchain-check-20261028.log` |

The original e102 failure is a test-harness timing issue, not accepted M3 data corruption or a teacher-code failure: the test was meant to exercise finalization overrun but used too little wall time for verification/startup under a full-suite load. The assertion was not weakened; only its setup allowance and corresponding deliberate overrun delay were increased. The exact failed output and its metadata remain separate from the corrected passing run.

Captured test logs preserve test names, statuses, summaries, and exit codes. A whitespace-only trailing-space cleanup was applied to one captured diagnostic line after `git diff --check` identified it; the original semantic failure output remains intact.

## 8. PR handoff and limitations

**PR:** [#10 — docs: prepare M5 Double DQN readiness](https://github.com/dodaonam/atari-videochess-rl/pull/10)

**Base:** `initial-idea` at `906178775d48e98e64c709673bfe73177dd15c02`

**Exact code/test revision verified in a fresh clone:** `0011a1c07e047cedf9394d70b2413cea74ba1437`. A subsequent evidence/checkpoint commit updates only this report, machine-readable verification data, captured logs and the append-only canonical checkpoint/handoff record; it contains no implementation or test-code changes. **PR status at the last live check of the tested source snapshot:** OPEN, non-draft, target `initial-idea`, unmerged; no merge was attempted and auto-merge is disabled. The `context` check passed at the recorded Actions URL. The author does not self-approve or merge. The required next action is independent PM review and decision; any later integration must be performed by an authorized human/operator.

A PM decision does not itself authorize M5; a separate direct M5 authorization and canonical state transition remain necessary. This report does not claim instructor approval, G3, M5 implementation, M5 training, or ALE learning.

Nonblocking limitations: the M3 dataset license remains unresolved for redistribution; M3/M4 artifacts are local-only; `initial-idea` lacks configured branch protection; M4 #8/#9 lack GitHub review submissions in the available record; recurrent compression and DDQN target parity have not been tested in a learner; the small profile does not establish M5 learning quality or throughput at scale; M6 simulator-to-ALE parity remains future work.
