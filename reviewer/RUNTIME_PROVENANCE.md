# Bundled Runtime Provenance

The Windows x64 reviewer asset contains a private runtime so that reviewers do
not need to install Python or packages.

## CPython

- Distribution: CPython 3.12.10 Windows embeddable package, 64-bit
- Official source:
  `https://www.python.org/ftp/python/3.12.10/python-3.12.10-embed-amd64.zip`
- Download SHA-256:
  `4acbed6dd1c744b0376e3b1cf57ce906f9dc9e95e68824584c8099a63025a3c3`
- Bundled `runtime/python.exe` SHA-256:
  `4d6f5f81a4bca11191c4c7c6b43632694d0a4ce74e068619d8fdc161d469859a`
- Bundled `runtime/python312.dll` SHA-256:
  `9a0e3435aaa680d868150f87ab3e388ad2eebc22f87e036155c7b4eda8cd2120`
- License: `runtime/LICENSE.txt`

## Bundled Python dependencies

- `attrs==26.1.0`
- `jsonschema==4.23.0`
- `jsonschema-specifications==2025.9.1`
- `referencing==0.37.0`
- `rpds-py==2026.6.3`
- `typing-extensions==4.16.0`

Package metadata and license files are retained under
`runtime/Lib/site-packages/*-dist-info`.

The runtime path configuration includes `../src`, so the reviewer workflow
executes the unchanged BGVD-State source distributed in the asset. It does not
install a second copy of BGVD-State. The embeddable runtime remains in isolated
mode, ignores `PYTHONHOME` and `PYTHONPATH`, and does not load user-level
site-packages from an existing Python installation.
