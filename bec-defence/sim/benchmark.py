"""Seeded scenario-matrix benchmark for the spectral detector.

The original ``run_spectral_benchmark`` is kept for backward compatibility
(it reports only session-level precision/recall on one attack scenario).
The new entry point is :func:`run_scenario_matrix`, which:

* Generates calibration data and evaluation data from **separate** random
  seeds, so thresholds calibrated on one set are tested on another.
* Covers four benign regimes (independent, correlated, synchronised, drift)
  and four attack regimes (bot fraction, coordination strength, multiple
  swarms, persistent weak activity).
* Reports window-level detection rate, session-level precision/recall,
  false-alarm rate, detection delay (in sessions) and runtime per window.
* Compares the spectral detector against :class:`MeanShiftBaseline` and
  :class:`DistanceBaseline` so callers can see whether spectral detection is
  doing anything the trivial baselines cannot.

All RNG is seeded and explicit. Results are returned as plain dicts/lists so
they can be JSON-dumped or printed by :func:`summarize_matrix`.
"""

from __future__ import annotations

import time
from typing import Any, Callable

import numpy as np


# --------------------------------------------------------------------------- #
# Scenario generators
# --------------------------------------------------------------------------- #
def _label_matrix(n_humans: int, n_bots: int) -> np.ndarray:
    """Return a (n_humans + n_bots,) int8 array: 0=benign, 1=bot."""
    y = np.zeros(n_humans + n_bots, dtype=np.int8)
    y[n_humans:] = 1
    return y


def make_benign_scenario(
    name: str,
    n: int,
    d: int,
    rng: np.random.Generator,
) -> tuple[np.ndarray, np.ndarray]:
    """Return ``(X, y)`` for one benign scenario (y is all zeros)."""
    if name == "independent":
        X = rng.normal(0, 1, size=(n, d))
    elif name == "correlated":
        # Benign but correlated: two groups, each pulls a shared latent
        # factor. Lambda_max will be elevated even though no attack.
        half = n // 2
        f1 = rng.normal(0, 1, size=d)
        f2 = rng.normal(0, 1, size=d)
        g1 = f1 + rng.normal(0, 0.4, size=(half, d))
        g2 = f2 + rng.normal(0, 0.4, size=(n - half, d))
        X = np.vstack([g1, g2])
    elif name == "synchronised":
        # A legitimate synchronised job: a quarter of sessions share a
        # small common offset (e.g. a cron burst). Should ideally NOT be
        # flagged as an attack.
        X = rng.normal(0, 1, size=(n, d))
        sync = n // 4
        offset = rng.normal(0, 0.3, size=d)
        X[:sync] += offset
    elif name == "drift":
        # Gradual mean drift over the session ordering. Tests that the
        # detector does not alarm purely on slow drift.
        X = rng.normal(0, 1, size=(n, d))
        drift = np.linspace(0, 1.0, n)[:, None]
        X += drift * 0.3
    else:
        raise ValueError(f"unknown benign scenario {name!r}")
    return X, np.zeros(n, dtype=np.int8)


def make_attack_scenario(
    name: str,
    n_humans: int,
    n_bots: int,
    d: int,
    rng: np.random.Generator,
    *,
    jitter: float = 0.25,
    bot_fraction: float | None = None,
    coordination: float | None = None,
    n_swarms: int | None = None,
    persistent_strength: float | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """Return ``(X, y)`` for one attack scenario. y is 1 for bot rows."""
    if bot_fraction is not None:
        n_bots = max(1, int(bot_fraction * n_humans))
    humans = rng.normal(0, 1, size=(n_humans, d))

    if name == "single_swarm":
        coord = coordination if coordination is not None else 0.75
        template = rng.normal(0, 1, size=d) * coord
        bots = template + rng.normal(0, jitter, size=(n_bots, d))
    elif name == "multiple_swarms":
        n_swarms = n_swarms or 3
        per = max(1, n_bots // n_swarms)
        bot_blocks = []
        for _ in range(n_swarms):
            tmpl = rng.normal(0, 1, size=d)
            bot_blocks.append(tmpl + rng.normal(0, jitter, size=(per, d)))
        bots = np.vstack(bot_blocks)
        # Trim/pad to exactly n_bots
        if bots.shape[0] > n_bots:
            bots = bots[:n_bots]
        elif bots.shape[0] < n_bots:
            extra = rng.normal(0, 1, size=(n_bots - bots.shape[0], d))
            bots = np.vstack([bots, extra])
    elif name == "persistent_weak":
        # A weak swarm: small coordination, hard to catch in a single
        # window but should accumulate in a rolling monitor.
        strength = persistent_strength if persistent_strength is not None else 0.4
        template = rng.normal(0, 1, size=d) * strength
        bots = template + rng.normal(0, jitter, size=(n_bots, d))
    elif name == "strong_swarm":
        coord = coordination if coordination is not None else 1.5
        template = rng.normal(0, 1, size=d) * coord
        bots = template + rng.normal(0, jitter, size=(n_bots, d))
    else:
        raise ValueError(f"unknown attack scenario {name!r}")

    X = np.vstack([humans, bots])
    y = _label_matrix(n_humans, n_bots)
    return X, y


# --------------------------------------------------------------------------- #
# Backward-compatible simple benchmark (single scenario, single seed)
# --------------------------------------------------------------------------- #
def run_spectral_benchmark(
    detector,
    n_trials: int = 50,
    n_humans: int = 400,
    n_bots: int = 100,
    d: int = 8,
    jitter: float = 0.25,
    seed: int = 0,
    rng: np.random.Generator | None = None,
) -> dict[str, Any]:
    """Original 50-trial synthetic benchmark, kept for backward compatibility.

    Reports batch detection rate, session-level precision/recall and
    false-positive rate. This is a **synthetic-demo** result, not evidence
    of real-world protection.
    """
    rng = rng or np.random.default_rng(seed)
    tp = fp = fn = 0
    detected_batches = 0

    for _ in range(n_trials):
        X, y = make_attack_scenario(
            "single_swarm", n_humans, n_bots, d, rng, jitter=jitter
        )
        res = detector.analyze_traffic(X)
        detected_batches += int(res.get("attack_detected", False))
        flagged = set(res.get("suspect_indices", []))
        truth = set(np.where(y == 1)[0].tolist())
        tp += len(flagged & truth)
        fn += len(truth - flagged)
        fp += len(flagged - truth)

    precision = tp / max(tp + fp, 1)
    recall = tp / max(tp + fn, 1)
    return {
        "batch_detection_rate": round(detected_batches / n_trials, 3),
        "precision": round(precision, 3),
        "recall": round(recall, 3),
        "false_positive_rate": round(fp / max(n_humans * n_trials, 1), 4),
        "note": "synthetic single-swarm demo; use run_scenario_matrix for broader evaluation",
    }


# --------------------------------------------------------------------------- #
# Scenario matrix
# --------------------------------------------------------------------------- #
BENIGN_SCENARIOS = ("independent", "correlated", "synchronised", "drift")
ATTACK_SCENARIOS = ("single_swarm", "multiple_swarms", "persistent_weak", "strong_swarm")


def _eval_one_window(
    detector, X: np.ndarray, y: np.ndarray
) -> dict[str, Any]:
    t0 = time.perf_counter()
    res = detector.analyze_traffic(X)
    runtime_ms = (time.perf_counter() - t0) * 1000.0
    flagged = set(res.get("suspect_indices", []))
    truth = set(np.where(y == 1)[0].tolist())
    tp = len(flagged & truth)
    fp = len(flagged - truth)
    fn = len(truth - flagged)
    tn = len(set(range(len(y))) - flagged - truth)
    detected = bool(res.get("attack_detected", False))
    return {
        "detected": detected,
        "alert_level": res.get("alert_level"),
        "lambda_max": res.get("lambda_max"),
        "threshold": res.get("mp_threshold"),
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "tn": tn,
        "runtime_ms": runtime_ms,
    }


def _eval_rolling(
    roller, X_stream: np.ndarray, attack_start: int, attack_end: int
) -> dict[str, Any]:
    """Stream sessions one-by-one through a RollingSpectralMonitor.

    Returns detection delay (sessions from attack_start to first alarm),
    number of alarms, and false alarms before the attack window.
    """
    alarms_during = 0
    first_alarm_at: int | None = None
    false_alarms_before = 0
    for i, feats in enumerate(X_stream):
        a = roller.add_session(feats)
        if a is not None:
            if i < attack_start:
                false_alarms_before += 1
            elif attack_start <= i < attack_end:
                alarms_during += 1
                if first_alarm_at is None:
                    first_alarm_at = i
            # alarms after the attack window are also counted as "during-ish"
            # but for delay we only care about the first one inside.
    delay = (first_alarm_at - attack_start) if first_alarm_at is not None else None
    return {
        "alarms_during": alarms_during,
        "false_alarms_before": false_alarms_before,
        "detection_delay_sessions": delay,
    }


def run_scenario_matrix(
    detectors: dict[str, Any],
    *,
    n_seeds: int = 3,
    n_humans: int = 400,
    n_bots: int = 100,
    d: int = 8,
    calibration_seed: int = 1000,
    calibration_sessions: int = 50000,
    rolling_window: int = 500,
    rolling_check_every: int = 25,
    rolling_stream_len: int = 3000,
    rolling_attack_start: int = 1500,
    rolling_attack_end: int = 2500,
    base_seed: int = 0,
) -> dict[str, Any]:
    """Run the full scenario matrix across multiple seeds.

    ``detectors`` maps a name (e.g. ``"spectral"``, ``"mean_shift"``,
    ``"distance"``) to a freshly-constructed detector. Each detector is
    fitted on the same calibration data (separate seed) and then evaluated
    on every benign and attack scenario, for ``n_seeds`` evaluation seeds.

    Returns a nested dict: ``results[detector_name][scenario_name]`` is a
    list of per-seed result dicts. Use :func:`summarize_matrix` to print.
    """
    calib_rng = np.random.default_rng(calibration_seed)
    X_calib = calib_rng.normal(0, 1, size=(calibration_sessions, d))
    # Lambda_max history from benign windows for empirical-edge calibration.
    lambda_history: list[float] = []
    for _ in range(200):
        sample = calib_rng.normal(0, 1, size=(n_humans, d))
        res = detectors["spectral"].analyze_traffic(sample)
        if res["lambda_max"] is not None:
            lambda_history.append(res["lambda_max"])

    for name, det in detectors.items():
        det.fit_baseline(X_calib)
    # Calibrate the spectral detector's empirical edge on benign history.
    if hasattr(detectors["spectral"], "calibrate_empirical_edge") and lambda_history:
        detectors["spectral"].calibrate_empirical_edge(lambda_history)

    results: dict[str, dict[str, list[dict[str, Any]]]] = {}
    for det_name, det in detectors.items():
        results[det_name] = {}
        # Benign scenarios -- expect attack_detected == False.
        for scen in BENIGN_SCENARIOS:
            seeds_run: list[dict[str, Any]] = []
            for s in range(n_seeds):
                rng = np.random.default_rng(base_seed + s * 17 + hash(scen) % 1000)
                X, y = make_benign_scenario(scen, n_humans, d, rng)
                ev = _eval_one_window(det, X, y)
                ev["scenario"] = scen
                ev["seed"] = s
                ev["kind"] = "benign"
                seeds_run.append(ev)
            results[det_name][scen] = seeds_run

        # Attack scenarios -- measure detection + suspect precision/recall.
        for scen in ATTACK_SCENARIOS:
            seeds_run = []
            for s in range(n_seeds):
                rng = np.random.default_rng(
                    base_seed + s * 31 + hash(scen) % 1000
                )
                X, y = make_attack_scenario(scen, n_humans, n_bots, d, rng)
                ev = _eval_one_window(det, X, y)
                ev["scenario"] = scen
                ev["seed"] = s
                ev["kind"] = "attack"
                seeds_run.append(ev)
            results[det_name][scen] = seeds_run

    # Rolling-evaluation only for the spectral detector (baselines have no
    # rolling mode of the same shape). Uses the persistent-weak scenario to
    # exercise the CUSUM accumulator.
    rolling_results: list[dict[str, Any]] = []
    spectral = detectors["spectral"]
    from engines.spectral import RollingSpectralMonitor  # local import; avoid cycle

    for s in range(n_seeds):
        rng = np.random.default_rng(base_seed + s * 41)
        roller = RollingSpectralMonitor(
            spectral,
            window=rolling_window,
            check_every=rolling_check_every,
            drift=0.1,
            alarm_h=0.5,
        )
        weak_template = rng.normal(0, 1, size=d) * 0.83
        X_stream = np.empty((rolling_stream_len, d))
        for i in range(rolling_stream_len):
            if rolling_attack_start <= i < rolling_attack_end and rng.random() < 0.10:
                X_stream[i] = weak_template + rng.normal(0, 0.25, size=d)
            else:
                X_stream[i] = rng.normal(0, 1, size=d)
        ev = _eval_rolling(
            roller, X_stream, rolling_attack_start, rolling_attack_end
        )
        ev["seed"] = s
        rolling_results.append(ev)

    return {
        "detectors": list(detectors.keys()),
        "n_seeds": n_seeds,
        "config": {
            "n_humans": n_humans,
            "n_bots": n_bots,
            "d": d,
            "calibration_seed": calibration_seed,
            "calibration_sessions": calibration_sessions,
            "rolling_window": rolling_window,
            "rolling_check_every": rolling_check_every,
            "rolling_stream_len": rolling_stream_len,
            "rolling_attack_window": [rolling_attack_start, rolling_attack_end],
        },
        "results": results,
        "rolling_spectral": rolling_results,
    }


# --------------------------------------------------------------------------- #
# Pretty-printer
# --------------------------------------------------------------------------- #
def _agg(rows: list[dict[str, Any]], key: str) -> tuple[float, float, float]:
    vals = [r.get(key) for r in rows if r.get(key) is not None]
    if not vals:
        return (float("nan"), float("nan"), float("nan"))
    arr = np.asarray(vals, dtype=float)
    return (float(arr.mean()), float(arr.std()), float(arr.max()))


def summarize_matrix(mat: dict[str, Any]) -> str:
    """Render a scenario-matrix result as a printable string table."""
    lines: list[str] = []
    cfg = mat["config"]
    lines.append(
        f"Scenario matrix -- seeds={mat['n_seeds']} "
        f"d={cfg['d']} humans={cfg['n_humans']} bots={cfg['n_bots']} "
        f"calib_seed={cfg['calibration_seed']}"
    )
    lines.append("")

    header = (
        f"{'detector':<10} {'scenario':<18} {'kind':<7} "
        f"{'det%':>6} {'prec':>6} {'rec':>6} {'fpr':>7} "
        f"{'rt_ms':>7}"
    )
    lines.append(header)
    lines.append("-" * len(header))

    for det_name in mat["detectors"]:
        for scen, rows in mat["results"][det_name].items():
            kind = rows[0]["kind"]
            det_rate = np.mean([r["detected"] for r in rows])
            tp = sum(r["tp"] for r in rows)
            fp = sum(r["fp"] for r in rows)
            fn = sum(r["fn"] for r in rows)
            tn = sum(r["tn"] for r in rows)
            prec = tp / max(tp + fp, 1)
            rec = tp / max(tp + fn, 1)
            fpr = fp / max(fp + tn, 1)
            rt_mean, _, _ = _agg(rows, "runtime_ms")
            lines.append(
                f"{det_name:<10} {scen:<18} {kind:<7} "
                f"{det_rate*100:>5.1f}% {prec:>6.3f} {rec:>6.3f} "
                f"{fpr:>7.4f} {rt_mean:>7.2f}"
            )
        lines.append("")

    # Rolling summary.
    if mat.get("rolling_spectral"):
        lines.append("Rolling CUSUM (persistent_weak, streamed):")
        lines.append(
            f"  {'seed':<6} {'alarms_during':>14} "
            f"{'false_before':>13} {'delay':>8}"
        )
        for r in mat["rolling_spectral"]:
            delay = r["detection_delay_sessions"]
            delay_s = "-" if delay is None else str(delay)
            lines.append(
                f"  {r['seed']:<6} {r['alarms_during']:>14} "
                f"{r['false_alarms_before']:>13} {delay_s:>8}"
            )
    return "\n".join(lines)
