"""MAYA / VoiceGuard — Phase 2 tests: capture contract, retention, JS parity.

Phase 2 exit criteria (VOICEGUARD_ROADMAP.md §2):
  * the browser and Python decimators agree sample-for-sample
  * the API refuses more audio than policy allows (no trust in the client)
  * "we keep nothing" is a test, not a sentence
  * a broken worklet fails the *Python* suite, so a Python-only CI run still
    catches it
"""

import json
import os
import shutil
import subprocess
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from citizen.voiceguard import capture as CAP

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP = os.path.join(ROOT, "citizen", "app")
NODE = shutil.which("node")


# --------------------------------------------------------------------------- #
# 1. Policy constants
# --------------------------------------------------------------------------- #
class TestRetentionPolicy:
    def test_policy_matches_the_build_guide(self):
        p = CAP.retention_policy()
        assert p["ring_seconds"] == 3.0
        assert p["sample_rate_hz"] == 16000
        assert p["uploads"] == "never"
        assert p["consent_required"] is True
        assert "BUILD_GUIDE" in p["source"]

    def test_ceiling_is_bounded_to_the_ring(self):
        """The old API allowed 15 s — five times the documented retention."""
        assert CAP.MAX_SCREEN_SAMPLES < 16000 * 4
        assert CAP.MAX_SCREEN_SAMPLES >= CAP.RING_SAMPLES

    def test_policy_is_json_serialisable(self):
        json.dumps(CAP.retention_policy(), allow_nan=False)


# --------------------------------------------------------------------------- #
# 2. Resampling / decimation parity
# --------------------------------------------------------------------------- #
class TestDecimation:
    def test_decimate3_length_is_one_third(self):
        assert CAP.decimate3(np.zeros(4800)).size == 1600

    def test_decimate3_drops_partial_tail(self):
        assert CAP.decimate3([0.1, 0.2, 0.3, 0.4]).size == 1
        assert CAP.decimate3([0.1, 0.2]).size == 0

    def test_decimate3_averages_before_clamping(self):
        out = CAP.decimate3([0.0, 3.0, 6.0])
        assert out[0] == 1.0            # mean is 3, then clamped: correct
        assert CAP.decimate3([0.2, 0.5, 0.8])[0] == pytest.approx(0.5)

    def test_48k_to_16k_uses_decimation(self):
        x = np.sin(np.arange(4800) / 20.0)
        assert CAP.resample_to_16k(x, 48000).size == 1600

    def test_non_finite_input_is_neutralised(self):
        out = CAP.decimate3([float("nan"), float("inf"), 0.3])
        assert np.isfinite(out).all()

    def test_sanitize_sample_matches_js_semantics(self):
        assert CAP.sanitize_sample(float("nan")) == 0.0
        assert CAP.sanitize_sample(float("inf")) == 0.0
        assert CAP.sanitize_sample(5.0) == 1.0
        assert CAP.sanitize_sample(-5.0) == -1.0
        assert CAP.sanitize_sample("0.25") == 0.25


# --------------------------------------------------------------------------- #
# 3. Ring buffer retention
# --------------------------------------------------------------------------- #
class TestRingBuffer:
    def test_buffer_never_grows(self):
        r = CAP.RingBuffer(length=100)
        for _ in range(1000):
            r.push(0.5)
        assert r._buf.size == 100

    def test_holds_at_most_three_seconds(self):
        r = CAP.RingBuffer()
        for i in range(CAP.RING_SAMPLES * 3):
            r.push(0.1)
        assert r.seconds() <= CAP.RING_SECONDS + 1e-9

    def test_wraps_and_keeps_newest(self):
        r = CAP.RingBuffer(sr=1000, length=4)
        for v in (0.1, 0.2, 0.3, 0.4, 0.5, 0.6):
            r.push(v)
        assert list(np.round(r.read(), 4)) == [0.3, 0.4, 0.5, 0.6]

    def test_partial_fill_reads_in_order(self):
        r = CAP.RingBuffer(sr=1000, length=4)
        r.push(0.1)
        r.push(0.2)
        assert list(np.round(r.read(), 4)) == [0.1, 0.2]

    def test_read_returns_a_copy(self):
        r = CAP.RingBuffer(sr=1000, length=4)
        for v in (0.1, 0.2, 0.3, 0.4):
            r.push(v)
        out = r.read()
        out[0] = 0.9
        assert r.read()[0] == pytest.approx(0.1)

    def test_stop_zeroes_and_refuses_writes(self):
        r = CAP.RingBuffer(sr=1000, length=100)
        for _ in range(50):
            r.push(0.7)
        r.stop()
        assert np.all(r._buf == 0.0)
        r.push(0.9)
        assert np.all(r._buf == 0.0)
        assert r.read().size == 0

    def test_zeros_are_counted(self):
        r = CAP.RingBuffer(sr=1000, length=10)
        r.zero()
        r.zero()
        assert r.zero_count == 2


# --------------------------------------------------------------------------- #
# 4. Consent + server-side enforcement (do not trust the client)
# --------------------------------------------------------------------------- #
class TestConsentAndEnforcement:
    def test_ingest_without_consent_raises(self):
        s = CAP.CaptureSession()
        with pytest.raises(CAP.RetentionError, match="consent required"):
            s.ingest(np.zeros(1600))

    def test_ingest_after_consent_succeeds(self):
        s = CAP.CaptureSession()
        s.require_consent(True)
        arr = s.ingest(np.zeros(1600))
        assert arr.size == 1600 and s.screens == 1

    def test_oversized_window_is_refused_server_side(self):
        """The PWA promises 3 s; the API must not take its word for it."""
        s = CAP.CaptureSession()
        s.require_consent(True)
        with pytest.raises(CAP.RetentionError, match="retention ceiling"):
            s.ingest(np.zeros(CAP.MAX_SCREEN_SAMPLES + 1))

    def test_old_15s_cap_would_now_be_refused(self):
        s = CAP.CaptureSession()
        s.require_consent(True)
        with pytest.raises(CAP.RetentionError):
            s.ingest(np.zeros(240_000))       # the pre-Phase-2 MAX_SAMPLES

    def test_non_16k_input_is_resampled_not_rejected(self):
        s = CAP.CaptureSession()
        s.require_consent(True)
        arr = s.ingest(np.sin(np.arange(4800) / 20.0), sr=48000)
        assert arr.size == 1600

    def test_destroy_reports_a_zero_pass(self):
        s = CAP.CaptureSession()
        s.require_consent(True)
        s.ingest(np.zeros(1600))
        report = s.destroy()
        assert report["destroyed"] is True
        assert report["zero_passes"] >= 1
        assert s.destroyed is True


# --------------------------------------------------------------------------- #
# 5. API surface: the endpoint must enforce the same ceiling
# --------------------------------------------------------------------------- #
class TestApiRetention:
    @pytest.fixture()
    def client(self):
        from fastapi.testclient import TestClient

        from citizen.api import build_app
        app = build_app(bus_url="", poster=lambda e: {"accepted": 1})
        return TestClient(app)

    def test_api_rejects_more_than_retention_window(self, client):
        r = client.post("/api/citizen/screen_voice",
                        json={"consent": True, "samples": [0.0] * 240_000})
        assert r.status_code == 413

    def test_api_accepts_a_three_second_window(self, client):
        samples = [0.1 * float(np.sin(i / 40.0)) for i in range(48_000)]
        r = client.post("/api/citizen/screen_voice", json={"consent": True, "samples": samples})
        assert r.status_code == 200
        assert r.json()["verdict"] in {"SILENT", "INCONCLUSIVE", "SUSPICIOUS",
                                       "LIKELY_SYNTHETIC"}

    def test_retention_policy_is_exposed_to_the_client(self, client):
        r = client.get("/api/citizen/retention")
        assert r.status_code == 200
        body = r.json()
        assert body["uploads"] == "never"
        assert body["consent_required"] is True


# --------------------------------------------------------------------------- #
# 6. JS parity + privacy, driven from pytest
# --------------------------------------------------------------------------- #
@pytest.mark.skipif(NODE is None, reason="node not installed")
class TestJavaScript:
    def _run_node(self, script: str) -> str:
        proc = subprocess.run([NODE, "-e", script], capture_output=True,
                              text=True, timeout=120, cwd=ROOT)
        assert proc.returncode == 0, proc.stderr
        return proc.stdout.strip()

    def test_python_and_js_decimators_agree(self):
        script = f"""
        const {{ decimate3 }} = require({json.dumps(os.path.join(APP, 'maya-capture.js'))});
        const input = [0.1, -0.4, 0.7, 0.25, 0.0, -0.9, 0.33, 0.12, 0.66];
        process.stdout.write(JSON.stringify(decimate3(input)));
        """
        js = json.loads(self._run_node(script))
        py = list(CAP.decimate3([0.1, -0.4, 0.7, 0.25, 0.0, -0.9, 0.33, 0.12, 0.66]))
        assert len(js) == len(py) == 3
        assert np.allclose(js, py, atol=1e-12)

    def test_python_and_js_rings_agree_on_ordering(self):
        script = f"""
        const {{ RingBuffer }} = require({json.dumps(os.path.join(APP, 'maya-capture.js'))});
        const r = new RingBuffer(1000, 4);
        [0.1, 0.2, 0.3, 0.4, 0.5, 0.6].forEach(v => r.push(v));
        process.stdout.write(JSON.stringify(r.read()));
        """
        js = json.loads(self._run_node(script))
        r = CAP.RingBuffer(sr=1000, length=4)
        for v in (0.1, 0.2, 0.3, 0.4, 0.5, 0.6):
            r.push(v)
        assert np.allclose(js, r.read(), atol=1e-12)

    def test_js_suite_passes(self):
        """A broken worklet must fail the Python suite, not only `node --test`."""
        test_file = os.path.join(ROOT, "tests", "maya_capture.test.js")
        proc = subprocess.run([NODE, "--test", test_file], capture_output=True,
                              text=True, timeout=180, cwd=ROOT)
        assert proc.returncode == 0, (proc.stdout + proc.stderr)[-3000:]
        assert "# fail 0" in proc.stdout

    def test_privacy_contract_in_capture_core(self):
        """Scan code (not comments) for persistence and network APIs."""
        import re
        src = open(os.path.join(APP, "maya-capture.js")).read()
        src = re.sub(r"/\*[\s\S]*?\*/", "", src)
        src = re.sub(r"//.*$", "", src, flags=re.M)
        for banned in ("localStorage", "sessionStorage", "indexedDB", "fetch(",
                       "XMLHttpRequest", "sendBeacon", "MediaRecorder",
                       "toDataURL", "new Blob"):
            assert banned not in src, f"capture core references {banned}"

    def test_worklet_zeroes_on_stop(self):
        src = open(os.path.join(APP, "maya-capture-worklet.js")).read()
        assert "ring.fill(0)" in src
        assert 'type === "stop"' in src
