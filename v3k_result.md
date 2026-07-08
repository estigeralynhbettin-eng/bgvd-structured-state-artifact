# Phase9i-V3k Generic Structured Weak-Memory Baseline

Date: 2026-07-08

## Purpose

This control tests whether generic JSON structure is sufficient, or whether the security-specific state interface fields are needed.

## Aggregate

| Provider::Arm | Correct | Total | Accuracy | State update failures | Wrong candidate | Parse failures | Stale misuse |
|---|---:|---:|---:|---:|---:|---:|---:|
| `deepseek::generic_structured_memory` | 16 | 30 | 0.533 | 0 | 1 | 0 | 3 |
| `deepseek::matched_freeform_weak_memory` | 20 | 30 | 0.667 | 0 | 3 | 1 | 1 |
| `deepseek::raw_running_log` | 22 | 30 | 0.733 | 0 | 2 | 3 | 0 |
| `deepseek::schema_guided_weak_memory` | 27 | 30 | 0.900 | 0 | 3 | 0 | 0 |
| `deepseek::untyped_curated_state` | 26 | 30 | 0.867 | 0 | 4 | 0 | 0 |
| `deepseek::untyped_weak_qwen35_9b` | 22 | 30 | 0.733 | 0 | 4 | 0 | 0 |
| `glm::generic_structured_memory` | 16 | 30 | 0.533 | 0 | 1 | 0 | 2 |
| `glm::matched_freeform_weak_memory` | 22 | 30 | 0.733 | 0 | 1 | 0 | 0 |
| `glm::raw_running_log` | 25 | 30 | 0.833 | 0 | 4 | 0 | 0 |
| `glm::schema_guided_weak_memory` | 27 | 30 | 0.900 | 0 | 3 | 0 | 0 |
| `glm::untyped_curated_state` | 26 | 30 | 0.867 | 0 | 4 | 0 | 0 |
| `glm::untyped_weak_qwen35_9b` | 22 | 30 | 0.733 | 0 | 1 | 0 | 0 |

## Paired Contrasts

| Provider | Arm A | Arm B | A better | B better | Ties | p(A>B) |
|---|---|---|---:|---:|---:|---:|
| pooled | `schema_guided_weak_memory` | `generic_structured_memory` | 22 | 0 | 38 | 2.38419e-07 |
| pooled | `generic_structured_memory` | `matched_freeform_weak_memory` | 0 | 10 | 50 | 1 |
| pooled | `schema_guided_weak_memory` | `matched_freeform_weak_memory` | 12 | 0 | 48 | 0.000244141 |
| pooled | `untyped_curated_state` | `generic_structured_memory` | 20 | 0 | 40 | 9.53674e-07 |
| pooled | `generic_structured_memory` | `untyped_weak_qwen35_9b` | 0 | 12 | 48 | 1 |
| glm | `schema_guided_weak_memory` | `generic_structured_memory` | 11 | 0 | 19 | 0.000488281 |
| glm | `generic_structured_memory` | `matched_freeform_weak_memory` | 0 | 6 | 24 | 1 |
| deepseek | `schema_guided_weak_memory` | `generic_structured_memory` | 11 | 0 | 19 | 0.000488281 |
| deepseek | `generic_structured_memory` | `matched_freeform_weak_memory` | 0 | 4 | 26 | 1 |

## Interpretation Guard

If schema-guided security memory beats this arm, the paper gains evidence that the useful mechanism is security-specific state semantics rather than JSON structure alone. If this arm ties schema-guided memory, the paper must narrow novelty to structured handoff and weaken the security-specific-field claim.
