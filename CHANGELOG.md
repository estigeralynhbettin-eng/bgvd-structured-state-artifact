# Changelog

## 1.2.0 - 2026-09-17

- Validate complete events before mutating event history or lifecycle state;
  reject invalid reserved metadata without leaving partial state.
- Document and test canonical input schemas and compatibility aliases;
  state explicitly that event order is supplied by the client.
- Add independent continuation, cross-family, and recorded-token scorers,
  complete-population checks, protocol-failure and retry sensitivities.
- Release scoreable cross-family evidence and 144 projected call records;
  14 failed updater calls have no recorded usage and are excluded from sums.
- Expand regression tests and show current results, retained logs, and
  durable HTML/Markdown/JSON links in the no-install reviewer workflow.
- Provide new Windows x64, macOS Apple Silicon, and macOS Intel kits.
  Preserve v1.1.1 and historical experiments unchanged.

## 1.1.1 - 2026-07-16

- Clarified BGVD-State as middleware between security-event producers and
  downstream models, reviewers, and reporting pipelines.
- Added a reviewer quick check with installation, 18-test, replay, gate, and
  expected-output instructions.
- Published the three reviewed repositories and fixed commits while continuing
  to withhold candidate-specific source locations and reproduction details.
- Corrected the validation wording from concurrent candidates to a fixed
  six-candidate event-volume profile.

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
