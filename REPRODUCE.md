# Reproduce the SoftwareX evidence

Reproduction guide for **v1.2.0**, 2026-09-17. Use the
[versioned Release page](https://github.com/estigeralynhbettin-eng/bgvd-structured-state-artifact/releases/tag/v1.2.0)
for the revised three-platform reviewer kits. The unchanged v1.1.1 release
remains the historical submitted baseline.

## Start here

Reviewers who do not want to install Python should use the platform-specific
reviewer kit linked from the v1.2.0 Release page. Extract the entire
ZIP, launch `00_DOUBLE_CLICK_TO_VERIFY_...`, and read the result page and its
linked logs. The kit includes an isolated runtime and dependencies. Its
`REVIEWER_KIT_BUILD.json` records the complete expected test count. Missing,
skipped or partial test runs must not produce a PASS.

The following commands are the optional **source/developer** route, requiring
Python 3.10–3.12 and installation of test dependencies. They are not required
for the no-install reviewer route.

```bash
python -m pip install -e ".[dev]"
python -m unittest discover -s tests -v
python score_released_rows.py --artifact . --out-dir scoring_output
python score_cross_family.py --artifact . --output cross_family_output.json
python score_token_accounting.py --artifact . --out-dir token_output
python validate_structured_state_artifact.py --artifact . --out-dir artifact_validation_output
```

The test log must report a nonzero count followed by an unqualified `OK`.
The scorer must recompute verdicts from released decisions and fixture oracles,
not assume the stored `correct` labels are true. The validator must require
complete comparison populations. Consult each generated report for its actual
status; historical PASS files in the repository are not a substitute for a new
execution.

## Replay the public software example

```bash
python -m bgvd_state replay --events examples/discovery_runtime_case/events.json --state-out state.json --handoff-out handoff.json
python -m bgvd_state summary --state state.json
python -m bgvd_state gate --state state.json --candidate CASE-C06
```

Expected: 23 events, 6 candidate lifecycles, 5 rejected candidates and 5 retained
failed paths; no candidate is eligible for finalization. The CASE-C06 gate
returns `current_verifier_not_positive` and exit status 2. This is the intended
negative gate outcome, not a program crash. The earlier technical observation
and the later scope decision remain available for audit.

The original local third-party review had 22 records. The public de-identified case
adds the subsequent scope decision as its 23rd event. The two counts are not
interchangeable; see `validation/runtime/authorized_review_use_manifest.json`.

## SoftwareX result map

The current machine-readable field paths are listed in
[`R1_RESULT_MAP.md`](R1_RESULT_MAP.md). Historical CSV entries remain labeled
as baseline provenance and should not be mistaken for revised-version tests.

| Paper item | Unit and source | Check |
|---|---|---|
| Section 2 runtime contract | `src/bgvd_state`, `schemas`, `docs/integration.md` | Unit tests, legacy-input normalization, invalid-event no-mutation tests |
| Section 3 applied case | 23 public events, 6 candidates; original 22-record scope documented separately | Replay and gate commands above |
| Section 3 engineering profile | `validation/runtime/runtime_benchmark.json`, including all 20 historical runs | Six fixed candidates, four event sizes, five repeats; v1.1.1 historical timing, not new-version throughput |
| Table 5 high pressure | 30 continuation fixtures, each evaluated under two providers; `v3j_summary.json` and `v3e_episodes.redacted.json` | Independent scorer, fixture-level paired comparison; retain protocol-failure sensitivity separately |
| Table 5 low pressure | 16 provider–episode pairs; `phase9o_summary_protocol_repaired.json`, `phase9o_episodes.redacted.json` | Independent scorer; raw, lexical and matched-freeform contrasts distinguished |
| Table 5 information-equivalent prose | 60 provider–episode pairs; `v3e_summary.json` and its episodes | Independent scorer; typed protocol versus curated prose |
| Section 4 token observation | 30 provider–fixture runs per route; 144 projected call records in `token_accounting/calls.json` | `score_token_accounting.py`: independently sum 130 recorded-usage records; see `token_accounting/README.md` for the definition and failed-call accounting |
| Cross-family boundary | 12 tasks × 2 providers per arm, `cross_family/source_audit_evidence.json` | `score_cross_family.py`: published lexical/anchor acceptance rules over preserved response fields; original failures, targeted retries and handoff fallback are retained in v1.2.0 |

The standalone scorer's report distinguishes output/protocol failures from
valid model answers. Raw historical labels and records are preserved even
where a recomputed verdict or alternative failure policy differs.

High pressure is a **fixture-level** comparison: count correct outputs across
the same two providers within each fixture, then compare those counts between
arms. The original 30 fixtures give 7/0/23 (wins/losses/ties), including one
matched-finalizer protocol failure. Removing that entire fixture from both arms
gives the post-audit sensitivity 6/0/23 across 29 fixtures. At the provider–episode
level, remove only the failed pair to obtain 11/0/48 over 59 pairs. The two
provider outputs are not independent fixture replications.

Cross-family scoring is different: it checks task-specific source anchors and
lexical response conditions, not the continuation oracle or actual exploit
success. Schema versus matched gives 10/24 versus 12/24 accepted (2/4/18).
Extended schema versus the reused matched control gives 12/24 versus 12/24
(4/4/16), after two targeted final-response protocol repairs. One shared
intermediate handoff used raw-text fallback; excluding that task's two provider
pairs symmetrically gives 10/22 versus 10/22 (4/4/14). See
[`cross_family/README.md`](cross_family/README.md) for the full protocol and
[`token_accounting/README.md`](token_accounting/README.md) for accounting limits.

The combined artifact validator runs all three independent reconstructions;
missing new datasets or scorers cannot silently fall back to the old result.

## Historical retry protocols

The repaired archives preserve selected replacement outputs from failed calls.
They do not represent a uniform output-budget protocol across every attempt.
The limits below are generation settings, not observed or billed token counts.
The six low-pressure repairs reused the saved prompts and were triggered by
transport failures, not by a valid answer's correctness.

| Archive / setting | Initial output-token limit | Retry limit | Recorded repair scope and analysis policy |
|---|---:|---:|---|
| `phase9o_summary_protocol_repaired.json` / Table 5 reduced pressure | 2048 | 8192 | Six transport-failed calls: matched free-form 2, schema-guided 1, generic structured 1, lexical retrieval 1, raw log 1. Selected replacements enter the historical repaired comparison; identities and original failure categories are in `protocol_repair.retried_rows`. |
| `cross_family/source_audit_evidence.json` / extended schema | 4096 | 8192 | DeepSeek WP-H-001 exhausted the original budget; WP-H-011 had a connection reset. Both used the saved prompts. The two original failures and selected retries are retained; the matched control reuses original runs. |
| `phase9n_summary_protocol_repaired.json` / auxiliary historical retrieval study | 2048 | 8192 | The archive's `protocol_repair` documents allowed failure categories, but lacks the per-row retry list used by Phase9o. Do not infer a retry count from this field or treat these records as uniformly budget-matched. |
| `phase9p_summary_protocol_repaired.json` / auxiliary historical BM25 study | 2048 | 8192 | Seven retries: four transport, one provider/transport and two schema failures, recorded in `protocol_repair.retried_rows`. This auxiliary study is not the Table 5 high-pressure schema/matched contrast. |

Post-audit sensitivity removes the same provider-episode pair from both arms
if either arm contains a selected retry. In reduced pressure, schema-guided
versus matched then gives 1/0/12 over 13 pairs; versus raw and lexical it gives
0/0/14 over 14 pairs each. For extended cross-family versus matched, removing
both retry pairs gives 4/3/15 over 22 pairs; additionally removing the two
raw-handoff-fallback pairs gives 4/3/13 over 20 pairs. These descriptive checks
do not establish superiority and do not replace the historical main counts.
They were performed after audit, not prespecified before the experiments.

The existing production scorers retain their historical scoring rules. The
retry-exclusion check is separately reproducible with:

```bash
python protocol_sensitivity.py --artifact . --output protocol_sensitivity.json
```

This offline script identifies pairs from the recorded repair metadata and
scores preserved answers against the same oracles. It does not call a model
or change the source archives. Successful independent rescoring of all archived
rows does not imply that all historical studies share one experimental protocol.

## Historical materials and limits

Root-level `v3*` and `phase9*` data are historical sanitized experimental
records. The older nested `BGVD_structured_state_interface_*20260709.zip`
is a legacy fixture bundle, not the current Python runtime or reviewer kit.
Its old RQ numbers, figure names and 24-page manuscript instructions do not
describe the SoftwareX submission. It is retained as provenance only.

The SoftwareX manuscript source is maintained separately from the runtime
repository. This repository does not promise that running an old `main.tex`
command will reproduce the submitted SoftwareX PDF.

All commands above operate offline after the optional developer dependencies
are installed. They do not call models, contact live targets, start containers,
or establish the substantive truth of supplied security observations.
