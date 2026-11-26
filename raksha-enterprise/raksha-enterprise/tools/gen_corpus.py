"""Deterministic fixture/corpus generator for the eval harness.

Generates the same frozen corpora the Part 6 evals were measured on
(seed 20261126) so numbers stay comparable across runs and machines.
Writes data/evals/corpora.json.
"""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

ORGANS = ["voiceguard", "docguard", "sessionguard", "fileguard",
          "netguard", "idguard", "quorumguard", "tier0guard"]
ATTACK_N = {"voiceguard": 60, "docguard": 50, "sessionguard": 40, "fileguard": 45,
            "netguard": 50, "idguard": 35, "quorumguard": 30, "tier0guard": 25}
CLEAN_N = {o: 150 for o in ORGANS}


def _g(rng: random.Random, mean: float, sd: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, rng.gauss(mean, sd)))


def _attack(organ: str, n: int, rng: random.Random) -> list[dict]:
    rows = []
    for _ in range(n):
        r: dict = {"label": "attack"}
        if organ == "voiceguard":
            r |= {"synth_score": _g(rng, 0.93, 0.05, 0.55, 0.99) if rng.random() > 0.12 else _g(rng, 0.66, 0.05, 0.55, 0.74),
                  "caller_reputation": _g(rng, 0.10, 0.08, 0.0, 0.6), "call_duration_s": rng.randint(120, 900)}
        elif organ == "docguard":
            r |= {"vendor_age_days": rng.randint(5, 40) if rng.random() > 0.15 else rng.randint(95, 400),
                  "bank_detail_changed": 1 if rng.random() > 0.08 else 0,
                  "amount_z": _g(rng, 4.0, 1.0, 1.0, 9.0), "pdf_metadata_mismatch": 1 if rng.random() > 0.25 else 0}
        elif organ == "sessionguard":
            r |= {"token_reuse_count": rng.randint(2, 6) if rng.random() > 0.1 else 1,
                  "geo_distance_km": rng.randint(500, 4000) if rng.random() > 0.1 else rng.randint(50, 200),
                  "ua_change": 1 if rng.random() > 0.3 else 0}
        elif organ == "fileguard":
            r |= {"encrypt_events_per_min": rng.randint(400, 1200) if rng.random() > 0.12 else rng.randint(80, 300),
                  "shadow_delete": 1 if rng.random() > 0.2 else 0, "entropy": _g(rng, 7.6, 0.4, 5.5, 8.0)}
        elif organ == "netguard":
            r |= {"egress_gb_24h": _g(rng, 2.6, 0.8, 0.8, 6.0), "dest_reputation": _g(rng, 0.12, 0.08, 0.0, 0.35),
                  "beacon_interval_jitter": _g(rng, 0.03, 0.02, 0.0, 0.09)}
        elif organ == "idguard":
            r |= {"privilege_requests_24h": rng.randint(15, 40) if rng.random() > 0.12 else rng.randint(5, 12),
                  "new_device": 1 if rng.random() > 0.1 else 0, "time_of_day_anomaly": 1 if rng.random() > 0.25 else 0}
        elif organ == "quorumguard":
            r |= {"decision_probe_rate": _g(rng, 0.62, 0.15, 0.2, 0.95) if rng.random() > 0.1 else _g(rng, 0.3, 0.05, 0.2, 0.38),
                  "ledger_gap_events": rng.randint(0, 2),
                  "signature_anomalies": rng.randint(1, 5) if rng.random() > 0.1 else 0}
        elif organ == "tier0guard":
            r |= {"crown_touch_events": rng.randint(3, 8) if rng.random() > 0.12 else rng.randint(1, 2),
                  "dependency_depth_traversed": rng.randint(1, 3)}
        rows.append(r)
    return rows


def _clean(organ: str, n: int, rng: random.Random) -> list[dict]:
    rows = []
    for _ in range(n):
        r: dict = {"label": "clean"}
        if organ == "voiceguard":
            r |= {"synth_score": _g(rng, 0.18, 0.09, 0.0, 0.78), "caller_reputation": _g(rng, 0.75, 0.15, 0.2, 1.0),
                  "call_duration_s": rng.randint(20, 2400)}
        elif organ == "docguard":
            r |= {"vendor_age_days": rng.randint(120, 3000), "bank_detail_changed": 1 if rng.random() > 0.9 else 0,
                  "amount_z": _g(rng, 0.8, 0.7, -1.0, 3.4), "pdf_metadata_mismatch": 1 if rng.random() > 0.92 else 0}
        elif organ == "sessionguard":
            r |= {"token_reuse_count": rng.randint(0, 1), "geo_distance_km": rng.randint(0, 120),
                  "ua_change": 1 if rng.random() > 0.85 else 0}
        elif organ == "fileguard":
            r |= {"encrypt_events_per_min": rng.randint(5, 260), "shadow_delete": 1 if rng.random() > 0.95 else 0,
                  "entropy": _g(rng, 4.5, 0.8, 2.0, 7.1)}
        elif organ == "netguard":
            r |= {"egress_gb_24h": _g(rng, 0.5, 0.3, 0.05, 2.2), "dest_reputation": _g(rng, 0.7, 0.15, 0.3, 1.0),
                  "beacon_interval_jitter": _g(rng, 0.35, 0.12, 0.05, 0.6)}
        elif organ == "idguard":
            r |= {"privilege_requests_24h": rng.randint(0, 10), "new_device": 1 if rng.random() > 0.9 else 0,
                  "time_of_day_anomaly": 1 if rng.random() > 0.8 else 0}
        elif organ == "quorumguard":
            r |= {"decision_probe_rate": _g(rng, 0.08, 0.05, 0.0, 0.3), "ledger_gap_events": 0,
                  "signature_anomalies": 1 if rng.random() > 0.93 else 0}
        elif organ == "tier0guard":
            r |= {"crown_touch_events": rng.randint(0, 2), "dependency_depth_traversed": rng.randint(0, 1)}
        rows.append(r)
    return rows


def generate(seed: int = 20261126) -> dict:
    rng = random.Random(seed)
    return {"seed": seed,
            "note": "fixture corpora for Part 6 evals; features are sandbox stand-ins for organ telemetry",
            "organs": {o: {"attack": _attack(o, ATTACK_N[o], rng), "clean": _clean(o, CLEAN_N[o], rng)}
                       for o in ORGANS}}


def main() -> None:
    parser = argparse.ArgumentParser(prog="gen-corpus")
    parser.add_argument("--out", default="./data/evals", help="output directory")
    parser.add_argument("--seed", type=int, default=20261126)
    args = parser.parse_args()
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    corpus = generate(args.seed)
    target = out_dir / "corpora.json"
    target.write_text(json.dumps(corpus, indent=1, sort_keys=True), encoding="utf-8")
    n_attack = sum(len(v["attack"]) for v in corpus["organs"].values())
    n_clean = sum(len(v["clean"]) for v in corpus["organs"].values())
    print(f"wrote {target} ({target.stat().st_size / 1024:.1f} KB): {n_attack} attack / {n_clean} clean rows, seed {args.seed}")


if __name__ == "__main__":
    main()
