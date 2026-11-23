# VoiceGuard — verified feature inventory

> Consolidated for the VoiceGuard build on 2026-11-23. The supplied
> main_final branch did not contain a file named features.md, nor any path or
> reference named Maya. This inventory records only features explicitly
> documented by the existing RAKSHA sources; it does not reproduce a missing
> specification.

## Product intent

VoiceGuard is the voice-screening component of RAKSHA Citizen. It provides
short, advisory screening of user-consented microphone audio. An optional
local ONNX model can provide anti-spoof scores if separately supplied. It is
not an identity verifier and never makes a finding of fraud by itself.

## Source-backed requirements and delivery status

| Requirement | Source in the repository | Build status |
|---|---|---|
| Screen a short audio window (target: 2 seconds) | raksha/ARCHITECTURE.md | PWA captures a two-second microphone sample; API enforces the same limit |
| Spectral descriptors plus LFCC/LPCC lineage | raksha/ARCHITECTURE.md | Implemented |
| On-device/local anti-spoof model interface | raksha/ARCHITECTURE.md; raksha/BUILD_GUIDE.md M3 | Optional local ONNX adapter implemented; model weights are not present |
| Deterministic fallback when no model is available | raksha/BUILD_GUIDE.md M3 | Implemented; real speech remains inconclusive |
| No audio transfer without consent | raksha/ARCHITECTURE.md; raksha/BUILD_GUIDE.md safety rule 4 | Unchecked-by-default PWA consent plus API consent gate |
| Visible microphone activity; ephemeral buffer; discard in under 3 seconds | raksha/BUILD_GUIDE.md safety rule 5 | Visible two-second capture; tracks stop and temporary buffers are cleared after processing |
| Advisory verdicts and no unsupported clone claims | raksha/CHANGELOG.md v0.4.0 | Implemented and tested |
| Citizen incident reporting stays separate from audio | raksha/ARCHITECTURE.md; citizen/api.py | Preserved; audio never enters report payload or spine telemetry |

## Explicit boundaries

- A browser PWA cannot intercept the operating system's live phone-call audio.
  It only screens a short microphone sample the user deliberately records.
  A true incoming-call integration needs a separately permissioned native
  Android CallScreeningService and platform review.
- The sample is sent to the configured RAKSHA service after explicit consent.
  Users should only use a trusted or self-hosted service.
- No trained anti-spoof weights or validated benchmark corpus were found in
  the branch. The ONNX adapter is an integration contract, not a shipped model.
- The fallback never labels ordinary speech as genuine. Model performance,
  multilingual/accent performance, and real-world error rates are unmeasured.
- The API processes audio in request memory. It is not written to disk,
  telemetry, or incident reports. The browser clears temporary audio arrays
  and stops microphone tracks on all completion/error paths.
