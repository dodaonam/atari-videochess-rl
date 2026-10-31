# M6-001 Stage 3 v2 Corrective Authorization

**Recorded:** 2026-10-31T01:49:17Z
**Authority:** direct project-owner instruction in the current corrective continuation
**Task:** M6-001 remains in progress; this is a separately versioned experiment amendment, not retroactive v1 authorization.
**Base:** `initial-idea` `e6d444e475e447e9f37951f16585bf496f804c9d`
**Feature branch at recovery:** `feature/m6-ale-integration` `61c624b803a4481509e84fed767f103d8b521340`

The user-message transport does not provide a separate signed timestamp in repository records; the timestamp above is when this direct authorization was entered into the canonical evidence package.

The project owner directly authorized the fixed 20-attempt paired M5 extended-horizon local CPU v2 campaign and its resource limits. M6 remains in progress; no PM acceptance or G4 approval is claimed.

## Authorization record

The owner directly authorizes the bounded M6 corrective continuation and Stage 3 v2 local CPU Atari campaign. The owner reports that the independent PM identified PM6-F01 through PM6-F05. This record preserves that attribution; it does not represent a new PM decision or claim PM acceptance of M6.

The authorization permits corrective code, tests, documentation, private M4/M5 artifact read-only verification, local ALE execution of the fixed v2 schedule, local evidence retention, commits/pushes to the existing feature branch, and updating PR #14. It does not authorize M5 training/fine-tuning, changing accepted checkpoints/results, Stockfish, cloud execution, upload/redistribution, more than the fixed schedule, protocol changes after v2 outcomes are observed, PR merge, self-approval, M6 acceptance, or G4 approval.

## Immutable v1 boundary

The v1 campaign remains identified by run ID `m6-stage3-ad3998200e31-c5ff389dc4fe`, source commit `ad3998200e31e77b292ffc1138d02354f188bf5f`, and config SHA-256 `05aedeb30efb8b6b97667c44f9d606b58d4da8ae20800d4ef143e629420cebac`. Its schedule, traces, manifests, accepted checkpoint bytes, outcome classifications, and hashes remain unchanged. V2 is a follow-on extended-horizon re-evaluation on the same paired seeds; v1 and v2 results must not be pooled as one unchanged protocol or treated as independent held-out runs.

## Frozen v2 scope

- Protocol: `M6 Stage 3 v2 — Extended-Horizon Frozen M5 Evaluation`.
- Configuration: `configs/m6/m6-stage3-v2.json`, schema `videochess-m6-stage3-config/2.0`.
- Policies: only the preselected Warm and Scratch `post_rl`, seed `20261104`, accepted M5 checkpoints and sidecars pinned in that config; no model selection by Atari outcome.
- Schedule: exactly 20 reset attempts, ten per policy, paired ALE seeds `20261130`–`20261139`; Warm first on even seeds and Scratch first on odd seeds. No seed replacement, selective omission, or unfavorable-result retry.
- Runtime: local CPU; one serialized ALE process; `ALE/VideoChess-v5`, RGB, White, mode 4, difficulty 0, frameskip 4, sticky probability 0.25. The explicitly extended emulator horizon is `max_num_frames_per_episode=500000`, distinct from the registered 108000 default. The runner allows 432000 post-reset action frames; reset counter offset is recorded separately.
- Per attempt: at most 432000 post-reset action frames, 1800 seconds, 200 player moves, and 40000 opponent-response action frames.
- Campaign: at most 43200 gameplay seconds and 8589934592 new v2 artifact bytes; at least 12884901888 bytes free before official start; 128 MiB artifact-finalization reserve; maximum process RSS 6442450944 bytes; one global process-start retry only before the first ALE action.
- Evidence: create a deterministic run ID and immutable run manifest from committed source commit/tree, v2 config SHA, and schedule SHA before the first outcome. Keep raw traces/RGB local, outside Git, and verify them from manifests/hash chains.

## Entry gate and safety conditions

No official v2 reset may occur until the final corrective implementation/configuration/tests are committed on the feature branch; the complete suite and preflight pass; both selected checkpoints, sidecars, and the full M5 root manifest match their accepted hashes; runtime versions match `uv.lock`; the ROM SHA matches the pinned identity; the installed ALE instance reports mode/difficulty/RGB/action profile and `ale.getInt("max_num_frames_per_episode") == 500000`; the v1 artifact tree remains verified and unchanged; disk/RSS/resource gates pass; and the deterministic schedule/config/source manifest is frozen.

Stop safely on a checkpoint/schema/root-manifest mismatch, ROM mismatch, unsupported or unhonored horizon, schedule/config/source drift, trace-write failure, an uncertain controller action, RSS/disk/artifact/wall ceiling, or any need to alter the protocol after results become visible. An attempt with a reset is never replayed or replaced. Incomplete and terminal-unknown attempts are never draws; ALE reward/flags, not the shadow board, own game outcomes.

**Governance:** M6 remains authorized and in progress pending independent PM review. M6-001 is not accepted. G3 remains approved; G4 remains unapproved. PR #14 remains open and unmerged.
