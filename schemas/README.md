# Event contract and compatibility input

[`event.schema.json`](event.schema.json) describes the **canonical, normalized
event representation** exported by `Event.to_dict()`. It deliberately excludes
legacy spellings and unknown top-level fields. The Python `Event.from_dict()`
adapter accepts the compatibility superset below, normalizes it, and then
validates the complete normalized event. Validate `Event.from_dict(raw).to_dict()`
against the canonical schema when importing legacy input.

New producers should emit canonical fields and values. Direct Python `Event(...)`
construction does not run the compatibility adapter; it must use `EventType`
values and canonical field types. `EventStore.append()` and the lifecycle validate
those directly constructed events before storing or applying them. Schema
validation alone cannot check whether an identifier is already present in a store.

## Eight legacy type names

| Accepted input type | Canonical type |
| --- | --- |
| `material_trace` | `material_evidence` |
| `terminal_verifier` | `verifier_result` |
| `worker_note` | `hypothesis` |
| `duplicate_worker_output` | `candidate_update` |
| `superseding_check` | `candidate_update` |
| `noise` | `observation` |
| `tool_observation` | `observation` |
| `verifier` | `verifier_result` |

## Six alternative field names

| Alternative | Canonical field | Selection rule |
| --- | --- | --- |
| `event_id` | `id` | First truthy value: `id`, then `event_id`. |
| `event_type` | `type` | First truthy value: `type`, `event_type`, then `kind`. |
| `kind` | `type` | Same precedence as above. |
| `candidate` | `candidate_id` | Used only when the canonical key is absent. |
| `time` | `timestamp` | First truthy value: `timestamp`, then `time`. |
| `status` | `verifier_status` | Used only when the canonical key is absent. |

The top-level `status` alias is a verifier boolean. It is distinct from
`metadata.status`, which requests a candidate lifecycle status.

## Normalization and defaults

- The selected identifier and `summary` are converted to strings and stripped
  of surrounding whitespace. Missing values default to an empty string and are
  rejected; an explicitly supplied non-string summary follows Python `str()`.
- Scalar JSON candidate identifiers are converted to strings, except `null`, the
  empty string, `"NONE"`, and `"null"`, which become `None`. Arrays and objects
  are rejected, not converted into identifiers.
- Verifier booleans are retained. Case-insensitive strings `"true"` and `"false"`
  become booleans. Other verifier-status values become `None` (unknown), never a
  positive verifier. A present canonical key, including `false` or `null`, takes
  precedence over the alternative `status` key.
- `refs` and `invalidates` default to empty lists. The compatibility adapter
  iterates each supplied collection and converts its items to strings; this
  includes historical iterable inputs. Producers should use JSON arrays, since
  passing a string would iterate its individual characters.
- `metadata` defaults to an empty dictionary and follows Python `dict()` input
  conversion. The normalized value must be JSON serializable with finite numbers.
  `timestamp` and `outcome` must be strings or `null` after selection.
- The reserved `metadata.vulnerability_type` and `metadata.target_object` fields,
  when supplied, must be strings or `null`. The lifecycle copies them into the
  candidate description, so this constraint preserves the handoff schema's types.
  Invalid values are rejected before storing or applying the event. Other metadata
  keys remain extensible, subject to the JSON-serializability requirement above.
- Unrecognized top-level keys are ignored by the compatibility adapter and do
  not appear in the canonical representation. This differs intentionally from
  the canonical schema's `additionalProperties: false`.
- For `candidate_update`, `metadata.status`, if supplied and non-null, must be
  one of `proposed`, `active`, `partial_evidence`, `verified`, `rejected`,
  `superseded`, or `finalized`. An unrecognized, empty, or non-string status is
  rejected before any event-store or lifecycle mutation. `finalized` remains
  subject to the finalization gate; naming a status does not supply evidence.

## Ordering and rejection boundary

The lifecycle applies events in the submitted sequence. Timestamps are optional
descriptive fields, not ordering keys. Clients serialize multiple producers into
one sequence before replay.

Validation failure or a duplicate identifier leaves the rejected event out of
the store and leaves candidates, invalidations, failed paths, and the handoff
unchanged. Replay is atomic **per event**: a failure stops the batch and retains
the already accepted prefix. It does not roll back the whole batch.

This contract governs event ingestion into a normally constructed lifecycle.
State objects and loaded checkpoints are trusted application data; they are not
authenticated evidence containers. Do not modify accepted `Event` or state
objects in place. Replay the source events when checking an untrusted checkpoint.

Regression coverage is in `tests/test_event_validation.py` and
`tests/test_schemas.py`: every legacy alias, canonical export, malformed inputs,
state-preserving rejection, valid-prefix replay, and candidate-bound gate checks.
