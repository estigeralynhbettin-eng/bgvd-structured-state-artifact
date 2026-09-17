"""Negative-path checks for the public event ingestion boundary."""

from __future__ import annotations

import copy
import unittest

from bgvd_state import CandidateStatus, EvidenceLifecycle, Event, EventStore, EventType
from bgvd_state import FinalizationGate, HandoffBuilder


def ready_lifecycle() -> EvidenceLifecycle:
    lifecycle = EvidenceLifecycle()
    lifecycle.replay([
        Event("material", EventType.MATERIAL_EVIDENCE, "Evidence", candidate_id="C1"),
        Event("verifier", EventType.VERIFIER_RESULT, "Verified", candidate_id="C1",
              verifier_status=True),
    ])
    return lifecycle


class EventValidationTests(unittest.TestCase):
    def assert_rejected_without_mutation(self, item: Event) -> None:
        lifecycle = ready_lifecycle()
        before_state = copy.deepcopy(lifecycle.state.to_dict())
        before_packet = copy.deepcopy(HandoffBuilder().build(lifecycle.state))
        before_ids = [event.id for event in lifecycle.store.events]
        with self.assertRaises((ValueError, TypeError)):
            lifecycle.apply(item)
        self.assertEqual(lifecycle.state.to_dict(), before_state)
        self.assertEqual(HandoffBuilder().build(lifecycle.state), before_packet)
        self.assertEqual([event.id for event in lifecycle.store.events], before_ids)
        self.assertIsNone(lifecycle.store.get(item.id))
        # Failed identifiers must remain reusable, not just hidden from state.
        lifecycle.apply(Event(item.id, EventType.OBSERVATION, "Corrected event"))

    def test_invalid_status_does_not_invalidate_or_append(self) -> None:
        self.assert_rejected_without_mutation(Event(
            "bad-status", EventType.CANDIDATE_UPDATE, "Invalid update", candidate_id="C1",
            invalidates=["material", "verifier"], metadata={"status": "not-a-status"},
        ))

    def test_invalid_status_does_not_create_candidate(self) -> None:
        self.assert_rejected_without_mutation(Event(
            "bad-new", EventType.CANDIDATE_UPDATE, "Invalid update", candidate_id="NEW",
            invalidates=["verifier"], metadata={"status": "not-a-status"},
        ))

    def test_direct_constructor_rejects_malformed_fields_before_mutation(self) -> None:
        cases = {
            "type": "not-an-event-type",
            "metadata": [],
            "refs": "material",
            "invalidates": [None],
            "verifier_status": "false",
            "timestamp": 123,
            "outcome": {},
            "candidate_id": [],
            "summary": "   ",
        }
        for field, value in cases.items():
            with self.subTest(field=field):
                item = Event("bad-field", EventType.OBSERVATION, "Observation",
                             candidate_id="NEW", invalidates=["verifier"])
                setattr(item, field, value)
                self.assert_rejected_without_mutation(item)

    def test_direct_constructor_requires_event_type_enum(self) -> None:
        self.assert_rejected_without_mutation(Event(
            "raw-type", "verifier_result", "Use EventType or from_dict", candidate_id="C1",
            verifier_status=True,
        ))

    def test_non_json_metadata_is_rejected_before_mutation(self) -> None:
        for value in [object(), {"set"}, float("nan"), float("inf")]:
            with self.subTest(value=type(value).__name__):
                self.assert_rejected_without_mutation(Event(
                    "bad-json", EventType.OBSERVATION, "Bad metadata", metadata={"x": value},
                ))

    def test_invalid_status_in_dict_is_rejected(self) -> None:
        for status in ["not-a-status", "", False, 0, [], {}]:
            with self.subTest(status=status):
                with self.assertRaises((ValueError, TypeError)):
                    Event.from_dict({"id": "bad", "type": "candidate_update",
                                     "summary": "Bad status", "metadata": {"status": status}})

    def test_invalid_type_in_dict_is_rejected_without_state_change(self) -> None:
        lifecycle = ready_lifecycle()
        before = lifecycle.state.to_dict()
        with self.assertRaises(ValueError):
            lifecycle.apply(Event.from_dict({
                "id": "bad", "type": "unrecognized", "summary": "Bad type",
                "invalidates": ["material"],
            }))
        self.assertEqual(lifecycle.state.to_dict(), before)

    def test_missing_and_blank_ids_or_summaries_are_rejected(self) -> None:
        for field in ["id", "summary"]:
            for value in ["", "  "]:
                with self.subTest(field=field, value=value):
                    raw = {"id": "event", "type": "observation", "summary": "Observation"}
                    raw[field] = value
                    with self.assertRaises(ValueError):
                        Event.from_dict(raw)

    def test_duplicate_id_does_not_apply_invalidations(self) -> None:
        lifecycle = ready_lifecycle()
        before = lifecycle.state.to_dict()
        with self.assertRaisesRegex(ValueError, "duplicate event id"):
            lifecycle.apply(Event("material", EventType.INVALIDATION, "Duplicate",
                                  candidate_id="NEW", invalidates=["verifier"]))
        self.assertEqual(lifecycle.state.to_dict(), before)
        self.assertEqual([event.id for event in lifecycle.store.events], ["material", "verifier"])

    def test_store_itself_rejects_semantically_invalid_event(self) -> None:
        store = EventStore()
        with self.assertRaises(ValueError):
            store.append(Event("bad", EventType.CANDIDATE_UPDATE, "Bad status",
                               metadata={"status": "unknown"}))
        self.assertEqual(store.events, [])
        store.append(Event("bad", EventType.OBSERVATION, "Identifier reusable"))

    def test_replay_retains_valid_prefix_but_not_rejected_event(self) -> None:
        lifecycle = ready_lifecycle()
        prefix = Event("prefix", EventType.OBSERVATION, "Valid prefix")
        expected = ready_lifecycle()
        expected.apply(prefix)
        with self.assertRaises(ValueError):
            lifecycle.replay([
                prefix,
                Event("bad", EventType.CANDIDATE_UPDATE, "Invalid", candidate_id="NEW",
                      metadata={"status": "unknown"}, invalidates=["verifier"]),
                Event("tail", EventType.OBSERVATION, "Must not execute"),
            ])
        self.assertEqual(lifecycle.state.to_dict(), expected.state.to_dict())
        self.assertEqual([event.id for event in lifecycle.store.events],
                         [event.id for event in expected.store.events])

    def test_false_string_is_not_a_positive_verifier(self) -> None:
        lifecycle = ready_lifecycle()
        lifecycle.apply(Event.from_dict({
            "id": "negative", "kind": "verifier", "candidate": "C1",
            "summary": "Negative verifier", "status": "false",
        }))
        self.assertIs(lifecycle.state.candidates["C1"].current_verifier_status, False)
        self.assertFalse(FinalizationGate().evaluate(lifecycle.state, "C1").allowed)

    def test_foreign_refs_do_not_create_evidence_for_other_candidate(self) -> None:
        lifecycle = ready_lifecycle()
        lifecycle.apply(Event("foreign", EventType.VERIFIER_RESULT, "Other verifier",
                              candidate_id="C2", verifier_status=True, refs=["material"]))
        self.assertTrue(FinalizationGate().evaluate(lifecycle.state, "C1").allowed)
        self.assertFalse(FinalizationGate().evaluate(lifecycle.state, "C2").allowed)
        self.assertEqual(lifecycle.state.candidates["C2"].material_evidence_refs, [])

    def test_negative_verifier_remains_bound_to_its_candidate(self) -> None:
        lifecycle = ready_lifecycle()
        lifecycle.replay([
            Event("negative", EventType.VERIFIER_RESULT, "Negative", candidate_id="C1",
                  verifier_status=False),
            Event("other-material", EventType.MATERIAL_EVIDENCE, "Other evidence",
                  candidate_id="C2"),
            Event("other-verifier", EventType.VERIFIER_RESULT, "Other positive",
                  candidate_id="C2", verifier_status=True),
        ])
        self.assertFalse(FinalizationGate().evaluate(lifecycle.state, "C1").allowed)
        self.assertTrue(FinalizationGate().evaluate(lifecycle.state, "C2").allowed)

    def test_invalidation_revokes_finalization(self) -> None:
        lifecycle = ready_lifecycle()
        lifecycle.apply(Event("final", EventType.FINALIZATION, "Finalize", candidate_id="C1"))
        self.assertEqual(lifecycle.state.candidates["C1"].status, CandidateStatus.FINALIZED)
        lifecycle.apply(Event("revoke", EventType.INVALIDATION, "Verifier stale",
                              invalidates=["verifier"]))
        self.assertFalse(FinalizationGate().evaluate(lifecycle.state, "C1").allowed)
        self.assertNotEqual(lifecycle.state.candidates["C1"].status, CandidateStatus.FINALIZED)

    def test_timestamp_does_not_reorder_submitted_sequence(self) -> None:
        lifecycle = EvidenceLifecycle()
        lifecycle.replay([
            Event("newer", EventType.OBSERVATION, "First submitted", timestamp="2026-09-16"),
            Event("older", EventType.OBSERVATION, "Second submitted", timestamp="2026-01-01"),
        ])
        self.assertEqual([event.id for event in lifecycle.state.events], ["newer", "older"])


if __name__ == "__main__":
    unittest.main()
