#!/usr/bin/env python3
"""Boot-manifest gate: exactly two apps, active Citizen VIGIL, dry-run Infra."""
from __future__ import annotations

import json
import pathlib
import sys
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "raksha-code")]

from fastapi.testclient import TestClient  # noqa: E402
from apps.citizen.api import build_app as build_citizen_app  # noqa: E402
from apps.infra import features as infra_features  # noqa: E402
from apps.infra.backend.app import create_app as create_infra_app  # noqa: E402
from apps.infra.console import console_card  # noqa: E402

APPS = ROOT / "apps"
REQUIRED = (
    "contract", "app", "app_count", "entrypoint", "default_port", "bind",
    "root_redirect", "health_path", "model_backed", "active_model",
    "vigil_integrated", "executor",
)


def _phosphor_checks(client, manifest, label: str, route: str) -> None:
    """The Phosphor console is the default UI of both apps, not an extra app."""
    from packages.frontend import FRONTEND_CONTRACT_VERSION  # local: keeps import cost at call time

    root = client.get("/", follow_redirects=False)
    check(root.status_code == 307 and root.headers.get("location") == manifest["root_redirect"],
          f"{label} root must redirect to the Phosphor console route in its manifest")
    check(manifest.get("frontend_contract") == FRONTEND_CONTRACT_VERSION,
          f"{label} manifest does not pin the active frontend contract")
    check(manifest.get("frontend_health_path") == "/api/frontend/health",
          f"{label} manifest must publish the frontend health path")
    health = client.get("/api/frontend/health")
    check(health.status_code == 200, f"{label} frontend health route did not boot")
    body = health.json()
    check(body["contract"] == FRONTEND_CONTRACT_VERSION and body["static_build"] is True,
          f"{label} is not serving a built Phosphor bundle")
    check(body["service"] == manifest["app"], f"{label} frontend health names the wrong service")
    page = client.get(f"{route}/")
    check(page.status_code == 200 and "ARK OMNITEK" in page.text,
          f"{label} did not serve the Phosphor console at {route}")
    missing = client.get("/api/definitely-not-a-route")
    check(missing.status_code == 404,
          f"{label} must answer an unknown api path with a 404, not the SPA shell")



def check(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def main(argv: list[str] | None = None) -> int:
    try:
        app_dirs = sorted(p for p in APPS.iterdir() if p.is_dir() and p.name != "__pycache__")
        check([p.name for p in app_dirs] == ["citizen", "infra"],
              f"exactly two app roots required, found {[p.name for p in app_dirs]}")
        manifests: dict[str, dict[str, Any]] = {}
        for app_dir in app_dirs:
            path = app_dir / "BOOT_MANIFEST.json"
            check(path.is_file(), f"missing boot manifest: {path}")
            manifest = json.loads(path.read_text(encoding="utf-8"))
            check(all(key in manifest for key in REQUIRED),
                  f"incomplete boot manifest: {path}")
            check(manifest["contract"] == "raksha-boot-manifest-v2",
                  f"wrong boot manifest contract: {path}")
            check(manifest["app"] == app_dir.name and manifest["app_count"] == 2,
                  f"boot manifest app identity mismatch: {path}")
            check(manifest["bind"] == "0.0.0.0", f"manifest must bind all interfaces: {path}")
            manifests[app_dir.name] = manifest

        citizen_manifest = manifests["citizen"]
        infra_manifest = manifests["infra"]
        check(citizen_manifest["model_backed"] is True, "Citizen manifest must report an active model")
        check(citizen_manifest["active_model"] == "VIGIL PrivacyNet TorchScript",
              "Citizen manifest active model changed")
        check(citizen_manifest["vigil_integrated"] is True and citizen_manifest["vigil_route"] == "/vigil/",
              "Citizen manifest must expose the VIGIL route")
        check((ROOT / citizen_manifest["weights_manifest"]).is_file(),
              "Citizen weights manifest is missing")
        check(citizen_manifest["executor"] == "none", "Citizen must not declare an Infra executor")
        check(infra_manifest["model_backed"] is False and infra_manifest["deterministic"] is True,
              "Infra manifest must stay deterministic")
        check(infra_manifest["vigil_integrated"] is False, "VIGIL must not become an Infra service")
        check(infra_manifest["executor"] == "DryRunExecutor-v1" and infra_manifest["executor_mode"] == "dry-run",
              "Infra executor must stay dry-run")
        check(infra_manifest.get("status_path") == infra_features.STATUS_PATH,
              "Infra manifest missing owned status path")
        check(infra_manifest.get("capabilities_path") == infra_features.CAPABILITIES_PATH,
              "Infra manifest missing capabilities path")
        check(infra_manifest.get("detectors_path") == infra_features.DETECTORS_PATH,
              "Infra manifest missing detector-card path")
        check(infra_manifest.get("console_path") == infra_features.CONSOLE_PATH,
              "Infra manifest missing console path")
        check(infra_manifest.get("infra_ready") is True,
              "Infra manifest does not mark the app complete")
        check(infra_manifest.get("commander_enabled") is False,
              "Infra manifest unexpectedly enabled Commander")
        check(infra_manifest.get("fake_hospital_demo") is True
              and infra_manifest.get("functional_demo") is True,
              "Infra manifest missing functional fake-hospital demo")
        check(infra_manifest.get("demo_isolated_runtime") is True
              and infra_manifest.get("demo_real_action_count") == 0,
              "Infra demo must stay isolated and dry-run")
        check(infra_manifest.get("hospital_demo_path") == infra_features.HOSPITAL_DEMO_PATH,
              "Infra manifest missing fake-hospital demo UI path")
        check(infra_manifest.get("hospital_state_path") == infra_features.HOSPITAL_STATE_PATH,
              "Infra manifest missing fake-hospital demo state path")
        check(infra_manifest.get("hospital_step_path") == infra_features.HOSPITAL_STEP_PATH,
              "Infra manifest missing fake-hospital demo step path")
        check(console_card()["contract"] == "raksha-readonly-console-v2",
              "completed console contract changed")

        citizen = build_citizen_app(bus_url="", poster=lambda event: {"accepted": 1})
        citizen_client = TestClient(citizen)
        check(citizen.state.model_backed is True, "Citizen app state lost active model")
        check(citizen.state.vigil_integrated is True, "Citizen app state lost VIGIL integration")
        check(citizen.state.vigil_status_path == "/api/citizen/vigil/status",
              "Citizen app state VIGIL status path changed")
        check(citizen_manifest.get("vigil_status_path") == "/api/citizen/vigil/status",
              "Citizen manifest missing VIGIL status path")
        health = citizen_client.get(citizen_manifest["health_path"])
        check(health.status_code == 200, "Citizen health route did not boot")
        health_body = health.json()
        check(health_body["model_backed"] is True, "Citizen did not report an active model")
        check(health_body["active_model"] == "VIGIL PrivacyNet TorchScript",
              "Citizen active model changed")
        check(health_body["vigil"]["enabled"] is True, "Citizen VIGIL card disabled")
        _phosphor_checks(citizen_client, citizen_manifest, "Citizen",
                         citizen_manifest["root_redirect"])
        check(citizen_client.get(citizen_manifest["manifest_path"]).status_code == 200,
              "Citizen manifest route did not boot")
        check(citizen_client.get("/vigil/", follow_redirects=False).status_code == 200,
              "VIGIL dashboard did not boot under Citizen")
        overview = citizen_client.get("/vigil/api/overview")
        check(overview.status_code == 200 and overview.json()["model_status"]["is_neural_active"] is True,
              "VIGIL neural weights are not active")
        check(citizen_client.get("/vigil/static/app.js").status_code == 200,
              "VIGIL static assets are not mounted")
        status = citizen_client.get(citizen_manifest["vigil_status_path"])
        check(status.status_code == 200 and status.json()["model_status"]["is_neural_active"] is True,
              "Citizen VIGIL status endpoint did not report neural weights")

        infra = create_infra_app(
            sensor_key=b"boot-manifest-checker-key",
            token_records=[
                ("boot-admin", "admin", ("admin", "read", "telemetry:write")),
                ("boot-sensor", "sensor", ("telemetry:write",)),
                ("boot-observer", "observer", ("read",)),
            ],
            console_token="boot-observer",
            seed_demo=False,
        )
        infra_client = TestClient(infra)
        check(infra_client.get(infra_manifest["health_path"]).status_code == 200,
              "Infra health route did not boot")
        _phosphor_checks(infra_client, infra_manifest, "Infra",
                         infra_manifest["root_redirect"])
        check(infra_client.get(infra_manifest["state_path"],
                               headers={"X-API-Token": "boot-observer"}).status_code == 200,
              "Infra state route did not boot")
        check(infra_client.get("/app/contract").status_code == 200,
              "Infra contract route did not boot")
        status = infra_client.get(infra_manifest["status_path"])
        check(status.status_code == 200 and status.json()["ready"] is True,
              "Infra owned status endpoint did not boot")
        check(infra_client.get(infra_manifest["capabilities_path"]).status_code == 200,
              "Infra capabilities endpoint did not boot")
        check(infra_client.get(infra_manifest["detectors_path"]).status_code == 200,
              "Infra detector-card endpoint did not boot")
        check(infra_client.get(infra_manifest["console_path"]).status_code == 200,
              "Infra console did not boot")
        check(infra_client.get(infra_manifest["hospital_demo_path"]).status_code == 200,
              "Infra fake-hospital demo UI did not boot")
        check(infra_client.get(infra_manifest["hospital_demo_js_path"]).status_code == 200,
              "Infra fake-hospital demo JS did not boot")
        demo_state = infra_client.get(infra_manifest["hospital_state_path"])
        check(demo_state.status_code == 200
              and demo_state.json()["contract"] == infra_manifest["hospital_demo_contract"],
              "Infra fake-hospital demo state did not boot")
        check(infra_client.get(infra_manifest["state_path"]).status_code == 200,
              "Infra read-cookie fallback did not boot")
        check(infra_client.get(infra_manifest["state_path"] + "?access_token=boot-observer").status_code == 200,
              "Infra read-query fallback did not boot")
        check(infra.state.model_backed is False, "Infra is no longer deterministic")
        check(infra.state.infra_ready is True, "Infra app state is not marked complete")
        check(infra.state.infra_status_path == infra_manifest["status_path"],
              "Infra app state status path changed")
        check(infra.state.commander_enabled is False, "Infra app state enabled Commander")
    except Exception as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    print("OK: exactly two boot manifests; Citizen VIGIL and completed Infra are active")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
