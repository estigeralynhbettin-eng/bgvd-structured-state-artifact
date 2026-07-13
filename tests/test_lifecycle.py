from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from bgvd_state import (
    CandidateStatus,
    EvidenceLifecycle,
    Event,
    EventStore,
    EventType,
    FinalizationGate,
    HandoffBuilder,
)


def event(
    event_id: str,
    event_type: EventType,
    candidate: str | None,
    summary: str,
    **kwargs: object,
) -> Event:
    return Event(event_id, event_type, summary, candidate_id=candidate, **kwargs)


class EvidenceLifecycleTests(unittest.TestCase):
    def test_current_material_and_positive_verifier_allow_finalization(self) -> None:
        lifecycle = EvidenceLifecycle()
        lifecycle.replay(
            [
                event("E0001", EventType.MATERIAL_EVIDENCE, "C1", "Current evidence."),
                event(
                    "E0002",
                    EventType.VERIFIER_RESULT,
                    "C1",
                    "Current positive verifier.",
                    verifier_status=True,
                ),
            ]
        )
        decision = FinalizationGate().evaluate(lifecycle.state, "C1")
        self.assertTrue(decision.allowed)
        self.assertEqual(decision.material_evidence_refs, ["E0001"])
        self.assertEqual(decision.verifier_ref, "E0002")
        self.assertEqual(lifecycle.state.candidates["C1"].status, CandidateStatus.VERIFIED)

    def test_invalidated_verifier_cannot_be_reused(self) -> None:
        lifecycle = EvidenceLifecycle()
        lifecycle.replay(
            [
                event("E0001", EventType.MATERIAL_EVIDENCE, "C1", "Current evidence."),
                event(
                    "E0002",
                    EventType.VERIFIER_RESULT,
                    "C1",
                    "Positive verifier.",
                    verifier_status=True,
                ),
                event(
                    "E0003",
                    EventType.INVALIDATION,
                    "C1",
                    "Verifier becomes stale.",
                    invalidates=["E0002"],
                ),
            ]
        )
        decision = FinalizationGate().evaluate(lifecycle.state, "C1")
        self.assertFalse(decision.allowed)
        self.assertIn("no_current_verifier", decision.reasons)
        self.assertIn("E0002", lifecycle.state.invalidated_event_ids)

    def test_latest_negative_verifier_blocks_earlier_positive(self) -> None:
        lifecycle = EvidenceLifecycle()
        lifecycle.replay(
            [
                event("E0001", EventType.MATERIAL_EVIDENCE, "C1", "Current evidence."),
                event(
                    "E0002",
                    EventType.VERIFIER_RESULT,
                    "C1",
                    "Earlier positive verifier.",
                    verifier_status=True,
                ),
                event(
                    "E0003",
                    EventType.VERIFIER_RESULT,
                    "C1",
                    "Current negative verifier.",
                    verifier_status=False,
                ),
            ]
        )
        decision = FinalizationGate().evaluate(lifecycle.state, "C1")
        self.assertFalse(decision.allowed)
        self.assertEqual(decision.verifier_ref, "E0003")
        self.assertIn("current_verifier_not_positive", decision.reasons)

    def test_candidate_replacement_does_not_inherit_old_evidence(self) -> None:
        lifecycle = EvidenceLifecycle()
        lifecycle.replay(
            [
                event("E0001", EventType.MATERIAL_EVIDENCE, "OLD", "Old evidence."),
                event(
                    "E0002",
                    EventType.VERIFIER_RESULT,
                    "OLD",
                    "Old verifier.",
                    verifier_status=True,
                ),
                event(
                    "E0003",
                    EventType.INVALIDATION,
                    "OLD",
                    "Reset old candidate.",
                    invalidates=["E0001", "E0002"],
                ),
                event("E0004", EventType.MATERIAL_EVIDENCE, "NEW", "New evidence."),
                event(
                    "E0005",
                    EventType.VERIFIER_RESULT,
                    "NEW",
                    "New verifier.",
                    verifier_status=True,
                ),
            ]
        )
        gate = FinalizationGate()
        self.assertFalse(gate.evaluate(lifecycle.state, "OLD").allowed)
        self.assertTrue(gate.evaluate(lifecycle.state, "NEW").allowed)
        packet = HandoffBuilder().build(lifecycle.state)
        self.assertEqual([item["id"] for item in packet["active_candidates"]], ["NEW"])
        self.assertEqual([item["id"] for item in packet["superseded_candidates"]], ["OLD"])

    def test_failed_path_remains_in_handoff(self) -> None:
        lifecycle = EvidenceLifecycle()
        lifecycle.apply(
            event(
                "E0001",
                EventType.FAILED_PATH,
                "C1",
                "A candidate path was rejected by the defensive verifier.",
                metadata={"reason": "negative_control_failed"},
            )
        )
        packet = HandoffBuilder().build(lifecycle.state)
        self.assertEqual(packet["failed_paths"][0]["reason"], "negative_control_failed")
        self.assertEqual(packet["rejected_candidates"][0]["id"], "C1")

    def test_finalization_event_cannot_bypass_gate(self) -> None:
        lifecycle = EvidenceLifecycle()
        lifecycle.apply(event("E0001", EventType.FINALIZATION, "C1", "Request finalization."))

        candidate = lifecycle.state.candidates["C1"]
        self.assertNotEqual(candidate.status, CandidateStatus.FINALIZED)
        self.assertFalse(FinalizationGate().evaluate(lifecycle.state, "C1").allowed)

    def test_candidate_update_cannot_bypass_finalization_gate(self) -> None:
        lifecycle = EvidenceLifecycle()
        lifecycle.apply(
            event(
                "E0001",
                EventType.CANDIDATE_UPDATE,
                "C1",
                "Request finalized status.",
                metadata={"status": "finalized"},
            )
        )

        self.assertNotEqual(lifecycle.state.candidates["C1"].status, CandidateStatus.FINALIZED)
        self.assertFalse(FinalizationGate().evaluate(lifecycle.state, "C1").allowed)

    def test_gated_finalization_remains_visible_in_handoff(self) -> None:
        lifecycle = EvidenceLifecycle()
        lifecycle.replay(
            [
                event("E0001", EventType.MATERIAL_EVIDENCE, "C1", "Current evidence."),
                event(
                    "E0002",
                    EventType.VERIFIER_RESULT,
                    "C1",
                    "Current positive verifier.",
                    verifier_status=True,
                ),
                event("E0003", EventType.FINALIZATION, "C1", "Finalize verified candidate."),
            ]
        )

        self.assertEqual(lifecycle.state.candidates["C1"].status, CandidateStatus.FINALIZED)
        packet = HandoffBuilder().build(lifecycle.state)
        self.assertEqual([item["id"] for item in packet["finalized_candidates"]], ["C1"])
        self.assertEqual(packet["finalization_allowed_for"], ["C1"])

    def test_state_round_trip_preserves_gate_decision(self) -> None:
        lifecycle = EvidenceLifecycle()
        lifecycle.replay(
            [
                event("E0001", EventType.MATERIAL_EVIDENCE, "C1", "Current evidence."),
                event(
                    "E0002",
                    EventType.VERIFIER_RESULT,
                    "C1",
                    "Current positive verifier.",
                    verifier_status=True,
                ),
            ]
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "state.json"
            lifecycle.save(path)
            loaded = EvidenceLifecycle.load(path)
        self.assertTrue(FinalizationGate().evaluate(loaded.state, "C1").allowed)

    def test_event_store_rejects_duplicate_ids(self) -> None:
        store = EventStore()
        item = event("E0001", EventType.OBSERVATION, None, "Observed state.")
        store.append(item)
        with self.assertRaisesRegex(ValueError, "duplicate event id"):
            store.append(item)

    def test_checkpoint_resume_matches_uninterrupted_replay(self) -> None:
        items = [
            event("E0001", EventType.HYPOTHESIS, "C1", "Candidate proposed."),
            event("E0002", EventType.MATERIAL_EVIDENCE, "C1", "Evidence recorded."),
            event(
                "E0003",
                EventType.VERIFIER_RESULT,
                "C1",
                "Positive verifier.",
                verifier_status=True,
            ),
            event(
                "E0004",
                EventType.INVALIDATION,
                "C1",
                "Verifier invalidated.",
                invalidates=["E0003"],
            ),
            event(
                "E0005",
                EventType.VERIFIER_RESULT,
                "C1",
                "Current negative verifier.",
                verifier_status=False,
            ),
        ]
        uninterrupted = EvidenceLifecycle()
        uninterrupted.replay(items)

        with tempfile.TemporaryDirectory() as tmp:
            checkpoint = Path(tmp) / "checkpoint.json"
            resumed = EvidenceLifecycle()
            resumed.replay(items[:3])
            resumed.save(checkpoint)
            resumed = EvidenceLifecycle.load(checkpoint)
            resumed.replay(items[3:])

        self.assertEqual(resumed.state.to_dict(), uninterrupted.state.to_dict())
        self.assertEqual(
            HandoffBuilder().build(resumed.state),
            HandoffBuilder().build(uninterrupted.state),
        )

    def test_event_store_reports_malformed_jsonl_line(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "events.jsonl"
            path.write_text(
                '{"id":"E0001","type":"observation","summary":"Valid event."}\nnot-json\n',
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "line 2"):
                EventStore.from_jsonl(path)

    def test_example_aliases_are_supported(self) -> None:
        raw = {
            "id": "E0001",
            "kind": "terminal_verifier",
            "candidate": "C1",
            "status": "true",
            "summary": "A redacted terminal verifier result.",
        }
        parsed = Event.from_dict(json.loads(json.dumps(raw)))
        self.assertEqual(parsed.type, EventType.VERIFIER_RESULT)
        self.assertTrue(parsed.verifier_status)


if __name__ == "__main__":
    unittest.main()
