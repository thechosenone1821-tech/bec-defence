"""Phase 3 — one verdict-band table and one legacy organ band map."""
from __future__ import annotations

VERDICT_ORDER = ("LOW", "MODERATE", "HIGH", "CRITICAL")
BAND_EDGES = ((0.20, "LOW"), (0.45, "MODERATE"), (0.70, "HIGH"))
LEGACY_BANDS = {
    "LOW": 0.25,
    "MODERATE": 0.50,
    "HIGH": 0.75,
    "CRITICAL": 0.99,
}
LEGACY_MIN = 0.25
LEGACY_MAX = 0.99


def band(score: float) -> str:
    """Map a final MessageGuard score to a verdict band."""
    for edge, name in BAND_EDGES:
        if score < edge:
            return name
    return "CRITICAL"


def verdict_at_least(verdict: str, minimum: str) -> bool:
    try:
        return VERDICT_ORDER.index(str(verdict).upper()) >= VERDICT_ORDER.index(
            str(minimum).upper()
        )
    except ValueError:
        return False


def to_legacy_band(verdict: str) -> float:
    """Translate a categorical verdict into the legacy 0.25-0.99 float."""
    if verdict not in LEGACY_BANDS:
        raise ValueError(f"unknown verdict band: {verdict!r}")
    value = LEGACY_BANDS[verdict]
    assert LEGACY_MIN <= value <= LEGACY_MAX
    return value


__all__ = [
    "VERDICT_ORDER", "BAND_EDGES", "LEGACY_BANDS", "LEGACY_MIN", "LEGACY_MAX",
    "band", "verdict_at_least", "to_legacy_band",
]
