# Discovery Runtime Case

This de-identified case is derived from the structure of an authorized open-source review. It contains no project identity, revision, network address, payload, credential, or target-specific reproduction procedure.

The case exercises the complete BGVD-State runtime path:

1. load 23 ordered events from multiple producers;
2. reconstruct six candidate identities;
3. retain five rejected exploration paths;
4. bind material evidence and verifier results;
5. preserve an earlier positive technical verifier;
6. replace the current verifier view with a negative scope review; and
7. block unsupported finalization while retaining the full audit history.

The final scope decision is supplied by an external human or policy verifier. BGVD-State records and enforces that decision; it does not infer a threat model or disclosure policy by itself.

Run the case:

```console
bgvd-state replay --events examples/discovery_runtime_case/events.json \
  --state-out state.json --handoff-out handoff.json
bgvd-state gate --state state.json --candidate CASE-C06 --out gate.json
bgvd-state summary --state state.json
```

Expected summary:

```text
BGVD-State Runtime Summary
Events loaded: 23
Candidates: 6
Rejected candidates: 5
Failed paths: 5
Frontier items: 1
Finalization allowed: none
```

The gate command exits with status `2`, because the current verifier is negative. The earlier technical verifier remains in the event history for audit.
