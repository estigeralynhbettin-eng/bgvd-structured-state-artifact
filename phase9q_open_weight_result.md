# Phase9q Open-Weight Finalizer Subset Sensitivity Result

Date: 2026-07-09

## Purpose

Phase9q is a different-kind sensitivity check requested after the Phase9p GLM review. It does not rerun another same-family GLM/DeepSeek finalizer experiment. Instead, it reuses already saved redacted handoff states and asks a local open-weight finalizer, `qwen3.5-27b:q4km`, to classify a targeted subset of the main schema-guided-vs-matched-free-form contrast.

This is not a new target-runtime experiment. It does not start any vulnerability target, Docker service, or exploit workflow. It only reads redacted replay evidence and final handoff states already produced by V3i/V3j.

## Source Artifacts

- Script: `<BGVD_PROJECT_ROOT>\scripts\run_phase9q_claude_finalizer_subset.py`
- Full run directory: `<BGVD_PROJECT_ROOT>\outputs\phase9q_claude_finalizer_subset\phase9q_claude_finalizer_subset_20260708_150250`
- Summary: `<BGVD_PROJECT_ROOT>\outputs\phase9q_claude_finalizer_subset\phase9q_claude_finalizer_subset_20260708_150250\summary.json`
- Attempt status: `<BGVD_PROJECT_ROOT>\outputs\phase9q_claude_finalizer_subset\phase9q_claude_finalizer_subset_20260708_150250\attempt_status.json`
- Prompt audit: `<BGVD_PROJECT_ROOT>\outputs\phase9q_claude_finalizer_subset\phase9q_claude_finalizer_subset_20260708_150250\prompt_audit.json`
- Claude account-failure smoke: `<BGVD_PROJECT_ROOT>\outputs\phase9q_claude_finalizer_subset\phase9q_claude_finalizer_subset_20260708_150233`

## Protocol

- Backend: native Ollama `/api/chat`
- Model: `qwen3.5-27b:q4km`
- Reasoning: disabled with `think=false`
- Context: `num_ctx=8192`
- Max output: `768`
- Temperature: `0`
- Subset size: 10 episodes, two arms per episode, 20 finalizer prompts
- Selection: schema-fixture wins first from the V3i/V3j contrast, followed by tie controls
- Prompt audit: 20 prompts, min 2099 chars, p50 2819 chars, max 3926 chars, 0 leak findings
- Provider/schema status: 20/20 rows with `provider_failure_type=ok`

The selected subset is intentionally enriched for schema-discordant cases. It is therefore a sensitivity probe for whether a third finalizer preserves the same direction on high-value discordants. It is not a replacement for the full 30-fixture GLM/DeepSeek result.

## Result

| Arm | Correct | Total | Accuracy |
|---|---:|---:|---:|
| Schema-guided weak memory | 10 | 10 | 1.000 |
| Matched free-form weak memory | 4 | 10 | 0.400 |

Paired contrast:

- Schema-guided weak memory vs matched free-form weak memory: 6 schema-only wins, 0 free-form-only wins, 4 ties.
- One-sided exact sign-test for schema superiority: `p=0.015625`.

By selected relation:

- Schema-fixture-win subset: schema 7/7, matched free-form 1/7.
- Fixture-tie controls: schema 3/3, matched free-form 3/3.

Observed matched-free-form failure modes include stale/superseded support reuse in one row, wrong-candidate finalization in one row, three continue decisions where finalization was expected, and missing material or verifier references in several rows. The schema-guided arm had no wrong-candidate, stale-reuse, missing-material, missing-verifier, or continue-error rows in this subset.

## Claude Attempt Classification

The Claude Opus 4.8 smoke did not return a scientific judgment. The API returned:

`This organization has been disabled.`

The script now classifies this as `provider_account_disabled`, not as a safety refusal, balance issue, model judgment, or experiment result.

## Interpretation

Phase9q strengthens the finalizer-specificity story. The main RQ1 result was already observed with GLM 5.2 and DeepSeek v4-pro. This targeted local open-weight finalizer subset shows the same direction on selected schema-discordant replay cases: schema-guided weak memory remains correct, while matched free-form memory often fails to preserve the candidate/evidence/verifier lifecycle.

The result should be integrated as a sensitivity check, not as a primary endpoint. Because the subset is deliberately enriched for schema wins, the defensible manuscript wording is:

> A targeted open-weight finalizer subset preserved the schema-favoring direction on selected schema-discordant replay cases, with 6 schema-only wins, 0 free-form-only wins, and 4 ties. This supports finalizer-sensitivity robustness but does not replace an independent public benchmark replication.

## Environment Notes

- GPU: NVIDIA RTX A4500 Laptop GPU.
- The model loaded with approximately 14.6 GB GPU memory usage during generation.
- After the run, `ollama stop qwen3.5-27b:q4km` was executed and GPU memory returned to idle state.

## Decision

Use Phase9q as supplemental finalizer-sensitivity evidence. Do not use it to broaden the claim beyond access-control-style verifier replay, and do not treat it as a public artifact substitute. The public DOI/anonymous artifact URL remains the main SCI-readiness blocker.
