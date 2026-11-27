"""Phase 4 — app-owned, model-free retention and consent gate.

This mirrors the frozen capture contract's *policy* without importing the
frozen VoiceGuard package, MAYA model, numpy frontend or any AI model. The
active voice endpoint is disabled; this gate still enforces consent and the
3.5 s ceiling for compatibility and fail-closed behaviour.
"""
from __future__ import annotations

import math
from typing import Any, Dict

TARGET_SR: int = 16000
RING_SECONDS: float = 3.0
RING_SAMPLES: int = 48000
DECIMATE: int = 3
MAX_SCREEN_SAMPLES: int = 56000

REFUSAL_COPY: Dict[str, Dict[str, Any]] = {'consent': {'en': ('Recording needs your permission',
                    'Tap Start listening first. Nothing is recorded until you do.'),
             'hi': ('रिकॉर्डिंग के लिए आपकी अनुमति चाहिए',
                    "पहले 'सुनना शुरू करें' दबाएँ। जब तक आप न करें, कुछ रिकॉर्ड नहीं होता।"),
             'te': ('రికార్డింగ్\u200cకు మీ అనుమతి కావాలి',
                    "మొదట 'వినడం ప్రారంభించండి' నొక్కండి. మీరు నొక్కేవరకు ఏమీ రికార్డ్ కాదు.")},
 'no_audio': {'en': ('No audio arrived', 'Try again, or use the message check instead.'),
              'hi': ('कोई ऑडियो नहीं आया', 'दोबारा कोशिश करें, या संदेश जाँच का उपयोग करें।'),
              'te': ('ఆడియో రాలేదు', 'మళ్లీ ప్రయత్నించండి, లేదా సందేశ తనిఖీని ఉపయోగించండి.')},
 'too_long': {'en': ('That was longer than we keep',
                     'Only the last few seconds are ever used. Try a shorter clip.'),
              'hi': ('यह हमारे रखने से लंबा था',
                     'केवल आखिरी कुछ सेकंड उपयोग होते हैं। छोटी क्लिप आज़माएँ।'),
              'te': ('ఇది మేము ఉంచే దానికంటే పొడవు',
                     'చివరి కొన్ని సెకన్లు మాత్రమే వాడతాము. చిన్న క్లిప్ ప్రయత్నించండి.')}}

class RetentionError(ValueError):
    """Raised only by legacy callers; the active gate returns data."""


def sanitize_sample(v: Any) -> float:
    try:
        x = float(v)
    except (TypeError, ValueError):
        return 0.0
    if not math.isfinite(x):
        return 0.0
    return 1.0 if x > 1.0 else (-1.0 if x < -1.0 else x)


def _as_float_list(samples: Any) -> list[float]:
    if samples is None:
        return []
    try:
        return [sanitize_sample(v) for v in list(samples)]
    except TypeError:
        return []


def refusal(reason: str, lang: str = "en") -> Dict[str, Any]:
    lang = lang if lang in ("en", "hi", "te") else "en"
    entry = REFUSAL_COPY.get(reason) or REFUSAL_COPY["no_audio"]
    title, action = entry[lang]
    return {
        "accepted": False,
        "reason": reason,
        "audio_processed": False,
        "explanation": {"title": title, "action": action, "lang": lang,
                        "helpline": "1930"},
    }


def screen_with_consent(samples: Any, consented: Any, sr: int = TARGET_SR,
                        lang: str = "en") -> Dict[str, Any]:
    """Enforce consent and the retention ceiling without processing audio."""
    if consented is not True:
        return refusal("consent", lang)
    clean = _as_float_list(samples)
    if not clean:
        return refusal("no_audio", lang)
    if len(clean) > MAX_SCREEN_SAMPLES:
        return refusal("too_long", lang)
    return {
        "accepted": True,
        "reason": "ok",
        "audio_processed": True,
        "samples": clean,
        "lang": lang if lang in ("en", "hi", "te") else "en",
    }


def retention_policy() -> Dict[str, Any]:
    return {
        "ring_seconds": RING_SECONDS,
        "max_samples_per_screen": MAX_SCREEN_SAMPLES,
        "sample_rate_hz": TARGET_SR,
        "storage": "memory only",
        "uploads": "never",
        "zeroed_on": ["stop", "tab_blur", "page_hide", "teardown"],
        "consent_required": True,
        "source": "raksha/BUILD_GUIDE.md §5.5",
    }


__all__ = ["DECIMATE", "MAX_SCREEN_SAMPLES", "REFUSAL_COPY", "RING_SAMPLES",
           "RING_SECONDS", "TARGET_SR", "RetentionError", "refusal",
           "retention_policy", "sanitize_sample", "screen_with_consent"]
