# Bundled Runtime Provenance

Each reviewer kit contains a private, platform-matched CPython runtime from
Astral's `python-build-standalone` project:

- Fixed release: `20260728`
- CPython: `3.12.13`
- Runtime variant: `install_only_stripped`
- Upstream checksums:
  [`SHA256SUMS`](https://github.com/astral-sh/python-build-standalone/releases/download/20260728/SHA256SUMS)

The build script pins and verifies a distinct runtime archive for Windows x64,
macOS Apple Silicon, and macOS Intel. It also vendors:

- `attrs==26.1.0`
- `jsonschema==4.23.0`
- `jsonschema-specifications==2025.9.1`
- `referencing==0.37.0`
- `rpds-py==2026.6.3`
- `typing-extensions==4.16.0`

Every built kit includes its exact runtime asset name, upstream asset SHA-256,
bundled-interpreter SHA-256, dependency versions, build metadata, and a
per-file manifest. The reviewer workflow uses Python isolated mode (`-I -s`),
clears `PYTHONHOME` and `PYTHONPATH`, and does not load user-level packages.
