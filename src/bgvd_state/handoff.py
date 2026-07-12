"""Build compact, model-independent handoff packets."""

from __future__ import annotations

from typing import Any

from .gate import FinalizationGate
from .models import CandidateStatus, SecurityState


class HandoffBuilder:
    def __init__(self, gate: FinalizationGate | None = None) -> None:
        self.gate = gate or FinalizationGate()

    def build(self, state: SecurityState) -> dict[str, Any]:
        candidates: list[dict[str, Any]] = []
        allowed: list[str] = []
        for candidate in state.candidates.values():
            decision = self.gate.evaluate(state, candidate.id)
            if decision.allowed:
                allowed.append(candidate.id)
            candidates.append(
                {
                    "id": candidate.id,
                    "status": candidate.status.value,
                    "vulnerability_type": candidate.vulnerability_type,
                    "target_object": candidate.target_object,
                    "current_material_evidence_refs": decision.material_evidence_refs,
                    "current_verifier_ref": candidate.current_verifier_ref,
                    "current_verifier_status": candidate.current_verifier_status,
                    "invalidated_refs": list(candidate.invalidated_refs),
                    "failed_refs": list(candidate.failed_refs),
                    "finalization_allowed": decision.allowed,
                    "gate_reasons": decision.reasons,
                }
            )

        return {
            "schema_version": "bgvd.handoff.v1",
            "active_candidates": [
                item
                for item in candidates
                if item["status"]
                not in {
                    CandidateStatus.REJECTED.value,
                    CandidateStatus.SUPERSEDED.value,
                    CandidateStatus.FINALIZED.value,
                }
            ],
            "rejected_candidates": [
                item for item in candidates if item["status"] == CandidateStatus.REJECTED.value
            ],
            "superseded_candidates": [
                item for item in candidates if item["status"] == CandidateStatus.SUPERSEDED.value
            ],
            "finalized_candidates": [
                item for item in candidates if item["status"] == CandidateStatus.FINALIZED.value
            ],
            "failed_paths": [
                {
                    "event_id": path.event_id,
                    "candidate_id": path.candidate_id,
                    "reason": path.reason,
                    "refs": path.refs,
                }
                for path in state.failed_paths
                if path.active
            ],
            "invalidated_event_ids": list(state.invalidated_event_ids),
            "frontier": list(state.frontier),
            "open_questions": list(state.open_questions),
            "finalization_allowed_for": allowed,
        }
