# API Reference

## `Event`

`Event` is the append-only input record. Required fields are `id`, `type`, and
`summary`. Security relations use `candidate_id`, `refs`, `invalidates`, and
`verifier_status`. The normative JSON representation is in
`schemas/event.schema.json`.

## `EventStore`

```python
store = EventStore()
store.append(event)
store.get("E0001")
store.to_jsonl("events.jsonl")
store = EventStore.from_jsonl("events.jsonl")
```

Event identifiers are unique. Duplicate identifiers and empty summaries are
rejected before state mutation.

## `EvidenceLifecycle`

```python
lifecycle = EvidenceLifecycle()
lifecycle.apply(event)
lifecycle.replay(events)
lifecycle.save("state.json")
lifecycle = EvidenceLifecycle.load("state.json")
```

The lifecycle applies these invariants:

1. Evidence references remain attached until explicitly invalidated.
2. A candidate is verified only with current material evidence and a current
   positive verifier result bound to the same candidate.
3. A current verifier result supersedes an earlier verifier result.
4. Failed paths remain visible in subsequent handoff packets.
5. Invalidated evidence cannot support finalization.
6. A `finalization` event changes status only when `FinalizationGate` allows it.

## `FinalizationGate`

```python
decision = FinalizationGate().evaluate(lifecycle.state, "C1")
```

The decision contains `allowed`, machine-readable `reasons`, current material
evidence references, and the current verifier reference.

## `HandoffBuilder`

```python
packet = HandoffBuilder().build(lifecycle.state)
```

The packet separates active, rejected, superseded, and finalized candidates. It also
contains failed paths, invalidated event identifiers, frontier items, open
questions, and the candidate identifiers currently eligible for finalization.
