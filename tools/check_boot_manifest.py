#!/usr/bin/env python3
"""Phase 10 boot-manifest gate: exactly two apps, both bootable, no AI."""
from __future__ import annotations

import json
import pathlib
import sys
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "raksha-code")]

from fastapi.testclient import TestClient  # noqa: E402
from apps.citizen.api import build_app as build_citizen_app  # noqa: E402
from apps.infra.backend.app import create_app as create_infra_app  # noqa: E402

APPS = ROOT / "apps"
REQUIRED = ("contract", "app", "app_count", "entrypoint", "default_port",
            "bind", "root_redirect", "health_path", "no_ai_models",
            "voiceguard_integrated", "dry_run")


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
            check(manifest["contract"] == "raksha-boot-manifest-v1",
                  f"wrong boot manifest contract: {path}")
            check(manifest["app"] == app_dir.name and manifest["app_count"] == 2,
                  f"boot manifest app identity mismatch: {path}")
            check(manifest["bind"] == "0.0.0.0", f"manifest must bind all interfaces: {path}")
            check(manifest["no_ai_models"] is True and manifest["dry_run"] is True,
                  f"manifest must stay no-AI and dry-run: {path}")
            check(manifest["voiceguard_integrated"] is False,
                  f"VoiceGuard must stay deferred: {path}")
            manifests[app_dir.name] = manifest

        citizen = build_citizen_app(bus_url="", poster=lambda event: {"accepted": 1})
        citizen_client = TestClient(citizen)
        check(citizen_client.get(manifests["citizen"]["health_path"]).status_code == 200,
              "Citizen health route did not boot")
        check(citizen_client.get("/", follow_redirects=False).status_code == 307,
              "Citizen root redirect did not boot")
        check(citizen_client.get(manifests["citizen"]["manifest_path"]).status_code == 200,
              "Citizen manifest route did not boot")
        check(citizen_client.get(manifests["citizen"]["health_path"]).json()["no_ai_models"] is True,
              "Citizen booted with AI models enabled")

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
        check(infra_client.get(manifests["infra"]["health_path"]).status_code == 200,
              "Infra health route did not boot")
        check(infra_client.get("/", follow_redirects=False).status_code == 307,
              "Infra root redirect did not boot")
        check(infra_client.get(manifests["infra"]["state_path"],
                               headers={"X-API-Token": "boot-observer"}).status_code == 200,
              "Infra state route did not boot")
        check(infra_client.get("/app/contract").status_code == 200,
              "Infra contract route did not boot")
        check(infra.state.no_ai_models is True,
              "Infra booted with AI models enabled")
    except Exception as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    print("OK: exactly two boot manifests; Citizen and Infra boot read-only, no-AI, dry-run")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
