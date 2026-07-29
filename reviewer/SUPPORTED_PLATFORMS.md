# Supported Reviewer Platforms

## No-install reviewer bundle

| Bundle | Status | Reviewer action |
|---|---|---|
| Windows 10/11 x64 | Verified | Extract and double-click `00_DOUBLE_CLICK_TO_VERIFY_WINDOWS.bat` |
| macOS Apple Silicon | Not included | Use a separately named and verified macOS arm64 asset when available |
| macOS Intel | Not included | Use a separately named and verified macOS x86_64 asset when available |
| Linux x64 | Not included | Use a separately named and verified Linux x64 asset when available |
| iOS/iPadOS | Not supported | Mobile operating systems are outside the intended execution environment |

The asset filename identifies its platform. A reviewer should not be expected
to install a programming language, package manager, container runtime, or system
dependency merely to run a no-install reviewer check.

## Source software

The BGVD-State v1.1.1 source package supports Python 3.10, 3.11, and 3.12. The
source workflow is distinct from the no-install reviewer bundle and may require
an existing Python environment.

Do not describe the Windows x64 no-install bundle as macOS-verified. A separate
macOS bundle should be released only after it has produced `OVERALL RESULT:
PASS` on the matching operating system and architecture.
