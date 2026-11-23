# VoiceGuard — verified feature inventory

> Consolidated for the VoiceGuard build on 2026-11-23. The supplied
> main_final branch did not contain a file named features.md, nor any path or
> reference named Maya. This inventory records only features explicitly
> documented by the existing RAKSHA sources; it does not reproduce a missing
> specification.

## Product intent

VoiceGuard is the voice-screening component of RAKSHA Citizen. It provides
short, advisory screening of user-consented caller/voice audio, with local
inference where a validated on-device anti-spoof model is installed. It is not
an identity verifier and never makes a finding of fraud by itself.

## Source-backed requirements and delivery status

| Requirement | Source in the repository | Build status |
|---|---|---|
| Screen a short caller-audio window (target: 2 seconds) | raksha/ARCHITECTURE.md | Implemented for a user-started microphone sample in the PWA; direct phone-call audio is not exposed by the PWA |
| Spectral descriptors plus LFCC/LPCC lineage | raksha/ARCHITECTURE.md | Spectral, LFCC, and LPCC summaries implemented |
| On-device anti-spoof model interface | raksha/ARCHITECTURE.md; raksha/BUILD_GUIDE.md M3 | Optional ONNX adapter planned; model weights are not present in this repository |
| Deterministic fallback when no model is available | raksha/BUILD_GUIDE.md M3; existing voiceguard.py | Implemented; flags only degenerate signal anomalies and leaves ordinary speech inconclusive |
| No audio transfer without consent | raksha/ARCHITECTURE.md; raksha/BUILD_GUIDE.md safety rule 4 | To be enforced by the API and PWA in later phases |
| Visible microphone activity; ephemeral ring buffer; discard in under 3 seconds | raksha/BUILD_GUIDE.md safety rule 5 | To be implemented in the PWA |
| Advisory verdicts and no unsupported clone claims | raksha/CHANGELOG.md v0.4.0 | Preserved and made explicit in analysis output |
| One-tap Citizen report remains separate from audio screening | raksha/ARCHITECTURE.md; citizen/api.py | Existing signed report rail preserved; no raw audio is attached to reports |

## Explicit boundaries

- The browser app cannot intercept the operating system's live phone-call
  audio. A true incoming-call integration requires a separately permissioned
  Android CallScreeningService/native application, which is not present here.
- No trained anti-spoof weights or validated benchmark corpus were found in
  the branch. ONNX inference is therefore an adapter, not a claim that a model
  ships today.
- The heuristic fallback must never label normal speech as genuine. Model
  performance, multilingual/accent performance, and real-world error rates
  remain unmeasured until a model and representative consented evaluation set
  are supplied.
- No audio is written to disk, included in telemetry, or attached to reports.
