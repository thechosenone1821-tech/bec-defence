"""MessageGuard deterministic signal-family scorer (integrated v1).

This is the one canonical MessageGuard scorer under ``apps/citizen/messageguard``;
``citizen.messageguard`` is a compatibility alias, not a second implementation.
``analyze()`` is the measured scorer used by the evaluation harness;
``score_message()`` is the Citizen API's backwards-compatible adapter.

SIX WEIGHTED SIGNAL FAMILIES
============================

    credential   0.45   OTP / CVV / PIN / UPI-PIN requests, collect requests
    authority    0.40   police / CBI / ED / RBI / TRAI impersonation, "digital arrest"
    money_action 0.30   transfer, fee, fine, bail demands
    prize        0.30   lottery, lucky draw, "you have won"
    urgency      0.20   24 hours, last warning, else-clauses
    link_grab    0.25   shorteners, click-here, verify-now, lookalike domains

A family "fires" when at least one of its token patterns matches the
normalized text. A family contributes its full weight once, regardless
of how many phrases matched.

    raw score   = sum of weights of fired families
    >= 3 families fired  =>  raw is multiplied by 1.3 (the multi-signal
    boost), then capped at 1.0; the cap applies to every final score.

    VERDICT BANDS:  < 0.20 LOW   < 0.45 MODERATE   < 0.70 HIGH   >= 0.70 CRITICAL

`bandmap.to_legacy_band()` translates the verdict into the 0.25-0.99
float the Governor's legacy organ RPC expects.

KNOWN FAILURE MODES (kept stated, per the spec)
===============================================
1. Novel scripts: anything outside the token sets is invisible.
2. Legitimate urgency: a genuine bank KYC-update SMS with a link and
   "immediately" scores like a phishing script; a real "your card is
   blocked" alert shares vocabulary with impersonation scripts.
3. Transliteration: explicit ``lang="hinglish"`` covers the ported
   hand-authored Hinglish corpus; the long tail of Latin transliteration
   remains unmeasured, not a field claim.
4. Obfuscation: spaced-out text ("O T P") is partially mitigated in
   normalize.py and the Hinglish row set; homoglyphs defeat exact tokens.
5. No URLs are ever fetched: links are pattern-matched only, so the app
   never leaks that a message was checked.

This is deliberately rules, not a trained model: it runs offline on a
low-end phone, every hit is explainable (family + matched phrase), and
it needs zero training data. The cost — novel-script misses and
false positives on genuine urgent bank messages — is accepted and
documented, not apologized for.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Union

from . import normalize as _normalize
from . import reasons as _reasons
from .bandmap import to_legacy_band
from .detect import SUPPORTED_LANGS as SUPPORTED_DETECTOR_LANGS
from packages.contracts.bands import (
    BAND_EDGES, VERDICT_ORDER, band, verdict_at_least,
)
from .tokens_en import PATTERNS as _PATTERNS_EN
from .tokens_hi import PATTERNS as _PATTERNS_HI
from .tokens_te import PATTERNS as _PATTERNS_TE
from .tokens_hinglish import PATTERNS as _PATTERNS_HINGLISH

__all__ = [
    "analyze", "band", "FAMILY_WEIGHTS", "VERDICT_ORDER",
    "score_message", "verdict_at_least", "evaluate_fixtures", "ENGINE",
    "SUPPORTED_DETECTOR_LANGS",
]

ENGINE = "messageguard-rules-v1 (538 hand-authored/in-distribution fixtures; real-world UNMEASURED)"

FAMILY_WEIGHTS = {
    "credential": 0.45,
    "authority": 0.40,
    "money_action": 0.30,
    "prize": 0.30,
    "urgency": 0.20,
    "link_grab": 0.25,
}

BOOST_MIN_FAMILIES = 3
BOOST_FACTOR = 1.3
SCORE_CAP = 1.0

# Phase 3: BAND_EDGES and VERDICT_ORDER come from packages.contracts.bands.
# Negation guards. A credential-family match is suppressed when a
# negation cue sits just before or just after the match window: real
# banks write "Do not share your OTP", "OTP किसी को नहीं बताएं",
# "OTP షేర్ చేయవద్దు" — the request-direction is the opposite of the
# scam, and the family must not fire on it.
# Cues are word-delimited. An earlier bare `न करें` matched the tail of
# `सत्यापन करें` ("verification: do") and suppressed real credential
# requests; that is a false negative, so the cue now needs whitespace or
# punctuation on both sides.
_NEGATION_CUES = {
    "en": re.compile(r"\b(do\s*not|don'?t|dont|never|please\s+do\s*not)\b"),
    "hi": re.compile(
        r"(?:^|\s)(?:नहीं|मत|न\s*करें|न\s*करो|न\s*बताएं|न\s*भेजें|"
        r"न\s*शेयर|किसी\s*को\s*नहीं)(?=\s|[.!?।,;]|$)"
    ),
    "te": re.compile(
        r"(?:^|\s)(?:చేయవద్దు|చెప్పవద్దు|చేయకండి|చెప్పకండి|"
        r"చేయవు|చెప్పవు|అడగదు)(?=\s|[.!?।,;]|$)"
    ),
    "hinglish": re.compile(
        r"(?:^|\s)(?:na\s*karo|na\s*karein|mat\s*karo|mat\s*karein|"
        r"nahi|nahin|kabhi\s*bhi|share\s*na\s*karein|"
        r"share\s*mat\s*karo|kisi\s*ke\s*sath\s*share\s*na)"
        r"(?=\s|[.!?।,;]|$)"
    ),
}
_NEG_LOOKBACK = 30   # characters before the match start
_NEG_LOOKAHEAD = 16  # characters after the match end


class _Row:
    """One compiled pattern row (family, reason code, lang, regexes)."""

    __slots__ = ("family", "code", "lang", "regexes", "neg")

    def __init__(self, family, code, lang, regex_strings):
        self.family = family
        self.code = code
        self.lang = lang
        self.regexes = [re.compile(rx) for rx in regex_strings]
        self.neg = _NEGATION_CUES.get(lang)


_ROWS = [
    _Row(family, code, row_lang, regexes)
    for _source_lang, patterns in (
        ("en", _PATTERNS_EN),
        ("hi", _PATTERNS_HI),
        ("te", _PATTERNS_TE),
        ("hinglish", _PATTERNS_HINGLISH),
    )
    for family, code, row_lang, regexes in patterns
]


# Phase 3: band() and verdict_at_least() come from packages.contracts.bands.


def _is_negated(text: str, start: int, end: int, row_lang: str,
                detector_lang: str = "auto") -> bool:
    """True if a negation cue surrounds the match window."""
    lo = max(0, start - _NEG_LOOKBACK)
    hi = min(len(text), end + _NEG_LOOKAHEAD)
    cue = _NEGATION_CUES.get(row_lang)
    if cue is None:
        # "any" rows: check English plus script cues. Hinglish cues are added
        # only in explicit Hinglish mode, so auto en/hi/te numbers stay pinned.
        if _NEGATION_CUES["en"].search(text, lo, hi):
            return True
        others = ("hi", "te", "hinglish") if detector_lang == "hinglish" else ("hi", "te")
        for other in others:
            if _NEGATION_CUES[other].search(text, lo, hi):
                return True
        return False
    return bool(cue.search(text, lo, hi))


def analyze(text: str, lang: str = "auto") -> dict:
    """Score one message. Deterministic and offline.

    lang: "auto" (default) applies the en/hi/te token sets plus all "any"
    rows, preserving the published measurement. "hinglish" applies the
    dedicated Latin-Hindi rows plus "any" rows. Other values restrict to
    that language's rows plus "any" rows.

    Returns a dict with:
      score           final capped (and possibly boosted) score
      verdict         LOW / MODERATE / HIGH / CRITICAL
      legacy_band     float in 0.25-0.99 for the legacy organ RPC
      families_fired  sorted list of fired family names
      boost_applied   True when the >=3-family multiplier was used
      reasons         list of {code, family, matched, pattern_lang}
    """
    if not isinstance(text, str):
        raise TypeError("text must be a str")
    if lang not in SUPPORTED_DETECTOR_LANGS:
        raise ValueError(f"unsupported lang: {lang!r}")

    norm = _normalize.normalize(text)

    reasons_by_key = {}
    families_fired = set()

    for row in _ROWS:
        if lang == "auto":
            if row.lang == "hinglish":
                continue
        elif row.lang not in (lang, "any"):
            continue
        for regex in row.regexes:
            for match in regex.finditer(norm):
                if row.family == "credential" and _is_negated(
                    norm, match.start(), match.end(), row.lang, lang
                ):
                    continue
                matched = match.group(0)
                key = (row.code, matched)
                if key in reasons_by_key:
                    continue
                reasons_by_key[key] = {
                    "code": row.code,
                    "family": row.family,
                    "matched": matched,
                    "pattern_lang": row.lang,
                }
                families_fired.add(row.family)
                break  # one hit per regex is enough; deterministic order

    reasons = sorted(
        reasons_by_key.values(),
        key=lambda r: (FAMILY_WEIGHTS[r["family"]], r["family"], r["code"], r["matched"]),
        reverse=True,
    )

    raw = sum(FAMILY_WEIGHTS[f] for f in families_fired)
    boost_applied = len(families_fired) >= BOOST_MIN_FAMILIES
    score = raw * BOOST_FACTOR if boost_applied else raw
    score = min(SCORE_CAP, score)
    verdict = band(score)

    # Validate every emitted reason against the shared catalogue.
    for r in reasons:
        entry = _reasons.reason_for(r["code"])
        assert entry is not None, f"reason code missing from catalogue: {r['code']}"
        assert entry[0] == r["family"], f"family mismatch for {r['code']}"

    return {
        "score": round(score, 4),
        "verdict": verdict,
        "legacy_band": to_legacy_band(verdict),
        "families_fired": sorted(families_fired),
        "boost_applied": boost_applied,
        "reasons": reasons,
    }


# --------------------------------------------------------------------------- #
# Citizen API compatibility layer
#
# The app and its tests have called score_message()/evaluate_fixtures() since
# M3. Those names stay stable; the scoring underneath is now the measured v1
# engine above. Raw diagnostics stay in the payload, but explain_message() is
# still responsible for what a citizen actually sees.
# --------------------------------------------------------------------------- #

def score_message(text: Any, lang: str = "auto") -> Dict[str, Any]:
    """Score one message with the legacy Citizen payload contract.

    `lang` is the *detector* language filter; the Citizen API deliberately
    leaves it at `"auto"` because its request `lang` selects explanatory copy,
    not the language a scam may be written in. Explicit `"hinglish"` enables
    the dedicated Latin-Hindi rows for the eval runner and operator CLI.
    """
    raw = "" if text is None else str(text)
    detector_lang = lang if lang in SUPPORTED_DETECTOR_LANGS else "auto"
    if not raw.strip():
        return {
            "verdict": "LOW", "score": 0.0, "hits": {},
            "families_hit": [], "families_fired": [],
            "reasons": ["empty input"], "reason_details": [],
            "reason_codes": [], "boost_applied": False,
            "legacy_band": to_legacy_band("LOW"), "engine": ENGINE,
            "detector_lang": detector_lang,
        }

    result = analyze(raw, lang=detector_lang)
    hits: Dict[str, List[str]] = {}
    codes: List[str] = []
    for reason in result["reasons"]:
        family = reason["family"]
        matched = reason["matched"]
        bucket = hits.setdefault(family, [])
        if matched not in bucket:
            bucket.append(matched)
        if reason["code"] not in codes:
            codes.append(reason["code"])
    families_hit = sorted(hits)
    reasons = [f"{family}: {len(hits[family])} signal(s)"
               for family in families_hit]
    return {
        "verdict": result["verdict"],
        "score": result["score"],
        "hits": {family: matches[:4] for family, matches in hits.items()},
        "families_hit": families_hit,
        "families_fired": result["families_fired"],
        "reasons": reasons or ["no known scam signals present"],
        "reason_details": result["reasons"],
        "reason_codes": codes,
        "boost_applied": result["boost_applied"],
        "legacy_band": result["legacy_band"],
        "engine": ENGINE,
        "detector_lang": detector_lang,
    }


def _legacy_rows(data: Dict[str, Any]):
    for item in data.get("scam", []):
        yield item, ">=MODERATE", item.get("expect_at_least", "MODERATE")
    for item in data.get("clean", []):
        yield item, "LOW", "LOW"


def evaluate_fixtures(path: Union[str, Path]) -> Dict[str, Any]:
    """Measure either the 20-item M3 JSON corpus or the v1 JSONL corpus.

    The 538-item corpus uses the published >=MODERATE operating point for
    scams and LOW for genuine alerts; Hinglish rows are scored with the
    explicit `lang="hinglish"` interface. The report is deliberately
    diagnostic: the generated root `EVALS.md` is the single source
    of published numbers; real-world recall and FPR are UNMEASURED.
    """
    p = Path(path)
    rows: List[Dict[str, Any]] = []

    if p.is_dir() or p.suffix == ".jsonl":
        files = sorted(p.glob("*.jsonl")) if p.is_dir() else [p]
        for file in files:
            with file.open(encoding="utf-8") as fh:
                for line in fh:
                    if not line.strip():
                        continue
                    record = json.loads(line)
                    label = record.get("label")
                    result = analyze(
                        record["text"],
                        lang="hinglish" if record.get("lang") == "hinglish" else "auto",
                    )
                    if label == "scam":
                        expected = ">=MODERATE"
                        ok = verdict_at_least(result["verdict"], "MODERATE")
                    else:
                        expected = "LOW"
                        ok = result["verdict"] == "LOW"
                    rows.append({
                        "id": record.get("id"), "lang": record.get("lang"),
                        "label": label, "expect": expected,
                        "got": result["verdict"], "score": result["score"],
                        "ok": bool(ok),
                    })
    else:
        with p.open(encoding="utf-8") as fh:
            data = json.load(fh)
        for item, expected, minimum in _legacy_rows(data):
            result = score_message(item["text"])
            ok = (verdict_at_least(result["verdict"], minimum)
                  if expected == ">=MODERATE" else result["verdict"] == "LOW")
            rows.append({
                "lang": item.get("lang"), "expect": expected,
                "got": result["verdict"], "score": result["score"],
                "ok": bool(ok),
            })

    passed = sum(1 for row in rows if row["ok"])
    total = len(rows)
    return {
        "passed": passed,
        "total": total,
        "accuracy": round(passed / total, 4) if total else 0.0,
        "rows": rows,
    }
