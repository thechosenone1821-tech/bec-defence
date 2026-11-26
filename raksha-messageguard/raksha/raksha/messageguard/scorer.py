"""The deterministic signal-family scorer.

raksha.messageguard — Part 3: MessageGuard
==========================================

Reads a suspicious SMS / WhatsApp message and tells the person whether it
looks like a known scam script. Six weighted signal families; three or more
families fire a x1.3 boost; verdict bands LOW / MODERATE / HIGH / CRITICAL.

Why rules and not a model (deliberate, defended — do not apologise for it):
    1. Runs offline on a low-end phone: no download, no GPU, no battery cost.
    2. Explainable: every reason names the family and the matched phrase, so
       a person can see WHY it fired — that matters more than 3% accuracy.
    3. Zero training-data requirement, so it can ship today.

The cost, stated and kept stated:
    - It misses novel scripts. Anything outside the token sets is invisible.
    - It will false-positive on genuine urgent payment messages from a real
      bank. The false-positive rate is measured on genuine bank alerts and
      published in raksha/EVALS.md — never hidden.
    - Transliterated Hinglish (Latin script) is only partly covered.
    - Spaced-out text ("O T P") and homoglyphs defeat exact tokens.
    - Links are NEVER fetched. They are pattern-matched only, so the app
      never leaks to the network that a message was checked.

A trained classifier is explicitly out of scope here (see spec section 3 and
4): corpus first, model second, and only behind this same interface.
"""

from __future__ import annotations

from .detect import detect_language
from .families import FAMILY_WEIGHTS, FamilyHit, match_families
from .tokens import LANG_UNIVERSES, normalize
from .types import (
    BOOST_FACTOR,
    BOOST_MIN_FAMILIES,
    SCORE_CAP,
    Band,
    Reason,
    Verdict,
    band_for,
)

__all__ = ["SignalFamilyScorer", "assess", "score"]


class SignalFamilyScorer:
    """Stateless, deterministic scorer. Same input always gives the same verdict."""

    def score(self, text: str, lang: str | None = None) -> Verdict:
        text = text or ""
        resolved = lang if lang in LANG_UNIVERSES else detect_language(text)
        norm = normalize(text)

        hits: list[FamilyHit] = match_families(resolved, norm)

        families = tuple(h.family for h in hits)
        raw = sum(h.weight for h in hits)
        boosted = len(hits) >= BOOST_MIN_FAMILIES
        if boosted:
            raw *= BOOST_FACTOR
        score = min(raw, SCORE_CAP)

        reasons: list[Reason] = []
        for hit in hits:
            reasons.extend(hit.reasons)

        return Verdict(
            text=text,
            lang=resolved,
            score=score,
            band=band_for(score),
            families=families,
            reasons=tuple(reasons),
            boosted=boosted,
            family_hits={h.family: h.total_matches for h in hits},
        )


_MODULE_SCORER = SignalFamilyScorer()


def assess(text: str, lang: str | None = None) -> Verdict:
    """Convenience entry point: assess one message and return the verdict."""
    return _MODULE_SCORER.score(text, lang)


score = assess  # alias
