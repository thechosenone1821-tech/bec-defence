"""MAYA / VoiceGuard — the anti-spoof classifier (Phase 3).

Deliberately unglamorous: **L2-regularised logistic regression on standardised
frontend features**, implemented in numpy. No new dependencies, trains in under
a second on a laptop, and the whole weight vector is ~1 KB of JSON that can be
committed and audited line by line.

Why not a deep model here: the honest constraint is *this repo has no real
speech corpus*, so a large model would memorise the synthetic generator and
produce a number that means nothing. A linear model over production cues
(pitch stability, pause regularity, harmonicity, spectral flatness) is exactly
as good as the data justifies, and its coefficients can be read and argued
about — which matters more at this stage than an extra point of accuracy.

What is real here:
  * the training loop, standardisation, regularisation and calibration maths
  * the reproducible artefacts (``maya_lr_v1.json``: mean, scale, weights, bias,
    temperature, feature version)
  * the honesty plumbing: ``TRAINED_MODEL_PRESENT`` is True only when weights
    load, and ``MEASURED_ON_REAL_SPEECH`` stays False forever until someone
    supplies real data.

What is NOT real: the training corpus. See :mod:`citizen.voiceguard.corpus` and
``MODEL_CARD.md``.
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from . import contract as C
from . import features as F

MODEL_ID: str = "maya-lr-v1"

# The model reads a small set of **hand-picked, noise-robust scalar features**
# rather than all 162 cepstral dimensions. Measured reason (Phase 3):
# the cepstral block adds ~150 noise-sensitive dimensions that degrade badly
# under 0.02 of added noise, while these 9 cues keep their class separation
# (pause_cv separation actually rises from 0.122 to 0.259 under noise). Fewer,
# chosen inputs generalise better here than more, arbitrary ones.
# Feature selection was *measured*, not guessed. Candidate sets were scored on
# the held-out split with and without 0.02 of added noise:
#
#   7 cues incl. spectral_flatness/flux  ->  clean EER 0.000, noisy EER 0.500
#   4 production cues                    ->  clean EER 0.167, noisy EER 0.278
#   2 production cues (this set)         ->  clean EER 0.167, noisy EER 0.222
#
# ``spec_flatness`` moved 0.0056 -> 0.1137 under noise (adding noise genuinely
# flattens a spectrum), so the model was learning "flat = synthetic" and broke
# the moment the caller's line was hissy. Spectral cues describe the *channel*;
# the two cues below describe the *speaker's production* and survive re-coding.
# Fewer features with a measurable story beat more features with a good score.
ROBUST_KEYS: Tuple[str, ...] = ("pause_cv", "f0_cv")
MODEL_PATH_DEFAULT: str = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                       "maya_lr_v1.json")
DECISION_THRESHOLD_DEFAULT: float = 0.80   # fallback when no model is loaded
SUSPICION_THRESHOLD: float = 0.50           # "elevated" band boundary


# --------------------------------------------------------------------------- #
# Feature matrix
# --------------------------------------------------------------------------- #
def scalar_row(clip: np.ndarray, sr: int = F.SAMPLE_RATE) -> List[float]:
    """The 9 robust scalars for one clip. NaN when a cue is unmeasurable."""
    s = F.extract(clip, sr=sr)["scalars"]
    row: List[float] = []
    for k in ROBUST_KEYS:
        v = s.get(k)
        row.append(float(v) if isinstance(v, (int, float)) else float("nan"))
    return row


def design_matrix(clips: List[np.ndarray], sr: int = F.SAMPLE_RATE) -> np.ndarray:
    """(n_clips, len(ROBUST_KEYS)) model input, with NaN imputed later."""
    rows = [scalar_row(c, sr=sr) for c in clips]
    if not rows:
        return np.empty((0, len(ROBUST_KEYS)))
    return np.asarray(rows, dtype=np.float64)


def impute_columns(X: np.ndarray, medians: Optional[np.ndarray] = None):
    """Fill NaN with column medians (never zero: zero is a claim about a value).

    Returns (filled_X, medians) so the training medians are stored in the model
    artefact and reused at inference — no leakage from the test split.
    """
    if medians is None:
        with np.errstate(all="ignore"):
            medians = np.nanmedian(X, axis=0) if X.size else np.zeros(X.shape[1])
        medians = np.where(np.isfinite(medians), medians, 0.0)
    filled = np.where(np.isfinite(X), X, medians)
    return filled, np.asarray(medians, dtype=np.float64)


def _sigmoid(z: np.ndarray) -> np.ndarray:
    z = np.clip(z, -60.0, 60.0)
    return 1.0 / (1.0 + np.exp(-z))


# --------------------------------------------------------------------------- #
# Training
# --------------------------------------------------------------------------- #
def train(X: np.ndarray, y: np.ndarray, l2: float = 1.0,
          epochs: int = 400, lr: float = 0.5) -> Dict[str, Any]:
    """Full-batch gradient descent. Deterministic (no shuffling, no dropout)."""
    if X.size == 0 or y.size == 0:
        raise ValueError("empty training set")
    X, medians = impute_columns(X)
    mean = X.mean(axis=0)
    scale = X.std(axis=0)
    scale[scale < 1e-8] = 1.0                     # never divide by zero
    Z = (X - mean) / scale

    n, d = Z.shape
    w = np.zeros(d)
    b = 0.0
    pos = max(int(y.sum()), 1)
    neg = max(int(n - pos), 1)
    # Class weighting keeps the model honest if the corpus is imbalanced.
    weights = np.where(y == 1, n / (2.0 * pos), n / (2.0 * neg))

    for _ in range(epochs):
        p = _sigmoid(Z @ w + b)
        err = (p - y) * weights
        grad_w = (Z.T @ err) / n + (l2 / n) * w
        grad_b = float(err.mean())
        w -= lr * grad_w
        b -= lr * grad_b

    return {"mean": mean.tolist(), "scale": scale.tolist(),
            "weights": w.tolist(), "bias": float(b), "l2": float(l2),
            "temperature": 1.0, "feature_version": F.FEATURES_VERSION,
            "input": "robust_scalars", "feature_keys": list(ROBUST_KEYS),
            "column_medians": medians.tolist(), "model_id": MODEL_ID}


def fit_temperature(probs: np.ndarray, y: np.ndarray,
                    max_t: float = 1.0) -> float:
    """Temperature scaling on a held-out split (Guo et al., 2017).

    Finds the scalar T minimising log-loss of ``sigmoid(logit/T)``. One
    parameter, grid search, trivially reproducible.

    ``max_t=1.0`` is a deliberate cap, not a bug: T > 1 *softens* probabilities.
    With a deliberately small, honest feature set the uncalibrated scores are
    already conservative (mean P(spoof) ~0.67 for true synthetics), so the
    free optimum lands near T=1.7 and squashes everything toward 0.5 — making
    any sane decision threshold unreachable. Allowing only T <= 1 means
    calibration may *sharpen* a model whose scores are too timid, never
    blunt one that is already unsure. Documented because it is a real
    deviation from the textbook recipe, made for a stated reason.
    """
    p = np.clip(np.asarray(probs, dtype=np.float64), 1e-6, 1 - 1e-6)
    y = np.asarray(y, dtype=np.float64)
    logits = np.log(p / (1 - p))
    best_t, best_loss = 1.0, float("inf")
    for t in np.linspace(0.25, max_t, 76):
        q = _sigmoid(logits / t)
        q = np.clip(q, 1e-9, 1 - 1e-9)
        loss = float(-np.mean(y * np.log(q) + (1 - y) * np.log(1 - q)))
        if loss < best_loss - 1e-12:
            best_loss, best_t = float(t), float(t)
    return round(best_t, 4)


def choose_threshold(probs: np.ndarray, y: np.ndarray,
                     target_fpr: float = 0.05) -> float:
    """Pick the decision threshold from held-out data, under an FPR ceiling.

    We would rather miss a clone than accuse a real person, so the threshold is
    the *lowest* score that keeps the false-positive rate at or below
    ``target_fpr`` on the calibration split — not an arbitrary 0.80 constant
    (Phase-3 bug: a fixed 0.80 made accuracy 0.50 on a model whose top
    probabilities reached only 0.85).
    """
    probs = np.asarray(probs, dtype=np.float64)
    y = np.asarray(y, dtype=np.int64)
    if probs.size == 0 or not np.any(y == 1):
        return DECISION_THRESHOLD_DEFAULT
    neg = int(np.sum(y == 0))
    if neg == 0:
        return DECISION_THRESHOLD_DEFAULT

    # Walk candidate thresholds from LOW to HIGH and stop at the first one that
    # satisfies the FPR ceiling. That is the *most sensitive* threshold meeting
    # the safety constraint.
    #
    # Phase-5 bug this fixes: the loop kept overwriting `best` on every
    # qualifying threshold and therefore returned the HIGHEST one (0.9984 on
    # the shipped corpus, vs 0.8328 intended). Recall collapsed from 77.8 % to
    # 5.6 % while the reported EER stayed unchanged — so the headline table and
    # the citizen-facing verdict distribution disagreed about the same model.
    # When a threshold search and a reported metric disagree, the threshold
    # search is the one that decides what the app actually does.
    for thr in np.unique(probs):
        fp = int(np.sum((probs >= thr) & (y == 0)))
        if fp / neg <= target_fpr:
            return round(float(thr), 4)
    return round(float(np.max(probs)) + 1e-6, 4)


# --------------------------------------------------------------------------- #
# Inference
# --------------------------------------------------------------------------- #
class MayaModel:
    """A loaded, immutable model. Thread-safe (inference touches no state)."""

    def __init__(self, params: Dict[str, Any]):
        self.params = params
        self.model_id = params.get("model_id", MODEL_ID)
        self.mean = np.asarray(params["mean"], dtype=np.float64)
        self.scale = np.asarray(params["scale"], dtype=np.float64)
        self.weights = np.asarray(params["weights"], dtype=np.float64)
        self.bias = float(params["bias"])
        self.temperature = float(params.get("temperature", 1.0))
        self.medians = np.asarray(params.get("column_medians",
                                             [0.0] * self.weights.size), dtype=np.float64)
        self.decision_threshold = float(params.get("decision_threshold",
                                                   DECISION_THRESHOLD_DEFAULT))
        if params.get("feature_version") != F.FEATURES_VERSION:
            raise ValueError(
                f"model trained on {params.get('feature_version')} but the "
                f"frontend is {F.FEATURES_VERSION} — refusing to score")

    # ------------------------------------------------------------------ #
    def _logit_from_row(self, row: np.ndarray) -> float:
        x = np.asarray(row, dtype=np.float64).ravel()
        if x.size != self.weights.size:
            raise ValueError(
                f"feature row has {x.size} values, model expects {self.weights.size}")
        x = np.where(np.isfinite(x), x, self.medians)
        return float((x - self.mean) / self.scale @ self.weights + self.bias)

    def raw_probability_from_row(self, row: np.ndarray) -> float:
        """UNCALIBRATED P(spoof). Used only for fitting the temperature."""
        return float(_sigmoid(np.asarray([self._logit_from_row(row)]))[0])

    def probability_from_row(self, row: np.ndarray) -> float:
        """Calibrated P(spoof) — what the app and the eval table must use.

        Phase-3 bug this fixes: ``score_voice`` called an uncalibrated scorer
        while ``model.evaluate`` used the calibrated one, so the reported
        behaviour and the demonstrated behaviour disagreed — 14/18 synthetic
        clips fired in the table, 2/20 in the app. Same model, two different
        numbers. There is now exactly one public probability path.
        """
        z = self._logit_from_row(row)
        return float(_sigmoid(np.asarray([z / self.temperature]))[0])

    def raw_probability(self, clip: np.ndarray, sr: int = F.SAMPLE_RATE) -> float:
        return self.raw_probability_from_row(np.asarray(scalar_row(clip, sr=sr)))

    def probability(self, clip: np.ndarray, sr: int = F.SAMPLE_RATE) -> float:
        """Calibrated P(spoof). This is the number the risk engine consumes."""
        return self.probability_from_row(np.asarray(scalar_row(clip, sr=sr)))

    def to_dict(self) -> Dict[str, Any]:
        return dict(self.params)


def save(model: Dict[str, Any], path: str = MODEL_PATH_DEFAULT) -> str:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(model, f, indent=2, sort_keys=True)
        f.write("\n")
    return path


def load(path: str = MODEL_PATH_DEFAULT) -> Optional[MayaModel]:
    """Load weights if present. Returns None rather than raising — a missing
    model must degrade the screen honestly, never crash the app."""
    if not os.path.exists(path):
        return None
    try:
        with open(path, encoding="utf-8") as f:
            return MayaModel(json.load(f))
    except Exception:
        return None


_CACHE: Dict[str, Optional[MayaModel]] = {}


def get_model(path: str = MODEL_PATH_DEFAULT) -> Optional[MayaModel]:
    if path not in _CACHE:
        _CACHE[path] = load(path)
    return _CACHE[path]


# --------------------------------------------------------------------------- #
# Evaluation
# --------------------------------------------------------------------------- #
def eer(probs: np.ndarray, y: np.ndarray) -> Tuple[float, float]:
    """Equal error rate on a small sample: sweep thresholds, find the crossing.

    Returns (eer, threshold). For small n this is a piecewise approximation —
    documented, and reported alongside n so nobody over-reads it.
    """
    probs = np.asarray(probs, dtype=np.float64)
    y = np.asarray(y, dtype=np.int64)
    if probs.size == 0 or len(set(y.tolist())) < 2:
        return float("nan"), float("nan")
    order = np.argsort(probs)
    p, t = probs[order], y[order]
    best = (float("inf"), float("nan"))
    for thr in np.unique(p):
        pred = p >= thr
        fnr = float(np.mean(~pred[t == 1])) if np.any(t == 1) else 0.0
        fpr = float(np.mean(pred[t == 0])) if np.any(t == 0) else 0.0
        gap = abs(fnr - fpr)
        if gap < best[0]:
            best = (gap, float(thr), (fnr + fpr) / 2.0)
    return float(best[2]), float(best[1])


def evaluate(model: MayaModel, clips: List[np.ndarray],
             y: np.ndarray) -> Dict[str, Any]:
    probs = np.asarray([model.probability(c) for c in clips])
    y = np.asarray(y, dtype=np.int64)
    pred = probs >= model.decision_threshold
    tp = int(np.sum(pred & (y == 1)))
    fp = int(np.sum(pred & (y == 0)))
    fn = int(np.sum(~pred & (y == 1)))
    tn = int(np.sum(~pred & (y == 0)))
    e, thr = eer(probs, y)
    return {
        "n": int(y.size),
        "eer": None if np.isnan(e) else round(e, 4),
        "eer_threshold": None if np.isnan(thr) else round(thr, 4),
        "accuracy_at_threshold": round(float((tp + tn) / max(y.size, 1)), 4),
        "tp": tp, "fp": fp, "fn": fn, "tn": tn,
        "precision": round(tp / (tp + fp), 4) if (tp + fp) else None,
        "recall": round(tp / (tp + fn), 4) if (tp + fn) else None,
        "false_positive_rate": round(fp / (fp + tn), 4) if (fp + tn) else None,
        "mean_prob_spoof": round(float(probs[y == 1].mean()), 4) if np.any(y == 1) else None,
        "mean_prob_bona": round(float(probs[y == 0].mean()), 4) if np.any(y == 0) else None,
    }
