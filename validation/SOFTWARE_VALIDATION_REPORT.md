# BGVD-State Software Validation Report

- Generated: `2026-07-16T05:47:02.336649+00:00`
- Status: **PASS**
- Python: `3.12.13`
- Platform: `Windows-11-10.0.26200-SP0`
- Tests passed: `18`

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
| `SW-RUNTIME-CASE` | 0 | [0] | PASS |
| `SW-RUNTIME-CASE-GATE` | 2 | [2] | PASS |
| `SW-RUNTIME-ENGINEERING` | 0 | [0] | PASS |
| `ARTIFACT-REGRESSION` | 0 | [0] | PASS |

The stale-verifier gate uses expected exit code `2`; that outcome is a passing
negative-control check because unsupported finalization must be rejected.
The complete runtime case also uses expected exit code `2` after a current
negative scope verifier supersedes an earlier positive technical verifier.

Machine-readable report: `software_validation_report.json`.
