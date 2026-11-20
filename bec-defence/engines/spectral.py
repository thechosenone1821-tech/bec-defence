# engines/spectral.py
import math
from collections import deque

import numpy as np


class SpectralCondensationDetector:
    def __init__(self, safety_margin=1.2, z_alert=2.5, min_sessions_per_feature=10.0):
        self.safety_margin = safety_margin
        self.z_alert = z_alert
        self.min_sessions_per_feature = min_sessions_per_feature
        self.baseline_mean = None
        self.baseline_std = None
        self.empirical_edge = None

    def fit_baseline(self, X_normal):
        """Fit standardisation stats on known-normal traffic. Re-fit periodically."""
        self.baseline_mean = X_normal.mean(axis=0)
        std = X_normal.std(axis=0)
        self.baseline_std = np.where(std < 1e-6, 1.0, std)

    def calibrate_empirical_edge(self, lambda_max_history):
        """Optional: use historical normal windows as the null instead of pure MP."""
        self.empirical_edge = float(np.quantile(lambda_max_history, 0.999)) * self.safety_margin

    def analyze_traffic(self, session_matrix):
        X = np.asarray(session_matrix, dtype=float)
        n, d = X.shape
        if n < self.min_sessions_per_feature * d:
            return {"attack_detected": False, "reason": "INSUFFICIENT_SESSIONS",
                    "lambda_max": None, "mp_threshold": None,
                    "condensation_ratio": None, "suspect_indices": []}

        mean = self.baseline_mean if self.baseline_mean is not None else X.mean(axis=0)
        std = self.baseline_std if self.baseline_std is not None else X.std(axis=0)
        Z = (X - mean) / std

        C = (Z.T @ Z) / n
        eigvals, eigvecs = np.linalg.eigh(C)
        lambda_max = float(eigvals[-1])
        condensation = lambda_max / max(float(np.trace(C)), 1e-9)

        mp_edge = (1.0 + math.sqrt(d / n)) ** 2
        threshold = self.empirical_edge or mp_edge * self.safety_margin
        detected = lambda_max > threshold

        v = eigvecs[:, -1]
        z_scores = Z @ v                      # raw projections: ~N(0,1) under null
        suspects = np.where(np.abs(z_scores) > self.z_alert)[0].tolist()

        return {
            "attack_detected": bool(detected),
            "lambda_max": round(lambda_max, 3),
            "mp_threshold": round(threshold, 3),
            "condensation_ratio": round(condensation, 3),
            "suspect_indices": suspects,
            "suspect_zscores": [round(float(z_scores[i]), 2) for i in suspects],
        }


class RollingSpectralMonitor:
    """CUSUM accumulator: catches weak-but-persistent swarms that a single
    window's lambda_max never exceeds the alarm threshold."""

    def __init__(self, detector, window=500, check_every=25, drift=0.15, alarm_h=1.0):
        self.det = detector
        self.buf = deque(maxlen=window)
        self.window, self.every = window, check_every
        self.k, self.h = drift, alarm_h
        self.S, self.tick, self.null = 0.0, 0, None

    def add_session(self, feats):
        self.buf.append(feats)
        self.tick += 1
        if len(self.buf) < self.window or self.tick % self.every:
            return None
        res = self.det.analyze_traffic(np.array(self.buf))
        if self.null is None:                       # calibrate null on first full window
            n, d = np.array(self.buf).shape
            self.null = (1.0 + math.sqrt(d / n)) ** 2
        excess = max(0.0, res["lambda_max"] - self.null - self.k)
        self.S = max(0.0, self.S + excess)          # accumulate; noise resets toward 0
        if self.S > self.h:
            self.S = 0.0
            return res                              # persistent-elevation alarm
        return None