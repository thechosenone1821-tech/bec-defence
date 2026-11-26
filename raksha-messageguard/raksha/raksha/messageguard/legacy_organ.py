"""Adapter for the Governor's legacy organ RPC.

The legacy organ RPC validates its numeric confidence field to the closed
band ``[0.25, 0.99]``. MessageGuard's raw score lives in ``[0.0, 1.0]``, so
this adapter maps every verdict into that band WITHOUT changing the contract:
the same scorer can feed the shared graph unchanged.

Two mapping modes are provided:

``band`` (default) — piecewise-linear onto each verdict band's legacy
interval, so the legacy number stays consistent with the band label:
    LOW      [0.25, 0.44]   (raw 0.00-0.20)
    MODERATE [0.45, 0.69]   (raw 0.20-0.45)
    HIGH     [0.70, 0.98]   (raw 0.45-0.70)
    CRITICAL 0.99           (raw >= 0.70)

The mapping is monotone non-decreasing and label-consistent: a LOW verdict
can never surface as a HIGH-looking number downstream. The band label in the
payload remains the authoritative verdict; the numeric field is advisory.

``clamp`` — the literal reading: floor at 0.25, cap at 0.99, pass through
everything in between.

Field names below follow the legacy organ contract as far as Part 3 knows it;
the only constraint the spec fixes is the 0.25-0.99 numeric band. If the real
contract names fields differently, adjust ``LegacyOrganPayload.to_dict()``
in one place — the mapping logic is unaffected.
"""

from __future__ import annotations

from dataclasses import dataclass

from .types import Band, Verdict

__all__ = ["legacy_confidence", "LegacyOrganPayload", "to_legacy_organ_payload"]

_LEGACY_MIN = 0.25
_LEGACY_MAX = 0.99

_BAND_INTERVALS: dict[Band, tuple[float, float]] = {
    Band.LOW: (0.25, 0.44),
    Band.MODERATE: (0.45, 0.69),
    Band.HIGH: (0.70, 0.98),
    Band.CRITICAL: (0.99, 0.99),
}

# raw-score ranges that correspond to each band (mirror types.BAND_THRESHOLDS)
_BAND_RAW_SPANS: dict[Band, tuple[float, float]] = {
    Band.LOW: (0.00, 0.20),
    Band.MODERATE: (0.20, 0.45),
    Band.HIGH: (0.45, 0.70),
    Band.CRITICAL: (0.70, 1.00),
}


def legacy_confidence(score: float, mode: str = "band") -> float:
    """Map a raw score in [0, 1] into the legacy organ band [0.25, 0.99]."""
    if mode == "clamp":
        value = min(_LEGACY_MAX, max(_LEGACY_MIN, score))
    elif mode == "band":
        band = Band.LOW
        from .types import band_for

        band = band_for(score)
        lo, hi = _BAND_INTERVALS[band]
        raw_lo, raw_hi = _BAND_RAW_SPANS[band]
        span = (raw_hi - raw_lo) or 1.0
        t = min(1.0, max(0.0, (score - raw_lo) / span))
        value = lo + (hi - lo) * t
        value = min(_LEGACY_MAX, max(_LEGACY_MIN, value))
    else:
        raise ValueError(f"unknown mode: {mode!r}")
    return round(value, 2)


@dataclass(frozen=True)
class LegacyOrganPayload:
    """Payload shaped for the legacy organ RPC."""

    organ: str
    confidence: float      # always within [0.25, 0.99]
    band: str              # authoritative verdict label
    reason_codes: tuple[str, ...]
    message_lang: str
    deterministic: bool = True

    def to_dict(self) -> dict:
        return {
            "organ": self.organ,
            "confidence": self.confidence,
            "band": self.band,
            "reason_codes": list(self.reason_codes),
            "message_lang": self.message_lang,
            "deterministic": self.deterministic,
        }


def to_legacy_organ_payload(verdict: Verdict, mode: str = "band") -> LegacyOrganPayload:
    """Build the legacy organ RPC payload from a MessageGuard verdict."""
    return LegacyOrganPayload(
        organ="messageguard",
        confidence=legacy_confidence(verdict.score, mode=mode),
        band=verdict.band.value,
        reason_codes=tuple(dict.fromkeys(r.code for r in verdict.reasons)),
        message_lang=verdict.lang,
    )
