"""No-install reviewer check for BGVD-State v1.1.1.

The script is launched by the private Python runtime included in each
platform-specific reviewer ZIP. It performs no installation, network access,
model call, service start, or system configuration change.
"""

from __future__ import annotations

import html
import json
import os
import platform
import shutil
import site
import subprocess
import sys
import tempfile
import textwrap
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "reviewer_output"
LOGS = OUTPUT / "logs"
PRIVATE_PYTHON = [sys.executable, "-I", "-s", "-X", "utf8"]


class CheckFailure(RuntimeError):
    """Raised when a reviewer check does not meet its expected result."""


def _private_environment() -> dict[str, str]:
    environment = dict(os.environ)
    environment.pop("PYTHONHOME", None)
    environment.pop("PYTHONPATH", None)
    environment["PYTHONNOUSERSITE"] = "1"
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    environment["PYTHONUTF8"] = "1"
    environment["PYTHONIOENCODING"] = "utf-8"
    return environment


def _write_log(
    name: str,
    command: Iterable[str],
    result: subprocess.CompletedProcess[str],
) -> None:
    LOGS.mkdir(parents=True, exist_ok=True)
    text = (
        "COMMAND\n"
        + " ".join(str(item) for item in command)
        + "\n\nRETURN CODE\n"
        + str(result.returncode)
        + "\n\nSTDOUT\n"
        + result.stdout
        + "\n\nSTDERR\n"
        + result.stderr
    )
    (LOGS / f"{name}.txt").write_text(text, encoding="utf-8")


def _run(
    name: str,
    command: list[str],
    *,
    cwd: Path = ROOT,
    expected_codes: tuple[int, ...] = (0,),
) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        command,
        cwd=cwd,
        env=_private_environment(),
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    _write_log(name, command, result)
    if result.returncode not in expected_codes:
        tail = "\n".join((result.stdout + "\n" + result.stderr).splitlines()[-20:])
        raise CheckFailure(
            f"{name} returned {result.returncode}; expected {expected_codes}.\n{tail}"
        )
    return result


def _copy_if_present(source: Path, destination: Path) -> None:
    if source.exists():
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)


def _normalized_machine(value: str) -> str:
    aliases = {
        "amd64": "x86_64",
        "x64": "x86_64",
        "x86_64": "x86_64",
        "aarch64": "arm64",
        "arm64": "arm64",
    }
    return aliases.get(value.strip().lower(), value.strip().lower())


def _check_runtime_identity() -> dict[str, object]:
    runtime_root = (ROOT / "runtime").resolve()
    executable = Path(sys.executable).resolve()
    if not executable.is_relative_to(runtime_root):
        raise CheckFailure("The check was not started with the bundled private runtime.")
    if (
        not sys.flags.isolated
        or not sys.flags.ignore_environment
        or not sys.flags.no_user_site
        or not sys.flags.utf8_mode
    ):
        raise CheckFailure("The bundled runtime did not start in the required isolated mode.")
    if site.ENABLE_USER_SITE is not False:
        raise CheckFailure("User-level Python packages were not disabled.")

    build_path = ROOT / "REVIEWER_KIT_BUILD.json"
    build = json.loads(build_path.read_text(encoding="utf-8"))
    expected_system = str(build["expected_system"])
    expected_machine = _normalized_machine(str(build["expected_machine"]))
    actual_system = platform.system()
    actual_machine = _normalized_machine(platform.machine())
    if actual_system != expected_system or actual_machine != expected_machine:
        raise CheckFailure(
            "This reviewer kit does not match the current computer: "
            f"expected {expected_system}/{expected_machine}, "
            f"found {actual_system}/{actual_machine}."
        )
    return build


def _write_summaries(payload: dict[str, object]) -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    (OUTPUT / "REVIEWER_CHECK_SUMMARY.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    checks = payload.get("checks", [])
    rows = "\n".join(
        f"- {item['label']}: **{item['status']}** - {item['detail']}"
        for item in checks
        if isinstance(item, dict)
    )
    markdown = f"""# BGVD-State Reviewer Check

Overall result: **{payload['status']}**

Generated: {payload['generated_at']}

## Checks

{rows}

## Clear Conclusion

A `PASS` confirms that the bundled software runs without installing Python or
packages, all 18 tests pass, the fixed 23-event case reconstructs six candidate
lifecycles, five rejected candidates and five failed paths remain visible,
unsupported finalization is blocked, and the offline artifact validator passes.

The gate exit code `2` is an expected evidence-gating decision, not a software
failure.

No internet connection, administrator permission, API key, model call,
container, service, or live target was used.

## Raw Logs

- `logs/01_runtime.txt`
- `logs/02_tests.txt`
- `logs/03_replay.txt`
- `logs/04_summary.txt`
- `logs/05_gate.txt`
- `logs/06_artifact_validator.txt`
"""
    (OUTPUT / "REVIEWER_CHECK_SUMMARY.md").write_text(markdown, encoding="utf-8")
    (OUTPUT / "REVIEWER_CHECK_SUMMARY.txt").write_text(
        markdown.replace("**", "").replace("`", ""),
        encoding="utf-8",
    )

    status = str(payload["status"])
    status_color = "#16794a" if status == "PASS" else "#b42318"
    cards = []
    for item in checks:
        if not isinstance(item, dict):
            continue
        cards.append(
            "<li><strong>{label}: {status}</strong><br>{detail}</li>".format(
                label=html.escape(str(item["label"])),
                status=html.escape(str(item["status"])),
                detail=html.escape(str(item["detail"])),
            )
        )
    html_text = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>BGVD-State Reviewer Check: {html.escape(status)}</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Arial, sans-serif; margin: 0; color: #182230; background: #f5f7fa; }}
    main {{ max-width: 860px; margin: 32px auto; padding: 0 20px 48px; }}
    .result {{ color: white; background: {status_color}; border-radius: 14px; padding: 30px; }}
    .result h1 {{ margin: 0 0 8px; font-size: 38px; }}
    .result p {{ margin: 0; font-size: 18px; }}
    section {{ background: white; border: 1px solid #d8dee8; border-radius: 12px; padding: 22px; margin-top: 18px; }}
    li {{ margin: 12px 0; line-height: 1.45; }}
    code {{ background: #eef2f6; padding: 2px 5px; border-radius: 4px; }}
    a {{ color: #175cd3; }}
    .note {{ color: #475467; }}
  </style>
</head>
<body>
<main>
  <div class="result">
    <h1>OVERALL RESULT: {html.escape(status)}</h1>
    <p>BGVD-State v1.1.1 no-install reviewer check</p>
  </div>
  <section>
    <h2>What was verified</h2>
    <ul>{''.join(cards)}</ul>
  </section>
  <section>
    <h2>Clear conclusion</h2>
    <p>A PASS confirms that the bundled software ran without installing Python
    or packages; all 18 tests passed; the fixed case replayed 23 events into 6
    candidate lifecycles; 5 rejected candidates and 5 failed paths remained
    visible; unsupported finalization was blocked; and the offline artifact
    validator passed.</p>
    <p>The gate exit code <code>2</code> is the expected safety decision, not a
    software failure.</p>
    <p class="note">No internet connection, administrator permission, API key,
    model call, container, service, or live target was used.</p>
  </section>
  <section>
    <h2>Raw logs</h2>
    <ul>
      <li><a href="logs/01_runtime.txt">Bundled runtime</a></li>
      <li><a href="logs/02_tests.txt">18 automated tests</a></li>
      <li><a href="logs/03_replay.txt">Case replay</a></li>
      <li><a href="logs/04_summary.txt">Runtime summary</a></li>
      <li><a href="logs/05_gate.txt">Evidence-gate decision</a></li>
      <li><a href="logs/06_artifact_validator.txt">Artifact validation</a></li>
    </ul>
    <p><a href="REVIEWER_CHECK_SUMMARY.json">Machine-readable JSON summary</a></p>
  </section>
</main>
</body>
</html>
"""
    (OUTPUT / "REVIEWER_CHECK_SUMMARY.html").write_text(html_text, encoding="utf-8")


def main() -> int:
    print("BGVD-State v1.1.1 No-Install Reviewer Check")
    print("=" * 47)
    print("Nothing will be installed or added to the system.")
    print("No internet connection or administrator permission is needed.")
    print()

    if OUTPUT.exists():
        shutil.rmtree(OUTPUT)
    OUTPUT.mkdir(parents=True, exist_ok=True)
    LOGS.mkdir(parents=True, exist_ok=True)
    temporary_root = Path(tempfile.mkdtemp(prefix="bgvd_state_reviewer_"))
    work_dir = temporary_root / "work"
    work_dir.mkdir(parents=True, exist_ok=True)
    checks: list[dict[str, str]] = []

    try:
        print("[1/5] Checking the bundled private runtime...")
        build = _check_runtime_identity()
        _run(
            "01_runtime",
            PRIVATE_PYTHON
            + [
                "-c",
                (
                    "import importlib.metadata, json, pathlib, site, sys; "
                    "print(json.dumps({"
                    "'python': sys.version, "
                    "'executable': sys.executable, "
                    "'isolated': sys.flags.isolated, "
                    "'ignore_environment': sys.flags.ignore_environment, "
                    "'no_user_site': sys.flags.no_user_site, "
                    "'utf8_mode': sys.flags.utf8_mode, "
                    "'user_site_enabled': site.ENABLE_USER_SITE, "
                    "'jsonschema': importlib.metadata.version('jsonschema'), "
                    "'path': sys.path"
                    "}, indent=2))"
                ),
            ],
        )
        checks.append(
            {
                "label": "No-install runtime",
                "status": "PASS",
                "detail": (
                    "The private bundled runtime and schema dependency loaded locally "
                    f"for {build['platform_key']}."
                ),
            }
        )

        print("[2/5] Running the 18 unit and integration tests...")
        tests = _run(
            "02_tests",
            PRIVATE_PYTHON + ["-m", "unittest", "discover", "-s", "tests", "-v"],
        )
        combined_test_output = tests.stdout + "\n" + tests.stderr
        if "Ran 18 tests" not in combined_test_output or "\nOK" not in combined_test_output:
            raise CheckFailure("The test command returned success but did not report 18 tests and OK.")
        checks.append(
            {
                "label": "Automated tests",
                "status": "PASS",
                "detail": "18 tests completed with OK.",
            }
        )

        print("[3/5] Replaying the fixed 23-event case...")
        state = work_dir / "state.json"
        handoff = work_dir / "handoff.json"
        gate = work_dir / "gate.json"
        events = ROOT / "examples" / "discovery_runtime_case" / "events.json"
        _run(
            "03_replay",
            PRIVATE_PYTHON
            + [
                "-m",
                "bgvd_state",
                "replay",
                "--events",
                str(events),
                "--state-out",
                str(state),
                "--handoff-out",
                str(handoff),
            ],
        )
        summary = _run(
            "04_summary",
            PRIVATE_PYTHON + ["-m", "bgvd_state", "summary", "--state", str(state)],
        )
        expected_summary = (
            "Events loaded: 23",
            "Candidates: 6",
            "Rejected candidates: 5",
            "Failed paths: 5",
            "Finalization allowed: none",
        )
        missing = [item for item in expected_summary if item not in summary.stdout]
        if missing:
            raise CheckFailure(f"Runtime summary is missing expected lines: {missing}")
        checks.append(
            {
                "label": "Runtime replay",
                "status": "PASS",
                "detail": "23 events, 6 candidates, 5 rejected candidates, and 5 failed paths.",
            }
        )

        print("[4/5] Checking the evidence gate...")
        _run(
            "05_gate",
            PRIVATE_PYTHON
            + [
                "-m",
                "bgvd_state",
                "gate",
                "--state",
                str(state),
                "--candidate",
                "CASE-C06",
                "--out",
                str(gate),
            ],
            expected_codes=(2,),
        )
        gate_payload = json.loads(gate.read_text(encoding="utf-8"))
        if gate_payload.get("allowed") is not False:
            raise CheckFailure("The evidence gate did not block unsupported finalization.")
        if "current_verifier_not_positive" not in gate_payload.get("reasons", []):
            raise CheckFailure("The gate result did not contain the expected reason.")
        checks.append(
            {
                "label": "Evidence gate",
                "status": "PASS",
                "detail": "Unsupported finalization was blocked with the expected exit code 2.",
            }
        )

        print("[5/5] Running the offline artifact validator...")
        validation_dir = work_dir / "artifact_validation"
        _run(
            "06_artifact_validator",
            PRIVATE_PYTHON
            + [
                str(ROOT / "validate_structured_state_artifact.py"),
                "--artifact",
                str(ROOT),
                "--out-dir",
                str(validation_dir),
            ],
        )
        validation_json = validation_dir / "artifact_validation_report.json"
        validation_payload = json.loads(validation_json.read_text(encoding="utf-8-sig"))
        if validation_payload.get("status") != "PASS":
            raise CheckFailure("The offline artifact validator did not return PASS.")
        checks.append(
            {
                "label": "Offline artifact validation",
                "status": "PASS",
                "detail": "The sanitized artifact passed consistency and leakage checks.",
            }
        )

        _copy_if_present(state, OUTPUT / "state.json")
        _copy_if_present(handoff, OUTPUT / "handoff.json")
        _copy_if_present(gate, OUTPUT / "gate.json")
        _copy_if_present(
            validation_json,
            OUTPUT / "artifact_validation" / "artifact_validation_report.json",
        )
        _copy_if_present(
            validation_dir / "ARTIFACT_VALIDATION_REPORT.md",
            OUTPUT / "artifact_validation" / "ARTIFACT_VALIDATION_REPORT.md",
        )

        payload: dict[str, object] = {
            "schema_version": "bgvd.reviewer_check.v2",
            "status": "PASS",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "python": sys.version,
            "python_executable": str(Path(sys.executable).resolve()),
            "platform": platform.platform(),
            "machine": platform.machine(),
            "installation_required": False,
            "network_required": False,
            "administrator_required": False,
            "checks": checks,
        }
        _write_summaries(payload)
        print()
        print("OVERALL RESULT: PASS")
        print("The result page will open automatically.")
        return 0
    except Exception as exc:
        checks.append(
            {
                "label": "Reviewer workflow",
                "status": "FAIL",
                "detail": str(exc),
            }
        )
        payload = {
            "schema_version": "bgvd.reviewer_check.v2",
            "status": "FAIL",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "python": sys.version,
            "python_executable": str(Path(sys.executable).resolve()),
            "platform": platform.platform(),
            "machine": platform.machine(),
            "installation_required": False,
            "network_required": False,
            "administrator_required": False,
            "checks": checks,
        }
        _write_summaries(payload)
        print()
        print("OVERALL RESULT: FAIL")
        print(textwrap.fill(str(exc), width=88))
        print("Open reviewer_output/REVIEWER_CHECK_SUMMARY.html for the explanation.")
        return 1
    finally:
        shutil.rmtree(temporary_root, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
