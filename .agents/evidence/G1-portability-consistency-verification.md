# G1 Pre-Commit Portability and Context Consistency Verification

- **Scope:** Separate the portable tracked baseline from local workspace observations, remove stale task authority prose, and verify recovery in a real clean clone.
- **Governance:** G0 and G1 remain approved. M0 remains `pending_user_approval`; M0/M1 work, commit, and push are outside this task.
- **Base revision:** `c410173ecccc3178ea41b4202ce6a4a437f9aafe` on `initial-idea`.
- **No commit or push was created.**

## Recovery design

`last_checkpoint.portable_git` records the staged tracked-file manifest as repository paths, Git modes, and blob IDs, plus semantic state and handoff checksums. It excludes the state file and handoff pointer from the manifest to avoid self-reference. A clean checkout whose `HEAD` manifest matches this snapshot is an expected commit/checkout transition and does not require storing a future commit hash.

`last_checkpoint.git` remains a workspace-local observation of branch, `HEAD`, status entries, ordinary-file hashes, and local artifact inventory. A per-clone Git config UUID distinguishes that workspace observation from a new clone. Legacy checkpoints remain readable; a clean commit transition is accepted only when every current tracked file can be checked against the legacy hash inventory. Checkpoint refreshes append the prior snapshot to `checkpoint_history`; the immutable G1-start baseline remains unchanged.

This inventory is also the regression fixture's approved baseline allowlist. Local-only files below are deliberately absent from the clone.

## Explicit exclusions (local-only)

- `chat_history.md`, the documentation ZIP archives, and local conversation exports.
- Untracked `main.py` and generated `__pycache__` directories.
- Credentials, datasets, and private artifact/model directories.

These paths are not part of the portable tracked manifest. Artifact/data directories present in a workspace still require independent manifests; tracked artifact contents remain covered by Git object IDs.

## Approved baseline inventory (30 paths)

- `.gitignore`
- `.python-version`
- `AGENTS.md`
- `README.md`
- `atari-videochess-rl-roadmap.html`
- `.agents/PLANS.md`
- `.agents/evidence/G1-10-recovery-verification.md`
- `.agents/evidence/G1-hardening-verification.md`
- `.agents/evidence/G1-git-baseline-verification.md`
- `.agents/evidence/G1-portability-consistency-verification.md`
- `.agents/plans/G1-consistency-hardening.md`
- `.agents/plans/M00-bootstrap.md`
- `.agents/state/BLOCKERS.md`
- `.agents/state/PROJECT_STATE.yaml`
- `.agents/state/SESSION_HANDOFF.md`
- `.agents/state/VERIFIED_FINDINGS.md`
- `.agents/tasks/BACKLOG.yaml`
- `docs/01-foundation/PROJECT_OVERVIEW.md`
- `docs/01-foundation/REQUIREMENTS.md`
- `docs/01-foundation/ROADMAP.md`
- `docs/02-management/EXECUTION_PLAN.md`
- `docs/02-management/RISK_REGISTER.md`
- `docs/02-management/decisions/ADR-0001-governance-crosswalk-and-file-priorities.md`
- `docs/05-operations/SETUP.md`
- `docs/06-quality/ACCEPTANCE_CRITERIA.md`
- `docs/06-quality/TEST_STRATEGY.md`
- `pyproject.toml`
- `scripts/agent_checkpoint.py`
- `scripts/agent_preflight.py`
- `tests/test_agent_context.py`

`README.md` is already tracked and unchanged; it is included in the baseline inventory but is not a staged change.

## Verification results

**Git revision:** `c410173ecccc3178ea41b4202ce6a4a437f9aafe` (`initial-idea`; staged baseline is not committed).

- **Executed:** `2026-10-14T16:51:30Z` — `python3 -m unittest discover -s tests -v`; exit code 0; `Ran 36 tests ... OK`.
- The clean-clone regression created a temporary Git repository from the 30-path allowlist, committed it, and cloned it into a separate directory. Before running recovery, the clone had no `chat_history.md`, documentation ZIPs, `main.py`, or Python cache directories.
- Clone preflight returned `portable_commit_transition`, matched the portable tracked baseline, recovered G1 as approved with O-01–O-08 open, recovered M0-001 as the pending next task dependent on G1-008, and kept M0 unauthorized. The cloned context suite passed with recursive clone testing disabled.
- The regression then created ordinary ignored caches and confirmed no source-content or hash-inventory drift. A real edit to tracked `PROJECT_OVERVIEW.md` produced `WORKTREE_CONTENT_DRIFT` and `repo_content_matches=false`.
- The same regression exercised a legacy checkpoint without the portable manifest and verified safe tracked-hash migration. A separate test confirmed that staging checkpoint-owned state/handoff files does not create a false workspace snapshot warning.
- **Checkpoint:** `2026-10-14T16:52:38Z` — `python3 scripts/agent_checkpoint.py`; exit code 0; wrote `cp-c410173e-20261014T165238186543Z`; its post-checkpoint preflight passed.
- **Preflight:** `2026-10-14T16:52:41Z` — `python3 scripts/agent_preflight.py`; exit code 0; no errors or warnings; workspace snapshot and portable index matched. It reported G1 approved, M0 pending and unauthorized, no active blockers, and O-01–O-08 open.
- **Staged review:** the 30-path approved allowlist matched exactly 29 staged files plus unchanged `README.md`; no excluded path was staged. `git diff --cached --check` and `git diff --check` both exited 0. The staged-blob scan found zero high-confidence secret patterns. `git check-ignore` confirmed exclusions for chat history, both documentation ZIPs, caches, datasets, artifacts, `.env`, and credentials; `main.py` remains preserved and unstaged.
- **Limitations:** this validates a local Git commit/clone simulation, not a commit to the project branch or a remote repository. No M0/M1, dependency setup, Colab, or RL work was run.

This Markdown record is the sanitized retained verification log. No credentials, chat transcript, environment dump, ZIP contents, or private artifact contents were retained.
