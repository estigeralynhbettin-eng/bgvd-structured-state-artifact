# Phase9n RAG-Style Retrieval Memory Baseline

Date: 2026-07-08

## Purpose

This control tests whether a retrieval-augmented untyped memory framework can match the security-specific structured state interface.

## Aggregate

| Provider::Arm | Correct | Total | Accuracy | State update failures | Wrong candidate | Parse failures | Stale misuse |
|---|---:|---:|---:|---:|---:|---:|---:|
| `deepseek::generic_structured_memory` | 16 | 30 | 0.533 | 0 | 1 | 0 | 3 |
| `deepseek::matched_freeform_weak_memory` | 20 | 30 | 0.667 | 0 | 3 | 1 | 1 |
| `deepseek::rag_retrieval_memory` | 23 | 30 | 0.767 | 0 | 7 | 0 | 0 |
| `deepseek::raw_running_log` | 22 | 30 | 0.733 | 0 | 2 | 3 | 0 |
| `deepseek::schema_guided_weak_memory` | 27 | 30 | 0.900 | 0 | 3 | 0 | 0 |
| `deepseek::untyped_curated_state` | 26 | 30 | 0.867 | 0 | 4 | 0 | 0 |
| `deepseek::untyped_weak_qwen35_9b` | 22 | 30 | 0.733 | 0 | 4 | 0 | 0 |
| `glm::generic_structured_memory` | 16 | 30 | 0.533 | 0 | 1 | 0 | 2 |
| `glm::matched_freeform_weak_memory` | 22 | 30 | 0.733 | 0 | 1 | 0 | 0 |
| `glm::rag_retrieval_memory` | 21 | 30 | 0.700 | 0 | 7 | 0 | 0 |
| `glm::raw_running_log` | 25 | 30 | 0.833 | 0 | 4 | 0 | 0 |
| `glm::schema_guided_weak_memory` | 27 | 30 | 0.900 | 0 | 3 | 0 | 0 |
| `glm::untyped_curated_state` | 26 | 30 | 0.867 | 0 | 4 | 0 | 0 |
| `glm::untyped_weak_qwen35_9b` | 22 | 30 | 0.733 | 0 | 1 | 0 | 0 |

## Paired Contrasts

| Provider | Arm A | Arm B | A better | B better | Ties | p(A>B) |
|---|---|---|---:|---:|---:|---:|
| pooled | `schema_guided_weak_memory` | `rag_retrieval_memory` | 10 | 0 | 50 | 0.000976562 |
| pooled | `rag_retrieval_memory` | `matched_freeform_weak_memory` | 5 | 3 | 52 | 0.363281 |
| pooled | `rag_retrieval_memory` | `generic_structured_memory` | 13 | 1 | 46 | 0.000915527 |
| pooled | `untyped_curated_state` | `rag_retrieval_memory` | 8 | 0 | 52 | 0.00390625 |
| pooled | `rag_retrieval_memory` | `raw_running_log` | 2 | 5 | 53 | 0.9375 |
| pooled | `schema_guided_weak_memory` | `matched_freeform_weak_memory` | 12 | 0 | 48 | 0.000244141 |
| deepseek | `schema_guided_weak_memory` | `rag_retrieval_memory` | 4 | 0 | 26 | 0.0625 |
| deepseek | `rag_retrieval_memory` | `matched_freeform_weak_memory` | 3 | 0 | 27 | 0.125 |
| deepseek | `untyped_curated_state` | `rag_retrieval_memory` | 3 | 0 | 27 | 0.125 |
| glm | `schema_guided_weak_memory` | `rag_retrieval_memory` | 6 | 0 | 24 | 0.015625 |
| glm | `rag_retrieval_memory` | `matched_freeform_weak_memory` | 2 | 3 | 25 | 0.8125 |
| glm | `untyped_curated_state` | `rag_retrieval_memory` | 5 | 0 | 25 | 0.03125 |

## Interpretation Guard

This is a RAG-style baseline, not a new exploit or live-target run. If schema-guided memory beats this arm, novelty against memory-framework baselines is strengthened. If RAG ties or beats schema-guided memory, the manuscript must narrow the claim and treat retrieval memory as a competitive baseline.
