"""BGVD-State public API."""

from .engine import EvidenceLifecycle
from .gate import FinalizationDecision, FinalizationGate
from .handoff import HandoffBuilder
from .models import (
    Candidate,
    CandidateStatus,
    Event,
    EventType,
    FailedPath,
    SecurityState,
)
from .store import EventStore

__all__ = [
    "Candidate",
    "CandidateStatus",
    "EvidenceLifecycle",
    "Event",
    "EventStore",
    "EventType",
    "FailedPath",
    "FinalizationDecision",
    "FinalizationGate",
    "HandoffBuilder",
    "SecurityState",
]

__version__ = "0.1.0"
