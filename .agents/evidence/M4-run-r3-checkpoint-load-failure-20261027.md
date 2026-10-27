# M4 run r3 safe checkpoint reload failure — 2026-10-27

**Run:** `m4-behavior-20261027-r3`
**Source revision:** `7988af28f768c203c9cc7e2794785c99df588645`
**Run interval:** `2026-10-27T15:29:38.330190Z` to `2026-10-27T15:51:10.084361Z`
**Command exit:** 1
**Disposition:** failed run preserved; no M4-03 checkpoint acceptance, test evaluation, or simulator evaluation is claimed.

## Completed work before failure

- The revised M4-02 sanity gate passed at update 140. Its separate result and protocol evidence remain recorded in [the M4-02 pass report](M4-02-revised-sanity-pass-20261027.md).
- All three configured training seeds completed under the per-seed caps. They stopped by validation patience:
  - `20261022`: best epoch 10, validation NLL `2.425930260628157`, 369.8343 seconds.
  - `20261023`: best epoch 9, validation NLL `2.445335060126488`, 344.1740 seconds.
  - `20261024`: best epoch 11, validation NLL `2.4127401237590953`, 398.4582 seconds.
- Validation selected seed `20261024`, epoch 11. The held-out test partition was not inspected.
- Run process time was 1,291.7544 seconds; recorded aggregate use including prior release verifications, prior attempts, and the diagnostic was 1,934.9984 seconds. Peak RSS was 625,577,984 bytes.

## Failure and repair

During the freeze/reload stage, safe `torch.load(..., weights_only=True)` rejected the serialized `torch.torch_version.TorchVersion` object in runtime metadata. The failure is specifically caused by `_environment()` recording `torch.__version__` without conversion to a built-in `str`. The checkpoint loader correctly kept safe loading enabled. The source fix converts the version to a plain string, and the checkpoint test now exercises a round trip with the complete runtime metadata.

The original r3 run manifest records `failed_or_budget_stopped`, stage `freeze_validation_selected_checkpoint`, exception `UnpicklingError`, and exit code 1. Its run manifest SHA-256 is `d979a54ffd18c7caa7562487dbf21f07404978972db2d7a10085ae671f86f6d7`. Per-seed metric JSON and validation-best checkpoints remain in the approved external artifact directory. The selected validation-best checkpoint SHA-256 is `8b57aefda7a9608af95b16cd20cf6528a4b4d6593fcf3bf99b4beeb215add6ac`; its checkpoint integrity manifest remains intact. The frozen copy is byte-identical but safe reload also failed. No r3 artifact was deleted or relabeled as accepted.

The code correction is in progress under the same M4 scope. The next run must charge the full r3 execution and per-seed usage to the existing cumulative budgets, repeat the complete protocol with the corrected serialization, and proceed to test evaluation only after the checkpoint reload succeeds.

Backlog result record: M4 run `m4-behavior-20261027-r3` completed the three bounded training seeds and validation selection, then failed safe checkpoint reload because runtime metadata contained `torch.torch_version.TorchVersion`; exit 1. M4-02 remains PASS. M4-03 and M4-04 remain incomplete.

M4 run m4-behavior-20261027-r3 completed the three bounded training seeds and validation selection, then failed safe checkpoint reload because runtime metadata contained torch.torch_version.TorchVersion; exit 1. M4-02 remains PASS. M4-03 and M4-04 remain incomplete.
