"""Command-line interface for replaying and inspecting defensive state."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .engine import EvidenceLifecycle
from .gate import FinalizationGate
from .handoff import HandoffBuilder
from .models import Event
from .store import atomic_write_text


def _read_events(path: Path) -> list[Event]:
    if path.suffix.lower() == ".jsonl":
        items = [
            json.loads(line)
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
    else:
        data: Any = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            items = data.get("events", [])
        elif isinstance(data, list):
            items = data
        else:
            raise ValueError("events file must contain a JSON array or an object with events[]")
    return [Event.from_dict(item) for item in items]


def _write_json(path: Path | None, value: dict[str, Any]) -> None:
    text = json.dumps(value, ensure_ascii=False, indent=2) + "\n"
    if path:
        atomic_write_text(path, text)
    else:
        print(text, end="")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="bgvd-state",
        description="Deterministic evidence-lifecycle middleware for defensive LLM agents.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    replay = sub.add_parser("replay", help="Replay events into state and a handoff packet.")
    replay.add_argument("--events", required=True, type=Path)
    replay.add_argument("--state-out", type=Path)
    replay.add_argument("--handoff-out", type=Path)

    gate = sub.add_parser("gate", help="Evaluate whether a candidate may be finalized.")
    gate.add_argument("--state", required=True, type=Path)
    gate.add_argument("--candidate", required=True)
    gate.add_argument("--out", type=Path)

    handoff = sub.add_parser("handoff", help="Build a handoff packet from saved state.")
    handoff.add_argument("--state", required=True, type=Path)
    handoff.add_argument("--out", type=Path)

    summary = sub.add_parser("summary", help="Print a concise runtime-state summary.")
    summary.add_argument("--state", required=True, type=Path)
    return parser


def _print_summary(lifecycle: EvidenceLifecycle) -> None:
    packet = HandoffBuilder().build(lifecycle.state)
    allowed = packet["finalization_allowed_for"]
    print("BGVD-State Runtime Summary")
    print(f"Events loaded: {len(lifecycle.state.events)}")
    print(f"Candidates: {len(lifecycle.state.candidates)}")
    print(f"Rejected candidates: {len(packet['rejected_candidates'])}")
    print(f"Failed paths: {len(packet['failed_paths'])}")
    print(f"Frontier items: {len(packet['frontier'])}")
    print(f"Finalization allowed: {', '.join(allowed) if allowed else 'none'}")


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "replay":
        lifecycle = EvidenceLifecycle()
        lifecycle.replay(_read_events(args.events))
        if args.state_out:
            lifecycle.save(args.state_out)
        packet = HandoffBuilder().build(lifecycle.state)
        _write_json(args.handoff_out, packet)
        return 0
    if args.command == "gate":
        lifecycle = EvidenceLifecycle.load(args.state)
        decision = FinalizationGate().evaluate(lifecycle.state, args.candidate)
        _write_json(args.out, decision.to_dict())
        return 0 if decision.allowed else 2
    if args.command == "handoff":
        lifecycle = EvidenceLifecycle.load(args.state)
        _write_json(args.out, HandoffBuilder().build(lifecycle.state))
        return 0
    if args.command == "summary":
        _print_summary(EvidenceLifecycle.load(args.state))
        return 0
    raise AssertionError(f"unhandled command: {args.command}")
