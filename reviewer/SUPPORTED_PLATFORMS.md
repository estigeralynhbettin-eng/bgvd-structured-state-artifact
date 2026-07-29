# Supported Reviewer Platforms

## No-install reviewer bundles

| Bundle | Status | Reviewer action |
|---|---|---|
| Windows 10/11 x64 | CI-verified | Extract and double-click the Windows `.bat` launcher |
| macOS Apple Silicon | CI-verified | Extract and double-click the macOS `.command` launcher |
| macOS Intel | CI-verified | Extract and double-click the macOS `.command` launcher |
| Linux x64 | Source workflow only | No no-install reviewer bundle in v1.1.1 |
| iOS/iPadOS | Not supported | Mobile operating systems are outside the execution environment |

Each no-install asset is built and executed on a matching GitHub-hosted runner.
The asset filename identifies its platform and CPU architecture. Reviewers are
not expected to install a programming language, package manager, container
runtime, or system dependency.

The macOS bundles are not notarized with a paid Apple Developer ID. Gatekeeper
may therefore require the standard one-time Control-click, **Open** confirmation
for a file downloaded from the internet. No installation or administrator
permission is required.

## Source software

The BGVD-State v1.1.1 source package supports Python 3.10, 3.11, and 3.12. The
source workflow is distinct from the no-install reviewer bundles and may
require an existing Python environment.
