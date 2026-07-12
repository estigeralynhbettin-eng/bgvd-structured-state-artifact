"""Serializable state objects used by the deterministic evidence lifecycle."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


class EventType(str, Enum):
    TOOL_CALL = "tool_call"
    OBSERVATION = "observation"
    HYPOTHESIS = "hypothesis"
    MATERIAL_EVIDENCE = "material_evidence"
    VERIFIER_RESULT = "verifier_result"
    INVALIDATION = "invalidation"
    FAILED_PATH = "failed_path"
    CANDIDATE_UPDATE = "candidate_update"
    FINALIZATION = "finalization"


class CandidateStatus(str, Enum):
    PROPOSED = "proposed"
    ACTIVE = "active"
    PARTIAL_EVIDENCE = "partial_evidence"
    VERIFIED = "verified"
    REJECTED = "rejected"
    SUPERSEDED = "superseded"
    FINALIZED = "finalized"


@dataclass(slots=True)
class Event:
    id: str
    type: EventType
    summary: str
    candidate_id: str | None = None
    timestamp: str | None = None
    refs: list[str] = field(default_factory=list)
    invalidates: list[str] = field(default_factory=list)
    verifier_status: bool | None = None
    outcome: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Event":
        event_id = str(data.get("id") or data.get("event_id") or "").strip()
        raw_type = data.get("type") or data.get("event_type") or data.get("kind")
        type_aliases = {
            "material_trace": EventType.MATERIAL_EVIDENCE,
            "terminal_verifier": EventType.VERIFIER_RESULT,
            "worker_note": EventType.HYPOTHESIS,
            "duplicate_worker_output": EventType.CANDIDATE_UPDATE,
            "superseding_check": EventType.CANDIDATE_UPDATE,
            "noise": EventType.OBSERVATION,
            "tool_observation": EventType.OBSERVATION,
            "verifier": EventType.VERIFIER_RESULT,
        }
        event_type = type_aliases.get(str(raw_type), raw_type)
        status = data.get("verifier_status", data.get("status"))
        if isinstance(status, str):
            lowered = status.lower()
            status = True if lowered == "true" else False if lowered == "false" else None
        candidate_id = data.get("candidate_id", data.get("candidate"))
        if candidate_id in {"NONE", "null", ""}:
            candidate_id = None
        return cls(
            id=event_id,
            type=EventType(event_type),
            summary=str(data.get("summary", "")).strip(),
            candidate_id=str(candidate_id) if candidate_id is not None else None,
            timestamp=data.get("timestamp") or data.get("time"),
            refs=[str(item) for item in data.get("refs", [])],
            invalidates=[str(item) for item in data.get("invalidates", [])],
            verifier_status=status if isinstance(status, bool) else None,
            outcome=data.get("outcome"),
            metadata=dict(data.get("metadata", {})),
        )

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["type"] = self.type.value
        return data


@dataclass(slots=True)
class FailedPath:
    event_id: str
    candidate_id: str | None
    summary: str
    reason: str
    refs: list[str] = field(default_factory=list)
    active: bool = True


@dataclass(slots=True)
class Candidate:
    id: str
    vulnerability_type: str | None = None
    target_object: str | None = None
    status: CandidateStatus = CandidateStatus.PROPOSED
    material_evidence_refs: list[str] = field(default_factory=list)
    verifier_refs: list[str] = field(default_factory=list)
    current_verifier_ref: str | None = None
    current_verifier_status: bool | None = None
    failed_refs: list[str] = field(default_factory=list)
    invalidated_refs: list[str] = field(default_factory=list)
    rejection_reason: str | None = None
    last_updated: str | None = None

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["status"] = self.status.value
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Candidate":
        copy = dict(data)
        copy["status"] = CandidateStatus(copy.get("status", CandidateStatus.PROPOSED.value))
        return cls(**copy)


@dataclass(slots=True)
class SecurityState:
    schema_version: str = "bgvd.state.v1"
    events: list[Event] = field(default_factory=list)
    candidates: dict[str, Candidate] = field(default_factory=dict)
    failed_paths: list[FailedPath] = field(default_factory=list)
    invalidated_event_ids: list[str] = field(default_factory=list)
    frontier: list[str] = field(default_factory=list)
    open_questions: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "events": [event.to_dict() for event in self.events],
            "candidates": {key: value.to_dict() for key, value in self.candidates.items()},
            "failed_paths": [asdict(path) for path in self.failed_paths],
            "invalidated_event_ids": list(self.invalidated_event_ids),
            "frontier": list(self.frontier),
            "open_questions": list(self.open_questions),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SecurityState":
        return cls(
            schema_version=str(data.get("schema_version", "bgvd.state.v1")),
            events=[Event.from_dict(item) for item in data.get("events", [])],
            candidates={
                str(key): Candidate.from_dict(value)
                for key, value in data.get("candidates", {}).items()
            },
            failed_paths=[FailedPath(**item) for item in data.get("failed_paths", [])],
            invalidated_event_ids=[str(item) for item in data.get("invalidated_event_ids", [])],
            frontier=[str(item) for item in data.get("frontier", [])],
            open_questions=[str(item) for item in data.get("open_questions", [])],
        )
