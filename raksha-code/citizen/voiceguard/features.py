"""Deterministic, explainable acoustic descriptors for VoiceGuard.

These descriptors are diagnostics and model inputs, not a standalone deepfake
classifier. Real speech must remain INCONCLUSIVE until a validated anti-spoof
model is available.
"""
from __future__ import annotations
import math
from typing import Dict
import numpy as np

SAMPLE_RATE = 16_000
_FRAME_LENGTH = 400
_FRAME_HOP = 160
_FFT_SIZE = 512
_LFCC_FILTERS = 20
_CEPSTRAL_ORDER = 12

def _frames(samples: np.ndarray) -> np.ndarray:
    x = np.asarray(samples, dtype=np.float64)
    if x.size < _FRAME_LENGTH:
        x = np.pad(x, (0, _FRAME_LENGTH - x.size))
    count = 1 + int(math.ceil((x.size - _FRAME_LENGTH) / _FRAME_HOP))
    padded_size = (count - 1) * _FRAME_HOP + _FRAME_LENGTH
    if padded_size > x.size:
        x = np.pad(x, (0, padded_size - x.size))
    starts = np.arange(count) * _FRAME_HOP
    return np.stack([x[start:start + _FRAME_LENGTH] for start in starts])

def _linear_filterbank() -> np.ndarray:
    bins = _FFT_SIZE // 2 + 1
    edges = np.linspace(0, bins - 1, _LFCC_FILTERS + 2)
    bank = np.zeros((_LFCC_FILTERS, bins), dtype=np.float64)
    for index in range(_LFCC_FILTERS):
        left, centre, right = edges[index:index + 3]
        for k in range(bins):
            if left <= k <= centre and centre > left:
                bank[index, k] = (k - left) / (centre - left)
            elif centre < k <= right and right > centre:
                bank[index, k] = (right - k) / (right - centre)
    return bank

_LFCC_BANK = _linear_filterbank()
_LFCC_DCT = np.cos(np.pi / _LFCC_FILTERS
                   * np.arange(_CEPSTRAL_ORDER + 1)[:, None]
                   * (np.arange(_LFCC_FILTERS)[None, :] + 0.5))

def _lfcc(frame_matrix: np.ndarray) -> np.ndarray:
    emphasized = np.empty_like(frame_matrix)
    emphasized[:, 0] = frame_matrix[:, 0]
    emphasized[:, 1:] = frame_matrix[:, 1:] - 0.97 * frame_matrix[:, :-1]
    spectrum = np.abs(np.fft.rfft(emphasized * np.hamming(_FRAME_LENGTH),
                                  n=_FFT_SIZE, axis=1)) ** 2
    energies = spectrum @ _LFCC_BANK.T
    return (2.0 / _LFCC_FILTERS) * (
        np.log(np.maximum(energies, 1e-10)) @ _LFCC_DCT.T
    )

def _lpcc_one(frame: np.ndarray) -> np.ndarray:
    x = frame.astype(np.float64)
    x = x - np.mean(x)
    ac = np.correlate(x, x, mode="full")[len(x) - 1:len(x) + _CEPSTRAL_ORDER]
    ac[0] = max(float(ac[0]), 1e-10)
    lpc = np.zeros(_CEPSTRAL_ORDER + 1, dtype=np.float64)
    lpc[0] = 1.0
    error = float(ac[0])
    for order in range(1, _CEPSTRAL_ORDER + 1):
        numerator = float(ac[order])
        for j in range(1, order):
            numerator += lpc[j] * ac[order - j]
        reflection = float(np.clip(-numerator / max(error, 1e-10), -0.98, 0.98))
        prior = lpc.copy()
        for j in range(1, order):
            lpc[j] = prior[j] + reflection * prior[order - j]
        lpc[order] = reflection
        error *= max(1.0 - reflection * reflection, 1e-6)
    cepstra = np.zeros(_CEPSTRAL_ORDER + 1, dtype=np.float64)
    cepstra[0] = math.log(max(float(ac[0]), 1e-10))
    for n in range(1, _CEPSTRAL_ORDER + 1):
        value = -lpc[n]
        for k in range(1, n):
            value -= (k / n) * cepstra[k] * lpc[n - k]
        cepstra[n] = value
    return cepstra

def extract_features(samples: np.ndarray, sample_rate: int = SAMPLE_RATE) -> Dict[str, object]:
    """Return scalar descriptors plus LFCC/LPCC summary vectors."""
    x = np.asarray(samples, dtype=np.float64)
    if x.size == 0 or sample_rate <= 0:
        return {}
    rms = float(np.sqrt(np.mean(x * x)))
    zcr = float(np.mean(np.abs(np.diff(np.signbit(x))))) if x.size > 1 else 0.0
    spectrum = np.abs(np.fft.rfft(x * np.hanning(x.size))) + 1e-12
    power = spectrum ** 2
    probabilities = spectrum / np.sum(spectrum)
    frequencies = np.fft.rfftfreq(x.size, d=1.0 / sample_rate)
    centroid = float(np.sum(probabilities * frequencies))
    flatness = float(np.exp(np.mean(np.log(spectrum))) / np.mean(spectrum))
    peak = float(np.max(np.abs(x)))
    crest = peak / (rms + 1e-12)
    cumulative = np.cumsum(power)
    rolloff_index = int(np.searchsorted(cumulative, 0.85 * cumulative[-1]))
    rolloff = float(frequencies[min(rolloff_index, len(frequencies) - 1)])
    bandwidth = float(np.sqrt(np.sum(probabilities * (frequencies - centroid) ** 2)))
    frames = _frames(x)
    lfcc_values = _lfcc(frames)
    lpcc_values = np.stack([_lpcc_one(frame) for frame in frames])
    return {
        "duration_ms": round(1000.0 * x.size / sample_rate, 1),
        "rms": round(rms, 7), "peak": round(peak, 7), "zcr": round(zcr, 5),
        "spectral_centroid_hz": round(centroid, 1),
        "spectral_bandwidth_hz": round(bandwidth, 1),
        "spectral_rolloff_85_hz": round(rolloff, 1),
        "spectral_flatness": round(flatness, 7), "crest_factor": round(crest, 4),
        "lfcc_mean": np.round(np.mean(lfcc_values, axis=0), 5).tolist(),
        "lfcc_std": np.round(np.std(lfcc_values, axis=0), 5).tolist(),
        "lpcc_mean": np.round(np.mean(lpcc_values, axis=0), 5).tolist(),
    }
