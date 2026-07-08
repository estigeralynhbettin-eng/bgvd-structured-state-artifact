# Phase9o Low-Pressure Boundary Check

Date: 2026-07-08

## Purpose

This experiment constructs 8 low-pressure counterfactual replay fixtures from already redacted authorized traces. It removes candidate collision, stale evidence, failed paths, duplicate worker outputs, lost writeback, and long multi-round pressure. The goal is to test whether the schema-guided advantage shrinks when the state-management pressure targeted by the main study is absent.

## Fixture Pressure

| Band | Fixtures |
|---|---:|
| low | 8 |

## Aggregate

| Provider::Arm | Correct | Total | Accuracy | State update failures | Parse failures | Wrong candidate |
|---|---:|---:|---:|---:|---:|---:|
| `deepseek::generic_structured_memory` | 8 | 8 | 1.000 | 0 | 0 | 0 |
| `deepseek::matched_freeform_weak_memory` | 8 | 8 | 1.000 | 0 | 0 | 0 |
| `deepseek::rag_retrieval_memory` | 8 | 8 | 1.000 | 0 | 0 | 0 |
| `deepseek::raw_running_log` | 8 | 8 | 1.000 | 0 | 0 | 0 |
| `deepseek::schema_guided_weak_memory` | 8 | 8 | 1.000 | 0 | 0 | 0 |
| `glm::generic_structured_memory` | 4 | 8 | 0.500 | 0 | 0 | 4 |
| `glm::matched_freeform_weak_memory` | 7 | 8 | 0.875 | 0 | 0 | 0 |
| `glm::rag_retrieval_memory` | 8 | 8 | 1.000 | 0 | 0 | 0 |
| `glm::raw_running_log` | 8 | 8 | 1.000 | 0 | 0 | 0 |
| `glm::schema_guided_weak_memory` | 8 | 8 | 1.000 | 0 | 0 | 0 |

## Paired Contrasts

| Arm A | Arm B | A better | B better | Ties | p(A>B) |
|---|---|---:|---:|---:|---:|
| `schema_guided_weak_memory` | `matched_freeform_weak_memory` | 1 | 0 | 15 | 0.5 |
| `schema_guided_weak_memory` | `generic_structured_memory` | 4 | 0 | 12 | 0.0625 |
| `schema_guided_weak_memory` | `rag_retrieval_memory` | 0 | 0 | 16 | 1 |
| `schema_guided_weak_memory` | `raw_running_log` | 0 | 0 | 16 | 1 |

## Interpretation Guard

If all arms saturate, the result is not a failure. It supports the bounded mechanism claim: the security-specific interface is useful under state pressure, while low-pressure replay does not need the interface. If schema-guided memory still wins, the selection-circularity concern becomes weaker but the paper must explain why even simple states benefit.

This is a pressure-reduced counterfactual derived from the same authorized trace source, not an independent public benchmark replication.
