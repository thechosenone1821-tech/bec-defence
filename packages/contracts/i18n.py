"""Shared language/copy rendering contract.

Language normalisation, fallback accounting and sentence selection live here.
The sentences are owned by the Citizen app and passed in as a catalogue; shared
contracts never import app code, the VIGIL model package or a live-executor
implementation.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Optional

from .reasons import REASON_CATALOGUE

CONTRACT_VERSION = "raksha-citizen-i18n-v1"
LANGUAGES = ("en", "hi", "te")
DEFAULT_LANGUAGE = "en"
HELPLINE = "1930"
R_LOW_CONFIDENCE = "R_LOW_CONFIDENCE"
MESSAGE_ACTIONABLE_VERDICTS = ("HIGH", "CRITICAL")

_FALLBACK_LIMIT = 200


def normalise_language(lang: Any) -> str:
    """Map caller language tags onto the supported copy codes."""
    if not lang:
        return DEFAULT_LANGUAGE
    base = str(lang).strip().lower().replace("_", "-").split("-")[0]
    return base if base in LANGUAGES else DEFAULT_LANGUAGE


@dataclass
class FallbackLog:
    """Bounded record of copies that had to borrow the default language."""

    records: List[Dict[str, str]] = field(default_factory=list)
    limit: int = _FALLBACK_LIMIT

    def record(self, code: str, lang: str) -> None:
        try:
            if len(self.records) >= self.limit:
                return
            self.records.append({"code": str(code), "lang": str(lang)})
        except Exception:  # diagnostics must never break a warning
            pass

    def entries(self) -> List[Dict[str, str]]:
        return list(self.records)

    def reset(self) -> None:
        self.records.clear()


def reason_family(code: str) -> Optional[str]:
    entry = REASON_CATALOGUE.get(str(code))
    return str(entry[0]) if entry else None


def message_reason_codes() -> List[str]:
    return sorted(REASON_CATALOGUE)


class CitizenRenderer:
    """Render app-owned copy using one shared, fail-closed i18n algorithm."""

    def __init__(self, catalogue: Mapping[str, Any], fallback_log: Optional[FallbackLog] = None):
        self.catalogue = dict(catalogue)
        self.fallback_log = fallback_log or FallbackLog()

    def _table(self, name: str) -> Dict[str, Any]:
        table = self.catalogue.get(name)
        return dict(table) if isinstance(table, Mapping) else {}

    def _lang_value(self, table: Mapping[str, Any], lang: str, code: str = "") -> Any:
        """Return a language value or the default, recording every fallback."""
        if lang in table and table[lang]:
            return table[lang]
        if DEFAULT_LANGUAGE in table:
            if code:
                self.fallback_log.record(code, lang)
            return table[DEFAULT_LANGUAGE]
        return None

    def render_band(self, band: str, lang: str = DEFAULT_LANGUAGE) -> Dict[str, str]:
        lang = normalise_language(lang)
        bands = self._table("band_copy")
        entry = bands.get(str(band)) or bands.get("LOW_CONFIDENCE") or {}
        body = self._lang_value(entry, lang, str(band)) if isinstance(entry, Mapping) else None
        if isinstance(body, (tuple, list)) and len(body) >= 2:
            headline, action = body[0], body[1]
        elif isinstance(body, Mapping):
            headline = str(body.get("title") or "")
            action = str(body.get("action") or "")
        else:
            headline, action = "Not enough information to judge", "If in doubt, call 1930."
        return {"headline": headline, "action": action, "lang": lang}

    def render_advisory(self, lang: str = DEFAULT_LANGUAGE) -> str:
        lang = normalise_language(lang)
        return str(self._lang_value(self._table("advisory"), lang, "advisory") or "")

    def render_band_reason(self, why: str, lang: str = DEFAULT_LANGUAGE) -> str:
        lang = normalise_language(lang)
        text = str(why or "").lower()
        for needle, (_key, table) in self._table("band_reason_kinds").items():
            if needle in text and isinstance(table, Mapping):
                return str(self._lang_value(table, lang, str(needle)) or "")
        return ""

    def render_reason(self, code: str, lang: str = DEFAULT_LANGUAGE,
                      params: Optional[Dict[str, Any]] = None) -> str:
        lang = normalise_language(lang)
        reasons = self._table("reasons")
        entry = reasons.get(str(code))
        if not isinstance(entry, Mapping):
            self.fallback_log.record(str(code), lang)
            entry = reasons.get(R_LOW_CONFIDENCE) or {}
        text = str(self._lang_value(entry, lang, str(code)) or "")
        if params:
            try:
                text = text.format(**params)
            except Exception:
                pass
        return text

    def render_family(self, family: str, lang: str = DEFAULT_LANGUAGE) -> str:
        lang = normalise_language(lang)
        table = self._table("families")
        entry = table.get(str(family)) or table.get("urgency") or {}
        return str(self._lang_value(entry, lang, str(family)) or "")

    def render_message_reason(self, code: str, lang: str = DEFAULT_LANGUAGE) -> str:
        lang = normalise_language(lang)
        override = self._table("message_reason_overrides").get(str(code))
        if isinstance(override, Mapping):
            return str(self._lang_value(override, lang, str(code)) or "")
        family = reason_family(code)
        if family:
            return self.render_family(family, lang)
        no_signal = self._table("no_message_signal")
        return str(self._lang_value(no_signal, lang, "no_message_signal") or "")

    def render_source(self, signal: Dict[str, Any], lang: str = DEFAULT_LANGUAGE) -> str:
        lang = normalise_language(lang)
        table = self._table("source_sentences")
        if not isinstance(signal, dict):
            fallback = table.get("user_doubt") or {}
            return str(self._lang_value(fallback, lang, "user_doubt") or "")
        source = str(signal.get("source") or "")
        detail = str(signal.get("detail") or "")
        entry = table.get(f"{source}:{detail}") or table.get(source) or table.get("user_doubt") or {}
        return str(self._lang_value(entry, lang, f"{source}:{detail}") or "")

    def explain_message(self, result: Dict[str, Any], lang: str = DEFAULT_LANGUAGE) -> Dict[str, Any]:
        lang = normalise_language(lang)
        verdict = str(result.get("verdict") or "MODERATE").upper()
        verdicts = self._table("message_verdict")
        entry = verdicts.get(verdict) or verdicts.get("MODERATE") or {}
        copy = self._lang_value(entry, lang, verdict) if isinstance(entry, Mapping) else {}
        copy = copy if isinstance(copy, Mapping) else {}

        families = [f for f in (result.get("families_hit") or []) if isinstance(f, str)]
        details = [d for d in (result.get("reason_details") or [])
                   if isinstance(d, dict) and d.get("code")]
        first_code_by_family: Dict[str, str] = {}
        for detail in details:
            family = detail.get("family")
            code = detail.get("code")
            if family and code and family not in first_code_by_family:
                first_code_by_family[str(family)] = str(code)
        selected_codes = [first_code_by_family[f] for f in families if f in first_code_by_family]
        if selected_codes:
            sentences = [self.render_message_reason(code, lang) for code in selected_codes]
        else:
            sentences = [self.render_family(f, lang) for f in families]
        if not families:
            no_signal = self._table("no_message_signal")
            sentences = [str(self._lang_value(no_signal, lang, "no_message_signal") or "")]

        message_codes = sorted({str(d["code"]) for d in details
                                if str(d.get("code")) in REASON_CATALOGUE})
        return {
            "verdict": verdict,
            "title": str(copy.get("title") or ""),
            "action": str(copy.get("action") or ""),
            "reasons": sentences,
            "reason_codes": families,
            "message_reason_codes": message_codes,
            "helpline": HELPLINE,
            "disclaimer": str(self._lang_value(self._table("disclaimer"), lang, "disclaimer") or ""),
            "lang": lang,
            "actionable": verdict in MESSAGE_ACTIONABLE_VERDICTS,
        }

    def explain_report(self, result: Optional[Dict[str, Any]], lang: str = DEFAULT_LANGUAGE,
                       state: str = "sent") -> Dict[str, Any]:
        lang = normalise_language(lang)
        table = self._table("report_copy")
        entry = table.get(state) or table.get("failed") or {}
        body = self._lang_value(entry, lang, state) if isinstance(entry, Mapping) else None
        if not isinstance(body, (tuple, list)) or len(body) < 2:
            body = ("Report not sent", "Call 1930 instead. Your data did not leave this phone.")
        out: Dict[str, Any] = {
            "title": str(body[0]), "detail": str(body[1]),
            "helpline": HELPLINE, "lang": lang,
        }
        fwd = result.get("forwarded") if isinstance(result, dict) else None
        reached = bool(isinstance(fwd, dict) and fwd.get("forwarded"))
        out["reached_network"] = reached
        out["accepted"] = bool(isinstance(result, dict) and result.get("status") == "REPORTED")
        out["delivered"] = reached
        if out["accepted"] and not reached:
            failed = table.get("forwarding_failed") or {}
            fallback_body = self._lang_value(failed, lang, "forwarding_failed")
            if isinstance(fallback_body, (tuple, list)) and len(fallback_body) >= 2:
                out["title"], out["detail"] = str(fallback_body[0]), str(fallback_body[1])
        return out

    def privacy_tab_copy(self, lang: str = DEFAULT_LANGUAGE) -> Dict[str, Any]:
        lang = normalise_language(lang)
        table = self._table("privacy_tab")
        entry = table.get(lang) or table.get(DEFAULT_LANGUAGE) or {}
        return {
            "enabled": True,
            "status": "active",
            "title": str(entry.get("title") or "Image privacy — VIGIL"),
            "detail": str(entry.get("detail") or "VIGIL image privacy is available. Call 1930 if in doubt."),
            "helpline": HELPLINE,
            "lang": lang,
            "model_backed": True,
            "privacy_efficacy": "UNMEASURED",
        }

    def catalogue_codes(self) -> List[str]:
        return sorted(self._table("reasons"))

    def fallbacks(self) -> List[Dict[str, str]]:
        return self.fallback_log.entries()

    def reset_fallbacks(self) -> None:
        self.fallback_log.reset()


__all__ = [
    "CONTRACT_VERSION", "LANGUAGES", "DEFAULT_LANGUAGE", "HELPLINE",
    "R_LOW_CONFIDENCE", "MESSAGE_ACTIONABLE_VERDICTS", "FallbackLog",
    "CitizenRenderer", "normalise_language", "reason_family",
    "message_reason_codes",
]
