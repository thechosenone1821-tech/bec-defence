"""MessageGuard normalization helpers.

Pure-stdlib, deterministic, offline. The normalizer is deliberately
conservative: it must never invent text, only collapse irrelevant
variation (case, Unicode width, zero-width joiners, spaces inside
well-known acronyms like "O T P").

What it does NOT do (known failure modes, kept stated per the spec):
- homoglyph substitution across scripts (Cyrillic 'о' vs Latin 'o') is
  NOT resolved;
- spaced-out Devanagari/Telugu letters are NOT re-joined (only the
  Latin acronym allowlist below).
"""

import re
import unicodedata

# Zero-width and bidi-invisible characters that scam senders inject to
# break exact-token matching.
_ZERO_WIDTH = re.compile("[\u200b\u200c\u200d\u200e\u200f\u2060-\u2064\u206a-\u206f\ufeff]")

_WHITESPACE = re.compile(r"\s+")

# Spaced-out / digit-confusable spellings of the small set of acronyms
# every Indian scam script leans on. This is a cheap partial mitigation
# of failure mode 4 ("O T P"); homoglyphs remain unhandled.
_DEOBFUSCATE = [
    (re.compile(r"\b[o0][\s.\-]*[t7][\s.\-]*[p]\b", re.IGNORECASE), "otp"),
    (re.compile(r"\bc[\s.\-]*v[\s.\-]*v\b", re.IGNORECASE), "cvv"),
    (re.compile(r"\bk[\s.\-]*y[\s.\-]*c\b", re.IGNORECASE), "kyc"),
    (re.compile(r"\bu[\s.\-]*p[\s.\-]*i\b", re.IGNORECASE), "upi"),
]


def normalize(text: str) -> str:
    """Return the canonical form a scorer should match against.

    Deterministic: same input string always yields the same output.
    """
    t = unicodedata.normalize("NFKC", text)
    t = _ZERO_WIDTH.sub("", t)
    t = t.casefold()
    for rx, repl in _DEOBFUSCATE:
        t = rx.sub(repl, t)
    t = _WHITESPACE.sub(" ", t).strip()
    return t
