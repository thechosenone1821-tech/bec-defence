"""Legacy organ RPC band mapping.

The Governor's legacy organ RPC expects a single float in the fixed
band 0.25–0.99. MessageGuard's own verdict bands are categorical
(LOW / MODERATE / HIGH / CRITICAL), so this module is the ONLY place
where the categorical verdict is translated into the legacy numeric
contract — keeping the scorer free of legacy concerns and avoiding any
contract change on the shared graph.

Mapping (deliberately coarse, band-floored):

    LOW       -> 0.25
    MODERATE  -> 0.50
    HIGH      -> 0.75
    CRITICAL  -> 0.99
"""

LEGACY_BANDS = {
    "LOW": 0.25,
    "MODERATE": 0.50,
    "HIGH": 0.75,
    "CRITICAL": 0.99,
}

# Contract bounds of the legacy organ RPC.
LEGACY_MIN = 0.25
LEGACY_MAX = 0.99


def to_legacy_band(verdict: str) -> float:
    """Translate a MessageGuard verdict band into the legacy 0.25–0.99 float.

    Raises ValueError on an unknown verdict instead of guessing — the
    legacy contract has exactly four accepted bands.
    """
    if verdict not in LEGACY_BANDS:
        raise ValueError(f"unknown verdict band: {verdict!r}")
    value = LEGACY_BANDS[verdict]
    assert LEGACY_MIN <= value <= LEGACY_MAX
    return value
