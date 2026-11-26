"""VoiceGuard + MessageGuard — reason catalogue and sentence rendering (en / hi / te).

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

from typing import Any, Dict, List, Optional, Tuple

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


# --------------------------------------------------------------------------- #
# Band copy (Part Two, task 2.1).
#
# This table used to live in `citizen/risk/engine.py` — five bands x three
# languages of citizen-facing copy inside the module whose whole job was to hold
# no English at all. It belongs here: everything a citizen reads comes from this
# file, so there is one place to review copy and one place to translate it.
# --------------------------------------------------------------------------- #
_BAND_COPY: Dict[str, Dict[str, Tuple[str, str]]] = {
    "LOW_CONFIDENCE": {
        "en": ("Not enough information to judge",
               "Trust your instinct. If they ask for money or OTP, hang up and call 1930."),
        "hi": ("पर्याप्त जानकारी नहीं है",
               "अपनी समझ पर भरोसा रखें। पैसे या OTP माँगे जाएँ तो फोन काटें और 1930 पर कॉल करें।"),
        "te": ("సరిపడా సమాచారం లేదు",
               "మీ బుద్ధిని నమ్మండి. డబ్బు లేదా OTP అడిగితే ఫోన్ పెట్టేసి 1930కి కాల్ చేయండి."),
    },
    "LOW": {
        "en": ("No known fraud warning signs found",
               "Still never share OTP, PIN or CVV with anyone."),
        "hi": ("धोखाधड़ी के ज्ञात संकेत नहीं मिले",
               "फिर भी OTP, PIN या CVV किसी को न दें।"),
        "te": ("తెలిసిన మోసపు సంకేతాలు లేవు",
               "అయినా OTP, PIN లేదా CVV ఎవరికీ ఇవ్వకండి."),
    },
    "ELEVATED": {
        "en": ("Some warning signs are present",
               "Pause. Verify through an official number before doing anything."),
        "hi": ("कुछ चेतावनी संकेत मौजूद हैं",
               "रुकें। कुछ भी करने से पहले आधिकारिक नंबर से पुष्टि करें।"),
        "te": ("కొన్ని హెచ్చరిక సంకేతాలు ఉన్నాయి",
               "ఆగండి. ఏదైనా చేసే ముందు అధికారిక నంబర్ ద్వారా నిర్ధారించుకోండి."),
    },
    "HIGH": {
        "en": ("This looks like a scam attempt",
               "Do not pay, do not share OTP. Call 1930."),
        "hi": ("यह धोखाधड़ी का प्रयास लगता है",
               "पैसे न दें, OTP न बताएँ। 1930 पर कॉल करें।"),
        "te": ("ఇది మోసం ప్రయత్నంలా ఉంది",
               "డబ్బు ఇవ్వద్దు, OTP చెప్పవద్దు. 1930కి కాల్ చేయండి."),
    },
    "CRITICAL": {
        "en": ("This is almost certainly a scam",
               "Hang up now. Call 1930 and your bank immediately."),
        "hi": ("यह लगभग निश्चित रूप से धोखाधड़ी है",
               "अभी फोन काटें। 1930 और अपने बैंक को तुरंत कॉल करें।"),
        "te": ("ఇది దాదాపు ఖచ్చితంగా మోసం",
               "వెంటనే ఫోన్ పెట్టేయండి. 1930కి, మీ బ్యాంకుకు వెంటనే కాల్ చేయండి."),
    },
}

# --------------------------------------------------------------------------- #
# The honesty label (Part Two, task 2.2).
#
# This is the sentence that stops the app being believed more than it deserves:
# "judgement-based weighting, not calibrated against real fraud outcomes". It was
# English-only, so a Telugu reader received a Telugu warning and an English
# disclaimer explaining that the warning was not proof. The one sentence that
# must survive translation was the one that did not.
#
# It stays deliberately long and unflattering. Shortening it would raise the
# credibility of the screen beyond what the measurements support.
# --------------------------------------------------------------------------- #
_ADVISORY: Dict[str, str] = {
    "en": ("Judgement-based weighting, not calibrated against real fraud "
           "outcomes — an aid to your decision, not a verdict."),
    "hi": ("यह मानव-निर्धारित भारांक पर आधारित है, असली धोखाधड़ी के आँकड़ों पर "
           "कैलिब्रेटेड नहीं है — यह आपके फैसले में एक सहायता है, कोई अंतिम निर्णय नहीं।"),
    "te": ("ఇది నిర్ణయించిన బరువుల ఆధారంగా పనిచేస్తుంది, నిజమైన మోసం ఫలితాలపై "
           "కాలిబ్రేట్ చేయబడలేదు — ఇది మీ నిర్ణయానికి సహాయం మాత్రమే, తీర్పు కాదు."),
}


def render_band(band: str, lang: str = DEFAULT_LANGUAGE) -> Dict[str, str]:
    """A risk band -> the headline and action a citizen reads.

    Falls back to ``LOW_CONFIDENCE`` copy for an unknown band: the safe rendering
    for "we do not recognise this band" is "we cannot judge", never "all clear".
    """
    lang = normalise_language(lang)
    entry = _BAND_COPY.get(str(band)) or _BAND_COPY["LOW_CONFIDENCE"]
    title, action = entry.get(lang) or entry[DEFAULT_LANGUAGE]
    return {"headline": title, "action": action, "lang": lang}


def render_advisory(lang: str = DEFAULT_LANGUAGE) -> str:
    """The honesty label, in the reader's language."""
    lang = normalise_language(lang)
    return _ADVISORY.get(lang) or _ADVISORY[DEFAULT_LANGUAGE]


# --------------------------------------------------------------------------- #
# Band *reasons* (Part Two, task 2.4).
#
# `fusion.band_for()` returns a machine explanation of why a band is what it is:
# "a single weak signal is not enough without corroboration". That is the most
# useful sentence in the whole payload and it was English developer text that no
# citizen could read. These three shapes are the only ones Part One produces.
# --------------------------------------------------------------------------- #
_BAND_REASON_KINDS = {
    # (substring to look for) -> (catalogue key, sentence per language)
    "no signals": ("nothing_seen", {
        "en": "There was nothing to judge yet.",
        "hi": "अभी जाँचने के लिए कुछ नहीं था।",
        "te": "ఇంకా అంచనా వేయడానికి ఏమీ లేదు.",
    }),
    "corroboration": ("needs_more", {
        "en": "One weak sign alone is not enough. Tell us if they ask for money or OTP.",
        "hi": "एक कमज़ोर संकेत ही पर्याप्त नहीं है। पैसे या OTP माँगे जाएँ तो बताएँ।",
        "te": "ఒక బలహీన సంకేతం మాత్రమే సరిపోదు. డబ్బు లేదా OTP అడిగితే చెప్పండి.",
    }),
    "falls in": ("scored", {
        "en": "Enough separate signs were seen together to raise this.",
        "hi": "अलग-अलग संकेत साथ मिले, इसलिए यह चेतावनी बढ़ी।",
        "te": "వేర్వేరు సంకేతాలు కలిసి కనిపించాయి, అందుకే ఈ హెచ్చరిక పెరిగింది.",
    }),
    "exceeds": ("reached_top", {
        "en": "Several independent signs agree. Treat this as a serious warning.",
        "hi": "कई स्वतंत्र संकेत एक ही बात कह रहे हैं। इसे गंभीर चेतावनी मानें।",
        "te": "అనేక స్వతంత్ర సంకేతాలు ఏకీభవిస్తున్నాయి. దీన్ని తీవ్రమైన హెచ్చరికగా తీసుకోండి.",
    }),
    "below": ("too_weak", {
        "en": "The signs seen so far are weak.",
        "hi": "अब तक मिले संकेत कमज़ोर हैं।",
        "te": "ఇప్పటివరకు కనిపించిన సంకేతాలు బలహీనంగా ఉన్నాయి.",
    }),
}


def render_band_reason(why: str, lang: str = DEFAULT_LANGUAGE) -> str:
    """Turn Part One's English band explanation into a citizen sentence.

    Matching is by substring rather than by parsing, because Part One's reasons
    are prose for engineers and this must never raise on a wording change. An
    unrecognised reason returns "" and the caller shows nothing — a missing
    explanation is survivable, a wrong one is not.
    """
    lang = normalise_language(lang)
    text = str(why or "").lower()
    for needle, (key, table) in _BAND_REASON_KINDS.items():
        if needle in text:
            return table.get(lang) or table[DEFAULT_LANGUAGE]
    return ""


def normalise_language(lang: Optional[str]) -> str:
    """Map anything caller-ish onto a supported code, defaulting to English."""
    if not lang:
        return DEFAULT_LANGUAGE
    base = str(lang).strip().lower().replace("_", "-").split("-")[0]
    return base if base in LANGUAGES else DEFAULT_LANGUAGE


# Part Two, task 2.3. Every fallback that quietly served English is recorded
# here (code -> language that was asked for). A missing Telugu string used to be
# invisible: the app kept working, kept looking finished, and shipped English to
# a Telugu reader forever. Nothing raises on a gap, but a gap can now be asserted
# to be empty instead of assumed to be.
FALLBACK_LOG: List[Dict[str, str]] = []
_FALLBACK_LIMIT = 200


def _record_fallback(code: str, lang: str) -> None:
    """Note a code that had to borrow English. Bounded, and never raises."""
    try:
        if len(FALLBACK_LOG) >= _FALLBACK_LIMIT:
            return
        FALLBACK_LOG.append({"code": str(code), "lang": str(lang)})
    except Exception:      # a diagnostics hook must never break a warning
        pass


def fallbacks() -> List[Dict[str, str]]:
    """Copy of the fallback log, for tests and for a support probe."""
    return list(FALLBACK_LOG)


def reset_fallbacks() -> None:
    """Clear the log. Tests call this so one gap cannot hide behind another."""
    del FALLBACK_LOG[:]


def render_reason(code: str, lang: str = DEFAULT_LANGUAGE,
                  params: Optional[Dict[str, Any]] = None) -> str:
    """One reason code -> one sentence. Never raises, never returns a raw key.

    A missing translation falls back to English *and records that it did*
    (task 2.3). Silence was the failure mode: the screen looked complete while
    quietly answering in the wrong language.
    """
    lang = normalise_language(lang)
    entry = _REASONS.get(code)
    if entry is None:
        _record_fallback(str(code), lang)
        return _REASONS[C.R_LOW_CONFIDENCE][lang]
    if not entry.get(lang):
        _record_fallback(str(code), lang)
        return entry[DEFAULT_LANGUAGE]
    return entry[lang]


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


# --------------------------------------------------------------------------- #
# MessageGuard signal families -> citizen sentences.
#
# These are NOT the same thing as reason codes: a "family" is an input signal
# that contributed to a message verdict, and a citizen should see "it is asking
# for your OTP", never the internal name `credential`.
# --------------------------------------------------------------------------- #
_FAMILIES: Dict[str, Dict[str, str]] = {
    "credential": {
        "en": "It asks for your OTP, PIN, CVV or password.",
        "hi": "यह आपका OTP, PIN, CVV या पासवर्ड माँगता है।",
        "te": "ఇది మీ OTP, PIN, CVV లేదా పాస్‌వర్డ్ అడుగుతోంది.",
    },
    "authority": {
        "en": "It pretends to be police, a court, the RBI or a tax officer.",
        "hi": "यह पुलिस, अदालत, RBI या कर अधिकारी होने का दिखावा करता है।",
        "te": "ఇది పోలీసు, కోర్టు, RBI లేదా పన్ను అధికారిగా నటిస్తోంది.",
    },
    "money_action": {
        "en": "It asks you to send or transfer money.",
        "hi": "यह पैसे भेजने या ट्रांसफर करने को कहता है।",
        "te": "ఇది డబ్బు పంపమని లేదా బదిలీ చేయమని అడుగుతోంది.",
    },
    "prize": {
        "en": "It claims you won a prize or lottery.",
        "hi": "यह दावा करता है कि आपने इनाम या लॉटरी जीती है।",
        "te": "మీరు బహుమతి లేదా లాటరీ గెలిచారని చెబుతోంది.",
    },
    "urgency": {
        "en": "It pressures you to act immediately.",
        "hi": "यह तुरंत कार्रवाई करने का दबाव बनाता है।",
        "te": "వెంటనే చర్య తీసుకోవాలని ఒత్తిడి చేస్తోంది.",
    },
    "link_grab": {
        "en": "It pushes you to click a link or verify now.",
        "hi": "यह लिंक पर क्लिक करने या अभी सत्यापित करने को कहता है।",
        "te": "లింక్ నొక్కమని లేదా వెంటనే ధృవీకరించమని చెబుతోంది.",
    },
}

# Stable MSG-* reason codes from citizen/messageguard/reasons.py. The i18n
# layer deliberately does not import the detector package at runtime; a test
# asserts this map stays identical to that catalogue.
MSG_REASON_FAMILY = {
    "MSG-CRED-OTP-SHARE": "credential",
    "MSG-CRED-CVV-SHARE": "credential",
    "MSG-CRED-UPI-PIN-RECEIVE": "credential",
    "MSG-CRED-UPI-PIN-ENTRY": "credential",
    "MSG-CRED-UPI-COLLECT-REQUEST": "credential",
    "MSG-CRED-BANK-DETAILS": "credential",
    "MSG-AUTH-DIGITAL-ARREST": "authority",
    "MSG-AUTH-ARREST-WARRANT": "authority",
    "MSG-AUTH-CASE-AGAINST-YOU": "authority",
    "MSG-AUTH-AGENCY-THREAT": "authority",
    "MSG-AUTH-PARCEL-SEIZED": "authority",
    "MSG-AUTH-TELECOM-BLOCK": "authority",
    "MSG-AUTH-RBI-ACTION": "authority",
    "MSG-AUTH-POWER-DISCONNECT": "authority",
    "MSG-MONEY-FEE-DEMAND": "money_action",
    "MSG-MONEY-FINE-PENALTY": "money_action",
    "MSG-MONEY-BAIL": "money_action",
    "MSG-MONEY-TRANSFER-DEMAND": "money_action",
    "MSG-PRIZE-LOTTERY": "prize",
    "MSG-PRIZE-WON-AMOUNT": "prize",
    "MSG-URG-DEADLINE-HOURS": "urgency",
    "MSG-URG-LAST-WARNING": "urgency",
    "MSG-URG-IMMEDIATELY": "urgency",
    "MSG-URG-ELSE-CLAUSE": "urgency",
    "MSG-LINK-SHORTENER": "link_grab",
    "MSG-LINK-CLICK-HERE": "link_grab",
    "MSG-LINK-VERIFY-NOW": "link_grab",
    "MSG-LINK-LOOKALIKE-DOMAIN": "link_grab",
    "MSG-LINK-APK": "link_grab",
}

# A few codes need a more actionable sentence than the family-level copy.
# Every other MSG-* code renders through render_family() below, so no code can
# leak as a raw key and no matched scam phrase is shown to a citizen.
_MESSAGE_REASON_OVERRIDES: Dict[str, Dict[str, str]] = {
    "MSG-CRED-UPI-PIN-RECEIVE": {
        "en": "It says to enter a UPI PIN to receive money. A PIN is never needed to receive money.",
        "hi": "यह पैसे पाने के लिए UPI PIN डालने को कहता है। पैसे पाने के लिए कभी PIN नहीं चाहिए।",
        "te": "డబ్బు పొందడానికి UPI PIN నమోదు చేయమంటోంది. డబ్బు పొందడానికి PIN ఎప్పుడూ అవసరం లేదు.",
    },
    "MSG-LINK-SHORTENER": {
        "en": "It hides the destination behind a shortened link.",
        "hi": "यह छोटे लिंक के पीछे असली पता छुपाता है।",
        "te": "ఇది చిన్న లింక్ వెనుక అసలు చిరునామా దాచిపెడుతుంది.",
    },
    "MSG-LINK-APK": {
        "en": "It asks you to install an app or APK from a link.",
        "hi": "यह लिंक से ऐप या APK इंस्टॉल करने को कहता है।",
        "te": "ఇది లింక్ నుంచి యాప్ లేదా APK ఇన్‍స్టాల్ చేయమంటోంది.",
    },
}

_NO_MESSAGE_SIGNAL = {
    "en": "We recognise no known scam wording here — that is not proof it is safe.",
    "hi": "यहाँ कोई ज्ञात धोखाधड़ी शब्द नहीं मिला — यह सुरक्षित होने का सबूत नहीं है।",
    "te": "ఇక్కడ తెలిసిన మోసపు పదాలు లేవు — ఇది సురక్షితమని రుజువు కాదు.",
}

_MESSAGE_VERDICT = {
    "LOW": {
        "en": {"title": "No known scam signals found",
               "action": "Still never share OTP, PIN or CVV with anyone."},
        "hi": {"title": "धोखाधड़ी के ज्ञात संकेत नहीं मिले",
               "action": "फिर भी OTP, PIN या CVV किसी को न दें।"},
        "te": {"title": "తెలిసిన మోసపు సంకేతాలు లేవు",
               "action": "అయినా OTP, PIN లేదా CVV ఎవరికీ ఇవ్వకండి."},
    },
    "MODERATE": {
        "en": {"title": "Some warning signs are present",
               "action": "Verify through the official number on your card. Do not reply."},
        "hi": {"title": "कुछ चेतावनी संकेत मौजूद हैं",
               "action": "अपने कार्ड पर दिए आधिकारिक नंबर से पुष्टि करें। जवाब न दें।"},
        "te": {"title": "కొన్ని హెచ్చరిక సంకేతాలు ఉన్నాయి",
               "action": "మీ కార్డ్‌పై ఉన్న అధికారిక నంబర్ ద్వారా నిర్ధారించుకోండి. రిప్లై ఇవ్వవద్దు."},
    },
    "HIGH": {
        "en": {"title": "This looks like a scam message",
               "action": "Do not reply, do not click, do not pay. Call 1930."},
        "hi": {"title": "यह धोखाधड़ी का संदेश लगता है",
               "action": "जवाब न दें, लिंक न खोलें, पैसे न दें। 1930 पर कॉल करें।"},
        "te": {"title": "ఇది మోసపు సందేశంలా ఉంది",
               "action": "రిప్లై ఇవ్వవద్దు, లింక్ నొక్కవద్దు, డబ్బు ఇవ్వద్దు. 1930కి కాల్ చేయండి."},
    },
    "CRITICAL": {
        "en": {"title": "This is almost certainly a scam",
               "action": "Delete it. Do not pay. Call 1930 and your bank."},
        "hi": {"title": "यह लगभग निश्चित रूप से धोखाधड़ी है",
               "action": "इसे हटा दें। पैसे न दें। 1930 और अपने बैंक को कॉल करें।"},
        "te": {"title": "ఇది దాదాపు ఖచ్చితంగా మోసం",
               "action": "దీన్ని తొలగించండి. డబ్బు ఇవ్వద్దు. 1930కి, మీ బ్యాంకుకు కాల్ చేయండి."},
    },
}


def render_family(family: str, lang: str = DEFAULT_LANGUAGE) -> str:
    """One MessageGuard signal family -> one sentence. Never a raw key."""
    lang = normalise_language(lang)
    entry = _FAMILIES.get(family)
    if entry is None:
        return _FAMILIES["urgency"][lang]
    return entry.get(lang) or entry[DEFAULT_LANGUAGE]


def render_message_reason(code: str, lang: str = DEFAULT_LANGUAGE) -> str:
    """One stable MSG-* reason code -> one citizen sentence.

    Codes, not matched scam phrases, cross this boundary. A code outside the
    catalogue returns the honest "nothing found is not nothing wrong" sentence.
    """
    lang = normalise_language(lang)
    entry = _MESSAGE_REASON_OVERRIDES.get(code)
    if entry:
        return entry.get(lang) or entry[DEFAULT_LANGUAGE]
    family = MSG_REASON_FAMILY.get(code)
    if family:
        return render_family(family, lang)
    return _NO_MESSAGE_SIGNAL[lang]


def message_reason_codes() -> List[str]:
    """All MSG-* codes with a translation — used by the coverage test."""
    return sorted(MSG_REASON_FAMILY)


# --------------------------------------------------------------------------- #
# Part One emits *sources* (voice / message / campaign / repeat / doubt) and
# internal detail values. Part Two turns those into sentences.
#
# Phase 1 fixed this for the message tab but left the risk engine still returning
# raw codes like "LIKELY_SYNTHETIC" and "same pattern already reported" straight
# into a citizen-facing `reasons` list. That is the same bug on a different
# surface, so the mapping lives here once.
# --------------------------------------------------------------------------- #
_SOURCE_SENTENCES: Dict[str, Dict[str, str]] = {
    "voice:LIKELY_SYNTHETIC": {
        "en": "The voice on this call shows strong signs of being machine-generated.",
        "hi": "इस कॉल की आवाज़ में मशीन से बने होने के स्पष्ट संकेत हैं।",
        "te": "ఈ కాల్‌లోని స్వరంలో యంత్రంతో తయారైనట్టు స్పష్టమైన సంకేతాలున్నాయి.",
    },
    "voice:SUSPICIOUS": {
        "en": "The voice on this call has some machine-like characteristics.",
        "hi": "इस कॉल की आवाज़ में कुछ मशीन जैसी विशेषताएँ हैं।",
        "te": "ఈ కాల్‌లోని స్వరంలో కొన్ని యంత్రంలాంటి లక్షణాలున్నాయి.",
    },
    "message:CRITICAL": {
        "en": "The message uses words and demands seen in confirmed fraud.",
        "hi": "संदेश में पुष्ट धोखाधड़ी में देखे गए शब्द और माँगें हैं।",
        "te": "సందేశంలో నిర్ధారిత మోసాల్లో కనిపించే పదాలు, డిమాండ్లు ఉన్నాయి.",
    },
    "message:HIGH": {
        "en": "The message matches a known scam pattern.",
        "hi": "संदेश एक ज्ञात धोखाधड़ी पैटर्न से मेल खाता है।",
        "te": "సందేశం తెలిసిన మోసం నమూనాతో సరిపోతుంది.",
    },
    "campaign": {
        "en": "Other people have already reported this exact pattern.",
        "hi": "अन्य लोग इसी पैटर्न की शिकायत पहले ही कर चुके हैं।",
        "te": "ఇతరులు ఇదే నమూనాను ఇప్పటికే నివేదించారు.",
    },
    "repeat_contact": {
        "en": "They have contacted you several times in a short period.",
        "hi": "उन्होंने थोड़े समय में आपसे कई बार संपर्क किया है।",
        "te": "వారు కొద్ది సమయంలో మీతో పలుమార్లు సంప్రదించారు.",
    },
    "user_doubt": {
        "en": "You felt something was wrong about this contact.",
        "hi": "आपको इस संपर्क में कुछ गड़बड़ लगी।",
        "te": "ఈ సంపర్కంలో ఏదో తప్పు ఉందని మీరు భావించారు.",
    },
}


def render_source(signal: Dict[str, Any], lang: str = DEFAULT_LANGUAGE) -> str:
    """One fused signal -> one sentence a person can read.

    Never returns an internal code. The detail value is used only to pick the
    sentence; if no sentence exists for it, the generic sentence for that source
    is used rather than leaking the code to the screen.
    """
    lang = normalise_language(lang)
    if not isinstance(signal, dict):
        return _SOURCE_SENTENCES["user_doubt"][lang]
    source = str(signal.get("source") or "")
    detail = str(signal.get("detail") or "")

    entry = _SOURCE_SENTENCES.get(f"{source}:{detail}") or _SOURCE_SENTENCES.get(source)
    if entry is None:
        return _SOURCE_SENTENCES["user_doubt"][lang]
    return entry.get(lang) or entry[DEFAULT_LANGUAGE]


def explain_message(result: Dict[str, Any], lang: str = DEFAULT_LANGUAGE) -> Dict[str, Any]:
    """Turn a ``score_message`` payload into a citizen-facing explanation.

    Deliberately drops ``score`` and ``hits``: §2.2 of the Part 1 spec says a
    raw score never reaches the screen, and matched token lists are diagnostics
    for a developer, not advice for a person.
    """
    lang = normalise_language(lang)
    verdict = str(result.get("verdict") or "MODERATE").upper()
    body = _MESSAGE_VERDICT.get(verdict) or _MESSAGE_VERDICT["MODERATE"]
    copy = body.get(lang) or body["en"]

    families = [f for f in (result.get("families_hit") or []) if isinstance(f, str)]
    details = [d for d in (result.get("reason_details") or [])
               if isinstance(d, dict) and d.get("code")]
    first_code_by_family: Dict[str, str] = {}
    for detail in details:
        family = detail.get("family")
        code = detail.get("code")
        if family and code and family not in first_code_by_family:
            first_code_by_family[family] = str(code)
    selected_codes = [first_code_by_family[f] for f in families
                      if f in first_code_by_family]
    if selected_codes:
        sentences = [render_message_reason(code, lang) for code in selected_codes]
    else:
        sentences = [render_family(f, lang) for f in families]
    if not families:
        # Message-specific fallback. Using R_LOW_CONFIDENCE here produced
        # "This clip does not give a clear answer" on a *text message* screen —
        # voice wording leaking into a different surface. Small, but it tells
        # the user the app does not know what it is looking at.
        sentences = [_NO_MESSAGE_SIGNAL[lang]]
    message_codes = sorted({str(d["code"]) for d in details
                            if str(d.get("code")) in MSG_REASON_FAMILY})

    return {
        "verdict": verdict,
        "title": copy["title"],
        "action": copy["action"],
        "reasons": sentences,
        "reason_codes": families,
        "message_reason_codes": message_codes,
        "helpline": HELPLINE,
        "disclaimer": _DISCLAIMER[lang],
        "lang": lang,
        "actionable": verdict in ("HIGH", "CRITICAL"),
    }


_REPORT_COPY = {
    "sent": {
        "en": ("Report sent",
               "Only the category, a severity band and a random token were sent. "
               "No audio, message text or phone number left your phone."),
        "hi": ("रिपोर्ट भेज दी गई",
               "केवल श्रेणी, गंभीरता और एक यादृच्छिक टोकन भेजा गया। आपका ऑडियो, संदेश या फ़ोन नंबर नहीं भेजा गया।"),
        "te": ("నివేదిక పంపబడింది",
               "కేవలం వర్గం, తీవ్రత స్థాయి మరియు యాదృచ్ఛిక టోకెన్ మాత్రమే పంపబడ్డాయి. మీ ఆడియో, సందేశం లేదా ఫోన్ నంబర్ పంపలేదు."),
    },
    "offline": {
        "en": ("Saved on this phone",
               "It will be sent when you are back online. Nothing has left the device yet."),
        "hi": ("इस फ़ोन पर सहेजा गया",
               "ऑनलाइन होने पर भेजा जाएगा। अभी कुछ भी डिवाइस से बाहर नहीं गया।"),
        "te": ("ఈ ఫోన్‌లో సేవ్ చేయబడింది",
               "ఆన్‌లైన్‌లోకి వచ్చినప్పుడు పంపబడుతుంది. ఇంకా ఏమీ పరికరం నుండి బయటకు పోలేదు."),
    },
    "forwarding_failed": {
        # The server accepted the report and failed to pass it on. A 200 is not
        # delivery, and "Report sent" here would be the exact lie Part Four
        # exists to prevent: the citizen believes a report is filed that reached
        # nobody. Says what is true — it is on the server — and what to do now.
        "en": ("Received, but not passed on",
               "The service took your report but could not send it upstream. "
               "It is on the server. Call 1930 so a person hears it now."),
        "hi": ("रिपोर्ट मिली, लेकिन आगे नहीं भेजी जा सकी",
               "सेवा ने रिपोर्ट ली, पर आगे नहीं भेज सकी। यह सर्वर पर है। अभी 1930 पर कॉल करें ताकि किसी व्यक्ति तक बात पहुँचे।"),
        "te": ("నివేదిక అందింది, కానీ ముందుకు పంపబడలేదు",
               "సేవ మీ నివేదికను తీసుకుంది, కానీ ముందుకు పంపలేకపోయింది. అది సర్వర్‌పై ఉంది. ఇప్పుడే 1930కి కాల్ చేయండి."),
    },
    "failed": {
        "en": ("Report not sent",
               "Call 1930 instead. Your data did not leave this phone."),
        "hi": ("रिपोर्ट नहीं भेजी गई",
               "इसके बजाय 1930 पर कॉल करें। आपका डेटा फ़ोन से बाहर नहीं गया।"),
        "te": ("నివేదిక పంపబడలేదు",
               "బదులుగా 1930కి కాల్ చేయండి. మీ డేటా ఫోన్ నుండి బయటకు పోలేదు."),
    },
}


def explain_report(result: Optional[Dict[str, Any]], lang: str = DEFAULT_LANGUAGE,
                   state: str = "sent") -> Dict[str, str]:
    """Citizen-facing copy for the report screen.

    The API returns an event id and a numeric severity. Neither is meaningful to
    a person in distress, and the id looks like an account number. This wrapper
    says what happened and, more importantly, *what did not leave the phone*.
    """
    lang = normalise_language(lang)
    entry = _REPORT_COPY.get(state) or _REPORT_COPY["failed"]
    body = entry.get(lang) or entry["en"]
    out = {"title": body[0], "detail": body[1], "helpline": HELPLINE, "lang": lang}
    fwd = result.get("forwarded") if isinstance(result, dict) else None
    reached = bool(isinstance(fwd, dict) and fwd.get("forwarded"))
    out["reached_network"] = reached
    out["accepted"] = bool(isinstance(result, dict) and result.get("status") == "REPORTED")
    # `accepted but not reached` is its own state, never "sent".
    out["delivered"] = reached
    if out["accepted"] and not reached:
        fb = _REPORT_COPY["forwarding_failed"].get(lang) or _REPORT_COPY["forwarding_failed"]["en"]
        out["title"], out["detail"] = fb
    return out


def catalogue_codes() -> List[str]:
    """All codes that have a translation — used by the coverage test."""
    return sorted(_REASONS)


def all_reason_constants() -> List[str]:
    """Every R_* constant declared in the contract."""
    return sorted(v for k, v in vars(C).items()
                  if k.startswith("R_") and isinstance(v, str))
