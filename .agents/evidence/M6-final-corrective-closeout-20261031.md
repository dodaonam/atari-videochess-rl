# M6 final corrective closeout — engineering handover

**Engineering disposition:** Pending final full-suite and canonical preflight execution. No PM acceptance is claimed. M6 remains `in_progress`; G4 remains unapproved; M7 remains unauthorized.

**PR:** [#14](https://github.com/dodaonam/atari-videochess-rl/pull/14), base `initial-idea`. This closeout updates the existing PR and does not create a new experiment or milestone.

## Scope and preservation

This closeout is limited to PM6-F06, independent read-only verification of existing v1/v2 raw evidence, regression coverage, and handover documentation. No ALE reset/action, model inference for gameplay, training, fine-tuning, checkpoint substitution, or new official attempt was performed. The Stage 3 v1/v2 configs, schedules, source identities, run manifests, traces, RGB evidence, ledgers, accepted M4/M5 artifacts, and outcomes remain unchanged.

The execution source for Stage 3 v2 remains `91f51b14690eba12e9e4fd25a4fc1671801fac0d` (tree `4d6ed616971c8f5606a0a7250fe68fa2eea40949`). Corrective code is in commits `8c8eab874054db8e15afa7aa3a0cefb1876fddf2` and `fbcc9826032bb390acb91b240787ba4b0d3409a0`; it does not retroactively change that execution identity.

## PM6-F06 — root cause and correction

The v2 config defines a 43,200-second `gameplay_wall_budget_scope` that covers Stage 3 v2 only and excludes historical v1 and completed diagnostics. The original run manifest nevertheless records `budget.gameplay_wall_budget_includes_diagnostics=true` because the original shared `_run_manifest()` used `.get(..., True)` when the v2 schema omitted the legacy boolean. A later summary copied that value. The original manifest SHA-256 is `e5870bdc4c1aa05108ed58eacc6ec95123ab2b4bc9436d43c9c9640113eabd83`; the frozen config SHA-256 is `663651050db80ab027b452241c7d39837ec7986927c0aefc7c7be631f459a49b`.

The inconsistency affected metadata only. The v2 enforcement path reads the frozen v2 wall ceiling and sums attempt time in its isolated v2 artifact root; it does not consult this boolean. The v2 path rejects diagnostics. The immutable run record reports zero prior v2 use; the raw audit reconstructed 3,519.969 seconds of gameplay, no resource-stop events, and per-attempt use within the fixed caps. V1's corresponding `true` remains correct under its separate diagnostic-inclusive scope.

`campaign.py` now binds budget metadata to the protocol schema: v2 requires its exact textual scope and serializes `false`; v1 retains its accepted `true` meaning. Missing or conflicting scope is rejected. Resource arithmetic is unchanged. Tests cover both schemas, serialization, conflicts, v1/v2 budget isolation, and frozen config/schedule hashes. The original manifest was not repaired in place; its incorrect value and impact are recorded in the [PM6-F06 erratum](M6-PM6-F06-erratum-20261031.md).

## Independent raw-evidence audit

The final portable r3 standard-library verifier was run read-only against both the preserved local copy and the original execution roots. It does not import the original campaign summary or ledger verifier and does not open ALE. Reports, exact commands, timestamps, verifier source identity, and report hashes are in the [human audit](M6-stage3-v2-independent-raw-audit-20261031-r3.md), [persistent-copy machine report](M6-stage3-v2-independent-raw-audit-20261031-r3.json), [original-root machine report](M6-stage3-v2-original-root-audit-20261031-r3.json), and audit logs.

The verifier checked the complete artifact inventories, every listed path/size/SHA-256, safe paths and non-symlink regular files, run/config/schedule/source/ROM/checkpoint identities, all per-attempt manifests, trace hashes and internal chains, and both event ledgers. V1: 4,540 files / 616,539,017 manifest bytes, 839,785 ledger events, 35 starts/resets/finishes. V2: 4,159 files / 728,148,524 manifest bytes, 968,132 ledger events (ledger SHA-256 `c8364fa194a65c8de6d90bf9165743a411d0a63eba2459f3023821f3d0d838cb`), 20 unique scheduled slots, resets, per-attempt manifests and traces. No missing/unexpected entries, unsafe paths, symlinks, duplicate attempts, omitted slots, retries, or reset replacements were found.

The v2 run identity is `m6-stage3-v2-91f51b14690e-d05d42400cfc`; config SHA-256 `663651050db80ab027b452241c7d39837ec7986927c0aefc7c7be631f459a49b`; schedule SHA-256 `be4e6548e6fd3e3db4605e6b55fbe860848dccb2df87d8a7122145bdabe22ffc`; root M5 manifest SHA-256 `a201a254671ad59ae1fecb402abf994d5bf523097f1c3010b5c7fa237ae6dd4c`; runtime-recorded ROM SHA-256 `d44f2a115393b0a6cbcd5398d62369e652f3670a9ee585883d183e740edad0f7`. Frozen Warm and Scratch checkpoint and sidecar hashes are listed in the audit report and match the accepted roster.

The original and persistent raw roots are retained locally at repository-relative `artifacts/m6/...` and `artifacts/m6-preserved-20261031/...`. Their raw RGB and traces are not committed or uploaded. The current repository checkout can verify them locally; an independent reviewer on a different host will need separately authorized access to that local artifact filesystem to inspect raw bytes. The sanitized reports expose hashes and per-attempt evidence summaries without publishing private bytes.

## Reconstructed v2 results

These are independently reconstructed historical experiment results, not gameplay generated during this closeout.

| Policy | Attempts | ALE terminal W/D/L | Terminal unknown | Incomplete | Initiated / RGB-verified moves | Verified Atari replies | Cursor displacement corrections | Board desynchronizations |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Warm | 10 | 0 / 0 / 4 | 0 | 6 | 232 / 222 | 222 | 1,157 | 0 |
| Scratch | 10 | 0 / 0 / 7 | 0 | 3 | 173 / 163 | 163 | 714 | 0 |
| **Total** | **20** | **0 / 0 / 11** | **0** | **9** | **405 / 385** | **385** | **1,871** | **0** |

The nine incomplete attempts were five Atari reply timeouts, two source-selection uncertainty stops, and two target-navigation uncertainty stops. Each scheduled attempt has one pending final move categorized exactly once. There are no draws, terminal-unknown outcomes, retries, substitutions, or resource-stop events. The primary initiated-move metric remains 385/405 RGB-verified (95.0617%); per-policy rates are 222/232 Warm and 163/173 Scratch. Descriptive Wilson intervals are retained in the raw audit and do not account for within-game correlation. All 11 terminal results have authoritative `terminated=true`, `truncated=false`, finite White reward `-1.0`, verified terminal trace/image identities, and no post-terminal action. The last verified FEN is retained because the terminal screen may clear.

Runtime accounting: 1,936,199 final ALE frame-counter units; 1,936,119 post-reset action frames after subtracting the verified reset offset; 484,035 ALE environment steps; 3,519.969 seconds gameplay; peak RSS 620,105,728 bytes; 728,148,524 retained artifact bytes; 6,131 ambiguous/unlocated RGB or cursor observations; zero unresolved cursor displacements. All v2 frame, wall, memory, campaign, and artifact ceilings were respected. V1 and v2 remain distinct protocols; the v2 reused-seed extended-horizon re-evaluation is not independent held-out evidence and supports no Warm/Scratch superiority or Elo claim.

## Findings and current acceptance evidence

| Item | Engineering evidence status | Evidence / limitation |
|---|---|---|
| PM6-F06 | PASS | Schema-aware manifest generation and regression tests; immutable historical inconsistency retained with erratum; runtime impact independently checked. |
| PM6-F01–F05 | PASS | Previously completed corrective implementation and v2 campaign remain supported by the existing final M6 report and the r3 raw audit. |
| M6-01 | PASS (engineering evidence) | Genuine ALE RGB-derived structured policy observations and per-decision trace bindings; raw evidence is local-only. |
| M6-02 | PASS (engineering evidence) | 385 verified player moves and replies, typed safe stops, no recorded board desynchronization; nine attempts remain incomplete. |
| M6-03 | PASS (engineering evidence) | Frozen M5 policies, legal candidates, no training/replay/optimizer/Stockfish decision-path participation; checkpoint identities verified. |
| M6-04 | PASS (engineering evidence) | Eleven completed ALE-terminal M5 games with supported outcomes and all 20 attempts retained; nine incomplete attempts are outside W/D/L. Independent PM decides formal acceptance. |
| M6-05 | PASS (engineering evidence) | Frozen extended-horizon configuration and effective 500,000 ALE horizon are independently represented in the run records; v1 and v2 remain separate. |

This is an engineering evidence assessment, not M6 PM acceptance. G4 remains unapproved, PR #14 remains unmerged, and M7 has not started.

## Verification record

The focused corrective suite passed 27 tests at source revision `fbcc9826032bb390acb91b240787ba4b0d3409a0`, with zero failures or skips; see `logs/M6-F06-focused-tests-fbcc982.log` (SHA-256 `161528daf84177bfe0ef1437b5ac334d7c9a3eaec5d1cda861161d7b9abcb862`). The M5 artifact verifier passed seven manifests / 6,544,747,450 bytes at M5 revision `c9df9db36c6146a34ef301052a206fe8a3512ffc`; see `logs/M6-v2-m5-artifact-recheck-portable-20261031.log` (SHA-256 `7b81512158fb01bc39a5a6238573869ac7d4eac1a803d1844c42894036ff76a6`).

Two earlier full-suite invocations failed for setup reasons and are preserved as sanitized logs: at `8c8eab8`, an M4 artifact root was selected one directory too high, Stockfish readiness was absent from `PATH`, and context tests saw an outdated checkpoint; at `4fe4af1`, the explicit Warm checkpoint path was mistyped. No test was weakened. The final full-suite result and canonical preflight are **pending** and will be appended with exact command, timestamps, counts, exit codes, revision, and log hashes before handover.

## Independent PM handover

Review PR #14 at the final feature head and check: (1) PM6-F06 source/schema behavior against the frozen v1/v2 config semantics; (2) the immutable raw-manifest hashes and separate erratum; (3) the r3 verifier implementation and its original-root/persistent-copy records; (4) the 20-row schedule/outcome/censor table and local raw terminal/stop traces; (5) final full-suite/preflight evidence and GitHub CI coverage; (6) local-only raw artifact access and retention; and (7) M6 criteria without conflating engineering evidence with PM approval. Decide M6 acceptance and PR merge separately. G4 approval and M7 authorization remain separate governance decisions.
