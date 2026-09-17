"""Reserved metadata must preserve the event-to-handoff type contract."""

from __future__ import annotations

import copy
import json
from pathlib import Path
import unittest

from jsonschema import Draft202012Validator

from bgvd_state import EvidenceLifecycle, Event, EventStore, EventType
from bgvd_state import FinalizationGate, HandoffBuilder


ROOT = Path(__file__).resolve().parents[1]
RESERVED = ("vulnerability_type", "target_object")
INVALID_JSON_VALUES = (False, True, 0, 1, 1.5, [], ["item"], {"label": "item"})


def ready_lifecycle() -> EvidenceLifecycle:
    lifecycle = EvidenceLifecycle()
    lifecycle.replay([
        Event("material", EventType.MATERIAL_EVIDENCE, "Evidence", candidate_id="C1"),
        Event("verifier", EventType.VERIFIER_RESULT, "Positive", candidate_id="C1",
              verifier_status=True),
        Event("failed", EventType.FAILED_PATH, "Rejected route", candidate_id="C2"),
        Event("stale", EventType.MATERIAL_EVIDENCE, "Old evidence", candidate_id="C3"),
        Event("invalidate", EventType.INVALIDATION, "Stale", invalidates=["stale"]),
    ])
    lifecycle.state.open_questions.append("Existing review question")
    return lifecycle


def snapshot(lifecycle: EvidenceLifecycle) -> dict:
    return copy.deepcopy({
        "state": lifecycle.state.to_dict(),
        "store_events": [event.to_dict() for event in lifecycle.store.events],
        "store_ids": set(lifecycle.store._ids),
        "handoff": HandoffBuilder().build(lifecycle.state),
        "gates": {key: FinalizationGate().evaluate(lifecycle.state, key).to_dict()
                  for key in lifecycle.state.candidates},
    })


class ReservedMetadataContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.event_schema = Draft202012Validator(json.loads(
            (ROOT / "schemas" / "event.schema.json").read_text(encoding="utf-8")))
        self.handoff_schema = Draft202012Validator(json.loads(
            (ROOT / "schemas" / "handoff.schema.json").read_text(encoding="utf-8")))

    def assert_rejection_is_atomic(self, key: str, value: object, direct: bool) -> None:
        for candidate_id in ("C1", "NEW"):
            with self.subTest(candidate_id=candidate_id):
                lifecycle = ready_lifecycle()
                before = snapshot(lifecycle)
                raw = {"id": "bad-metadata", "type": "hypothesis", "summary": "Bad metadata",
                       "candidate_id": candidate_id, "invalidates": ["material", "verifier"],
                       "metadata": {key: value}}
                with self.assertRaisesRegex(ValueError, f"metadata[.]{key} must be a string or null"):
                    event = (Event(**{**raw, "type": EventType.HYPOTHESIS}) if direct
                             else Event.from_dict(raw))
                    lifecycle.apply(event)
                self.assertEqual(snapshot(lifecycle), before)
                self.assertIsNone(lifecycle.store.get("bad-metadata"))
                lifecycle.apply(Event("bad-metadata", EventType.OBSERVATION, "Corrected input"))
                self.assertIsNotNone(lifecycle.store.get("bad-metadata"))

    def test_schema_rejects_reserved_non_string_json_values(self) -> None:
        for key in RESERVED:
            for value in INVALID_JSON_VALUES:
                with self.subTest(key=key, value=value):
                    raw = {"id": "E", "type": "hypothesis", "summary": "Candidate",
                           "candidate_id": "C1", "metadata": {key: value}}
                    self.assertFalse(self.event_schema.is_valid(raw))

    def test_from_dict_rejects_before_any_state_change(self) -> None:
        for key in RESERVED:
            for value in INVALID_JSON_VALUES:
                with self.subTest(key=key, value=value):
                    self.assert_rejection_is_atomic(key, value, direct=False)

    def test_direct_event_rejects_before_any_state_change(self) -> None:
        for key in RESERVED:
            for value in INVALID_JSON_VALUES:
                with self.subTest(key=key, value=value):
                    self.assert_rejection_is_atomic(key, value, direct=True)

    def test_store_alone_rejects_reserved_values_without_reserving_id(self) -> None:
        for key in RESERVED:
            for value in INVALID_JSON_VALUES:
                with self.subTest(key=key, value=value):
                    store = EventStore()
                    with self.assertRaises(ValueError):
                        store.append(Event("E", EventType.OBSERVATION, "Bad metadata",
                                           metadata={key: value}))
                    self.assertEqual(store.events, [])
                    self.assertEqual(store._ids, set())
                    store.append(Event("E", EventType.OBSERVATION, "Corrected input"))
                    self.assertEqual(len(store.events), 1)

    def test_strings_and_null_produce_schema_valid_handoffs(self) -> None:
        for direct in (False, True):
            for key in RESERVED:
                for value in (None, "", "valid label", "中文标签"):
                    for candidate_id in ("C1", "NEW"):
                        with self.subTest(direct=direct, key=key, value=value,
                                          candidate_id=candidate_id):
                            lifecycle = ready_lifecycle()
                            raw = {"id": "E", "type": "hypothesis", "summary": "Valid metadata",
                                   "candidate_id": candidate_id, "metadata": {key: value}}
                            event = (Event(**{**raw, "type": EventType.HYPOTHESIS}) if direct
                                     else Event.from_dict(raw))
                            self.event_schema.validate(event.to_dict())
                            lifecycle.apply(event)
                            self.handoff_schema.validate(HandoffBuilder().build(lifecycle.state))
                            self.assertEqual(getattr(lifecycle.state.candidates[candidate_id], key),
                                             value)

    def test_missing_reserved_fields_and_extensible_metadata_remain_supported(self) -> None:
        metadata = {"custom_flag": False, "custom_count": 3, "custom_items": [1, None, "x"],
                    "custom_object": {"target_object": [], "vulnerability_type": {}},
                    "reason": {"detail": "application-specific metadata"}}
        for direct in (False, True):
            for event_type in EventType:
                with self.subTest(direct=direct, event_type=event_type):
                    raw = {"id": "E", "type": event_type.value, "summary": "Custom metadata",
                           "candidate_id": "C1", "metadata": metadata}
                    event = (Event(**{**raw, "type": event_type}) if direct else Event.from_dict(raw))
                    self.assertEqual(event.to_dict()["metadata"], metadata)
                    self.event_schema.validate(event.to_dict())
                    lifecycle = EvidenceLifecycle()
                    lifecycle.apply(event)
                    self.handoff_schema.validate(HandoffBuilder().build(lifecycle.state))

    def test_legacy_adapter_preserves_valid_reserved_metadata(self) -> None:
        metadata = {"vulnerability_type": "review category", "target_object": "source path"}
        event = Event.from_dict({"event_id": "E", "kind": "material_trace", "summary": "Legacy",
                                 "candidate": "C1", "metadata": metadata})
        self.assertEqual(event.metadata, metadata)
        self.assertIs(event.type, EventType.MATERIAL_EVIDENCE)
        self.event_schema.validate(event.to_dict())
        lifecycle = EvidenceLifecycle()
        lifecycle.apply(event)
        self.handoff_schema.validate(HandoffBuilder().build(lifecycle.state))

    def test_candidate_id_scalar_conversion_and_container_rejection(self) -> None:
        base = {"id": "E", "type": "observation", "summary": "Candidate ID"}
        for value in (None, "", "NONE", "null", "C1", False, True, 0, 1.5):
            with self.subTest(value=value):
                expected = None if value in (None, "", "NONE", "null") else str(value)
                self.assertEqual(Event.from_dict({**base, "candidate_id": value}).candidate_id,
                                 expected)
        for value in ([], {}, ["C1"], {"id": "C1"}):
            with self.subTest(value=value):
                with self.assertRaises(TypeError):
                    Event.from_dict({**base, "candidate_id": value})


if __name__ == "__main__":
    unittest.main()
