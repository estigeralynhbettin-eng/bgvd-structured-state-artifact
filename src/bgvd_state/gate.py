"""Verifier-gated finalization policy."""

from __future__ import annotations

from dataclasses import asdict, dataclass

from .models import CandidateStatus, SecurityState


@dataclass(slots=True)
class FinalizationDecision:
    candidate_id: str
    allowed: bool
    reasons: list[str]
    material_evidence_refs: list[str]
    verifier_ref: str | None

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


class FinalizationGate:
    def evaluate(self, state: SecurityState, candidate_id: str) -> FinalizationDecision:
        candidate = state.candidates.get(candidate_id)
        if candidate is None:
            return FinalizationDecision(candidate_id, False, ["candidate_not_found"], [], None)

        current_material = [
            ref
            for ref in candidate.material_evidence_refs
            if ref not in state.invalidated_event_ids
        ]
        reasons: list[str] = []
        if not current_material:
            reasons.append("no_current_material_evidence")
        if not candidate.current_verifier_ref:
            reasons.append("no_current_verifier")
        elif candidate.current_verifier_ref in state.invalidated_event_ids:
            reasons.append("current_verifier_invalidated")
        elif candidate.current_verifier_status is not True:
            reasons.append("current_verifier_not_positive")
        if candidate.status in {CandidateStatus.REJECTED, CandidateStatus.SUPERSEDED}:
            reasons.append(f"candidate_status_{candidate.status.value}")

        return FinalizationDecision(
            candidate_id=candidate_id,
            allowed=not reasons,
            reasons=reasons,
            material_evidence_refs=current_material,
            verifier_ref=candidate.current_verifier_ref,
        )
