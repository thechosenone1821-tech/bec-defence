"""Compatibility re-export: the canonical Phase 3 verdict/legacy band table."""
from packages.contracts.bands import (
    LEGACY_BANDS, LEGACY_MAX, LEGACY_MIN, to_legacy_band,
)

__all__ = ["LEGACY_BANDS", "LEGACY_MIN", "LEGACY_MAX", "to_legacy_band"]
