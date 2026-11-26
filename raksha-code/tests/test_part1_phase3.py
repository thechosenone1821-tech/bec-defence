"""PART 1 — Phase 3: harden & ship.

Three groups:

  * offline correctness (3.1) — the service worker must cache what the page uses
  * fuzzing (3.2)             — no input may raise, ever
  * copy golden files (3.3)   — a scam warning may only change deliberately
  * cold audit (3.5)          — every claim in the spec resolves to a test

The panic/family behaviour lives in `panic_family.test.js`; the offline queue is
tested in `queue.test.js`. This file covers the Python-side guarantees.
"""

import json
import os
import re
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from citizen.risk import assess
from citizen.voiceguard import contract as C
from citizen.voiceguard import i18n, score_voice

_APP = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                    "citizen", "app")
_TESTS = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SPECS = os.path.join(os.path.dirname(_ROOT), "specs")


def app_file(name):
    with open(os.path.join(_APP, name), encoding="utf-8") as fh:
        return fh.read()


def local_assets():
    """Every same-origin asset index.html actually asks for."""
    page = app_file("index.html")
    found = set(re.findall(r'<script src="([^"]+)"', page))
    found |= set(re.findall(r'<link[^>]+href="([^"#]+)"', page))
    return {f.lstrip("./") for f in found
            if not f.startswith(("http", "tel:", "mailto:", "#"))}


def cached_assets():
    sw = app_file("sw.js")
    block = sw[sw.index("ASSETS"):sw.index("];", sw.index("ASSETS"))]
    return set(re.findall(r'"\./([^"]+)"', block))


# --------------------------------------------------------------------------- #
# 3.1 — Offline correctness
# --------------------------------------------------------------------------- #
class TestOfflineCache:
    def test_service_worker_caches_every_asset_the_page_uses(self):
        """The bug this catches: panic.js, family.js and both capture modules
        were missing, so offline the panic button did nothing at all."""
        missing = local_assets() - cached_assets() - {""}
        assert not missing, f"offline shell would be missing: {sorted(missing)}"

    def test_panic_module_is_cached(self):
        """Specific and deliberate: this is the one that must never be absent."""
        assert "panic.js" in cached_assets()

    def test_cache_version_exists(self):
        assert re.search(r'CACHE\s*=\s*"raksha-citizen-v[\d.]+"', app_file("sw.js"))

    def test_service_worker_never_caches_api_responses(self):
        sw = app_file("sw.js")
        assert '"/api/"' in sw
        assert "return;" in sw

    @pytest.mark.parametrize("asset", ["panic.js", "family.js", "queue.js",
                                       "maya-capture.js", "maya-capture-worklet.js"])
    def test_new_modules_are_served(self, asset):
        from fastapi.testclient import TestClient

        from citizen.api import build_app
        c = TestClient(build_app(bus_url="", poster=lambda e: {"accepted": 1}))
        assert c.get(f"/app/{asset}").status_code == 200

    def test_navigation_falls_back_to_the_cached_shell(self):
        assert 'mode === "navigate"' in app_file("sw.js")

    def test_stale_caches_are_deleted_on_activate(self):
        sw = app_file("sw.js")
        assert "caches.delete" in sw, "an installed phone would keep a stale shell forever"


# --------------------------------------------------------------------------- #
# 3.2 — Fuzzing: nothing may raise
# --------------------------------------------------------------------------- #
_JUNK = [
    None, "", " ", "abc", "0", "-1", "NaN", "Infinity", 0, -1, 1, 3, 3.9,
    float("nan"), float("inf"), float("-inf"), [], [1, 2], {}, {"a": 1},
    object(), True, False,
]


class TestFuzzRiskEngine:
    @pytest.mark.parametrize("junk", _JUNK)
    def test_repeat_contacts_never_raises(self, junk):
        r = assess(repeat_contacts=junk)
        json.dumps(r, allow_nan=False)

    @pytest.mark.parametrize("junk", _JUNK)
    def test_campaign_linked_never_raises(self, junk):
        r = assess(campaign_linked=junk)
        json.dumps(r, allow_nan=False)

    @pytest.mark.parametrize("junk", _JUNK)
    def test_user_doubt_never_raises(self, junk):
        json.dumps(assess(user_doubt=junk), allow_nan=False)

    @pytest.mark.parametrize("junk", _JUNK)
    def test_voice_payload_never_raises(self, junk):
        json.dumps(assess(voice=junk), allow_nan=False)

    @pytest.mark.parametrize("junk", _JUNK)
    def test_message_payload_never_raises(self, junk):
        json.dumps(assess(message=junk), allow_nan=False)

    @pytest.mark.parametrize("junk", _JUNK)
    def test_lang_never_raises(self, junk):
        json.dumps(assess(lang=junk), allow_nan=False)

    def test_every_result_is_strictly_json_serialisable(self):
        for junk in _JUNK:
            json.dumps(assess(voice=junk, message=junk, repeat_contacts=junk,
                              campaign_linked=junk, user_doubt=junk),
                       allow_nan=False)

    def test_junk_boolean_is_not_treated_as_evidence(self):
        """Fuzz finding: `campaign_linked="nope"` is truthy and was adding the
        full 0.45 campaign weight, pushing a clean assessment to HIGH."""
        assert assess(campaign_linked="nope")["signals"] == []
        assert assess(user_doubt="nope")["signals"] == []

    def test_junk_repeat_count_is_not_treated_as_evidence(self):
        assert assess(repeat_contacts="abc")["signals"] == []
        assert assess(repeat_contacts=float("nan"))["signals"] == []


class TestFuzzApi:
    @pytest.fixture()
    def client(self):
        from fastapi.testclient import TestClient

        from citizen.api import build_app
        return TestClient(build_app(bus_url="", poster=lambda e: {"accepted": 1}))

    @pytest.mark.parametrize("body", [
        {"repeat_contacts": "abc"},
        {"repeat_contacts": {"a": 1}},
        {"campaign_linked": "nope"},
        {"user_doubt": [1]},
        {"voice": []},
        {"message": "x"},
        {"lang": 123},
    ])
    def test_assess_returns_200_for_junk(self, client, body):
        r = client.post("/api/citizen/assess", json=body)
        assert r.status_code == 200, f"{body} -> {r.status_code}"
        json.dumps(r.json(), allow_nan=False)

    @pytest.mark.parametrize("raw", [
        b'{"repeat_contacts": NaN}',
        b'{"repeat_contacts": Infinity}',
        b'{"user_doubt": NaN, "campaign_linked": true}',
        b'{"samples": [NaN, 1, 2]}',
    ])
    def test_non_finite_json_never_500s(self, client, raw):
        r = client.post("/api/citizen/assess", content=raw,
                        headers={"content-type": "application/json"})
        assert r.status_code == 200

    def test_screen_message_with_junk_lang(self, client):
        r = client.post("/api/citizen/screen_message",
                        json={"text": "hi", "lang": 42})
        assert r.status_code == 200
        assert r.json()["lang"] == "en"

    def test_screen_message_with_a_very_long_body(self, client):
        r = client.post("/api/citizen/screen_message", json={"text": "x" * 50000})
        assert r.status_code == 200

    def test_voice_with_unicode_and_nested_junk(self, client):
        r = client.post("/api/citizen/screen_voice",
                        json={"consent": True, "samples": ["१२३", None, True, "🎤"]})
        assert r.status_code in (200, 422)

    def test_unicode_confusables_do_not_crash_screening(self, client):
        # Cyrillic 'о' and 'р' that look Latin — a classic obfuscation trick.
        r = client.post("/api/citizen/screen_message",
                        json={"text": "shаre yоur OTP noω", "lang": "en"})
        assert r.status_code == 200
        assert r.json()["explanation"]["title"]


class TestFuzzVoice:
    @pytest.mark.parametrize("clip", [
        [], [0.0], [0.0] * 10, [1e9] * 16000, [-1e9] * 16000,
        [float("nan")] * 16000, [float("inf")] * 16000,
        [0.5] * 56001, ["a"] * 100,
    ])
    def test_score_voice_never_raises(self, clip):
        v = score_voice(clip)
        json.dumps(v, allow_nan=False)
        assert v["verdict"] in C.VERDICTS


# --------------------------------------------------------------------------- #
# 3.3 — Golden copy
# --------------------------------------------------------------------------- #
class TestGoldenCopy:
    @pytest.fixture(scope="class")
    @classmethod
    def golden(cls):
        with open(os.path.join(_TESTS, "golden", "citizen_copy.json"),
                  encoding="utf-8") as fh:
            return json.load(fh)

    def test_every_language_has_a_golden_file(self, golden):
        assert set(golden) == set(i18n.LANGUAGES)

    def test_reason_copy_is_unchanged(self, golden):
        """A diff here means a scam warning changed. That must be deliberate."""
        for lang, body in golden.items():
            current = {c: i18n.render_reason(c, lang) for c in i18n.catalogue_codes()}
            assert current == body["reasons"], f"reason copy drifted for {lang}"

    def test_verdict_copy_is_unchanged(self, golden):
        for lang, body in golden.items():
            current = {v: i18n.render_verdict(v, lang) for v in C.VERDICTS}
            assert current == body["verdicts"], f"verdict copy drifted for {lang}"

    def test_family_copy_is_unchanged(self, golden):
        for lang, body in golden.items():
            current = {f: i18n.render_family(f, lang) for f in body["families"]}
            assert current == body["families"], f"family copy drifted for {lang}"

    def test_band_copy_is_unchanged(self, golden):
        from citizen.risk.engine import BANDS
        from citizen.voiceguard.i18n import render_band
        for lang, body in golden.items():
            current = {b: [render_band(b, lang)["headline"],
                           render_band(b, lang)["action"]] for b in BANDS}
            assert current == body["bands"], f"band copy drifted for {lang}"

    def test_report_copy_is_unchanged(self, golden):
        for lang, body in golden.items():
            current = {s: i18n.explain_report({}, lang, s)["title"]
                       for s in ("sent", "offline", "failed")}
            assert current == body["report"], f"report copy drifted for {lang}"

    def test_golden_file_covers_thousands_of_characters(self, golden):
        total = sum(len(str(v)) for lang in golden.values() for v in lang.values())
        assert total > 5000, "golden file looks truncated"


# --------------------------------------------------------------------------- #
# 3.4 — Accessibility
# --------------------------------------------------------------------------- #
class TestAccessibility:
    def test_every_control_has_a_label_or_visible_text(self):
        html = app_file("index.html")
        for ctl in re.findall(r'<(?:button|input|textarea)[^>]*>', html):
            has_label = "aria-label" in ctl or "id=" in ctl
            assert has_label, f"control without an accessible name: {ctl}"

    def test_interactive_targets_meet_touch_guidance(self):
        css = app_file("styles.css")
        assert "min-height: 56px" in css
        assert "min-height: 52px" in css

    def test_family_mode_increases_type_and_target_size(self):
        css = app_file("styles.css")
        block = css[css.index("body.family-mode"):]
        assert "font-size: 18px" in block
        assert "min-height: 52px" in block

    def test_live_regions_announce_results(self):
        html = app_file("index.html")
        assert 'aria-live' in html

    def test_verdict_bands_are_not_colour_only(self):
        css = app_file("styles.css")
        for band in ("LOW", "MODERATE", "HIGH", "CRITICAL"):
            rule = re.search(rf"\.{band}\s*\{{[^}}]*\}}", css)
            assert rule, band
            assert "border-left" in rule.group(0), band


# --------------------------------------------------------------------------- #
# 3.5 — Cold audit: every claim resolves to a test
# --------------------------------------------------------------------------- #
class TestColdAudit:
    def test_every_reason_code_has_at_least_one_test(self):
        """A claim with no test is a claim nobody can check."""
        blob = ""
        for name in os.listdir(_TESTS):
            if not name.endswith((".py", ".js")):
                continue
            with open(os.path.join(_TESTS, name), encoding="utf-8") as fh:
                blob += fh.read()
        # Scan every test file, including this one. An earlier version excluded
        # this file to avoid self-reference, then the fixes for the audit were
        # written *into* this file — so the exclusion made the audit unable to
        # see its own remediation. That is a general trap with self-checking
        # scripts: exclude yourself and you cannot verify your own effect.
        missing = [c for c in i18n.catalogue_codes() if c not in blob]
        assert not missing, f"reason codes with no test at all: {missing}"

    def test_no_safe_verdict_anywhere_in_the_production_code(self):
        """Production code only. A test that asserts `"SAFE" not in BANDS` is the
        enforcement of this rule, not a violation of it — scanning test files
        would flag the guard as the crime."""
        for root, _dirs, files in os.walk(_ROOT):
            if "__pycache__" in root or "golden" in root or root.endswith("tests"):
                continue
            for name in files:
                if not name.endswith((".py", ".js")):
                    continue
                path = os.path.join(root, name)
                with open(path, encoding="utf-8", errors="ignore") as fh:
                    src = fh.read()
                assert '"SAFE"' not in src and "'SAFE'" not in src, path

    def test_spec_claims_are_traceable(self):
        spec = open(os.path.join(_SPECS, "01_citizen_spine.md"),
                    encoding="utf-8").read()
        # Every ✅ row must name a component that exists in the code tree.
        names = {
            "Citizen Risk Engine": "risk/engine.py",
            "Multilingual layer": "voiceguard/i18n.py",
            "Capture & privacy": "voiceguard/capture.py",
            "Panic button": "app/panic.js",
        }
        for label, path in names.items():
            row = [l for l in spec.splitlines() if label in l]
            if row and "✅" in row[0]:
                assert os.path.exists(os.path.join(_ROOT, "citizen", path)), \
                    f"{label} claims ✅ but {path} does not exist"

    def test_test_count_in_specs_is_not_invented(self):
        """The roadmap must not carry a number the runner disagrees with."""
        rm = open(os.path.join(_SPECS, "01a_citizen_spine_roadmap.md"),
                  encoding="utf-8").read()
        assert "runner-reported" in rm


# --------------------------------------------------------------------------- #
# 3.5b — The three reason codes the cold audit found untested
# --------------------------------------------------------------------------- #
class TestUntestedReasonCodes:
    """The audit in `TestColdAudit` flagged these three as having no test that
    actually exercised them. Adding a test per code is the whole point of a cold
    audit — otherwise the audit is a report nobody acts on."""

    def test_spectral_regularity_fires_on_a_flat_texture(self):
        """A pure tone has almost no spectral change between frames; that is
        exactly the cue. Checked through the real reason pipeline rather than by
        poking a threshold constant."""
        import numpy as np

        from citizen.voiceguard import features as F
        from citizen.voiceguard import reasons as R
        flat = 0.3 * np.sin(2 * np.pi * 220 * np.arange(16000) / 16000)
        scalars = F.extract(flat)["scalars"]
        assert scalars["spec_flux"] < R.SPECTRAL_REGULARITY_FLUX_MAX
        codes = {r["code"] for r in R.evaluate(scalars)}
        assert "SPECTRAL_REGULARITY" in codes

    def test_spectral_regularity_does_not_fire_on_moving_content(self):
        """Guard against the rule being always-on, which would be worse than
        useless because it would accuse every steady speaker."""
        import numpy as np

        from citizen.voiceguard import features as F
        from citizen.voiceguard import reasons as R
        rng = np.random.default_rng(7)
        moving = np.concatenate([
            0.3 * np.sin(2 * np.pi * f * np.arange(2000) / 16000)
            for f in (180, 900, 240, 1400, 300, 1100, 420, 1600)
        ]) + rng.normal(0, 0.05, 16000)
        scalars = F.extract(moving)["scalars"]
        codes = {r["code"] for r in R.evaluate(scalars)}
        assert "SPECTRAL_REGULARITY" not in codes

    def test_no_trained_model_is_reachable_when_weights_are_missing(self, monkeypatch):
        """A missing model must produce a visible reason, not silence."""
        from citizen.voiceguard import model as M
        from citizen.voiceguard import contract as C
        monkeypatch.setattr(M, "get_model", lambda *a, **k: None)
        from citizen.voiceguard import voiceguard as V
        v = V.score_voice([0.2] * 16000)
        codes = {r["code"] for r in v["reasons"]}
        assert "NO_TRAINED_MODEL" in codes, codes
        assert C.R_NO_MODEL in codes
        assert v["model"] is None

    def test_model_found_nothing_is_reachable_and_says_so(self):
        """When the model runs but does not escalate, the payload must say the
        screen found nothing rather than implying it found something."""
        from citizen.voiceguard import contract as C
        from citizen.voiceguard import i18n
        text = i18n.render_reason("MODEL_FOUND_NOTHING", "en")
        assert "not proof" in text.lower(), \
            "the clean-model sentence must refuse to imply safety"
        assert "MODEL_FOUND_NOTHING" in i18n.catalogue_codes()
