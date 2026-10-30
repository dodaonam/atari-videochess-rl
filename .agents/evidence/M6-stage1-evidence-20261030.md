# M6 Stage 1 — Genuine ALE Policy Integration

**Verified run:** `m6-stage1-development-debug-5bb88459a1d3`
**Source commit:** `5bb88459a1d38ad62dcbce6b4805541f8c2b3acf`
**Attempt:** `m5-warm-seed-20261104-post-rl-seed-20261129-slot-000-attempt-0000`
**Profile:** development/debug; `ALE/VideoChess-v5`, White, mode 4, difficulty 0, RGB, frameskip 1, sticky-action probability 0.0.
**Run frozen at:** `2026-10-30T15:36:30.625188Z`
**Attempt interval:** `2026-10-30T15:36:30.688049Z` to `2026-10-30T15:36:36.361399Z`

## Result

The accepted frozen M5 Warm-start policy `m5-warm-seed-20261104-post-rl` made one decision from stable RGB at ALE frame 4. Its checkpoint was `0b2405017a8e1d539851f0cd278883d3fd23936fb5c2f7962c813590a6fd1767` and sidecar `80d8689e4b349576c5708bb4dce3451e5a8c64d81470cd6f4273a4746844b682`. The decision input carried the RGB-confirmed standard start, empty full history, White to move, and all 20 sorted legal UCI candidates.

The policy selected **`g1f3`**. The controller completed the calibrated action sequence, RGB independently verified the player move, and RGB later verified the Atari reply **`c7c5`**. The trace retained the reset, decision boundary, controller phases, screenshots, and final verified FEN `rnbqkbnr/pp1ppppp/8/2p5/8/5N2/PPPPPPPP/RNBQKB1R w KQkq - 0 2`.

- Attempted player moves: 1
- RGB-verified player moves: 1
- Verified Atari replies: 1
- Desynchronizations: 0
- Move success: 1.000; Wilson 95% interval [0.20654931437723745, 1.0]
- Policy inference latency: 0.005271 s
- Full decision/controller latency: 5.276783 s
- Episode wall time: 5.67 s; process peak RSS 620105728 bytes
- ALE frames/environment steps: 1110/1106
- Stop: `RUNNER_MAX_PLAYER_MOVES` after the authorized one-player-move diagnostic limit; this is not a completed game or Atari outcome.

## Provenance and retained local evidence

- ROM SHA-256: `d44f2a115393b0a6cbcd5398d62369e652f3670a9ee585883d183e740edad0f7`
- M5 root manifest SHA-256: `a201a254671ad59ae1fecb402abf994d5bf523097f1c3010b5c7fa237ae6dd4c`
- Dependency lock SHA-256: `60b55b57bd89c08274b470ea5c525f60037e893194e5815feeeaccf98b23df1a`
- Source bundle SHA-256: `8728a7071d13d2c235cb3f62fd9615526dd438793cb9d059b41914e9fd801e4d`
- Run manifest SHA-256: `aa866c027f7f6ab60c99c013375f5dd0c823ad41d3b6f966c9e10cf7e160b21d`
- Attempt trace SHA-256: `8955a4ce292c4fd2525232f373f61e97c6a8e88fc480c954f454a9f5695dc752`; trace event hash chain verified.
- Attempt artifact manifest SHA-256: `4c37b396dfcbc78bf79e43edf0ba1bcc92add73871a1763123e3642796c06e52`; reset RGB and eight PNG evidence frames are listed in the local manifest.
- Run event ledger SHA-256: `4f21e79800376dffd711ddd63ac9e898c1f60573a0c9294dced6dcbf51e984d1`; 2217 hash-chained events verified.
- Run artifact manifest SHA-256: `d80f7d40191f4a347a607fcfefa451da004057b9e66bdbbda25292b02dceaeda`.
- Private gameplay artifacts remain under ignored local directory `artifacts/m6/m6-stage1-development-debug-5bb88459a1d3` and are not uploaded or committed.

## Scope note

This verifies the policy-to-controller path for one real ALE decision and one real Atari reply under debug settings. It does not pass full-game evaluation or default-v5 reliability criteria. The preceding attempt under source `bb0792d` reset ALE but stopped before any controller action because a relative artifact root broke path conversion; its reset was recovered and sealed as an incomplete pre-action attempt. No action was repeated.
