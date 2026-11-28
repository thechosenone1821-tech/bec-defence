"""RAKSHA applications — separate app packages, one shared spine.

Each app owns its own code and may be edited without changing the other app.
Shared imports belong in ``packages``; direct app-to-app imports are forbidden.
"""
from __future__ import annotations

APP_NAMES = ("citizen", "infra")

__all__ = ["APP_NAMES"]
