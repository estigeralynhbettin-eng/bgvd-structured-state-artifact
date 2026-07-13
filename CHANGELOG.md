# Changelog

## 1.1.0 - 2026-07-13

- Reframed the package as a replayable discovery-state runtime while keeping
  models, schedulers, tool execution, and disclosure policy outside the core.
- Added a de-identified 23-event engineering case with six candidates, five
  failed paths, technical verification, and scope-gated finalization.
- Added atomic state/JSONL writes, a CLI runtime summary, checkpoint-resume
  equivalence, invalid-input checks, and v1 state compatibility validation.
- Added deterministic 100-replay validation and a five-repeat performance
  benchmark from 100 to 100,000 events under a fixed six-candidate profile.
- Extended GitHub Actions coverage to Python 3.11.

## 1.0.0 - 2026-07-13

- Added the installable `bgvd-state` Python package.
- Added deterministic event storage, candidate lifecycle management,
  invalidation handling, failed-path memory, verifier-gated finalization, and
  handoff packet generation.
- Added CLI commands, defensive examples, unit tests, and cross-platform CI.
- Separated MIT code licensing from CC BY 4.0 artifact-data licensing.
