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

- Define a strict mono, 16 kHz, maximum two-second audio contract.
- Reject malformed, non-finite, oversized, multi-channel, and unsupported-rate
  input without producing a positive authenticity verdict.
- Add stable spectral descriptors, LFCC and LPCC summaries.
- Keep fallback behavior conservative: silence and degenerate signal patterns
  can be surfaced; ordinary speech is INCONCLUSIVE.
- Tests: input bounds, deterministic behavior, feature shape/finiteness,
  silence, tone, and non-claim behavior.
- Exit gate: focused VoiceGuard tests green.

## Phase 2 — Optional local anti-spoof model adapter
**Status: COMPLETE (adapter only; no trained weights)**

- Add an ONNX Runtime adapter with an explicit 16 kHz, 32,000-sample waveform
  input and documented probability/logit output contract.
- Support a configurable local model file through
  \`RAKSHA_VOICEGUARD_ONNX\`; never download weights automatically.
- Cache a loaded model; if it cannot load or inference returns invalid values,
  fail closed to INCONCLUSIVE/fallback.
- Add tests using deterministic fake sessions for the ONNX boundary.
- Exit gate: model interface, output shape, thresholds, and model-error tests
  green. Actual model accuracy is not an exit claim.

## Phase 3 — Privacy-aware API and service integration
**Status: COMPLETE**

- Require \`consent: true\` on every voice-screen request.
- Enforce at most 32,000 mono samples at 16 kHz.
- Expose model readiness without revealing a local filesystem path.
- Keep raw audio out of persistent storage, report events, and telemetry.
- Preserve the signed Citizen incident-report flow.
- Exit gate: consent, validation, response, and retention-contract tests green.

## Phase 4 — Consent-first Citizen PWA microphone experience
**Status: IN PROGRESS**

- Replace the bundled sample-tone button with a user-started microphone sample.
- Explain that the sample is sent to the configured RAKSHA service for
  screening; require the user to confirm before requesting microphone access.
- Show a clear recording indicator while capturing, stop tracks immediately,
  and clear in-memory audio after analysis (target under 3 seconds after capture).
- Show verdict, engine/model status, advisory limitations, and the 1930 route.
- Do not claim to monitor or intercept the live phone call. Native Android
  call-screening integration is outside this PWA phase.
- Tests: JavaScript syntax/static checks, safe error handling, and manual
  browser permission/capture/cleanup checklist.
- Exit gate: consent cannot be bypassed through UI; tracks are stopped on
  success, failure, and cancellation; no audio persisted.

## Phase 5 — End-to-end verification, documentation, and handoff
**Status: PENDING**

- Run focused VoiceGuard tests and the complete existing repository pytest
  suite; resolve regressions.
- Add integration tests for health/model readiness, consent gate, API request
  validation, and absence of audio in Citizen report events.
- Run service-worker/PWA smoke tests and document browser support/limitations.
- Update README, changelog, and feature matrix; publish setup instructions
  for optional ONNX Runtime and local model weights.
- Report exact test outcomes, what is still unmeasured, and the native Android
  follow-on requirement.
- Exit gate: all available tests pass; no claim of deepfake accuracy without a
  separately benchmarked and supplied model.
