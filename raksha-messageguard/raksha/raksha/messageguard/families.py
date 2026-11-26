"""Six weighted signal families and their deterministic matchers.

Weights (fixed by the Part 3 spec):

    credential   0.45   OTP / CVV / PIN / UPI-PIN requests, collect-request acceptance
    authority    0.40   Police / CBI / ED / RBI impersonation, "digital arrest"
    money_action 0.30   transfer, fine, bail, processing fee
    prize        0.30   lottery, lucky draw
    urgency      0.20   24 hours, last warning, else-clause
    link_grab    0.25   shorteners, "click / verify now"

A family fires once per message no matter how many tokens matched; the
distinct fired families are what the scorer sums.

Matching order is fully deterministic: families are evaluated in a fixed
order, phrases/patterns/pairs keep the tuple order declared in ``tokens.py``,
and the hit list is sorted by (weight desc, family name).
"""

from __future__ import annotations

from dataclasses import dataclass

from . import tokens as T
from .types import Reason

__all__ = ["FAMILY_WEIGHTS", "FAMILY_TO_CODE", "FamilyHit", "match_families"]

FAMILY_WEIGHTS: dict[str, float] = {
    "credential": 0.45,
    "authority": 0.40,
    "money_action": 0.30,
    "prize": 0.30,
    "urgency": 0.20,
    "link_grab": 0.25,
}

# reason codes from the Part 1 catalogue, one per family
FAMILY_TO_CODE: dict[str, str] = {
    "credential": "msg.credential.request",
    "authority": "msg.authority.impersonation",
    "money_action": "msg.money.action",
    "prize": "msg.prize.claim",
    "urgency": "msg.urgency.pressure",
    "link_grab": "msg.link.grab",
}

MAX_MATCHES_PER_FAMILY = 6  # keep reasons bounded; SMS messages are short anyway


@dataclass(frozen=True)
class FamilyHit:
    family: str
    weight: float
    reasons: tuple[Reason, ...]
    total_matches: int


def _reason(family: str, trigger: str, matched: str, spans: tuple[tuple[int, int], ...]) -> Reason:
    return Reason(code=FAMILY_TO_CODE[family], family=family, trigger=trigger, matched=matched, spans=spans)


def _collect(langs: tuple[str, ...], table: dict[str, tuple[str, ...]]) -> tuple[str, ...]:
    """Merge phrase lists across the language universe, preserving order."""
    seen: set[str] = set()
    out: list[str] = []
    for lang in langs:
        for p in table.get(lang, ()):
            if p not in seen:
                seen.add(p)
                out.append(p)
    return tuple(out)


def _rules_for(family: str, langs: tuple[str, ...]):
    per_lang = T.PAIR_RULES.get(family, {})
    return tuple(rule for lang in langs for rule in per_lang.get(lang, ()))


def _pair_hits(norm: str, rules):
    """Yield (matched_label, spans, entity_order, partner_order) for pair rules."""
    out = []
    for entities, partners in rules:
        e_hits = T.iter_phrase_hits(norm, entities)
        if not e_hits:
            continue
        p_hits = T.iter_phrase_hits(norm, partners)
        if not p_hits:
            continue
        for e in e_hits:
            for p in p_hits:
                out.append((f"{e[2]} + {p[2]}", (e[0:2], p[0:2]), e[0], p[0]))
    out.sort(key=lambda x: (x[2], x[3], x[0]))
    return out


def match_families(lang: str, norm_text: str) -> list[FamilyHit]:
    """Run every family matcher over one normalized message."""
    langs = T.LANG_UNIVERSES.get(lang, ("en",))
    norm = norm_text
    guarded = T.guard_active(langs, norm)
    hits: list[FamilyHit] = []

    for family in T.FAMILIES:
        # The credential family stays silent when a genuine bank warning
        # guard phrase is present (see tokens.GUARDS docstring).
        if family == "credential" and guarded:
            continue

        reasons: list[Reason] = []

        phrases = _collect(langs, T.PHRASES[family])
        for start, end, phrase in T.iter_phrase_hits(norm, phrases)[:MAX_MATCHES_PER_FAMILY]:
            reasons.append(_reason(family, "phrase", phrase, ((start, end),)))

        for start, end, hit in T.iter_pattern_hits(norm, T.PATTERNS[family])[:MAX_MATCHES_PER_FAMILY]:
            reasons.append(_reason(family, "pattern", hit, ((start, end),)))

        for matched, spans, _, _ in _pair_hits(norm, _rules_for(family, langs))[:MAX_MATCHES_PER_FAMILY]:
            reasons.append(_reason(family, "pair", matched, spans))

        if reasons:
            hits.append(FamilyHit(family, FAMILY_WEIGHTS[family], tuple(reasons), len(reasons)))

    hits.sort(key=lambda h: (-h.weight, h.family))
    return hits
