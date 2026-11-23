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
| Screen a short audio window (target: 2 seconds) | raksha/ARCHITECTURE.md | API enforces 2 seconds; PWA microphone capture is next |
| Spectral descriptors plus LFCC/LPCC lineage | raksha/ARCHITECTURE.md | Implemented |
| On-device/local anti-spoof model interface | raksha/ARCHITECTURE.md; raksha/BUILD_GUIDE.md M3 | Optional local ONNX adapter implemented; model weights are not present |
| Deterministic fallback when no model is available | raksha/BUILD_GUIDE.md M3 | Implemented; real speech remains inconclusive |
| No audio transfer without consent | raksha/ARCHITECTURE.md; raksha/BUILD_GUIDE.md safety rule 4 | API requires consent=true; visible PWA consent is next |
| Visible microphone activity; ephemeral buffer; discard in under 3 seconds | raksha/BUILD_GUIDE.md safety rule 5 | PWA capture is next |
| Advisory verdicts and no unsupported clone claims | raksha/CHANGELOG.md v0.4.0 | Implemented and tested |
| Citizen incident reporting stays separate from audio | raksha/ARCHITECTURE.md; citizen/api.py | Preserved; audio never enters report payload or spine telemetry |

## Explicit boundaries

- A browser PWA cannot intercept the operating system's live phone-call audio.
  The current planned microphone flow analyses an audio sample the user
  deliberately records; a true incoming-call integration needs a separately
  permissioned native Android CallScreeningService and platform review.
- No trained anti-spoof weights or validated benchmark corpus were found in
  the branch. The ONNX adapter is an integration contract, not a shipped model.
- The fallback never labels ordinary speech as genuine. Model performance,
  multilingual/accent performance, and real-world error rates are unmeasured.
- The API only accepts audio with explicit request consent. Audio is processed
  in request memory and is not written to disk, telemetry, or reports.
- The caller should only use a self-hosted/trusted API endpoint. A remote
  deployment necessarily receives the consented audio for processing.
