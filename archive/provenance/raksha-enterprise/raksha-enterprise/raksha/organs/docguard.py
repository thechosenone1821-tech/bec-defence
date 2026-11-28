"""docguard — poisoned vendor invoices (bank-detail manipulation)."""

from __future__ import annotations

from typing import Any

from .base import Organ, _flag, _num


class DocGuard(Organ):
    name = "docguard"

    def evaluate(self, payload: dict[str, Any]) -> tuple[bool, str | None]:
        if not _flag(payload, "bank_detail_changed"):
            return False, None
        fresh_vendor = _num(payload, "vendor_age_days", 9999.0) < 90
        metadata_mismatch = _flag(payload, "pdf_metadata_mismatch")
        if fresh_vendor:
            return True, "DG-BANKCHG-FRESH"
        if metadata_mismatch:
            return True, "DG-BANKCHG-META"
        return False, None
