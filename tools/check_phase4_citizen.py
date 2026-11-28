#!/usr/bin/env python3
"""Active Citizen checker: one service, one console, one mounted VIGIL runtime.

The Phosphor console is the Citizen app's default UI and the legacy PWA stays
mounted as a compatibility surface; this checker asserts both, plus the VIGIL
runtime and the transcript screen the console calls.
"""
from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "raksha-code")]

from fastapi.testclient import TestClient  # noqa: E402
from apps.citizen import features  # noqa: E402
from apps.citizen.api import build_app  # noqa: E402
from packages.vigil.config import DEFAULT_WEIGHTS_CANDIDATES  # noqa: E402
from tools.check_vigil_assets import main as check_weight_assets  # noqa: E402


def check(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def main(argv: list[str] | None = None) -> int:
    try:
        check(features.MODEL_BACKED is True, "Citizen lost its active model status")
        check(features.PHASE == 11, "Citizen phase changed")
        check(features.ACTIVE_MODEL == "VIGIL PrivacyNet TorchScript", "active model changed")
        check(features.FEATURE_FLAGS["vigil"] is True, "VIGIL feature flag is disabled")
        check(features.FEATURE_FLAGS["commander_model"] is False, "Commander flag must stay disabled")
        card = features.vigil_card()
        check(card["enabled"] is True and card["route"] == "/vigil/", "VIGIL card changed")
        check(card["privacy_efficacy"] == "UNMEASURED", "privacy efficacy must stay UNMEASURED")
        check(check_weight_assets([]) == 0, "active weight artifacts did not verify")
        check(DEFAULT_WEIGHTS_CANDIDATES[0].name == "cloakpixel_privacynet_384.torchscript.pt",
              "runtime weight preference changed")

        app = build_app(bus_url="", poster=lambda event: {"accepted": 1})
        client = TestClient(app)
        health = client.get("/api/citizen/health")
        check(health.status_code == 200, "Citizen health route failed")
        body = health.json()
        check(body["model_backed"] is True, "Citizen health lost active model status")
        check(body["active_model"] == features.ACTIVE_MODEL, "Citizen health active model changed")
        check(body["vigil"]["enabled"] is True, "Citizen health VIGIL card disabled")
        check(client.get("/api/citizen/features").status_code == 200, "Citizen features route failed")
        check(client.get("/api/citizen/capabilities").status_code == 200, "Citizen capability card failed")
        root = client.get("/", follow_redirects=False)
        check(root.status_code == 307 and root.headers.get("location") == "/console/call-screen",
              "Citizen root must open the Phosphor console")
        frontend_health = client.get("/api/frontend/health")
        check(frontend_health.status_code == 200 and frontend_health.json()["static_build"] is True,
              "Citizen is not serving a built Phosphor bundle")
        console = client.get("/console/call-screen/")
        check(console.status_code == 200 and "ARK OMNITEK" in console.text,
              "Citizen did not serve the Call Screen console page")
        screened = client.post("/api/citizen/screen_message",
                               json={"text": "Share the OTP and pay the verification fee by UPI now.",
                                     "lang": "en"})
        check(screened.status_code == 200 and screened.json()["verdict"] in
              {"MODERATE", "HIGH", "CRITICAL"},
              "Citizen transcript screen stopped flagging a known scam script")
        check(client.get("/app/manifest.json").status_code == 200,
              "legacy Citizen PWA manifest stopped serving")
        check(client.get("/vigil/", follow_redirects=False).status_code == 200, "VIGIL dashboard failed")
        check(client.get("/vigil/static/app.js").status_code == 200, "VIGIL static assets failed")
        overview = client.get("/vigil/api/overview")
        check(overview.status_code == 200, "VIGIL overview failed")
        check(overview.json()["model_status"]["is_neural_active"] is True,
              "VIGIL neural weights are not active")
        status = client.get(features.VIGIL_STATUS_PATH)
        check(status.status_code == 200, "Citizen VIGIL status endpoint failed")
        check(status.json()["model_status"]["is_neural_active"] is True,
              "Citizen VIGIL status endpoint lost neural weights")
        check(status.json()["privacy_efficacy"] == "UNMEASURED",
              "Citizen VIGIL status endpoint lost honest efficacy label")
        check(status.json()["vigil"]["status_path"] == features.VIGIL_STATUS_PATH,
              "Citizen VIGIL status endpoint lost its status path")
        check(app.state.model_backed is True, "Citizen app state lost active model")
        check(app.state.vigil_integrated is True, "Citizen app state lost VIGIL integration")
        check(app.state.vigil_status_path == features.VIGIL_STATUS_PATH,
              "Citizen app state lost VIGIL status path")
    except Exception as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    print("OK: one Citizen service hosts active VIGIL weights and honest model status")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
