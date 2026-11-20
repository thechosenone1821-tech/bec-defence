"""Spectral coordination detection.

Design notes (read before relying on this engine)
--------------------------------------------------

1.  The leading eigenvalue of ``Z.T @ Z / n`` is treated as *evidence of
    anomalous structure*, not proof of malicious coordination. Per-feature
    standardisation does **not** remove normal correlations between features,
    so the Marchenko-Pastur (MP) edge is a heuristic null, not a guarantee.
    Production deployments should call :meth:`calibrate_empirical_edge` on
    held-out benign windows that include correlated benign workloads.

2.  ``Z.T @ Z / n`` is baseline-centred, so a current-window mean shift can
    raise the leading eigenvalue even without coordinated agents. We expose a
    separate ``mean_shift_stat`` (squared Mahalanobis distance of the window
    mean from the baseline mean) so callers can tell the two effects apart.

3.  ``attack_detected`` reflects **only** the ``lambda_max > threshold``
    decision. ``suspect_indices`` is a separate *candidate anomaly* list and
    MAY be non-empty when ``attack_detected`` is ``False`` -- do not treat a
    non-empty suspect list as permission to act. Downstream enforcement must
    consult ``attack_detected`` / ``alert_level`` explicitly.

4.  Internal statistics are kept unrounded; rounding is applied only by
    :meth:`for_display`.
"""

from __future__ import annotations

import math
from collections import deque
from typing import Any

import numpy as np


# --------------------------------------------------------------------------- #
# Input validation helpers
# --------------------------------------------------------------------------- #
class InvalidSessionMatrix(ValueError):
    """Raised when a session matrix is structurally unusable."""


def _validate_session_matrix(session_matrix, *, min_features: int = 2) -> np.ndarray:
    """Coerce and validate a session-feature matrix.

    Raises :class:`InvalidSessionMatrix` for shape, dtype or finiteness
    problems. Constant-feature handling happens later in
    :meth:`SpectralCondensationDetector.analyze_traffic`, where the baseline
    guard can be applied.
    """
    if session_matrix is None:
        raise InvalidSessionMatrix("session_matrix is None")
    try:
        X = np.asarray(session_matrix, dtype=float)
    except (TypeError, ValueError) as exc:
        raise InvalidSessionMatrix(f"cannot convert to float matrix: {exc}") from exc
    if X.ndim != 2:
        raise InvalidSessionMatrix(
            f"expected a 2-D (n_sessions, n_features) matrix, got shape {X.shape}"
        )
    if X.shape[0] == 0 or X.shape[1] == 0:
        raise InvalidSessionMatrix(f"empty matrix: shape {X.shape}")
    if X.shape[1] < min_features:
        raise InvalidSessionMatrix(
            f"need at least {min_features} features for spectral analysis, "
            f"got {X.shape[1]}"
        )
    if not np.all(np.isfinite(X)):
        bad = int(np.sum(~np.isfinite(X)))
        raise InvalidSessionMatrix(f"matrix contains {bad} non-finite value(s)")
    return X


# --------------------------------------------------------------------------- #
# Spectral detector
# --------------------------------------------------------------------------- #
class SpectralCondensationDetector:
    """Spectral coordination detector on standardised session features."""

    def __init__(
        self,
        safety_margin: float = 1.2,
        z_alert: float = 2.5,
        min_sessions_per_feature: float = 10.0,
        constant_feature_floor: float = 1e-6,
    ):
        if safety_margin <= 0:
            raise ValueError("safety_margin must be > 0")
        if z_alert <= 0:
            raise ValueError("z_alert must be > 0")
        if min_sessions_per_feature <= 0:
            raise ValueError("min_sessions_per_feature must be > 0")
        if constant_feature_floor <= 0:
            raise ValueError("constant_feature_floor must be > 0")

        self.safety_margin = float(safety_margin)
        self.z_alert = float(z_alert)
        self.min_sessions_per_feature = float(min_sessions_per_feature)
        self.constant_feature_floor = float(constant_feature_floor)

        self.baseline_mean: np.ndarray | None = None
        self.baseline_std: np.ndarray | None = None
        self._baseline_constant_mask: np.ndarray | None = None
        self.empirical_edge: float | None = None
        self.n_features_: int | None = None

    # -- baseline ----------------------------------------------------------- #
    def fit_baseline(self, X_normal) -> None:
        """Fit standardisation statistics on known-normal traffic.

        Constant features (std < ``constant_feature_floor``) are replaced with
        ``1.0`` so they do not blow up the standardisation, and recorded in
        ``_baseline_constant_mask`` so callers can be warned that those
        features carry no information.
        """
        X = _validate_session_matrix(X_normal)
        self.n_features_ = X.shape[1]
        self.baseline_mean = X.mean(axis=0)
        std = X.std(axis=0)
        constant = std < self.constant_feature_floor
        self.baseline_std = np.where(constant, 1.0, std)
        self._baseline_constant_mask = constant
        # Fitting a new baseline invalidates any prior empirical edge.
        self.empirical_edge = None

    def calibrate_empirical_edge(self, lambda_max_history) -> None:
        """Use historical normal-window ``lambda_max`` values as the null.

        The empirical edge is the ``safety_margin``-scaled 0.999-quantile of
        the supplied history. When set, it overrides the MP edge in
        :meth:`analyze_traffic`.
        """
        hist = np.asarray(lambda_max_history, dtype=float)
        if hist.ndim != 1 or hist.size < 10:
            raise ValueError(
                "need at least 10 finite lambda_max history values to calibrate"
            )
        if not np.all(np.isfinite(hist)):
            raise ValueError("lambda_max_history contains non-finite values")
        self.empirical_edge = float(np.quantile(hist, 0.999)) * self.safety_margin

    # -- analysis ----------------------------------------------------------- #
    def _standardise(self, X: np.ndarray) -> np.ndarray:
        if self.baseline_mean is None or self.baseline_std is None:
            mean = X.mean(axis=0)
            std = X.std(axis=0)
            constant = std < self.constant_feature_floor
            std = np.where(constant, 1.0, std)
        else:
            mean = self.baseline_mean
            std = self.baseline_std
            if mean.shape[0] != X.shape[1]:
                raise InvalidSessionMatrix(
                    f"feature count mismatch: baseline has {mean.shape[0]} "
                    f"features, input has {X.shape[1]}"
                )
        return (X - mean) / std

    def analyze_traffic(self, session_matrix) -> dict[str, Any]:
        """Analyse one window of session features.

        Returns a dict with:

        * ``attack_detected`` -- ``lambda_max > threshold`` only.
        * ``alert_level`` -- one of ``"none" | "candidate" | "alarm"``:
          ``"alarm"`` means ``attack_detected``; ``"candidate"`` means
          suspects exist but the window did not cross threshold; ``"none"``
          means neither.
        * ``suspect_indices`` / ``suspect_zscores`` -- candidate anomalies,
          may be non-empty even when ``attack_detected`` is ``False``.
        * ``lambda_max`` / ``mp_threshold`` / ``condensation_ratio`` /
          ``mean_shift_stat`` -- unrounded internal statistics.
        * ``display`` -- rounded copies for human-readable output.
        """
        X = _validate_session_matrix(session_matrix)
        n, d = X.shape

        if self.n_features_ is not None and d != self.n_features_:
            raise InvalidSessionMatrix(
                f"feature count mismatch: baseline has {self.n_features_} "
                f"features, input has {d}"
            )

        if n < self.min_sessions_per_feature * d:
            return {
                "attack_detected": False,
                "alert_level": "none",
                "reason": "INSUFFICIENT_SESSIONS",
                "lambda_max": None,
                "mp_threshold": None,
                "condensation_ratio": None,
                "mean_shift_stat": None,
                "suspect_indices": [],
                "suspect_zscores": [],
                "constant_features": [],
                "display": None,
            }

        Z = self._standardise(X)

        # Baseline-centred second moment. Note: a window mean shift from the
        # baseline can still raise lambda_max; we surface mean_shift_stat so
        # callers can distinguish the two regimes.
        C = (Z.T @ Z) / n
        eigvals, eigvecs = np.linalg.eigh(C)
        lambda_max = float(eigvals[-1])
        trace = float(np.trace(C))
        condensation = lambda_max / trace if trace > 1e-12 else 0.0

        # Squared Mahalanobis distance of window mean from baseline mean.
        # NOT divided by n: this is an aggregate of the window mean, not a
        # per-sample statistic. Under the null (window drawn from baseline
        # distribution) it is approximately chi-squared with d degrees of
        # freedom.
        window_mean = X.mean(axis=0)
        if self.baseline_mean is not None and self.baseline_std is not None:
            mz = (window_mean - self.baseline_mean) / self.baseline_std
        else:
            mz = (window_mean - X.mean(axis=0)) / np.where(
                X.std(axis=0) < self.constant_feature_floor, 1.0, X.std(axis=0)
            )
        mean_shift_stat = float(mz @ mz)

        mp_edge = (1.0 + math.sqrt(d / n)) ** 2
        threshold = self.empirical_edge or (mp_edge * self.safety_margin)
        detected = lambda_max > threshold

        v = eigvecs[:, -1]
        z_scores = Z @ v
        suspect_mask = np.abs(z_scores) > self.z_alert
        suspects = np.where(suspect_mask)[0].tolist()

        # Constant-feature reporting: union of (a) features that were
        # constant in the baseline (so they carry no information ever) and
        # (b) features that became constant in this input window.
        if self._baseline_constant_mask is not None:
            base_const = self._baseline_constant_mask
        else:
            base_const = np.zeros(d, dtype=bool)
        window_const = X.std(axis=0) < self.constant_feature_floor
        constant_features = np.where(base_const | window_const)[0].tolist()

        alert_level = "alarm" if detected else ("candidate" if suspects else "none")

        return {
            "attack_detected": bool(detected),
            "alert_level": alert_level,
            "reason": "LAMBDA_EXCEEDED" if detected else ("SUSPECTS_PRESENT" if suspects else "OK"),
            "lambda_max": lambda_max,
            "mp_threshold": float(threshold),
            "condensation_ratio": condensation,
            "mean_shift_stat": mean_shift_stat,
            "suspect_indices": suspects,
            "suspect_zscores": [float(z_scores[i]) for i in suspects],
            "constant_features": constant_features,
            "display": self.for_display(
                lambda_max=lambda_max,
                threshold=threshold,
                condensation=condensation,
                mean_shift_stat=mean_shift_stat,
                suspect_zscores=[float(z_scores[i]) for i in suspects],
            ),
        }

    @staticmethod
    def for_display(**kwargs) -> dict[str, Any]:
        """Round numeric values for human-readable output only."""
        out: dict[str, Any] = {}
        for key, val in kwargs.items():
            if isinstance(val, float):
                out[key] = round(val, 3)
            elif isinstance(val, list):
                out[key] = [round(float(v), 2) for v in val]
            else:
                out[key] = val
        return out


# --------------------------------------------------------------------------- #
# Simple baselines for comparison (not coordination detectors)
# --------------------------------------------------------------------------- #
class MeanShiftBaseline:
    """A trivial mean-shift detector used as a comparison baseline.

    Flags a window if its mean shifts more than ``z_alert`` baseline-std
    units along any feature. Useful to show that the spectral detector is
    doing something the simple mean test cannot.
    """

    def __init__(self, z_alert: float = 3.0, constant_feature_floor: float = 1e-6):
        self.z_alert = float(z_alert)
        self.constant_feature_floor = float(constant_feature_floor)
        self.baseline_mean: np.ndarray | None = None
        self.baseline_std: np.ndarray | None = None

    def fit_baseline(self, X_normal) -> None:
        X = _validate_session_matrix(X_normal)
        self.baseline_mean = X.mean(axis=0)
        std = X.std(axis=0)
        self.baseline_std = np.where(std < self.constant_feature_floor, 1.0, std)

    def analyze_traffic(self, session_matrix) -> dict[str, Any]:
        X = _validate_session_matrix(session_matrix)
        if self.baseline_mean is None or self.baseline_std is None:
            raise RuntimeError("MeanShiftBaseline.fit_baseline must be called first")
        mean = X.mean(axis=0)
        z = (mean - self.baseline_mean) / self.baseline_std
        flagged = np.where(np.abs(z) > self.z_alert)[0].tolist()
        return {
            "attack_detected": bool(len(flagged) > 0),
            "alert_level": "alarm" if flagged else "none",
            "flagged_features": flagged,
            "max_abs_z": float(np.max(np.abs(z))),
        }


class DistanceBaseline:
    """A trivial distance-based detector used as a comparison baseline.

    Flags sessions whose Euclidean distance from the baseline mean exceeds
    ``z_alert`` baseline-std units. Captures gross outliers but not
    coordination.
    """

    def __init__(self, z_alert: float = 3.0, constant_feature_floor: float = 1e-6):
        self.z_alert = float(z_alert)
        self.constant_feature_floor = float(constant_feature_floor)
        self.baseline_mean: np.ndarray | None = None
        self.baseline_std: np.ndarray | None = None

    def fit_baseline(self, X_normal) -> None:
        X = _validate_session_matrix(X_normal)
        self.baseline_mean = X.mean(axis=0)
        std = X.std(axis=0)
        self.baseline_std = np.where(std < self.constant_feature_floor, 1.0, std)

    def analyze_traffic(self, session_matrix) -> dict[str, Any]:
        X = _validate_session_matrix(session_matrix)
        if self.baseline_mean is None or self.baseline_std is None:
            raise RuntimeError("DistanceBaseline.fit_baseline must be called first")
        Z = (X - self.baseline_mean) / self.baseline_std
        dist = np.linalg.norm(Z, axis=1)
        suspects = np.where(dist > self.z_alert)[0].tolist()
        return {
            "attack_detected": bool(len(suspects) > 0),
            "alert_level": "alarm" if suspects else "none",
            "suspect_indices": suspects,
            "max_distance": float(dist.max()) if dist.size else 0.0,
        }


# --------------------------------------------------------------------------- #
# Rolling CUSUM-style monitor
# --------------------------------------------------------------------------- #
class RollingSpectralMonitor:
    """One-sided CUSUM accumulator over sliding spectral windows.

    The accumulator decays correctly: ``increment`` may be negative when
    ``lambda_max`` falls below ``null + drift``, which lets normal traffic
    pull ``S`` back toward zero.

    .. note::

       Windows overlap by ``window - check_every`` rows. This is fine for
       alarm latency but means successive ``lambda_max`` samples are not
       independent -- thresholds calibrated on independent windows will be
       conservative (more alarms, not fewer). Calibrate on overlapping
       windows of the same step size if you want accurate false-alarm rates.
    """

    def __init__(
        self,
        detector: SpectralCondensationDetector,
        window: int = 500,
        check_every: int = 25,
        drift: float = 0.15,
        alarm_h: float = 1.0,
    ):
        if window < 10:
            raise ValueError("window must be >= 10")
        if check_every < 1 or check_every > window:
            raise ValueError("check_every must be in [1, window]")
        if drift < 0:
            raise ValueError("drift must be >= 0")
        if alarm_h <= 0:
            raise ValueError("alarm_h must be > 0")

        self.det = detector
        self.buf: deque = deque(maxlen=window)
        self.window = int(window)
        self.every = int(check_every)
        self.k = float(drift)
        self.h = float(alarm_h)
        self.S = 0.0
        self.tick = 0
        self.null: float | None = None
        self.last_result: dict[str, Any] | None = None

    def _calibrate_null(self) -> None:
        n, d = np.array(self.buf).shape
        self.null = (1.0 + math.sqrt(d / n)) ** 2

    def add_session(self, feats) -> dict[str, Any] | None:
        """Append one session's features; return an alarm result if ``S > h``.

        The returned dict is the underlying ``analyze_traffic`` result with
        an added ``cusum`` block (``S_before``, ``S_after``, ``increment``,
        ``null``, ``drift``). Returns ``None`` when no analysis was run this
        tick (window not full or not on a check beat).
        """
        feats_arr = np.asarray(feats, dtype=float)
        if feats_arr.ndim != 1 or feats_arr.size < 2:
            raise InvalidSessionMatrix(
                f"feats must be a 1-D array of length >= 2, got shape {feats_arr.shape}"
            )
        if not np.all(np.isfinite(feats_arr)):
            raise InvalidSessionMatrix("feats contains non-finite value(s)")

        self.buf.append(feats_arr)
        self.tick += 1

        if len(self.buf) < self.window:
            return None
        if (self.tick % self.every) != 0:
            return None

        res = self.det.analyze_traffic(np.array(self.buf))
        self.last_result = res

        # INSUFFICIENT_SESSIONS or other early returns: nothing to accumulate.
        if res["lambda_max"] is None:
            return None

        if self.null is None:
            self._calibrate_null()

        # Conventional one-sided CUSUM: increment can be negative, so normal
        # traffic pulls S back toward zero (the original code wrapped a
        # non-negative `excess` in max(0, ...), which prevented any decay).
        increment = res["lambda_max"] - self.null - self.k
        S_before = self.S
        self.S = max(0.0, self.S + increment)

        res = dict(res)
        res["cusum"] = {
            "S_before": float(S_before),
            "S_after": float(self.S),
            "increment": float(increment),
            "null": float(self.null),
            "drift": float(self.k),
            "threshold": float(self.h),
            "window_overlap_rows": int(self.window - self.every),
        }

        if self.S > self.h:
            self.S = 0.0  # reset after alarm
            return res
        return None
