# Structured-State Artifact Validation

Validated at: `2026-07-09T03:27:38`

Status: `PASS`

## Checks

| Check | Result |
|---|---|
| `required_files_present` | `True` |
| `strict_leakage_pass` | `True` |
| `schema_beats_matched_provider_episode_12_0` | `True` |
| `schema_beats_matched_fixture_7_0` | `True` |
| `schema_beats_generic_22_0` | `True` |
| `schema_beats_lexical_10_0` | `True` |
| `schema_beats_bm25_10_0` | `True` |
| `schema_beats_hashed_dense_10_0` | `True` |
| `bm25_beats_generic_13_1` | `True` |
| `hashed_dense_beats_generic_14_2` | `True` |
| `low_pressure_schema_ties_raw_and_lexical` | `True` |
| `typed_surface_null_0_0` | `True` |
| `weak_and_strong_curated_both_30_30` | `True` |
| `phase9q_open_weight_subset_schema_beats_matched_6_0` | `True` |

## Recomputed Contrasts

| Contrast | Comparable | A better | B better | Ties | One-sided p |
|---|---:|---:|---:|---:|---:|
| `schema_vs_matched_provider_episode` | 60 | 12 | 0 | 48 | 0.000244140625 |
| `schema_vs_matched_fixture_level` | 30 | 7 | 0 | 23 | 0.0078125 |
| `schema_vs_generic_provider_episode` | 60 | 22 | 0 | 38 | 2.384185791e-07 |
| `schema_vs_lexical_provider_episode` | 60 | 10 | 0 | 50 | 0.0009765625 |
| `schema_vs_bm25_provider_episode` | 60 | 10 | 0 | 50 | 0.0009765625 |
| `schema_vs_hashed_dense_provider_episode` | 60 | 10 | 0 | 50 | 0.0009765625 |
| `lexical_vs_generic_provider_episode` | 60 | 13 | 1 | 46 | 0.0009155273438 |
| `bm25_vs_generic_provider_episode` | 60 | 13 | 1 | 46 | 0.0009155273438 |
| `hashed_dense_vs_generic_provider_episode` | 60 | 14 | 2 | 44 | 0.002090454102 |
| `curated_vs_schema_provider_episode` | 60 | 6 | 8 | 46 | 0.7880249023 |
| `typed_surface_vs_curated_prose` | 60 | 0 | 0 | 60 | 1 |
| `low_pressure_schema_vs_matched` | 16 | 1 | 0 | 15 | 0.5 |
| `low_pressure_schema_vs_lexical` | 16 | 0 | 0 | 16 | 1 |
| `low_pressure_schema_vs_raw` | 16 | 0 | 0 | 16 | 1 |
| `phase9q_open_weight_schema_vs_matched` | 10 | 6 | 0 | 4 | 0.015625 |

## Strong Paid-Token Proxy

| Arm | Correct/Total | Strong paid tokens | Parse failures |
|---|---:|---:|---:|
| Weak/local curated handoff | 30/30 | 24391 | 0 |
| Strong-curated handoff | 30/30 | 146855 | 0 |

Observed strong-token ratio: `6.020868`.

## Leakage Audit

Strict status: `PASS`; strict zero: `True`.

Broad status: `PASS_WITH_CONTEXTUAL_WARNINGS`; blocking broad patterns zero: `True`.

## Interpretation

This validation is an artifact reproducibility check. It confirms that the release candidate contains enough sanitized summary data to recompute the manuscript-level paired contrasts and leakage-audit status without external model calls. It does not replace public Zenodo/OSF/GitHub deposition.
