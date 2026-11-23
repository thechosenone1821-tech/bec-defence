from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "citizen" / "app"


def test_voiceguard_ui_requires_unchecked_consent_by_default():
    html = (APP / "index.html").read_text(encoding="utf-8")
    assert '<input type="checkbox" id="voiceConsent">' in html
    assert 'id="btnScreenVoice" disabled' in html
    assert "Use only a server you trust or host yourself" in html
    assert "does not listen to or intercept phone calls" in html


def test_voiceguard_capture_is_bounded_and_visible():
    js = (APP / "app.js").read_text(encoding="utf-8")
    assert "getUserMedia" in js
    assert "RECORDING — microphone active" in js
    assert "}, 2000);" in js
    assert "new OfflineContextClass(1, 32000, 16000)" in js
    assert "getTracks().forEach(track => track.stop())" in js


def test_consent_revocation_and_page_exit_stop_capture():
    js = (APP / "app.js").read_text(encoding="utf-8")
    assert "Consent withdrawn. Recording stopped" in js
    assert "Consent was withdrawn. No sample was sent." in js
    assert 'window.addEventListener("pagehide"' in js
    assert "stopMicrophoneTracks();" in js


def test_samples_are_sent_only_with_explicit_consent_and_cleared():
    js = (APP / "app.js").read_text(encoding="utf-8")
    assert "consent:true,sample_rate:16000" in js
    assert "if (!consentVoice.checked) throw new Error" in js
    assert "if (samples) samples.fill(0);" in js
    assert "synthTone" not in js


def test_service_worker_never_caches_api_requests():
    sw = (APP / "sw.js").read_text(encoding="utf-8")
    assert 'if (url.pathname.startsWith("/api/")) return;' in sw


def test_page_exit_marks_active_capture_cancelled_before_stopping():
    js = (APP / "app.js").read_text(encoding="utf-8")
    pagehide = js.split('window.addEventListener("pagehide"', 1)[1]
    assert "cancelCapture = true;" in pagehide
    assert "consentVoice.checked = false;" in pagehide
    assert "stopMicrophoneTracks();" in pagehide
