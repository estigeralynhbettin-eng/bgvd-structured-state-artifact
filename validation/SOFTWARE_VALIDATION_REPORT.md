# BGVD-State Software Validation Report

- Generated: `2026-07-12T15:53:00.835911+00:00`
- Status: **PASS**
- Python: `3.12.13`
- Platform: `Windows-11-10.0.26200-SP0`
- Tests passed: `15`

| Check | Return code | Expected | Status |
|---|---:|---|---|
| `SW-LINT` | 0 | [0] | PASS |
| `SW-FORMAT` | 0 | [0] | PASS |
| `SW-TEST` | 0 | [0] | PASS |
| `SW-BUILD` | 0 | [0] | PASS |
| `SW-EXAMPLE-REPLACEMENT` | 0 | [0] | PASS |
| `SW-GATE-CURRENT` | 0 | [0] | PASS |
| `SW-EXAMPLE-STALE` | 0 | [0] | PASS |
| `SW-GATE-STALE-REJECT` | 2 | [2] | PASS |
| `ARTIFACT-REGRESSION` | 0 | [0] | PASS |

The stale-verifier gate uses expected exit code `2`; that outcome is a passing
negative-control check because unsupported finalization must be rejected.

Machine-readable report: `software_validation_report.json`.
