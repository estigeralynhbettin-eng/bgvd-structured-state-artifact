# BGVD-State v1.1.1 Reviewer Quick Start

This is the recommended entry point for reviewers. Choose the no-install bundle
that matches the operating system and processor.

## Three Steps

1. Download and extract one complete reviewer ZIP from the
   [`v1.1.1` Release page](https://github.com/estigeralynhbettin-eng/bgvd-structured-state-artifact/releases/tag/v1.1.1):
   - Windows x64: `BGVD-State-v1.1.1-Reviewer-Kit-Windows-x64.zip`
   - macOS Apple Silicon: `BGVD-State-v1.1.1-Reviewer-Kit-macOS-Apple-Silicon.zip`
   - macOS Intel: `BGVD-State-v1.1.1-Reviewer-Kit-macOS-Intel.zip`
2. Double-click the `00_DOUBLE_CLICK_TO_VERIFY_...` file.
3. Read the result page that opens automatically.

The expected headline is:

```text
OVERALL RESULT: PASS
```

That is all that is required.

## Nothing to Install

Each reviewer ZIP includes its own private Python runtime and all required
packages. The check:

- does not use the computer's Python or Anaconda installation;
- does not install Python or any package;
- does not need an internet connection;
- does not need administrator permission;
- does not change system settings;
- does not use an API key, language model, Docker container, service, or live
  target; and
- writes results only inside `reviewer_output` in the extracted folder.

The private runtime uses isolated mode and ignores `PYTHONHOME`, `PYTHONPATH`,
and user-level packages. An existing Python installation cannot override it.

If the launcher reports that the private runtime is missing, the ZIP was not
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

It gives one clear `PASS` or `FAIL`, explains the conclusion, and links to six
raw logs. Markdown, plain-text, JSON, reconstructed-state, handoff, gate, and
artifact-validation outputs are stored in the same folder.

## What a PASS Supports

A `PASS` confirms that the bundled software runs without installation, all 18
tests pass, the released case is replayable, rejected and failed paths remain
visible, unsupported finalization is blocked, and the sanitized artifact is
internally consistent.

It does not claim autonomous vulnerability discovery, a maintainer-confirmed
vulnerability, universal performance superiority, or production-scale
distributed execution.

## macOS First Launch

The macOS bundles are not notarized with a paid Apple Developer ID. If
Gatekeeper blocks the first double-click after a browser download, Control-click
the `.command` file, choose **Open**, and confirm **Open** once. This does not
install software or require administrator permission. Subsequent launches can
use a normal double-click.

## Optional Source Workflow

Technical reviewers who prefer their own Python 3.10--3.12 environment can run:

```bash
python -m pip install -e ".[dev]"
python -m unittest discover -s tests -v
python validate_structured_state_artifact.py \
  --artifact . \
  --out-dir artifact_validation_output
```

This optional workflow may download Python packages. It is not needed for a
no-install reviewer check.

## Package Integrity

Each ZIP has a matching `.sha256.txt` file beside it on the Release page.

## Manual Documentation

- `README.md`: software overview, installation, examples, and API introduction.
- `REPRODUCE.md`: detailed reproduction notes and evidence mapping.
- `docs/api.md`: public Python API.
- `docs/integration.md`: producer, state, and consumer contracts.
- `docs/runtime-validation.md`: runtime engineering protocol.
- `examples/*/README.md`: step-by-step example explanations.
