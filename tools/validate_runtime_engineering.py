from __future__ import annotations

import argparse
import hashlib
import json
import platform
import tempfile
from pathlib import Path
from typing import Any

from bgvd_state import EvidenceLifecycle, Event, EventStore, FinalizationGate, HandoffBuilder


ROOT = Path(__file__).resolve().parents[1]


def canonical_hash(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def load_events(path: Path) -> list[Event]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return [Event.from_dict(item) for item in data]


def build_outputs(events: list[Event]) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    lifecycle = EvidenceLifecycle()
    lifecycle.replay(events)
    state = lifecycle.state.to_dict()
    handoff = HandoffBuilder().build(lifecycle.state)
    gate = FinalizationGate().evaluate(lifecycle.state, "CASE-C06").to_dict()
    return state, handoff, gate


def validate(out_dir: Path, repeats: int) -> dict[str, Any]:
    case_path = ROOT / "examples" / "discovery_runtime_case" / "events.json"
    events = load_events(case_path)
    hashes = {"state": set(), "handoff": set(), "gate": set()}
    reference: tuple[dict[str, Any], dict[str, Any], dict[str, Any]] | None = None

    for _ in range(repeats):
        outputs = build_outputs(events)
        reference = reference or outputs
        for name, value in zip(hashes, outputs, strict=True):
            hashes[name].add(canonical_hash(value))

    assert reference is not None
    full_state, full_handoff, full_gate = reference

    with tempfile.TemporaryDirectory() as tmp:
        checkpoint = Path(tmp) / "checkpoint.json"
        split = len(events) // 2
        resumed = EvidenceLifecycle()
        resumed.replay(events[:split])
        resumed.save(checkpoint)
        resumed = EvidenceLifecycle.load(checkpoint)
        resumed.replay(events[split:])
        resumed_state = resumed.state.to_dict()
        resumed_handoff = HandoffBuilder().build(resumed.state)
        resumed_gate = FinalizationGate().evaluate(resumed.state, "CASE-C06").to_dict()

        malformed = Path(tmp) / "malformed.jsonl"
        malformed.write_text(
            '{"id":"VALID","type":"observation","summary":"Valid event."}\nnot-json\n',
            encoding="utf-8",
        )
        malformed_rejected = False
        try:
            EventStore.from_jsonl(malformed)
        except ValueError as exc:
            malformed_rejected = "line 2" in str(exc)

    duplicate_rejected = False
    try:
        EventStore([events[0], events[0]])
    except ValueError as exc:
        duplicate_rejected = "duplicate event id" in str(exc)

    compatibility_path = ROOT / "tests" / "fixtures" / "v1_state.json"
    compatible = EvidenceLifecycle.load(compatibility_path)
    compatible_packet = HandoffBuilder().build(compatible.state)

    checks = {
        "deterministic_replay": all(len(values) == 1 for values in hashes.values()),
        "checkpoint_state_equivalence": resumed_state == full_state,
        "checkpoint_handoff_equivalence": resumed_handoff == full_handoff,
        "checkpoint_gate_equivalence": resumed_gate == full_gate,
        "duplicate_event_rejected": duplicate_rejected,
        "malformed_jsonl_rejected": malformed_rejected,
        "v1_state_loads": compatible.state.schema_version == "bgvd.state.v1",
        "v1_handoff_builds": bool(compatible_packet.get("active_candidates")),
        "case_finalization_blocked": full_gate["allowed"] is False,
    }
    status = "PASS" if all(checks.values()) else "FAIL"
    result = {
        "status": status,
        "runtime_version": "1.1.1",
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
        },
        "case": {
            "events": len(full_state["events"]),
            "candidates": len(full_state["candidates"]),
            "failed_paths": len(full_state["failed_paths"]),
            "finalization_allowed_for": full_handoff["finalization_allowed_for"],
            "gate_reasons": full_gate["reasons"],
        },
        "determinism": {
            "repeats": repeats,
            "unique_state_hashes": len(hashes["state"]),
            "unique_handoff_hashes": len(hashes["handoff"]),
            "unique_gate_hashes": len(hashes["gate"]),
            "state_sha256": next(iter(hashes["state"])),
            "handoff_sha256": next(iter(hashes["handoff"])),
            "gate_sha256": next(iter(hashes["gate"])),
        },
        "checks": checks,
    }

    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "runtime_engineering_validation.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    lines = [
        "# Runtime Engineering Validation",
        "",
        f"Status: **{status}**",
        "",
        f"- Deterministic replays: {repeats}",
        f"- Events: {result['case']['events']}",
        f"- Candidates: {result['case']['candidates']}",
        f"- Failed paths: {result['case']['failed_paths']}",
        f"- Finalization allowed for: {result['case']['finalization_allowed_for'] or 'none'}",
        "",
        "## Checks",
        "",
        *[f"- {name}: {'PASS' if passed else 'FAIL'}" for name, passed in checks.items()],
    ]
    (out_dir / "RUNTIME_ENGINEERING_VALIDATION.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", type=Path, default=ROOT / "validation" / "runtime")
    parser.add_argument("--repeats", type=int, default=100)
    args = parser.parse_args()
    result = validate(args.out_dir, args.repeats)
    print(json.dumps({"status": result["status"], "out_dir": str(args.out_dir)}))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
