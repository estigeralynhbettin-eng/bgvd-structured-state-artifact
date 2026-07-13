"""Append-only event storage with deterministic JSON persistence."""

from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile
from typing import Iterable

from .models import Event


def atomic_write_text(path: str | Path, text: str) -> None:
    """Atomically replace a UTF-8 text file after flushing its temporary copy."""

    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{target.name}.", suffix=".tmp", dir=target.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, target)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise


class EventStore:
    def __init__(self, events: Iterable[Event] | None = None) -> None:
        self._events: list[Event] = []
        self._ids: set[str] = set()
        for event in events or []:
            self.append(event)

    @property
    def events(self) -> list[Event]:
        return list(self._events)

    def append(self, event: Event) -> Event:
        if not event.id:
            raise ValueError("event id must not be empty")
        if event.id in self._ids:
            raise ValueError(f"duplicate event id: {event.id}")
        if not event.summary:
            raise ValueError(f"event {event.id} must have a summary")
        self._events.append(event)
        self._ids.add(event.id)
        return event

    def get(self, event_id: str) -> Event | None:
        return next((event for event in self._events if event.id == event_id), None)

    def to_jsonl(self, path: str | Path) -> None:
        text = "\n".join(json.dumps(event.to_dict(), ensure_ascii=False) for event in self._events)
        atomic_write_text(path, text + ("\n" if text else ""))

    @classmethod
    def from_jsonl(cls, path: str | Path) -> "EventStore":
        events: list[Event] = []
        for line_no, raw in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), 1):
            if not raw.strip():
                continue
            try:
                events.append(Event.from_dict(json.loads(raw)))
            except (json.JSONDecodeError, TypeError, ValueError) as exc:
                raise ValueError(f"invalid event JSONL at line {line_no}: {exc}") from exc
        return cls(events)
