# Pre-M4 Readiness — 2026-10-22

**Status:** Draft while the exact-branch final test suite, checkpointed clean-clone recovery, documentation-link audit, and pull-request checks are pending. This mission-local record will own readiness checks R01–R08; those IDs do not extend the formal acceptance-criteria inventory.

## Verified baseline

The latest verified integration baseline is `initial-idea` at `aba04d7b30fa614e2e7e74789dd610a162dd2cf0`, parented by merged M3 integration commit `2867bd58f29331a7429c649fe9e82fe620157a4d`. PR #3 is merged. M3 acceptance, current artifacts, M4 authorization, and G3 status are recorded in the sections below as verification completes.

## R01–R08 readiness matrix

| Check | Status | Evidence |
|---|---|---|
| R01 — Baseline and governance integrity | Pending final clean-clone verification | See baseline above and canonical state/backlog. |
| R02 — M3 data readiness | Pending final artifact-availability review | See accepted M3 closure records and current artifact inventory. |
| R03 — M2/M3/M4 interface compatibility | Pending recorded test logs | See `MODEL_DESIGN.md` and `test_pre_m4_contracts.py`. |
| R04 — M4 model design readiness | Pending final design review | See proposed `MODEL_DESIGN.md` and ADR-0003. |
| R05 — M5 compatibility readiness | Pending final interface review | See `MODEL_DESIGN.md` and M5 comparison protocol. |
| R06 — Training/evaluation protocol readiness | Pending final protocol review | See `TRAINING_PROTOCOL.md`. |
| R07 — Checkpoint-history and recovery risk | Pending final test log and clean-clone recovery | See RSK-010 in `RISK_REGISTER.md` and the checkpoint section of `REPRODUCIBILITY.md`. |
| R08 — Repository verification and handoff | Pending full suite, final preflight, diff review, and PR checks | Complete after branch verification. |
