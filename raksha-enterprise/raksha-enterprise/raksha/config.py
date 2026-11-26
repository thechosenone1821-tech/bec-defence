"""Service configuration.

Everything is environment-driven (RAKSHA_* prefix) with safe defaults, so the
same image runs in dev, staging and prod. Secret material never lives in code:
sensor HMAC keys and API tokens are seeded on first boot under the data
directory with restrictive permissions.
"""

from __future__ import annotations

import os
import secrets
import stat
import sys
from dataclasses import dataclass, field
from pathlib import Path

_DEFAULT_CROWN_ASSETS = ("N-TIER0-CORE", "N-IDENTITY-VAULT")


def _env(name: str, default: str = "") -> str:
    return os.environ.get(f"RAKSHA_{name}", default)


@dataclass(frozen=True)
class Settings:
    data_dir: Path
    log_level: str
    rate_limit_epm: int
    crown_assets: tuple[str, ...] = field(default=_DEFAULT_CROWN_ASSETS)
    # Governor policy knobs (part of the frozen contract; change deliberately)
    blast_cap: int = 8            # G2: proposals severing more than this are refused
    precision_max_blast: int = 2  # G4: allowed without escalation up to this blast

    @property
    def keys_dir(self) -> Path:
        return self.data_dir / "keys"

    @property
    def sensor_key_path(self) -> Path:
        return self.keys_dir / "sensor.key"

    @property
    def api_tokens_path(self) -> Path:
        return self.keys_dir / "api_tokens.toml"

    @property
    def events_db_path(self) -> Path:
        return self.data_dir / "events.db"

    @property
    def ledger_db_path(self) -> Path:
        return self.data_dir / "ledger.db"


def load_settings() -> Settings:
    data_dir = Path(_env("DATA_DIR", "./data")).resolve()
    rate_limit_raw = _env("RATE_LIMIT_EPM", "600")
    try:
        rate_limit = max(1, int(rate_limit_raw))
    except ValueError:
        rate_limit = 600
    crowns = tuple(x.strip() for x in _env("CROWN_ASSETS", ",".join(_DEFAULT_CROWN_ASSETS)).split(",") if x.strip())
    return Settings(
        data_dir=data_dir,
        log_level=_env("LOG_LEVEL", "INFO").upper(),
        rate_limit_epm=rate_limit,
        crown_assets=crowns or _DEFAULT_CROWN_ASSETS,
    )


def ensure_dirs(settings: Settings) -> None:
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    settings.keys_dir.mkdir(parents=True, exist_ok=True)


def _write_private(path: Path, data: str) -> None:
    """Write a file with 0600 permissions (best effort on platforms without chmod)."""
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        fh.write(data)
    try:
        os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)
    except OSError:
        pass


def load_or_create_sensor_key(settings: Settings) -> bytes:
    """The HMAC key used to sign/verify telemetry. Seeded on first boot."""
    settings.sensor_key_path.parent.mkdir(parents=True, exist_ok=True)
    override = _env("SENSOR_KEY")
    if override:
        return bytes.fromhex(override)
    if settings.sensor_key_path.exists():
        return bytes.fromhex(settings.sensor_key_path.read_text(encoding="utf-8").strip())
    key = secrets.token_bytes(32)
    _write_private(settings.sensor_key_path, key.hex())
    # stderr, not stdout: stdout stays machine-parseable (JSON reports)
    print(
        f"[bootstrap] generated NEW sensor HMAC key at {settings.sensor_key_path} — "
        "distribute it to sensors; events signed with other keys will be quarantined",
        file=sys.stderr,
        flush=True,
    )
    return key


def load_or_create_admin_token(settings: Settings) -> str:
    """Bootstrap admin token. Seeded on first boot; printed once, never logged again."""
    override = _env("ADMIN_TOKEN")
    if override:
        return override
    if settings.api_tokens_path.exists():
        # Existing token file wins; the caller should use tokens from it.
        return ""
    return secrets.token_urlsafe(32)
