"""SPINE — FastAPI + WebSocket real-time telemetry broker.

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

from spine.sanitizer import sanitize_event, sanitize_batch
from sentinel.shields.base_organ import sign_rpc
from spine.entity_graph import EntityGraph

try:
    from spine.orchestrator import Orchestrator
    from spine.slm_client import SLMClient
    from spine.governor import PolicyEngine
    from spine.ledger import AuditLedger
    _PLANES_34 = True
except Exception:  # Plane 3/4 not importable: bus still serves telemetry
    _PLANES_34 = False

try:
    from spine.telemetry_mac import sign_event, verify_event, SeenEventCache
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
# In-process executor — organ-backed (M2) with DRY_RUN fallback
# Preferred path: the Sentinel shield organs (sentinel/shields). Their RPCs are
# dry-run SAFE by construction (no os.kill, virtual graph cuts, simulated
# eBPF). If the shields are not importable, degrade loudly to labeled
# DRY_RUN stubs — never silently, never to something real.
# RAKSHA_EXECUTOR=dry-run forces the stub table (CI, stages without shields).
# --------------------------------------------------------------------------- #
def _try_organ_executor():
    from sentinel.shields.ring1_perimeter_identity import BECSpectralFilter, CookieFluidTurbulence
    from sentinel.shields.ring2_ai_defense import BraggFFTFirewall, HessianLyapunovGuard
    from sentinel.shields.ring3_endpoint_silicon import PageCurveTrap, LandauerThermalAudit
    from sentinel.shields.ring4_network_healing import HashimotoPercolation, MutsEbpfRepair

    bec = BECSpectralFilter()
    cookie = CookieFluidTurbulence()
    bragg = BraggFFTFirewall()
    lyap = HessianLyapunovGuard()
    trap = PageCurveTrap()  # dry-run by default: never os.kill from the bus
    thermal = LandauerThermalAudit()
    percol = HashimotoPercolation()
    muts = MutsEbpfRepair()

    # Part 4 Phase 2. Each entry maps a Governor-approved tool to the organ that
    # owns it. The call is made through `organ.handle_rpc()` with a *signed*
    # envelope — never by reaching into `_rpc_*` directly.
    #
    # Before this, every entry called the organ's private handler, so the
    # signature gate the organ implements was never consulted. The organ
    # rejected an unsigned call via handle_rpc() while the reachable actuator
    # performed it anyway: a gate that exists only where nothing can reach it.
    #
    # `set_service_readonly` and `escalate_human_stepup` are platform actions
    # with no organ behind them, so they stay local and say so.
    owned = {
        "drop_bec_cluster": bec,
        "revoke_turbulent_session": cookie,
        "quarantine_ai_document": bragg,
        "clamp_lyapunov_steering": lyap,
        "arm_page_curve_traps": trap,
        "isolate_thermal_anomaly_host": thermal,
        "execute_percolation_cut": percol,
        "deploy_muts_ebpf_shield": muts,
    }
    local = {
        "set_service_readonly": lambda a: {"status": "SERVICE_READONLY_SET", "service_id": a.get("service_id"), "ttl_seconds": a.get("ttl_seconds"), "dry_run": True},
        "escalate_human_stepup": lambda a: {"status": "HUMAN_STEPUP_REQUESTED", "incident_id": a.get("incident_id"), "severity": a.get("severity"), "summary": str(a.get("summary", ""))[:280]},
    }

    def execute(tool: str, args: Dict[str, Any]) -> Dict[str, Any]:
        org = owned.get(tool)
        if org is not None:
            envelope = sign_rpc(tool, dict(args or {}))
            reply = org.handle_rpc(envelope)
            if reply.get("status") != "OK":
                # A refused RPC is a refusal, not a silent success. Returning
                # the rejected envelope keeps the Governor's audit trail honest.
                return {"status": "RPC_" + str(reply.get("status")),
                        "reason": reply.get("reason", "organ refused the call"),
                        "tool": tool, "rpc_id": reply.get("rpc_id")}
            inner = reply.get("result")
            out = dict(inner) if isinstance(inner, dict) else {"result": inner}
            out["dispatch"] = "signed_rpc"
            out["organ"] = getattr(org, "organ", "ORGAN_UNKNOWN")
            return out
        fn = local.get(tool)
        if fn is None:
            return {"status": "ERROR", "reason": f"no executor for tool {tool}"}
        out = dict(fn(args))
        out["dispatch"] = "platform_local"
        return out

    return execute, "organ"


def _dry(tool: str, args: Dict[str, Any], **extra) -> Dict[str, Any]:
    out = {"status": f"DRY_RUN_{tool.upper()}", "tool": tool, "args": dict(args),
           "dry_run": True, "executed_at": time.time()}
    out.update(extra)
    return out


def _build_dry_executor():
    table = {
        "drop_bec_cluster": lambda a: _dry("drop_bec_cluster", a,
            detail={"cluster_id": a.get("cluster_id"), "ttl_seconds": a.get("ttl_seconds", 3600)}),
        "revoke_turbulent_session": lambda a: _dry("revoke_turbulent_session", a,
            detail={"session_id": a.get("session_id"), "user_id": a.get("user_id"),
                    "require_fido2": a.get("require_fido2", True)}),
        "quarantine_ai_document": lambda a: _dry("quarantine_ai_document", a,
            detail={"doc_hash": a.get("doc_hash"), "agent_id": a.get("agent_id")}),
        "clamp_lyapunov_steering": lambda a: _dry("clamp_lyapunov_steering", a,
            detail={"model_id": a.get("model_id"), "stiffness_gain": a.get("stiffness_gain")}),
        "arm_page_curve_traps": lambda a: _dry("arm_page_curve_traps", a,
            detail={"host_id": a.get("host_id"), "density_level": a.get("density_level")}),
        "isolate_thermal_anomaly_host": lambda a: _dry("isolate_thermal_anomaly_host", a,
            detail={"host_id": a.get("host_id"), "dump_hardware_trace": a.get("dump_hardware_trace")}),
        "execute_percolation_cut": lambda a: _dry("execute_percolation_cut", a,
            detail={"target_spectral_radius": a.get("target_spectral_radius"),
                    "preserve_tier0_vlans": a.get("preserve_tier0_vlans")}),
        "deploy_muts_ebpf_shield": lambda a: _dry("deploy_muts_ebpf_shield", a,
            detail={"service_id": a.get("service_id"),
                    "patch_profile_id": a.get("patch_profile_id")}),
        "set_service_readonly": lambda a: _dry("set_service_readonly", a,
            detail={"service_id": a.get("service_id"), "ttl_seconds": a.get("ttl_seconds")}),
        "escalate_human_stepup": lambda a: _dry("escalate_human_stepup", a,
            detail={"incident_id": a.get("incident_id"), "severity": a.get("severity"),
                    "summary": str(a.get("summary", ""))[:280]}),
    }

    def execute(tool: str, args: Dict[str, Any]) -> Dict[str, Any]:
        fn = table.get(tool)
        if fn is None:
            return {"status": "ERROR", "reason": f"no executor for tool {tool}"}
        out = dict(fn(args))
        # Same provenance field as the organ path, with a value that cannot be
        # mistaken for a real dispatch. A dry run that reports only "dry_run"
        # deep inside a status string is easy to miss in a log.
        out["dispatch"] = "dry_run"
        return out

    return execute, "dry-run"


def _build_executor():
    if os.environ.get("RAKSHA_EXECUTOR", "auto") != "dry-run":
        try:
            return _try_organ_executor()
        except Exception as exc:
            print(f"[spine] shields unavailable ({exc}); executor degraded to dry-run stubs")
    return _build_dry_executor()


# --------------------------------------------------------------------------- #
def create_app(policy_path: Optional[str] = None,
               topology_path: Optional[str] = None,
               model: Optional[str] = None) -> FastAPI:
    TOPOLOGY_PATH = topology_path or os.path.join(os.path.dirname(__file__), "config", "company_topology.json")
    app = FastAPI(title="RAKSHA Spine Telemetry Bus", version="0.2.0-m5")
    # Dashboard is built separately by the UI/UX team (see docs/UI_UX_BRIEF.md);
    # allow static dev servers on any origin. No credentials are used.
    app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=False,
                       allow_methods=["*"], allow_headers=["*"])

    buffer: deque[Dict[str, Any]] = deque(maxlen=500)
    seen_ids = SeenEventCache()
    state_quarantine = {"unverified_held": 0, "replay_dropped": 0}
    graph = EntityGraph()
    clients: Set[WebSocket] = set()
    state = {"last_plan": None, "orchestration_count": 0, "started_at": time.time(),
             "last_containment": None}

    ledger = None
    governor = None
    orchestrator = None
    if _PLANES_34:
        policy_path = policy_path or os.path.join(os.path.dirname(__file__), "config", "policy.yaml")
        ledger = AuditLedger(os.path.join(os.path.dirname(policy_path), "audit_ledger.jsonl"))
        try:
            governor = PolicyEngine(policy_path, ledger=ledger)
            slm = SLMClient(model=model or os.environ.get("EIGENSHIELD_MODEL", "qwen3.5:4b"))
            orchestrator = Orchestrator(slm=slm)
        except Exception as exc:
            print(f"[bus] Plane 3/4 wiring degraded: {exc}")

    def _tripwire_status():
        try:
            from spine import tripwire
            return tripwire.shared().status()
        except Exception:
            return {"frozen": False, "status": "tripwire unavailable"}

    executor, executor_mode = _build_executor()
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
                    from spine import tripwire
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
                      # Part 4 Phase 3: a rule that matched but could not act
                      # (no target in the event) is now visible to the operator
                      # instead of dying inside the Commander.
                      "skipped_actions": plan.get("skipped_actions", []),
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
            "service": "RAKSHA Spine Telemetry Bus",
            "status": "online",
            "dashboard": "served separately — see raksha/ROADMAP.md (SOC console owned by UI/UX team)",
            "endpoints": ["/api/health", "/api/state", "/api/ingest", "/api/orchestrate", "/ws/telemetry"],
        }

    @app.get("/api/health")
    async def health():
        mode = "unavailable"
        if orchestrator is not None:
            mode = orchestrator.mode()
        return {"status": "ok", "planes_3_4": _PLANES_34, "commander_mode": mode,
                "executor_mode": executor_mode,
                "uptime_sec": round(time.time() - state["started_at"], 1)}

    @app.get("/api/state")
    async def api_state():
        return {
            "buffered_events": len(buffer),
            "executor_mode": executor_mode,
            "governor": governor.status() if governor is not None else None,
            "fortress": {"telemetry_mac": _FORTRESS,
                         "unverified_held": state_quarantine["unverified_held"],
                         "replay_dropped": state_quarantine["replay_dropped"],
                         **({"tripwire": _tripwire_status()} if _FORTRESS else {})},
            "entity_graph": graph.snapshot(),
            "campaigns": graph.campaigns(),
            "last_plan": state["last_plan"],
            "last_containment": state.get("last_containment"),
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
                from spine.sanitizer import looks_like_injection
                blob = json.dumps(raw_match or evt, default=str)
                if looks_like_injection(blob):
                    from spine import tripwire
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

    @app.post("/api/containment")
    async def containment_propose(payload: Any = Body(default={})):
        """M5 containment planner: minimum-disruption cut sewing off the
        attacked side from Tier-0. Proposes only — the Governor disposes,
        the executor is a dry-run. Fixture-measured; never production SLO."""
        from spine import containment
        body = payload if isinstance(payload, dict) else {}
        seeds = body.get("seeds")
        if seeds is None:
            # derive from the live buffer: VLANs named in the current window,
            # excluding Tier-0/unknown — the attacker's apparent foothold
            topo = containment.load_topology(TOPOLOGY_PATH)
            tier0 = set(topo.get("tier0_vlans", []))
            valid = set(topo.get("vlans", []))
            derived = []
            for evt in buffer:
                v = (evt.get("entities") or {}).get("vlan_id")
                if v and v in valid and v not in tier0 and v not in derived:
                    derived.append(v)
            seeds = derived
            seed_source = "derived_from_buffer"
        else:
            if not isinstance(seeds, list) or not all(isinstance(s, str) for s in seeds):
                return JSONResponse({"status": "REFUSED", "reason": "seeds must be a list of VLAN id strings"}, status_code=400)
            seed_source = "caller_supplied"

        def _knob(name, default, lo, hi):
            try:
                v = float(body.get(name, default))
            except (TypeError, ValueError):
                return default
            return max(lo, min(hi, v))

        plan = containment.propose(TOPOLOGY_PATH, seeds,
                                   lam=_knob("lambda", 2.0, 0.0, 100.0),
                                   mu=_knob("mu", 0.1, 0.0, 100.0),
                                   nu=_knob("nu", 5.0, 0.0, 100.0))
        plan["seed_source"] = seed_source
        bundle = {"plan_source": "containment_planner", "containment": plan}

        if plan.get("status") == "PLAN_PROPOSED" and governor is not None:
            # Dynamic rho_after from the actual proposed cut (measured, clamped
            # to the tool schema's [0.5, 0.99] band for the legacy organ RPC).
            rho_after = 0.99
            rho_before = 0.99
            tier0_vlans = []
            try:
                from sentinel.shields.ring4_network_healing.hashimoto_percolation import spectral_radius
                topo = containment.load_topology(TOPOLOGY_PATH)
                nodes = topo["vlans"]
                tier0_vlans = topo.get("tier0_vlans", [])
                idx = {v: i for i, v in enumerate(nodes)}
                cut = {tuple(sorted((e["a"], e["b"]))) for e in plan["cut_edges"]}
                all_idx = [(idx[e["a"]], idx[e["b"]]) for e in topo["edges"]]
                edges_idx = [pair for pair, e in zip(all_idx, topo["edges"])
                             if tuple(sorted((e["a"], e["b"]))) not in cut]
                rho_before = spectral_radius(len(nodes), all_idx)
                rho_after = max(0.5, min(0.99, spectral_radius(len(nodes), edges_idx)))
            except Exception:
                pass
            # Part 4 Phase 3: this route used to hardcode
            # ``preserve_tier0_vlans: True`` and ignore whatever the caller
            # sent — so a request that explicitly asked for False came back
            # ``status: OK`` / ``APPROVED`` with tier-0 preserved anyway. The
            # system did the safe thing, but it *reported a decision the caller
            # had explicitly overridden*, which teaches an operator that their
            # input is advisory. Honouring it and refusing is honest; silently
            # substituting it is not. The Governor and the organ both refuse
            # ``not True``, so this is now a visible refusal, not a rewrite.
            wants_tier0_preserved = body.get("preserve_tier0_vlans", True)
            # Part 4 Phase 3: the organ used to be handed only a target radius
            # and answered with a status string — it never cut anything. The
            # planner's decision is now passed through so the actuator executes
            # the approved cut rather than inventing its own.
            action = {"tool": "execute_percolation_cut",
                      "args": {"target_spectral_radius": round(rho_after, 4),
                               "preserve_tier0_vlans": wants_tier0_preserved,
                               "seeds": plan.get("seeds", []),
                               "cut_edges": plan.get("cut_edges", []),
                               "rho_before": rho_before,
                               "rho_after": round(rho_after, 4),
                               "preserved_critical_weight_pct":
                                   plan.get("preserved_critical_weight_pct", 0.0)},
                      "rationale": f"containment planner {plan['plan_id']}: severs {plan['cut_size']} access-layer edge(s); ICU untouched; tier0 never cut"}
            decision = governor.evaluate(action, context={"trigger": "containment_planner",
                                                          "expected_preserved_uptime_pct": plan["preserved_critical_weight_pct"]})
            bundle["action"] = action
            bundle["governor"] = decision
            if decision["decision"] == "APPROVED":
                bundle["executor_result"] = executor(action["tool"], action["args"])
                bundle["status"] = "OK"
            else:
                bundle["executor_result"] = None
                bundle["status"] = "HELD_EXECUTION_BLOCKED"
            if ledger is not None:
                ledger.append("containment_plan", bundle)
        else:
            bundle["governor"] = None
            bundle["executor_result"] = None
            bundle["status"] = plan.get("status", "REFUSED")
        bundle["brief"] = (f"Containment planner proposes cutting {plan.get('cut_size')} edge(s) "
                           f"({', '.join(e['a'] + '↔' + e['b'] for e in plan.get('cut_edges', []))}). "
                           f"Tier-0 untouched; ICU {plan.get('icu_status', 'INTACT')}; "
                           f"fixture flow preserved {plan.get('preserved_fixture_flow_pct')}%.") if plan.get("status") == "PLAN_PROPOSED" else plan.get("reason", "refused")
        state["last_containment"] = bundle
        await broadcast({"type": "action_plan", "data": bundle})
        return JSONResponse(bundle)

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
    parser = argparse.ArgumentParser(description="RAKSHA spine telemetry broker")
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
