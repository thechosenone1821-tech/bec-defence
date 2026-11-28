"""Shared static Phosphor frontend and same-origin Python gateway.

The built Next.js export is served by both active RAKSHA apps. The gateway is a
backend-for-frontend layer: it injects scoped tokens, maps compatibility paths
to active endpoints, signs sandbox telemetry and keeps credentials server-side.
"""
from __future__ import annotations

from .gateway import (
    FRONTEND_BUILD_DIR,
    FRONTEND_CONTRACT_VERSION,
    register_frontend,
)

__all__ = [
    "FRONTEND_BUILD_DIR",
    "FRONTEND_CONTRACT_VERSION",
    "register_frontend",
]
