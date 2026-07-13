#!/usr/bin/env python3
"""Run the local SoftwareX release checks and write an auditable report."""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]


def public_text(value: str) -> str:
    return value.replace(str(ROOT), "<repo>").replace(ROOT.as_posix(), "<repo>")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run_check(
    check_id: str,
    command: list[str],
    expected_codes: set[int] | None = None,
) -> dict[str, Any]:
    expected = expected_codes or {0}
    completed = subprocess.run(
        command,
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    return {
        "check_id": check_id,
        "command": [public_text(item) for item in command],
        "return_code": completed.returncode,
        "expected_return_codes": sorted(expected),
        "passed": completed.returncode in expected,
        "stdout": public_text(completed.stdout[-8000:]),
        "stderr": public_text(completed.stderr[-8000:]),
    }


def source_manifest() -> list[dict[str, Any]]:
    files: list[Path] = []
    for folder in ["src", "tests", "examples", "schemas", "docs", "tools"]:
        files.extend(
            path
            for path in (ROOT / folder).rglob("*")
            if path.is_file()
            and "__pycache__" not in path.parts
            and path.suffix not in {".pyc", ".pyo"}
        )
    files.extend(
        ROOT / name
        for name in [
            "pyproject.toml",
            "README.md",
            "LICENSE.txt",
            "DATA_LICENSE.txt",
            "CITATION.cff",
            "codemeta.json",
        ]
    )
    return [
        {
            "path": path.relative_to(ROOT).as_posix(),
            "bytes": path.stat().st_size,
            "sha256": sha256(path),
        }
        for path in sorted(set(files))
    ]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", type=Path, default=ROOT / "validation")
    args = parser.parse_args()
    out_dir = args.out_dir.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    run_dir = out_dir / "run_outputs"
    run_dir.mkdir(parents=True, exist_ok=True)

    python = sys.executable
    ruff = shutil.which("ruff") or str(Path(python).with_name("ruff.exe"))
    checks = [
        run_check("SW-LINT", [ruff, "check", "src", "tests", "tools"]),
        run_check("SW-FORMAT", [ruff, "format", "--check", "src", "tests", "tools"]),
        run_check("SW-TEST", [python, "-m", "pytest"]),
        run_check("SW-BUILD", [python, "-m", "build"]),
        run_check(
            "SW-EXAMPLE-REPLACEMENT",
            [
                python,
                "-m",
                "bgvd_state",
                "replay",
                "--events",
                "examples/candidate_replacement/events.json",
                "--state-out",
                str(run_dir / "candidate_state.json"),
                "--handoff-out",
                str(run_dir / "candidate_handoff.json"),
            ],
        ),
        run_check(
            "SW-GATE-CURRENT",
            [
                python,
                "-m",
                "bgvd_state",
                "gate",
                "--state",
                str(run_dir / "candidate_state.json"),
                "--candidate",
                "C_CURRENT",
                "--out",
                str(run_dir / "candidate_gate.json"),
            ],
        ),
        run_check(
            "SW-EXAMPLE-STALE",
            [
                python,
                "-m",
                "bgvd_state",
                "replay",
                "--events",
                "examples/stale_verifier/events.json",
                "--state-out",
                str(run_dir / "stale_state.json"),
                "--handoff-out",
                str(run_dir / "stale_handoff.json"),
            ],
        ),
        run_check(
            "SW-GATE-STALE-REJECT",
            [
                python,
                "-m",
                "bgvd_state",
                "gate",
                "--state",
                str(run_dir / "stale_state.json"),
                "--candidate",
                "C_STALE",
                "--out",
                str(run_dir / "stale_gate.json"),
            ],
            expected_codes={2},
        ),
        run_check(
            "SW-RUNTIME-CASE",
            [
                python,
                "-m",
                "bgvd_state",
                "replay",
                "--events",
                "examples/discovery_runtime_case/events.json",
                "--state-out",
                str(run_dir / "runtime_case_state.json"),
                "--handoff-out",
                str(run_dir / "runtime_case_handoff.json"),
            ],
        ),
        run_check(
            "SW-RUNTIME-CASE-GATE",
            [
                python,
                "-m",
                "bgvd_state",
                "gate",
                "--state",
                str(run_dir / "runtime_case_state.json"),
                "--candidate",
                "CASE-C06",
                "--out",
                str(run_dir / "runtime_case_gate.json"),
            ],
            expected_codes={2},
        ),
        run_check(
            "SW-RUNTIME-ENGINEERING",
            [
                python,
                "tools/validate_runtime_engineering.py",
                "--out-dir",
                str(run_dir / "runtime_engineering"),
                "--repeats",
                "100",
            ],
        ),
        run_check(
            "ARTIFACT-REGRESSION",
            [
                python,
                "validate_structured_state_artifact.py",
                "--artifact",
                ".",
                "--out-dir",
                str(run_dir / "artifact_validation"),
            ],
        ),
    ]

    test_output = next(item["stdout"] for item in checks if item["check_id"] == "SW-TEST")
    match = re.search(r"(\d+) passed", test_output)
    report = {
        "schema_version": "bgvd.software_validation.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "PASS" if all(item["passed"] for item in checks) else "FAIL",
        "python": sys.version,
        "platform": platform.platform(),
        "test_count": int(match.group(1)) if match else None,
        "checks": checks,
        "source_manifest": source_manifest(),
    }
    json_path = out_dir / "software_validation_report.json"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# BGVD-State Software Validation Report",
        "",
        f"- Generated: `{report['generated_at']}`",
        f"- Status: **{report['status']}**",
        f"- Python: `{platform.python_version()}`",
        f"- Platform: `{report['platform']}`",
        f"- Tests passed: `{report['test_count']}`",
        "",
        "| Check | Return code | Expected | Status |",
        "|---|---:|---|---|",
    ]
    for item in checks:
        status = "PASS" if item["passed"] else "FAIL"
        lines.append(
            f"| `{item['check_id']}` | {item['return_code']} | "
            f"{item['expected_return_codes']} | {status} |"
        )
    lines.extend(
        [
            "",
            "The stale-verifier gate uses expected exit code `2`; that outcome is a passing",
            "negative-control check because unsupported finalization must be rejected.",
            "The complete runtime case also uses expected exit code `2` after a current",
            "negative scope verifier supersedes an earlier positive technical verifier.",
            "",
            f"Machine-readable report: `{json_path.name}`.",
        ]
    )
    md_path = out_dir / "SOFTWARE_VALIDATION_REPORT.md"
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(
        json.dumps({"status": report["status"], "json": str(json_path), "markdown": str(md_path)})
    )
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
