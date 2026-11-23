"""MAYA / VoiceGuard — measurement harness (Phase 5).

    python evals/run_maya.py            # full table
    python evals/run_maya.py --quick    # smaller corpus, for a pre-commit check

Every number printed here is measured on a **SYNTHETIC** corpus and is labelled
as such in the output. The table is the only source of figures that may appear
in ``raksha/EVALS.md``; if a number is not in this output, it does not go in a
slide.

The conditions section is the important one. A single "accuracy" number hides
the fact that narrowband telephony, packet loss and codec transcoding each move
real performance. Reporting the degradation curve is the honest alternative to
reporting a headline.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from typing import Any, Dict, List

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from citizen.voiceguard import corpus, features as F, model as M
from citizen.voiceguard import score_voice
from citizen.voiceguard import train as T


# --------------------------------------------------------------------------- #
# Signal degradations that approximate real call conditions
# --------------------------------------------------------------------------- #
def degrade_narrowband(x: np.ndarray, sr: int = 16000, cutoff_hz: float = 3400.0) -> np.ndarray:
    """Telephone band-limit (8 kHz sampling, ~300-3400 Hz passband).

    Implemented as a crude FFT mask: honest, deterministic, and obviously an
    approximation. It removes the high band, which is exactly where most
    anti-spoof evidence lives — which is why the number moves.
    """
    if x.size == 0:
        return x
    n = 1 << int(np.ceil(np.log2(x.size)))
    spec = np.fft.rfft(x, n=n)
    freqs = np.fft.rfftfreq(n, 1.0 / sr)
    mask = (freqs >= 300.0) & (freqs <= cutoff_hz)
    out = np.fft.irfft(spec * mask, n=n)[: x.size]
    return out.astype(np.float32)


def degrade_mulaw(x: np.ndarray) -> np.ndarray:
    """μ-law companding at 8 bits — the G.711 codec a phone call uses."""
    mu = 255.0
    clipped = np.clip(x, -1.0, 1.0)
    comp = np.sign(clipped) * np.log1p(mu * np.abs(clipped)) / np.log1p(mu)
    quant = np.round(comp * 127.0) / 127.0        # 8-bit (sign bit + 7)
    expanded = np.sign(quant) * (np.expm1(np.abs(quant) * np.log1p(mu)) / mu)
    return expanded.astype(np.float32)


def degrade_packet_loss(x: np.ndarray, seed: int = 0, p: float = 0.02,
                        sr: int = 16000) -> np.ndarray:
    """Drop 20 ms packets at rate ``p`` (replaced with silence)."""
    rng = np.random.default_rng(seed)
    pkt = int(0.020 * sr)
    out = x.copy()
    n_pkts = x.size // pkt
    for i in range(n_pkts):
        if rng.random() < p:
            out[i * pkt:(i + 1) * pkt] = 0.0
    return out


def degrade_noise(x: np.ndarray, seed: int = 0, sigma: float = 0.02) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return (x + rng.normal(0.0, sigma, x.size)).astype(np.float32)


def degrade_gain(x: np.ndarray, factor: float = 0.3) -> np.ndarray:
    return (x * factor).astype(np.float32)


CONDITIONS = {
    "clean": lambda c, i: c,
    "narrowband (telephony)": lambda c, i: degrade_narrowband(c),
    "mu-law 8-bit": lambda c, i: degrade_mulaw(c),
    "packet loss 2%": lambda c, i: degrade_packet_loss(c, seed=i),
    "noise 0.02": lambda c, i: degrade_noise(c, seed=i),
    "gain x0.3": lambda c, i: degrade_gain(c),
}


# --------------------------------------------------------------------------- #
def _file_digest(path: str) -> str:
    import hashlib
    try:
        with open(path, "rb") as fh:
            return hashlib.sha256(fh.read()).hexdigest()[:16]
    except OSError:
        return "unavailable"


def measure_conditions(model: M.MayaModel, clips: List[np.ndarray],
                       y: np.ndarray) -> Dict[str, Dict[str, Any]]:
    out: Dict[str, Dict[str, Any]] = {}
    for name, fn in CONDITIONS.items():
        perturbed = [fn(c, i) for i, c in enumerate(clips)]
        out[name] = M.evaluate(model, perturbed, y)
    return out


def measure_latency(clips: List[np.ndarray], n: int = 12) -> Dict[str, Any]:
    """Wall-clock per screening call on THIS machine — not a phone.

    Reported as p50/p95 with the machine caveat attached, because a laptop
    number has never been a phone number and pretending otherwise is how SLAs
    get invented.
    """
    sample = clips[:n]
    times: List[float] = []
    for c in sample:
        t0 = time.perf_counter()
        score_voice(c)
        times.append((time.perf_counter() - t0) * 1000.0)
    arr = np.asarray(times)
    return {"n": int(arr.size),
            "p50_ms": round(float(np.percentile(arr, 50)), 1),
            "p95_ms": round(float(np.percentile(arr, 95)), 1),
            "max_ms": round(float(arr.max()), 1),
            "note": "sandbox laptop wall-clock; NOT a phone measurement"}


def measure_verdict_distribution(clips: List[np.ndarray], y: np.ndarray) -> Dict[str, Any]:
    """How the citizen-facing verdicts actually land, per class."""
    counts = {"bona": {}, "spoof": {}}
    for c, label in zip(clips, y):
        key = "spoof" if label == 1 else "bona"
        v = score_voice(c)["verdict"]
        counts[key][v] = counts[key].get(v, 0) + 1
    return counts


def false_accusation_rate(clips: List[np.ndarray], y: np.ndarray) -> float:
    """The number that decides whether anyone keeps the app installed."""
    bona = [c for c, t in zip(clips, y) if t == 0]
    if not bona:
        return float("nan")
    flagged = sum(1 for c in bona if score_voice(c)["verdict"] == "LIKELY_SYNTHETIC")
    return round(flagged / len(bona), 4)


# --------------------------------------------------------------------------- #
def run(quick: bool = False) -> Dict[str, Any]:
    n_per_class = 20 if quick else 60
    training = T.run(seed=20260101, n_per_class=60, l2=1.0, save=False)
    model = M.get_model()
    if model is None:
        raise SystemExit("no model artefact found — run python -m citizen.voiceguard.train")

    data = corpus.build(seed=20260101, n_per_class=n_per_class)
    clips = data["test"]["clips"]
    y = data["test"]["labels"]

    return {
        "corpus": "SYNTHETIC (procedural) — real-world accuracy UNMEASURED",
        "model_id": model.model_id,
        # Computed from disk rather than from training, because this harness
        # loads the *shipped* artefact via M.get_model() and only retrains to
        # report metrics. The digest must describe the file the app loads.
        "file_sha256_16": _file_digest(M.MODEL_PATH_DEFAULT),
        "threshold": model.decision_threshold,
        "temperature": model.temperature,
        "n_test": int(y.size),
        "splits": {"train": training["train"], "val": training["val"],
                   "test": training["test"]},
        "conditions": measure_conditions(model, clips, y),
        "latency": measure_latency(clips),
        "verdicts": measure_verdict_distribution(clips, y),
        "false_accusation_rate": false_accusation_rate(clips, y),
    }


def _pct(v: Any) -> str:
    return "—" if v is None else f"{v * 100:.1f}%"


def _num(v: Any) -> str:
    return "—" if v is None else f"{v:.3f}"


def print_report(r: Dict[str, Any]) -> None:
    print("MAYA / VoiceGuard — measured evaluation")
    print(f"  model      : {r['model_id']} (file {r['file_sha256_16']})")
    print(f"  corpus     : {r['corpus']}")
    print(f"  threshold  : {r['threshold']}   temperature: {r['temperature']}")
    print(f"  test clips : {r['n_test']}")
    print()
    print("## Headline (held-out test split)")
    print("| split | n | EER | accuracy | precision | recall | FPR |")
    print("|---|---|---|---|---|---|---|")
    for name, m in r["splits"].items():
        print(f"| {name} | {m['n']} | {_num(m['eer'])} | {_pct(m['accuracy_at_threshold'])} "
              f"| {_pct(m['precision'])} | {_pct(m['recall'])} | {_pct(m['false_positive_rate'])} |")
    print()
    print("## Robustness by condition — the table that matters")
    print("| condition | n | EER | accuracy | recall | FPR |")
    print("|---|---|---|---|---|---|")
    for name, m in r["conditions"].items():
        print(f"| {name} | {m['n']} | {_num(m['eer'])} | {_pct(m['accuracy_at_threshold'])} "
              f"| {_pct(m['recall'])} | {_pct(m['false_positive_rate'])} |")
    print()
    print("## Citizen-facing verdict distribution")
    for key, counts in r["verdicts"].items():
        total = sum(counts.values()) or 1
        parts = ", ".join(f"{k} {v}/{total}" for k, v in sorted(counts.items()))
        print(f"  {key:5}: {parts}")
    print(f"  false accusation rate (bona-fide flagged LIKELY_SYNTHETIC): "
          f"{_pct(r['false_accusation_rate'])}")
    print()
    print("## Latency")
    lat = r["latency"]
    print(f"  p50 {lat['p50_ms']} ms · p95 {lat['p95_ms']} ms · max {lat['max_ms']} ms")
    print(f"  {lat['note']}")
    print()
    print("## What this table does NOT claim")
    for line in (
        "real-world detection accuracy (the corpus is procedural, not recorded)",
        "any modern neural voice clone (none is present in the corpus)",
        "Indian-language or accented speech (the generator has no phonetics)",
        "a production SLO (latency is one sandbox laptop)",
    ):
        print(f"  - {line}")


def main() -> None:
    ap = argparse.ArgumentParser(description="Measure the Maya voiceguard")
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--json", action="store_true", help="emit raw JSON")
    args = ap.parse_args()
    report = run(quick=args.quick)
    if args.json:
        print(json.dumps(report, indent=2, default=str))
    else:
        print_report(report)


if __name__ == "__main__":
    main()
