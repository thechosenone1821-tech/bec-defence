"""Part 4 Phase 5 — the captured-traffic format, and what it refuses to do.

Phase 5 says "real traffic, not fixtures; thresholds either earn their values or
are replaced". This module is the part of that phase which can be built without
the traffic: a loader for captured sessions, and a calibration routine that only
publishes a threshold when it is justified by the data it was given.

**The rule that governs this file:** a calibration result is either
`CALIBRATED` (n is large enough and the classes are separable) or
`INSUFFICIENT_DATA` with the reason. There is no third state where a threshold
is quietly reused and called calibrated. A spec that cannot express "I do not
know yet" produces confident numbers that are wrong.

Capture format
--------------
One JSON object per line (JSONL). One line == one observation, already reduced
to the organ's feature space. That reduction is deliberate: raw packets and raw
cursor traces are huge, and every organ's inputs are already defined in its
corpus schema, so a capture file is the same shape with a label attached.

    {"organ": "COOKIE_FLUID_TURBULENCE", "label": "benign",
     "captured_at": "2026-11-23T10:00:00Z", "source": "prod-gw-01",
     "features": {"rho_cadence": 4.1, "v_cursor": 118.0, "l_nav": 402.0}}

`label` must be `attack` or `benign`. Benign is the default an operator can
collect immediately; attack labels require an incident to have been confirmed,
which is why real capture files are almost entirely benign at first and why
`calibrate` will refuse to pick a threshold from benign data alone.
"""

from __future__ import annotations

import json
import math
import os
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

VALID_LABELS = ("attack", "benign")
# Below this, a per-class quantile is not a measurement, it is a guess.
MIN_PER_CLASS = 30
# 5th/95th percentile targets for a "flag the tail" threshold.
DEFAULT_TARGET_FPR = 0.05
DEFAULT_TARGET_TPR = 0.95


class CaptureError(ValueError):
    """A capture file that cannot be trusted."""


def read_capture(path: str) -> List[Dict[str, Any]]:
    """Read a JSONL capture file, rejecting anything malformed.

    Strict on purpose: a capture file that silently skips bad lines produces a
    threshold from an unknown subset of the traffic, which is worse than no
    threshold.
    """
    if not os.path.exists(path):
        raise CaptureError(f"no capture file at {path}")
    rows: List[Dict[str, Any]] = []
    with open(path, encoding="utf-8") as f:
        for lineno, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise CaptureError(f"{path}:{lineno}: not JSON ({exc})") from exc
            for field in ("organ", "label", "features"):
                if field not in row:
                    raise CaptureError(f"{path}:{lineno}: missing {field!r}")
            if row["label"] not in VALID_LABELS:
                raise CaptureError(f"{path}:{lineno}: bad label {row['label']!r}")
            if not isinstance(row["features"], dict) or not row["features"]:
                raise CaptureError(f"{path}:{lineno}: features must be a non-empty object")
            for k, v in row["features"].items():
                if not isinstance(v, (int, float)) or isinstance(v, bool):
                    raise CaptureError(f"{path}:{lineno}: feature {k!r} is not numeric")
                if not math.isfinite(float(v)):
                    raise CaptureError(f"{path}:{lineno}: feature {k!r} is not finite")
            rows.append(row)
    if not rows:
        raise CaptureError(f"{path}: contains no observations")
    return rows


def summarize(rows: Sequence[Dict[str, Any]], organ: str) -> Dict[str, Any]:
    sel = [r for r in rows if r.get("organ") == organ]
    attacks = [r for r in sel if r["label"] == "attack"]
    benign = [r for r in sel if r["label"] == "benign"]
    sources = sorted({r.get("source") for r in sel if r.get("source")})
    return {
        "organ": organ,
        "n_total": len(sel),
        "n_attack": len(attacks),
        "n_benign": len(benign),
        "sources": sources,
    }


def _quantile(sorted_vals: List[float], q: float) -> float:
    """Linear-interpolated quantile; no numpy dependency in this module."""
    if not sorted_vals:
        raise ValueError("empty sample")
    if len(sorted_vals) == 1:
        return float(sorted_vals[0])
    pos = q * (len(sorted_vals) - 1)
    lo = int(math.floor(pos))
    hi = min(lo + 1, len(sorted_vals) - 1)
    frac = pos - lo
    return float(sorted_vals[lo] * (1 - frac) + sorted_vals[hi] * frac)


def calibrate(
    rows: Sequence[Dict[str, Any]],
    organ: str,
    feature: str,
    *,
    direction: str = "high",
    target_fpr: float = DEFAULT_TARGET_FPR,
    target_tpr: float = DEFAULT_TARGET_TPR,
    min_per_class: int = MIN_PER_CLASS,
) -> Dict[str, Any]:
    """Propose a threshold for ``feature`` from captured observations.

    ``direction="high"`` means the organ flags when ``feature > threshold``
    (a rate such as Re_beh); ``"low"`` means ``feature < threshold`` (a
    connectivity such as lambda2).

    Returns ``status="CALIBRATED"`` only when both classes have at least
    ``min_per_class`` observations and a threshold exists that meets both
    targets. Otherwise ``status="INSUFFICIENT_DATA"`` with the arithmetic that
    made it insufficient — never a silently reused default.
    """
    if direction not in ("high", "low"):
        raise ValueError("direction must be 'high' or 'low'")
    sel = [r for r in rows if r.get("organ") == organ]
    attacks = [float(r["features"][feature]) for r in sel
               if r["label"] == "attack" and feature in r["features"]]
    benign = [float(r["features"][feature]) for r in sel
              if r["label"] == "benign" and feature in r["features"]]

    out: Dict[str, Any] = {
        "organ": organ,
        "feature": feature,
        "direction": direction,
        "n_attack": len(attacks),
        "n_benign": len(benign),
        "target_fpr": target_fpr,
        "target_tpr": target_tpr,
        "min_per_class": min_per_class,
    }
    if len(attacks) < min_per_class or len(benign) < min_per_class:
        out.update({
            "status": "INSUFFICIENT_DATA",
            "reason": (f"need >= {min_per_class} per class; have {len(attacks)} attack "
                       f"and {len(benign)} benign"),
            "default_in_use": None,
        })
        return out

    attacks.sort()
    benign.sort()
    # The threshold that would admit `target_tpr` of attacks, and the one that
    # would admit `target_fpr` of benign. If they do not separate, say so.
    if direction == "high":
        t_tpr = _quantile(attacks, 1 - target_tpr)
        t_fpr = _quantile(benign, 1 - target_fpr)
        separable = t_tpr > t_fpr
    else:
        t_tpr = _quantile(attacks, target_tpr)
        t_fpr = _quantile(benign, target_fpr)
        separable = t_tpr < t_fpr

    out.update({
        "threshold_for_tpr": round(t_tpr, 6),
        "threshold_for_fpr": round(t_fpr, 6),
        "benign_p50": round(_quantile(benign, 0.5), 6),
        "benign_p95": round(_quantile(benign, 0.95), 6),
        "attack_p05": round(_quantile(attacks, 0.05), 6),
        "attack_p50": round(_quantile(attacks, 0.5), 6),
    })
    if not separable:
        out.update({
            "status": "NOT_SEPARABLE",
            "reason": (f"no threshold meets TPR {target_tpr:.2f} and FPR {target_fpr:.2f} "
                       f"simultaneously on this capture"),
            "default_in_use": None,
        })
        return out

    chosen = round((t_tpr + t_fpr) / 2.0, 6)
    out.update({
        "status": "CALIBRATED",
        "threshold": chosen,
        "reason": (f"{len(attacks)} attack / {len(benign)} benign observations separate at "
                   f"{chosen} (attack p50 {out['attack_p50']}, benign p95 {out['benign_p95']})"),
        "default_in_use": None,
    })
    return out


def load_and_calibrate(path: str, organ: str, feature: str, **kwargs: Any) -> Dict[str, Any]:
    return calibrate(read_capture(path), organ, feature, **kwargs)


def write_capture(path: str, rows: Iterable[Dict[str, Any]]) -> int:
    """Write observations as JSONL. Used by the operator tooling and the tests."""
    n = 0
    with open(path, "w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, sort_keys=True) + "\n")
            n += 1
    return n
