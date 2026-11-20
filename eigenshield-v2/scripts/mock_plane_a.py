#!/usr/bin/env python3
"""Mock Plane 1+2 for Part B (commander/governor) developers.

Part B can build and test the correlation/governor path without the real
reflex organs. Prints a fixed sequence of sanitized events (the exact shape
bus.sanitizer emits) that exercise every fallback rule in the orchestrator:

    python scripts/mock_plane_a.py --count 7

Usage: feed stdout into your test harness, or curl each line to /api/ingest.
"""

import argparse
import json
import os
import sys
import time
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

MOCK_EVENTS = [
    {"ring": "RING_1_PERIMETER_IDENTITY", "organ": "BEC_SPECTRAL_PROJECTOR",
     "signal_type": "RANK1_CONDENSATION_DETECTED", "severity": 0.88,
     "entities": {"host_id": "HOST_GATEWAY_01", "vlan_id": "VLAN_CORP_IT", "cluster_id": "CLUS_MOCK_BOTNET"},
     "metrics": {"condensation_ratio": 0.91}},
    {"ring": "RING_1_PERIMETER_IDENTITY", "organ": "COOKIE_FLUID_TURBULENCE",
     "signal_type": "TURBULENT_SESSION_REPLAY", "severity": 0.74,
     "entities": {"session_id": "SESS_MOCK_001", "user_id": "USER_019", "host_id": "HOST_042", "vlan_id": "VLAN_CORP_IT"},
     "metrics": {"re_beh": 5400.0}},
    {"ring": "RING_2_AI_DEFENSE", "organ": "BRAGG_FFT_FIREWALL",
     "signal_type": "INDIRECT_INJECTION_BLOCKED", "severity": 0.70,
     "entities": {"doc_hash": "sha256:mockinjection", "agent_id": "agent_banking_01", "host_id": "HOST_APP_SRV_07", "vlan_id": "VLAN_CORP_IT"},
     "metrics": {"bragg_peak_ratio": 0.61}},
    {"ring": "RING_2_AI_DEFENSE", "organ": "HESSIAN_LYAPUNOV_GUARD",
     "signal_type": "JAILBREAK_TRAJECTORY_DEFLECTED", "severity": 0.66,
     "entities": {"agent_id": "agent_banking_01", "host_id": "HOST_APP_SRV_07", "vlan_id": "VLAN_CORP_IT"},
     "metrics": {"kappa": 19.9}},
    {"ring": "RING_3_ENDPOINT_SILICON", "organ": "ENDPOINT_PAGE_CURVE",
     "signal_type": "PARITY_ENTROPY_COLLAPSE", "severity": 0.96,
     "entities": {"host_id": "HOST_042", "vlan_id": "VLAN_CORP_IT", "user_id": "USER_019", "process_hash": "pid:4242"},
     "metrics": {"bytes_written": 4096, "parity_delta": 0.994}},
    {"ring": "RING_3_ENDPOINT_SILICON", "organ": "LANDAUER_THERMAL_AUDITOR",
     "signal_type": "UNACCOUNTED_POWER_RESIDUAL", "severity": 0.71,
     "entities": {"host_id": "HOST_042", "vlan_id": "VLAN_CORP_IT"},
     "metrics": {"unaccounted_watts": 16.5}},
    {"ring": "RING_4_NETWORK_HEALING", "organ": "MUTS_EBPF_REPAIR",
     "signal_type": "MISMATCH_SHIELD_SPLICED", "severity": 0.90,
     "entities": {"service_id": "APP_SRV_07", "host_id": "HOST_APP_SRV_07", "vlan_id": "VLAN_CORP_IT"},
     "metrics": {"splice_ms": 48.0}},
]

parser = argparse.ArgumentParser()
parser.add_argument("--count", type=int, default=len(MOCK_EVENTS))
parser.add_argument("--delay", type=float, default=0.0)
parser.add_argument("--unsigned", action="store_true",
                    help="do NOT attach the organ HMAC (simulates an external forged feed)")
args = parser.parse_args()

try:
    from fortress.telemetry_mac import sign_event
    have_mac = True
except Exception:
    have_mac = False

for i in range(args.count):
    evt = dict(MOCK_EVENTS[i % len(MOCK_EVENTS)])
    evt["event_id"] = f"evt_mock_{uuid.uuid4().hex[:10]}"
    evt["timestamp_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    if have_mac and not args.unsigned:
        evt = sign_event(evt)  # internal organ path: signed at birth
    print(json.dumps(evt), flush=True)
    if args.delay:
        time.sleep(args.delay)
