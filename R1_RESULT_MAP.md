# v1.2.0 result map

This map describes the revised SoftwareX manuscript. The existing
`RESULT_TRACEABILITY.csv` also indexes historical analyses and version-specific
v1.1.1 engineering reports; its historical numbers are not replacements for
the revised failure policies below. The current release is v1.2.0.

Run `python validate_structured_state_artifact.py --artifact . --out-dir results`.
The combined report is `results/artifact_validation_report.json`.

`status: PASS` means that the software checks and independent result
reconstructions completed successfully. `scientific_review_status:
REVIEW_REQUIRED` is separate: the recorded protocol failures, descriptive
cross-family results, and incomplete historical token accounting require
scientific interpretation. It is not a software-execution failure and must
not be changed to PASS merely because the program runs successfully.

| Manuscript claim | Data and independent scorer | Field in combined report | Interpretation |
|---|---|---|---|
| Table 5, high-pressure sensitivity | `v3j_summary.json`, `v3e_episodes.redacted.json`; `score_released_rows.py` | `row_scoring.table5.semantic_valid_only.high_pressure` | 29 fixtures, 6/0/23, p=.015625; exclude affected fixture symmetrically; post-audit sensitivity |
| Historical high-pressure count | Same | `row_scoring.table5.historical_replication.high_pressure` | 30 fixtures, 7/0/23; reproduces old failure-as-incorrect convention, not primary semantic evidence |
| Provider-pair sensitivity | Same | `row_scoring.table5.semantic_valid_only.high_pressure_provider_sensitivity` | 59 valid provider–episode pairs, 11/0/48; not 59 independent fixtures |
| Table 5, reduced pressure | `phase9o_*` records; `score_released_rows.py` | `row_scoring.table5.semantic_valid_only.low_pressure` | 16 pairs, 1/0/15 against matched free-form; raw/lexical contrasts separately under `contrasts` |
| Table 5, information-equivalent prose | `v3e_*` records; `score_released_rows.py` | `row_scoring.table5.semantic_valid_only.information_equivalent` | 60 pairs, 0/0/60; no formal equivalence claim |
| R1-CROSS-FAMILY | `cross_family/source_audit_evidence.json`; `score_cross_family.py` | `cross_family.comparisons.final_response_eligible` | 24 pairs per contrast: 2/4/18 and 4/4/16; task-specific lexical/source-anchor acceptance |
| Cross-family fallback sensitivity | Same | `cross_family.comparisons.end_to_end_eligible.extended_vs_matched` | 22 pairs, both10/22, 4/4/14; two provider observations of failed handoff excluded symmetrically |
| R1-TOKEN-ACCOUNTING | `token_accounting/calls.json`; `score_token_accounting.py` | `token_accounting.arms` | 30 runs per route; 24,391 / 146,855 recorded tokens; 14 failed calls with no recorded usage across 8 runs |

The scoring and accounting programs use response fields, explicit oracles and
per-call usage rather than trusting the old outcome or aggregate labels. They
do not rerun models, verify original raw-text parsing, certify a vulnerability,
or establish complete billed costs. Source hashes establish content identity;
they do not make unreleased raw archives independently visible.

Runtime evidence is separate: `unittest discover -s tests -v`, event replay,
negative gate checks and checkpoint recovery. The historical memory experiments
did not execute the Python lifecycle engine as an experimental treatment.
