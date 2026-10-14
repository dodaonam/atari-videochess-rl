# G1 Git Baseline Preparation

- **Approval:** User explicitly approved G1 on 2026-10-14 after G1-10 was accepted. This record documents G1 approval only; it did not authorize a commit or M0/M1 work at the time.
- **Recorded at (UTC):** 2026-10-14T15:37:31Z.
- **Base Git revision:** `c410173ecccc3178ea41b4202ce6a4a437f9aafe` on branch `initial-idea`.
- **Purpose:** Prepare a reviewable staged baseline of approved project documentation, governance context, G1 evidence, automation, tests, and project configuration. No commit or push was created.

## Worktree audit

The initial worktree had two tracked files (`.gitignore`, `README.md`) and 29 untracked paths. The only ignored files found were Python bytecode caches under `scripts/__pycache__/` and `tests/__pycache__/`. No symlinks, credentials, datasets, model weights, or private artifact directories were found. The 949,319-byte roadmap HTML source is retained; the 354,563-byte documentation ZIP and `chat_history.md` are excluded. The 97-byte `main.py` is an existing hello-world stub and is left untouched outside this documentation/configuration baseline. The pyproject description placeholder was replaced with a project description.

The original `.gitignore` covered Python caches, local environments, logs, and several tool outputs, but did not exclude the conversation export or documentation archive and lacked project data/artifact and common credential patterns. It now excludes those items, generated model artifacts, and temporary files. High-confidence secret-pattern scan found no matches in candidate text files; `chat_history.md`, the ZIP, and bytecode caches were not opened or staged.

## Verification runs

- `python3 -m unittest discover -s tests -v` at 2026-10-14T15:37:54Z: exit 1; one recovery test saw Git/hash snapshot drift after the authorized state and ignore-rule edits. Preflight diagnostics showed only `GIT_SNAPSHOT_DRIFT` and `WORKTREE_CONTENT_DRIFT` warnings, with no validation errors.
- `python3 scripts/agent_checkpoint.py` at 2026-10-14T15:38:37Z: exit 0; refreshed the checkpoint and its internal preflight passed.
- `python3 -m unittest discover -s tests -v` at 2026-10-14T15:38:47Z: exit 0; all 33 context tests passed.
- `python3 -m unittest discover -s tests -v` at 2026-10-14T15:40:05Z: exit 0; all 33 context tests passed again after the verification record was completed.
- `python3 -m unittest discover -s tests -v` at 2026-10-14T15:46:56Z: exit 0; all 33 context tests passed after the Markdown whitespace cleanup.
- `python3 scripts/agent_preflight.py` at 2026-10-14T15:39:08Z: exit 0; PASS; Git status and content-hash snapshots matched, and 30 ordinary files were hashed.
- Secret-pattern scan and `.gitignore` path checks at 2026-10-14T15:39:25Z: exit 0; no high-confidence secret patterns found; conversation history, documentation ZIP, local secret/credential examples, model artifacts, and checkpoint temp files matched ignore rules.
- `git diff --cached --check` and `git diff --check` at 2026-10-14T15:42:53Z: exit 0 after replacing five Markdown hard-break trailing spaces with `<br>` and removing one extra blank line at EOF; rendered line breaks are preserved.
- Final staged review at 2026-10-14T15:49:03Z: `git diff --cached --check`, `git diff --check`, and `git diff --exit-code` all exited 0. The 29-path inventory equals the 28 staged changes plus the already-tracked, unchanged `README.md`; there are no unexpected staged paths.
- Staged-blob secret scan at 2026-10-14T15:49:03Z: exit 0; no high-confidence secret patterns found.
- Post-stage `python3 scripts/agent_preflight.py --json` at 2026-10-14T15:49:03Z: exit 0, no errors, content hashes match. It reports one expected `GIT_SNAPSHOT_DRIFT` warning because `PROJECT_STATE.yaml` and `SESSION_HANDOFF.md` were staged after the latest checkpoint; their contents and all other content hashes match.
- **Git revision for these runs:** `c410173ecccc3178ea41b4202ce6a4a437f9aafe`.
- **Retained sanitized results:** `.agents/evidence/G1-git-baseline-verification.md` (this file). No credentials, environment dumps, or conversation transcript are retained.

## Exact baseline inventory (29 paths)

`README.md` is already tracked and remains unchanged, so it belongs to the baseline inventory but does not appear in the staged change list.

- `.gitignore`
- `.python-version`
- `AGENTS.md`
- `README.md`
- `atari-videochess-rl-roadmap.html`
- `.agents/PLANS.md`
- `.agents/evidence/G1-10-recovery-verification.md`
- `.agents/evidence/G1-hardening-verification.md`
- `.agents/evidence/G1-git-baseline-verification.md`
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

## Explicit exclusions

- `chat_history.md` — private conversation history; ignored and not opened.
- `atari-videochess-rl-documentation-g1.zip` — redundant documentation archive; ignored and not opened.
- `scripts/__pycache__/` and `tests/__pycache__/` — generated bytecode caches; ignored.
- `main.py` — pre-existing hello-world stub outside the approved G1 documentation, context, test, and configuration baseline; preserved unmodified and unstaged.
- No credentials, datasets, model weights, or private artifacts were present in the audited tree.

## Authorization and next milestone at record time

G1 was recorded as approved. M0 was the next milestone and remained not started and unauthorized at the time of this baseline-preparation record; M1 remained dependent on M0. The staged inventory and proposed commit message were prepared for review, with no commit or push created. Live phase and authorization are maintained in `.agents/state/PROJECT_STATE.yaml` and the latest direct user instructions.
