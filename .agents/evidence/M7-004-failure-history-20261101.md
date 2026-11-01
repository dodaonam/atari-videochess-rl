# M7-004 Verification Failure and Remediation History

This record preserves documented failures encountered while preparing delivery evidence. Failures remain visible; successful reruns do not erase them. No training, simulator campaign, ALE campaign, or artifact mutation occurred.

## 1. Incorrect M3 evidence-manifest path

- **Observed:** an initial read-only command attempted to read .agents/evidence/M3-release-manifest-r6-20261021.json; that repository path does not exist.
- **Evidence:** [initial verification log](logs/M7-004-private-input-verification-20261101.log), exit code 1.
- **Impact:** the command stopped before it hashed or changed any payload; it did not establish an M3 artifact mismatch.
- **Remediation:** use the owner-local accepted M3 release directory and the repository's accepted videochess.data.cli verify path.
- **Rerun:** [private input verification rerun](logs/M7-004-private-input-verification-rerun1-20261101.log), exit code 0. The accepted release ID and manifest matched, seven outputs were verified, and no artifact was written.

## 2. Dependency-bearing CLI help under the system Python

- **Observed:** scripts/verify_m7_inputs.py --help, scripts/analyze_m7_campaign.py --help, and scripts/run_m7_campaign.py --help were first invoked with system python3, which lacked chess and/or numpy; all three exited 1 before argument parsing.
- **Evidence:** [sanitized host-interpreter failure capture](logs/M7-004-cli-host-python-failures-20261101.log).
- **Impact:** only CLI help discovery failed; no evaluation runner or analysis function was entered and no experiment artifact was read or changed by those invocations.
- **Remediation:** repeat help checks with the already-installed project interpreter, PYTHONPATH=. and bytecode writes disabled. No package was installed.
- **Rerun:** all three commands exited 0; the supported arguments are documented in USER_GUIDE.md and were inspected against the actual argparse output.

## 3. Initial artifact-verifier import-path failure

- **Observed:** the first invocation of the new verify_m7_artifact_manifest.py --help did not place the checkout root on sys.path, so the package import failed before CLI parsing.
- **Provenance:** historical session observation; no standalone timestamped log was retained. Treat the initial failure detail as historical_unverified, not as a formal test record.
- **Impact:** no artifact operation occurred.
- **Remediation:** the script now inserts its repository root before importing the project verifier module.
- **Rerun:** unit tests cover valid manifests, expected-hash mismatch, modified/unlisted files, unsafe manifest paths, and symlink roots. The final --help check exited 0; the M7 raw root re-verification is recorded in [the read-only manifest log](logs/M7-004-M7-manifest-verification-20261101.log).

## 4. Delivery-document regression assertion

- **Observed:** the first focused M7 delivery-document suite found that MODEL_CARD.md did not repeat the frozen M7 evaluation run ID, even though the ID was present in the report and acceptance evidence. One of 12 test methods failed; the other 11 passed.
- **Evidence status:** the exact failure was returned in the executor tool output, but no separate timestamped log was retained. Mark the initial failure provenance historical_unverified; do not count it as a pass.
- **Remediation:** added the M7 run ID, protocol, and configuration hash to the model card.
- **Rerun:** the focused suite is rerun after this correction and its retained log is attached to the M7-004 acceptance record.

## 5. Initial full-suite run on a dirty worktree

- **Observed:** the full command ran 503 tests and exited 1 with two failures and three skips.
- **Evidence:** [sanitized full-suite log](logs/M7-004-full-suite-20261101.log), started 2026-11-01T04:15:20.234712Z, source HEAD d7332b91128d3daf919421db2e71a9f2ee4b48ec.
- **Failure A:** the context-recovery test requires a clean Git snapshot; this feature worktree intentionally contains the M7-004 changes. This is a workspace precondition mismatch, not a code assertion failure. Verify in a clean clone.
- **Failure B:** the M0 smoke test could not find a Stockfish executable on PATH. A read-only search of the expected system binary directories found none. No package was installed and Stockfish was not run. This check remains environment-blocked unless an existing authorized executable is supplied.
- **Remediation:** run the suite in a clean clone, then run all available tests while explicitly excluding only the Stockfish readiness test if the executable remains unavailable. Preserve the original full-suite failure record and report the exclusion.

## 6. Clean-clone full-suite result and isolated environment check

- **Observed:** a clean clone at 2e34299c3994a8e3658c7a570a29fda02dcdd71d passed canonical preflight; the full suite ran 505 tests with one failure and three skips. The only failure was Stockfish UCI readiness because no executable was available. The dirty-worktree Git snapshot failure did not recur.
- **Evidence:** [clean-clone full-suite log](logs/M7-004-clean-clone-full-suite-20261101.log), exit code 1.
- **Remediation/verification:** reran all discovered tests in the same clean clone while excluding exactly the unavailable Stockfish readiness test. Result: 504 executed, three existing skips, zero failures/errors. The excluded test ID and complete filter source are in [the filtered-suite log](logs/M7-004-clean-clone-suite-excluding-stockfish-20261101.log).
- **Boundary:** this is an explicitly qualified suite result, not a claim that all repository tests passed. No Stockfish binary was installed or invoked.

After the canonical M7-004 completion state was committed at source revision a80dbae1e9185d0e5545803710b0793f3405aa84, another clean clone passed preflight with only ARTIFACT_MANIFEST_REQUIRED and passed the 24 focused documentation/manifest/governance tests. See the final clean-clone preflight and focused-test logs. These results include the final done/pending gate pointers.

After the evidence records were linked at source revision e23e8f3cc64ec2797697bc4116f215907b3d9c31, repository preflight and the 24-test focused suite passed again; the only preflight warning remains the expected artifact-manifest requirement.

## 7. Verification boundary

The incorrect-path and interpreter failures are diagnostic failures, not frozen experiment results. The successful checks used accepted identities, did not repair or regenerate historical artifacts, and did not add campaign attempts. M7-004 focused/full-suite and clean-clone outcomes are recorded separately in the M7-004 acceptance evidence.
