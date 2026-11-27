"""Phase 6 — one Infra/Sentinel detection registry.

The eight Sentinel shield organs are represented by exactly one feature-rule
registry. ``detect(event)`` is the only active detection contract: it first
validates the shared signed envelope, then resolves one organ, then evaluates
only rules whose required features are present. Missing features degrade to
``no_detection``; unsigned, tampered, forged, malformed and unknown-organ
events are quarantined and never become findings.

This module is deterministic and import-safe. It does not import frozen Citizen
VoiceGuard/MAYA assets, an AI model, the legacy spine bus, or an executor.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Mapping

from packages.contracts.envelope import EnvelopeValidationError

CONTRACT_VERSION = "raksha-infra-detectors-v1"
DETECTION_CONTRACT = "detect(event) -> DetectionResult"
RING_1 = "RING_1_PERIMETER_IDENTITY"
RING_2 = "RING_2_AI_AGENT_DEFENSE"
RING_3 = "RING_3_ENDPOINT_SILICON"
RING_4 = "RING_4_NETWORK_HEALING"

VERIFICATION_VALID = "valid"


def _number(payload: Mapping[str, Any], key: str) -> float | None:
    """Return a strict finite number, or None when a feature is unusable."""
    value = payload.get(key)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    value = float(value)
    if value != value or value in (float("inf"), float("-inf")):
        return None
    return value


def _flag(payload: Mapping[str, Any], key: str) -> bool:
    return payload.get(key) == 1


def _at_least(key: str, threshold: float) -> Callable[[Mapping[str, Any]], bool]:
    return lambda payload: (_number(payload, key) is not None
                            and _number(payload, key) >= threshold)


def _above(key: str, threshold: float) -> Callable[[Mapping[str, Any]], bool]:
    return lambda payload: (_number(payload, key) is not None
                            and _number(payload, key) > threshold)


def _at_most(key: str, threshold: float) -> Callable[[Mapping[str, Any]], bool]:
    return lambda payload: (_number(payload, key) is not None
                            and _number(payload, key) <= threshold)


def _flag_is(key: str) -> Callable[[Mapping[str, Any]], bool]:
    return lambda payload: _flag(payload, key)


@dataclass(frozen=True)
class DetectionRule:
    rule_id: str
    required: tuple[str, ...]
    predicate: Callable[[Mapping[str, Any]], bool]
    reason: str


@dataclass(frozen=True)
class OrganSpec:
    name: str
    ring: str
    legacy_organ: str
    legacy_class: str
    rules: tuple[DetectionRule, ...]
    firing_payload: dict[str, Any] = field(default_factory=dict)
    silent_payload: dict[str, Any] = field(default_factory=dict)
    missing_payload: dict[str, Any] = field(default_factory=dict)

    def evaluate(self, payload: Mapping[str, Any]) -> tuple[str, str] | None:
        """Return ``(rule_id, reason)`` only when all required features exist."""
        if not isinstance(payload, Mapping):
            return None
        for rule in self.rules:
            if any(key not in payload for key in rule.required):
                continue  # missing features are not evidence
            try:
                if rule.predicate(payload):
                    return rule.rule_id, rule.reason
            except (TypeError, ValueError, KeyError):
                continue
        return None


@dataclass(frozen=True)
class DetectionResult:
    status: str
    state: str
    reason: str
    envelope: dict[str, Any] | None = None
    finding: dict[str, Any] | None = None
    quarantine: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status, "state": self.state, "reason": self.reason,
            "contract": CONTRACT_VERSION, "detection_contract": DETECTION_CONTRACT,
            "envelope": self.envelope, "finding": self.finding,
            "quarantine": self.quarantine,
        }


def _r(rule_id: str, required: tuple[str, ...], predicate: Callable[[Mapping[str, Any]], bool], reason: str) -> DetectionRule:
    return DetectionRule(rule_id, required, predicate, reason)


ORGAN_SPECS: tuple[OrganSpec, ...] = (
    OrganSpec(
        name="bec_spectral_filter", ring=RING_1,
        legacy_organ="BEC_SPECTRAL_PROJECTOR", legacy_class="BECSpectralFilter",
        rules=(_r("BEC-RANK1-CONDENSATION", ("condensation_ratio", "session_count"),
                  lambda p: (_number(p, "condensation_ratio") or 0.0) >= 0.72
                  and (_number(p, "session_count") or 0.0) >= 4,
                  "rank-1 session condensation with a sufficient sample window"),),
        firing_payload={"condensation_ratio": 0.91, "session_count": 12},
        silent_payload={"condensation_ratio": 0.41, "session_count": 12},
        missing_payload={"session_count": 12},
    ),
    OrganSpec(
        name="cookie_fluid_turbulence", ring=RING_1,
        legacy_organ="COOKIE_FLUID_TURBULENCE", legacy_class="CookieFluidTurbulence",
        rules=(_r("COOKIE-TURBULENT-REPLAY", ("reynolds_number", "cookie_replay_count"),
                  lambda p: (_number(p, "reynolds_number") or 0.0) > 2300
                  and (_number(p, "cookie_replay_count") or 0.0) >= 2,
                  "turbulent replay cadence above the laminar boundary"),),
        firing_payload={"reynolds_number": 3100.0, "cookie_replay_count": 3},
        silent_payload={"reynolds_number": 1400.0, "cookie_replay_count": 1},
        missing_payload={"cookie_replay_count": 3},
    ),
    OrganSpec(
        name="bragg_fft_firewall", ring=RING_2,
        legacy_organ="BRAGG_FFT_FIREWALL", legacy_class="BraggFFTFirewall",
        rules=(
            _r("BRAGG-FFT-PEAK", ("fft_peak_ratio",), _at_least("fft_peak_ratio", 0.65),
               "periodic adversarial suffix energy in the token spectrum"),
            _r("BRAGG-FIEDLER-SPLIT", ("fiedler_value",), _at_most("fiedler_value", 0.12),
               "document/system prompt token graph fracture"),
        ),
        firing_payload={"fft_peak_ratio": 0.88, "fiedler_value": 0.04},
        silent_payload={"fft_peak_ratio": 0.21, "fiedler_value": 0.55},
        missing_payload={"session_note": "no spectral features supplied"},
    ),
    OrganSpec(
        name="hessian_lyapunov_guard", ring=RING_2,
        legacy_organ="HESSIAN_LYAPUNOV_GUARD", legacy_class="HessianLyapunovGuard",
        rules=(_r("HESSIAN-LYAPUNOV-CLIFF", ("lyapunov_exponent", "curvature"),
                  lambda p: (_number(p, "lyapunov_exponent") or 0.0) > 0.35
                  and (_number(p, "curvature") or 0.0) > 1.5,
                  "sharp-curvature trajectory with positive Lyapunov drift"),),
        firing_payload={"lyapunov_exponent": 0.62, "curvature": 2.4},
        silent_payload={"lyapunov_exponent": 0.10, "curvature": 0.8},
        missing_payload={"curvature": 2.4},
    ),
    OrganSpec(
        name="page_curve_trap", ring=RING_3,
        legacy_organ="ENDPOINT_PAGE_CURVE", legacy_class="PageCurveTrap",
        rules=(
            _r("PAGECURVE-PARITY-BREAK", ("parity_break",), _flag_is("parity_break"),
               "4 KB honey-block XOR invariant broken on first write"),
            _r("PAGECURVE-ENCRYPT-BURST", ("encrypt_events_per_min",),
               _at_least("encrypt_events_per_min", 400),
               "mass encryption event burst"),
            _r("PAGECURVE-ENTROPY-SHADOW", ("entropy", "shadow_delete"),
               lambda p: (_number(p, "entropy") or 0.0) > 7.2 and _flag(p, "shadow_delete"),
               "high entropy plus shadow-copy deletion"),
        ),
        firing_payload={"parity_break": 1, "encrypt_events_per_min": 512},
        silent_payload={"parity_break": 0, "encrypt_events_per_min": 12,
                        "entropy": 3.1, "shadow_delete": 0},
        missing_payload={"entropy": 8.0},
    ),
    OrganSpec(
        name="landauer_thermal_audit", ring=RING_3,
        legacy_organ="LANDAUER_THERMAL_AUDITOR", legacy_class="LandauerThermalAudit",
        rules=(_r("LANDAUER-POWER-RESIDUAL", ("power_residual_w",),
                  _above("power_residual_w", 12.0),
                  "macroscopic package-power residual not explained by instruction rate"),),
        firing_payload={"power_residual_w": 18.5},
        silent_payload={"power_residual_w": 2.1},
        missing_payload={},
    ),
    OrganSpec(
        name="hashimoto_percolation", ring=RING_4,
        legacy_organ="HASHIMOTO_PERCOLATION", legacy_class="HashimotoPercolation",
        rules=(_r("HASHIMOTO-CASCADE-RISK", ("spectral_radius",),
                  _above("spectral_radius", 1.0),
                  "non-backtracking spectral radius above the cascade threshold"),),
        firing_payload={"spectral_radius": 1.42},
        silent_payload={"spectral_radius": 0.82},
        missing_payload={},
    ),
    OrganSpec(
        name="muts_ebpf_repair", ring=RING_4,
        legacy_organ="MUTS_EBPF_REPAIR", legacy_class="MutsEbpfRepair",
        rules=(
            _r("MUTS-MISMATCH-REPAIR", ("invariant_mismatch",), _flag_is("invariant_mismatch"),
               "dual-strand invariant mismatch observed"),
            _r("MUTS-REPEAT-BLOCKED", ("repeat_mismatch", "shield_spliced"),
               lambda p: _flag(p, "repeat_mismatch") and _flag(p, "shield_spliced"),
               "repeat exploit blocked by an already spliced simulated shield"),
        ),
        firing_payload={"invariant_mismatch": 1, "repeat_mismatch": 0},
        silent_payload={"invariant_mismatch": 0, "repeat_mismatch": 0, "shield_spliced": 0},
        missing_payload={"repeat_mismatch": 1},
    ),
)

ORGANS: dict[str, OrganSpec] = {spec.name: spec for spec in ORGAN_SPECS}

# Compatibility aliases: legacy organ identifiers and enterprise-style names
# point at the same eight records. No second registry is created.
ORGAN_ALIASES: dict[str, str] = {
    spec.legacy_organ.lower(): spec.name for spec in ORGAN_SPECS
}
ORGAN_ALIASES.update({
    "docguard": "bragg_fft_firewall",
    "sessionguard": "cookie_fluid_turbulence",
    "fileguard": "page_curve_trap",
    "netguard": "hashimoto_percolation",
    "idguard": "muts_ebpf_repair",
    "quorumguard": "hessian_lyapunov_guard",
    "tier0guard": "landauer_thermal_audit",
    "voiceguard": "cookie_fluid_turbulence",  # Infra alias only; NOT Citizen VoiceGuard
})
ORGAN_FIXTURES: dict[str, dict[str, dict[str, Any]]] = {
    spec.name: {
        "firing": dict(spec.firing_payload),
        "silent": dict(spec.silent_payload),
        "missing": dict(spec.missing_payload),
    }
    for spec in ORGAN_SPECS
}


def known_organs() -> tuple[str, ...]:
    return tuple(sorted(ORGANS))


def get_organ(name: str) -> OrganSpec | None:
    if not isinstance(name, str):
        return None
    key = name.strip().lower().replace("-", "_").replace(" ", "_")
    return ORGANS.get(ORGAN_ALIASES.get(key, key))


def _quarantine(raw: dict[str, Any], state: str, reason: str) -> DetectionResult:
    item = {
        "event_id": str(raw.get("event_id") or ""),
        "organ": str(raw.get("organ") or ""),
        "state": state,
        "reason": reason,
        "actionable": False,
        "detection_performed": False,
    }
    return DetectionResult(status="quarantined", state=state, reason=reason,
                           quarantine=item)


def detect(event: Mapping[str, Any], *, key: Any = None) -> DetectionResult:
    """One signed-event detection contract.

    Returns a :class:`DetectionResult` with status ``quarantined``,
    ``unknown_organ``, ``no_detection`` or ``finding``. A verified event is
    never described as a finding unless a rule's complete feature set fired.
    """
    raw = dict(event) if isinstance(event, Mapping) else {}
    try:
        from packages.contracts.envelope import validate_envelope
        envelope = validate_envelope(raw, key=key, require_signature=True)
    except EnvelopeValidationError as exc:
        return _quarantine(raw, "invalid_envelope", f"malformed envelope: {exc}")
    except Exception as exc:  # total: a detector failure must not become a finding
        return _quarantine(raw, "invalid_envelope", f"envelope validation failed: {exc}")

    env = envelope.to_dict()
    state = env["signature"]["state"]
    if not envelope.verified or not envelope.actionable:
        reason = "signature not verified — quarantined before detection"
        if state == "unsigned":
            reason = "unsigned event — quarantined before detection"
        elif state == "tampered":
            reason = "tampered or forged signature — quarantined before detection"
        return _quarantine(raw, state, reason)

    organ = get_organ(envelope.organ)
    if organ is None:
        return _quarantine(raw, "unknown_organ",
                           f"unknown organ {envelope.organ!r} — no detector executed")

    matched = organ.evaluate(envelope.payload)
    if matched is None:
        return DetectionResult(
            status="no_detection", state=state,
            reason="verified; required features absent or benign — no accusation",
            envelope=env,
        )
    rule_id, why = matched
    finding = {
        "organ": organ.name, "ring": organ.ring, "rule_id": rule_id,
        "reason": why, "event_id": envelope.event_id, "ts": envelope.ts,
        "campaign_id": str(raw.get("campaign_id") or ""),
        "case_id": str(raw.get("case_id") or ""), "leg": envelope.leg,
        "entity": str(raw.get("entity") or envelope.entities.get("entity") or ""),
        "severity": envelope.severity_raw, "summary": envelope.signal_type,
        "payload": dict(envelope.payload), "contract": CONTRACT_VERSION,
        "verified": True, "actionable": True,
    }
    return DetectionResult(status="finding", state=state,
                           reason=f"{organ.name} fired {rule_id}",
                           envelope=env, finding=finding)


def detector_card() -> dict[str, Any]:
    return {
        "contract": CONTRACT_VERSION,
        "detection_contract": DETECTION_CONTRACT,
        "organs": known_organs(),
        "rings": sorted({spec.ring for spec in ORGAN_SPECS}),
        "registry_count": 1,
        "organ_count": len(ORGANS),
        "fixtures": {name: sorted(bundle) for name, bundle in ORGAN_FIXTURES.items()},
        "quarantine_before_detection": True,
        "missing_features": "no_detection",
        "frozen_voiceguard_integrated": False,
    }


__all__ = [
    "CONTRACT_VERSION", "DETECTION_CONTRACT", "DetectionRule", "OrganSpec",
    "DetectionResult", "ORGAN_SPECS", "ORGANS", "ORGAN_ALIASES", "ORGAN_FIXTURES",
    "known_organs", "get_organ", "detect", "detector_card",
]
