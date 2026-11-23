"""MAYA / VoiceGuard — Phase 5 tests: measurement, degradation, release gates.

Phase 5 is the phase allowed to change what the demo *claims*, so its tests are
mostly about honesty rather than accuracy:

  * `choose_threshold` must pick the most sensitive threshold that respects the
    FPR ceiling (a Phase-5 bug returned the *least* sensitive one)
  * the headline table and the citizen-facing verdicts must agree about the
    same model — if they disagree, one of them is lying
  * every degradation condition must be reported, not hidden
  * no output may claim real-world accuracy
  * the shipped artefact must be the one the tests think it is
"""

import json
import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from citizen.voiceguard import contract as C
from citizen.voiceguard import corpus, model as M, score_voice
from citizen.voiceguard import train as T

ARTEFACT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "citizen", "voiceguard", "maya_lr_v1.json")


# --------------------------------------------------------------------------- #
# 1. Threshold search — the Phase-5 correctness bug
# --------------------------------------------------------------------------- #
class TestThresholdSearch:
    def test_returns_most_sensitive_threshold_within_fpr(self):
        """Given a well-separated set, the lowest threshold meeting the FPR
        ceiling is the correct answer, not the highest."""
        probs = np.array([0.1, 0.2, 0.3, 0.4, 0.55, 0.6, 0.7, 0.8, 0.9, 0.95])
        y = np.array([0, 0, 0, 0, 0, 1, 1, 1, 1, 1])
        thr = M.choose_threshold(probs, y, target_fpr=0.0)
        # With FPR 0 the threshold must sit above every negative.
        assert thr > probs[y == 0].max()
        assert thr <= probs[y == 1].min() + 1e-9

    def test_threshold_attains_the_target_fpr(self):
        rng = np.random.default_rng(3)
        probs = np.concatenate([rng.uniform(0, 0.6, 200), rng.uniform(0.4, 1.0, 200)])
        y = np.concatenate([np.zeros(200, int), np.ones(200, int)])
        thr = M.choose_threshold(probs, y, target_fpr=0.05)
        fpr = float(np.mean(probs[y == 0] >= thr))
        assert fpr <= 0.05 + 1e-9

    def test_threshold_is_not_degenerate_high(self):
        """The regression itself: a symmetric, well-separated sample must not
        produce a threshold at the very top of the score range."""
        rng = np.random.default_rng(7)
        probs = np.concatenate([rng.uniform(0.0, 0.45, 50), rng.uniform(0.55, 1.0, 50)])
        y = np.concatenate([np.zeros(50, int), np.ones(50, int)])
        thr = M.choose_threshold(probs, y, target_fpr=0.05)
        assert thr < 0.75, f"threshold {thr} would flag almost nothing"

    def test_threshold_search_is_monotone_in_target_fpr(self):
        rng = np.random.default_rng(11)
        probs = np.concatenate([rng.uniform(0, 0.7, 100), rng.uniform(0.3, 1.0, 100)])
        y = np.concatenate([np.zeros(100, int), np.ones(100, int)])
        strict = M.choose_threshold(probs, y, target_fpr=0.0)
        loose = M.choose_threshold(probs, y, target_fpr=0.20)
        assert loose <= strict

    def test_falls_back_without_positives(self):
        assert M.choose_threshold(np.array([0.1, 0.2]), np.array([0, 0])) == \
            M.DECISION_THRESHOLD_DEFAULT

    def test_falls_back_without_negatives(self):
        assert M.choose_threshold(np.array([0.1, 0.2]), np.array([1, 1])) == \
            M.DECISION_THRESHOLD_DEFAULT

    def test_empty_input_falls_back(self):
        assert M.choose_threshold(np.array([]), np.array([])) == \
            M.DECISION_THRESHOLD_DEFAULT


# --------------------------------------------------------------------------- #
# 2. Shipped artefact integrity
# --------------------------------------------------------------------------- #
class TestShippedArtefact:
    @pytest.fixture(scope="class")
    @classmethod
    def art(cls):
        with open(ARTEFACT) as fh:
            return json.load(fh)

    def test_artefact_exists_and_is_small(self):
        assert os.path.exists(ARTEFACT)
        assert os.path.getsize(ARTEFACT) < 4096

    def test_artefact_declares_synthetic_training(self, art):
        blob = json.dumps(art).lower()
        assert "synthetic" in blob

    def test_artefact_threshold_is_in_a_sane_range(self, art):
        thr = art["decision_threshold"]
        assert 0.5 < thr < 1.0, f"threshold {thr} is outside a usable range"

    def test_artefact_is_loadable_and_self_consistent(self, art):
        m = M.get_model()
        assert m is not None
        assert m.decision_threshold == pytest.approx(art["decision_threshold"])
        assert m.temperature == pytest.approx(art["temperature"])

    def test_artefact_file_digest_matches_the_pinned_value(self, art):
        """The pinned digest must describe the bytes on disk, so a reviewer can
        verify it with `sha256sum` without running the test suite."""
        import hashlib
        raw = open(ARTEFACT, "rb").read()
        actual = hashlib.sha256(raw).hexdigest()[:16]
        from tests.test_maya_phase3 import EXPECTED_SHA
        assert actual == EXPECTED_SHA

    def test_artefact_params_digest_is_recorded(self, art):
        recorded = art["training"].get("params_sha256_16")
        assert isinstance(recorded, str) and len(recorded) == 16


# --------------------------------------------------------------------------- #
# 3. Headline table and citizen verdicts must agree
# --------------------------------------------------------------------------- #
class TestMetricCoherence:
    @pytest.fixture(scope="class")
    @classmethod
    def report(cls):
        return T.run(seed=20260101, n_per_class=60, l2=1.0, save=False)

    def test_test_split_accuracy_matches_direct_probability_path(self, report):
        """If `evaluate()` and `probability()` disagree, the app and the slide
        deck are describing different models. This happened in Phase 5."""
        m = M.get_model()
        data = corpus.build(seed=20260101, n_per_class=60)
        clips, y = data["test"]["clips"], data["test"]["labels"]
        probs = np.array([m.probability(c) for c in clips])
        pred = probs >= m.decision_threshold
        direct_acc = float(np.mean(pred == y))
        assert abs(direct_acc - report["test"]["accuracy_at_threshold"]) < 0.01

    def test_reported_recall_is_not_a_mirage(self, report):
        """A threshold that flags almost nothing still reports a fine EER.
        Guard the thing the citizen actually experiences."""
        assert report["test"]["recall"] > 0.40, \
            f"recall {report['test']['recall']} means the app rarely says anything"

    def test_headline_accuracy_is_honest_not_perfect(self, report):
        """86 % on a 36-clip synthetic split is plausible; 100 % is a bug."""
        assert 0.60 <= report["test"]["accuracy_at_threshold"] <= 0.99

    def test_decision_threshold_beats_the_naive_default(self, report):
        assert report["test"]["accuracy_at_threshold"] >= \
            report["test"]["accuracy_naive"] - 1e-9 if "accuracy_naive" in \
            report["test"] else True


# --------------------------------------------------------------------------- #
# 4. Degradation conditions — reported, not hidden
# --------------------------------------------------------------------------- #
class TestRobustness:
    def test_every_condition_is_measured(self):
        sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(
            os.path.abspath(__file__))), "evals"))
        import run_maya as RM
        m = M.get_model()
        data = corpus.build(seed=20260101, n_per_class=8)
        table = RM.measure_conditions(m, data["test"]["clips"], data["test"]["labels"])
        assert set(table) == set(RM.CONDITIONS)
        for name, row in table.items():
            assert row["n"] > 0, name
            assert 0.0 <= row["eer"] <= 0.5, name

    def test_narrowband_degrades_or_holds_but_is_reported(self):
        """Telephony band-limiting removes the high band where anti-spoof
        evidence lives. We do not require it to be good — we require it to be
        *measured* and published."""
        sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(
            os.path.abspath(__file__))), "evals"))
        import run_maya as RM
        clean = np.sin(2 * np.pi * 300 * np.arange(16000) / 16000).astype(np.float32)
        nb = RM.degrade_narrowband(clean)
        assert nb.shape == clean.shape
        assert np.isfinite(nb).all()
        # The high band really is gone.
        spec = np.abs(np.fft.rfft(nb))
        freqs = np.fft.rfftfreq(nb.size, 1 / 16000)
        assert spec[freqs > 5000].max() < spec[freqs <= 3000].max()

    def test_mulaw_is_bounded_and_roundtrip_close(self):
        sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(
            os.path.abspath(__file__))), "evals"))
        import run_maya as RM
        x = np.linspace(-1, 1, 4000).astype(np.float32)
        y = RM.degrade_mulaw(x)
        assert np.abs(y).max() <= 1.0
        assert np.max(np.abs(y - x)) < 0.05

    def test_packet_loss_keeps_length_and_is_deterministic(self):
        sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(
            os.path.abspath(__file__))), "evals"))
        import run_maya as RM
        x = np.ones(16000, dtype=np.float32) * 0.5
        a = RM.degrade_packet_loss(x, seed=1, p=0.5)
        b = RM.degrade_packet_loss(x, seed=1, p=0.5)
        assert a.shape == x.shape
        assert np.array_equal(a, b)
        assert np.any(a == 0.0)

    def test_degradations_never_produce_non_finite_audio(self):
        sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(
            os.path.abspath(__file__))), "evals"))
        import run_maya as RM
        base = corpus.make_bona_fide(2)
        for name, fn in RM.CONDITIONS.items():
            out = fn(base, 0)
            assert np.isfinite(out).all(), name
            assert out.shape == base.shape, name


# --------------------------------------------------------------------------- #
# 5. What the release may and may not claim
# --------------------------------------------------------------------------- #
class TestReleaseClaims:
    def test_clone_detection_is_still_not_claimed(self):
        assert C.may_claim_clone_detection() is False

    def test_real_world_measurement_flag_is_still_false(self):
        assert C.MEASURED_ON_REAL_SPEECH is False

    def test_engine_label_states_the_synthetic_training(self):
        label = C.engine_label("maya-lr-v1")
        assert "SYNTHETIC" in label
        assert "UNMEASURED" in label.upper()
        assert "NOT a validated" in label

    def test_score_payload_never_says_safe(self):
        for clip in (corpus.make_bona_fide(3), corpus.make_synthetic(3)):
            blob = json.dumps(score_voice(clip)).lower()
            assert "safe" not in blob
            assert "verified" not in blob

    def test_payload_always_carries_the_engine_disclaimer(self):
        v = score_voice(corpus.make_bona_fide(5))
        assert "SYNTHETIC" in v["engine"]

    def test_roadmap_phase5_gaps_are_still_open_and_documented(self):
        """Phase 5 does not close the real-world gaps. If this test ever needs
        changing, it must be because a real measured corpus arrived."""
        gaps = {
            "real speech corpus": C.MEASURED_ON_REAL_SPEECH,
            "clone detection claim": C.may_claim_clone_detection(),
        }
        assert not any(gaps.values()), f"unexpectedly claimed: {gaps}"


# --------------------------------------------------------------------------- #
# 6. End-to-end: the app path a citizen actually exercises
# --------------------------------------------------------------------------- #
class TestCitizenPath:
    @pytest.fixture()
    def client(self):
        from fastapi.testclient import TestClient

        from citizen.api import build_app
        return TestClient(build_app(bus_url="", poster=lambda e: {"accepted": 1}))

    def test_full_path_synthetic_clip_is_actionable(self, client):
        clip = corpus.make_synthetic(9)
        r = client.post("/api/citizen/screen_voice",
                        json={"samples": [float(x) for x in clip[:16000]], "lang": "en"}).json()
        ex = r["explanation"]
        assert ex["action"] and ex["title"]
        # Whatever the verdict, a citizen is never left without an action.
        assert len(ex["action"]) > 20

    def test_full_path_silence_gives_silent_not_an_accusation(self, client):
        r = client.post("/api/citizen/screen_voice",
                        json={"samples": [0.0] * 16000}).json()
        assert r["verdict"] == "SILENT"
        assert r["explanation"]["actionable"] is False

    def test_non_finite_samples_in_raw_json_do_not_500(self, client):
        """Python's json.loads accepts the bare tokens NaN / Infinity, so a
        client can inject them even though strict JSON forbids them. Before the
        Phase-5 fix this produced a 500 with a traceback instead of a verdict —
        i.e. a malformed request could take the screening endpoint down."""
        body = b'{"samples": [0.0, NaN, 0.1, Infinity, -Infinity]}'
        r = client.post("/api/citizen/screen_voice", content=body,
                        headers={"content-type": "application/json"})
        assert r.status_code == 200
        assert r.json()["verdict"] in {"SILENT", "INCONCLUSIVE", "SUSPICIOUS",
                                       "LIKELY_SYNTHETIC"}

    def test_non_finite_mixed_with_real_audio_still_returns_a_verdict(self, client):
        clip = [round(float(x), 6) for x in corpus.make_synthetic(4)[:16000]]
        clip[100:105] = ["NaN"] * 5
        body = ("{\"samples\": [" + ", ".join(str(x) for x in clip) + "]}").encode()
        r = client.post("/api/citizen/screen_voice", content=body,
                        headers={"content-type": "application/json"})
        assert r.status_code == 200
        assert r.json()["verdict"]

    def test_no_audio_is_echoed_back(self, client):
        clip = [float(x) for x in corpus.make_synthetic(4)[:16000]]
        r = client.post("/api/citizen/screen_voice", json={"samples": clip}).json()
        blob = json.dumps(r)
        assert "samples" not in r
        assert len(blob) < 20000, "payload looks like it may contain audio"


# --------------------------------------------------------------------------- #
# 7. Deployment: the page must actually be able to load its own assets
# --------------------------------------------------------------------------- #
class TestDeployment:
    """Found by starting the server and curling it, not by running pytest.

    The suite tested the API in isolation and the capture module in Node, so
    nothing noticed that the served page could not load a single one of its
    assets. Tests that exercise units cannot catch a broken URL.
    """

    @pytest.fixture()
    def client(self):
        from fastapi.testclient import TestClient

        from citizen.api import build_app
        return TestClient(build_app(bus_url="", poster=lambda e: {"accepted": 1}))

    def test_root_redirects_to_the_static_mount(self, client):
        r = client.get("/", follow_redirects=False)
        assert r.status_code in (301, 302, 307, 308)
        assert "/app" in r.headers["location"]

    def test_every_asset_resolves_relative_to_the_landing_url(self, client):
        """Resolve assets exactly as a browser would: from the URL the user
        actually opened. Testing only /app/ let the broken-root bug through,
        because the page's *relative* references then pointed at /styles.css."""
        import re
        from urllib.parse import urljoin

        landing = client.get("/", follow_redirects=True)
        assert landing.status_code == 200
        base = str(landing.url)

        refs = re.findall(r'(?:src|href)="([^"#]+)"', landing.text)
        local = [r for r in refs if not r.startswith(("http", "tel:", "mailto:"))]
        assert local, "index.html references no local assets — suspect"
        for ref in local:
            url = urljoin(base, ref)
            path = url.split("://", 1)[-1].split("/", 1)[1]
            r = client.get("/" + path)
            assert r.status_code == 200, f"{url} 404s from the landing page"

    def test_capture_scripts_are_served(self, client):
        for name in ("maya-capture.js", "maya-capture-worklet.js"):
            assert client.get(f"/app/{name}").status_code == 200, name

    def test_index_html_references_the_capture_scripts(self, client):
        page = client.get("/app/").text
        assert "maya-capture.js" in page
        assert "maya-capture-worklet.js" in page

    def test_api_routes_still_work_from_the_root(self, client):
        """The redirect must not capture /api/*."""
        assert client.post("/api/citizen/assess", json={}).status_code == 200
        assert client.get("/api/citizen/languages").status_code == 200
