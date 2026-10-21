# M3 pre-merge final verification — 2026-10-21

## Scope and baseline

This record covers the final pre-merge audit items R-01 through R-03. The existing PR remains open and targets `initial-idea`; this record does not approve M3 or G3. Starting feature SHA: `df1efcfb55ef6df7786f65728ae76b7a825ca920`. The worktree was clean before this corrective pass. The current runtime is the pinned Python 3.12.3 environment with `python-chess` 1.11.2. The source archive and generated datasets remain ignored local artifacts.

## Findings and corrections

| Finding | Disposition | Root cause and correction | Regression evidence |
|---|---|---|---|
| R-01 | Confirmed, fixed | `verify_release()` trusted a self-consistent split manifest and its digest without recomputing the canonical group assignment. It now validates the configured seed as a positive non-boolean integer, requires the manifest seed to match the release config, and independently recomputes `assign_game_split(seed, normalized_game_sha256)` for every group before validating inheritance/counts/purge. | `test_release_verifier_recomputes_game_group_split_rule` changes a group, games, positions, purge data, statistics, output hashes, split digest, release ID, and manifest checksum consistently; the verifier rejects the deterministic-rule mismatch. `test_release_verifier_rejects_boolean_split_seed_even_with_consistent_hashes` reaches the seed type check with config, position provenance, stats, and file/release hashes rebound. Both pass in the final M3 suite. |
| R-02 | Confirmed, fixed | Position validation checked SHA-256 syntax, but did not bind sampling metadata to the release or recompute selected plies. The verifier now binds each row's sampling config digest to the release config, recomputes the documented sampling-run identity, and reconstructs the deterministic per-game/global bottom-K sample set from released game histories. Retained IDs plus purge-ledger IDs must equal that set. Selection reconstruction is bounded by the configured per-game and global caps. | `test_release_verifier_binds_sampling_fields_to_release_config` mutates valid-looking digests and rehashes the release. `test_release_verifier_reconstructs_sampled_ply_membership` changes seed/config/row identities and statistics consistently while retaining the old selected plies; the verifier rejects the set mismatch. Both pass in the final M3 suite. |
| R-03 | Confirmed, fixed with versioned compatibility | Manifest schema 1.1 called a planned reserve projection an elapsed-time “upper bound,” although publication can exceed the reserve. New teacher manifests use schema 1.2 and the explicit `command_elapsed_projection_seconds` plus estimate-only semantics. Actual post-closure elapsed time still governs budget status; an overrun cannot remain `complete`. Schema 1.1 is read as its historical projection field, not a guarantee; schema 1.0 remains supported. Row schema and identity algorithms are unchanged. | The teacher finalization test injects a 2.2-second publication delay, demonstrates that actual elapsed can exceed the projection, verifies the estimate-only metadata, and checks completion/overrun behavior. Synthetic current 1.2 and historical 1.1/1.0 manifests pass semantic verification; malformed projection metadata is rejected. |

One additional type edge was found while testing R-01: because Python treats `True == 1`, a JSON boolean config seed could otherwise compare equal to integer seed 1. The verifier now rejects boolean seeds explicitly. This is covered by the hash-consistent negative test above.

The initial red regression run reproduced acceptance of forged split assignments, arbitrary sampling hashes, and stale selected-ply membership. The corrected focused suite subsequently passed. No split, sample, candidate, config, source, or release identity algorithm was changed.

## Artifact impact and compatibility

The immutable final-closure release r6/r7 was produced at revision `40cd4e88bcaf987033a27f5f73995c5f44f21fb5`, release ID `f10a679deddf06f3e1e3c39cf58db4e21176629c26c09034a271bf278189e890`, manifest SHA-256 `be1e1f9316fac01be893774cfe09a313de193fbd1a12ab2d219ff5c041104a12`. The release verifier's current code is newer, but the release manifest correctly remains bound to its producer revision/tree. The new release checks are independent verification; they do not alter dataset generation or release identity semantics. `sampling_run_identity()` factors the existing formula into a helper without changing its domain or serialized inputs. The producer and verifier therefore remain distinguishable without relabeling old artifacts. Regeneration is not required by the artifact provenance contract.

Final source-backed verification of r6 under the corrected verifier passed at the current code worktree. It confirmed the source archive SHA-256 `ad374c8fd9fb2fe5f03c1297aa1d47cbbce5caedf6e6e2d387ee816930afdb11` (97,163,552 bytes), PGN member SHA-256 `0f88f18836be7e321aa1e0211b618e78d4e92065c126c45c95a6a55c1500a8e6` (326,476,031 bytes), CRC validation, 1,000 games, 19,268 positions, 182 quarantined games, seven listed outputs, and 39,994,522 manifest-listed output bytes. The release ID and manifest SHA match the immutable prior record.

Historical compatibility checks passed: schema 1.0 release r4, schema 1.1 corrective r4, and final r6/r7 all verify without rewriting their files or identities. Final r6/r7 were previously independently generated and their nine release files match byte-for-byte. The real Stockfish 19 `teacher-final-closure-r1` remains bound to r6/r7's release ID and was independently verified as 128/128 analyzed, 0 failed/unattempted, 377 cp and 3 mate MultiPV rows. The teacher manifest is historical schema 1.1; the 1.2 format is covered by synthetic tests. No new Stockfish search or dataset build was necessary.

The additional release-plus-teacher verification under the corrected code completed 2026-10-21 15:50:08.723000–15:54:11.473718 UTC, exit 0. It reproduced the same release ID and verified teacher run ID `58febd814bb6bdd6fa67b990a1e4906ada14c31fafa265829fb49b7d3c203272`, 128/128 analyzed positions, zero failed/unattempted positions, 377 cp and 3 mate rows, teacher results SHA-256 `9add961adc73013776d96c8b84467b0f73a8edd310c13b0f55b0cfc9c5f70d65`, and teacher manifest SHA-256 `71429e0f5993aed968454b1a94f3abba6a5c7d602ea698439495c59402b6c584`.

## Verification at the starting feature revision

The successful final M3-focused run was executed in the pinned Python environment against the corrective working tree based at `df1efcfb55ef6df7786f65728ae76b7a825ca920`: 32 tests passed, exit 0, 2026-10-21 15:42:52.415968–15:43:38.109691 UTC. The pre-M3 contract suite passed 8/8, exit 0. `compileall`, `uv lock --check`, `agent_preflight.py`, and `git diff --check` exited 0. The preflight reports expected worktree drift before commit and an independent artifact-manifest requirement.

An initial full-suite attempt in the modified worktree ran 224 tests and had two environmental/context failures: the workspace recovery assertion correctly rejected the dirty worktree, and the M0 Stockfish smoke test could not find Stockfish because `.venv/bin` was absent from `PATH`. It was not treated as a passing suite. Final full-suite and clean-clone results for the pushed PR SHA are recorded in the exact-SHA PR review comment to avoid a self-referential evidence commit; the final run places the already-installed pinned `.venv/bin` on `PATH` and tests a clean clone.

## Resource, source, and governance boundaries

All work used local CPU and the existing pinned dependency/Stockfish installation. No source archive or bulk game/position/teacher records were uploaded, added to Git, or redistributed. The curated package's own license remains unstated/unverified; the owner-authorized scope remains local internal academic use only. No model training or M4–M7 work occurred. `M3-001` remains in progress pending independent PM acceptance; G3 remains unapproved.

Before the required final checkpoint, `PROJECT_STATE.yaml` measured 4,130,517 bytes with 128 checkpoint-history entries. The one final portable checkpoint required to bind the complete correction to clean-clone recovery crosses the documented `>128` trigger and may cross 4 MiB. No history migration or truncation is part of M3 closure. The resulting size and checkpoint duration are reported in the exact-SHA PR handoff; design/test a lossless migration before future checkpoint-heavy work.

## Evidence files

- Focused test log: `logs/M3-premerge-focused-m3-df1efcf.log` (32 PASS).
- Pre-M3 test log: `logs/M3-premerge-pre-m3-df1efcf.log` (8 PASS).
- Initial modified-worktree full-suite diagnostic: `logs/M3-premerge-full-suite-df1efcf.log` (224 tests; two environment/worktree failures, described above).
- Compile, lock, preflight, and diff-check logs: `logs/M3-premerge-compile-df1efcf.log`, `logs/M3-premerge-lock-check-df1efcf.log`, `logs/M3-premerge-preflight-df1efcf.log`, `logs/M3-premerge-diff-check-df1efcf.log`.
- Source-backed r6 verification: `logs/M3-premerge-source-release-r6-df1efcf.log`.
- Release-linked teacher verification: `logs/M3-premerge-teacher-r6-df1efcf.log`.
- Final exact-SHA clean-clone test and preflight evidence: PR #3 review comment, recorded after push.
