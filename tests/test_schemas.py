from __future__ import annotations

import json
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator

from bgvd_state import EvidenceLifecycle, Event, EventType, HandoffBuilder


ROOT = Path(__file__).resolve().parents[1]


class SchemaTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
