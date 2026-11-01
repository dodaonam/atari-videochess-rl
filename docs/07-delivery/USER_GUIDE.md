# User Guide — Atari VideoChess RL

This guide covers repository-only checks and read-only verification of authorized local artifacts. The Project Owner has recorded existing accepted research results as final; no further training or evaluation campaign is authorized in this project scope. This guide does not authorize artifact redistribution or publication. No affirmative permission to distribute restricted artifacts is established; the earlier blanket-owner-prohibition attribution is unverified. See the [research-scope decision](../../.agents/evidence/PROJECT-OWNER-final-research-scope-decision-20261101.md), [G5-F02 erratum](../../.agents/evidence/G5-F02-provenance-erratum-20261101.md), and [release disposition](RELEASE_DISPOSITION.md).

## Prerequisites and artifact access

- Python 3.12 or newer, as required by pyproject.toml.
- Runtime packages pinned by uv.lock: ALE-Py 0.11, Gymnasium, python-chess, NumPy, and PyTorch. Consult pyproject.toml and uv.lock for exact constraints and resolved versions.
- A project environment that can import the required package set for M4/M5/M6/M7 tools. This repository-only preflight uses the Python standard library.
- Private artifact access is separate from cloning. M3 source/release data, M4/M5 checkpoints, M6/M7 raw run records, and the exact VideoChess ROM are not distributed in this repository. Obtain authorized local artifact paths from the Project Owner.
- For M7, the accepted ROM identity is SHA-256 d44f2a115393b0a6cbcd5398d62369e652f3670a9ee585883d183e740edad0f7. The campaign's accepted profile is ALE/VideoChess-v5, White, mode 4, difficulty 0, RGB, frameskip 4, sticky probability .25, and an extended horizon. A system-installed ROM is not assumed to match.
- Historical campaign reproduction requires the frozen configuration, exact private artifacts, compatible runtime, authorized compute, and explicit authorization. The historical local CPU limits are not a standing grant for another campaign.

The project records Python 3.12.3, PyTorch 2.14.1+cpu, Gymnasium 1.4.0, ALE-Py 0.11.2, python-chess 1.11.2, and NumPy 2.5.4 in the accepted M6/M7 environment records. These versions describe that evidence; they are not a promise that a different installation has been verified.

## Repository setup

Clone the repository and select an accepted revision:

    git clone https://github.com/dodaonam/atari-videochess-rl.git
    cd atari-videochess-rl
    git checkout d7332b91128d3daf919421db2e71a9f2ee4b48ec
    git status --short --branch

The integration branch may advance. For current work, inspect its history and canonical state rather than forcing this historical revision.

The repository requires Python >=3.12 and has a uv.lock. If the environment administrator provides uv, the locked sync command is:

    uv sync --locked

This creates/updates a project environment and installs dependencies. It was not run for this task because uv was unavailable on the executor host; no package was installed. An existing approved environment can instead run repository commands by setting PYTHONPATH to the checkout root and using that environment's Python interpreter.

## Level A — Repository-only verification

These checks need code and committed reports, not private raw data.

### Canonical preflight

    python3 scripts/agent_preflight.py

- **Purpose**: validate canonical state, backlog/dependencies, checkpoint pointers, acceptance references, links, and tracked-file consistency.
- **Inputs**: repository checkout; Python standard library.
- **Expected result**: “Agent context preflight: PASS”; warnings may remain for ignored artifact directories requiring separate manifest checks.
- **Side effects**: prints diagnostics; does not run model training or an ALE campaign.
- **Failure**: inspect every error and warning, then follow AGENTS.md and canonical governance files. A preflight warning is not an approval.

### Read the accepted reports

Open the M7 analysis report, its machine-readable JSON, the four delivery documents, and the acceptance records linked in them. The analysis report is a committed summary; raw M7 ledgers and RGB traces remain private. A report link does not prove that private bytes exist in a clone.

## Level B — Private artifact verification

These are read-only integrity checks. They require paths supplied by the Project Owner. Set the following task-specific shell variables to authorized local directories; do not put private absolute paths into documentation, logs, or issue comments.

    M4_RUN_DIR=/path/to/authorized/m4-behavior-20261027-r4
    M5_ARTIFACT_ROOT=/path/to/authorized/m5
    M6_V1_RUN_DIR=/path/to/authorized/m6/v1-run
    M6_V2_RUN_DIR=/path/to/authorized/m6/v2-run
    M7_RUN_ROOT=/path/to/authorized/m7-option-b-20261031-v1-8387b289432f

### Verify the accepted M4 artifact

    PYTHONPATH=. python -m videochess_rl.model.cli verify-artifacts "$M4_RUN_DIR"

- **Purpose**: verify M4 run and checkpoint hashes.
- **Inputs**: an accepted M4 artifact directory with its run/root manifests and checkpoint sidecar.
- **Expected result**: JSON reports verified files and the selected checkpoint SHA-256.
- **Side effects**: reads files only.
- **Failure**: stop if a checkpoint, sidecar, or manifest identity differs; do not repair or regenerate accepted evidence.

### Verify M5 manifests

    PYTHONPATH=. python scripts/m5_artifact_manifests.py --root "$M5_ARTIFACT_ROOT" --verify

- **Purpose**: verify the accepted M5 root and per-run manifests.
- **Expected result**: status verified and the expected run-manifest count.
- **Side effects**: read-only when --verify is supplied. Do not omit --verify; without it, the script creates manifests.
- **Failure**: stop on a missing or mismatched manifest; never recreate a frozen manifest.

### Verify an M6/M7 root artifact manifest

    PYTHONPATH=. python scripts/verify_m7_artifact_manifest.py --root "$M7_RUN_ROOT" --expected-manifest-sha256 25a8b6bcfbf1d948bed886a0a4964cf48210fb1be12809c72bf122157b8d05e4

- **Purpose**: verify every listed file and the expected root-manifest identity.
- **Expected result**: JSON with status verified, file count, byte count, and read_only true.
- **Side effects**: reads and hashes files; does not rewrite the manifest.
- **Failure**: any mismatch, unlisted file, unsafe path, missing file, or symbolic-link root returns failure; stop and preserve evidence.

### Verify the complete frozen M7 input roster

    PYTHONPATH=. python scripts/verify_m7_inputs.py --config configs/m7/m7-option-b-1.0.0.json --m4-root "$M4_RUN_DIR" --m5-root "$M5_ARTIFACT_ROOT" --m6-v1-root "$M6_V1_RUN_DIR" --m6-v2-root "$M6_V2_RUN_DIR"

- **Purpose**: reverify the nine-policy mapping and accepted M4–M6 inputs against the frozen M7 config.
- **Inputs**: all named private artifact roots and the committed config.
- **Expected result**: a raw-derived verification summary.
- **Side effects**: reads checkpoints/manifests and can use CPU/memory while parsing records; does not launch ALE or change the accepted evidence.
- **Failure**: stop on missing inputs or identity mismatch. Do not substitute a checkpoint or repair a manifest.

These verification tools and argument names were checked with --help. On this executor, package-dependent help initially failed when run with the system Python because chess/NumPy were absent; the same help checks passed with the existing project interpreter. See the retained failure history in M7-004 evidence.

## Level C — Historical experiment reproduction

The analysis command can reconstruct M4–M7 summaries from private source records and writes generated outputs to the required output directory:

    PYTHONPATH=. python scripts/analyze_m7_campaign.py --config configs/m7/m7-option-b-1.0.0.json --m7-run-dir "$M7_RUN_ROOT" --m4-root "$M4_RUN_DIR" --m5-root "$M5_ARTIFACT_ROOT" --m6-v1-root "$M6_V1_RUN_DIR" --m6-v2-root "$M6_V2_RUN_DIR" --output-dir "$NEW_ANALYSIS_OUTPUT_DIR"

Use a new empty output directory; never point it at accepted M7 evidence. This command does not run games, but it reads private raw records and writes derived output. Secure the output under the same privacy controls as the source artifacts.

The official campaign runner is scripts/run_m7_campaign.py. It can execute or resume ALE attempts. Do not run it as setup or routine verification. Any new campaign requires separate Project Owner authorization and a separately approved protocol. The M5 CLI evaluation also runs a frozen simulator schedule and is not a routine check.

## Troubleshooting

| Symptom | Meaning and action |
|---|---|
| ROM missing or hash differs | Stop. Ask the Project Owner for the authorized ROM path/identity; do not substitute a package ROM. |
| Checkpoint missing | The clone does not include private model artifacts. Obtain authorized local access; do not fetch from an unapproved source. |
| Checksum/manifest mismatch | Stop dependent verification. Preserve the mismatch log; never overwrite, regenerate, or select another accepted artifact. |
| Manifest absent | Confirm the correct owner-supplied root. Do not run a manifest-creation mode against frozen evidence. |
| Import error for chess, NumPy, ALE, or torch | Use the project environment matching pyproject.toml/uv.lock. Do not install packages into a shared/system interpreter without authorization. |
| Preflight failure or warning | Read the diagnostic and canonical governance record. A clean preflight does not authorize a milestone or release. |
| M7 verification missing a run | Confirm M7_RUN_ROOT points to the exact accepted run. Do not resume or rerun to fill missing artifacts. |
| Controller/ALE runtime behavior differs | Stop. Runtime or ROM changes can alter the protocol; preserve diagnostics and request a new approved evaluation decision before gameplay. |
| Historical run differs from current code | Compare the recorded run and analysis source revisions. Do not treat the current branch as the historical executable. |

## Privacy

Do not commit or externally upload ROMs, checkpoints, raw RGB, raw traces, datasets, credentials, or private artifact paths without explicit scope-specific permission and applicable rights/privacy review. Do not bypass access controls. No affirmative authorization to distribute restricted artifacts is established; this is not an owner prohibition. M7-005's earlier owner-decision attribution is superseded by [G5-F02](../../.agents/evidence/G5-F02-provenance-erratum-20261101.md). G5 is approved with limitations following the [final Independent PM decision](../../.agents/evidence/G5-PM-final-decision-20261101.md); M7-04 acceptance remains intact. See the [current release inventory](RELEASE_DISPOSITION.md) and [historical G5 PM decision](../../.agents/evidence/G5-PM-acceptance-20261101.md).
