# Phase9r Hashed Dense-Vector Event-Retrieval Memory Baseline

Date: 2026-07-09

## Purpose

This control tests whether a dependency-free dense-vector event-retrieval memory can replace the security-specific structured state interface.

## Aggregate

| Provider::Arm | Correct | Total | Accuracy | State update failures | Wrong candidate | Parse failures | Stale misuse |
|---|---:|---:|---:|---:|---:|---:|---:|
| `deepseek::bm25_retrieval_memory` | 22 | 30 | 0.733 | 0 | 6 | 0 | 0 |
| `deepseek::generic_structured_memory` | 16 | 30 | 0.533 | 0 | 1 | 0 | 3 |
| `deepseek::hashed_dense_retrieval_memory` | 22 | 30 | 0.733 | 0 | 4 | 0 | 0 |
| `deepseek::matched_freeform_weak_memory` | 20 | 30 | 0.667 | 0 | 3 | 1 | 1 |
| `deepseek::rag_retrieval_memory` | 23 | 30 | 0.767 | 0 | 7 | 0 | 0 |
| `deepseek::raw_running_log` | 22 | 30 | 0.733 | 0 | 2 | 3 | 0 |
| `deepseek::schema_guided_weak_memory` | 27 | 30 | 0.900 | 0 | 3 | 0 | 0 |
| `deepseek::untyped_curated_state` | 26 | 30 | 0.867 | 0 | 4 | 0 | 0 |
| `deepseek::untyped_weak_qwen35_9b` | 22 | 30 | 0.733 | 0 | 4 | 0 | 0 |
| `glm::bm25_retrieval_memory` | 22 | 30 | 0.733 | 0 | 6 | 0 | 0 |
| `glm::generic_structured_memory` | 16 | 30 | 0.533 | 0 | 1 | 0 | 2 |
| `glm::hashed_dense_retrieval_memory` | 22 | 30 | 0.733 | 0 | 7 | 0 | 0 |
| `glm::matched_freeform_weak_memory` | 22 | 30 | 0.733 | 0 | 1 | 0 | 0 |
| `glm::rag_retrieval_memory` | 21 | 30 | 0.700 | 0 | 7 | 0 | 0 |
| `glm::raw_running_log` | 25 | 30 | 0.833 | 0 | 4 | 0 | 0 |
| `glm::schema_guided_weak_memory` | 27 | 30 | 0.900 | 0 | 3 | 0 | 0 |
| `glm::untyped_curated_state` | 26 | 30 | 0.867 | 0 | 4 | 0 | 0 |
| `glm::untyped_weak_qwen35_9b` | 22 | 30 | 0.733 | 0 | 1 | 0 | 0 |

## Paired Contrasts

| Provider | Arm A | Arm B | A better | B better | Ties | p(A>B) |
|---|---|---|---:|---:|---:|---:|
| pooled | `schema_guided_weak_memory` | `hashed_dense_retrieval_memory` | 10 | 0 | 50 | 0.000976562 |
| pooled | `hashed_dense_retrieval_memory` | `bm25_retrieval_memory` | 1 | 1 | 58 | 0.75 |
| pooled | `hashed_dense_retrieval_memory` | `rag_retrieval_memory` | 2 | 2 | 56 | 0.6875 |
| pooled | `hashed_dense_retrieval_memory` | `matched_freeform_weak_memory` | 5 | 3 | 52 | 0.363281 |
| pooled | `hashed_dense_retrieval_memory` | `generic_structured_memory` | 14 | 2 | 44 | 0.00209045 |
| pooled | `untyped_curated_state` | `hashed_dense_retrieval_memory` | 8 | 0 | 52 | 0.00390625 |
| pooled | `hashed_dense_retrieval_memory` | `raw_running_log` | 2 | 5 | 53 | 0.9375 |
| glm | `schema_guided_weak_memory` | `hashed_dense_retrieval_memory` | 5 | 0 | 25 | 0.03125 |
| glm | `hashed_dense_retrieval_memory` | `bm25_retrieval_memory` | 0 | 0 | 30 | 1 |
| glm | `hashed_dense_retrieval_memory` | `rag_retrieval_memory` | 2 | 1 | 27 | 0.5 |
| glm | `hashed_dense_retrieval_memory` | `matched_freeform_weak_memory` | 2 | 2 | 26 | 0.6875 |
| glm | `untyped_curated_state` | `hashed_dense_retrieval_memory` | 4 | 0 | 26 | 0.0625 |
| deepseek | `schema_guided_weak_memory` | `hashed_dense_retrieval_memory` | 5 | 0 | 25 | 0.03125 |
| deepseek | `hashed_dense_retrieval_memory` | `bm25_retrieval_memory` | 1 | 1 | 28 | 0.75 |
| deepseek | `hashed_dense_retrieval_memory` | `rag_retrieval_memory` | 0 | 1 | 29 | 1 |
| deepseek | `hashed_dense_retrieval_memory` | `matched_freeform_weak_memory` | 3 | 1 | 26 | 0.3125 |
| deepseek | `untyped_curated_state` | `hashed_dense_retrieval_memory` | 4 | 0 | 26 | 0.0625 |

## Interpretation Guard

This is a deterministic hashed dense-vector retrieval baseline, not a neural embedding model, reranker, MemGPT-style system, or full external memory framework. If the structured-state interface beats this arm, the manuscript can say that a vector-style event retrieval control did not explain away the lifecycle-interface gain. If this arm ties or beats the interface, the claim must narrow toward retrieval-based memory rather than security lifecycle-state semantics.
