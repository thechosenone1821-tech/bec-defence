"""Root-level active Citizen and VIGIL acceptance checks."""
from __future__ import annotations

import sys
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "raksha-code")]

from apps.citizen import features  # noqa: E402
from apps.citizen.api import build_app  # noqa: E402
from tools import check_phase4_citizen  # noqa: E402


def test_citizen_checker_is_green():
    assert check_phase4_citizen.main([]) == 0


def test_active_citizen_reports_model_backed_vigil():
    assert features.MODEL_BACKED is True
    assert features.ACTIVE_MODEL == "VIGIL PrivacyNet TorchScript"
    assert features.vigil_card()["enabled"] is True
    assert features.vigil_card()["status_path"] == features.VIGIL_STATUS_PATH
    app = build_app(bus_url="")
    client = TestClient(app)
    health = client.get("/api/citizen/health").json()
    assert health["model_backed"] is True
    assert health["vigil"]["enabled"] is True
    assert health["vigil_status_path"] == features.VIGIL_STATUS_PATH
    assert app.state.model_backed is True
    assert app.state.vigil_integrated is True
    assert client.get("/vigil/", follow_redirects=False).status_code == 200
    overview = client.get("/vigil/api/overview")
    assert overview.status_code == 200
    assert overview.json()["model_status"]["is_neural_active"] is True
    status = client.get(features.VIGIL_STATUS_PATH)
    assert status.status_code == 200
    assert status.json()["model_status"]["is_neural_active"] is True
    assert status.json()["privacy_efficacy"] == "UNMEASURED"
