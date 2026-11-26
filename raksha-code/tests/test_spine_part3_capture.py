"""CITIZEN SPINE — PART THREE: Capture & Consent.

Privacy bugs are the ones that cannot be undone: a clip that was screened
without consent cannot be unscreened, and a buffer that was not wiped cannot be
un-wiped later. So the four invariants here are tested from the outside — through
the HTTP surface a real client uses — as well as in the class.

  1. Consent-first  no sample is processed before consent, and the refusal is reported
  2. Auditable      destroy() reports the real buffer, and says so when it cannot
  3. Bounded        nothing larger than the documented window is accepted
  4. Total          malformed input produces a refusal, never a 500

Two of these tests exist because the code was wrong: consent was advertised and
not enforced, and destroy() wiped a buffer that had never held the samples.
"""

import os
import sys

import numpy as np
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from citizen.api import build_app
from citizen.voiceguard import capture as CAP
from citizen.voiceguard.capture import (MAX_SCREEN_SAMPLES, RING_SAMPLES,
                                        CaptureSession, RetentionError, refusal,
                                        screen_with_consent)


@pytest.fixture()
def client():
    return TestClient(build_app())


def clip(n=16_000):
    return [0.01 * ((i % 17) - 8) for i in range(n)]


# --------------------------------------------------------------------------- #
# 1. Consent-first
# --------------------------------------------------------------------------- #
class TestConsentFirst:
    def test_the_api_refuses_audio_without_consent(self, client):
        """The defect this test was written for.

        `/retention` advertised `"consent_required": true` while
        `/screen_voice` never checked it. The guarantee existed only in
        `CaptureSession`, which nothing outside the tests constructed.
        """
        r = client.post("/api/citizen/screen_voice", json={"samples": clip()})
        assert r.status_code == 403

    def test_the_refusal_is_showable_copy_not_an_error_string(self, client):
        """A client must be able to *display* why it was refused."""
        detail = client.post("/api/citizen/screen_voice",
                             json={"samples": clip()}).json()["detail"]
        assert detail["title"] and detail["action"]
        assert detail["helpline"] == "1930"
        assert detail["lang"] in ("en", "hi", "te")

    @pytest.mark.parametrize("lang", ["en", "hi", "te"])
    def test_the_refusal_is_localised(self, client, lang):
        detail = client.post("/api/citizen/screen_voice",
                             json={"samples": clip(), "lang": lang}).json()["detail"]
        assert detail["lang"] == lang
        assert detail["title"] == CAP.REFUSAL_COPY["consent"][lang][0]

    @pytest.mark.parametrize("consented", [False, "true", "yes", 1, 1.0, [], {}, None])
    def test_only_explicit_true_counts_as_consent(self, consented):
        """Junk truthiness is not consent.

        Phase 3 found `campaign_linked="nope"` producing evidence from nothing;
        the same class of bug here would be "yes" recorded as permission to
        listen. `1` and `1.0` are excluded from acceptance for the same reason:
        a number is not a person saying yes.
        """
        out = screen_with_consent(np.ones(1000), consented)
        assert out["accepted"] is False, f"{consented!r} was treated as consent"
        assert out["audio_processed"] is False

    def test_consent_granted_lets_the_audio_through(self, client):
        r = client.post("/api/citizen/screen_voice",
                        json={"consent": True, "samples": clip()})
        assert r.status_code == 200
        assert r.json()["verdict"]

    def test_a_refusal_never_reaches_the_scoring_layer(self, client, monkeypatch):
        """Consent is not a guard clause in front of scoring — it is a wall.

        If the model were called before the gate, a refusal would still have
        processed the audio and the 403 would be theatre.
        """
        import citizen.api as api_mod
        called = []
        monkeypatch.setattr(api_mod, "score_voice", lambda s: called.append(s) or {})
        client.post("/api/citizen/screen_voice", json={"samples": clip()})
        assert called == [], "the model ran on audio the user never consented to"


# --------------------------------------------------------------------------- #
# 2. Auditable retention
# --------------------------------------------------------------------------- #
class TestAuditableRetention:
    def test_destroy_reports_the_buffer_that_actually_held_the_audio(self):
        """The defect this test was written for.

        `ingest()` validated the window and returned it without ever writing to
        `self.ring`, so `destroy()` reported `zero_passes: 1` about a buffer that
        had never held anything. The accounting described a wipe that protected
        nothing.
        """
        s = CaptureSession()
        s.require_consent(True)
        for _ in range(3):
            s.ingest(np.ones(16_000))
        report = s.destroy()
        assert report["buffered_samples"] == 48_000, report
        assert report["screens"] == 3

    def test_destroy_says_zero_when_nothing_was_ingested(self):
        s = CaptureSession()
        s.require_consent(True)
        assert s.destroy()["buffered_samples"] == 0

    def test_the_ring_is_actually_zeroed(self):
        s = CaptureSession()
        s.require_consent(True)
        s.ingest(np.ones(16_000))
        s.destroy()
        assert not np.any(s.ring.read())

    def test_retention_accounting_survives_many_screens(self):
        s = CaptureSession()
        s.require_consent(True)
        for _ in range(50):
            s.ingest(np.ones(1000))
        assert s.destroy()["screens"] == 50

    def test_destroy_is_idempotent(self):
        s = CaptureSession()
        s.require_consent(True)
        s.ingest(np.ones(1000))
        first = s.destroy()
        second = s.destroy()
        assert first["destroyed"] and second["destroyed"]
        assert second["buffered_samples"] == 0

    def test_the_documented_limit_is_the_enforced_limit(self):
        policy = CAP.retention_policy()
        assert policy["max_samples_per_screen"] == MAX_SCREEN_SAMPLES
        assert policy["ring_seconds"] == CAP.RING_SECONDS
        assert policy["consent_required"] is True

    def test_the_class_still_refuses_without_consent(self):
        """The old contract keeps working — the API gate adds a second wall."""
        s = CaptureSession()
        with pytest.raises(RetentionError):
            s.ingest(np.ones(100))


# --------------------------------------------------------------------------- #
# 3. Bounded
# --------------------------------------------------------------------------- #
class TestBounded:
    def test_the_api_rejects_an_oversized_window_with_413(self, client):
        r = client.post("/api/citizen/screen_voice",
                        json={"consent": True, "samples": [0.0] * 250_000})
        assert r.status_code == 413

    def test_the_gate_rejects_one_sample_over_the_ceiling(self):
        out = screen_with_consent(np.ones(MAX_SCREEN_SAMPLES + 1), True)
        assert out["accepted"] is False and out["reason"] == "too_long"

    def test_the_gate_accepts_exactly_the_ceiling(self):
        out = screen_with_consent(np.ones(MAX_SCREEN_SAMPLES), True)
        assert out["accepted"] is True

    def test_refusals_keep_their_http_meaning(self, client):
        """403 / 413 / 422 are different problems with different next steps.

        Collapsing every refusal to one code would force the client to guess,
        which is exactly what task 3.3 exists to prevent.
        """
        assert client.post("/api/citizen/screen_voice",
                           json={"samples": clip()}).status_code == 403
        assert client.post("/api/citizen/screen_voice",
                           json={"consent": True, "samples": [0.0] * 250_000}).status_code == 413
        assert client.post("/api/citizen/screen_voice",
                           json={"consent": True}).status_code == 422


# --------------------------------------------------------------------------- #
# 4. Total
# --------------------------------------------------------------------------- #
class TestTotal:
    @pytest.mark.parametrize("junk", [
        None, "", "not audio", 0, [], {}, [None], ["x"], [True, False],
        [[1, 2], [3, 4]],
    ])
    def test_no_malformed_input_produces_a_500(self, client, junk):
        r = client.post("/api/citizen/screen_voice",
                        json={"consent": True, "samples": junk})
        assert r.status_code in (200, 403, 413, 422), r.status_code

    def test_a_nan_in_a_real_clip_does_not_lose_the_verdict(self, client):
        """A single bad sample must not turn a real clip into "no audio".

        The gate decides consent and size, not data quality: the API's boundary
        already drops non-finite values and screens the rest. Rejecting the
        whole clip at the gate would deny a citizen the verdict they came for
        because one sample was malformed.

        Sent as raw bytes: `json=` cannot serialise NaN, which is exactly why
        Phase 5's version of this test posts a hand-built body. Python's
        `json.loads` accepts the bare token `NaN` even though strict JSON
        forbids it, so this is the only way to reach the real path.
        """
        body = ('{"consent": true, "samples": [' +
                ", ".join(["0.01", "NaN", "0.02", "Infinity", "-Infinity"]) + "]}").encode()
        r = client.post("/api/citizen/screen_voice", content=body,
                        headers={"content-type": "application/json"})
        assert r.status_code == 200
        assert r.json()["verdict"]

    def test_every_refusal_reason_has_copy_in_three_languages(self):
        for reason in CAP.REFUSAL_COPY:
            for lang in ("en", "hi", "te"):
                out = refusal(reason, lang)
                assert out["explanation"]["title"]
                assert out["explanation"]["lang"] == lang

    def test_an_unknown_refusal_reason_still_renders(self):
        """A refusal with no copy must still say something a person can act on."""
        out = refusal("a_reason_from_the_future")
        assert out["accepted"] is False
        assert out["explanation"]["title"]


# --------------------------------------------------------------------------- #
# 5. Delivered is a separate fact from accepted (Part Four, found live)
# --------------------------------------------------------------------------- #
class TestDeliveryHonesty:
    """A 200 from our own server is not delivery.

    Found by running the app rather than the tests: `POST /api/citizen/report`
    with no bus configured returned `status: "REPORTED"` and
    `forwarded: {"forwarded": False, "reason": "RAKSHA_BUS_URL not configured"}`,
    while `explanation.title` read **"Report sent"**. The API chose the copy from
    local forwarding success, so a report the server accepted and never passed on
    told the citizen it had been sent.

    Part Four's rule is that a report is reported sent only when it reached
    somewhere. This test asserts the words a person actually reads.
    """

    def test_accepted_but_not_forwarded_is_not_called_sent(self, client):
        r = client.post("/api/citizen/report",
                        json={"category": "voice", "severity": 0.8, "lang": "en"})
        body = r.json()
        # In the test harness no bus is configured, so forwarding fails.
        assert body["forwarded"]["forwarded"] is False
        assert body["delivered"] is False
        assert body["explanation"]["title"] != "Report sent", \
            "a report that reached nobody must not be called sent"
        assert body["explanation"]["title"] == "Received, but not passed on"

    def test_the_copy_still_points_at_the_helpline(self, client):
        r = client.post("/api/citizen/report",
                        json={"category": "voice", "severity": 0.8, "lang": "en"})
        assert "1930" in r.json()["explanation"]["detail"]

    @pytest.mark.parametrize("lang", ["hi", "te"])
    def test_the_not_delivered_copy_is_translated(self, client, lang):
        r = client.post("/api/citizen/report",
                        json={"category": "voice", "severity": 0.8, "lang": lang})
        title = r.json()["explanation"]["title"]
        assert title
        assert title != "Received, but not passed on", f"{lang} fell back to English"

    def test_a_forwarded_report_says_sent(self, monkeypatch):
        """The other half: when it really is passed on, the copy says so.

        Without this, the fix could be 'never say sent', which would be its own
        kind of lie — and would make a working report rail look broken.
        """
        import citizen.api as api_mod
        app = api_mod.build_app(poster=lambda ev: {"accepted": True})
        c = TestClient(app)
        body = c.post("/api/citizen/report",
                      json={"category": "voice", "severity": 0.8,
                            "lang": "en"}).json()
        assert body["forwarded"]["forwarded"] is True
        assert body["delivered"] is True
        assert body["explanation"]["title"] == "Report sent"
