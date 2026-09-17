from __future__ import annotations

import json
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator

from bgvd_state import EvidenceLifecycle, Event, EventType, HandoffBuilder


ROOT = Path(__file__).resolve().parents[1]


class SchemaTests(unittest.TestCase):
    def event_validator(self) -> Draft202012Validator:
        schema = json.loads((ROOT / "schemas" / "event.schema.json").read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(schema)
        return Draft202012Validator(schema)

    def test_event_example_validates(self) -> None:
        schema = json.loads((ROOT / "schemas" / "event.schema.json").read_text(encoding="utf-8"))
        fixture = json.loads(
            (ROOT / "examples" / "candidate_replacement" / "events.json").read_text(
                encoding="utf-8"
            )
        )
        validator = Draft202012Validator(schema)
        for item in fixture["events"]:
            validator.validate(item)

    def test_generated_handoff_validates(self) -> None:
        schema = json.loads((ROOT / "schemas" / "handoff.schema.json").read_text(encoding="utf-8"))
        lifecycle = EvidenceLifecycle()
        lifecycle.replay(
            [
                Event("E1", EventType.MATERIAL_EVIDENCE, "Evidence.", candidate_id="C1"),
                Event(
                    "E2",
                    EventType.VERIFIER_RESULT,
                    "Positive verifier.",
                    candidate_id="C1",
                    verifier_status=True,
                ),
            ]
        )
        Draft202012Validator(schema).validate(HandoffBuilder().build(lifecycle.state))

    def test_all_legacy_type_aliases_normalize_to_canonical_schema(self) -> None:
        aliases = {
            "material_trace": "material_evidence",
            "terminal_verifier": "verifier_result",
            "worker_note": "hypothesis",
            "duplicate_worker_output": "candidate_update",
            "superseding_check": "candidate_update",
            "noise": "observation",
            "tool_observation": "observation",
            "verifier": "verifier_result",
        }
        validator = self.event_validator()
        for legacy, canonical in aliases.items():
            with self.subTest(alias=legacy):
                raw = {"id": "E1", "type": legacy, "summary": "Legacy input"}
                self.assertFalse(validator.is_valid(raw))
                normalized = Event.from_dict(raw).to_dict()
                self.assertEqual(normalized["type"], canonical)
                validator.validate(normalized)

    def test_all_six_legacy_field_names_normalize_to_canonical_schema(self) -> None:
        aliases = {
            "event_id": ("id", "E1"),
            "event_type": ("type", "observation"),
            "kind": ("type", "observation"),
            "candidate": ("candidate_id", "C1"),
            "time": ("timestamp", "2026-09-16"),
            "status": ("verifier_status", False),
        }
        validator = self.event_validator()
        for legacy, (canonical, value) in aliases.items():
            with self.subTest(alias=legacy):
                raw = {"id": "E1", "type": "observation", "summary": "Legacy input"}
                raw.pop(canonical, None)
                raw[legacy] = value
                self.assertFalse(validator.is_valid(raw))
                normalized = Event.from_dict(raw).to_dict()
                self.assertEqual(normalized[canonical], value)
                validator.validate(normalized)

    def test_compatibility_precedence_and_coercions(self) -> None:
        normalized = Event.from_dict({
            "id": "canonical", "event_id": "ignored", "type": "observation",
            "kind": "verifier", "summary": "  Trimmed  ", "candidate_id": None,
            "candidate": "ignored", "verifier_status": False, "status": True,
            "timestamp": "", "time": "2026-09-16", "refs": [1],
            "invalidates": [2], "unused_legacy_field": "discarded",
        }).to_dict()
        self.assertEqual(normalized["id"], "canonical")
        self.assertEqual(normalized["type"], "observation")
        self.assertEqual(normalized["summary"], "Trimmed")
        self.assertIsNone(normalized["candidate_id"])
        self.assertIs(normalized["verifier_status"], False)
        self.assertEqual(normalized["timestamp"], "2026-09-16")
        self.assertEqual(normalized["refs"], ["1"])
        self.assertEqual(normalized["invalidates"], ["2"])
        self.assertNotIn("unused_legacy_field", normalized)
        self.event_validator().validate(normalized)

    def test_candidate_update_status_rejection_agrees_with_schema(self) -> None:
        validator = self.event_validator()
        for status in ["unknown", "", False, 0, [], {}]:
            with self.subTest(status=status):
                raw = {"id": "E1", "type": "candidate_update", "summary": "Invalid status",
                       "metadata": {"status": status}}
                self.assertFalse(validator.is_valid(raw))
                with self.assertRaises(ValueError):
                    Event.from_dict(raw)
        for status in [None, "proposed", "active", "partial_evidence", "verified", "rejected",
                       "superseded", "finalized"]:
            raw = {"id": "E1", "type": "candidate_update", "summary": "Valid status",
                   "metadata": {"status": status}}
            validator.validate(Event.from_dict(raw).to_dict())

    def test_all_released_event_examples_normalize_to_canonical_schema(self) -> None:
        validator = self.event_validator()
        examples = sorted((ROOT / "examples").glob("*/events.json"))
        self.assertTrue(examples)
        for path in examples:
            fixture = json.loads(path.read_text(encoding="utf-8"))
            rows = fixture["events"] if isinstance(fixture, dict) else fixture
            for item in rows:
                with self.subTest(example=path.parent.name, event=item.get("id")):
                    validator.validate(Event.from_dict(item).to_dict())


if __name__ == "__main__":
    unittest.main()
