"""Shared pytest fixtures: a fully wired pipeline + TestClient on tmp state."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from raksha.bus import TokenStore, create_app
from raksha.config import Settings
from raksha.events import Event, sign_event
from raksha.ledger import LedgerStore
from raksha.metrics import Metrics
from raksha.pipeline import Pipeline
from raksha.storage import EventStore

SENSOR_KEY = b"raksha-test-sensor-key-0123456789ab"
ADMIN_TOKEN = "admin-test-token"
SENSOR_TOKEN = "sensor-test-token"
OBSERVER_TOKEN = "observer-test-token"


def _write_tokens(tmp_path: Path) -> Path:
    path = tmp_path / "keys" / "api_tokens.toml"
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = []
    for name, token, scopes in (
        ("admin", ADMIN_TOKEN, ["admin", "read", "telemetry:write"]),
        ("sensor-1", SENSOR_TOKEN, ["telemetry:write"]),
        ("observer", OBSERVER_TOKEN, ["read"]),
    ):
        digest = hashlib.sha256(token.encode()).hexdigest()
        lines += [f"[[token]]", f'name = "{name}"', f'hash = "{digest}"',
                  f"scopes = {scopes!r}", ""]
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(data_dir=tmp_path, log_level="ERROR", rate_limit_epm=600)


@pytest.fixture
def components(settings: Settings) -> dict:
    return {
        "store": EventStore(settings.events_db_path),
        "ledger": LedgerStore(settings.ledger_db_path),
        "metrics": Metrics(),
    }


@pytest.fixture
def pipeline(settings: Settings, components: dict) -> Pipeline:
    return Pipeline(settings, SENSOR_KEY, components["ledger"], components["store"],
                    components["metrics"])


@pytest.fixture
def client(settings: Settings, components: dict, pipeline: Pipeline) -> TestClient:
    token_path = _write_tokens(settings.data_dir)
    app = create_app(
        settings, pipeline=pipeline, ledger=components["ledger"], store=components["store"],
        sensor_key=SENSOR_KEY, metrics=components["metrics"],
        token_store=TokenStore.load(token_path), auto_seed=False,
    )
    with TestClient(app) as c:
        yield c


def make_event(event_id: str = "EV-T-1", organ: str = "voiceguard", leg: str = "citizen",
               entity: str = "N-VICTIM-PHONE", payload: dict | None = None,
               campaign: str = "C-TEST", case: str = "case-test", severity: int = 4) -> Event:
    payload = payload or {"synth_score": 0.93, "caller_reputation": 0.11}
    return Event(event_id, "2026-11-26T09:03:30Z", organ, campaign, case, leg,
                 severity, entity, "test event summary", payload)


def signed_event(**kwargs) -> Event:
    event = make_event(**kwargs)
    sign_event(event, SENSOR_KEY)
    return event
