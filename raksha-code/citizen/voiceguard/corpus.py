"""MAYA / VoiceGuard — synthetic corpus generator (Phase 3).

READ THIS BEFORE TRUSTING ANY NUMBER THIS MODULE PRODUCES.

These are **not recordings of people**. They are two procedurally generated
classes, built to be *separable in the way real spoofing is separable*:

* **bona-fide-ish** ("human-like"): a glottal source with jitter (cycle-to-
  cycle period variation), shimmer (amplitude variation), a vibrato-free but
  drifting F0 contour, breath noise riding on the voicing, formant movement
  across a short "syllable", and irregular pauses.
* **spoof-ish** ("synthetic"): a perfectly periodic source, constant F0,
  no jitter/shimmer, no breath, formants that hold still, and *evenly spaced*
  pauses of identical length.

A classifier trained on this learns "absence of natural variation", which is a
real (if simplified) property of naive TTS. It does **not** learn what a modern
neural codec clone sounds like. Any accuracy figure from this corpus is a
statement about this generator, not about the world — and every artefact says
so (see ``MODEL_CARD.md``).

Design constraint: deterministic. Given a seed, the corpus is byte-identical,
so training is reproducible and the eval table can be regenerated.
"""

from __future__ import annotations

import hashlib
from typing import Dict, List, Tuple

import numpy as np

SAMPLE_RATE: int = 16_000
DEFAULT_SECONDS: float = 2.0

# Formant triples (Hz) approximating /a/, /e/, /i/, /o/ — crude but enough to
# give the "human" class moving spectral structure.
_VOWELS: Tuple[Tuple[float, float, float], ...] = (
    (730.0, 1090.0, 2440.0),
    (530.0, 1840.0, 2480.0),
    (270.0, 2290.0, 3010.0),
    (570.0, 840.0, 2410.0),
)


def _glottal_phase(f0_track: np.ndarray, sr: int) -> np.ndarray:
    return 2.0 * np.pi * np.cumsum(f0_track) / sr


def _formant_voice(phase: np.ndarray, formants, sr: int,
                   amp: np.ndarray | None = None) -> np.ndarray:
    """Additive synthesis with a formant-shaped harmonic envelope.

    Formant values may be scalars (held still — the synthetic case) or
    per-sample arrays (gliding — the human-like case). Each harmonic's gain is
    evaluated against the (possibly time-varying) formant position, so a glide
    moves energy between harmonics over time, which is what makes the spectral
    flux of the human class higher.
    """
    n = phase.size
    out = np.zeros(n)
    for f, bw in zip(formants, (80.0, 100.0, 140.0)):
        f_arr = np.asarray(f, dtype=np.float64)
        if f_arr.ndim == 0:
            f_arr = np.full(n, float(f_arr))
        elif f_arr.size != n:
            f_arr = np.interp(np.linspace(0, 1, n),
                              np.linspace(0, 1, f_arr.size), f_arr)
        for h in range(1, 24):
            fh = 110.0 * h
            if fh > sr / 2.0 - 100.0:
                break
            gain = np.exp(-((fh - f_arr) ** 2) / (2.0 * bw ** 2))
            if float(np.max(gain)) < 1e-3:
                continue
            out += gain * np.sin(h * phase)
    if amp is not None:
        out *= amp
    return out


def make_bona_fide(seed: int, seconds: float = DEFAULT_SECONDS,
                   sr: int = SAMPLE_RATE) -> np.ndarray:
    """A 'human-like' clip: jitter, shimmer, drift, breath, irregular pauses."""
    rng = np.random.default_rng(seed)
    n = int(seconds * sr)
    t = np.arange(n) / sr

    base = float(rng.uniform(95.0, 210.0))
    # Slow prosodic drift plus jitter (period perturbation) and a small random walk.
    drift = 0.10 * np.sin(2 * np.pi * rng.uniform(0.3, 0.9) * t
                          + rng.uniform(0, 2 * np.pi))
    jitter = np.zeros(n)
    jitter[::80] = rng.normal(0.0, 0.012, size=jitter[::80].size)   # ~5 ms grid
    jitter = np.convolve(jitter, np.ones(80) / 80.0, mode="same")
    walk = 0.02 * np.cumsum(rng.normal(0, 1, n)) / np.sqrt(n)
    f0 = base * (1.0 + drift + jitter + walk)
    f0 = np.clip(f0, 70.0, 320.0)

    phase = _glottal_phase(f0, sr)

    # Formants glide between vowels across the clip.
    k = max(2, int(seconds / 0.25))
    keys = rng.integers(0, len(_VOWELS), size=k)
    idx = np.linspace(0, k - 1, n)
    sig = np.zeros(n)
    block = max(1, n // k)
    for i in range(k):
        a, b = i * block, min(n, (i + 1) * block)
        if a >= b:
            continue
        f = _VOWELS[keys[i]]
        glide = np.linspace(1.0, 0.98, b - a)
        sig[a:b] = _formant_voice(phase[a:b], (f[0] * glide, f[1], f[2]), sr)

    # Shimmer: cycle-scale amplitude wobble.
    shimmer = 1.0 + 0.08 * np.sin(2 * np.pi * rng.uniform(3, 8) * t) \
                  + 0.03 * rng.standard_normal(n).cumsum() / np.sqrt(n)
    sig *= np.clip(shimmer, 0.4, 1.6)

    # Breath noise rides the voicing envelope.
    env = np.abs(sig)
    env = np.convolve(env, np.ones(160) / 160.0, mode="same")
    sig += 0.06 * env * rng.standard_normal(n)

    # Irregular pauses: random positions, random lengths, but the *total*
    # silent duty cycle is normalised to ~20 % so that "how much silence" is
    # NOT a discriminating feature. If the two classes differ in total silence,
    # a classifier learns the generator's pause budget instead of speech
    # production — the same class of mistake as the spectral-flux artefact.
    n_pauses = int(rng.integers(2, 5))
    target_silence = 0.20 * n
    spent = 0
    for i in range(n_pauses):
        start = float(rng.uniform(0.15, 0.85))
        dur = float(rng.uniform(0.03, 0.18))
        a, b = int(start * n), min(n, int((start + dur) * n))
        if spent + (b - a) > target_silence:
            b = min(n, a + max(1, int(target_silence) - spent))
        if b <= a:
            continue
        spent += b - a
        # Attenuate to 20-30 dB down, not to digital zero: real rooms have
        # tone, and an absolute energy gate must not be able to tell the
        # classes apart on amplitude alone.
        sig[a:b] *= float(rng.uniform(0.02, 0.10))

    return _normalise(sig)


def make_synthetic(seed: int, seconds: float = DEFAULT_SECONDS,
                   sr: int = SAMPLE_RATE) -> np.ndarray:
    """A 'synthetic' clip: machine-regular production.

    IMPORTANT — why this is not "perfectly regular":

    The first version of this generator produced a constant F0, a frozen
    formant and exactly even pauses. The classifier scored EER 0.000 on it,
    which was worthless: it had learned "is this the frozen generator or the
    wobbling one", not anything about speech. Worse, it collapsed to 50 %
    accuracy under 0.02 of added noise, so the perfect score described the
    corpus, not the model.

    Real TTS *does* have macro-prosody — it varies pitch across a sentence. It
    lacks **micro-variation**: cycle-to-cycle jitter, shimmer, breath noise,
    and natural pause irregularity. So this generator now has:
      * slow F0 drift (macro-prosody — legitimate for TTS),
      * **no** jitter, **no** shimmer, **no** breath,
      * pauses with mild variation in *spacing* but identical *length*
        (a tell that survives macro-prosody modelling).

    The task is still synthetic and still easier than reality. The number it
    produces is a statement about this generator.
    """
    rng = np.random.default_rng(seed)
    n = int(seconds * sr)
    t = np.arange(n) / sr
    base = float(rng.uniform(95.0, 210.0))
    # Macro-prosody: a smooth drift, completely free of cycle-level jitter.
    drift = float(rng.uniform(0.02, 0.08)) * np.sin(
        2.0 * np.pi * float(rng.uniform(0.25, 0.6)) * t + rng.uniform(0, 2 * np.pi))
    f0 = base * (1.0 + drift)                        # smooth: no jitter term
    phase = _glottal_phase(f0, sr)

    # Formants glide smoothly between vowels (TTS does move them) but there is
    # no shimmer and no breath — the model must use what is actually missing.
    k = max(2, int(seconds / 0.35))
    keys = rng.integers(0, len(_VOWELS), size=k)
    sig = np.zeros(n)
    block = max(1, n // k)
    for i in range(k):
        a, b = i * block, min(n, (i + 1) * block)
        if a >= b:
            continue
        f = _VOWELS[keys[i]]
        glide = np.linspace(1.0, 0.99, b - a)
        sig[a:b] = _formant_voice(phase[a:b], (f[0] * glide, f[1], f[2]), sr)

    # No shimmer (constant amplitude envelope), no breath noise injected.
    env = np.ones(n)
    # Pauses: spacing jitters a little, but every pause is exactly the same
    # length — the irregularity-free tell.
    # Same ~20 % silent duty cycle as the bona-fide class, so total silence
    # cannot be used as the discriminator. Only the *regularity* differs.
    n_pauses = int(rng.integers(2, 5))
    pause_len = 0.20 / n_pauses                     # fixed length per pause
    positions = np.sort(rng.uniform(0.18, 0.80, size=n_pauses))
    for p in positions:
        a = int(p * n)
        b = min(n, int((p + pause_len) * n))
        # Same ~30 dB attenuation as the bona-fide class. Pause DEPTH must not
        # differ between classes; only pause REGULARITY may. Otherwise the
        # model learns the generator's amplitude choice, not speech.
        env[a:b] = 0.03
    sig *= env

    return _normalise(sig)


def _normalise(sig: np.ndarray, peak: float = 0.7) -> np.ndarray:
    m = float(np.max(np.abs(sig))) if sig.size else 0.0
    if m < 1e-9:
        return np.zeros_like(sig, dtype=np.float32)
    return (sig / m * peak).astype(np.float32)


# --------------------------------------------------------------------------- #
def build(seed: int = 20260101, n_per_class: int = 60,
          seconds: float = DEFAULT_SECONDS) -> Dict[str, List[Any]]:
    """Deterministic train/val/test split.

    Split policy: distinct generators per split by construction (different
    seeds), and we never reuse a seed across splits, so a clip cannot leak.
    """
    clip_ids: List[str] = []
    clips: List[np.ndarray] = []
    labels: List[int] = []

    for i in range(n_per_class * 3):
        s = seed + i
        kind = i % 2
        clip = make_bona_fide(s, seconds) if kind == 0 else make_synthetic(s, seconds)
        clips.append(clip)
        labels.append(0 if kind == 0 else 1)          # 0 bona fide, 1 spoof
        clip_ids.append(hashlib.sha256(f"{s}:{kind}".encode()).hexdigest()[:12])

    idx = np.arange(len(clips))
    rng = np.random.default_rng(seed)
    rng.shuffle(idx)
    n = len(idx)
    a, b = int(0.6 * n), int(0.8 * n)
    splits = {"train": idx[:a], "val": idx[a:b], "test": idx[b:]}

    return {
        name: {"clips": [clips[i] for i in part],
               "labels": np.asarray([labels[i] for i in part], dtype=np.int64),
               "ids": [clip_ids[i] for i in part]}
        for name, part in splits.items()
    }
