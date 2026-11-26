"""MAYA / VoiceGuard — capture contract, in Python.

The browser does the real capture (``citizen/app/maya-capture.js``). This module
exists for three reasons, all of them about honesty:

1. **Reference implementation.** The JS decimator and this one must agree, or a
   model trained on one will misbehave on the other. A parity test pins that.
2. **Server-side enforcement.** Even though the PWA promises 3 s, the API must
   refuse anything larger. Trusting the client is how retention bugs happen.
3. **Retention accounting.** :class:`CaptureSession` records exactly how many
   samples existed and when they were destroyed, so "we keep nothing" is a
   claim with a test behind it rather than a sentence in a README.
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Sequence

import numpy as np

TARGET_SR: int = 16_000
RING_SECONDS: float = 3.0
RING_SAMPLES: int = int(TARGET_SR * RING_SECONDS)
DECIMATE: int = 3
# Hard ceiling for one screening call: 3 s of ring plus a small margin. The old
# API allowed 240 000 samples (15 s) — five times the documented retention.
MAX_SCREEN_SAMPLES: int = RING_SAMPLES + TARGET_SR // 2      # 3.5 s


class RetentionError(ValueError):
    """Raised when a caller tries to hold more audio than policy allows."""


def sanitize_sample(v: Any) -> float:
    """Match the JS ``sanitizeSample``: NaN/Inf -> 0, clamp to [-1, 1]."""
    try:
        x = float(v)
    except (TypeError, ValueError):
        return 0.0
    if not math.isfinite(x):
        return 0.0
    return 1.0 if x > 1.0 else (-1.0 if x < -1.0 else x)


def decimate3(samples: Sequence[float]) -> np.ndarray:
    """3-tap box decimation, 48 kHz -> 16 kHz. Mirrors ``decimate3`` in JS.

    The last partial group is dropped (never padded) so both implementations
    produce identical lengths — parity is a test, not a hope.

    Order matters: non-finite values become 0 and the *mean* is clamped, never
    the individual samples. Clamping samples first would turn a loud block of
    [0, 3, 6] into 0.67 instead of the correct 1.0 — this exact divergence
    between the JS and Python versions was caught by the Phase-2 parity test.
    """
    raw = np.asarray(samples, dtype=np.float64)
    raw = np.where(np.isfinite(raw), raw, 0.0)
    n = (raw.size // DECIMATE) * DECIMATE
    if n == 0:
        return np.empty(0, dtype=np.float64)
    means = raw[:n].reshape(-1, DECIMATE).mean(axis=1)
    return np.clip(means, -1.0, 1.0)


def resample_to_16k(samples: Sequence[float], sr: int) -> np.ndarray:
    """Best-effort conversion for callers that cannot capture at 16 kHz.

    Uses polyphase resampling when scipy is present, linear interpolation
    otherwise. Both are documented approximations; the phone path is expected
    to decimate at capture time, which is the only lossless-in-practice route.
    """
    x = np.asarray([sanitize_sample(v) for v in samples], dtype=np.float64)
    if sr == TARGET_SR or x.size == 0:
        return x
    if sr <= 0:
        raise ValueError("sample rate must be positive")
    if sr == TARGET_SR * DECIMATE:
        return decimate3(x)
    try:
        from math import gcd

        from scipy.signal import resample_poly

        g = gcd(int(sr), TARGET_SR)
        return resample_poly(x, TARGET_SR // g, int(sr) // g)
    except Exception:
        n_out = int(round(x.size * TARGET_SR / float(sr)))
        if n_out <= 0:
            return np.empty(0)
        src = np.linspace(0.0, 1.0, x.size, endpoint=False)
        dst = np.linspace(0.0, 1.0, n_out, endpoint=False)
        return np.interp(dst, src, x)


class RingBuffer:
    """Python twin of ``RingBuffer`` in ``maya-capture.js``.

    Overwrites in place, never grows, and can be zeroed. Used to prove the
    retention numbers in tests and to back the API's own bookkeeping.
    """

    def __init__(self, sr: int = TARGET_SR, length: int = RING_SAMPLES):
        self.sr = sr
        self.length = int(length)
        self._buf = np.zeros(self.length, dtype=np.float64)
        self._idx = 0
        self._filled = 0
        self.stopped = False
        self.zero_count = 0

    def push(self, sample: float) -> None:
        if self.stopped:
            return
        self._buf[self._idx] = sanitize_sample(sample)
        self._idx = (self._idx + 1) % self.length
        if self._filled < self.length:
            self._filled += 1

    def push_block(self, block: Sequence[float], src_sr: int = TARGET_SR * DECIMATE) -> None:
        for s in resample_to_16k(block, src_sr):
            self.push(float(s))

    def read(self) -> np.ndarray:
        """Chronological copy. The caller never gets the live buffer."""
        if self._filled < self.length:
            return self._buf[: self._filled].copy()
        return np.concatenate((self._buf[self._idx:], self._buf[: self._idx]))

    def seconds(self) -> float:
        return self._filled / float(self.sr)

    def zero(self) -> None:
        self._buf.fill(0.0)
        self.zero_count += 1

    def stop(self) -> None:
        self.stopped = True
        self._filled = 0
        self._idx = 0
        self.zero()


class CaptureSession:
    """Server-side retention accounting for one screening interaction."""

    def __init__(self, sr: int = TARGET_SR, length: int = RING_SAMPLES):
        self.ring = RingBuffer(sr=sr, length=length)
        self.consented = False
        self.screens = 0
        self.destroyed = False

    def require_consent(self, consented: bool) -> None:
        self.consented = bool(consented)

    def ingest(self, samples: Sequence[float], sr: int = TARGET_SR) -> np.ndarray:
        """Accept a window for screening, enforcing the retention ceiling.

        Part Three, task 3.2. This used to validate the window and return it
        without ever writing it into ``self.ring``. ``destroy()`` then reported
        ``zero_passes: 1`` — a true statement about an empty buffer and a false
        impression about the audio. The samples that had been screened were
        handed to the caller and held nowhere this object could reach, so the
        retention accounting described a buffer that never held anything.

        The window is now copied into the ring before it is returned, so
        ``destroy()`` zeroes the memory that actually held it. What this can and
        cannot promise is stated plainly: the ring copy is wiped, the array this
        returns is the caller's working buffer, and a Python module cannot reach
        into it later. Claiming otherwise would be the same lie in a new place.
        """
        if not self.consented:
            raise RetentionError("consent required before any audio is processed")
        arr = np.asarray(samples, dtype=np.float64)
        arr = arr.ravel()
        if sr != TARGET_SR:
            arr = resample_to_16k(arr, sr)
        if arr.size > MAX_SCREEN_SAMPLES:
            raise RetentionError(
                f"window of {arr.size} samples exceeds the {MAX_SCREEN_SAMPLES} "
                f"({MAX_SCREEN_SAMPLES / TARGET_SR:.1f} s) retention ceiling")
        # Keep the screened window in this object's ring so it can be zeroed.
        self.ring.push_block(arr, TARGET_SR)
        self.screens += 1
        return arr

    def destroy(self) -> Dict[str, Any]:
        """Zero the ring and report exactly what was wiped.

        ``buffered_samples`` is the number of samples that were actually in the
        ring at destroy time — 0 only when nothing was ever ingested, which is
        now a meaningful statement rather than an accident.
        """
        held = int(self.ring._filled) if hasattr(self.ring, "_filled") else 0
        self.ring.stop()
        self.destroyed = True
        return {"destroyed": True, "zero_passes": self.ring.zero_count,
                "screens": self.screens, "buffered_samples": held}


# --------------------------------------------------------------------------- #
# Refusal as a state (Part Three, task 3.3).
#
# A UI that has to catch an exception to learn *why* it was refused will show
# the wrong copy: "consent required" and "clip too long" need different words and
# different next steps. These refusals are data, not raises, so the caller can
# render them without a try/except around user-facing logic.
# --------------------------------------------------------------------------- #
REFUSAL_COPY = {
    "consent": {
        "en": ("Recording needs your permission",
               "Tap Start listening first. Nothing is recorded until you do."),
        "hi": ("रिकॉर्डिंग के लिए आपकी अनुमति चाहिए",
               "पहले 'सुनना शुरू करें' दबाएँ। जब तक आप न करें, कुछ रिकॉर्ड नहीं होता।"),
        "te": ("రికార్డింగ్‌కు మీ అనుమతి కావాలి",
               "మొదట 'వినడం ప్రారంభించండి' నొక్కండి. మీరు నొక్కేవరకు ఏమీ రికార్డ్ కాదు."),
    },
    "no_audio": {
        "en": ("No audio arrived",
               "Try again, or use the message check instead."),
        "hi": ("कोई ऑडियो नहीं आया",
               "दोबारा कोशिश करें, या संदेश जाँच का उपयोग करें।"),
        "te": ("ఆడియో రాలేదు",
               "మళ్లీ ప్రయత్నించండి, లేదా సందేశ తనిఖీని ఉపయోగించండి."),
    },
    "too_long": {
        "en": ("That was longer than we keep",
               "Only the last few seconds are ever used. Try a shorter clip."),
        "hi": ("यह हमारे रखने से लंबा था",
               "केवल आखिरी कुछ सेकंड उपयोग होते हैं। छोटी क्लिप आज़माएँ।"),
        "te": ("ఇది మేము ఉంచే దానికంటే పొడవు",
               "చివరి కొన్ని సెకన్లు మాత్రమే వాడతాము. చిన్న క్లిప్ ప్రయత్నించండి."),
    },
}


def refusal(reason: str, lang: str = "en") -> Dict[str, Any]:
    """A refusal a client can show without catching anything."""
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
    """The consent gate, as a value.

    Returns ``{"accepted": False, ...}`` for every refusal and
    ``{"accepted": True, "samples": <arr>}`` when the window may be screened.
    ``audio_processed`` is present and False on every refusal so a caller can
    assert the promise rather than trust it.
    """
    if consented is not True:
        return refusal("consent", lang)
    if samples is None:
        return refusal("no_audio", lang)
    try:
        arr = np.asarray(samples, dtype=np.float64).ravel()
    except (TypeError, ValueError):
        return refusal("no_audio", lang)
    if arr.size == 0:
        return refusal("no_audio", lang)
    # Deliberately NOT rejecting non-finite samples here. The API's boundary
    # already drops them and screens the rest (Phase 5), and a single NaN must
    # not turn a real clip into "no audio": the citizen would lose the verdict
    # they came for. This gate decides *consent and size*, not data quality.
    if sr != TARGET_SR:
        arr = resample_to_16k(arr, sr)
    if arr.size > MAX_SCREEN_SAMPLES:
        return refusal("too_long", lang)
    return {"accepted": True, "reason": "ok", "audio_processed": True,
            "samples": arr, "lang": lang if lang in ("en", "hi", "te") else "en"}


def retention_policy() -> Dict[str, Any]:
    """The machine-readable version of BUILD_GUIDE.md §5.5.

    Shipped to the client so the UI can state the policy it actually enforces.
    """
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
