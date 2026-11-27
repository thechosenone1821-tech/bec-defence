"""Phase 6 — canonical Infra/Sentinel detector boundary.

``detect`` is the one active detection contract. The legacy eight shield class
names remain available lazily for compatibility; they are not a second
registry and are not imported by the active runtime.
"""
from __future__ import annotations

from typing import Any

from .registry import (
    CONTRACT_VERSION, DETECTION_CONTRACT, DetectionResult, ORGAN_ALIASES,
    ORGAN_FIXTURES, ORGAN_SPECS, ORGANS, detect, detector_card, get_organ,
    known_organs,
)

_LEGACY_CLASS_NAMES = (
    "BECSpectralFilter", "CookieFluidTurbulence", "BraggFFTFirewall",
    "HessianLyapunovGuard", "PageCurveTrap", "LandauerThermalAudit",
    "HashimotoPercolation", "MutsEbpfRepair",
)


def _legacy_classes() -> tuple[type, ...]:
    from sentinel.shields.ring1_perimeter_identity import (
        BECSpectralFilter, CookieFluidTurbulence,
    )
    from sentinel.shields.ring2_ai_defense import (
        BraggFFTFirewall, HessianLyapunovGuard,
    )
    from sentinel.shields.ring3_endpoint_silicon import (
        LandauerThermalAudit, PageCurveTrap,
    )
    from sentinel.shields.ring4_network_healing import (
        HashimotoPercolation, MutsEbpfRepair,
    )
    return (BECSpectralFilter, CookieFluidTurbulence, BraggFFTFirewall,
            HessianLyapunovGuard, PageCurveTrap, LandauerThermalAudit,
            HashimotoPercolation, MutsEbpfRepair)


def __getattr__(name: str) -> Any:
    if name == "ORGAN_CLASSES":
        return _legacy_classes()
    if name in _LEGACY_CLASS_NAMES:
        return {cls.__name__: cls for cls in _legacy_classes()}[name]
    if name in {"BaseOrgan", "coerce_severity", "seal_event", "sign_rpc",
                "verify_rpc", "verify_sealed"}:
        from sentinel.shields import base_organ
        return getattr(base_organ, name)
    raise AttributeError(name)


__all__ = [
    "CONTRACT_VERSION", "DETECTION_CONTRACT", "DetectionResult",
    "ORGAN_SPECS", "ORGANS", "ORGAN_ALIASES", "ORGAN_FIXTURES",
    "known_organs", "get_organ", "detect", "detector_card",
    "ORGAN_CLASSES", *_LEGACY_CLASS_NAMES,
    "BaseOrgan", "coerce_severity", "seal_event", "sign_rpc", "verify_rpc",
    "verify_sealed",
]
