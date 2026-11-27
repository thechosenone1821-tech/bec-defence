"""RAAVAN kill-chain player (M4).

Replays the canonical RAAVAN campaign — citizen voice-clone fraud → poisoned
vendor invoice → session replay → ransomware → governor probing — as SIGNED
organ telemetry into the spine bus. Every step is a real endpoint through the
same verification path real organs use; RAAVAN never bypasses the pipeline.

    python -m raavan.killchain --bus-url http://127.0.0.1:8090

Design honesty:
* RAAVAN emits *detections of its own attacks*, the way real organs would see
  them (this is the only end-to-end path the sandbox can honestly exercise).
* The per-step executors are dry-run by construction; Governor gates apply.
* campaign fusion works via `case_id` — an opaque link token shared by the
  citizen and infrastructure legs. The sanitizer HMACs unknown entity keys
  into stable sha256 tokens, so both legs land on the same campaign without
  any contract change. Case tokens MUST be high-entropy random in any real
  deployment (the sandbox uses low-entropy fixtures, which are dictionary-able).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import time
import urllib.request
from typing import Any, Callable, Dict, List, Optional

_CASE_ID = "CASE_RAAVAN_1930_0001"

STEPS: List[Dict[str, Any]] = [
    {
        "name": "T01 voice-clone vishing (citizen leg)",
        "event": {"ring": "RING_0_CITIZEN", "organ": "CITIZEN_APP",
                  "signal_type": "CITIZEN_REPORT_VOICE", "severity": 0.9,
                  "entities": {"case_id": _CASE_ID, "agent_id": "CITIZEN_ANON"},
                  "metrics": {"reports_day": 1}},
        "expect": "citizen signal lands; verified; campaign seed",
    },
    {
        "name": "T03 poisoned vendor invoice (agent leg)",
        "event": {"ring": "RING_2_AI_DEFENSE", "organ": "BRAGG_FFT_FIREWALL",
                  "signal_type": "INDIRECT_INJECTION_BLOCKED", "severity": 0.87,
                  "entities": {"case_id": _CASE_ID, "doc_hash": "sha256:mockinv0123",
                               "agent_id": "AGENT_075AB2", "host_id": "HOST_AB12CD"},
                  "metrics": {"f2_norm_ratio": 0.81}},
        "expect": "document quarantined proposal; injection blocked",
    },
    {
        "name": "T04 stolen session replay (identity leg)",
        "event": {"ring": "RING_1_PERIMETER_IDENTITY", "organ": "COOKIE_FLUID_TURBULENCE",
                  "signal_type": "TURBULENT_SESSION_REPLAY", "severity": 0.85,
                  "entities": {"case_id": _CASE_ID, "session_id": "SESS_9A8B7C",
                               "user_id": "USER_D15E55", "host_id": "HOST_AB12CD"},
                  "metrics": {"laminar_ratio": 0.11}},
        "expect": "session revoked proposal; trap pre-arm",
    },
    {
        "name": "T05 ransomware parity collapse (endpoint leg)",
        "event": {"ring": "RING_3_ENDPOINT_SILICON", "organ": "ENDPOINT_PAGE_CURVE",
                  "signal_type": "PARITY_ENTROPY_COLLAPSE", "severity": 0.96,
                  "entities": {"case_id": _CASE_ID, "host_id": "HOST_AB12CD",
                               "user_id": "USER_D15E55", "vlan_id": "VLAN_CORP_IT"},
                  "metrics": {"bytes_written": 4096, "parity_delta": 0.99}},
        "expect": "PID termination + human step-up escalation",
    },
    {
        "name": "T02/T08 sustained unattributed power residual (endpoint leg)",
        "event": {"ring": "RING_3_ENDPOINT_SILICON", "organ": "LANDAUER_THERMAL_AUDIT",
                  "signal_type": "UNACCOUNTED_POWER_RESIDUAL", "severity": 0.73,
                  "entities": {"case_id": _CASE_ID, "host_id": "HOST_AB12CD",
                               "user_id": "USER_D15E55", "vlan_id": "VLAN_CORP_IT"},
                  "metrics": {"unaccounted_watts": 17.4}},
        "expect": "host isolation proposal (dry-run)",
    },
]


def build_campaign(case_id: str = _CASE_ID) -> List[Dict[str, Any]]:
    nonce = hashlib.sha256(case_id.encode()).hexdigest()[:6]
    events = []
    for i, step in enumerate(STEPS, start=1):
        evt = dict(step["event"])
        evt["entities"] = {k: (case_id if v == _CASE_ID else v) for k, v in evt["entities"].items()}
        evt["event_id"] = f"evt_raavan_{nonce}_{i:04d}"
        evt["timestamp_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        events.append(evt)
    return events


def run(ingest: Callable[[List[Dict[str, Any]]], Dict[str, Any]],
        orchestrate: Callable[[], Dict[str, Any]],
        state: Callable[[], Dict[str, Any]],
        sign: Callable[[Dict[str, Any]], Dict[str, Any]],
        log: Callable[[str], None] = print) -> Dict[str, Any]:
    events = build_campaign()
    signed = [sign(dict(e)) for e in events]

    log("RAAVAN unleashed. Submitting forged (unsigned) probe first …")
    forge = ingest(events)
    log(f"  forged ingest -> {forge}")
    held = orchestrate()
    log(f"  orchestrator responds -> status={held.get('status')}")
    assert held.get("status") == "HELD_UNVERIFIED_EVIDENCE", \
        "forged telemetry steered the AI path — FAIL"

    log("Now the organ-signed campaign (the real attack, observed) …")
    ack = ingest(signed)
    log(f"  signed ingest  -> {ack}")
    bundle = orchestrate()
    log(f"  orchestrate    -> status={bundle.get('status')} commander={bundle.get('commander_mode')}")
    for res in bundle.get("results", []):
        log(f"    {res['tool']} -> {json.dumps(res['result'])[:110]}")

    snap = state()
    campaigns = snap.get("campaigns", [])
    biggest = campaigns[0] if campaigns else {}
    log("Fused campaign view:")
    log(f"  campaign_id={biggest.get('campaign_id')} size={biggest.get('size')} "
        f"severity_max={biggest.get('severity_max')}")
    layers = sorted({e.get("organ", "?") for e in snap.get("recent_events", [])})
    log(f"  layers touched: {layers}")
    return {"forge": forge, "signed": ack, "bundle": bundle,
            "campaigns": campaigns, "layers": layers}


def _http_json(url: str, payload: Optional[Any] = None):
    data = None if payload is None else json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data,
                                 headers={"Content-Type": "application/json"},
                                 method=("POST" if payload is not None else "GET"))
    with urllib.request.urlopen(req, timeout=180) as resp:
        return json.loads(resp.read().decode())


def main() -> None:
    parser = argparse.ArgumentParser(description="RAAVAN kill-chain replay")
    parser.add_argument("--bus-url", default="http://127.0.0.1:8090")
    args = parser.parse_args()
    try:
        from spine.telemetry_mac import sign_event
    except Exception:
        import os, sys
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from spine.telemetry_mac import sign_event
    base = args.bus_url.rstrip("/")
    run(lambda p: _http_json(base + "/api/ingest", p),
        lambda: _http_json(base + "/api/orchestrate", {}),
        lambda: _http_json(base + "/api/state"),
        sign_event)


if __name__ == "__main__":
    main()
