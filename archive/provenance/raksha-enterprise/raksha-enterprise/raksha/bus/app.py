"""FastAPI application factory: the telemetry bus and observability API.

Surface (all JSON, no UI):
  GET  /healthz                              liveness (no auth)
  POST /v1/telemetry          telemetry:write  ingest one signed envelope
  GET  /v1/state              read           campaigns + topology + detections
  GET  /v1/campaigns          read           fused campaign list
  GET  /v1/decisions          read           ledger decisions incl. refusals
  POST /v1/decisions/{id}/override  admin    ALWAYS 403 — decisions are append-only
  GET  /v1/ledger/head        read           chain head + height
  GET  /v1/ledger/verify      read           recompute the whole chain
  POST /v1/ledger/entries     admin          operator note (hashed, append-only)
  GET  /v1/quarantine         read           tampered/unsigned events (never actionable)
  GET  /v1/metrics            read           counters + stage latency p50/p95
  WS   /v1/telemetry/stream   read           verified events, detections, decisions
"""

from __future__ import annotations

import asyncio
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse

from .. import __version__
from ..bootstrap import seed_api_tokens
from ..config import Settings, ensure_dirs, load_or_create_sensor_key, load_settings
from ..events import Event, EventValidationError
from ..ledger import LedgerStore
from ..logging_setup import setup_logging
from ..metrics import Metrics
from ..pipeline import Pipeline
from ..storage import EventStore
from .auth import AuthError, TokenStore


class Hub:
    """Fan-out for WebSocket subscribers; safe to publish from worker threads.

    The loop is re-attached on every subscription: test portals and some ASGI
    servers run each connection on a fresh event loop, so a loop captured at
    startup can go stale. Publishing to a closed loop is swallowed — dead
    sockets must never break the pipeline. Counters expose the fan-out path
    through /v1/metrics (ws.*) so a silent broadcast is diagnosable in prod.
    """

    def __init__(self, metrics: Metrics | None = None) -> None:
        self._clients: set[asyncio.Queue] = set()
        self._loop: asyncio.AbstractEventLoop | None = None
        self._metrics = metrics

    def _inc(self, name: str) -> None:
        if self._metrics is not None:
            self._metrics.inc(name)

    def attach_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop

    def subscribe(self) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue(maxsize=512)
        self._clients.add(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue) -> None:
        self._clients.discard(queue)

    def publish_sync(self, kind: str, data: dict[str, Any]) -> None:
        item = {"kind": kind, "data": data}
        self._inc("ws.publish_calls")

        def _fanout() -> None:
            for queue in list(self._clients):
                try:
                    queue.put_nowait(item)
                    self._inc("ws.delivered")
                except asyncio.QueueFull:
                    self._inc("ws.dropped_slow_consumer")

        if self._loop is None:
            self._inc("ws.no_loop")
            return
        try:
            self._loop.call_soon_threadsafe(_fanout)
        except RuntimeError:
            self._inc("ws.loop_closed")


def create_app(
    settings: Settings | None = None,
    *,
    pipeline: Pipeline | None = None,
    ledger: LedgerStore | None = None,
    store: EventStore | None = None,
    sensor_key: bytes | None = None,
    metrics: Metrics | None = None,
    token_store: TokenStore | None = None,
    auto_seed: bool = True,
) -> FastAPI:
    settings = settings or load_settings()
    ensure_dirs(settings)
    setup_logging(settings.log_level)
    if auto_seed and not settings.api_tokens_path.exists():
        seed_api_tokens(settings)

    store = store or EventStore(settings.events_db_path)
    ledger = ledger or LedgerStore(settings.ledger_db_path)
    metrics = metrics or Metrics()
    sensor_key = sensor_key or load_or_create_sensor_key(settings)
    hub = Hub(metrics=metrics)
    if pipeline is None:
        pipeline = Pipeline(settings, sensor_key, ledger, store, metrics, notifier=hub.publish_sync)
    else:
        # Wire an injected pipeline (tests, embedded embedding) to the hub too,
        # so WebSocket subscribers see its detections and decisions.
        pipeline.notifier = hub.publish_sync
    token_store = token_store or TokenStore.load(settings.api_tokens_path)

    app = FastAPI(
        title="Project Raksha — Part 6 backend",
        version=__version__,
        description="Signed telemetry pipeline, organ detection, campaign fusion, "
                    "Governor decisions (incl. refusals), append-only ledger. "
                    "The console observes; it never overrides.",
    )
    app.state.hub = hub
    app.state.pipeline = pipeline

    # -- auth helpers --------------------------------------------------------
    def bearer_token(request: Request) -> str:
        header = request.headers.get("authorization", "")
        if header.lower().startswith("bearer "):
            return header[7:].strip()
        token = request.headers.get("x-api-token", "").strip()
        if token:
            return token
        raise AuthError(401, "missing API token (Authorization: Bearer ... or X-API-Token)")

    def auth(request: Request, scope: str) -> Any:
        record = token_store.authenticate(bearer_token(request))
        TokenStore.authorize(record, scope)
        return record

    @app.exception_handler(AuthError)
    async def auth_error_handler(_request: Request, exc: AuthError) -> JSONResponse:
        return JSONResponse(status_code=exc.status, content={"error": "auth", "detail": exc.detail})

    @app.exception_handler(EventValidationError)
    async def envelope_error_handler(_request: Request, exc: EventValidationError) -> JSONResponse:
        return JSONResponse(status_code=422, content={"error": "invalid_envelope", "detail": str(exc)})

    # -- routes --------------------------------------------------------------
    @app.get("/healthz")
    def healthz() -> dict:
        return {"status": "ok", "version": __version__}

    @app.post("/v1/telemetry")
    def post_telemetry(request: Request, body: dict) -> dict:
        auth(request, "telemetry:write")
        event = Event.from_dict(body)
        source = auth_record.name if (auth_record := _quiet_auth(token_store, bearer_token(request))) else "sensor"
        return pipeline.process(event, source=source)

    @app.get("/v1/state")
    def get_state(request: Request) -> dict:
        auth(request, "read")
        return pipeline.state_snapshot()

    @app.get("/v1/campaigns")
    def get_campaigns(request: Request) -> dict:
        auth(request, "read")
        return {"campaigns": [c.to_dict() for c in pipeline.fusion.all()]}

    @app.get("/v1/decisions")
    def get_decisions(request: Request) -> dict:
        auth(request, "read")
        blocks = ledger.by_kind("containment", "refusal")
        return {"decisions": [
            {"seq": b["seq"], "ts": b["ts"], "kind": b["kind"], "ref": b["ref"],
             "text": b["text"], "verdict": b["payload"].get("verdict"),
             "rule_id": b["payload"].get("rule_id"),
             "fallback": b["payload"].get("fallback_proposal_id"),
             "assets_severed": b["payload"].get("assets_severed")}
            for b in blocks
        ]}

    @app.post("/v1/decisions/{proposal_id}/override")
    def override_decision(request: Request, proposal_id: str) -> JSONResponse:
        record = auth(request, "admin")
        # Contract R6: append-only. Even admin cannot overturn a decision; the
        # correct move is a new, narrower proposal through the planner.
        raise HTTPException(
            status_code=403,
            detail=(f"decisions are append-only; token {record.name!r} cannot override "
                    f"{proposal_id}. Submit a narrower proposal instead."),
        )

    @app.get("/v1/ledger/head")
    def ledger_head(request: Request) -> dict:
        auth(request, "read")
        head = ledger.head()
        return {"height": ledger.height(), "head": head["hash"], "seq": head["seq"], "ts": head["ts"]}

    @app.get("/v1/ledger/verify")
    def ledger_verify(request: Request) -> dict:
        auth(request, "read")
        report = ledger.verify()
        return {"ok": report.ok, "height": report.height, "head": report.head[:16],
                "first_bad_seq": report.first_bad_seq, "reason": report.reason}

    @app.post("/v1/ledger/entries")
    def ledger_append(request: Request, body: dict) -> dict:
        auth(request, "admin")
        for field in ("kind", "ref", "text"):
            if not isinstance(body.get(field), str) or not body[field]:
                raise HTTPException(status_code=422, detail=f"missing {field!r}")
        block = ledger.append(kind=body["kind"], ref=body["ref"], text=body["text"],
                              payload=body.get("payload") or {})
        return block

    @app.get("/v1/quarantine")
    def quarantine(request: Request) -> dict:
        auth(request, "read")
        return {"items": store.list_quarantined()}

    @app.get("/v1/metrics")
    def get_metrics(request: Request) -> dict:
        auth(request, "read")
        snap = metrics.snapshot()
        snap["store"] = store.counts()
        return snap

    @app.websocket("/v1/telemetry/stream")
    async def stream(ws: WebSocket, token: str = "") -> None:
        try:
            record = token_store.authenticate(token)
            TokenStore.authorize(record, "read")
        except AuthError as exc:
            await ws.close(code=4401)
            return
        await ws.accept()
        # Attach the CURRENT loop: each connection may run on its own loop.
        hub.attach_loop(asyncio.get_running_loop())
        queue = hub.subscribe()
        try:
            await ws.send_json({"kind": "hello", "data": {"version": __version__,
                                                          "ledger_height": ledger.height()}})
            while True:
                item = await queue.get()
                await ws.send_json(item)
        except WebSocketDisconnect:
            pass
        finally:
            hub.unsubscribe(queue)

    return app


def _quiet_auth(token_store: TokenStore, token: str):
    try:
        return token_store.authenticate(token)
    except AuthError:
        return None
