"""Part 4 Phase 6 — load, fatigue and drift, measured rather than asserted.

Three questions, each with a number attached:

1. **Load.** What does the organ fleet do under sustained event volume, and is
   there an input size at which a detector becomes a liability? (§6.1)

2. **Fatigue.** An operator does not read alerts; they read *some* alerts. The
   alert-fatigue budget is the number of alerts per shift above which a human
   stops investigating. This module measures what each organ would produce over
   a shift of benign activity, which is the number that decides whether the
   fleet is livable. (§6.2)

3. **Drift and garbage.** Feed an organ nothing but junk for an hour of
   simulated time and see whether it degrades, throws, or silently goes quiet.
   Silence must not look like safety. (§6.3)

Nothing here sleeps in real time. Every window is simulated by driving the
clock/inputs, because a one-hour soak that takes one hour does not get run.
"""

from __future__ import annotations

import os
import statistics
import sys
import time
from typing import Any, Callable, Dict, List, Optional

from pathlib import Path as _Path
_REPO = _Path(__file__).resolve().parents[3]
HERE = os.path.dirname(os.path.abspath(__file__))
CODE = str(_REPO / "raksha-code")
if CODE not in sys.path:
    sys.path.insert(0, CODE)

import numpy as np


# --------------------------------------------------------------------------- #
# 1. Load — input-size scaling
# --------------------------------------------------------------------------- #
def scaling_probe(sizes: List[int] = (100, 400, 800, 1600, 3200)) -> List[Dict[str, Any]]:
    """Time Organ 3 against documents of increasing token count.

    Memory is measured with tracemalloc so the quadratic term is attributable to
    the organ rather than to the interpreter.
    """
    import tracemalloc
    from sentinel.shields.ring2_ai_defense import BraggFFTFirewall

    base = "the server read the log file and wrote a report about the incident "
    rows = []
    for n in sizes:
        text = (base * (n // 13 + 1))[: n * 8]
        tokens = len(text.split())
        tracemalloc.start()
        t0 = time.perf_counter()
        organ = BraggFFTFirewall()
        organ.screen(text)
        organ.drain_events()
        elapsed = time.perf_counter() - t0
        peak_mb = tracemalloc.get_traced_memory()[1] / 1e6
        tracemalloc.stop()
        rows.append({"tokens": tokens, "seconds": round(elapsed, 4),
                     "peak_mb": round(peak_mb, 2)})
    return rows


def fit_growth(rows: List[Dict[str, Any]], key: str) -> float:
    """Log-log slope: 1.0 is linear, 2.0 is quadratic."""
    xs = [np.log(r["tokens"]) for r in rows]
    ys = [np.log(max(r[key], 1e-9)) for r in rows]
    return float(np.polyfit(xs, ys, 1)[0])


# --------------------------------------------------------------------------- #
# 2. Fatigue — alerts per shift from benign activity
# --------------------------------------------------------------------------- #
def fatigue_benign_corpus() -> List[Any]:
    """Benign inputs for each organ, drawn from the Phase 4 benign cases.

    Deliberately includes the adversarial-benign families: those are the ones
    that fire, and a fatigue budget computed from easy cases is fiction.
    """
    from corpora.harness import load_corpus
    from corpora.run_corpus import compile_payload

    out = []
    for name in ("organ1_spectral_condensation.json", "organ2_cookie_turbulence.json",
                 "organ3_bragg_injection.json", "organ4_lyapunov_trajectory.json",
                 "organ5_landauer_thermal.json"):
        corpus = load_corpus(name)
        for case in corpus["cases"]:
            if case["label"] == "benign" and case.get("role", "scored") == "scored":
                out.append((corpus["organ"], case["id"], compile_payload(case), case))
    return out


def fatigue_run(cycles: int = 20) -> Dict[str, Any]:
    """Drive every benign input ``cycles`` times and count emissions per organ.

    A shift is modelled as ``cycles`` independent benign observations per case.
    The per-shift alert count is then ``emissions / cycles`` so the number does
    not depend on the arbitrary choice of ``cycles``.
    """
    from corpora.run_corpus import ADAPTERS

    benign = fatigue_benign_corpus()
    fired: Dict[str, int] = {}
    for organ_name, case_id, payload, case in benign:
        # run_organ8 is a refusal path and has no benign emission by design;
        # the registry below only contains detectors that can raise.
        if organ_name not in ADAPTERS:
            continue
        for _ in range(cycles):
            if ADAPTERS[organ_name](case, payload):
                fired[organ_name] = fired.get(organ_name, 0) + 1

    per_shift = {k: v / cycles for k, v in fired.items()}
    # What this number IS: the fraction of *benign corpus families* that fire,
    # under equal weighting. The corpus holds one case per family, so there is
    # no traffic distribution to weight by, and a real shift has far more
    # observations than families. Labelling it "alerts per shift" without this
    # caveat would be the exact kind of unearned precision this part exists to
    # remove.
    per_organ_inputs = {}
    for organ_name, _, _, _ in benign:
        per_organ_inputs[organ_name] = per_organ_inputs.get(organ_name, 0) + 1
    rates = {k: v / per_organ_inputs[k] for k, v in per_shift.items()}
    return {
        "cycles": cycles,
        "n_benign_inputs": len(benign),
        "benign_inputs_per_organ": per_organ_inputs,
        "alerts_per_shift": per_shift,
        "benign_family_fire_rate": rates,
        "total_alerts_per_shift": round(sum(per_shift.values()), 2),
        "interpretation": (
            "alerts_per_shift counts distinct benign *families* that fire, once "
            "per cycle, because the corpus holds one case per family. It is an "
            "equal-weighted upper bound on per-family firing, not a rate for real "
            "traffic, whose family mix is unknown."
        ),
    }


# The threshold above which an analyst stops reading. Chosen from the alert
# literature's usual figure and stated here as an assumption, not a measurement.
FATIGUE_BUDGET_PER_SHIFT = 12


# --------------------------------------------------------------------------- #
# 3. Drift and garbage
# --------------------------------------------------------------------------- #
def garbage_soak(organ_name: str, rounds: int = 600) -> Dict[str, Any]:
    """Feed one organ junk for ``rounds`` observations and watch for degradation.

    Junk means structurally valid but semantically empty input: empty strings,
    single tokens, zeros, nans-as-strings, huge magnitudes. The organ must never
    raise, must never emit a fabricated 'unknown' event, and must not stop
    reporting — a detector that goes quiet under garbage is indistinguishable
    from one that is satisfied.
    """
    from sentinel.shields.ring1_perimeter_identity import BECSpectralFilter, CookieFluidTurbulence
    from sentinel.shields.ring2_ai_defense import BraggFFTFirewall, HessianLyapunovGuard
    from sentinel.shields.ring3_endpoint_silicon import LandauerThermalAudit
    from sentinel.shields.ring4_network_healing import MutsEbpfRepair

    raised: List[str] = []
    emitted = 0
    processed = 0

    if organ_name == "COOKIE_FLUID_TURBULENCE":
        organ = CookieFluidTurbulence()
        organ.calibrate_baseline([{"rho_cadence": 4.0, "v_cursor": 120.0, "l_nav": 400.0}] * 8)
        generator = _garbage_triples
        call = lambda v: organ.observe(*v)
    elif organ_name == "BRAGG_FFT_FIREWALL":
        organ = BraggFFTFirewall()
        generator = _garbage_texts
        call = lambda v: organ.screen(v)
    elif organ_name == "HESSIAN_LYAPUNOV_GUARD":
        organ = HessianLyapunovGuard()
        generator = _garbage_vectors
        call = lambda v: organ.step(v)
    elif organ_name == "LANDAUER_THERMAL_AUDITOR":
        organ = LandauerThermalAudit()
        organ.calibrate([{"ipc": 2.0, "temp_c": 50.0, "power_w": 40.0}] * 12)
        generator = _garbage_thermal
        call = lambda v: organ.audit(*v)
    elif organ_name == "MUTS_EBPF_REPAIR":
        organ = MutsEbpfRepair()
        organ.register_invariant("svc_web", "bounds_check_v1")
        generator = _garbage_services
        call = lambda v: organ.report_mismatch(v)
    elif organ_name == "BEC_SPECTRAL_PROJECTOR":
        organ = BECSpectralFilter()
        generator = _garbage_matrices
        call = lambda v: organ.analyze(v)
    else:
        raise ValueError(f"no garbage generator for {organ_name}")

    for i in range(rounds):
        value = generator(i)
        try:
            call(value)
            processed += 1
        except Exception as exc:  # noqa: BLE001 - the point is to record, not handle
            raised.append(f"{type(exc).__name__}: {exc}")
        emitted += len(organ.drain_events())

    return {
        "organ": organ_name,
        "rounds": rounds,
        "processed": processed,
        "raised": len(raised),
        "first_raise": raised[0] if raised else None,
        "emitted": emitted,
        "went_silent": emitted == 0,
    }


def _garbage_triples(i: int):
    return [(0.0, 0.0, 0.0), (1e300, 1e300, 1e300), (-5.0, -5.0, -5.0),
            (1e-300, 1e-300, 1e-300)][i % 4]


def _garbage_texts(i: int) -> str:
    return ["", "a", " ", "\x00\x01\x02", "x" * 50000,
            "SELECT * FROM users; --", "🙂🙂🙂🙂", "1234567890" * 100][i % 8]


def _garbage_vectors(i: int):
    return [np.zeros(4), np.full(4, 1e300), np.array([1e-300] * 4),
            np.array([np.nan, 1.0, 2.0, 3.0]), np.array([np.inf, 0, 0, 0])][i % 5]


def _garbage_thermal(i: int):
    return [(0.0, 0.0, 0.0), (1e9, 1e9, 1e9), (-100.0, -1.0, -40.0),
            (40.0, 2.0, 50.0)][i % 4]


def _garbage_services(i: int) -> str:
    return ["", "svc_web", "svc_" + "x" * 10000, "../../etc/passwd",
            "svc_web\x00admin"][i % 5]


def _garbage_matrices(i: int):
    return [np.zeros((4, 5)), np.full((6, 5), 1e300), np.ones((5, 5)) * 1e-300,
            np.array([[np.nan, 1, 2, 3, 4]] * 4)][i % 4]


GARBAGE_ORGANS = ["BEC_SPECTRAL_PROJECTOR", "COOKIE_FLUID_TURBULENCE",
                  "BRAGG_FFT_FIREWALL", "HESSIAN_LYAPUNOV_GUARD",
                  "LANDAUER_THERMAL_AUDITOR", "MUTS_EBPF_REPAIR"]


# --------------------------------------------------------------------------- #
# Report
# --------------------------------------------------------------------------- #
def main() -> int:
    print("# Phase 6 — load, fatigue and drift\n")
    print("## 1. Input-size scaling (Organ 3)\n")
    rows = scaling_probe()
    print("| tokens | seconds | peak MB |", "|---|---|---|")
    for r in rows:
        print(f"| {r['tokens']} | {r['seconds']:.3f} | {r['peak_mb']:.1f} |")
    print(f"\ntime growth exponent: {fit_growth(rows, 'seconds'):.2f}")
    print(f"memory growth exponent: {fit_growth(rows, 'peak_mb'):.2f}\n")

    print("## 2. Alert fatigue — benign activity per shift\n")
    fat = fatigue_run()
    print(f"benign inputs driven: {fat['n_benign_inputs']} x {fat['cycles']} cycles")
    for organ, n in sorted(fat["alerts_per_shift"].items(), key=lambda kv: -kv[1]):
        print(f"  {organ:26} {n:6.1f} alerts / shift")
    print(f"\ntotal across fleet: {fat['total_alerts_per_shift']:.1f} "
          f"(budget {FATIGUE_BUDGET_PER_SHIFT})")
    for organ, r in sorted(fat["benign_family_fire_rate"].items(), key=lambda kv: -kv[1]):
        print(f"  {organ:26} fires on {r:.0%} of its benign families")
    print(f"\n{fat['interpretation']}\n")

    print("## 3. Garbage soak\n")
    print("| organ | processed | raised | emitted | silent |", "|---|---|---|---|---|")
    for organ in GARBAGE_ORGANS:
        r = garbage_soak(organ)
        print(f"| `{r['organ']}` | {r['processed']}/{r['rounds']} | {r['raised']} "
              f"| {r['emitted']} | {r['went_silent']} |")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
