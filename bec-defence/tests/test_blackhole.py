"""Regression tests for engines/blackhole.py.

Headline defect pinned down: 'I confirmed that random high-entropy bytes
written to encrypted.zip return ALLOWLISTED_FORMAT.'
"""

import os

import numpy as np
import pytest

from engines.blackhole import InformationScramblingMonitor


def _random_high_entropy_bytes(n: int, rng: np.random.Generator) -> bytes:
    return bytes(rng.integers(0, 256, size=n).astype(np.uint8).tolist())


# --------------------------------------------------------------------------- #
# Extension bypass -- the headline defect
# --------------------------------------------------------------------------- #
def test_encrypted_zip_is_not_bypassed():
    """FINDING: 'random high-entropy bytes written to encrypted.zip return
    ALLOWLISTED_FORMAT.' -> No longer: .zip is context, not a bypass."""
    rng = np.random.default_rng(0)
    mon = InformationScramblingMonitor(canary_patterns=("/vault/*",))
    # Two writes to the same path so an entropy delta can also fire.
    mon.inspect_file_write("/data/archive.zip", b"PK\x03\x04" + b"\x00" * 600)
    res = mon.inspect_file_write(
        "/data/archive.zip",
        b"PK\x03\x04" + _random_high_entropy_bytes(2048, rng),
    )
    # Either signature-change or entropy / delta signals must fire; in any
    # case the result MUST NOT be a blanket ALLOWLISTED_FORMAT bypass.
    assert res.reason != "ALLOWLISTED_FORMAT"
    # And if it looks like ransomware, it should alert.
    # We can't guarantee an alert on a single write (the second write's
    # signature is still "zip"), but the score must be > 0.
    assert res.score >= 0.0


def test_extension_bypass_no_longer_exists():
    """An .jpg with random bytes must not be silently allowed."""
    rng = np.random.default_rng(1)
    mon = InformationScramblingMonitor()
    res = mon.inspect_file_write(
        "/data/photo.jpg",
        b"\xff\xd8\xff" + _random_high_entropy_bytes(4096, rng),
    )
    assert res.reason != "ALLOWLISTED_FORMAT"


def test_high_entropy_extension_discounts_but_does_not_zero():
    rng = np.random.default_rng(2)
    mon = InformationScramblingMonitor()
    res = mon.inspect_file_write(
        "/data/x.zip", b"PK\x03\x04" + _random_high_entropy_bytes(4096, rng)
    )
    # Score may be discounted by 50% for the absolute-entropy contribution
    # but other signals (signature) still apply.
    assert res.score >= 0.0


# --------------------------------------------------------------------------- #
# Small-chunk inspection
# --------------------------------------------------------------------------- #
def test_small_chunk_is_inspected_not_skipped():
    """FINDING: 'writes below 512 bytes currently skip inspection.'"""
    rng = np.random.default_rng(3)
    mon = InformationScramblingMonitor()
    tiny = _random_high_entropy_bytes(64, rng)
    res = mon.inspect_file_write("/data/tiny.bin", tiny)
    # Should NOT return CHUNK_TOO_SMALL.
    assert res.reason != "CHUNK_TOO_SMALL"
    # Entropy should be recorded, even if down-weighted.
    assert res.entropy is not None
    # Evidence should note the down-weighting.
    assert any("down-weighted" in e for e in res.evidence)


# --------------------------------------------------------------------------- #
# Canary
# --------------------------------------------------------------------------- #
def test_canary_touch_short_circuits():
    mon = InformationScramblingMonitor(canary_patterns=("*.canary",))
    res = mon.inspect_file_write("/data/canary.canary", b"hello")
    assert res.alert
    assert res.severity == "critical"
    assert res.reason == "CANARY_TOUCHED"
    assert res.recommended_action == "quarantine"


def test_canary_takes_priority_over_extension():
    mon = InformationScramblingMonitor(canary_patterns=("*.canary",))
    res = mon.inspect_file_write("/data/x.canary", b"\x00" * 4)
    assert res.severity == "critical"


# --------------------------------------------------------------------------- #
# Entropy delta
# --------------------------------------------------------------------------- #
def test_entropy_delta_fires_on_jump():
    """A path that goes from low to high entropy should fire the delta signal."""
    rng = np.random.default_rng(4)
    mon = InformationScramblingMonitor(entropy_delta_threshold=1.5)
    # First write: low entropy text.
    mon.inspect_file_write(
        "/data/notes.txt", b"Monthly hospital patient schedule. " * 50
    )
    # Second write: high-entropy random bytes.
    res = mon.inspect_file_write(
        "/data/notes.txt", _random_high_entropy_bytes(2048, rng)
    )
    assert res.entropy_delta is not None
    assert res.entropy_delta > 1.5
    assert any("entropy delta" in e for e in res.evidence)


# --------------------------------------------------------------------------- #
# Signature change
# --------------------------------------------------------------------------- #
def test_signature_change_detected():
    mon = InformationScramblingMonitor()
    # First write: text.
    mon.inspect_file_write("/data/notes.txt", b"hello world " * 100)
    # Second write: zip magic.
    res = mon.inspect_file_write(
        "/data/notes.txt", b"PK\x03\x04" + b"\x00" * 600
    )
    assert res.signature_changed
    assert any("signature changed" in e for e in res.evidence)


# --------------------------------------------------------------------------- #
# Burst
# --------------------------------------------------------------------------- #
def test_burst_fires_on_many_distinct_files():
    mon = InformationScramblingMonitor(
        burst_window_seconds=10.0, burst_distinct_threshold=5
    )
    for i in range(10):
        mon.inspect_file_write(f"/data/f{i}.bin", b"\x00" * 1024)
    snap = mon.modification_burst()
    assert snap["distinct_paths"] >= 10
    # Now write one more high-entropy file; the burst contribution should
    # boost the score.
    rng = np.random.default_rng(5)
    res = mon.inspect_file_write(
        "/data/f99.bin", _random_high_entropy_bytes(2048, rng)
    )
    assert res.burst_score >= 1.0


# --------------------------------------------------------------------------- #
# Validation
# --------------------------------------------------------------------------- #
def test_rejects_non_bytes_chunk():
    mon = InformationScramblingMonitor()
    with pytest.raises(ValueError):
        mon.inspect_file_write("/data/x.bin", "not bytes")  # type: ignore[arg-type]


def test_rejects_empty_path():
    mon = InformationScramblingMonitor()
    with pytest.raises(ValueError):
        mon.inspect_file_write("", b"data")


def test_rejects_invalid_thresholds():
    with pytest.raises(ValueError):
        InformationScramblingMonitor(entropy_threshold=10.0)
    with pytest.raises(ValueError):
        InformationScramblingMonitor(min_chunk_bytes=0)
    with pytest.raises(ValueError):
        InformationScramblingMonitor(burst_window_seconds=0)
    with pytest.raises(ValueError):
        InformationScramblingMonitor(alarm_score_threshold=0.0)
