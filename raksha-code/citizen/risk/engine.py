"""RAKSHA Citizen — Risk Engine (Phase 4).

One verdict for a person, built from independent signals that were scored
separately:

    voice verdict   (Maya)      -- is the caller's voice machine-made?
    message verdict (MessageGuard) -- does the text look like a scam script?
    campaign link   (report rail)  -- has this pattern been reported before?
    repeat contact  (on device)    -- are they calling you again and again?
    user doubt      (explicit tap) -- do you feel something is wrong?

Two design decisions matter more than the maths:

**1. There is a "we don't know" answer.** A citizen screen that says "safe"
when it simply has no information is worse than useless: it transfers the
victim's trust to a system that cannot earn it. When no signal fires, or when
the only signals are weak/unknown, the engine returns ``LOW_CONFIDENCE`` — not
``SAFE``. There is no SAFE verdict anywhere in this module, by design.

**2. Fusion is bounded and inspectable.** Bounded noisy-OR: each independent
signal contributes ``1-(1-w)`` of the remaining ignorance, so the result can
never exceed 1.0 and no single signal can dominate. The weights are declared
constants, not learned, because a district hospital's IT generalist has to be
able to read this file and agree with it.

Honesty note: the weights are engineering judgement. They are not calibrated
against real fraud outcomes and must not be presented as if they were. The
band thresholds especially are a first cut.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from citizen.risk import fusion
from citizen.voiceguard import contract as VC
from citizen.voiceguard import i18n
from citizen.voiceguard.i18n import render_source as fusion_reason

# --------------------------------------------------------------------------- #
# Signal weights. Independent evidence contributions in [0, 1).
# --------------------------------------------------------------------------- #
W_VOICE_SUSPICIOUS = 0.40
W_VOICE_LIKELY_SYNTHETIC = 0.65
W_MESSAGE_HIGH = 0.35
W_MESSAGE_CRITICAL = 0.60
W_CAMPAIGN_LINK = 0.45      # the same pattern was reported by someone else
W_REPEAT_CONTACT = 0.20     # three or more attempts in a short window
W_USER_DOUBT = 0.15         # the person's own instinct, respected but light

# Bands. ``LOW_CONFIDENCE`` sorts below ``LOW`` so the ordering is explicit.
BAND_LOW_CONFIDENCE = "LOW_CONFIDENCE"
BAND_LOW = "LOW"
BAND_ELEVATED = "ELEVATED"
BAND_HIGH = "HIGH"
BAND_CRITICAL = "CRITICAL"

BANDS = (BAND_LOW_CONFIDENCE, BAND_LOW, BAND_ELEVATED, BAND_HIGH, BAND_CRITICAL)

# (upper_bound_exclusive, band) — first match wins.
_BAND_TABLE = (
    (0.20, BAND_LOW),
    (0.45, BAND_ELEVATED),
    (0.70, BAND_HIGH),
    (1.01, BAND_CRITICAL),
)

# "Nothing found" must never be reported as "nothing wrong".
#
# Two separate guards, because a fused score alone cannot express the
# difference between weak evidence and no evidence:
#
#   _MIN_MEANINGFUL   — the fused score must clear this to leave
#                       LOW_CONFIDENCE at all.
#   _MIN_SIGNAL_COUNT — and there must be at least this many contributing
#                       signals. One weak nudge (e.g. the user's own unease at
#                       weight 0.15) is not evidence; it is a prompt to look
#                       harder. A single isolated signal that exceeds the score
#                       floor on its own (voice, message, campaign) is strong
#                       enough to stand alone.
#
# Found by test: with only a fused-score floor, `user_doubt=True` (0.15)
# produced band LOW — i.e. the app told a nervous citizen "no known fraud
# warning signs found" on the strength of their own doubt. That is precisely
# the backwards reassurance this module exists to prevent.
_MIN_MEANINGFUL = 0.10
_MIN_SIGNAL_COUNT = 2

# Sources strong enough to justify a band on their own.
_STANDALONE_SOURCES = frozenset({"voice", "message", "campaign"})


def _safe_int(v: Any) -> int:
    """Coerce anything to an int without raising.

    Phase 3 fuzz finding: `repeat_contacts="abc"` and `repeat_contacts=NaN` both
    raised ValueError/OverflowError out of `int()`, which through the API became
    an HTTP 500. A malformed field must degrade to "no repeat-contact signal",
    never take the endpoint down — the caller may be a phone mid-update sending a
    half-formed payload.
    """
    try:
        f = float(v)
    except (TypeError, ValueError):
        return 0
    if f != f or f in (float("inf"), float("-inf")):
        return 0
    try:
        return int(f)
    except (ValueError, OverflowError):
        return 0


def _safe_bool(v: Any) -> bool:
    """Coerce to a bool without treating junk as evidence.

    Phase 3 fuzz finding: `campaign_linked="nope"` was truthy, so a malformed
    string added the 0.45 campaign-link weight and pushed the assessment to HIGH
    on evidence that did not exist. Only real booleans and the integers 0/1 count;
    every other type is "no signal". Failing towards *less* certainty is the only
    safe direction for a fraud screen.
    """
    if isinstance(v, bool):
        return v
    if isinstance(v, int):
        return v == 1
    if isinstance(v, str):
        return v.strip().lower() in ("true", "1", "yes")
    return False


def _clamp01(v: Any) -> float:
    try:
        f = float(v)
    except (TypeError, ValueError):
        return 0.0
    if f != f:            # NaN
        return 0.0
    return max(0.0, min(1.0, f))


def noisy_or(weights: List[float]) -> float:
    """Bounded union of independent evidence. Never exceeds 1.0."""
    remaining = 1.0
    for w in weights:
        remaining *= (1.0 - _clamp01(w))
    return 1.0 - remaining


def band_for(score: float, n_signals: int,
             sources: Optional[List[str]] = None) -> str:
    """Map a fused score to a band, honouring the 'we don't know' rule.

    A band above LOW_CONFIDENCE requires either:
      * one *standalone* source (voice / message / campaign), or
      * at least ``_MIN_SIGNAL_COUNT`` contributing signals (corroboration).

    Anything else is LOW_CONFIDENCE: the engine remains undecided and says so.
    """
    if n_signals == 0:
        return BAND_LOW_CONFIDENCE
    if score < _MIN_MEANINGFUL:
        return BAND_LOW_CONFIDENCE
    srcs = set(sources or [])
    corroborated = n_signals >= _MIN_SIGNAL_COUNT or bool(srcs & _STANDALONE_SOURCES)
    if not corroborated:
        return BAND_LOW_CONFIDENCE
    for limit, band in _BAND_TABLE:
        if score < limit:
            return band
    return BAND_CRITICAL


# --------------------------------------------------------------------------- #
def assess(voice: Optional[Dict[str, Any]] = None,
           message: Optional[Dict[str, Any]] = None,
           campaign_linked: bool = False,
           repeat_contacts: int = 0,
           user_doubt: bool = False,
           lang: str = "en") -> Dict[str, Any]:
    """Fuse whatever signals are available into one citizen-facing verdict.

    Part One of the four-part split moved all scoring arithmetic into
    ``citizen/risk/fusion.py``. This function is now a thin presentation adapter:
    it calls the pure fusion core, then attaches the sentences a person reads.
    Keeping it as the public entry point means every existing caller and test
    continues to work unchanged.

    Every input is optional. Passing nothing returns ``LOW_CONFIDENCE`` — never a
    reassuring ``LOW`` — because an empty assessment is not an acquittal.
    """
    lang = i18n.normalise_language(lang)
    core = fusion.evaluate(
        voice=voice,
        message=message,
        campaign_linked=campaign_linked,
        repeat_contacts=repeat_contacts,
        user_doubt=user_doubt,
    )

    band = core["band"]
    headline, action = _band_copy(band, lang)

    # Part One deliberately returns *internal* source/detail values. Turning them
    # into sentences is Part Two's job, and doing it here would put English in
    # the scoring path. The pre-rendered `reasons` list is kept for the existing
    # UI, but it is built from Part Two's catalogue, never from raw codes.
    reasons = [fusion_reason(s, lang) for s in core["signals"]]
    if not reasons:
        reasons = [i18n.render_reason(VC.R_LOW_CONFIDENCE, lang)]

    return {
        "band": band,
        "band_reason": core["band_reason"],
        "score": core["score"],
        "signals": core["signals"],
        "skipped": core["skipped"],
        "weights_used": core["weights_used"],
        "headline": headline,
        "action": action,
        "reasons": reasons,
        "helpline": i18n.HELPLINE,
        "lang": lang,
        "degraded": core["degraded"],
        "advisory": ("Judgement-based weighting, not calibrated against real "
                     "fraud outcomes — an aid to your decision, not a verdict."),
    }


_BAND_COPY = {
    BAND_LOW_CONFIDENCE: {
        "en": ("Not enough information to judge",
               "Trust your instinct. If they ask for money or OTP, hang up and call 1930."),
        "hi": ("पर्याप्त जानकारी नहीं है",
               "अपनी समझ पर भरोसा रखें। पैसे या OTP माँगे जाएँ तो फोन काटें और 1930 पर कॉल करें।"),
        "te": ("సరిపడా సమాచారం లేదు",
               "మీ బుద్ధిని నమ్మండి. డబ్బు లేదా OTP అడిగితే ఫోన్ పెట్టేసి 1930కి కాల్ చేయండి."),
    },
    BAND_LOW: {
        "en": ("No known fraud warning signs found",
               "Still never share OTP, PIN or CVV with anyone."),
        "hi": ("धोखाधड़ी के ज्ञात संकेत नहीं मिले",
               "फिर भी OTP, PIN या CVV किसी को न दें।"),
        "te": ("తెలిసిన మోసపు సంకేతాలు లేవు",
               "అయినా OTP, PIN లేదా CVV ఎవరికీ ఇవ్వకండి."),
    },
    BAND_ELEVATED: {
        "en": ("Some warning signs are present",
               "Pause. Verify through an official number before doing anything."),
        "hi": ("कुछ चेतावनी संकेत मौजूद हैं",
               "रुकें। कुछ भी करने से पहले आधिकारिक नंबर से पुष्टि करें।"),
        "te": ("కొన్ని హెచ్చరిక సంకేతాలు ఉన్నాయి",
               "ఆగండి. ఏదైనా చేసే ముందు అధికారిక నంబర్ ద్వారా నిర్ధారించుకోండి."),
    },
    BAND_HIGH: {
        "en": ("This looks like a scam attempt",
               "Do not pay, do not share OTP. Call 1930."),
        "hi": ("यह धोखाधड़ी का प्रयास लगता है",
               "पैसे न दें, OTP न बताएँ। 1930 पर कॉल करें।"),
        "te": ("ఇది మోసం ప్రయత్నంలా ఉంది",
               "డబ్బు ఇవ్వద్దు, OTP చెప్పవద్దు. 1930కి కాల్ చేయండి."),
    },
    BAND_CRITICAL: {
        "en": ("This is almost certainly a scam",
               "Hang up now. Call 1930 and your bank immediately."),
        "hi": ("यह लगभग निश्चित रूप से धोखाधड़ी है",
               "अभी फोन काटें। 1930 और अपने बैंक को तुरंत कॉल करें।"),
        "te": ("ఇది దాదాపు ఖచ్చితంగా మోసం",
               "వెంటనే ఫోన్ పెట్టేయండి. 1930కి, మీ బ్యాంకుకు వెంటనే కాల్ చేయండి."),
    },
}


def _band_copy(band: str, lang: str):
    entry = _BAND_COPY.get(band) or _BAND_COPY[BAND_LOW_CONFIDENCE]
    body = entry.get(lang) or entry["en"]
    return body[0], body[1]
