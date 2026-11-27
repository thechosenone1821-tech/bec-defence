"""Compatibility-cwd Citizen tests for the active VIGIL build."""
from __future__ import annotations

import sys
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / "raksha-code")]

from apps.citizen import copy as citizen_copy  # noqa: E402
from apps.citizen import features  # noqa: E402
from apps.citizen.api import build_app  # noqa: E402
from packages.contracts.i18n import CitizenRenderer  # noqa: E402


def test_app_copy_owns_citizen_sentences():
    assert citizen_copy.CONTRACT_VERSION.startswith("raksha-citizen-i18n-")
    assert "disclaimer" in citizen_copy.CITIZEN_COPY
    assert "message_verdict" in citizen_copy.CITIZEN_COPY
    renderer = CitizenRenderer(citizen_copy.CITIZEN_COPY)
    assert callable(renderer.explain_message)


def test_active_features_and_health_are_model_backed():
    assert features.MODEL_BACKED is True
    assert features.ACTIVE_MODEL == "VIGIL PrivacyNet TorchScript"
    assert features.FEATURE_FLAGS["vigil"] is True
    assert features.FEATURE_FLAGS["commander_model"] is False
    client = TestClient(build_app(bus_url=""))
    health = client.get("/api/citizen/health").json()
    assert health["model_backed"] is True
    assert health["vigil"]["enabled"] is True
    assert client.get("/vigil/", follow_redirects=False).status_code == 200
    assert client.get("/vigil/static/app.js").status_code == 200
