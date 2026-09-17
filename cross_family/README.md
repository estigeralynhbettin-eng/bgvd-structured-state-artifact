# Cross-family source-audit boundary evidence

This directory contains the previously collected Phase9l/Phase9m source-audit
boundary results in a form that can be rescored offline, released with
BGVD-State v1.2.0. It is not a new model
experiment, a vulnerability benchmark rerun, or a live-target test.

From the artifact root, run:

```text
python score_cross_family.py --output cross_family/cross_family_rescore.json
python -m unittest discover -s tests -p "test_cross_family*.py" -v
```

The scorer uses only the Python standard library. No API key, network access,
model, target source bundle or extra dependency is needed. The complete reviewer
kit can run it with its private Python interpreter.

## Design and outcome meaning

The archive has 12 source-only tasks from the frozen Phase9g-H task pool and two
strong-model providers (GLM 5.2 and DeepSeek v4-pro), giving 24 provider-task
pairs per arm. The local weak model was Qwen3.5:9b. The task families are
authorization, privilege, file upload, file deletion and SQL injection.
There was one run per task/provider/arm. Phase9m adds one extended-schema arm;
its comparison baselines are the original Phase9l rows, not new replications.

The historical `validate_final_h` rule accepts a parsed final response only if
all required fields are present, `finding_present` is the boolean `true`, and
the task's fixed source-anchor/word conditions are satisfied. It searches the
lowercased, sorted JSON representation of the entire parsed response. The full
rule is given by the `oracle` object in `source_audit_evidence.json`; the scorer
evaluates that rule from the preserved response fields and does not use the
stored `archived_accepted` verdict to determine correctness.

**Acceptance here means satisfying this lexical source-audit rule.** It is not
proof of a vulnerability, a maintainer-confirmed finding, or execution-based
verification. Lexical conditions can miss valid paraphrases and can also be
satisfied by unsupported statements. The data do not establish general
vulnerability-discovery effectiveness or prove equivalence between methods.

## Recomputed comparisons

| Comparison | Accepted A / B | Pairs | A wins / B wins / ties |
| --- | --- | ---: | --- |
| Original schema / matched free-form | 10/24 / 12/24 | 24 | 2 / 4 / 18 |
| Extended schema / matched free-form | 12/24 / 12/24 | 24 | 4 / 4 / 16 |

The comparison unit is a provider-task pair. The two provider outputs on each
task are not independent task replications. The table reports descriptive counts,
not independent-task statistical inference. Machine reports retain historical
nominal sign-test fields for traceability only. These results did not reproduce
the structured-state separation observed in the separate high-pressure setting.

## Protocol failures, retries and sensitivity

- Three original **generic structured memory** final responses failed protocol
  checks (one transport failure and two missing-field failures). They have
  `accepted=null` and are excluded from acceptance-rate denominators: this arm
  has 6 accepted responses among 21 eligible responses, not a 6/24 semantic rate.
  These failures do not affect the two main comparisons above.
- Two original DeepSeek extended-schema finalizer calls failed: WP-H-001
  exhausted its 4096-token output budget without a JSON response, and WP-H-011
  encountered a connection reset. Only these two failed calls were retried with
  the same saved prompts and an 8192-token output budget. Both retries completed.
  The original failed attempts and the selected replacements are retained with
  identities and prompt hashes; failed calls are never counted as semantic errors.
- The weak handoff for extended-schema WP-H-007 failed JSON parsing. The
  historical runner passed the weak model's raw text as a fallback, and both
  strong-provider responses were protocol-valid and accepted. The 12/24 result
  therefore describes the recorded pipeline **including this fallback**.
- The report additionally excludes both WP-H-007 rows for strict end-to-end
  protocol validity. On the remaining common pairs, extended-schema and matched
  free-form are each 10/22, with 4 wins, 4 losses and 14 ties. The conclusion about
  absent observed superiority is unchanged.
- A separate post-audit retry-exclusion sensitivity removes both retry pairs
  from both arms: 4 wins, 3 losses and 15 ties over 22 pairs. Also excluding the
  two raw-handoff-fallback pairs gives 4/3/13 over 20 pairs. These are descriptive
  checks, not prespecified analyses or evidence of superiority. See the root
  `REPRODUCE.md` for the offline sensitivity command and protocol table.

## Files, provenance and boundaries

- `source_audit_evidence.json`: 96 selected analysis responses, two retained
  replaced finalizer failures, status/identity fields, and the public oracle.
- `source_provenance.json`: original summary/script/parsed-response digests,
  released-response digests, redaction counts and the check-preservation audit.
- `cross_family_rescore.json`: output from the standalone scorer.
- `prepare_from_private_archive.py`: author-side deterministic extraction utility;
  it requires the private historical project archive and is not needed by reviewers.

The export preserves parsed model-response fields, public source filenames and
function identifiers needed by the oracle. It excludes original prompts, raw API
responses, local machine paths, credentials, provider endpoints and source code
bundles. Six illustrative traversal strings were redacted. Every historical
check was rerun before and after redaction; no check or acceptance result changed.
Remaining source anchors are identifiers, not executable exploit instructions.

This supports independent **rescoring of archived parsed responses**. It does
not reproduce the raw-text JSON extraction, original model calls, input source
bundle generation, or the scientific truth of model-written vulnerability claims.
Prompt hashes demonstrate retry identity without disclosing prompt contents.
Per-task or per-provider repetitions and a generalization estimate were not made.
Original private-source digests cover original bytes. The released evidence
digest uses canonical JSON (UTF-8, sorted keys, compact separators), so Git's
LF/CRLF transport conversion does not invalidate the content check.
