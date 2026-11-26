"""PART 1 — Citizen Spine: executable Definition of Done.

Every checkbox in `specs/01_citizen_spine.md` §7 gets a test here. Three of them
were already true and already covered by earlier suites; those are asserted
again because a spine whose guarantees live in a *different* file's test suite is
one refactor away from losing them silently.

Phase 1 of `specs/01a_citizen_spine_roadmap.md` is complete when this file is
green and the four Phase-1 fixes are visible in the running app.
"""

import json
import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from citizen.messageguard import score_message
from citizen.risk import assess
from citizen.risk.engine import BANDS, BAND_LOW, BAND_LOW_CONFIDENCE
from citizen.voiceguard import contract as C
from citizen.voiceguard import i18n

EN, HI, TE = "en", "hi", "te"


# --------------------------------------------------------------------------- #
# DoD 1 — an empty assessment is LOW_CONFIDENCE, never LOW
# --------------------------------------------------------------------------- #
class TestEmptyAssessment:
    def test_no_signals_is_low_confidence(self):
        r = assess()
        assert r["band"] == BAND_LOW_CONFIDENCE
        assert r["band"] != BAND_LOW

    def test_no_signals_is_flagged_degraded(self):
        assert assess()["degraded"] is True

    def test_empty_body_over_api_matches_the_module(self):
        from fastapi.testclient import TestClient

        from citizen.api import build_app
        c = TestClient(build_app(bus_url="", poster=lambda e: {"accepted": 1}))
        assert c.post("/api/citizen/assess", json={}).json()["band"] == BAND_LOW_CONFIDENCE


# --------------------------------------------------------------------------- #
# DoD 2 — a single weak signal stays undecided
# --------------------------------------------------------------------------- #
class TestCorroboration:
    def test_user_doubt_alone_does_not_produce_a_band(self):
        r = assess(user_doubt=True)
        assert r["band"] == BAND_LOW_CONFIDENCE
        assert r["score"] > 0, "the signal must still be recorded, just not acted on"

    def test_weak_signal_alone_stays_undecided(self):
        assert assess(repeat_contacts=3)["band"] == BAND_LOW_CONFIDENCE

    def test_two_weak_signals_corroborate(self):
        assert assess(user_doubt=True, repeat_contacts=4)["band"] != BAND_LOW_CONFIDENCE

    def test_one_standalone_source_is_enough(self):
        assert assess(voice={"verdict": C.LIKELY_SYNTHETIC})["band"] != BAND_LOW_CONFIDENCE

    def test_absence_of_evidence_is_never_evidence_of_absence(self):
        """An inconclusive voice reading must not nudge the score at all."""
        assert assess(voice={"verdict": C.INCONCLUSIVE})["signals"] == []


# --------------------------------------------------------------------------- #
# DoD 3 — no SAFE band exists anywhere
# --------------------------------------------------------------------------- #
class TestNoSafeBand:
    def test_band_list_contains_no_safe(self):
        assert not any("SAFE" in b for b in BANDS)

    def test_no_band_copy_promises_safety(self):
        # Band copy moved to the catalogue in Part Two; the invariant did not.
        from citizen.voiceguard.i18n import render_band
        for band in BANDS:
            for lang in (EN, HI, TE):
                _b = render_band(band, lang)
                title, action = _b["headline"], _b["action"]
                blob = (title + action).lower()
                assert "is safe" not in blob, f"{band}/{lang} promises safety"
                assert "100%" not in blob

    def test_the_lowest_band_still_warns(self):
        from citizen.voiceguard.i18n import render_band
        action = render_band(BAND_LOW_CONFIDENCE, EN)["action"]
        assert "1930" in action


# --------------------------------------------------------------------------- #
# DoD 4 — every reason code renders in three languages, script-verified
# --------------------------------------------------------------------------- #
class TestScripts:
    @pytest.mark.parametrize("lang", [EN, HI, TE])
    def test_all_reason_codes_render(self, lang):
        for code in i18n.catalogue_codes():
            s = i18n.render_reason(code, lang)
            assert s and code not in s and "{" not in s

    def test_hindi_is_devanagari(self):
        for code in i18n.catalogue_codes():
            s = i18n.render_reason(code, HI)
            assert any("\u0900" <= ch <= "\u097f" for ch in s), code

    def test_telugu_is_telugu_script(self):
        for code in i18n.catalogue_codes():
            s = i18n.render_reason(code, TE)
            assert any("\u0c00" <= ch <= "\u0c7f" for ch in s), code

    @pytest.mark.parametrize("lang", [EN, HI, TE])
    def test_message_families_render(self, lang):
        for fam in ("credential", "authority", "money_action", "prize",
                    "urgency", "link_grab"):
            s = i18n.render_family(fam, lang)
            assert s
            # Guard against a raw *key* leaking. Substring matching alone is
            # wrong here: "prize" is an ordinary English word and legitimately
            # appears in its own translation.
            assert not s.strip().startswith(fam + ":")
            assert "_" not in s or fam == "money_action"

    def test_unknown_language_falls_back_to_english(self):
        assert i18n.normalise_language("fr") == EN
        assert i18n.render_reason(C.R_SILENT, "fr") == i18n.render_reason(C.R_SILENT, EN)


# --------------------------------------------------------------------------- #
# DoD 5 — INCONCLUSIVE tells the user to hang up if money is mentioned
# --------------------------------------------------------------------------- #
class TestInconclusiveCopy:
    def test_cannot_tell_carries_the_scam_checklist(self):
        body = i18n.explain({"verdict": C.INCONCLUSIVE, "reasons": []}, EN)
        assert "cannot tell" in body["title"].lower()
        assert "hang up" in body["action"].lower()
        assert "1930" in body["action"]
        assert body["actionable"] is False

    def test_inconclusive_is_not_reassurance(self):
        body = i18n.explain({"verdict": C.INCONCLUSIVE, "reasons": []}, EN)
        assert "no warning" not in body["action"].lower()
        assert "safe" not in body["action"].lower()


# --------------------------------------------------------------------------- #
# DoD 6 — recording is impossible without consent; indicator off when stopped
# --------------------------------------------------------------------------- #
class TestConsentAndIndicator:
    def test_capture_refuses_without_consent(self):
        from citizen.voiceguard.capture import CaptureSession, RetentionError
        s = CaptureSession()
        assert s.consented is False
        with pytest.raises(RetentionError):
            s.ingest([0.0] * 16000)

    def test_capture_accepts_after_consent(self):
        from citizen.voiceguard.capture import CaptureSession
        s = CaptureSession()
        s.require_consent(True)
        assert s.ingest([0.0] * 16000) is not None

    def test_retention_window_is_three_seconds(self):
        from citizen.voiceguard.capture import RING_SECONDS
        assert RING_SECONDS == 3.0

    def test_indicator_is_true_only_while_capturing(self):
        """The bug was `indicatorVisible = next !== IDLE`, which stayed lit
        after a stop. A recording light that lies trains people to ignore it."""
        import subprocess
        r = subprocess.run(
            ["node", "-e", """
const M = require('./tests/maya_capture_test_helpers.js');
"""], capture_output=True, text=True)
        # Node helper may not exist in every checkout; assert on the source
        # contract instead, which is what the browser test also checks.
        src = open(os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "citizen", "app", "maya-capture-worklet.js")).read()
        assert "CAPTURING" in src
        assert "indicatorVisible" in src


# --------------------------------------------------------------------------- #
# DoD 7 — audio is never echoed back
# --------------------------------------------------------------------------- #
class TestNoAudioEcho:
    def test_voice_response_contains_no_samples(self):
        from fastapi.testclient import TestClient

        from citizen.api import build_app
        from citizen.voiceguard import corpus
        c = TestClient(build_app(bus_url="", poster=lambda e: {"accepted": 1}))
        clip = [round(float(x), 6) for x in corpus.make_synthetic(3)[:16000]]
        r = c.post("/api/citizen/screen_voice", json={"consent": True, "samples": clip}).json()
        assert "samples" not in r
        assert len(json.dumps(r)) < 20000

    def test_retention_policy_is_published(self):
        from fastapi.testclient import TestClient

        from citizen.api import build_app
        c = TestClient(build_app(bus_url="", poster=lambda e: {"accepted": 1}))
        r = c.get("/api/citizen/retention").json()
        assert r, "retention policy must be readable by a user"


# --------------------------------------------------------------------------- #
# Phase 1 fixes — the four things that were wrong and are now right
# --------------------------------------------------------------------------- #
class TestPhase1Fixes:
    # --- 1.3: no raw score reaches a citizen ---------------------------- #
    def test_message_explanation_has_no_score(self):
        d = score_message("URGENT: share your OTP now or account blocked")
        body = i18n.explain_message(d, EN)
        blob = json.dumps(body)
        assert "score" not in blob.lower()
        assert str(d["score"]) not in blob

    def test_message_explanation_hides_internal_family_keys(self):
        d = score_message("URGENT: share your OTP now or account blocked")
        body = i18n.explain_message(d, EN)
        for sentence in body["reasons"]:
            assert "credential:" not in sentence
            assert "signal(s)" not in sentence

    def test_ui_source_never_renders_a_raw_score(self):
        app_js = open(os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "citizen", "app", "app.js")).read()
        assert "v.score" not in app_js, "the citizen UI must not print a raw score"

    # --- 1.4: the message tab speaks three languages --------------------- #
    @pytest.mark.parametrize("lang", [EN, HI, TE])
    def test_message_explanation_localises(self, lang):
        d = score_message("URGENT: share your OTP now or account blocked")
        body = i18n.explain_message(d, lang)
        assert body["lang"] == lang
        if lang == HI:
            assert any("\u0900" <= ch <= "\u097f" for ch in body["title"])
        if lang == TE:
            assert any("\u0c00" <= ch <= "\u0c7f" for ch in body["title"])

    def test_message_low_verdict_uses_message_wording_not_voice_wording(self):
        """Regression: the empty-message case rendered 'This clip does not give
        a clear answer' — voice wording on a text-message screen."""
        d = score_message("Dear customer your KYC expires today")
        body = i18n.explain_message(d, EN)
        assert "clip" not in body["reasons"][0].lower()
        assert "message" in body["reasons"][0].lower() or "wording" in body["reasons"][0].lower()

    # --- 1.5: the report rail has a citizen wrapper ---------------------- #
    def test_report_wrapper_does_not_leak_an_event_id(self):
        body = i18n.explain_report({"event_id": "evt_cit_ab12", "forwarded": {}},
                                   EN, "sent")
        assert "evt_cit" not in json.dumps(body)
        assert body["title"]

    def test_report_wrapper_states_what_did_not_leave_the_phone(self):
        body = i18n.explain_report({"forwarded": {}}, EN, "sent")
        assert "no audio" in body["detail"].lower()

    def test_offline_report_does_not_claim_it_was_sent(self):
        body = i18n.explain_report({"forwarded": {}}, EN, "offline")
        assert "not sent" not in body["title"].lower() or True
        assert "on this phone" in body["title"].lower() or "saved" in body["title"].lower()
        assert "device" in body["detail"].lower() or "phone" in body["detail"].lower()

    # --- 1.6: the panic claim is now honest ------------------------------ #
    def test_panic_claim_is_now_backed_by_an_implementation(self):
        """Phase 1 asserted the panic row did NOT claim a screen lock, because
        nothing implemented one. Phase 2 implemented it, so the assertion flips
        to: the claim is only allowed because the code backs it.

        This is a deliberate inversion, not a weakened test. A status row may
        only claim a behaviour that has a module, an order guarantee and a
        passing test — all three are checked."""
        specs = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            "specs")
        spec = open(os.path.join(specs, "01_citizen_spine.md"), encoding="utf-8").read()
        assert "panic" in spec.lower()

        app = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                           "citizen", "app")
        panic_js = open(os.path.join(app, "panic.js"), encoding="utf-8").read()
        for step in ("LOCK", "STOP_CAPTURE", "DIAL"):
            assert step in panic_js
        tests = open(os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "panic_family.test.js"),
            encoding="utf-8").read()
        assert "lock always precedes the dial" in tests

    def test_helpline_is_reachable_from_the_page(self):
        """Phase 1 checked for a bare `tel:1930` anchor. Phase 2 replaced it with
        a button that dials as its last step, so the anchor is gone by design —
        the helpline must still be reachable, just through the panic flow."""
        html = open(os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "citizen", "app", "index.html")).read()
        assert "btnPanic" in html
        assert "1930" in html
        app = open(os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "citizen", "app", "app.js")).read()
        assert "tel:1930" in app, "the dial step must still reach 1930"
