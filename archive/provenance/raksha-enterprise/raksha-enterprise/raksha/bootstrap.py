"""First-boot bootstrap: directories, sensor HMAC key, API tokens, topology.

Run once per deployment (or from `make seed`). Idempotent: existing material is
kept, missing material is generated. The admin token is printed exactly once —
it is never logged again.
"""

from __future__ import annotations

import hashlib
import json
import secrets
import sys
from importlib import resources
from pathlib import Path

from .config import Settings, ensure_dirs, load_or_create_admin_token, load_or_create_sensor_key, load_settings
from .logging_setup import setup_logging

TOPOLOGY_PACKAGE_PATH = "packagedata/topology_c2247.json"


def seed_topology(settings: Settings) -> Path:
    target = settings.data_dir / "topology.json"
    if target.exists():
        return target
    raw = resources.files("raksha").joinpath(TOPOLOGY_PACKAGE_PATH).read_text(encoding="utf-8")
    target.write_text(raw, encoding="utf-8")
    return target


def seed_api_tokens(settings: Settings) -> dict[str, str]:
    """Create api_tokens.toml with sha256-hashed tokens. Returns plaintext->name for first boot."""
    if settings.api_tokens_path.exists():
        return {}
    admin = load_or_create_admin_token(settings)
    sensor_token = secrets.token_urlsafe(24)
    observer_token = secrets.token_urlsafe(24)
    admin = admin or secrets.token_urlsafe(32)
    lines = [
        "# API tokens (sha256-hashed). Rotate by regenerating this file.",
        "# Scopes: telemetry:write, read, admin",
        "",
    ]
    plaintext = {}
    for name, token, scopes in (
        ("admin", admin, ["admin", "read", "telemetry:write"]),
        ("sensor-1", sensor_token, ["telemetry:write"]),
        ("observer", observer_token, ["read"]),
    ):
        digest = hashlib.sha256(token.encode()).hexdigest()
        lines.append(f"[[token]]\nname = \"{name}\"\nhash = \"{digest}\"\nscopes = {scopes!r}\n")
        plaintext[name] = token
    settings.api_tokens_path.parent.mkdir(parents=True, exist_ok=True)
    from .config import _write_private  # noqa: PLC0415 — single-call helper reuse

    _write_private(settings.api_tokens_path, "\n".join(lines))
    print(
        "\n==== FIRST-BOOT TOKENS (printed once — store them now) ====\n"
        f"  admin    : {plaintext['admin']}\n"
        f"  sensor-1 : {plaintext['sensor-1']}\n"
        f"  observer : {plaintext['observer']}\n"
        "===========================================================\n",
        file=sys.stderr,
        flush=True,
    )
    return plaintext


def main() -> None:
    setup_logging("INFO")
    settings: Settings = load_settings()
    ensure_dirs(settings)
    load_or_create_sensor_key(settings)
    tokens = seed_api_tokens(settings)
    topology = seed_topology(settings)
    payload = {
        "data_dir": str(settings.data_dir),
        "sensor_key_path": str(settings.sensor_key_path),
        "api_tokens_path": str(settings.api_tokens_path),
        "topology_path": str(topology),
        "tokens_seeded": sorted(tokens),
    }
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
