"""Canonical legacy-organ adapter for the one MessageGuard result.

Phase 5 ports the alternative package's useful adapter behaviour without
porting its second scorer or its ``msg.*`` reason codes. The input is the
canonical ``analyze()`` / ``score_message()`` dictionary. Two monotone modes
map the diagnostic score into the legacy RPC's closed 0.25-0.99 numeric band:

``band``   piecewise-linear inside each verdict band (label-consistent);
``clamp``  literal floor/cap of the raw score.

The categorical band remains authoritative; the numeric confidence is
advisory. This is an operator/adapter payload, not citizen-facing copy, and
it contains no raw score, no matched phrases and no PII.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Tuple

from packages.contracts.bands import LEGACY_MAX, LEGACY_MIN, band

from .detect import detect_language

__all__ = [
    "LegacyOrganPayload", "legacy_confidence", "to_legacy_organ_payload",
]

_BAND_INTERVALS = {
    "LOW": (0.25, 0.44),
    "MODERATE": (0.45, 0.69),
    "HIGH": (0.70, 0.98),
    "CRITICAL": (0.99, 0.99),
}
_BAND_RAW_SPANS = {
    "LOW": (0.00, 0.20),
    "MODERATE": (0.20, 0.45),
    "HIGH": (0.45, 0.70),
    "CRITICAL": (0.70, 1.00),
}


def _score_from(result: Any) -> float:
    if isinstance(result, Mapping):
        value = result.get("score", 0.0)
    else:
        value = result
    return min(1.0, max(0.0, float(value)))


def legacy_confidence(result: Any, mode: str = "band") -> float:
    """Map a canonical result (or raw score) into 0.25-0.99."""
    score = _score_from(result)
    if mode == "clamp":
        value = min(LEGACY_MAX, max(LEGACY_MIN, score))
    elif mode == "band":
        verdict = band(score)
        lo, hi = _BAND_INTERVALS[verdict]
        raw_lo, raw_hi = _BAND_RAW_SPANS[verdict]
        span = (raw_hi - raw_lo) or 1.0
        t = min(1.0, max(0.0, (score - raw_lo) / span))
        value = min(LEGACY_MAX, max(LEGACY_MIN, lo + (hi - lo) * t))
    else:
        raise ValueError(f"unknown mode: {mode!r}")
    return round(value, 2)


@dataclass(frozen=True)
class LegacyOrganPayload:
    """Payload shaped for the legacy organ RPC."""

    organ: str
    confidence: float
    band: str
    reason_codes: Tuple[str, ...]
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


def to_legacy_organ_payload(result: Mapping[str, Any],
                            mode: str = "band") -> LegacyOrganPayload:
    """Build the legacy organ RPC payload from one canonical result dict."""
    score = _score_from(result)
    verdict = str(result.get("verdict") or band(score)).upper()
    codes: list[str] = []
    for code in result.get("reason_codes") or []:
        if str(code) not in codes:
            codes.append(str(code))
    if not codes:
        for detail in result.get("reason_details") or []:
            if isinstance(detail, Mapping) and detail.get("code"):
                code = str(detail["code"])
                if code not in codes:
                    codes.append(code)
    text = str(result.get("text") or "")
    message_lang = str(result.get("detector_lang") or "auto")
    if message_lang == "auto" and text:
        message_lang = detect_language(text)
    return LegacyOrganPayload(
        organ="messageguard",
        confidence=legacy_confidence(result, mode=mode),
        band=verdict,
        reason_codes=tuple(codes),
        message_lang=message_lang,
    )
