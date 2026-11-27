# Changelog

## Current — Phase Ten release

- Unified the whole repository behind one root README, one status board, one
  changelog and one document map.
- Delivered one install command, one test command, one eval command and one
  process launcher for the two-app system.
- Added CI gates for Python suites, browser suites, eval drift, ledger verify,
  boot manifests, no secrets and no live-executor imports.
- Replaced the historical evaluation sprawl with one deterministic corpus
  generator, one replay player, one eval runner, one generated `EVALS.md`, one
  claims ledger and one drift check.
- Conditioned every measured number and kept real-world accuracy, latency,
  uptime, recall and false-positive rate UNMEASURED.
- Moved retired standalone projects and historical uploads under
  `archive/provenance/` with integration notes.
- Froze the ten-phase board and wrote the VoiceGuard re-entry gate for a
  separate future Phase Eleven.
- Added the root [`summary.md`](summary.md) AI handoff and future-integration
  playbook, covered by the claims ledger and integration gates.

Historical phase-by-phase detail remains in
[`raksha/CHANGELOG.md`](raksha/CHANGELOG.md). Earlier counts in that file are
labelled historical and are not current release evidence. The final Phase Nine
and Ten validation snapshot is in
[`raksha/PHASE910_UNIFIED_RELEASE.md`](raksha/PHASE910_UNIFIED_RELEASE.md).
