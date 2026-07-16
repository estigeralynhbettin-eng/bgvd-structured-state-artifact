from __future__ import annotations

import argparse
import csv
import hashlib
import json
import platform
import statistics
import time
import tracemalloc
from pathlib import Path
from typing import Any

from bgvd_state import EvidenceLifecycle, Event, EventType, HandoffBuilder


ROOT = Path(__file__).resolve().parents[1]


def make_events(count: int, candidate_count: int) -> list[Event]:
    events: list[Event] = []
    for index in range(count):
        candidate_index = index % candidate_count
        candidate_id = f"BENCH-C{candidate_index:04d}"
        if index < candidate_count:
            event_type = EventType.HYPOTHESIS
            summary = "Candidate proposed for deterministic runtime benchmarking."
            verifier_status = None
        elif index < candidate_count * 2:
            event_type = EventType.MATERIAL_EVIDENCE
            summary = "Material benchmark evidence recorded."
            verifier_status = None
        elif index < candidate_count * 3:
            event_type = EventType.VERIFIER_RESULT
            summary = "Positive benchmark verifier recorded."
            verifier_status = True
        else:
            event_type = EventType.OBSERVATION
            summary = "Additional ordered benchmark observation."
            verifier_status = None
        events.append(
            Event(
                id=f"BENCH-E{index:07d}",
                type=event_type,
                summary=summary,
                candidate_id=candidate_id,
                verifier_status=verifier_status,
            )
        )
    return events


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )


def run_once(event_count: int, candidate_count: int) -> dict[str, Any]:
    tracemalloc.start()
    total_start = time.perf_counter()
    events = make_events(event_count, candidate_count)
    lifecycle = EvidenceLifecycle()
    replay_start = time.perf_counter()
    lifecycle.replay(events)
    replay_seconds = time.perf_counter() - replay_start
    handoff = HandoffBuilder().build(lifecycle.state)
    state_bytes = canonical_bytes(lifecycle.state.to_dict())
    handoff_bytes = canonical_bytes(handoff)
    total_seconds = time.perf_counter() - total_start
    _, peak_bytes = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return {
        "replay_seconds": replay_seconds,
        "total_seconds": total_seconds,
        "peak_memory_mib": peak_bytes / (1024 * 1024),
        "state_bytes": len(state_bytes),
        "handoff_bytes": len(handoff_bytes),
        "state_sha256": hashlib.sha256(state_bytes).hexdigest(),
        "handoff_sha256": hashlib.sha256(handoff_bytes).hexdigest(),
    }


def benchmark(sizes: list[int], repeats: int, candidate_count: int) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    raw: list[dict[str, Any]] = []
    for size in sizes:
        runs = [run_once(size, candidate_count) for _ in range(repeats)]
        for repeat, run in enumerate(runs, 1):
            raw.append({"events": size, "repeat": repeat, **run})
        rows.append(
            {
                "events": size,
                "candidates": candidate_count,
                "repeats": repeats,
                "median_replay_seconds": statistics.median(run["replay_seconds"] for run in runs),
                "stdev_replay_seconds": statistics.pstdev(run["replay_seconds"] for run in runs),
                "median_total_seconds": statistics.median(run["total_seconds"] for run in runs),
                "median_peak_memory_mib": statistics.median(run["peak_memory_mib"] for run in runs),
                "state_bytes": runs[0]["state_bytes"],
                "handoff_bytes": runs[0]["handoff_bytes"],
                "unique_state_hashes": len({run["state_sha256"] for run in runs}),
                "unique_handoff_hashes": len({run["handoff_sha256"] for run in runs}),
            }
        )
    return {
        "status": "PASS"
        if all(row["unique_state_hashes"] == row["unique_handoff_hashes"] == 1 for row in rows)
        else "FAIL",
        "runtime_version": "1.1.1",
        "profile": "fixed_candidate_count",
        "candidate_count": candidate_count,
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "processor": platform.processor(),
        },
        "summary": rows,
        "raw_runs": raw,
    }


def write_outputs(result: dict[str, Any], out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "runtime_benchmark.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    with (out_dir / "runtime_benchmark.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(result["summary"][0]))
        writer.writeheader()
        writer.writerows(result["summary"])
    lines = [
        "# Runtime Performance Benchmark",
        "",
        f"Status: **{result['status']}**",
        "",
        "The benchmark uses a fixed number of concurrent candidates. It characterizes event-volume scaling and does not establish scaling to an unbounded number of candidates.",
        "",
        "| Events | Median replay (s) | Median total (s) | Peak MiB | State bytes |",
        "|---:|---:|---:|---:|---:|",
    ]
    for row in result["summary"]:
        lines.append(
            f"| {row['events']} | {row['median_replay_seconds']:.6f} | "
            f"{row['median_total_seconds']:.6f} | {row['median_peak_memory_mib']:.2f} | "
            f"{row['state_bytes']} |"
        )
    (out_dir / "RUNTIME_BENCHMARK.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sizes", nargs="+", type=int, default=[100, 1000, 10000, 100000])
    parser.add_argument("--repeats", type=int, default=5)
    parser.add_argument("--candidates", type=int, default=6)
    parser.add_argument("--out-dir", type=Path, default=ROOT / "validation" / "runtime")
    args = parser.parse_args()
    result = benchmark(args.sizes, args.repeats, args.candidates)
    write_outputs(result, args.out_dir)
    print(json.dumps({"status": result["status"], "out_dir": str(args.out_dir)}))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
