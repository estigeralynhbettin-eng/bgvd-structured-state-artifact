# BGVD-State v1.1.1 Reviewer Quick Start — Windows x64

This is the recommended entry point for reviewers.

Supported by this no-install bundle: **64-bit Windows 10 or Windows 11**.

This bundle is not a macOS or iOS application. The BGVD-State Python source is
platform-independent, but no-install reviewer bundles must be downloaded for
the reviewer's operating system. See `SUPPORTED_PLATFORMS.md`.

## Three Steps

1. Download and extract the complete
   [`BGVD-State-v1.1.1-Reviewer-Kit-Windows-x64.zip`](https://github.com/estigeralynhbettin-eng/bgvd-structured-state-artifact/releases/download/v1.1.1/BGVD-State-v1.1.1-Reviewer-Kit-Windows-x64.zip).
2. Double-click `00_DOUBLE_CLICK_TO_VERIFY_WINDOWS.bat`.
3. Read the result page that opens automatically.

The expected headline is:

```text
OVERALL RESULT: PASS
```

That is all that is required.

## Nothing to Install

The Windows reviewer ZIP includes its own private Python runtime and all
required packages. The check:

- does not use the computer's Python installation;
- does not install Python or any package;
- does not need an internet connection;
- does not need administrator permission;
- does not change system settings;
- does not use an API key, language model, Docker container, service, or live
  target; and
- writes results only inside `reviewer_output` in the extracted folder.

The private runtime is isolated from `PYTHONHOME`, `PYTHONPATH`, and user-level
Python packages. An existing Python or Anaconda installation cannot override
the packages used by the reviewer check.

If Windows reports that `runtime/python.exe` is missing, the ZIP was not
extracted completely or the download is incomplete. Re-extract or re-download
the reviewer ZIP. Do not install anything.

## What the Check Does

The automated check:

1. loads the private bundled runtime;
2. runs all 18 unit and integration tests;
3. replays the fixed 23-event case;
4. confirms 6 candidate lifecycles, 5 rejected candidates, and 5 failed paths;
5. confirms that the evidence gate blocks unsupported finalization for
   `CASE-C06`; and
6. runs the offline artifact validator.

The gate command normally uses exit code `2`. In this case, that is the expected
safety decision, not a software failure. The reviewer check verifies this
explicitly.

## Result and Logs

After the run, the following page opens automatically:

`reviewer_output/REVIEWER_CHECK_SUMMARY.html`

It gives one clear `PASS` or `FAIL`, explains the conclusion, and links to the
raw logs for every step. Markdown, plain-text, JSON, reconstructed state,
handoff, gate, and artifact-validation outputs are stored in the same folder.

## What a PASS Supports

A `PASS` confirms that the bundled software runs without installation, all 18
tests pass, the released case is replayable, rejected and failed paths remain
visible, unsupported finalization is blocked, and the sanitized artifact is
internally consistent.

It does not claim autonomous vulnerability discovery, a maintainer-confirmed
vulnerability, universal performance superiority, or production-scale
distributed execution.

## Technical Source Workflow

The source-only workflow remains available for technical reviewers who prefer
to use their own Python 3.10--3.12 environment:

```bash
python -m pip install -e ".[dev]"
python -m unittest discover -s tests -v
python validate_structured_state_artifact.py \
  --artifact . \
  --out-dir artifact_validation_output
```

This optional workflow may download Python packages. It is not needed for the
recommended no-install Windows check.

## Package Integrity

The Windows asset SHA-256 is:

```text
922f5110fefc8b23d8c8bfbb026065fa735a8c850ecffee68d59692560640c17
```

The checksum file is available beside the ZIP on the
[`v1.1.1` Release page](https://github.com/estigeralynhbettin-eng/bgvd-structured-state-artifact/releases/tag/v1.1.1).

## Manual Documentation

- `README.md`: software overview, installation, examples, and API introduction.
- `REPRODUCE.md`: detailed reproduction notes and evidence mapping.
- `docs/api.md`: public Python API.
- `docs/integration.md`: producer, state, and consumer contracts.
- `docs/runtime-validation.md`: runtime engineering protocol.
- `examples/*/README.md`: step-by-step example explanations.
