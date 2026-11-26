"""Legacy organ RPC adapter tests.

The spec fixes one hard constraint: the numeric confidence fed to the
Governor's legacy organ RPC must lie in the closed band [0.25, 0.99].
"""

import pytest

from raksha.messageguard import assess, legacy_confidence, to_legacy_organ_payload
from raksha.messageguard.types import Band

LEGACY_MIN, LEGACY_MAX = 0.25, 0.99


class TestLegacyConfidenceRange:
    @pytest.mark.parametrize("mode", ["band", "clamp"])
    def test_every_score_maps_into_band(self, mode):
        for i in range(0, 1001):
            c = legacy_confidence(i / 1000, mode=mode)
            assert LEGACY_MIN <= c <= LEGACY_MAX

    def test_endpoints(self):
        assert legacy_confidence(0.0) == 0.25
        assert legacy_confidence(1.0) == 0.99

    def test_band_mode_is_monotone(self):
        values = [legacy_confidence(i / 1000, mode="band") for i in range(0, 1001)]
        for a, b in zip(values, values[1:]):
            assert b >= a

    def test_band_mode_is_label_consistent(self):
        """The legacy number must never contradict the verdict band."""
        from raksha.messageguard.types import band_for

        intervals = {
            Band.LOW: (0.25, 0.44),
            Band.MODERATE: (0.45, 0.69),
            Band.HIGH: (0.70, 0.98),
            Band.CRITICAL: (0.99, 0.99),
        }
        for i in range(0, 1001):
            s = i / 1000
            lo, hi = intervals[band_for(s)]
            c = legacy_confidence(s)
            # allow 1-hundredth rounding slack at interval edges
            assert lo - 0.005 <= c <= hi + 0.005, (s, band_for(s), c)


class TestClampMode:
    def test_clamp_floors_low_scores(self):
        assert legacy_confidence(0.10, mode="clamp") == 0.25

    def test_clamp_passthrough_inside_band(self):
        assert legacy_confidence(0.60, mode="clamp") == 0.60

    def test_unknown_mode_raises(self):
        with pytest.raises(ValueError):
            legacy_confidence(0.5, mode="nope")


class TestOrganPayload:
    def test_payload_shape_and_band(self):
        verdict = assess("Share your OTP at bit.ly/x within 24 hours or account will be blocked")
        payload = to_legacy_organ_payload(verdict)
        d = payload.to_dict()
        assert payload.organ == "messageguard"
        assert payload.band == "CRITICAL"
        assert payload.confidence == 0.99
        assert LEGACY_MIN <= payload.confidence <= LEGACY_MAX
        assert payload.deterministic is True
        assert set(d) == {
            "organ",
            "confidence",
            "band",
            "reason_codes",
            "message_lang",
            "deterministic",
        }

    def test_reason_codes_deduped_and_prefixed(self):
        verdict = assess("Share your OTP. CBI officer. Processing fee. bit.ly/x. Last warning.")
        payload = to_legacy_organ_payload(verdict)
        codes = list(payload.reason_codes)
        assert len(codes) == len(set(codes))
        assert all(c.startswith("msg.") for c in codes)

    def test_low_verdict_maps_to_floor(self):
        verdict = assess("hello there")
        payload = to_legacy_organ_payload(verdict)
        assert payload.band == "LOW"
        assert payload.confidence == 0.25
        assert payload.reason_codes == ()
