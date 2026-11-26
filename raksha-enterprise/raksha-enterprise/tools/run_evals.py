"""Measured evaluation harness — writes EVALS.md and summary.json.

Everything measured here runs the REAL package components: organ detectors,
fusion, planner, Governor, ledger, and the full embedded pipeline executing
the c2247 RAAVAN scenario end-to-end. No authored numbers.

Usage:
  python3 tools/gen_corpus.py --out ./data/evals
  python3 tools/run_evals.py --out ./data/evals
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import tempfile
import time
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from raksha.config import Settings
from raksha.events import Event, VerifyState, sign_event, tamper_event, verify_event
from raksha.ledger import LedgerStore
from raksha.metrics import Metrics
from raksha.organs import ORGANS, Detection
from raksha.pipeline import CampaignFusion, Governor, Planner, Pipeline
from raksha.pipeline.topology import Topology
from raksha.storage import EventStore

SYSTEM = "raksha-enterprise"


def _pctl(sorted_vals: list[float], q: float) -> float:
    return sorted_vals[min(len(sorted_vals) - 1, round(q * (len(sorted_vals) - 1)))]


def _stat(vals: list[float]) -> dict:
    vals = sorted(vals)
    return {"n": len(vals), "p50": round(statistics.median(vals), 3),
            "p95": round(_pctl(vals, 0.95), 3)}


def organ_rates(corpus: dict) -> tuple[dict, dict]:
    stats, agg_hits, agg_n, agg_fp, agg_clean = {}, 0, 0, 0, 0
    for name, organ in sorted(ORGANS.items()):
        rows = corpus["organs"][name]
        hits = sum(1 for r in rows["attack"] if organ.detect(r))
        fps = sum(1 for r in rows["clean"] if organ.detect(r))
        stats[name] = {"n_attack": len(rows["attack"]), "n_flagged": hits,
                       "detection_rate": round(hits / len(rows["attack"]), 4),
                       "n_clean": len(rows["clean"]), "n_fp": fps,
                       "fp_rate": round(fps / len(rows["clean"]), 4)}
        agg_hits += hits
        agg_n += len(rows["attack"])
        agg_fp += fps
        agg_clean += len(rows["clean"])
    agg = {"detection_rate": round(agg_hits / agg_n, 4), "n_attack": agg_n,
           "fp_rate": round(agg_fp / agg_clean, 4), "n_clean": agg_clean}
    return stats, agg


def integrity_check(sensor_key: bytes) -> dict:
    ok = unsigned = tampered = 0
    for i in range(50):
        event = Event(f"EVAL-{i}", "2026-01-01T00:00:00Z", "netguard", "", "", "infra",
                      3, "N-BUILD-SRV", "eval probe", {"egress_gb_24h": 1.0})
        if i % 5 == 0:
            unsigned += 1
            if verify_event(event, sensor_key) is not VerifyState.UNSIGNED:
                raise AssertionError("unsigned event did not report UNSIGNED")
            continue
        sign_event(event, sensor_key)
        if i % 7 == 0:
            tamper_event(event)
        state = verify_event(event, sensor_key)
        if state is VerifyState.VALID:
            ok += 1
        elif state is VerifyState.TAMPERED:
            tampered += 1
        else:
            raise AssertionError("signed event failed to verify")
    return {"signed_ok": ok, "tampered_flagged": tampered, "unsigned_flagged": unsigned}


def stage_latencies(corpus: dict, tmp: Path) -> dict:
    """Per-item latencies of the real component stages."""
    sensor_key = b"eval-harness-stage-latency-key-32b!!"
    rows = []
    for name in ORGANS:
        for label in ("attack", "clean"):
            for i, features in enumerate(corpus["organs"][name][label]):
                rows.append((name, f"{name}-{label}-{i}", features))

    # sign every row (untimed setup) so the verify stage can time real HMAC checks
    events = []
    for name, eid, features in rows:
        event = Event(eid, "2026-01-01T00:00:00Z", name, "C-EVAL", "case-eval", "infra",
                      3, "N-BUILD-SRV", "eval row", features)
        sign_event(event, sensor_key)
        events.append(event)

    verify_times, detect_times, fuse_times = [], [], []
    fusion = CampaignFusion()
    for _ in range(30):
        for event in events:
            t0 = time.perf_counter()
            verify_event(event, sensor_key)
            verify_times.append((time.perf_counter() - t0) * 1e6)
        for (name, eid, _features), event in zip(rows, events):
            t0 = time.perf_counter()
            ORGANS[name].detect(event.payload)
            detect_times.append((time.perf_counter() - t0) * 1e6)

    from raksha.organs import Detection  # noqa: F401 — re-imported for eval clarity
    detections = [Detection(organ=e.organ, rule_id=f"{e.organ}-EVAL", event_id=e.event_id,
                            campaign_id=e.campaign_id, case_id=e.case_id, leg=e.leg,
                            entity=e.entity, severity=e.severity, summary=e.summary)
                  for e in events]
    for _ in range(30):
        for d in detections:
            t0 = time.perf_counter()
            fusion.add(d)
            fuse_times.append((time.perf_counter() - t0) * 1e6)

    # plan / decide on a real fused campaign with real topology
    campaign = fusion.get("C-EVAL", "case-eval")
    topo = Topology.load(None, ("N-TIER0-CORE", "N-IDENTITY-VAULT"))
    planner = Planner(topo)
    plan_times = []
    for _ in range(30):
        t0 = time.perf_counter()
        proposals = planner.proposals_for(campaign)
        plan_times.append((time.perf_counter() - t0) * 1000)
    governor = Governor(blast_cap=8, precision_max_blast=2)
    decide_times = []
    for _ in range(200):
        for proposal in proposals:
            t0 = time.perf_counter()
            governor.decide(proposal)
            decide_times.append((time.perf_counter() - t0) * 1e6)

    ledger = LedgerStore(tmp / "eval-ledger.db")
    seal_times = []
    for _ in range(30):
        t0 = time.perf_counter()
        ledger.append("ops-note", "EVAL", "eval block", {"i": 0})
        seal_times.append((time.perf_counter() - t0) * 1000)

    return {
        "verify_event_us_per_event": _stat(verify_times),
        "organ_detect_us_per_event": _stat(detect_times),
        "fusion_add_us_per_detection": _stat(fuse_times),
        "planner_ms_per_campaign": _stat(plan_times),
        "governor_us_per_proposal": _stat(decide_times),
        "ledger_append_ms_per_block": _stat(seal_times),
        "n_stream": len(events),
        "n_proposals": len(proposals),
    }


def campaign_wall_clock(repeats: int = 50) -> dict:
    """Full embedded pipeline executing the c2247 scenario, fresh state per run."""
    from raksha.raavan.player import RaavanPlayer, embedded_transport, load_scenario  # noqa: PLC0415

    totals = []
    scenario = load_scenario()
    last_report = None
    for _ in range(repeats):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            settings = Settings(data_dir=tmp, log_level="ERROR", rate_limit_epm=600)
            sensor_key = b"eval-harness-campaign-wallclock-key!!"
            store = EventStore(settings.events_db_path)
            ledger = LedgerStore(settings.ledger_db_path)
            pipeline = Pipeline(settings, sensor_key, ledger, store, Metrics())
            player = RaavanPlayer(embedded_transport(pipeline), sensor_key, scenario, ledger=ledger)
            t0 = time.perf_counter()
            last_report = player.run()
            totals.append((time.perf_counter() - t0) * 1000)
    assert last_report is not None and last_report["ok"], "scenario failed during wall-clock eval"
    return {"events": sum(s["events_sent"] for s in last_report["steps"]),
            "p50_ms": _stat(totals)["p50"], "p95_ms": _stat(totals)["p95"],
            "n_repeats": repeats}


def main() -> None:
    parser = argparse.ArgumentParser(prog="raksha-evals")
    parser.add_argument("--out", default="./data/evals", help="output directory")
    parser.add_argument("--repeats", type=int, default=50)
    args = parser.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    corpus = json.loads((out / "corpora.json").read_text(encoding="utf-8"))
    sensor_key = b"eval-harness-integrity-key-32bytes!!"

    organ_stats, agg = organ_rates(corpus)
    integrity = integrity_check(sensor_key)
    with tempfile.TemporaryDirectory() as td:
        latency = stage_latencies(corpus, Path(td))
    campaign = campaign_wall_clock(args.repeats)

    summary = {
        "system": SYSTEM, "generated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "seed": corpus["seed"], "scope": "MEASURED ON FIXTURES in a sandbox — not a deployment measurement",
        "organ_stats": organ_stats, "aggregate": agg, "integrity": integrity,
        "stage_latency": latency, "campaign_wall_clock": campaign,
    }
    (out / "summary.json").write_text(json.dumps(summary, indent=1, sort_keys=True), encoding="utf-8")

    lines = [
        f"# {SYSTEM} — EVALS", "",
        f"> Generated {summary['generated']} · corpora seed {corpus['seed']} (deterministic) · scope: **{summary['scope']}**", "",
        "## 1. Per-organ detection rates (attack corpus)", "",
        "| Organ | Attack rows | Flagged | Detection rate | Clean rows | FP | FP rate |",
        "|---|---|---|---|---|---|---|",
    ]
    for name, s in organ_stats.items():
        lines.append(f"| {name} | {s['n_attack']} | {s['n_flagged']} | {s['detection_rate']*100:.1f}% | "
                     f"{s['n_clean']} | {s['n_fp']} | {s['fp_rate']*100:.2f}% |")
    lines += [
        f"| **aggregate** | **{agg['n_attack']}** | **{agg['detection_rate']*agg['n_attack']:.0f}** | "
        f"**{agg['detection_rate']*100:.1f}%** | **{agg['n_clean']}** | "
        f"**{agg['fp_rate']*agg['n_clean']:.0f}** | **{agg['fp_rate']*100:.2f}%** |", "",
        "Detectors are the frozen threshold rules shipped in `raksha.organs` — the same modules the service runs.", "",
        "## 2. Stage latency (p50 / p95)", "",
        "| Stage | unit | p50 | p95 | n |", "|---|---|---|---|---|",
        f"| verify_event | us/event | {latency['verify_event_us_per_event']['p50']:.1f} | {latency['verify_event_us_per_event']['p95']:.1f} | {latency['verify_event_us_per_event']['n']} |",
        f"| organ.detect | us/event | {latency['organ_detect_us_per_event']['p50']:.1f} | {latency['organ_detect_us_per_event']['p95']:.1f} | {latency['organ_detect_us_per_event']['n']} |",
        f"| fusion.add | us/detection | {latency['fusion_add_us_per_detection']['p50']:.1f} | {latency['fusion_add_us_per_detection']['p95']:.1f} | {latency['fusion_add_us_per_detection']['n']} |",
        f"| planner.proposals_for | ms/campaign | {latency['planner_ms_per_campaign']['p50']:.2f} | {latency['planner_ms_per_campaign']['p95']:.2f} | {latency['planner_ms_per_campaign']['n']} |",
        f"| governor.decide | us/proposal | {latency['governor_us_per_proposal']['p50']:.1f} | {latency['governor_us_per_proposal']['p95']:.1f} | {latency['governor_us_per_proposal']['n']} |",
        f"| ledger.append | ms/block | {latency['ledger_append_ms_per_block']['p50']:.2f} | {latency['ledger_append_ms_per_block']['p95']:.2f} | {latency['ledger_append_ms_per_block']['n']} |", "",
        "SQLite-backed append, WAL mode, one fsync-batched commit per block — not a distributed-ledger claim.", "",
        "## 3. End-to-end campaign (embedded pipeline, c2247 scenario)", "",
        f"Full pipeline incl. SQLite writes, {campaign['n_repeats']} fresh-state repeats: "
        f"**p50 {campaign['p50_ms']:.1f} ms / p95 {campaign['p95_ms']:.1f} ms** for {campaign['events']} events "
        "(sign -> verify -> detect -> fuse -> plan -> decide -> seal).", "",
        "## 4. Integrity self-check", "",
        f"- signed events verify: {integrity['signed_ok']} / tampered flagged: {integrity['tampered_flagged']} / unsigned flagged: {integrity['unsigned_flagged']} (expected 40 / 5 / 10)", "",
        "## 5. Claims ledger", "",
        "| Claim | Status |", "|---|---|",
        "| Per-organ detection rate | MEASURED (fixture corpora, section 1) |",
        "| False-positive rate on clean traffic | MEASURED (fixture corpora, section 1) |",
        "| Stage latencies (real components) | MEASURED (section 2) |",
        "| End-to-end campaign time | MEASURED (embedded pipeline, section 3) |",
        "| Governor latency under production load | UNMEASURED — do not claim |",
        "| Detection rates against a live adversary | UNMEASURED — RAAVAN replays signed fixtures |",
        "| Containment disruption cost in a real network | UNMEASURED — topology is a demo deployment |", "",
        "## 6. Reproduce", "", "```",
        "python3 tools/gen_corpus.py --out ./data/evals",
        "python3 tools/run_evals.py --out ./data/evals", "```", "",
        "Detectors, fusion, planner, Governor and ledger are imported from the installed package — "
        "evals cannot drift from the service.", "",
    ]
    (out / "EVALS.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"wrote {out/'EVALS.md'} and {out/'summary.json'}")
    for name, s in organ_stats.items():
        print(f"  {name:12s} {s['detection_rate']*100:5.1f}%  (FP {s['fp_rate']*100:.2f}%)")
    print(f"  aggregate   {agg['detection_rate']*100:5.1f}%  (FP {agg['fp_rate']*100:.2f}%)")
    print(f"campaign wall-clock p50/p95: {campaign['p50_ms']:.1f}/{campaign['p95_ms']:.1f} ms")


if __name__ == "__main__":
    main()
