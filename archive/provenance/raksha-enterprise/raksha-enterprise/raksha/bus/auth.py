"""API token authentication with scopes.

Tokens live in data/keys/api_tokens.toml as sha256 hashes — plaintext tokens
are only shown once at bootstrap. Scopes: `telemetry:write` (sensors),
`read` (observers/consoles), `admin` (ledger appends; still cannot override
decisions — nobody can).
"""

from __future__ import annotations

import hashlib
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path

try:
    from packages.contracts.config import AUTH_SCOPES as ALL_SCOPES
except ImportError:  # pragma: no cover - standalone historical checkout
    sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
    from packages.contracts.config import AUTH_SCOPES as ALL_SCOPES


class AuthError(Exception):
    def __init__(self, status: int, detail: str) -> None:
        super().__init__(detail)
        self.status = status
        self.detail = detail


@dataclass(frozen=True, slots=True)
class TokenRecord:
    name: str
    scopes: tuple[str, ...]


class TokenStore:
    def __init__(self, records: dict[str, TokenRecord]) -> None:
        self._records = records  # sha256 hex -> record

    @classmethod
    def load(cls, path: Path) -> "TokenStore":
        raw = tomllib.loads(Path(path).read_text(encoding="utf-8"))
        records: dict[str, TokenRecord] = {}
        for entry in raw.get("token", []):
            digest = entry["hash"].lower()
            records[digest] = TokenRecord(name=entry["name"], scopes=tuple(entry["scopes"]))
        return cls(records)

    def authenticate(self, token: str) -> TokenRecord:
        if not token:
            raise AuthError(401, "invalid or missing API token")
        digest = hashlib.sha256(token.encode()).hexdigest()
        record = self._records.get(digest)
        if record is None:
            raise AuthError(401, "invalid or missing API token")
        return record

    @staticmethod
    def authorize(record: TokenRecord, scope: str) -> None:
        if scope not in record.scopes and "admin" not in record.scopes:
            raise AuthError(403, f"token {record.name!r} lacks required scope {scope!r}")
