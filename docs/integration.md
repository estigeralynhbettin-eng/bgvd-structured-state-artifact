# Integration Guide

BGVD-State sits between an agent/tool runtime and a model or human finalizer.
It does not execute tools and does not require a particular LLM framework.

## Producer Contract

Tool wrappers, weak models, and deterministic parsers emit `Event` objects.
Every event must have a unique identifier and concise summary. Material evidence
and verifier results must name the candidate they concern.

## State Contract

Feed events to one `EvidenceLifecycle` instance in observed order. Persist state
after each tool round when crash recovery is required. Never edit the derived
candidate state directly; append an invalidation or update event instead.

## Consumer Contract

Pass the output of `HandoffBuilder` to a finalizer. The consumer may continue
exploration, reject a candidate, or request finalization. A model recommendation
does not override `FinalizationGate`.
Appending a `finalization` event therefore records a completed transition only
when current material evidence and a current positive verifier satisfy the gate.

## Framework Adapter Pattern

```python
def after_tool_call(tool_call, observation, lifecycle):
    lifecycle.apply(to_tool_event(tool_call))
    lifecycle.apply(to_observation_event(observation))
    lifecycle.save("run-state.json")
    return HandoffBuilder().build(lifecycle.state)
```

Framework-specific adapters should remain thin. The event schema and lifecycle
rules are the stable boundary; model prompts and tool clients may change.

## Defensive Scope

The package manages evidence state. It does not include live targets, payloads,
credentials, exploitation procedures, or autonomous target execution.
