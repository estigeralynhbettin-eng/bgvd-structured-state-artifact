# BGVD-State

BGVD-State is evidence-lifecycle middleware for verifier-gated handoff in
defensive LLM security agents. It records model and tool events, maintains
candidate identity, binds material evidence and verifier results, preserves
failed paths, invalidates stale evidence, and produces a compact handoff packet
for a stronger model or human analyst.

The safety-critical state transitions are deterministic. No API key, model
service, container, or live target is required to use the core package.

## Why It Exists

A prose summary can mention the right facts while losing the relations that
make a security finding valid: which evidence supports which candidate, whether
the verifier result is current, which paths have failed, and whether
finalization is allowed. BGVD-State makes those relations explicit and checks
them before a finding can be finalized.

This repository also contains the sanitized replay artifact used to evaluate
the accompanying structured-state-interface study. The software does not claim
that typed blackboards universally outperform prose memory or that it discovers
real-world vulnerabilities.

## Installation

BGVD-State supports Python 3.10-3.12 and has no runtime dependencies.

```bash
python -m pip install .
```

For an editable development install:

```bash
python -m pip install -e .
```

## Ten-Minute Example

Replay a sanitized candidate-replacement event stream:

```bash
bgvd-state replay \
  --events examples/candidate_replacement/events.json \
  --state-out state.json \
  --handoff-out handoff.json
```

Check the current candidate:

```bash
bgvd-state gate --state state.json --candidate C_CURRENT
```

The gate allows `C_CURRENT` and rejects `C_OLD`, whose evidence was invalidated.
The second example demonstrates that an old positive verifier cannot override a
current negative verifier:

```bash
bgvd-state replay \
  --events examples/stale_verifier/events.json \
  --state-out stale-state.json \
  --handoff-out stale-handoff.json

bgvd-state gate --state stale-state.json --candidate C_STALE
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

```bash
python -m unittest discover -s tests -v
python validate_structured_state_artifact.py \
  --artifact . \
  --out-dir artifact_validation_output
```

The test suite runs on Windows and Linux with Python 3.10 and 3.12 in GitHub
Actions. The artifact validator performs no model calls and starts no services.

## Sanitized Research Artifact

The root-level `v3*` and `phase9*` JSON/Markdown files are redacted replay
fixtures and result summaries. `REPRODUCE.md` maps the paper-facing contrasts to
those files. The release excludes live targets, credentials, operational
commands, network addresses, target-specific payloads, and direct reproduction
procedures.

The bounded evidence represented in the artifact is:

- security-specific state semantics improve weak-to-strong handoff over the
  tested matched free-form, generic structured, and retrieval-memory controls
  under selected verifier-replay state pressure;
- the advantage disappears in pressure-reduced replay and does not generalize
  to the tested cross-family source-audit setting;
- typed protocol surface alone does not improve over information-equivalent
  curated prose.

## Licenses

Code under `src/`, `tests/`, `examples/`, and the standalone validator is MIT
licensed; see `LICENSE.txt`. Sanitized fixtures, result summaries, and artifact
documentation are CC BY 4.0; see `DATA_LICENSE.txt`.

## Responsible Use

Use this package only for defensive research, authorized environments, and
false-positive control. See `SECURITY.md` for disclosure guidance.
