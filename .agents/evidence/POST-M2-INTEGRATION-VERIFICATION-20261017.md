# Post-M2 Integration Verification

- **Recorded:** 2026-10-16T17:44:31Z
- **Purpose:** Reconcile canonical project context with the actual GitHub squash merge of M2 PR #1.
- **Repository:** https://github.com/dodaonam/atari-videochess-rl
- **Verified integration commit:** 27dd9f73d2bf7545e194fe40391d0cae5f9b9003
- **Verification worktree:** feature/pre-m3-readiness, created cleanly from origin/initial-idea at the commit above.

## Remote and PR facts

- A fresh read of origin refs reported initial-idea at 27dd9f73d2bf7545e194fe40391d0cae5f9b9003 and main at c410173ecccc3178ea41b4202ce6a4a437f9aafe.
- GitHub reports PR #1, feat(m2): implement and verify chess foundation, state MERGED; base initial-idea; head feature/m2-chess-foundation; merge time 2026-10-16T16:34:50Z; merge commit 27dd9f73d2bf7545e194fe40391d0cae5f9b9003.
- main is an ancestor of initial-idea. The range comparison reports zero commits unique to main and 26 commits unique to initial-idea. No branch was merged or rewritten for this verification.
- GitHub reports default branch main. It remains at the original c410173 commit and is 26 commits behind the M2 integration tip.
- Existing feature/m2-chess-foundation remains associated with the merged PR. feature/pre-m3-readiness did not exist remotely at baseline. GitHub reported no open PRs.
- No newer commit appeared on initial-idea beyond the supplied M2 anchor at the time of inspection.

Commands and sources inspected:

- git fetch origin; git ls-remote origin refs/heads/initial-idea refs/heads/main refs/heads/feature/pre-m3-readiness
- git rev-list --left-right --count origin/main...origin/initial-idea
- git show -s --format=%H\ %P\ %s origin/main and origin/initial-idea
- gh pr view 1 --json mergeCommit,mergedAt,baseRefName,headRefName,state,url
- gh repo view --json defaultBranchRef,url
- gh pr list --state open --json number,title,baseRefName,headRefName

## Local checkpoint and preserved work

The pre-existing primary checkout was at 11b6dfe67c961bca3d5d693d87a1f27448983487, one commit behind the refreshed remote integration branch. It had a deleted tracked source HTML file and two untracked local files: main.py and .agents/evidence/M1-04-terminal-success-20261016.zip. These were not copied, reset, staged, or edited. Their observed sizes and SHA-256 digests at inspection were:

| Local path | Bytes | SHA-256 |
|---|---:|---|
| main.py | 97 | c101b2abfee28217d24a7c550eda37cffe548adfc9149244646199108361c0fe |
| .agents/evidence/M1-04-terminal-success-20261016.zip | 128574 | 340ba2da7ff6eeea4fc71e8769c3eb5e32b2039997870d61f8a42290c1c8f81a |

A separate clean worktree was created from the verified remote baseline so the user-local deletion and untracked files remain intact. Its agent preflight passed and reported an expected portable commit/checkout transition. It reported the known ARTIFACT_MANIFEST_REQUIRED warning because ignored artifact contents are not present in a clean clone and must be checked independently.

In the primary local checkout, the dated M1 manifests MANIFEST-20261015.sha256 and MANIFEST-20261016.sha256 each verified all listed entries: 1,214 and 1,388 entries respectively, with no missing files or hash mismatches. The older unversioned MANIFEST.sha256 listed 327 paths absent from the present artifact tree; it remains untouched as a historical/stale manifest and is not treated as the current artifact inventory.

## Canonical status reconciliation

- M2-001 and M2-01 through M2-04 remain complete and accepted; PR #1 is now integrated.
- G2 remains approved.
- G3 remains unapproved.
- M3 remains not started, not authorized, and pending separate owner authorization.
- O-01 through O-08 remain open unless the canonical requirement record later changes with appropriate authority.
- This verification does not approve G3, resolve any external approval, or authorize M3 data acquisition, Stockfish analysis, training, or compute.

