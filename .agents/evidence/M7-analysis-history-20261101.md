# M7 Analysis Reconstruction History

All three bundles below were independently derived from the same immutable raw M4/M5/M6/M7 inputs. They are retained to show the analysis corrections in sequence. **Use `M7-analysis-final-r2-20261101` as the authoritative report and machine-readable result for review.** Raw campaign artifacts remain local-only.

| Bundle | Source commit | Manifest SHA-256 | Status |
|---|---|---|---|
| [`M7-analysis-20261101`](M7-analysis-20261101/M7_ANALYSIS.md) | `58a604f2bd4bcd9113a047ee709a80ee97bd02a6` | `78f4f08e8aa0ec877f942a181d36653d6e25bf76b791e9c12308390d23315d73` | Initial raw reconstruction. It reported the M4 policy-input stop as incomplete but did not yet explain the shadow fivefold state or distinguish the finalized artifact-parent byte count. |
| [`M7-analysis-final-20261101`](M7-analysis-final-20261101/M7_ANALYSIS.md) | `3f2f1f3cfae4154dd0fc0ff00c59901606590e5f` | `8283272f303cae44e1f6f0d7e1e1628f30a218a1fc15e5c1d2b84438229a9508` | Corrected the shadow-terminal diagnostic and final artifact-parent accounting. Its per-policy outcome table did not yet show started attempts. |
| [`M7-analysis-final-r2-20261101`](M7-analysis-final-r2-20261101/M7_ANALYSIS.md) | `fe2cc4cc5e477841ffbc9368235eb9c5675f2f74` | `af084e1cd99a6541c19cad2a1dfa163129a3cb873c393ec3669711e5d7b4ffa1` | **Authoritative.** Adds explicit per-policy started counts and the tested report renderer. Raw hashes, outcomes, and summary reconciliation are unchanged. |

The analysis command logs and metadata are retained alongside each relevant run. The initial and intermediate output bundles are not presented as the final report; the supersession reasons are explicit above.
