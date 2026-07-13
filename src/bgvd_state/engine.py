"""Deterministic security evidence-lifecycle state transitions."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from .gate import FinalizationGate
from .models import Candidate, CandidateStatus, Event, EventType, FailedPath, SecurityState
from .store import EventStore, atomic_write_text


class EvidenceLifecycle:
    """Apply auditable event-to-state transitions for defensive agent handoff."""

    def __init__(self, state: SecurityState | None = None) -> None:
        self.state = state or SecurityState()
        self.store = EventStore(self.state.events)

    def apply(self, event: Event) -> SecurityState:
        self.store.append(event)
        self.state.events.append(event)
        self._apply_invalidations(event)
        candidate = self._candidate_for(event)

        if event.type is EventType.HYPOTHESIS and candidate:
            candidate.status = CandidateStatus.PROPOSED
        elif event.type is EventType.MATERIAL_EVIDENCE and candidate:
            self._add_unique(candidate.material_evidence_refs, event.id)
            candidate.status = CandidateStatus.PARTIAL_EVIDENCE
        elif event.type is EventType.VERIFIER_RESULT and candidate:
            self._add_unique(candidate.verifier_refs, event.id)
            candidate.current_verifier_ref = event.id
            candidate.current_verifier_status = event.verifier_status
            candidate.status = (
                CandidateStatus.VERIFIED
                if event.verifier_status is True and self._has_current_material(candidate)
                else CandidateStatus.PARTIAL_EVIDENCE
            )
        elif event.type is EventType.FAILED_PATH:
            reason = str(event.metadata.get("reason") or event.summary)
            self.state.failed_paths.append(
                FailedPath(event.id, event.candidate_id, event.summary, reason, list(event.refs))
            )
            if candidate:
                self._add_unique(candidate.failed_refs, event.id)
                candidate.status = CandidateStatus.REJECTED
                candidate.rejection_reason = reason
        elif event.type is EventType.CANDIDATE_UPDATE and candidate:
            requested = event.metadata.get("status")
            if requested:
                requested_status = CandidateStatus(str(requested))
                if (
                    requested_status is not CandidateStatus.FINALIZED
                    or FinalizationGate().evaluate(self.state, candidate.id).allowed
                ):
                    candidate.status = requested_status
        elif event.type is EventType.FINALIZATION and candidate:
            if FinalizationGate().evaluate(self.state, candidate.id).allowed:
                candidate.status = CandidateStatus.FINALIZED

        if candidate:
            candidate.last_updated = event.timestamp or event.id
            self._refresh_candidate_status(candidate)
        self._refresh_frontier()
        return self.state

    def replay(self, events: Iterable[Event]) -> SecurityState:
        for event in events:
            self.apply(event)
        return self.state

    def save(self, path: str | Path) -> None:
        atomic_write_text(
            path,
            json.dumps(self.state.to_dict(), ensure_ascii=False, indent=2) + "\n",
        )

    @classmethod
    def load(cls, path: str | Path) -> "EvidenceLifecycle":
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls(SecurityState.from_dict(data))

    def _candidate_for(self, event: Event) -> Candidate | None:
        if not event.candidate_id:
            return None
        candidate = self.state.candidates.get(event.candidate_id)
        if candidate is None:
            candidate = Candidate(
                id=event.candidate_id,
                vulnerability_type=event.metadata.get("vulnerability_type"),
                target_object=event.metadata.get("target_object"),
            )
            self.state.candidates[candidate.id] = candidate
        else:
            candidate.vulnerability_type = candidate.vulnerability_type or event.metadata.get(
                "vulnerability_type"
            )
            candidate.target_object = candidate.target_object or event.metadata.get("target_object")
        return candidate

    def _apply_invalidations(self, event: Event) -> None:
        for ref in event.invalidates:
            self._add_unique(self.state.invalidated_event_ids, ref)
            for candidate in self.state.candidates.values():
                if ref in candidate.material_evidence_refs or ref in candidate.verifier_refs:
                    self._add_unique(candidate.invalidated_refs, ref)
                    if candidate.current_verifier_ref == ref:
                        candidate.current_verifier_ref = None
                        candidate.current_verifier_status = None
                    candidate.status = CandidateStatus.SUPERSEDED

    def _refresh_candidate_status(self, candidate: Candidate) -> None:
        if candidate.status in {CandidateStatus.REJECTED, CandidateStatus.FINALIZED}:
            return
        has_material = self._has_current_material(candidate)
        verifier_true = (
            candidate.current_verifier_status is True
            and candidate.current_verifier_ref not in self.state.invalidated_event_ids
        )
        if has_material and verifier_true:
            candidate.status = CandidateStatus.VERIFIED
        elif has_material or candidate.current_verifier_ref:
            candidate.status = CandidateStatus.PARTIAL_EVIDENCE
        elif candidate.invalidated_refs:
            candidate.status = CandidateStatus.SUPERSEDED
        else:
            candidate.status = CandidateStatus.PROPOSED

    def _has_current_material(self, candidate: Candidate) -> bool:
        return any(
            ref not in self.state.invalidated_event_ids for ref in candidate.material_evidence_refs
        )

    def _refresh_frontier(self) -> None:
        frontier: list[str] = []
        for candidate in self.state.candidates.values():
            if candidate.status is CandidateStatus.PROPOSED:
                frontier.append(f"Collect material evidence for {candidate.id}.")
            elif candidate.status is CandidateStatus.PARTIAL_EVIDENCE:
                if not self._has_current_material(candidate):
                    frontier.append(
                        f"Replace stale or missing material evidence for {candidate.id}."
                    )
                elif candidate.current_verifier_status is not True:
                    frontier.append(
                        f"Obtain a current positive verifier result for {candidate.id}."
                    )
        self.state.frontier = frontier

    @staticmethod
    def _add_unique(items: list[str], value: str) -> None:
        if value not in items:
            items.append(value)
