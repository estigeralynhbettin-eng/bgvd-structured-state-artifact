# Recorded strong-model token accounting

This directory contains a sanitized, per-call projection of the original held-out
curation experiment. It lets a reviewer independently sum the recorded token
proxy without a model call, account, network connection, or new dependency.

From the artifact root, run:

```console
python score_token_accounting.py --artifact . --out-dir token_output
```

The expected result is `status: PASS` and
`accounting_completeness: OBSERVED_USAGE_ONLY`. The JSON report is written to
`token_output/token_accounting_report.json`.

## Definition and expected results

The proxy sums provider-reported **prompt plus completion tokens** recorded for
paid strong-model finalizers and, for the strong-curated route, state-update
calls. Each route uses the same 15 fixtures with two providers (30 model–fixture
runs). It excludes local/weak-model tokens, runtime, hardware costs, monetary
prices, and cache-price discounts. Reasoning tokens are retained as a reported
subset of completion tokens; they are not added a second time.

Token usage was not recorded for 14 failed state-update calls and is excluded
from the sum.

| Route | Finalizer calls | Updater calls | Recorded finalizer tokens | Recorded updater tokens | Recorded proxy |
|---|---:|---:|---:|---:|---:|
| Weak/local curated | 30 | 0 paid strong-model updates | 24,391 | 0 | 24,391 |
| Strong curated | 30 | 84 | 25,565 | 121,290 | 146,855 |

The data contain **144 call records**: 130 with usage extracted from archived
successful raw responses, and 14 failed updater records.
The failed calls affected 8 of the 30 strong-curated runs. They are retained with
`usage: null` and `usage_status: unavailable`. Their historical
`recorded_proxy_tokens: 0` is an accounting convention; it does **not** mean that
they consumed or were billed zero tokens.

## Files and provenance

- `calls.json`: call identities, numerical usage fields, outcome, usage
  availability, historical proxy contribution, and original source content hash.
- `origin_manifest.json`: SHA-256 of the projected data, source-summary hashes,
  released-summary hashes, and fixture hashes.
- `token_accounting_report.json`: checked totals and per-run reconciliation.
- `export_from_local.py`: author-side deterministic exporter for the archived
  source directories. It makes no API calls and exports no prompts, raw response
  text, request identifiers, credentials, or local filesystem paths.

Each reported-usage record was extracted from an archived `raw_response.json`;
each failed-call record is anchored to an archived failure record and the
released episode status. Source hashes preserve content identity but do not make
unpublished raw contents visible. The four existing `v3g_*_summary.json` and
`v3h_*_summary.json` files remain unchanged and are reconciliation targets, not
the source of successful per-call usage values.

Public JSON checksums use UTF-8, sorted keys and compact JSON serialization, so
Git line-ending conversion or JSON indentation does not change their content
identity. Original raw-response/failure/source-summary hashes remain byte hashes.

The scorer requires the full expected call grid, unique call IDs, valid token
components, explicit missing-usage status, and agreement with per-run released totals.
It fails if a successful or failed call is omitted, a count is changed, a record
is duplicated, or missing failed-call usage is replaced by invented zero usage.
