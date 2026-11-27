"""Phase 6–8 — one deterministic Infra runtime and unified backend.

This is the active app factory behind ``apps.infra.backend.app``. It wires the
single detector contract, one Governor/planner/executor/ledger safety path,
scoped tokens, dedupe, rate limits, quarantine, metrics, one WebSocket stream
and read-only state surfaces. It does not import Citizen, VIGIL, a Commander/SLM
client, the legacy ``spine.bus`` or a real containment executor.
"""
from __future__ import annotations

import asyncio
import hashlib
import os
import threading
import time
from collections import deque
from collections.abc import Mapping as ABCMapping
from dataclasses import dataclass, field
from typing import Any, Callable

from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse

from packages.contracts.canonical import canonical_hash
from packages.contracts.config import DEFAULT_TOPOLOGY
from packages.contracts.envelope import EnvelopeValidationError, sign_event
from packages.governance.commander import commander_card
from packages.governance.safety import (
    VERDICT_ALLOWED, DryRunExecutor, ExhaustivePlanner, Governor, Topology,
)
from packages.ledger.runtime_ledger import RuntimeLedger
from packages.spine.contract import SPINE_CONTRACT

RUNTIME_CONTRACT_VERSION = "raksha-infra-runtime-v1"
DEFAULT_SENSOR_KEY = b"raksha-phase678-dev-sensor-key"
DEFAULT_ADMIN_TOKEN = "demo-admin-token"
DEFAULT_SENSOR_TOKEN = "demo-sensor-token"
DEFAULT_OBSERVER_TOKEN = "demo-observer-token"


class AuthError(Exception):
    def __init__(self, status: int, detail: str) -> None:
        super().__init__(detail)
        self.status = status
        self.detail = detail


@dataclass(frozen=True)
class TokenRecord:
    name: str
    scopes: frozenset[str]


class TokenStore:
    def __init__(self, records: dict[str, TokenRecord], plaintext: tuple[tuple[str, str, tuple[str, ...]], ...]) -> None:
        self._records = records
        self.plaintext = plaintext

    @classmethod
    def from_tokens(cls, tokens: Any) -> "TokenStore":
        normalized: list[tuple[str, str, tuple[str, ...]]] = []
        for item in tokens:
            if isinstance(item, ABCMapping):
                token = str(item["token"])
                name = str(item.get("name") or "token")
                scopes = tuple(item.get("scopes") or ())
            else:
                token, name, scopes = item
                token, name, scopes = str(token), str(name), tuple(scopes)
            normalized.append((token, name, scopes))
        records = {
            hashlib.sha256(token.encode()).hexdigest(): TokenRecord(name, frozenset(scopes))
            for token, name, scopes in normalized
        }
        return cls(records, tuple(normalized))

    def authenticate(self, token: str) -> TokenRecord:
        if not token:
            raise AuthError(401, "missing API token")
        digest = hashlib.sha256(token.encode()).hexdigest()
        record = self._records.get(digest)
        if record is None:
            raise AuthError(401, "invalid API token")
        return record

    @staticmethod
    def authorize(record: TokenRecord, scope: str) -> None:
        if scope not in record.scopes and "admin" not in record.scopes:
            raise AuthError(403, f"token {record.name!r} lacks required scope {scope!r}")


def _default_tokens() -> list[tuple[str, str, tuple[str, ...]]]:
    return [
        (os.environ.get("RAKSHA_ADMIN_TOKEN", DEFAULT_ADMIN_TOKEN), "admin",
         ("admin", "read", "telemetry:write")),
        (os.environ.get("RAKSHA_SENSOR_TOKEN", DEFAULT_SENSOR_TOKEN), "sensor",
         ("telemetry:write",)),
        (os.environ.get("RAKSHA_OBSERVER_TOKEN", DEFAULT_OBSERVER_TOKEN), "observer",
         ("read",)),
    ]


def _coerce_key(value: Any) -> bytes:
    if value is None:
        raw = os.environ.get("RAKSHA_SENSOR_KEY", "")
        return raw.encode() if raw else DEFAULT_SENSOR_KEY
    if isinstance(value, bytes):
        return value
    return str(value).encode()


class Metrics:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._counters: dict[str, int] = {}
        self._t0 = time.monotonic()

    def inc(self, name: str, by: int = 1) -> None:
        with self._lock:
            self._counters[name] = self._counters.get(name, 0) + by

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            counters = dict(self._counters)
        return {
            "uptime_s": round(time.monotonic() - self._t0, 1),
            "counters": counters,
            "latency_ms": {},
            "deterministic": True,
            "ai_models_invoked": 0,
        }


class Hub:
    """One WebSocket fan-out. History is retained so a console sees the campaign."""

    def __init__(self, step_fn: Callable[[], int], metrics: Metrics) -> None:
        self._clients: set[asyncio.Queue] = set()
        self._loop: asyncio.AbstractEventLoop | None = None
        self._history: list[dict[str, Any]] = []
        self._lock = threading.Lock()
        self._step_fn = step_fn
        self._metrics = metrics

    def attach_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop

    def subscribe(self) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue(maxsize=512)
        with self._lock:
            self._clients.add(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue) -> None:
        with self._lock:
            self._clients.discard(queue)

    def history(self) -> list[dict[str, Any]]:
        with self._lock:
            return [dict(item) for item in self._history]

    def publish_sync(self, kind: str, data: dict[str, Any]) -> None:
        item = {"step": self._step_fn(), "kind": kind, "data": dict(data)}
        with self._lock:
            self._history.append(item)
            clients = list(self._clients)
        self._metrics.inc("ws.publish_calls")

        def _fanout() -> None:
            for queue in clients:
                try:
                    queue.put_nowait(item)
                    self._metrics.inc("ws.delivered")
                except asyncio.QueueFull:
                    self._metrics.inc("ws.dropped_slow_consumer")

        if self._loop is None:
            self._metrics.inc("ws.no_loop")
            return
        try:
            self._loop.call_soon_threadsafe(_fanout)
        except RuntimeError:
            self._metrics.inc("ws.loop_closed")


@dataclass
class CampaignState:
    campaign_id: str
    case_id: str
    legs: set[str] = field(default_factory=set)
    organs: set[str] = field(default_factory=set)
    entities: set[str] = field(default_factory=set)
    detections: list[dict[str, Any]] = field(default_factory=list)
    first_seen: int = 0
    last_seen: int = 0

    @property
    def fused(self) -> bool:
        return len(self.legs) >= 2

    def to_dict(self) -> dict[str, Any]:
        return {
            "campaign_id": self.campaign_id, "case_id": self.case_id,
            "legs": sorted(self.legs), "organs": sorted(self.organs),
            "entities": sorted(self.entities), "fused": self.fused,
            "risk_score": min(100, len(self.detections) * 10),
            "detections": len(self.detections),
            "first_seen": self.first_seen, "last_seen": self.last_seen,
        }


class SafetyRuntime:
    """One ingest → detect → fuse → plan → decide → seal → broadcast path."""

    def __init__(self, *, detector: Callable[..., Any], sensor_key: bytes,
                 token_store: TokenStore, topology_path: str | None = None,
                 policy_path: str | None = None, rate_limit_epm: int = 600,
                 blast_cap: int = 3) -> None:
        self.detector = detector
        self.sensor_key = sensor_key
        self.token_store = token_store
        self.policy_path = policy_path
        self.topology_path = str(topology_path or DEFAULT_TOPOLOGY)
        self.rate_limit_epm = max(1, int(rate_limit_epm))
        self.metrics = Metrics()
        self.ledger = RuntimeLedger()
        self.hub = Hub(self._step, self.metrics)
        self.topology = Topology.from_path(self.topology_path)
        self.planner = ExhaustivePlanner(self.topology)
        self.governor = Governor(blast_cap=blast_cap)
        self.executor = DryRunExecutor()
        self.commander = commander_card()
        self.quarantine: list[dict[str, Any]] = []
        self.detections: list[dict[str, Any]] = []
        self.campaigns: dict[tuple[str, str], CampaignState] = {}
        self.timeline: list[dict[str, Any]] = []
        self._lock = threading.RLock()
        self._step_counter = 0
        self._seen: set[str] = set()
        self._seen_order: deque[str] = deque(maxlen=200_000)
        self._windows: dict[str, deque[float]] = {}
        self._decided: set[str] = set()
        self._plan_locked_campaigns: set[str] = set()

    # -- deterministic logical clock / timeline ---------------------------
    def _step(self) -> int:
        with self._lock:
            self._step_counter += 1
            return self._step_counter

    def _timeline_add(self, stage: str, kind: str, *, ledger_seq: int | None = None,
                      ref: str = "", detail: str = "") -> None:
        entry = {
            "step": self._step(), "stage": stage, "kind": kind,
            "ledger_seq": ledger_seq, "ref": ref, "detail": detail,
        }
        with self._lock:
            self.timeline.append(entry)

    # -- one ledger write path -------------------------------------------
    def _seal(self, kind: str, ref: str, text: str, payload: dict[str, Any],
              *, actor: str = "SafetyRuntime") -> dict[str, Any]:
        block = self.ledger.append(kind=kind, ref=ref, text=text, payload=payload, actor=actor)
        self.metrics.inc("ledger.append")
        self._timeline_add("ledger", kind, ledger_seq=block["seq"], ref=ref, detail=text)
        return block

    def append_operator_note(self, body: dict[str, Any], *, actor: str) -> dict[str, Any]:
        return self._seal(
            kind=str(body["kind"]), ref=str(body["ref"]), text=str(body["text"]),
            payload=dict(body.get("payload") or {}), actor=f"admin:{actor}",
        )

    # -- ingest gates -----------------------------------------------------
    def _allow(self, source: str) -> bool:
        now = time.monotonic()
        with self._lock:
            window = self._windows.setdefault(source, deque())
            while window and now - window[0] > 60.0:
                window.popleft()
            if len(window) >= self.rate_limit_epm:
                return False
            window.append(now)
            return True

    def _mark_seen(self, event_id: str) -> bool:
        with self._lock:
            if event_id in self._seen:
                return False
            self._seen.add(event_id)
            self._seen_order.append(event_id)
            if len(self._seen_order) == self._seen_order.maxlen:
                self._seen.discard(self._seen_order[0])
            return True

    @staticmethod
    def _result_dict(result: Any) -> dict[str, Any]:
        if hasattr(result, "to_dict"):
            return dict(result.to_dict())
        if isinstance(result, ABCMapping):
            return dict(result)
        raise TypeError("detector must return a DetectionResult or mapping")

    def _quarantine(self, raw: dict[str, Any], result: dict[str, Any], source: str) -> dict[str, Any]:
        item = dict(result.get("quarantine") or {})
        item.update({
            "source": source,
            "event_id": str(raw.get("event_id") or item.get("event_id") or ""),
            "organ": str(raw.get("organ") or item.get("organ") or ""),
            "state": result.get("state") or item.get("state") or "quarantined",
            "reason": result.get("reason") or item.get("reason") or "quarantined",
            "actionable": False,
            "detection_performed": False,
        })
        with self._lock:
            self.quarantine.append(item)
        state = str(item["state"]).replace(" ", "_")
        self.metrics.inc(f"ingest.quarantine.{state}")
        block = self._seal("quarantine", item["event_id"] or "unknown-event",
                           f"quarantined {state}: {item['reason']}", item)
        item["ledger_seq"] = block["seq"]
        self._timeline_add("quarantine", state, ledger_seq=block["seq"],
                           ref=item["event_id"], detail=item["reason"])
        self.hub.publish_sync("quarantine", item)
        return item

    # -- detection / governance path -------------------------------------
    def _fuse(self, finding: dict[str, Any]) -> dict[str, Any]:
        key = (str(finding.get("campaign_id") or ""), str(finding.get("case_id") or ""))
        step = self._step()
        with self._lock:
            state = self.campaigns.get(key)
            if state is None:
                state = CampaignState(campaign_id=key[0], case_id=key[1], first_seen=step)
                self.campaigns[key] = state
            state.legs.add(str(finding.get("leg") or "infra"))
            state.organs.add(str(finding.get("organ") or ""))
            if finding.get("entity"):
                state.entities.add(str(finding["entity"]))
            state.detections.append(dict(finding))
            state.last_seen = step
            return state.to_dict()

    def _plan_and_decide(self, campaign: dict[str, Any]) -> list[dict[str, Any]]:
        if not campaign.get("fused"):
            return []
        campaign_id = str(campaign["campaign_id"])
        with self._lock:
            if campaign_id in self._plan_locked_campaigns:
                return []
            self._plan_locked_campaigns.add(campaign_id)
        fused_block = self._seal(
            "campaign_fused", f"FUSE-{campaign_id}",
            f"campaign {campaign_id} fused across {campaign['legs']} via opaque case token",
            {"case_id": campaign["case_id"], "legs": campaign["legs"],
             "organs": campaign["organs"]},
        )
        self.hub.publish_sync("campaign", {**campaign, "ledger_seq": fused_block["seq"]})
        results: list[dict[str, Any]] = []
        for proposal in self.planner.proposals_for(campaign):
            with self._lock:
                if proposal.proposal_id in self._decided:
                    continue
                self._decided.add(proposal.proposal_id)
            proposal_dict = proposal.to_dict()
            proposal_block = self._seal(
                "proposal", proposal.proposal_id, proposal.detail, proposal_dict,
            )
            proposal_dict["ledger_seq"] = proposal_block["seq"]
            self._timeline_add("proposal", proposal.action,
                               ledger_seq=proposal_block["seq"],
                               ref=proposal.proposal_id, detail=proposal.detail)
            self.hub.publish_sync("proposal", proposal_dict)

            decision = self.governor.decide(proposal)
            kind = "containment" if decision.verdict == VERDICT_ALLOWED else "refusal"
            decision_block = self._seal(
                kind, proposal.proposal_id,
                (f"Governor {decision.verdict}: {decision.reason}"),
                decision.to_dict(),
            )
            decision_dict = decision.to_dict()
            decision_dict["ledger_seq"] = decision_block["seq"]
            decision_dict["kind"] = kind
            self.metrics.inc(f"decide.{decision.verdict.lower()}")
            self._timeline_add("decision", kind, ledger_seq=decision_block["seq"],
                               ref=proposal.proposal_id, detail=decision.reason)
            execution = self.executor.execute(decision)
            self.metrics.inc("executor.simulated" if decision.verdict == VERDICT_ALLOWED
                             else "executor.skipped_refusal")
            self._timeline_add("execution", execution["status"],
                               ledger_seq=decision_block["seq"],
                               ref=proposal.proposal_id, detail=execution["reason"])
            # The decision is already sealed. Only now is it broadcast.
            self.hub.publish_sync("decision", {**decision_dict, "execution": execution})
            results.append({"proposal": proposal_dict, "decision": decision_dict,
                            "execution": execution})
        return results

    def process_event(self, raw: dict[str, Any], source: str = "sensor") -> dict[str, Any]:
        event_id = str(raw.get("event_id") or canonical_hash(raw)[:16])
        out: dict[str, Any] = {
            "event_id": event_id, "accepted": False, "verified": None,
            "reason": "", "quarantined": False, "detections": [],
            "proposals": [], "decisions": [], "executions": [],
            "contract": RUNTIME_CONTRACT_VERSION,
        }
        self.metrics.inc("ingest.received")
        if not self._allow(source):
            self.metrics.inc("ingest.rate_limited")
            out["reason"] = "rate limit exceeded for source"
            return {**out, "ledger_height": self.ledger.height()}
        if not self._mark_seen(event_id):
            self.metrics.inc("ingest.duplicate")
            out["reason"] = "duplicate event_id"
            return {**out, "ledger_height": self.ledger.height()}

        try:
            result = self._result_dict(self.detector(raw, key=self.sensor_key))
        except Exception as exc:
            result = {"status": "quarantined", "state": "detector_error",
                      "reason": f"detector failure is fail-closed: {exc}",
                      "quarantine": {"state": "detector_error"}}
        status = str(result.get("status") or "quarantined")
        state = str(result.get("state") or "unknown")
        reason = str(result.get("reason") or "")
        out["accepted"] = True
        out["verified"] = state

        if status in {"quarantined", "unknown_organ", "invalid_envelope"}:
            item = self._quarantine(raw, result, source)
            out.update({"quarantined": True, "reason": item["reason"],
                        "quarantine": item})
            return {**out, "ledger_height": self.ledger.height()}
        if status == "no_detection":
            self.metrics.inc("detect.benign")
            self._timeline_add("event", "verified_no_detection", ref=event_id,
                               detail=reason or "verified; no rule fired")
            self.hub.publish_sync("event", {"event_id": event_id,
                                            "organ": raw.get("organ"),
                                            "verified": True, "detection": False})
            out["reason"] = reason or "verified, no detection"
            return {**out, "ledger_height": self.ledger.height()}
        if status != "finding":
            item = self._quarantine(raw, {**result, "state": "unsupported_detector_status"}, source)
            out.update({"quarantined": True, "reason": item["reason"],
                        "quarantine": item})
            return {**out, "ledger_height": self.ledger.height()}

        finding = dict(result.get("finding") or {})
        detection = {**finding, "source": source}
        with self._lock:
            self.detections.append(detection)
        self.metrics.inc("ingest.verified")
        self.metrics.inc("detect.flagged")
        self._timeline_add("detection", str(finding.get("rule_id") or "finding"),
                           ref=event_id, detail=str(finding.get("reason") or ""))
        detection_block = self._seal(
            "detection", event_id,
            f"{finding.get('organ')} fired {finding.get('rule_id')}: {finding.get('reason')}",
            detection,
        )
        detection["ledger_seq"] = detection_block["seq"]
        out["detections"].append(detection)
        self.hub.publish_sync("detection", detection)
        campaign = self._fuse(finding)
        out["campaign"] = campaign
        planned = self._plan_and_decide(campaign)
        for item in planned:
            out["proposals"].append(item["proposal"])
            out["decisions"].append(item["decision"])
            out["executions"].append(item["execution"])
        out["reason"] = f"{finding.get('organ')} fired {finding.get('rule_id')}"
        return {**out, "ledger_height": self.ledger.height()}

    # -- snapshots --------------------------------------------------------
    def state_snapshot(self) -> dict[str, Any]:
        with self._lock:
            campaigns = [state.to_dict() for state in self.campaigns.values()]
            timeline = [dict(entry) for entry in self.timeline]
            detections = [dict(item) for item in self.detections]
            quarantine_count = len(self.quarantine)
        return {
            "app": "infra", "contract": SPINE_CONTRACT,
            "runtime_contract": RUNTIME_CONTRACT_VERSION,
            "dry_run": True, "model_backed": False, "deterministic": True,
            "commander": dict(self.commander),
            "campaigns": campaigns, "topology": self.topology.to_dict(),
            "detections": detections, "timeline": timeline,
            "quarantine_count": quarantine_count,
            "ledger_height": self.ledger.height(),
            "console_read_only": True,
        }

    def campaigns_snapshot(self) -> dict[str, Any]:
        state = self.state_snapshot()
        return {"campaigns": state["campaigns"], "ledger_height": state["ledger_height"]}

    def decisions_snapshot(self) -> dict[str, Any]:
        decisions = []
        for block in self.ledger.by_kind("containment", "refusal"):
            payload = dict(block["payload"])
            decisions.append({
                "seq": block["seq"], "ts": block["ts"], "kind": block["kind"],
                "ref": block["ref"], "text": block["text"],
                "ledger_seq": block["seq"], "verdict": payload.get("verdict"),
                "rule_id": payload.get("rule_id"),
                "fallback": payload.get("fallback_proposal_id"),
                "assets_severed": payload.get("assets_severed"),
                "dry_run": payload.get("dry_run", True),
                "admin_override": payload.get("admin_override", False),
            })
        return {"decisions": decisions, "count": len(decisions)}

    def quarantine_snapshot(self) -> dict[str, Any]:
        with self._lock:
            items = [dict(item) for item in self.quarantine]
        return {"items": items, "count": len(items)}

    def metrics_snapshot(self) -> dict[str, Any]:
        snap = self.metrics.snapshot()
        with self._lock:
            snap["store"] = {
                "detections": len(self.detections),
                "campaigns": len(self.campaigns),
                "quarantine": len(self.quarantine),
                "timeline": len(self.timeline),
                "decided_proposals": len(self._decided),
                "rate_limit_epm": self.rate_limit_epm,
            }
        snap["ledger_height"] = self.ledger.height()
        return snap

    # -- deterministic demo ----------------------------------------------
    def seed_demo(self) -> None:
        case = "CASE-P678-DEMO"
        campaign = "C-P678-DEMO"

        def raw(event_id: str, organ: str, leg: str, entity: str,
                payload: dict[str, Any], severity: int) -> dict[str, Any]:
            return {
                "event_id": event_id, "ts": f"2026-11-26T00:00:{len(event_id):02d}Z",
                "organ": organ, "campaign_id": campaign, "case_id": case,
                "leg": leg, "severity": severity, "entity": entity,
                "summary": f"phase 6-8 fixture {organ}", "payload": payload,
            }

        fixtures = [
            raw("EV-P678-CITIZEN", "cookie_fluid_turbulence", "citizen",
                "N-VICTIM-PHONE", {"reynolds_number": 3100.0, "cookie_replay_count": 3}, 4),
            raw("EV-P678-INFRA-1", "page_curve_trap", "infra",
                "HOST_APP_SRV_07", {"parity_break": 1, "encrypt_events_per_min": 512}, 5),
            raw("EV-P678-INFRA-2", "bragg_fft_firewall", "infra",
                "HOST_LAB_09", {"fft_peak_ratio": 0.88, "fiedler_value": 0.04}, 3),
        ]
        for item in fixtures:
            self.process_event(sign_event(item, key=self.sensor_key), source="demo-fixture")
        # Three first-class quarantine semantics: unsigned, tampered, forged.
        self.process_event(raw("EV-P678-UNSIGNED", "netguard", "infra", "HOST_042",
                               {"spectral_radius": 1.5}, 4), source="demo-fixture")
        tampered = sign_event(raw("EV-P678-TAMPERED", "fileguard", "infra", "HOST_042",
                                  {"parity_break": 1}, 4), key=self.sensor_key)
        tampered["severity"] = 1
        self.process_event(tampered, source="demo-fixture")
        forged = sign_event(raw("EV-P678-FORGED", "fileguard", "infra", "HOST_042",
                                {"parity_break": 1}, 4), key=b"wrong-forged-key")
        self.process_event(forged, source="demo-fixture")


def create_app(*, detector: Callable[..., Any], sensor_key: Any = None,
               token_records: Any = None, console_token: str | None = None,
               topology_path: str | None = None, policy_path: str | None = None,
               model: str | None = None, seed_demo: bool = True,
               rate_limit_epm: int = 600, blast_cap: int = 3) -> FastAPI:
    if detector is None:
        raise RuntimeError("one detector contract is required; no fallback detection path")
    tokens = list(token_records) if token_records is not None else _default_tokens()
    token_store = TokenStore.from_tokens(tokens)
    if console_token is None:
        console_token = next(
            (token for token, _name, scopes in token_store.plaintext
             if "read" in scopes and "admin" not in scopes),
            DEFAULT_OBSERVER_TOKEN,
        )
    if console_token not in {token for token, _name, _scopes in token_store.plaintext}:
        tokens.append((console_token, "console", ("read",)))
        token_store = TokenStore.from_tokens(tokens)
    runtime = SafetyRuntime(
        detector=detector, sensor_key=_coerce_key(sensor_key),
        token_store=token_store, topology_path=topology_path,
        policy_path=policy_path, rate_limit_epm=rate_limit_epm, blast_cap=blast_cap,
    )
    if seed_demo:
        runtime.seed_demo()

    app = FastAPI(
        title="RAKSHA Infra / Sentinel — unified Phase 6–8 backend",
        version="0.9.0-phase678",
        description="Signed telemetry, 8-organ detection, deterministic Governor, append-only ledger, WebSocket and read-only SOC console.",
    )
    app.state.runtime = runtime
    app.state.pipeline = runtime  # compatibility name; same object
    app.state.hub = runtime.hub
    app.state.token_store = token_store
    app.state.console_token = console_token
    app.state.policy_path = policy_path
    app.state.topology_path = str(topology_path or DEFAULT_TOPOLOGY)
    app.state.commander_model_requested = model or "disabled"
    app.state.model_backed = False

    def token_candidate(request: Request, *, allow_query: bool) -> tuple[str, str]:
        """Return one scoped token and its source.

        Preview proxies sometimes strip Authorization headers. The read cookie
        and a read-only query token keep the console navigable without ever
        widening write/admin scopes.
        """
        header = request.headers.get("authorization", "")
        if header.lower().startswith("bearer "):
            return header[7:].strip(), "header"
        header = request.headers.get("x-api-token", "").strip()
        if header:
            return header, "header"
        cookie = request.cookies.get("raksha_read_token", "").strip()
        if cookie:
            return cookie, "cookie"
        if allow_query:
            query = request.query_params.get("access_token", "").strip()
            if query:
                return query, "query"
        return "", "none"

    def auth(request: Request, scope: str, *, allow_query: bool = False) -> TokenRecord:
        candidate, source = token_candidate(request, allow_query=allow_query)
        record = token_store.authenticate(candidate)
        if source == "query":
            if (scope != "read" or "read" not in record.scopes
                    or "admin" in record.scopes
                    or "telemetry:write" in record.scopes):
                raise AuthError(
                    403,
                    "query token is read-only; use a scoped header or cookie",
                )
        TokenStore.authorize(record, scope)
        return record

    @app.exception_handler(AuthError)
    async def auth_error_handler(_request: Request, exc: AuthError) -> JSONResponse:
        return JSONResponse(status_code=exc.status,
                            content={"error": "auth", "detail": exc.detail})

    @app.exception_handler(EnvelopeValidationError)
    async def envelope_error_handler(_request: Request, exc: EnvelopeValidationError) -> JSONResponse:
        return JSONResponse(status_code=422,
                            content={"error": "invalid_envelope", "detail": str(exc)})

    @app.get("/healthz")
    @app.get("/api/health")
    def health() -> dict[str, Any]:
        return {"status": "ok", "version": RUNTIME_CONTRACT_VERSION,
                "contract": SPINE_CONTRACT, "dry_run": True,
                "model_backed": False, "deterministic": True,
                "commander": dict(runtime.commander)}

    @app.post("/v1/telemetry")
    @app.post("/api/ingest")
    def post_telemetry(request: Request, body: dict[str, Any]) -> dict[str, Any]:
        record = auth(request, "telemetry:write")
        return runtime.process_event(body, source=record.name)

    @app.get("/v1/state")
    @app.get("/api/state")
    def get_state(request: Request) -> dict[str, Any]:
        auth(request, "read", allow_query=True)
        return runtime.state_snapshot()

    @app.get("/v1/campaigns")
    @app.get("/api/orchestrate")
    @app.post("/api/orchestrate")
    @app.post("/v1/campaigns")
    def get_campaigns(request: Request) -> dict[str, Any]:
        auth(request, "read", allow_query=True)
        return runtime.campaigns_snapshot()

    @app.get("/v1/decisions")
    def get_decisions(request: Request) -> dict[str, Any]:
        auth(request, "read", allow_query=True)
        return runtime.decisions_snapshot()

    @app.post("/v1/decisions/{proposal_id}/override")
    def override_decision(request: Request, proposal_id: str) -> JSONResponse:
        record = auth(request, "admin")
        raise HTTPException(
            status_code=403,
            detail=(f"decisions are append-only; token {record.name!r} cannot override "
                    f"{proposal_id}. Submit a narrower proposal instead."),
        )

    @app.get("/v1/ledger/head")
    def ledger_head(request: Request) -> dict[str, Any]:
        auth(request, "read", allow_query=True)
        head = runtime.ledger.head()
        return {"height": runtime.ledger.height(), "head": head["hash"],
                "seq": head["seq"], "ts": head["ts"]}

    @app.get("/v1/ledger/verify")
    def ledger_verify(request: Request) -> dict[str, Any]:
        auth(request, "read", allow_query=True)
        return runtime.ledger.verify()

    @app.post("/v1/ledger/entries")
    def ledger_append(request: Request, body: dict[str, Any]) -> dict[str, Any]:
        record = auth(request, "admin")
        for field_name in ("kind", "ref", "text"):
            if not isinstance(body.get(field_name), str) or not body[field_name]:
                raise HTTPException(status_code=422, detail=f"missing {field_name!r}")
        return runtime.append_operator_note(body, actor=record.name)

    @app.get("/v1/quarantine")
    def quarantine(request: Request) -> dict[str, Any]:
        auth(request, "read", allow_query=True)
        return runtime.quarantine_snapshot()

    @app.get("/v1/metrics")
    def get_metrics(request: Request) -> dict[str, Any]:
        auth(request, "read", allow_query=True)
        return runtime.metrics_snapshot()

    @app.websocket("/v1/telemetry/stream")
    @app.websocket("/ws/telemetry")
    async def stream(ws: WebSocket, token: str = "") -> None:
        try:
            record = token_store.authenticate(token)
            TokenStore.authorize(record, "read")
        except AuthError:
            await ws.close(code=4401)
            return
        await ws.accept()
        runtime.hub.attach_loop(asyncio.get_running_loop())
        queue = runtime.hub.subscribe()
        try:
            for item in runtime.hub.history():
                await ws.send_json(item)
            while True:
                await ws.send_json(await queue.get())
        except WebSocketDisconnect:
            pass
        finally:
            runtime.hub.unsubscribe(queue)

    return app


__all__ = [
    "RUNTIME_CONTRACT_VERSION", "AuthError", "TokenRecord", "TokenStore",
    "Metrics", "Hub", "CampaignState", "SafetyRuntime", "create_app",
]
