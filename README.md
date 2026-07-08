# Sanitized Fixture Release Candidate

Date: 2026-07-09

This directory is a release candidate for the structured-state-interface manuscript evidence. It contains redacted replay fixtures and result summaries only. It does not contain live targets, credentials, operational exploit commands, network addresses, or target-specific reproduction procedures.

## Scope

The release candidate supports the accompanying manuscript on structured state
interfaces for defensive LLM security-agent verifier replay.

The scientific claim supported by this package is bounded:

- security-specific structured state interfaces improve defensive weak-to-strong handoff over matched-budget weak free-form memory;
- the improvement is not explained by ordinary generic JSON organization;
- the improvement is not explained by the tested simple lexical, BM25-style, or dependency-free hashed dense-vector event-retrieval memory under state pressure;
- a targeted local open-weight finalizer subset preserves the schema-favoring direction on selected schema-discordant replay cases;
- the improvement is pressure-dependent and disappears in pressure-reduced replay;
- deterministic runtime evidence curation is one auditable implementation, not a uniquely superior mechanism;
- typed protocol surface alone does not improve over information-equivalent curated prose;
- the weak-to-strong cost result is a strong paid-token proxy result, not total cost of ownership.

## Included Files

| File | Purpose |
|---|---|
| `v3e_episodes.redacted.json` | 30 redacted real-trace-derived fixtures used by V3e |
| `v3e_summary.json` | V3e arm-level and row-level outcomes |
| `v3e_stats.md` | V3e statistical report |
| `v3i_episodes.redacted.json` | V3i fixtures, same 30-fixture family |
| `v3i_summary.json` | Schema-guided weak-memory baseline result |
| `v3j_episodes.redacted.json` | V3j fixtures, same 30-fixture family |
| `v3j_summary.json` | Matched-budget free-form weak-memory baseline result |
| `v3k_episodes.redacted.json` | V3k fixtures, same 30-fixture family |
| `v3k_summary.json` | Generic structured weak-memory control result |
| `v3k_result.md` | V3k generic structured-memory result report |
| `phase9n_episodes.redacted.json` | 30 redacted fixtures used by the lexical event-retrieval memory control |
| `phase9n_summary_protocol_repaired.json` | Phase9n protocol-repaired lexical event-retrieval result |
| `phase9n_result.md` | Phase9n result report |
| `phase9n_prompt_audit.json` | Phase9n prompt/leak audit summary |
| `phase9p_episodes.redacted.json` | 30 redacted fixtures used by the BM25-style event-retrieval memory control |
| `phase9p_summary_protocol_repaired.json` | Phase9p protocol-repaired BM25-style event-retrieval result |
| `phase9p_result.md` | Phase9p result report |
| `phase9p_prompt_audit.json` | Phase9p prompt/leak audit summary |
| `phase9r_episodes.redacted.json` | 30 redacted fixtures used by the hashed dense-vector event-retrieval memory control |
| `phase9r_summary.json` | Phase9r hashed dense-vector event-retrieval result |
| `phase9r_result.md` | Phase9r result report |
| `phase9r_prompt_audit.json` | Phase9r prompt/leak audit summary |
| `phase9q_open_weight_summary.json` | Phase9q local open-weight finalizer subset sensitivity result |
| `phase9q_open_weight_result.md` | Phase9q result report |
| `phase9q_prompt_audit.json` | Phase9q prompt/leak audit summary |
| `phase9o_episodes.redacted.json` | 8 pressure-reduced low-pressure counterfactual fixtures |
| `phase9o_summary_protocol_repaired.json` | Phase9o protocol-repaired low-pressure boundary result |
| `phase9o_result.md` | Phase9o result report |
| `phase9o_prompt_audit.json` | Phase9o prompt/leak audit summary |
| `v3g_episodes.redacted.json` | 15 held-out cost fixtures |
| `v3g_glm_summary.json` | V3g GLM held-out result |
| `v3g_deepseek_summary.json` | V3g DeepSeek held-out result |
| `v3h_episodes.redacted.json` | 15 held-out strong-curated ablation fixtures |
| `v3h_glm_summary.json` | V3h GLM strong-curated result |
| `v3h_deepseek_summary.json` | V3h DeepSeek strong-curated result |
| `REPRODUCE.md` | Reproduction notes and result-to-figure mapping |
| `validate_structured_state_artifact.py` | Offline artifact validator that recomputes manuscript-level contrasts, leakage-audit status, and strong-token proxy from this release directory or ZIP |

## Fixed Selection Protocol

Fixtures were selected for state-management pressure rather than exploit novelty. A fixture must contain:

1. at least one candidate security finding;
2. at least one material-evidence relation;
3. at least one verifier relation, stale or failed-path relation, or finalization decision point;
4. no live target operation requirement in the manuscript-visible packet.

Fixtures with a single obvious answer and no competing evidence relation were excluded because they do not test handoff state management. V3g/V3h held-out fixtures were excluded from V3e before cost evaluation.

## Redaction Policy

The redaction removes operational command text, target-specific payload strings, network addresses, credentials, and direct reproduction steps. The retained information is state-level evidence: candidate identifiers, event references, evidence summaries, verifier status, stale markers, failed paths, and finalization eligibility.

## Release Caveat

This is a release candidate for external artifact review. Before final
publication, run the leakage audit and artifact validator again after download,
decide whether raw model outputs should be included or omitted, and assign
stable artifact identifiers.
