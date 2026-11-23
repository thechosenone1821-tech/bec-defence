"""MAYA / VoiceGuard — frontend feature extraction (pure numpy).

This replaces the 5-number probe in ``voiceguard.py`` with a real,
model-ready frontend. Everything here is deterministic, dependency-free
(numpy only) and fast enough to run per 1.5–2 s window on a phone-class CPU.

Two groups of features, deliberately kept separate:

**Timbre / spectral** — LFCC and MFCC (with deltas), centroid, bandwidth,
rolloff, flatness, flux, crest factor. These describe *what the signal looks
like*. They are what a learned model consumes.

**Prosody / production** — F0 track (autocorrelation pitch), pitch stability,
pauses, harmonicity. These describe *how speech is being produced*, and they
carry the interpretable evidence: a real speaker breathes, wobbles, and pauses
irregularly; a naive TTS does not.

Honesty notes that must stay in the code:
  * Pitch is estimated by autocorrelation in the 60–400 Hz band. It fails on
    whisper and on heavily compressed low-bitrate audio — those return NaN,
    and every consumer must tolerate NaN rather than treat it as zero.
  * Nothing here discriminates a *good* neural clone. That is the model's job
    (Phase 3). These features are the input, not the verdict.
"""

from __future__ import annotations

import math
from typing import Any, Dict, List

import numpy as np

SAMPLE_RATE: int = 16_000
N_FFT: int = 512
HOP: int = 160          # 10 ms
WIN: int = 400          # 25 ms
N_MELS: int = 26
N_LFCC: int = 20
N_MFCC: int = 13
F0_MIN_HZ: float = 60.0
F0_MAX_HZ: float = 400.0
FEATURES_VERSION: str = "maya-features-v1"

_EPS = 1e-10


# --------------------------------------------------------------------------- #
# Windowing / filterbanks
# --------------------------------------------------------------------------- #
def frame_signal(x: np.ndarray, win: int = WIN, hop: int = HOP) -> np.ndarray:
    """Split into overlapping frames. Returns (n_frames, win)."""
    if x.size < win:
        return np.empty((0, win), dtype=np.float64)
    n = 1 + (x.size - win) // hop
    idx = np.arange(win)[None, :] + hop * np.arange(n)[:, None]
    return x[idx]


def _hz_to_mel(hz):
    return 2595.0 * np.log10(1.0 + np.asarray(hz, dtype=np.float64) / 700.0)


def _mel_to_hz(mel):
    return 700.0 * (10.0 ** (np.asarray(mel, dtype=np.float64) / 2595.0) - 1.0)


def mel_filterbank(sr: int = SAMPLE_RATE, n_fft: int = N_FFT,
                   n_mels: int = N_MELS) -> np.ndarray:
    """Triangular mel filterbank, (n_mels, n_fft//2+1). Deterministic."""
    n_bins = n_fft // 2 + 1
    f_max = sr / 2.0
    mel_pts = np.linspace(_hz_to_mel(0.0), _hz_to_mel(f_max), n_mels + 2)
    hz_pts = _mel_to_hz(mel_pts)
    bins = np.floor((n_fft + 1) * hz_pts / sr).astype(int)
    bins = np.clip(bins, 0, n_bins - 1)
    fb = np.zeros((n_mels, n_bins), dtype=np.float64)
    for m in range(1, n_mels + 1):
        lo, mid, hi = bins[m - 1], bins[m], bins[m + 1]
        if mid == lo:
            mid = min(lo + 1, n_bins - 1)
        if hi <= mid:
            hi = min(mid + 1, n_bins - 1)
        fb[m - 1, lo:mid] = np.linspace(0.0, 1.0, mid - lo, endpoint=False)
        fb[m - 1, mid:hi] = np.linspace(1.0, 0.0, hi - mid, endpoint=False)
    return fb


def _dct_matrix(n_in: int, n_out: int) -> np.ndarray:
    """Orthonormal DCT-II matrix, (n_out, n_in)."""
    k = np.arange(n_out)[:, None]
    n = np.arange(n_in)[None, :]
    mat = np.cos(np.pi * k * (2 * n + 1) / (2.0 * n_in))
    mat *= np.sqrt(2.0 / n_in)
    mat[0, :] *= 1.0 / np.sqrt(2.0)
    return mat


# --------------------------------------------------------------------------- #
# Cepstral features
# --------------------------------------------------------------------------- #
def power_spectrum(frames: np.ndarray, n_fft: int = N_FFT) -> np.ndarray:
    """Hann-windowed |STFT|^2, (n_frames, n_fft//2+1)."""
    if frames.size == 0:
        return np.empty((0, n_fft // 2 + 1))
    windowed = frames * np.hanning(frames.shape[1])[None, :]
    spec = np.fft.rfft(windowed, n=n_fft, axis=1)
    return (np.abs(spec) ** 2).astype(np.float64)


def lfcc(power: np.ndarray, n_lfcc: int = N_LFCC) -> np.ndarray:
    """Linear-frequency cepstral coefficients.

    Uses a mel-shaped (warped) filterbank for stability at low frequency but
    *linear* spacing above 1 kHz is the textbook LFCC; we approximate with a
    linear triangular bank because that is what the anti-spoof literature
    actually feeds a classifier. Documented as an approximation.
    """
    if power.shape[0] == 0:
        return np.empty((0, n_lfcc))
    n_bins = power.shape[1]
    n_filters = n_lfcc * 2
    fb = np.zeros((n_filters, n_bins))
    edges = np.linspace(0, n_bins - 1, n_filters + 2).astype(int)
    for m in range(1, n_filters + 1):
        lo, mid, hi = edges[m - 1], edges[m], edges[m + 1]
        if mid <= lo:
            mid = lo + 1
        if hi <= mid:
            hi = mid + 1
        lo, mid, hi = min(lo, n_bins - 2), min(mid, n_bins - 1), min(hi, n_bins - 1)
        fb[m - 1, lo:mid] = np.linspace(0, 1, max(mid - lo, 1), endpoint=False)
        fb[m - 1, mid:hi] = np.linspace(1, 0, max(hi - mid, 1), endpoint=False)
    log_e = np.log(power @ fb.T + _EPS)
    return log_e @ _dct_matrix(n_filters, n_lfcc).T


def mfcc(power: np.ndarray, sr: int = SAMPLE_RATE, n_mfcc: int = N_MFCC) -> np.ndarray:
    """Mel-frequency cepstral coefficients."""
    if power.shape[0] == 0:
        return np.empty((0, n_mfcc))
    fb = mel_filterbank(sr=sr, n_mels=N_MELS)
    n_bins = min(fb.shape[1], power.shape[1])
    log_e = np.log(power[:, :n_bins] @ fb[:, :n_bins].T + _EPS)
    return log_e @ _dct_matrix(N_MELS, n_mfcc).T


def deltas(feat: np.ndarray, width: int = 2) -> np.ndarray:
    """Simple regression deltas (HTK-style), handles short input safely."""
    n = feat.shape[0]
    if n == 0:
        return feat.copy()
    if n < (2 * width + 1):
        return np.zeros_like(feat)
    pad = np.pad(feat, ((width, width), (0, 0)), mode="edge")
    denom = 2 * sum(i * i for i in range(1, width + 1))
    out = np.zeros_like(feat)
    for t in range(n):
        acc = np.zeros(feat.shape[1])
        for i in range(1, width + 1):
            acc += i * (pad[t + width + i] - pad[t + width - i])
        out[t] = acc / denom
    return out


# --------------------------------------------------------------------------- #
# Prosody
# --------------------------------------------------------------------------- #
def f0_track(x: np.ndarray, sr: int = SAMPLE_RATE,
             win: int = WIN, hop: int = HOP) -> np.ndarray:
    """Autocorrelation pitch per frame. NaN where unvoiced/uncertain."""
    frames = frame_signal(x, win, hop)
    if frames.shape[0] == 0:
        return np.empty(0)
    min_lag = max(1, int(sr / F0_MAX_HZ))
    max_lag = min(win - 2, int(sr / F0_MIN_HZ))
    out = np.full(frames.shape[0], np.nan)
    for i, fr in enumerate(frames):
        f = fr - fr.mean()
        energy = float(np.dot(f, f))
        if energy < 1e-6:
            continue
        ac = np.correlate(f, f, mode="full")[win - 1:]
        ac = ac / (ac[0] + _EPS)
        if max_lag <= min_lag or ac[min_lag:max_lag].size == 0:
            continue
        seg = ac[min_lag:max_lag]
        lag = int(np.argmax(seg)) + min_lag
        # Require a clear peak, else this frame has no trustworthy pitch.
        if ac[lag] > 0.30:
            out[i] = sr / lag
    return out


def _finite_or_none(value: Any) -> Any:
    """NaN/Inf must never cross this module's boundary.

    Two reasons, both learned the hard way in Phase 1:
      1. ``json.dumps`` raises on NaN, which would break the HTTP response.
      2. ``nan != nan`` makes any dict containing it non-deterministic, which
         breaks the ``score_voice(a) == score_voice(a)`` contract.
    A feature that could not be measured is ``None`` ("unknown"), never zero —
    zero is a *value* and would be silently averaged by the model.
    """
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def _sanitize(d: Dict[str, Any]) -> Dict[str, Any]:
    return {k: _finite_or_none(v) for k, v in d.items()}


def _nan_stats(arr: np.ndarray) -> Dict[str, float]:
    finite = arr[np.isfinite(arr)]
    if finite.size == 0:
        return {"mean": float("nan"), "std": float("nan"),
                "cv": float("nan"), "voiced_pct": 0.0}
    mean = float(finite.mean())
    std = float(finite.std())
    cv = float(std / mean) if mean > _EPS else float("nan")
    voiced = 100.0 * finite.size / float(arr.size) if arr.size else 0.0
    return _sanitize({"mean": round(mean, 3), "std": round(std, 3),
                      "cv": round(cv, 4), "voiced_pct": round(voiced, 2)})


def harmonicity(x: np.ndarray, sr: int = SAMPLE_RATE,
                win: int = WIN, hop: int = HOP) -> float:
    """Mean normalised autocorrelation peak — a cheap HNR proxy, 0..1."""
    frames = frame_signal(x, win, hop)
    if frames.shape[0] == 0:
        return 0.0
    peaks: List[float] = []
    for fr in frames:
        f = fr - fr.mean()
        if float(np.dot(f, f)) < 1e-6:
            continue
        ac = np.correlate(f, f, mode="full")[win - 1:]
        ac = ac / (ac[0] + _EPS)
        lo = max(1, int(sr / F0_MAX_HZ))
        hi = min(win - 2, int(sr / F0_MIN_HZ))
        if hi <= lo:
            continue
        peaks.append(float(np.max(ac[lo:hi])))
    return round(float(np.mean(peaks)), 4) if peaks else 0.0


def pause_stats(rms: np.ndarray, hop: int = HOP, sr: int = SAMPLE_RATE) -> Dict[str, Any]:
    """Count pauses and measure how *regular* they are.

    A silence gate at 12 % of the clip's peak RMS. ``cv`` (coefficient of
    variation) near zero means the gaps are machine-regular.
    """
    if rms.size == 0:
        return {"count": 0, "mean_s": 0.0, "cv": None,
                "regularity": None, "speech_ratio": 0.0}
    gate = max(1e-4, 0.12 * float(np.max(rms)))
    quiet = rms < gate
    runs: List[int] = []
    cur = 0
    for q in quiet:
        if q:
            cur += 1
        elif cur:
            runs.append(cur)
            cur = 0
    if cur:
        runs.append(cur)
    if not runs:
        return {"count": 0, "mean_s": 0.0, "cv": None,
                "regularity": None, "speech_ratio": 1.0}
    lens = np.asarray(runs, dtype=np.float64) * hop / sr
    mean = float(lens.mean())
    cv = float(lens.std() / mean) if mean > _EPS else float("nan")
    return _sanitize({"count": int(lens.size),
                      "mean_s": round(mean, 4),
                      "cv": round(cv, 4),
                      "regularity": round(float(max(0.0, 1.0 - cv)), 4) if np.isfinite(cv) else float("nan"),
                      "speech_ratio": round(float(1.0 - quiet.mean()), 4)})


# --------------------------------------------------------------------------- #
# Spectral shape
# --------------------------------------------------------------------------- #
# A frame is "silent" when its energy is below this *absolute* floor. It is a
# floor only to keep normalisation stable, NOT a speech/silence detector:
# using it that way would let a classifier learn the generator's pause
# amplitude rather than speech production. Voicing and pause structure are
# measured relative to the clip (see f0_track / pause_stats), not here.
_SILENT_FRAME_ENERGY: float = 1e-14


def _spectral_shape(power: np.ndarray, sr: int = SAMPLE_RATE) -> Dict[str, float]:
    """Spectral descriptors computed over *active* frames only.

    BUG THIS FIXES (caught while checking why the Phase-3 model trained to
    EER 0.000): silence frames were normalised by ``+1e-10`` and their
    floating-point residue divided, producing spectral flux values around
    1.4e9 and a flatness of 1.0 ("this is white noise") for pure silence.
    The classifier happily learned that artefact instead of anything about
    speech. Silent frames are now excluded from every descriptor, and the
    reported active-frame ratio makes the exclusion visible.
    """
    freqs = np.fft.rfftfreq(N_FFT, d=1.0 / sr)[: power.shape[1]]
    empty = {k: 0.0 for k in ("centroid_hz", "bandwidth_hz", "rolloff_hz",
                              "flatness", "flux", "crest")}
    empty["active_frame_ratio"] = 0.0
    if power.shape[0] == 0:
        return empty

    total = power.sum(axis=1)
    active = total > _SILENT_FRAME_ENERGY
    ratio = float(np.mean(active))
    if not np.any(active):
        out = dict(empty)
        out["active_frame_ratio"] = 0.0
        return out

    p_active = power[active]
    total_active = total[active]
    p = p_active / total_active[:, None]

    centroid = float(np.mean(p @ freqs))
    bandwidth = float(np.mean(np.sqrt(np.sum(p * (freqs[None, :] - (p @ freqs)[:, None]) ** 2, axis=1))))
    cum = np.cumsum(p, axis=1)
    roll = freqs[np.argmax(cum >= 0.85, axis=1)]
    geo = np.exp(np.mean(np.log(p_active + _EPS), axis=1))
    arith = np.mean(p_active, axis=1) + _EPS
    flatness = float(np.mean(geo / arith))

    if p.shape[0] > 1:
        num = np.linalg.norm(np.diff(p, axis=0), axis=1)
        den = np.linalg.norm(p[:-1], axis=1)
        ok = den > 1e-9
        flux = float(np.mean(num[ok] / den[ok])) if np.any(ok) else 0.0
    else:
        flux = 0.0
    crest = float(np.mean(np.max(p_active, axis=1) / (np.mean(p_active, axis=1) + _EPS)))

    return {
        "centroid_hz": round(centroid, 1),
        "bandwidth_hz": round(bandwidth, 1),
        "rolloff_hz": round(float(np.mean(roll)), 1),
        "flatness": round(flatness, 6),
        "flux": round(flux, 6),
        "crest": round(crest, 4),
        "active_frame_ratio": round(ratio, 4),
    }


# --------------------------------------------------------------------------- #
# Public API
# --------------------------------------------------------------------------- #
def extract(x: np.ndarray, sr: int = SAMPLE_RATE) -> Dict[str, Any]:
    """Full frontend for one clip.

    Returns a dict with:
      ``scalars``   — named, human-readable measurements (what reasons cite)
      ``matrix``    — (n_frames, n_dims) standardisation-ready feature matrix
      ``dims``      — ordered dim names matching ``matrix`` columns
      ``version``   — FEATURES_VERSION, pins model compatibility
    """
    x = np.asarray(x, dtype=np.float64).ravel()
    frames = frame_signal(x, WIN, HOP)
    power = power_spectrum(frames)
    lfc = lfcc(power)
    mfc = mfcc(power)
    d_lfc = deltas(lfc)
    d_mfc = deltas(mfc)

    blocks = [b for b in (lfc, d_lfc, mfc, d_mfc) if b.shape[0] == lfc.shape[0]]
    matrix = np.concatenate(blocks, axis=1) if blocks and lfc.shape[0] else np.empty((0, N_LFCC * 2 + N_MFCC * 2))
    dims = ([f"lfcc_{i}" for i in range(N_LFCC)]
            + [f"lfcc_d_{i}" for i in range(N_LFCC)]
            + [f"mfcc_{i}" for i in range(N_MFCC)]
            + [f"mfcc_d_{i}" for i in range(N_MFCC)])

    spec = _spectral_shape(power, sr)
    f0 = f0_track(x, sr)
    f0s = _nan_stats(f0)
    hnr = harmonicity(x, sr)
    rms = np.sqrt(np.mean(frames ** 2, axis=1)) if frames.size else np.empty(0)
    pauses = pause_stats(rms, HOP, sr)

    energy = float(np.sqrt(np.mean(x ** 2)))
    peak = float(np.max(np.abs(x))) if x.size else 0.0
    clipped = float(np.mean(np.abs(x) >= 0.999)) if x.size else 0.0

    scalars: Dict[str, Any] = {
        "duration_s": round(x.size / sr, 4),
        "rms": round(energy, 6),
        "peak": round(peak, 4),
        "clipped_ratio": round(clipped, 6),
        "zcr": round(float(np.mean(np.abs(np.diff(np.signbit(x))))) if x.size > 1 else 0.0, 5),
        **{f"spec_{k}": v for k, v in spec.items()},
        "f0_mean_hz": f0s["mean"],
        "f0_std_hz": f0s["std"],
        "f0_cv": f0s["cv"],
        "voiced_pct": f0s["voiced_pct"],
        "harmonicity": hnr,
        "n_pauses": pauses["count"],
        "pause_mean_s": pauses["mean_s"],
        "pause_cv": pauses["cv"],
        "pause_regularity": pauses["regularity"],
        "speech_ratio": pauses["speech_ratio"],
        "n_frames": int(frames.shape[0]),
    }
    return {"scalars": _sanitize(scalars), "matrix": matrix, "dims": dims,
            "version": FEATURES_VERSION}


# Cepstral coefficient 0 is log-energy, not timbre. Leaving it in the model
# vector is what destroyed the Phase-3 model's robustness:
#
#   same clip, LFCC c0:  -56.75 clean  ->  +0.67 with 0.02 of added noise
#
# A 57-unit swing on an unchanged utterance, because c0 is dominated by how
# many near-silent frames the clip contains. A model that keys on it learns
# loudness and silence statistics, then breaks the moment gain or noise
# changes. C0 is excluded from the model vector (it is still reported in
# ``scalars`` for humans and for the reason rules).
_ENERGY_DIMS_EXCLUDED: bool = True


def _model_columns(dims: List[str]) -> List[int]:
    """Indices of the timbre-bearing dimensions (all but the c0 terms)."""
    if not _ENERGY_DIMS_EXCLUDED:
        return list(range(len(dims)))
    skip = {"lfcc_0", "lfcc_d_0", "mfcc_0", "mfcc_d_0"}
    return [i for i, name in enumerate(dims) if name not in skip]


# Robus​tness anchor: the clip's own median absolute cepstral magnitude. Dividing
# by it removes gain without destroying the frame-to-frame variance that
# actually carries the signal (an earlier attempt at full per-clip z-scoring
# made the pooled mean identically zero and the model learned nothing — see the
# Phase-3 notes in VOICEGUARD_ROADMAP.md).
def vector_for_model(x: np.ndarray, sr: int = SAMPLE_RATE) -> np.ndarray:
    """Fixed-length, gain-robust summary vector for the Phase-3 model.

    Three steps, each tied to a measured failure during Phase 3:

    1. **Drop the energy terms** (``lfcc_0``/``mfcc_0`` + deltas). LFCC c0
       swung -56.75 -> +0.67 on the *same clip* with 0.02 of added noise: it is
       log-energy, and how many silent frames a clip happens to contain
       dominates it.

    2. **Divide by a scalar robust anchor** — the median absolute value across
       all remaining dimensions. This makes the vector gain-invariant (a
       measured gain drift of 0.31 -> 0.000) *without* flattening the
       frame-to-frame structure, because a single scalar is shared by every
       frame.

    3. **Mean and std pool the result.** The mean captures central tendency;
       the std captures how much the spectrum moves over time, which is the
       cue that separates a machine-regular voice from a human one.

    Deliberately *not* done: per-dimension z-scoring within the clip. It looks
    principled and is catastrophically wrong here — it makes the pooled mean
    identically 0 and every dimension's std identically 1, so the vector
    carries no information and the classifier falls to chance (EER 0.50,
    measured). Normalisation must remove *scale*, not *variance*.
    """
    feats = extract(x, sr)
    m = feats["matrix"]
    cols = _model_columns(feats["dims"])
    if m.shape[0] == 0:
        return np.zeros(len(cols) * 2)
    m = m[:, cols]
    anchor = float(np.median(np.abs(m)))
    if anchor < 1e-6:
        anchor = 1.0
    m = m / anchor
    return np.concatenate([m.mean(axis=0), m.std(axis=0)])
