"""Organ detectors: frozen rules fire on attack features, stay silent otherwise."""

from __future__ import annotations

import pytest

from raksha.organs import ORGANS

ATTACK_PAYLOADS = {
    "voiceguard": {"synth_score": 0.93, "caller_reputation": 0.11},
    "docguard": {"bank_detail_changed": 1, "vendor_age_days": 19, "pdf_metadata_mismatch": 1},
    "sessionguard": {"token_reuse_count": 3, "geo_distance_km": 1420},
    "fileguard": {"encrypt_events_per_min": 940, "shadow_delete": 1, "entropy": 7.8},
    "netguard": {"egress_gb_24h": 2.9, "dest_reputation": 0.07, "beacon_interval_jitter": 0.02},
    "idguard": {"privilege_requests_24h": 28, "new_device": 1},
    "quorumguard": {"decision_probe_rate": 0.71, "signature_anomalies": 3},
    "tier0guard": {"crown_touch_events": 5},
}

CLEAN_PAYLOADS = {
    "voiceguard": {"synth_score": 0.2, "caller_reputation": 0.8},
    "docguard": {"bank_detail_changed": 0, "vendor_age_days": 900, "pdf_metadata_mismatch": 0},
    "sessionguard": {"token_reuse_count": 1, "geo_distance_km": 40},
    "fileguard": {"encrypt_events_per_min": 120, "shadow_delete": 0, "entropy": 4.5},
    "netguard": {"egress_gb_24h": 0.4, "dest_reputation": 0.7, "beacon_interval_jitter": 0.3},
    "idguard": {"privilege_requests_24h": 5, "new_device": 0},
    "quorumguard": {"decision_probe_rate": 0.1, "signature_anomalies": 0},
    "tier0guard": {"crown_touch_events": 1},
}

RULE_PREFIX = {"voiceguard": "VG-", "docguard": "DG-", "sessionguard": "SG-",
               "fileguard": "FG-", "netguard": "NG-", "idguard": "ID-",
               "quorumguard": "QG-", "tier0guard": "T0-"}


@pytest.mark.parametrize("name", sorted(ORGANS))
def test_attack_features_flag(name: str) -> None:
    rule = ORGANS[name].detect(ATTACK_PAYLOADS[name])
    assert rule is not None and rule.startswith(RULE_PREFIX[name])


@pytest.mark.parametrize("name", sorted(ORGANS))
def test_clean_features_stay_silent(name: str) -> None:
    assert ORGANS[name].detect(CLEAN_PAYLOADS[name]) is None


@pytest.mark.parametrize("name", sorted(ORGANS))
def test_missing_features_never_flag(name: str) -> None:
    """Contract R3: an event without a rule's features is never actionable."""
    assert ORGANS[name].detect({}) is None


def test_fileguard_boundary_at_400() -> None:
    assert ORGANS["fileguard"].detect({"encrypt_events_per_min": 400}) is not None
    assert ORGANS["fileguard"].detect({"encrypt_events_per_min": 399}) is None


def test_registry_holds_exactly_eight_organs() -> None:
    assert len(ORGANS) == 8
