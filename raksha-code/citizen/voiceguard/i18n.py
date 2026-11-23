"""MAYA / VoiceGuard — reason catalogue and sentence rendering (en / hi / te).

Every reason code becomes a plain-language sentence a person can act on. The
rules that shape this file:

* **No raw scores reach a citizen.** A number without a sentence is noise.
* **Every sentence is short enough for a 360 px screen.**
* **Every non-trivial verdict ends with a human action** (hang up, don't pay,
  call back on an official number, call 1930).
* **No accusation.** "This voice has machine-like characteristics" — never
  "this is a criminal".
* **No unmeasured precision claims.** Nothing here says "99 % accurate".

Missing translations fall back to English rather than rendering a key, and a
test asserts all three languages cover every code — because a missing string on
a scam warning is a real-world failure, not a cosmetic one.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from . import contract as C

LANGUAGES = ("en", "hi", "te")
DEFAULT_LANGUAGE = "en"

# --------------------------------------------------------------------------- #
# Per-reason sentences. `{param}` slots are filled from the reason's params.
# Keep them under ~90 characters where the language allows.
# --------------------------------------------------------------------------- #
_REASONS: Dict[str, Dict[str, str]] = {
    C.R_TOO_SHORT: {
        "en": "The clip is too short to judge.",
        "hi": "क्लिप जाँचने के लिए बहुत छोटी है।",
        "te": "క్లిప్ అంచనా వేయడానికి చాలా చిన్నది.",
    },
    C.R_SILENT: {
        "en": "We could not hear any speech in this clip.",
        "hi": "इस क्लिप में कोई आवाज़ सुनाई नहीं दी।",
        "te": "ఈ క్లిప్‌లో ఎలాంటి మాటలు వినిపించలేదు.",
    },
    C.R_INVALID_PAYLOAD: {
        "en": "The audio could not be read.",
        "hi": "ऑडियो पढ़ा नहीं जा सका।",
        "te": "ఆడియో చదవలేకపోయాము.",
    },
    C.R_PURE_TONE: {
        "en": "This is a flat, machine-made tone, not a human voice.",
        "hi": "यह सपाट, मशीन से बनी आवाज़ है, इंसानी आवाज़ नहीं।",
        "te": "ఇది చదునైన, యంత్రంతో చేసిన శబ్దం, మనిషి గొంతు కాదు.",
    },
    C.R_WHITE_NOISE: {
        "en": "This sounds like background noise, not a person speaking.",
        "hi": "यह पृष्ठभूमि का शोर लगता है, किसी के बोलने की आवाज़ नहीं।",
        "te": "ఇది నేపథ్య శబ్దంలా ఉంది, ఎవరో మాట్లాడుతున్నట్టు కాదు.",
    },
    C.R_CLIPPED: {
        "en": "The recording is distorted and hard to judge.",
        "hi": "रिकॉर्डिंग विकृत है, जाँचना कठिन है।",
        "te": "రికార్డింగ్ వక్రీకరించింది, అంచనా కష్టం.",
    },
    C.R_MONOTONE_PITCH: {
        "en": "The voice does not change pitch the way a real person does.",
        "hi": "आवाज़ में उतार-चढ़ाव नहीं है, जैसा असली इंसान में होता है।",
        "te": "నిజమైన మనిషిలా స్వరం మారడం లేదు.",
    },
    C.R_MECHANICAL_PAUSES: {
        "en": "The pauses are exactly evenly spaced, as a machine makes them.",
        "hi": "ठहराव बिल्कुल बराबर अंतराल पर हैं, जैसे मशीन करती है।",
        "te": "విరామాలు సరిగ్గా సమాన దూరంలో ఉన్నాయి, యంత్రంలా.",
    },
    C.R_NO_BREATH: {
        "en": "There are no breath sounds between sentences.",
        "hi": "वाक्यों के बीच साँस लेने की आवाज़ नहीं है।",
        "te": "వాక్యాల మధ్య శ్వాస శబ్దాలు లేవు.",
    },
    C.R_SPECTRAL_REGULARITY: {
        "en": "The sound texture barely changes from moment to moment.",
        "hi": "आवाज़ की बनावट पल-पल में बदलती नहीं है।",
        "te": "శబ్దం నిర్మాణం క్షణం క్షణం మారడం లేదు.",
    },
    C.R_MODEL_CLONE: {
        "en": "Our on-device screen rated this likely AI-generated.",
        "hi": "ऑन-डिवाइस जाँच ने इसे AI से बना बताया।",
        "te": "మా పరికరంలోని పరీక్ష దీన్ని AI తయారు చేసినట్టు చెప్పింది.",
    },
    C.R_MODEL_CLEAN: {
        "en": "Our screen found nothing, but that is not proof.",
        "hi": "हमारी जाँच में कुछ नहीं मिला, पर यह सबूत नहीं है।",
        "te": "మా పరీక్షలో ఏమీ దొరకలేదు, కానీ అది రుజువు కాదు.",
    },
    C.R_NO_MODEL: {
        "en": "No trained model is installed, so only basic checks ran.",
        "hi": "कोई प्रशिक्षित मॉडल नहीं है, इसलिए केवल सामान्य जाँच हुई।",
        "te": "శిక్షణ పొందిన మాడల్ లేదు, కాబట్టి సాధారణ పరీక్షలే జరిగాయి.",
    },
    C.R_LOW_CONFIDENCE: {
        "en": "This clip does not give a clear answer.",
        "hi": "इस क्लिप से साफ़ जवाब नहीं मिलता।",
        "te": "ఈ క్లిప్ స్పష్టమైన సమాధానం ఇవ్వదు.",
    },
    C.R_INTERNAL_ERROR: {
        "en": "The check failed safely. Nothing was sent anywhere.",
        "hi": "जाँच सुरक्षित रूप से रुकी। कोई डेटा कहीं नहीं भेजा गया।",
        "te": "పరీక్ష సురక్షితంగా ఆగిపోయింది. ఎక్కడికీ డేటా పంపలేదు.",
    },
}

# --------------------------------------------------------------------------- #
# Verdict headlines + the action a person should take.
# --------------------------------------------------------------------------- #
_VERDICT: Dict[str, Dict[str, Dict[str, str]]] = {
    C.SILENT: {
        "en": {"title": "We could not hear a voice",
               "action": "Try again closer to the phone."},
        "hi": {"title": "आवाज़ सुनाई नहीं दी",
               "action": "फोन के पास से दोबारा कोशिश करें।"},
        "te": {"title": "స్వరం వినిపించలేదు",
               "action": "ఫోన్ దగ్గరకు తీసుకొచ్చి మళ్లీ ప్రయత్నించండి."},
    },
    C.INCONCLUSIVE: {
        "en": {"title": "We cannot tell",
               "action": "If they ask for money, OTP or an 'arrest' — hang up. Call 1930."},
        "hi": {"title": "हम निर्णय नहीं कर सकते",
               "action": "अगर पैसे, OTP या 'गिरफ्तारी' की बात हो — फोन काटें। 1930 पर कॉल करें।"},
        "te": {"title": "మేము నిర్ణయించలేము",
               "action": "డబ్బు, OTP లేదా 'అరెస్ట్' గురించి అడిగితే — ఫోన్ పెట్టేయండి. 1930కి కాల్ చేయండి."},
    },
    C.SUSPICIOUS: {
        "en": {"title": "This voice looks machine-made",
               "action": "Hang up and call back on the official number on your card."},
        "hi": {"title": "यह आवाज़ मशीन से बनी लगती है",
               "action": "फोन काटें और कार्ड पर दिए आधिकारिक नंबर पर कॉल करें।"},
        "te": {"title": "ఈ స్వరం యంత్రంతో చేసినట్టు ఉంది",
               "action": "ఫోన్ పెట్టేసి, కార్డ్‌పై ఉన్న అధికారిక నంబర్‌కు కాల్ చేయండి."},
    },
    C.LIKELY_SYNTHETIC: {
        "en": {"title": "This is probably an AI-generated voice",
               "action": "Hang up now. Do not pay. Call 1930 if money was asked for."},
        "hi": {"title": "यह संभवतः AI से बनी आवाज़ है",
               "action": "अभी फोन काटें। पैसे न दें। पैसे माँगे गए हों तो 1930 पर कॉल करें।"},
        "te": {"title": "ఇది బహుశా AI తయారు చేసిన స్వరం",
               "action": "వెంటనే ఫోన్ పెట్టేయండి. డబ్బు ఇవ్వద్దు. డబ్బు అడిగితే 1930కి కాల్ చేయండి."},
    },
    C.ERROR: {
        "en": {"title": "Check unavailable",
               "action": "Stay safe: if in doubt, call 1930."},
        "hi": {"title": "जाँच उपलब्ध नहीं",
               "action": "सतर्क रहें: संदेह हो तो 1930 पर कॉल करें।"},
        "te": {"title": "పరీక్ష అందుబాటులో లేదు",
               "action": "జాగ్రత్తగా ఉండండి: సందేహమైతే 1930కి కాల్ చేయండి."},
    },
}

HELPLINE = "1930"

_DISCLAIMER = {
    "en": "This is an advisory screen, not proof. Never share OTP, PIN or CVV.",
    "hi": "यह सलाहकार जाँच है, सबूत नहीं। OTP, PIN या CVV कभी साझा न करें।",
    "te": "ఇది సలహా పరీక్ష మాత్రమే, రుజువు కాదు. OTP, PIN లేదా CVV ఎప్పుడూ పంచుకోవద్దు.",
}


def normalise_language(lang: Optional[str]) -> str:
    """Map anything caller-ish onto a supported code, defaulting to English."""
    if not lang:
        return DEFAULT_LANGUAGE
    base = str(lang).strip().lower().replace("_", "-").split("-")[0]
    return base if base in LANGUAGES else DEFAULT_LANGUAGE


def render_reason(code: str, lang: str = DEFAULT_LANGUAGE,
                  params: Optional[Dict[str, Any]] = None) -> str:
    """One reason code -> one sentence. Never raises, never returns a raw key."""
    lang = normalise_language(lang)
    entry = _REASONS.get(code)
    if entry is None:
        return _REASONS[C.R_LOW_CONFIDENCE][lang]
    return entry.get(lang) or entry[DEFAULT_LANGUAGE]


def render_verdict(verdict: str, lang: str = DEFAULT_LANGUAGE) -> Dict[str, str]:
    lang = normalise_language(lang)
    entry = _VERDICT.get(verdict) or _VERDICT[C.INCONCLUSIVE]
    body = entry.get(lang) or entry[DEFAULT_LANGUAGE]
    return {
        "verdict": verdict,
        "title": body["title"],
        "action": body["action"],
        "helpline": HELPLINE,
        "disclaimer": _DISCLAIMER[lang],
        "lang": lang,
    }


def explain(result: Dict[str, Any], lang: str = DEFAULT_LANGUAGE) -> Dict[str, Any]:
    """Turn a ``score_voice`` payload into a citizen-facing explanation.

    The raw score is deliberately **not** included: a person cannot act on
    "0.83", and showing it invites false precision.

    ``INCONCLUSIVE`` never renders as reassurance. It says "we cannot tell" and
    then gives the scam checklist, because silence is not innocence.
    """
    lang = normalise_language(lang)
    verdict = result.get("verdict", C.INCONCLUSIVE)
    reasons = result.get("reasons") or []

    codes: List[str] = []
    for r in reasons:
        if isinstance(r, dict) and r.get("code"):
            code = r["code"]
            # Internal bookkeeping codes are not citizen-facing sentences.
            if code in (C.R_MODEL_CLEAN,) and verdict not in (C.SUSPICIOUS,
                                                             C.LIKELY_SYNTHETIC):
                continue
            if code not in codes:
                codes.append(code)

    sentences = [render_reason(c, lang) for c in codes]
    body = render_verdict(verdict, lang)
    return {
        **body,
        "reasons": sentences,
        "reason_codes": codes,
        "actionable": verdict in (C.SUSPICIOUS, C.LIKELY_SYNTHETIC),
    }


def catalogue_codes() -> List[str]:
    """All codes that have a translation — used by the coverage test."""
    return sorted(_REASONS)


def all_reason_constants() -> List[str]:
    """Every R_* constant declared in the contract."""
    return sorted(v for k, v in vars(C).items()
                  if k.startswith("R_") and isinstance(v, str))
