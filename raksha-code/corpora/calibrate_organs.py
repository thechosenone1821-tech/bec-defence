"""Part 4 Phase 5 — calibration status for every organ threshold.

    python3 corpora/calibrate_organs.py                    # current status
    python3 corpora/calibrate_organs.py corpora/captures/*.jsonl

With no capture argument, every organ reports `INSUFFICIENT_DATA` and names the
default that is actually in force. With capture files, each organ's declared
feature is calibrated from the pooled observations; anything that cannot be
separated reports `NOT_SEPARABLE` and the default stays in force.

**What this tool will not do:** substitute an author-chosen value for a
calibrated one and print `CALIBRATED`. The registry records where each default
came from — `unvalidated` means nobody has ever checked it against traffic —
and `apply` is deliberately not implemented. Changing a live threshold is a
human decision with a paper trail, not something a script does to a security
control at 3 a.m.
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import sys
from typing import Any, Dict, List

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

from corpora.capture import calibrate, read_capture, summarize


# --------------------------------------------------------------------------- #
# The registry. One row per threshold that a Phase 4 result actually exercised.
# --------------------------------------------------------------------------- #
REGISTRY: List[Dict[str, Any]] = [
    {
        "organ": "COOKIE_FLUID_TURBULENCE",
        "feature": "re_beh",
        "direction": "high",
        "symbol": "re_crit",
        "default": 2300.0,
        "origin": "unvalidated",
        "note": ("Chosen to sit above a brisk human in the Phase 4 corpus. The corpus "
                 "showed a fast human scores 6187 and a throttled script scores 619, "
                 "so the default separates activity from inactivity, not human from "
                 "machine."),
    },
    {
        "organ": "BEC_SPECTRAL_PROJECTOR",
        "feature": "condensation_ratio",
        "direction": "high",
        "symbol": "rank1_threshold",
        "default": 0.72,
        "origin": "unvalidated",
        "note": ("Phase 4 §4.3 showed the statistic is invariant to the bot fraction "
                 "when both populations share a law, and that a benign homogeneous "
                 "fleet reaches 1.000. No value of this threshold fixes that."),
    },
    {
        "organ": "BRAGG_FFT_FIREWALL",
        "feature": "bragg_peak_ratio",
        "direction": "high",
        "symbol": "bragg_peak_threshold",
        "default": 0.32,
        "origin": "unvalidated",
        "note": ("Phase 4 §4.4 showed this knob is inert: both real injections scored "
                 "below 0.32 and were blocked by the Fiedler rule instead."),
    },
    {
        "organ": "BRAGG_FFT_FIREWALL",
        "feature": "fiedler_lambda2",
        "direction": "low",
        "symbol": "fiedler_threshold",
        "default": 0.05,
        "origin": "unvalidated",
        "note": ("Phase 5 §5.4: this rule blocks 28/28 real project documents. It "
                 "measures connectivity of a kNN token graph, and one rare token "
                 "disconnects it."),
    },
    {
        "organ": "HESSIAN_LYAPUNOV_GUARD",
        "feature": "kappa",
        "direction": "high",
        "symbol": "cliff_threshold",
        "default": 2.5,
        "origin": "unvalidated",
        "note": ("Phase 4 corpus has 2 attack trajectories. Real hidden states were "
                 "never available, so this threshold has no evidence base at all."),
    },
    {
        "organ": "LANDAUER_THERMAL_AUDITOR",
        "feature": "unaccounted_w",
        "direction": "high",
        "symbol": "residual_threshold_w",
        "default": 8.0,
        "origin": "unvalidated",
        "note": ("Fitted against twelve identical synthetic points, so the model has "
                 "no IPC sensitivity; the 8 W residual is a guess against a guess."),
    },
    {
        "organ": "HASHIMOTO_PERCOLATION",
        "feature": "rho_before",
        "direction": "high",
        "symbol": "target_radius",
        "default": 1.0,
        "origin": "documented-deviation",
        "note": ("Not a tuned threshold: rho >= 1 on any cyclic graph is a stated "
                 "deviation from the classical result, recorded in the organ "
                 "docstring. Calibration does not apply."),
    },
]


def _load_all(paths: List[str]) -> Optional[List[Dict[str, Any]]]:
    rows: List[Dict[str, Any]] = []
    for path in paths:
        rows.extend(read_capture(path))
    return rows or None


def status(paths: List[str]) -> List[Dict[str, Any]]:
    rows = _load_all(paths) if paths else None
    out = []
    for entry in REGISTRY:
        if rows is None:
            out.append({**entry, "status": "INSUFFICIENT_DATA",
                        "reason": "no capture file supplied",
                        "default_in_use": entry["default"]})
            continue
        rep = calibrate(rows, entry["organ"], entry["feature"],
                        direction=entry["direction"])
        rep.update({k: entry[k] for k in ("symbol", "default", "origin", "note")})
        if rep["status"] != "CALIBRATED":
            rep["default_in_use"] = entry["default"]
        out.append(rep)
    return out


def render(reports: List[Dict[str, Any]]) -> str:
    lines = ["| Organ | Threshold | Default | Status |", "|---|---|---|---|"]
    for r in reports:
        lines.append(f"| `{r['organ']}` | `{r['symbol']}` = {r['default']} "
                     f"| {r['origin']} | **{r['status']}** — {r.get('reason', '')} |")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("captures", nargs="*", help="JSONL capture files")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    paths: List[str] = []
    for pattern in args.captures:
        matched = glob.glob(pattern)
        paths.extend(matched if matched else [pattern])

    reports = status(paths)
    if args.json:
        print(json.dumps(reports, indent=2))
    else:
        print("# Threshold calibration status — measured this run\n")
        print(render(reports))
        calibrated = sum(1 for r in reports if r["status"] == "CALIBRATED")
        print(f"\n**{calibrated} of {len(reports)} thresholds calibrated against captured "
              f"traffic.** The rest are running on values nobody has validated.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
