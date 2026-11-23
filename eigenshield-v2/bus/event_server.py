"""PLANE 2 — FastAPI + WebSocket real-time telemetry broker.

    python -m bus.event_server --policy config/policy.yaml \
        --topology config/company_topology.json --model qwen3.5:4b \
        --host 0.0.0.0 --port 8080

Endpoints
---------
GET  /api/health      liveness + commander mode (slm | fallback_rules)
GET  /api/state       ring buffer stats, entity-graph snapshot, last plan
POST /api/ingest      raw organ event -> sanitize -> buffer -> broadcast
POST /api/orchestrate force a correlation pass over the current buffer
WS   /ws/telemetry    live feed: event | action_plan | governor_decision | tool_result
GET  /                JSON service card (dashboard UI is built by the UI/UX team)

High-severity ingests (severity >= 0.8) trigger a background orchestration
pass automatically. The in-process executor dispatches Governor-APPROVED
actions to the owning organs. In production this crosses a signed-RPC
boundary (see reflexes.base_organ.sign_rpc); here it is one process.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import threading
import time
from collections import deque
from typing import Any, Dict, List, Optional, Set

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Body
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.concurrency import run_in_threadpool

from bus.sanitizer import sanitize_event, sanitize_batch
from bus.entity_graph import EntityGraph

try:
    from commander.orchestrator import Orchestrator
    from commander.slm_client import SLMClient
    from governor.policy_engine import PolicyEngine
    from governor.audit_ledger import AuditLedger
    _PLANES_34 = True
except Exception:  # Plane 3/4 not importable: bus still serves telemetry
    _PLANES_34 = False

try:
    from fortress.telemetry_mac import sign_event, verify_event, SeenEventCache
    _FORTRESS = True
except Exception:  # fortress absent: legacy behavior, everything unverified
    _FORTRESS = False
    def sign_event(event):  # type: ignore
        return dict(event)
    def verify_event(event):  # type: ignore
        return False
    class SeenEventCache:  # type: ignore
        def __init__(self, **kw): pass
        def check_and_mark(self, event_id): return True


# --------------------------------------------------------------------------- #
# In-process executor: tool -> owning organ (integration seam)
# --------------------------------------------------------------------------- #
def _build_executor():
    from reflexes.ring1_perimeter_identity import BECSpectralFilter, CookieFluidTurbulence
    from reflexes.ring2_ai_defense import BraggFFTFirewall, HessianLyapunovGuard
    from reflexes.ring3_endpoint_silicon import PageCurveTrap, LandauerThermalAudit
    from reflexes.ring4_network_healing import HashimotoPercolation, MutsEbpfRepair

    bec = BECSpectralFilter()
    cookie = CookieFluidTurbulence()
    bragg = BraggFFTFirewall()
    lyap = HessianLyapunovGuard()
    trap = PageCurveTrap()  # dry-run by default: never os.kill from the bus
    thermal = LandauerThermalAudit()
    percol = HashimotoPercolation()
    muts = MutsEbpfRepair()

    table = {
        "drop_bec_cluster": lambda a: bec.drop_cluster(a.get("cluster_id", "CLUS_UNKNOWN"), int(a.get("ttl_seconds", 3600))),
        "revoke_turbulent_session": lambda a: cookie._rpc_revoke(a),
        "quarantine_ai_document": lambda a: bragg._rpc_quarantine(a),
        "clamp_lyapunov_steering": lambda a: lyap._rpc_clamp(a),
        "arm_page_curve_traps": lambda a: trap._rpc_arm(a),
        "isolate_thermal_anomaly_host": lambda a: thermal._rpc_isolate(a),
        "execute_percolation_cut": lambda a: percol._rpc_execute_cut(a),
        "deploy_muts_ebpf_shield": lambda a: muts._rpc_deploy(a),
        "set_service_readonly": lambda a: {"status": "SERVICE_READONLY_SET", "service_id": a.get("service_id"), "ttl_seconds": a.get("ttl_seconds"), "dry_run": True},
        "escalate_human_stepup": lambda a: {"status": "HUMAN_STEPUP_REQUESTED", "incident_id": a.get("incident_id"), "severity": a.get("severity"), "summary": str(a.get("summary", ""))[:280]},
    }

    def execute(tool: str, args: Dict[str, Any]) -> Dict[str, Any]:
        fn = table.get(tool)
        if fn is None:
            return {"status": "ERROR", "reason": f"no executor for tool {tool}"}
        return fn(args)

    return execute


# --------------------------------------------------------------------------- #
def create_app(policy_path: Optional[str] = None,
               topology_path: Optional[str] = None,
               model: Optional[str] = None) -> FastAPI:
    app = FastAPI(title="EIGENSHIELD v2 Telemetry Bus", version="2.0.0")
    # Dashboard is built separately by the UI/UX team (see docs/UI_UX_BRIEF.md);
    # allow static dev servers on any origin. No credentials are used.
    app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=False,
                       allow_methods=["*"], allow_headers=["*"])

    buffer: deque[Dict[str, Any]] = deque(maxlen=500)
    seen_ids = SeenEventCache()
    state_quarantine = {"unverified_held": 0, "replay_dropped": 0}
    graph = EntityGraph()
    clients: Set[WebSocket] = set()
    state = {"last_plan": None, "orchestration_count": 0, "started_at": time.time()}

    ledger = None
    governor = None
    orchestrator = None
    if _PLANES_34:
        policy_path = policy_path or os.path.join(os.path.dirname(__file__), "..", "config", "policy.yaml")
        ledger = AuditLedger(os.path.join(os.path.dirname(policy_path), "..", "audit_ledger.jsonl"))
        try:
            governor = PolicyEngine(policy_path, ledger=ledger)
            slm = SLMClient(model=model or os.environ.get("EIGENSHIELD_MODEL", "qwen3.5:4b"))
            orchestrator = Orchestrator(slm=slm)
        except Exception as exc:
            print(f"[bus] Plane 3/4 wiring degraded: {exc}")

    executor = _build_executor()
    orchestrate_lock = threading.Lock()

    async def broadcast(message: Dict[str, Any]) -> None:
        dead: List[WebSocket] = []
        payload = json.dumps(message, default=str)
        for ws in list(clients):
            try:
                await ws.send_text(payload)
            except Exception:
                dead.append(ws)
        for ws in dead:
            clients.discard(ws)

    def run_pipeline(trigger: str = "manual") -> Dict[str, Any]:
        if orchestrator is None or governor is None:
            return {"status": "DEGRADED", "reason": "Plane 3/4 not wired"}
        with orchestrate_lock:
            events = list(buffer)[-50:]
            if not events:
                return {"status": "NO_EVENTS"}
            # FORTRESS: the Commander NEVER sees unsigned telemetry. Forged
            # events remain visible in the buffer/dashboard (they are security
            # evidence themselves) but cannot steer the AI or reach an executor.
            evidence_events = [e for e in events if e.get("verified")]
            if not evidence_events:
                try:
                    from fortress import tripwire
                    tripwire.shared().record("unverified_disruptive")
                except ImportError:
                    pass
                return {"status": "HELD_UNVERIFIED_EVIDENCE",
                        "reason": "no organ-signed telemetry in window; AI path held closed",
                        "unverified_events": len(events)}
            plan = orchestrator.plan_actions(evidence_events, graph_payload=graph.payload())
            decisions = []
            results = []
            for action in plan.get("actions", []):
                decision = governor.evaluate(action, context={"trigger": trigger, "graph": graph.snapshot()})
                decisions.append(decision)
                if decision["decision"] == "APPROVED":
                    result = executor(action["tool"], action.get("args", {}))
                    results.append({"tool": action["tool"], "result": result})
                else:
                    results.append({"tool": action["tool"], "result": {"status": decision["decision"]}})
            state["last_plan"] = plan
            state["orchestration_count"] += 1
            bundle = {"status": "OK", "trigger": trigger, "plan_id": plan.get("plan_id"),
                      "commander_mode": plan.get("commander_mode"),
                      "actions": plan.get("actions", []),
                      "decisions": decisions, "results": results,
                      "brief": plan.get("brief", "")}
            if ledger is not None:
                ledger.append("orchestration", bundle)
            return bundle

    def _auto_orchestrate() -> None:
        bundle = run_pipeline(trigger="auto_high_severity")
        try:
            asyncio.run(broadcast({"type": "action_plan", "data": bundle}))
        except Exception:
            pass  # WS feed is best-effort

    def maybe_auto_orchestrate(event: Dict[str, Any]) -> None:
        if event.get("severity", 0) >= 0.8 and event.get("verified") and _PLANES_34:
            threading.Thread(target=_auto_orchestrate, daemon=True).start()

    # ------------------------------------------------------------------ #
    async def ingest_trusted(event: Dict[str, Any]) -> Dict[str, Any]:
        """In-process organ path: sign, buffer, broadcast. Never reachable from HTTP."""
        raw = sign_event(dict(event))
        evt = sanitize_event(raw)
        evt["verified"] = verify_event(raw)
        if seen_ids.check_and_mark(evt["event_id"]):
            buffer.append(evt)
            graph.add_event(evt)
        await broadcast({"type": "event", "data": evt})
        return evt

    app.state_ingest_trusted = ingest_trusted  # for tests/tools; not routed

    @app.get("/")
    async def root():
        return {
            "service": "EIGENSHIELD v2 Telemetry Bus",
            "status": "online",
            "dashboard": "served separately — see docs/UI_UX_BRIEF.md (UI/UX team owns the SOC dashboard)",
            "endpoints": ["/api/health", "/api/state", "/api/ingest", "/api/orchestrate", "/ws/telemetry"],
        }

    @app.get("/api/health")
    async def health():
        mode = "unavailable"
        if orchestrator is not None:
            mode = orchestrator.mode()
        return {"status": "ok", "planes_3_4": _PLANES_34, "commander_mode": mode,
                "uptime_sec": round(time.time() - state["started_at"], 1)}

    @app.get("/api/state")
    async def api_state():
        return {
            "buffered_events": len(buffer),
            "governor": governor.status() if governor is not None else None,
            "fortress": {"telemetry_mac": _FORTRESS,
                         "unverified_held": state_quarantine["unverified_held"],
                         "replay_dropped": state_quarantine["replay_dropped"],
                         **({"tripwire": __import__("fortress.tripwire", fromlist=["shared"]).shared().status()}
                            if _FORTRESS else {})},
            "entity_graph": graph.snapshot(),
            "last_plan": state["last_plan"],
            "orchestration_count": state["orchestration_count"],
            "recent_events": list(buffer)[-20:],
        }

    @app.post("/api/ingest")
    async def ingest(payload: Any = Body(...)):
        raw_events = payload if isinstance(payload, list) else [payload]
        sanitized = sanitize_batch(raw_events)
        accepted = 0
        unverified = 0
        for evt in sanitized:
            raw_match = next((r for r in raw_events if isinstance(r, dict)
                              and r.get("event_id") == evt.get("event_id")), None)
            verified = bool(raw_match and verify_event(raw_match))
            if verified and not seen_ids.check_and_mark(evt["event_id"]):
                state_quarantine["replay_dropped"] += 1
                continue  # replay: dropped, not reprocessed
            evt = dict(evt)
            evt["verified"] = verified
            if not verified:
                state_quarantine["unverified_held"] += 1
                unverified += 1
            try:
                from bus.sanitizer import looks_like_injection
                blob = json.dumps(raw_match or evt, default=str)
                if looks_like_injection(blob):
                    from fortress import tripwire
                    tripwire.shared().record("injection_marker")
            except Exception:
                pass
            buffer.append(evt)
            if verified:
                graph.add_event(evt)
            accepted += 1
            await broadcast({"type": "event", "data": evt})
            maybe_auto_orchestrate(evt)
        return {"accepted": accepted, "received": len(raw_events), "unverified": unverified}

    @app.post("/api/orchestrate")
    async def orchestrate():
        bundle = await run_in_threadpool(run_pipeline, "manual")
        await broadcast({"type": "action_plan", "data": bundle})
        return JSONResponse(bundle)

    @app.websocket("/ws/telemetry")
    async def ws_telemetry(ws: WebSocket):
        await ws.accept()
        clients.add(ws)
        try:
            await ws.send_text(json.dumps({"type": "hello", "data": {"buffered_events": len(buffer)}}))
            while True:
                await ws.receive_text()  # keepalive / client pings
        except WebSocketDisconnect:
            pass
        finally:
            clients.discard(ws)

    return app


def main() -> None:
    parser = argparse.ArgumentParser(description="EIGENSHIELD v2 telemetry broker")
    parser.add_argument("--policy", default="config/policy.yaml")
    parser.add_argument("--topology", default="config/company_topology.json")
    parser.add_argument("--model", default=os.environ.get("EIGENSHIELD_MODEL", "qwen3.5:4b"))
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8080)
    args = parser.parse_args()

    import uvicorn
    app = create_app(policy_path=args.policy, topology_path=args.topology, model=args.model)
    uvicorn.run(app, host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    main()
