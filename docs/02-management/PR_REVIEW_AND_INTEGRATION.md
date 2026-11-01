# Pull Request Review and Integration Authority

**Status:** Owner governance instruction, adopted for current and future work on 2026-10-28. It supersedes historical mission text that allowed an engineering executor to merge after checks passed. Repository settings and branch protections are not modified by this document.

## Required workflow

1. **Codex implements** only the scope directly authorized by the current user and canonical state.
2. **Codex verifies** the proposed revision, preserves evidence, and corrects findings within scope.
3. **Codex opens or updates one PR** against the canonical integration branch and records exact head/check status.
4. **PM independently reviews** the actual diff, evidence, CI scope, and acceptance criteria. The PR author cannot self-issue PM acceptance, whether the author is Codex or a human contributor.
5. **PM decides** whether to accept, request changes, or reject the PR.
6. Only after that decision, an **authorized human/operator performs any merge** through the approved repository workflow.

Engineering completion, a green CI run, a direct task/milestone implementation authorization, a complete acceptance checklist, or a historical mission instruction is not merge permission. Codex must not merge any PR, approve its own PR as PM, use merge APIs/CLI, push directly to `initial-idea` or `main`, or enable auto-merge. The engineer's final action is the PR handoff and a truthful report of any remaining checks or external restriction.

## Separate status dimensions

Keep these facts distinct in state and evidence:

- implementation/engineering acceptance: whether code and evidence satisfy technical criteria;
- PM review decision: pending, changes requested, accepted, or rejected;
- repository integration: not merged or merged by an authorized operator;
- milestone authorization: direct authorization to start the next milestone;
- governance gate status: approved only through its separate decision process.

No PR, test, or milestone completion may infer the other statuses. A ready-to-review task remains not merged until the authorized integration event is observed. A merged PR does not by itself authorize a later milestone.

## Protection and CI limitations

Before submission, inspect branch protection/rulesets read-only and report actual findings. Do not change repository settings under an engineering mission. If the canonical branch lacks protection or GitHub review submissions are absent, record the risk and request independent PM/operator review; do not bypass policy by merging. A context-only workflow is described only by its actual job steps and is never represented as a full regression or PyTorch correctness run. Future PRs must attach exact clean-clone tests when CI does not run them.

This policy is reviewable and has a repository consistency test, but a text test cannot technically prevent a credentialed operator or API caller from merging. Administrative enforcement requires an authorized repository owner to configure GitHub protections; this document does not claim such configuration exists.

## Recorded one-time owner exception — PR #20

On 2026-11-01, the Project Owner issued a direct, PR-specific instruction authorizing Codex to integrate PR #20 only at the Independent PM-approved head `ec7ab8c0fe097004eb4d37018be898c68f41364b`, after checking the authentic PM decision and exact-head CI. The PM's [decision comment](https://github.com/dodaonam/atari-videochess-rl/pull/20#issuecomment-6556836388) explicitly accepted that revision for integration. The authorization and actual merge are recorded in [G5-PR20-integration-authorization](../../.agents/evidence/G5-PR20-integration-authorization-20261101.md) and [G5-PM acceptance](../../.agents/evidence/G5-PM-acceptance-20261101.md).

This narrowly records that one-time exception to the general no-Codex-merge rule; it creates no standing merge authority. At the time, GitHub reported no branch protection or repository ruleset for `initial-idea`, and there was no formal PR review-submission object; the PM's verified issue comment was the decision source. No repository settings were changed. The separate G5 governance-closeout PR remains outside this exception and must receive fresh Independent PM review; Codex must not approve or merge it.
