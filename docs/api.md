# API Reference

## `Event`

`Event` is the append-only input record. Required fields are `id`, `type`, and
`summary`. Security relations use `candidate_id`, `refs`, `invalidates`, and
`verifier_status`. The canonical JSON representation is in
`schemas/event.schema.json`. `Event.from_dict()` also accepts eight legacy type
names and six alternative field names; their normalization and precedence rules
are documented beside the schema in [`schemas/README.md`](../schemas/README.md).
Canonical schema validation applies after that normalization. Direct Python
construction uses `EventType` and canonical field types.

## `EventStore`

```python
store = EventStore()
store.append(event)
store.get("E0001")
store.to_jsonl("events.jsonl")
store = EventStore.from_jsonl("events.jsonl")
```

Event identifiers are unique. All normalized event fields, including candidate
status values, are validated before appending an event. Duplicate identifiers,
empty identifiers/summaries, and invalid event values are rejected without
changing the event store or lifecycle state.

## `EvidenceLifecycle`

```python
lifecycle = EvidenceLifecycle()
lifecycle.apply(event)
lifecycle.replay(events)
lifecycle.save("state.json")
lifecycle = EvidenceLifecycle.load("state.json")
```

Events are applied in the submitted order, not sorted by timestamp. Clients must
serialize multiple producers. On a replay error, earlier accepted events remain;
the rejected event leaves no partial state and later events are not applied.
Atomicity is per event, not per batch or across concurrent writers. Checkpoints
and in-memory state objects are trusted application data; use event replay to
verify untrusted state snapshots and do not modify accepted events in place.

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
