# VoiceGuard — five-phase implementation roadmap

**Branch:** \`voiceguard/five-phase-build\`  
**Baseline:** \`main_final\`  
**Started:** 2026-11-23  
**Scope:** expand the existing RAKSHA Citizen VoiceGuard prototype, not rebuild
the wider RAKSHA ecosystem.

The requested feature source file was absent from the supplied branch. This
roadmap therefore follows the explicit VoiceGuard contract in
\`raksha/ARCHITECTURE.md\`, \`raksha/BUILD_GUIDE.md\`, and the existing
\`citizen/voiceguard\` module. See \`raksha/features.md\` for the feature map.

## Phase 1 — Audio contract and feature extraction
**Status: COMPLETE**

- Strict mono, 16 kHz, maximum two-second audio contract.
- Reject malformed, non-finite, oversized, multi-channel, and unsupported-rate
  input without producing a positive authenticity verdict.
- Spectral descriptors, LFCC and LPCC summaries.
- Conservative fallback: degenerate signal anomalies can be surfaced;
  ordinary speech remains INCONCLUSIVE.
- Exit gate: focused VoiceGuard tests green.

## Phase 2 — Optional local anti-spoof model adapter
**Status: COMPLETE (adapter only; no trained weights)**

- ONNX Runtime adapter with a 16 kHz, 32,000-sample waveform input and
  documented probability/logit output contract.
- Configurable local model file through \`RAKSHA_VOICEGUARD_ONNX\`; no
  automatic model downloads.
- Model load or inference errors fail closed.
- Exit gate: deterministic mock-session, output, threshold and failure tests
  green. This does not measure real model accuracy.

## Phase 3 — Privacy-aware API and service integration
**Status: COMPLETE**

- Every voice-screen request requires \`consent: true\`.
- Maximum 32,000 mono samples at 16 kHz.
- Model readiness is exposed without disclosing a local filesystem path.
- Raw audio is kept out of persistent storage, incident reports and telemetry.
- Existing signed Citizen report path preserved.
- Exit gate: API consent, validation, response and retention tests green.

## Phase 4 — Consent-first Citizen PWA microphone experience
**Status: COMPLETE**

- Removed bundled test-tone button and added user-started microphone capture.
- Consent is unchecked by default and explained before microphone access.
- Capture is visibly indicated and limited to two seconds; the user can cancel.
- Audio is converted to mono 16 kHz, then sent only to the configured service
  after rechecking consent.
- Microphone tracks stop on completion, failure, cancellation and page exit.
  In-memory arrays are cleared after screening.
- API responses and report flows remain separate; service worker never caches
  API requests.
- Exit gate: JavaScript syntax check and focused PWA regression tests pass.

## Phase 5 — End-to-end verification, documentation, and handoff
**Status: PARTIAL — branch audit and focused checks complete; full suite/browser check pending**

- Focused acoustic, mock ONNX adapter, API-contract and PWA static checks:
  24/24 pass in an isolated local test workspace; JavaScript syntax check passes.
- Final Git tree audit confirms all VoiceGuard core, model, API, PWA, test and
  documentation files coexist on this branch. An intermediate stale-tree
  commit dropped the model adapter; it was detected and restored before handoff.
- The complete repository pytest suite and service smoke checks were not run:
  the sandbox could not clone GitHub (DNS/network unavailable), so this is not
  a claim that the existing 67-test suite remains green.
- Real-browser microphone permission, cancellation, resampling and cleanup
  still need manual verification; static tests are not a browser session.
- Documented optional ONNX Runtime setup and the exact model export contract.
- Report exact outcomes and remaining limitations. Do not claim anti-spoof
  accuracy until supplied model weights are benchmarked on representative
  consented data.

## Non-negotiable boundaries

- This PWA cannot intercept cellular/VoIP call audio. Native Android
  CallScreeningService integration is a separate project phase.
- No model weights or real-world performance dataset are present in the repo.
- VoiceGuard is advisory; a verdict cannot identify a caller or prove fraud.
