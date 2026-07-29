"""Build a platform-specific, no-install BGVD-State reviewer kit.

The build downloads one pinned Python Build Standalone runtime, verifies its
SHA-256 digest, vendors the exact schema-validation dependencies, and packages
the public source plus a one-click reviewer launcher. The resulting kit does
not download or install anything when a reviewer runs it.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import shutil
import stat
import subprocess
import sys
import tarfile
import tempfile
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
KIT_ROOT_NAME = "BGVD-State-v1.1.1-reviewer-kit"
RUNTIME_RELEASE = "20260728"
PYTHON_VERSION = "3.12.13"
RUNTIME_BASE_URL = (
    "https://github.com/astral-sh/python-build-standalone/releases/download/"
    f"{RUNTIME_RELEASE}"
)
DEPENDENCIES = (
    "attrs==26.1.0",
    "jsonschema==4.23.0",
    "jsonschema-specifications==2025.9.1",
    "referencing==0.37.0",
    "rpds-py==2026.6.3",
    "typing-extensions==4.16.0",
)
PLATFORMS: dict[str, dict[str, str]] = {
    "windows-x64": {
        "asset": (
            "cpython-3.12.13+20260728-x86_64-pc-windows-msvc-"
            "install_only_stripped.tar.gz"
        ),
        "asset_sha256": "242b94b37682ac55f9bf9eb624348dc8d17c64f74f56028104545ea3ffe35e26",
        "archive": "BGVD-State-v1.1.1-Reviewer-Kit-Windows-x64.zip",
        "system": "Windows",
        "machine": "AMD64",
        "runtime_python": "runtime/python.exe",
        "site_packages": "runtime/Lib/site-packages",
        "source_pth": "../../../src",
        "launcher": "00_DOUBLE_CLICK_TO_VERIFY_WINDOWS.bat",
    },
    "macos-arm64": {
        "asset": (
            "cpython-3.12.13+20260728-aarch64-apple-darwin-"
            "install_only_stripped.tar.gz"
        ),
        "asset_sha256": "2f18cdef4125ca1440dd1ba00ebcb267526efb532138c0860438f755ea4eebac",
        "archive": "BGVD-State-v1.1.1-Reviewer-Kit-macOS-Apple-Silicon.zip",
        "system": "Darwin",
        "machine": "arm64",
        "runtime_python": "runtime/bin/python3",
        "site_packages": "runtime/lib/python3.12/site-packages",
        "source_pth": "../../../../src",
        "launcher": "00_DOUBLE_CLICK_TO_VERIFY_MACOS.command",
    },
    "macos-x64": {
        "asset": (
            "cpython-3.12.13+20260728-x86_64-apple-darwin-"
            "install_only_stripped.tar.gz"
        ),
        "asset_sha256": "e654c21d0ba53e2c671868d4112fac5874deca4c35226d36c5cfe53bc5c9cd71",
        "archive": "BGVD-State-v1.1.1-Reviewer-Kit-macOS-Intel.zip",
        "system": "Darwin",
        "machine": "x86_64",
        "runtime_python": "runtime/bin/python3",
        "site_packages": "runtime/lib/python3.12/site-packages",
        "source_pth": "../../../../src",
        "launcher": "00_DOUBLE_CLICK_TO_VERIFY_MACOS.command",
    },
}

ROOT_FILES = (
    "README.md",
    "REPRODUCE.md",
    "LICENSE.txt",
    "DATA_LICENSE.txt",
    "SECURITY.md",
    "CHANGELOG.md",
    "CITATION.cff",
    "codemeta.json",
    "pyproject.toml",
    "CLAIM_EVIDENCE_MATRIX.csv",
    "RESULT_TRACEABILITY.csv",
    "LEAKAGE_AUDIT_COUNTS.json",
    "LEAKAGE_AUDIT_STRICT_COUNTS.json",
    "validate_structured_state_artifact.py",
    "artifact_manifest_20260709.json",
    "artifact_validation_report.json",
    "ARTIFACT_VALIDATION_REPORT.md",
    "DATA_AVAILABILITY_SNIPPETS_20260709.md",
)
ROOT_GLOBS = ("v3*.json", "v3*.md", "phase9*.json", "phase9*.md")
SOURCE_DIRECTORIES = ("src", "tests", "examples", "schemas", "docs", "validation")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def source_revision() -> dict[str, object]:
    try:
        commit = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=REPOSITORY_ROOT,
            check=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        ).stdout.strip()
        status = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=REPOSITORY_ROOT,
            check=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        ).stdout
        return {"commit": commit, "working_tree_dirty": bool(status.strip())}
    except (FileNotFoundError, subprocess.CalledProcessError):
        return {"commit": None, "working_tree_dirty": None}


def download(url: str, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(url, headers={"User-Agent": "BGVD-reviewer-kit-builder/1"})
    with urllib.request.urlopen(request, timeout=120) as response:
        with destination.open("wb") as output:
            shutil.copyfileobj(response, output, length=1024 * 1024)


def acquire_runtime(config: dict[str, str], cache_dir: Path) -> Path:
    asset_name = config["asset"]
    asset_path = cache_dir / asset_name
    expected = config["asset_sha256"]
    if asset_path.exists() and sha256_file(asset_path) != expected:
        asset_path.unlink()
    if not asset_path.exists():
        encoded_asset_name = asset_name.replace("+", "%2B")
        download(f"{RUNTIME_BASE_URL}/{encoded_asset_name}", asset_path)
    actual = sha256_file(asset_path)
    if actual != expected:
        raise RuntimeError(
            f"Runtime digest mismatch for {asset_name}: expected {expected}, got {actual}"
        )
    return asset_path


def extract_runtime(archive: Path, destination: Path) -> None:
    with tempfile.TemporaryDirectory(prefix="bgvd_runtime_extract_") as temporary:
        temporary_root = Path(temporary)
        with tarfile.open(archive, "r:gz") as tar:
            tar.extractall(temporary_root, filter="data")
        install_root = temporary_root / "python"
        legacy_install_root = install_root / "install"
        if legacy_install_root.is_dir():
            install_root = legacy_install_root
        if not install_root.is_dir():
            raise RuntimeError(f"Unexpected runtime archive layout: {archive}")
        shutil.copytree(install_root, destination, symlinks=True)


def copy_public_source(kit_root: Path) -> None:
    for name in ROOT_FILES:
        source = REPOSITORY_ROOT / name
        if not source.is_file():
            raise FileNotFoundError(f"Required public source file is missing: {source}")
        shutil.copy2(source, kit_root / name)
    for pattern in ROOT_GLOBS:
        for source in REPOSITORY_ROOT.glob(pattern):
            if source.is_file():
                shutil.copy2(source, kit_root / source.name)
    for name in SOURCE_DIRECTORIES:
        source = REPOSITORY_ROOT / name
        if not source.is_dir():
            raise FileNotFoundError(f"Required public source directory is missing: {source}")
        shutil.copytree(source, kit_root / name)


def vendor_dependencies(site_packages: Path) -> list[dict[str, str]]:
    site_packages.mkdir(parents=True, exist_ok=True)
    command = [
        sys.executable,
        "-m",
        "pip",
        "install",
        "--disable-pip-version-check",
        "--no-compile",
        "--only-binary=:all:",
        "--target",
        str(site_packages),
        *DEPENDENCIES,
    ]
    subprocess.run(command, check=True)
    distributions = sorted(
        importlib.metadata.distributions(path=[str(site_packages)]),
        key=lambda distribution: distribution.metadata["Name"].lower(),
    )
    return [
        {
            "name": distribution.metadata["Name"],
            "version": distribution.version,
        }
        for distribution in distributions
    ]


def reviewer_readme(platform_key: str, config: dict[str, str]) -> str:
    if platform_key == "windows-x64":
        platform_name = "64-bit Windows 10 or Windows 11"
        action = "Double-click `00_DOUBLE_CLICK_TO_VERIFY_WINDOWS.bat`."
        gatekeeper = ""
    elif platform_key == "macos-arm64":
        platform_name = "macOS 13 or later on Apple Silicon (M1, M2, M3, or newer)"
        action = "Double-click `00_DOUBLE_CLICK_TO_VERIFY_MACOS.command`."
        gatekeeper = """
## macOS Gatekeeper

This research artifact is not notarized with a paid Apple Developer ID. If
macOS blocks the first double-click because the file was downloaded from the
internet, Control-click the `.command` file, choose **Open**, and confirm
**Open** once. This does not install software or require administrator access.
Subsequent launches can use a normal double-click.
"""
    else:
        platform_name = "macOS 13 or later on an Intel Mac"
        action = "Double-click `00_DOUBLE_CLICK_TO_VERIFY_MACOS.command`."
        gatekeeper = """
## macOS Gatekeeper

This research artifact is not notarized with a paid Apple Developer ID. If
macOS blocks the first double-click because the file was downloaded from the
internet, Control-click the `.command` file, choose **Open**, and confirm
**Open** once. This does not install software or require administrator access.
Subsequent launches can use a normal double-click.
"""

    return f"""# BGVD-State v1.1.1 Reviewer Quick Start

This no-install bundle is for **{platform_name}**.

## Three Steps

1. Extract the complete `{config['archive']}` file.
2. {action}
3. Read the result page that opens automatically.

The expected headline is:

```text
OVERALL RESULT: PASS
```

## Nothing to Install

The bundle includes its own private Python runtime and exact dependencies. It
does not use or modify a Python or Anaconda installation already on the
computer. It needs no internet connection, administrator permission, API key,
language model, Docker container, service, or live target.

The check writes only to `reviewer_output` inside the extracted folder. It is
safe to delete the entire extracted folder after review.

## What PASS Means

The automated check runs all 18 tests, replays the fixed 23-event case,
confirms 6 candidate lifecycles, preserves 5 rejected candidates and 5 failed
paths, verifies that unsupported finalization is blocked, and runs the offline
artifact validator. The evidence-gate exit code `2` is expected and is checked
explicitly.

The result page links to six raw logs. It also preserves Markdown, plain-text,
JSON, reconstructed-state, handoff, gate, and artifact-validation outputs.

A PASS supports software execution and the stated evidence-preservation
behavior. It does not claim autonomous vulnerability discovery, a
maintainer-confirmed vulnerability, or universal performance superiority.

{gatekeeper}
## Manual Documentation

- `README.md`: software overview and examples.
- `REPRODUCE.md`: detailed reproduction and evidence mapping.
- `docs/api.md`: public Python API.
- `docs/integration.md`: producer, state, and consumer contracts.
- `docs/runtime-validation.md`: runtime engineering protocol.
- `examples/*/README.md`: step-by-step example explanations.
"""


def supported_platforms() -> str:
    return """# Supported Reviewer Platforms

| Bundle | Status | Reviewer action |
|---|---|---|
| Windows 10/11 x64 | CI-verified | Extract and double-click the Windows `.bat` launcher |
| macOS Apple Silicon | CI-verified | Extract and double-click the macOS `.command` launcher |
| macOS Intel | CI-verified | Extract and double-click the macOS `.command` launcher |
| Linux x64 | Source workflow only | No no-install reviewer bundle in v1.1.1 |
| iOS/iPadOS | Not supported | Mobile operating systems are outside the execution environment |

Each no-install asset is built and executed on a matching GitHub-hosted runner.
The asset filename identifies its platform and CPU architecture.

The source package supports Python 3.10, 3.11, and 3.12. That optional workflow
is distinct from these no-install reviewer bundles and may require an existing
Python environment.

The macOS bundles are not notarized with a paid Apple Developer ID. Gatekeeper
may therefore require the standard one-time Control-click, **Open** confirmation
for a file downloaded from the internet. No installation or administrator
permission is required.
"""


def runtime_provenance(
    platform_key: str,
    config: dict[str, str],
    dependency_metadata: list[dict[str, str]],
    runtime_python: Path,
) -> str:
    dependencies = "\n".join(
        f"- `{item['name']}=={item['version']}`" for item in dependency_metadata
    )
    asset_url = f"{RUNTIME_BASE_URL}/{config['asset'].replace('+', '%2B')}"
    return f"""# Bundled Runtime Provenance

- Kit platform: `{platform_key}`
- Expected operating system: `{config['system']}`
- Expected machine architecture: `{config['machine']}`
- CPython: `{PYTHON_VERSION}`
- Distribution: Astral `python-build-standalone`
- Fixed release: `{RUNTIME_RELEASE}`
- Runtime asset: `{config['asset']}`
- Runtime asset URL: `{asset_url}`
- Runtime asset SHA-256: `{config['asset_sha256']}`
- Bundled interpreter: `{config['runtime_python']}`
- Bundled interpreter SHA-256: `{sha256_file(runtime_python)}`

## Bundled Python dependencies

{dependencies}

Package metadata and license files are retained in the private runtime's
`site-packages` directory. The runtime loads the unchanged public source from
the kit's `src` directory through a relative `.pth` entry. Reviewer execution
uses Python isolated mode (`-I -s`) and clears `PYTHONHOME` and `PYTHONPATH`.
"""


def write_build_metadata(
    kit_root: Path,
    platform_key: str,
    config: dict[str, str],
    dependency_metadata: list[dict[str, str]],
) -> None:
    payload: dict[str, Any] = {
        "schema_version": "bgvd.reviewer_kit.build.v1",
        "built_at": datetime.now(timezone.utc).isoformat(),
        "platform_key": platform_key,
        "expected_system": config["system"],
        "expected_machine": config["machine"],
        "python_version": PYTHON_VERSION,
        "runtime_release": RUNTIME_RELEASE,
        "runtime_asset": config["asset"],
        "runtime_asset_sha256": config["asset_sha256"],
        "dependencies": dependency_metadata,
        "source_revision": source_revision(),
    }
    (kit_root / "REVIEWER_KIT_BUILD.json").write_text(
        json.dumps(payload, indent=2) + "\n",
        encoding="utf-8",
    )


def write_file_manifest(kit_root: Path) -> None:
    records = []
    manifest_path = kit_root / "REVIEWER_KIT_FILE_MANIFEST.json"
    for path in sorted(kit_root.rglob("*")):
        if path.is_file() and path != manifest_path:
            records.append(
                {
                    "path": path.relative_to(kit_root).as_posix(),
                    "bytes": path.stat().st_size,
                    "sha256": sha256_file(path),
                }
            )
    manifest_path.write_text(
        json.dumps(
            {
                "schema_version": "bgvd.reviewer_kit.files.v1",
                "file_count": len(records),
                "files": records,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def make_archive(kit_root: Path, archive_path: Path, platform_key: str) -> None:
    if platform_key.startswith("macos-"):
        if shutil.which("ditto") is None:
            raise RuntimeError("macOS reviewer archives must be created with ditto.")
        subprocess.run(
            [
                "ditto",
                "-c",
                "-k",
                "--sequesterRsrc",
                "--keepParent",
                str(kit_root),
                str(archive_path),
            ],
            check=True,
        )
        return

    with zipfile.ZipFile(
        archive_path,
        "w",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=9,
    ) as archive:
        for path in sorted(kit_root.rglob("*")):
            if path.is_file():
                archive.write(path, (Path(KIT_ROOT_NAME) / path.relative_to(kit_root)).as_posix())


def build(platform_key: str, output_dir: Path, cache_dir: Path) -> tuple[Path, Path]:
    config = PLATFORMS[platform_key]
    output_dir.mkdir(parents=True, exist_ok=True)
    cache_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="bgvd_reviewer_build_") as temporary:
        stage = Path(temporary)
        kit_root = stage / KIT_ROOT_NAME
        kit_root.mkdir()
        copy_public_source(kit_root)

        runtime_asset = acquire_runtime(config, cache_dir)
        runtime_root = kit_root / "runtime"
        extract_runtime(runtime_asset, runtime_root)

        site_packages = kit_root / Path(config["site_packages"])
        dependency_metadata = vendor_dependencies(site_packages)
        (site_packages / "bgvd_state_source.pth").write_text(
            config["source_pth"] + "\n",
            encoding="utf-8",
        )

        shutil.copy2(
            REPOSITORY_ROOT / "reviewer" / "reviewer_offline_check.py",
            kit_root / "reviewer_offline_check.py",
        )
        launcher_source = REPOSITORY_ROOT / "reviewer" / "launchers" / config["launcher"]
        launcher_destination = kit_root / config["launcher"]
        shutil.copy2(launcher_source, launcher_destination)
        if platform_key.startswith("macos-"):
            launcher_destination.chmod(
                launcher_destination.stat().st_mode
                | stat.S_IXUSR
                | stat.S_IXGRP
                | stat.S_IXOTH
            )

        (kit_root / "00_READ_ME_FIRST.md").write_text(
            reviewer_readme(platform_key, config),
            encoding="utf-8",
        )
        (kit_root / "SUPPORTED_PLATFORMS.md").write_text(
            supported_platforms(),
            encoding="utf-8",
        )
        write_build_metadata(kit_root, platform_key, config, dependency_metadata)
        runtime_python = kit_root / Path(config["runtime_python"])
        if not runtime_python.is_file():
            raise RuntimeError(f"Bundled interpreter is missing: {runtime_python}")
        (kit_root / "RUNTIME_PROVENANCE.md").write_text(
            runtime_provenance(
                platform_key,
                config,
                dependency_metadata,
                runtime_python,
            ),
            encoding="utf-8",
        )
        write_file_manifest(kit_root)

        archive_path = output_dir / config["archive"]
        archive_path.unlink(missing_ok=True)
        make_archive(kit_root, archive_path, platform_key)

    archive_sha = sha256_file(archive_path)
    checksum_path = archive_path.with_suffix(".sha256.txt")
    checksum_path.write_text(f"{archive_sha}  {archive_path.name}\n", encoding="ascii")
    return archive_path, checksum_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--platform", required=True, choices=sorted(PLATFORMS))
    parser.add_argument("--output-dir", type=Path, default=REPOSITORY_ROOT / "dist" / "reviewer")
    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=REPOSITORY_ROOT / ".reviewer-runtime-cache",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    archive, checksum = build(
        args.platform,
        args.output_dir.resolve(),
        args.cache_dir.resolve(),
    )
    print(
        json.dumps(
            {
                "status": "PASS",
                "platform": args.platform,
                "archive": str(archive),
                "sha256": sha256_file(archive),
                "checksum": str(checksum),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
