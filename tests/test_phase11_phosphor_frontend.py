"""Phase 11: the Phosphor console is a served surface of the active apps.

These tests boot the Infra app in-process and assert the two properties that
were wrong before the integration: a deep link must serve its own prerendered
document (not the client shell), and every gateway view must report only what
the deterministic runtime actually measured.  The end-to-end HTTP behaviour of
both apps — including the Citizen report forward and the three-act replay — is
covered by ``tools/run_frontend_smoke.py``; the static path contract is covered
by ``tools/check_frontend_integration.py``.
"""
from __future__ import annotations

import json
import socket
from pathlib import Path

from fastapi.testclient import TestClient

from apps.infra.backend.app import create_app
from packages.frontend import FRONTEND_BUILD_DIR, FRONTEND_CONTRACT_VERSION

ROOT = Path(__file__).resolve().parents[1]
READ_TOKEN = "phosphor-test-read-token"


def _client() -> TestClient:
    app = create_app(
        sensor_key=b"phosphor-test-ingest-key",
        token_records=[(READ_TOKEN, "console", ("admin", "read", "telemetry:write"))],
        console_token=READ_TOKEN,
        seed_demo=False,
    )
    return TestClient(app)


def test_both_manifests_make_the_console_the_default_ui() -> None:
    for name, route in (("citizen", "/console/call-screen"), ("infra", "/console/rings")):
        manifest = json.loads((ROOT / "apps" / name / "BOOT_MANIFEST.json").read_text(encoding="utf-8"))
        assert manifest["root_redirect"] == route, name
        assert manifest["frontend_contract"] == FRONTEND_CONTRACT_VERSION, name
        assert manifest["frontend_health_path"] == "/api/frontend/health", name


def test_deep_links_serve_their_own_document_not_the_shell() -> None:
    client = _client()
    root = client.get("/", follow_redirects=False)
    assert root.status_code == 307
    assert root.headers["location"] == "/console/rings"

    shell = (FRONTEND_BUILD_DIR / "index.html").read_bytes()
    for route in ("rings", "governance", "red-team", "call-screen", "message-guard",
                  "citizen-spine", "vigil", "attack-lab"):
        page = client.get(f"/console/{route}/")
        assert page.status_code == 200, route
        expected = (FRONTEND_BUILD_DIR / "console" / route / "index.html").read_bytes()
        assert page.content == expected, f"/console/{route}/ is not its own prerender"
        assert page.content != shell, f"/console/{route}/ served the landing shell"
        assert page.headers["cache-control"] == "no-store"
        assert "ARK OMNITEK" in page.text


def _closed_port() -> int:
    """A port nothing is listening on, so an unreachable backend is reproducible."""
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return int(probe.getsockname()[1])


def test_gateway_errors_are_structured_and_invent_nothing(monkeypatch) -> None:
    """An unreachable backend must surface as a structured 502, never a placeholder.

    The console talks to the apps over their internal URLs. Pinning the Infra URL
    to a closed port keeps this deterministic even when `./start.sh` has a real
    stack listening on the default port — the gateway has to answer 502 with an
    error envelope instead of dressing up a fallback payload as state. The HTTP
    smoke boots real servers and asserts the successful shape of every view.
    """
    monkeypatch.setenv("RAKSHA_INFRA_INTERNAL_URL", f"http://127.0.0.1:{_closed_port()}")
    client = _client()
    missing = client.get("/api/definitely-not-a-route")
    assert missing.status_code == 404
    assert missing.headers["content-type"].startswith("application/json")
    assert "<html" not in missing.text.lower()
    assert client.get("/console/not-a-real-app").status_code == 200  # SPA fallback

    for path in ("state", "fleet", "orchestrate", "containment", "health"):
        res = client.get(f"/api/gateway/spine/api/{path}")
        assert res.status_code == 502, path
        body = res.json()
        assert body["ok"] is False and body["error"], path
        for invented in ("planes_3_4", "campaigns", "organs", "risk_score", "confidence"):
            assert invented not in body, f"{path} synthesised {invented}"


def test_organ_control_is_refused_locally_without_touching_the_bus(monkeypatch) -> None:
    monkeypatch.setenv("RAKSHA_INFRA_INTERNAL_URL", f"http://127.0.0.1:{_closed_port()}")
    client = _client()
    for action in ("halt", "resume"):
        res = client.post(f"/api/gateway/spine/api/fleet/bec_spectral_filter/{action}")
        assert res.status_code == 200, action
        body = res.json()
        assert body["status"] == "DRY_RUN_ONLY", action
        assert body["real_action_count"] == 0 and body["organ"] == "bec_spectral_filter"
        assert "disabled" in body["reason"].lower()


def test_apps_self_address_their_console_gateway(monkeypatch) -> None:
    """``--port`` must move the gateway's internal URL with it.

    Both apps proxy console routes back into their own process, so a run on a
    non-default port cannot leave the browser talking to the packaged default.
    """
    from apps.citizen import api as citizen_api
    from apps.infra.backend import app as infra_app

    cases = ((infra_app, "RAKSHA_INFRA_INTERNAL_URL", ["--port", "39871", "--no-seed-demo"]),
             (citizen_api, "RAKSHA_CITIZEN_INTERNAL_URL", ["--port", "39872"]))
    for module, var, argv in cases:
        monkeypatch.delenv(var, raising=False)
        seen: list[str] = []
        monkeypatch.setattr("uvicorn.run", lambda *_a, **_k: seen.append(module.os.environ.get(var, "")))
        module.main(argv)
        expected = {"RAKSHA_INFRA_INTERNAL_URL": "http://127.0.0.1:39871",
                    "RAKSHA_CITIZEN_INTERNAL_URL": "http://127.0.0.1:39872"}[var]
        assert seen == [expected], var
        # `main` wrote the variable, so clear it here rather than recording the
        # polluted value as the thing to restore: the `delenv` above already holds
        # the pristine state, and a later test in the same process must not read a
        # leftover 39871-style port as if an operator had set it.
        module.os.environ.pop(var, None)
