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
    sentences = [render_family(f, lang) for f in families]
    if not families:
        # Message-specific fallback. Using R_LOW_CONFIDENCE here produced
        # "This clip does not give a clear answer" on a *text message* screen —
        # voice wording leaking into a different surface. Small, but it tells
        # the user the app does not know what it is looking at.
        sentences = [_NO_MESSAGE_SIGNAL[lang]]

    return {
        "verdict": verdict,
        "title": copy["title"],
        "action": copy["action"],
        "reasons": sentences,
        "reason_codes": families,
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
    if isinstance(result, dict) and result.get("forwarded"):
        fwd = result["forwarded"]
        out["reached_network"] = bool(isinstance(fwd, dict) and fwd.get("forwarded"))
    return out


def catalogue_codes() -> List[str]:
    """All codes that have a translation — used by the coverage test."""
    return sorted(_REASONS)


def all_reason_constants() -> List[str]:
    """Every R_* constant declared in the contract."""
    return sorted(v for k, v in vars(C).items()
                  if k.startswith("R_") and isinstance(v, str))
