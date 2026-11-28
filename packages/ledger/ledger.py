"""Compatibility facade for the shipped append-only ledger."""
from spine.ledger import *  # noqa: F401,F403
from spine.ledger import AuditLedger as AuditLedger

__all__ = ["AuditLedger"]
