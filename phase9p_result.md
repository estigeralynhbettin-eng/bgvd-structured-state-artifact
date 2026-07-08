# Phase9p BM25-Style Event-Retrieval Memory Baseline

Date: 2026-07-08

## Purpose

This control tests whether a stronger deterministic BM25-style event-retrieval memory can replace the security-specific structured state interface.

## Aggregate

| Provider::Arm | Correct | Total | Accuracy | State update failures | Wrong candidate | Parse failures | Stale misuse |
|---|---:|---:|---:|---:|---:|---:|---:|
| `deepseek::bm25_retrieval_memory` | 22 | 30 | 0.733 | 0 | 6 | 0 | 0 |
| `deepseek::generic_structured_memory` | 16 | 30 | 0.533 | 0 | 1 | 0 | 3 |
| `deepseek::matched_freeform_weak_memory` | 20 | 30 | 0.667 | 0 | 3 | 1 | 1 |
| `deepseek::rag_retrieval_memory` | 23 | 30 | 0.767 | 0 | 7 | 0 | 0 |
| `deepseek::raw_running_log` | 22 | 30 | 0.733 | 0 | 2 | 3 | 0 |
| `deepseek::schema_guided_weak_memory` | 27 | 30 | 0.900 | 0 | 3 | 0 | 0 |
| `deepseek::untyped_curated_state` | 26 | 30 | 0.867 | 0 | 4 | 0 | 0 |
| `deepseek::untyped_weak_qwen35_9b` | 22 | 30 | 0.733 | 0 | 4 | 0 | 0 |
| `glm::bm25_retrieval_memory` | 22 | 30 | 0.733 | 0 | 6 | 0 | 0 |
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
| pooled | `schema_guided_weak_memory` | `bm25_retrieval_memory` | 10 | 0 | 50 | 0.000976562 |
| pooled | `bm25_retrieval_memory` | `rag_retrieval_memory` | 2 | 2 | 56 | 0.6875 |
| pooled | `bm25_retrieval_memory` | `matched_freeform_weak_memory` | 4 | 2 | 54 | 0.34375 |
| pooled | `bm25_retrieval_memory` | `generic_structured_memory` | 13 | 1 | 46 | 0.000915527 |
| pooled | `untyped_curated_state` | `bm25_retrieval_memory` | 8 | 0 | 52 | 0.00390625 |
| pooled | `bm25_retrieval_memory` | `raw_running_log` | 2 | 5 | 53 | 0.9375 |
| deepseek | `schema_guided_weak_memory` | `bm25_retrieval_memory` | 5 | 0 | 25 | 0.03125 |
| deepseek | `bm25_retrieval_memory` | `rag_retrieval_memory` | 0 | 1 | 29 | 1 |
| deepseek | `bm25_retrieval_memory` | `matched_freeform_weak_memory` | 2 | 0 | 28 | 0.25 |
| deepseek | `untyped_curated_state` | `bm25_retrieval_memory` | 4 | 0 | 26 | 0.0625 |
| glm | `schema_guided_weak_memory` | `bm25_retrieval_memory` | 5 | 0 | 25 | 0.03125 |
| glm | `bm25_retrieval_memory` | `rag_retrieval_memory` | 2 | 1 | 27 | 0.5 |
| glm | `bm25_retrieval_memory` | `matched_freeform_weak_memory` | 2 | 2 | 26 | 0.6875 |
| glm | `untyped_curated_state` | `bm25_retrieval_memory` | 4 | 0 | 26 | 0.0625 |

## Interpretation Guard

This is still a deterministic event-retrieval baseline, not a dense embedding, reranker, or full external memory framework. If the structured-state interface beats this arm, the manuscript can say that a BM25-style retrieval memory did not explain away the lifecycle-interface gain. If BM25 ties or beats the interface, the claim must be narrowed toward retrieval-based memory rather than lifecycle-state semantics.
