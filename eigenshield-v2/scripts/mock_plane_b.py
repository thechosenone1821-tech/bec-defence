#!/usr/bin/env python3
"""Mock Plane 3+4 for Part A (reflex/bus) developers.

Part A can build and test the telemetry path without the real Commander or
Governor. This mock exposes the exact same shapes the real components produce:

    plan  : {"plan_id", "commander_mode": "mock", "actions": [...], "brief": "..."}
    decision: {"decision": "APPROVED", "tool": ..., "args": ..., "reasons": [...]}

Usage:
    python scripts/mock_plane_b.py < events.jsonl

Each stdin line is one sanitized event; the mock prints one plan JSON per line.
Deterministic; used by docs/BACKEND_PART_A.md.
"""

import json
import sys
import uuid
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

TOOL_FOR_SIGNAL = {
    "RANK1_CONDENSATION_DETECTED": ("drop_bec_cluster", lambda e: {"cluster_id": "CLUS_MOCK_01", "ttl_seconds": 3600}),
    "TURBULENT_SESSION_REPLAY": ("revoke_turbulent_session", lambda e: {"session_id": e.get("entities", {}).get("session_id", "SESS_MOCK"), "user_id": e.get("entities", {}).get("user_id", "USER_MOCK"), "require_fido2": True}),
    "PARITY_ENTROPY_COLLAPSE": ("arm_page_curve_traps", lambda e: {"host_id": e.get("entities", {}).get("host_id", "HOST_MOCK"), "density_level": "high"}),
    "INDIRECT_INJECTION_BLOCKED": ("quarantine_ai_document", lambda e: {"doc_hash": e.get("entities", {}).get("doc_hash", "sha256:mock"), "agent_id": e.get("entities", {}).get("agent_id", "agent_mock")}),
}

for line in sys.stdin:
    line = line.strip()
    if not line:
        continue
    evt = json.loads(line)
    sig = evt.get("signal_type", "")
    tool, fn = TOOL_FOR_SIGNAL.get(sig, ("escalate_human_stepup", lambda e: {"incident_id": f"inc_{uuid.uuid4().hex[:8]}", "severity": float(e.get("severity", 0.5)), "summary": f"mock review: {sig or 'unknown signal'}"}))
    plan = {
        "plan_id": f"mockplan_{uuid.uuid4().hex[:8]}",
        "commander_mode": "mock",
        "kill_chain_stage": "mock",
        "correlated_entities": list(evt.get("entities", {}).values()),
        "actions": [{"tool": tool, "args": fn(evt), "rationale": "mock decision for Part A development"}],
        "brief": f"Mock plan for signal {sig}. Real Commander replaces this.",
    }
    decision = {"decision": "APPROVED", "tool": tool, "args": plan["actions"][0]["args"], "reasons": ["mock approve"]}
    print(json.dumps({"plan": plan, "decision": decision}))
