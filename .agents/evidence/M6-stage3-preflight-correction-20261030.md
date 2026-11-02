# M6 Stage 3 preflight correction — M4 policy identity

**Disposition:** pre-game configuration correction; no Stage 3 attempt or ALE action occurred.

The first Stage 3 CLI invocation at `c0e77e318224e722703275548407e458cb2e7712` exited before creating an M6 Stage 3 run directory. `run_stage3` rejected `m4-behavior-only-seed-20261024` because the configured checkpoint digest differed from the accepted M4 identity. No ALE reset, gameplay action, or evaluation result was produced. The sanitized observed output is retained at [`M6-stage3-preflight-c0e77e3.log`](logs/M6-stage3-preflight-c0e77e3.log).

The M4 artifact bytes were present and matched the canonical M4 record: checkpoint SHA-256 `724ac730f3c5f2d01b48b26eb7670a3c764978a3dd4d6702b3057a99ab1a90a4`, checkpoint-sidecar SHA-256 `cc0af4694e45fc23acb740c652dd9a62e1bcaf7851815d179693d09539f0f606`, and root-manifest SHA-256 `f00fde1c59325105e0ffd45bb45eb269dfa303416010c9a0b6c6be47bd9a9921`. These identities match the [M4 acceptance report](M4-final-acceptance-20261027.md), [model design](../../docs/03-technical/MODEL_DESIGN.md), and the already-accepted M6 policy protocol.

The config contained a transcription error (`724ac730f3c5f2c01b48...`) where the accepted digest is `724ac730f3c5f2d01b48...`. I corrected that one field to the manifest-verified accepted digest and added `test_stage3_roster_pins_exact_accepted_checkpoint_identities`, which checks all five policy identities and their pinned sidecars, including M4. The prior config SHA-256 was `0d9495ca044f9abeef02d66af01e5d283e4c22b3271ea34f78e49b26b3c317ad`; corrected config SHA-256 is `05aedeb30efb8b6b97667c44f9d606b58d4da8ae20800d4ef143e629420cebac`.

This correction does not change the policy, checkpoint bytes, roster, evaluation settings, or any observed outcome. It happened before the first Stage 3 run manifest/reset/result. The full regression suite must pass on the corrected code/config before the campaign is launched.
