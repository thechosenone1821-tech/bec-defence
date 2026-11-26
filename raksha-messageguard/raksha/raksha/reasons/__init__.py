"""Part 1 contract: shared reason catalogue and citizen-facing i18n.

This package is the ONLY piece of Part 1 that MessageGuard (Part 3) consumes.
In the real monorepo it is Part 1's package; here it ships as a contract
stand-in with the same interface, so Part 3 can be developed and evaluated
independently of Part 2. The contract is:

    - ``ReasonCode``      : the reason-code enum (the single shared artefact
                            between Part 2 and Part 3, per the independence note).
    - ``reason_text()``   : citizen-facing explanation for a reason code, in
                            English / Hindi / Telugu, with ``{phrase}``
                            interpolation for the matched text.
    - ``FAMILY_LABELS``   : human labels for the six signal families.
    - ``BAND_LABELS``     : human labels for the four verdict bands.
    - ``BAND_ADVICE``     : the advice line shown to the citizen per band.
    - ``display_lang()``  : maps corpus language tags to a display language
                            (``hinglish`` citizens are shown Hindi).

All content is citizen-facing and deliberately non-technical: a person who
received the message must be able to read why the detector fired.
"""

from __future__ import annotations

from enum import Enum

LANGS: tuple[str, ...] = ("en", "hi", "te")

__all__ = [
    "LANGS",
    "ReasonCode",
    "REASON_TEMPLATES",
    "reason_text",
    "FAMILY_LABELS",
    "BAND_LABELS",
    "BAND_ADVICE",
    "display_lang",
]


class ReasonCode(str, Enum):
    """Reason codes emitted by MessageGuard.

    The ``MSG_`` prefix keeps these codes in a namespace of their own so that
    Part 2's codes (whatever they end up being) can live beside them in the
    shared Part 1 catalogue without collision. Every code names one of the six
    signal families; the matched phrase itself is carried alongside the code
    in the Reason object, never inside the code.
    """

    MSG_CREDENTIAL_REQUEST = "msg.credential.request"
    MSG_AUTHORITY_IMPERSONATION = "msg.authority.impersonation"
    MSG_MONEY_ACTION = "msg.money.action"
    MSG_PRIZE_CLAIM = "msg.prize.claim"
    MSG_URGENCY_PRESSURE = "msg.urgency.pressure"
    MSG_LINK_GRAB = "msg.link.grab"


REASON_TEMPLATES: dict[ReasonCode, dict[str, str]] = {
    ReasonCode.MSG_CREDENTIAL_REQUEST: {
        "en": "The message asks for sensitive details like OTP, PIN or CVV (matched: \u201c{phrase}\u201d). Banks and UPI apps never ask for these.",
        "hi": "संदेश OTP, PIN या CVV जैसी संवेदनशील जानकारी मांग रहा है (मिला: \u201c{phrase}\u201d)। बैंक और UPI ऐप ऐसा कभी नहीं पूछते।",
        "te": "సందేశం OTP, PIN లేదా CVV వంటి సమాచారం అడుగుతోంది (దొరికింది: \u201c{phrase}\u201d). బ్యాంకులు, UPI యాప్‌లు ఇలా ఎప్పుడూ అడగవు.",
    },
    ReasonCode.MSG_AUTHORITY_IMPERSONATION: {
        "en": "Someone claims to be the police, CBI, ED, RBI or a court (matched: \u201c{phrase}\u201d). Real agencies never arrest people over a phone call or WhatsApp.",
        "hi": "कोई खुद को पुलिस, CBI, ED, RBI या अदालत बता रहा है (मिला: \u201c{phrase}\u201d)। असली एजेंसियां फोन या व्हाट्सएप पर गिरफ्तारी नहीं करतीं।",
        "te": "ఎవరో తమను పోలీసు, CBI, ED, RBI లేదా కోర్టు అంటున్నారు (దొరికింది: \u201c{phrase}\u201d). నిజమైన ఏజెన్సీలు ఫోన్‌లో లేదా వాట్సాప్‌లో అరెస్ట్ చేయవు.",
    },
    ReasonCode.MSG_MONEY_ACTION: {
        "en": "The message pushes you to send or pay money (matched: \u201c{phrase}\u201d).",
        "hi": "संदेश आपसे पैसे भेजने या भुगतान करने के लिए कह रहा है (मिला: \u201c{phrase}\u201d)।",
        "te": "సందేశం మిమ్మల్ని డబ్బు పంపమని లేదా చెల్లించమని ఒత్తిడి తెస్తోంది (దొరికింది: \u201c{phrase}\u201d).",
    },
    ReasonCode.MSG_PRIZE_CLAIM: {
        "en": "The message claims you won a lottery, lucky draw or prize (matched: \u201c{phrase}\u201d). You cannot win a draw you never entered.",
        "hi": "संदेश आपके लॉटरी, लकी ड्रॉ या इनाम जीतने का दावा करता है (मिला: \u201c{phrase}\u201d)। जिस ड्रॉ में हिस्सा नहीं लिया, उसमें जीत नहीं सकते।",
        "te": "సందేశం మీరు లాటరీ, లక్కీ డ్రా లేదా బహుమతి గెలిచారని చెబుతోంది (దొరికింది: \u201c{phrase}\u201d). పాల్గొనని డ్రాలో గెలవలేరు.",
    },
    ReasonCode.MSG_URGENCY_PRESSURE: {
        "en": "The message creates false urgency (matched: \u201c{phrase}\u201d) so that you act without thinking.",
        "hi": "संदेश झूठी जल्दबाजी पैदा करता है (मिला: \u201c{phrase}\u201d) ताकि आप सोचे बिना कुछ कर दें।",
        "te": "సందేశం బుద్ధి మాయం చేసే తొందరపాటు కల్పిస్తోంది (దొరికింది: \u201c{phrase}\u201d).",
    },
    ReasonCode.MSG_LINK_GRAB: {
        "en": "The message pushes a suspicious link or shortener (matched: \u201c{phrase}\u201d). The app never opens links — it only pattern-checks them, so nothing is fetched.",
        "hi": "संदेश संदिग्ध लिंक या शॉर्टनर पर जाने को कह रहा है (मिला: \u201c{phrase}\u201d)। ऐप कभी भी लिंक नहीं खोलता — केवल पैटर्न जांच होती है।",
        "te": "సందేశం అనుమానాస్పద లింక్ వైపు నెడుతోంది (దొరికింది: \u201c{phrase}\u201d). యాప్ లింక్ ఎప్పుడూ తెరవదు — ప్యాటర్న్ తనిఖీ మాత్రమే.",
    },
}

FAMILY_LABELS: dict[str, dict[str, str]] = {
    "credential": {
        "en": "Sensitive-info request (OTP / PIN / CVV)",
        "hi": "संवेदनशील जानकारी की मांग (OTP / PIN / CVV)",
        "te": "సమాచారం అభ్యర్థన (OTP / PIN / CVV)",
    },
    "authority": {
        "en": "Police / CBI / ED / RBI impersonation",
        "hi": "पुलिस / CBI / ED / RBI की आड़ में धोखा",
        "te": "పోలీసు / CBI / ED / RBI వేషంలో మోసం",
    },
    "money_action": {
        "en": "Demand to send or pay money",
        "hi": "पैसे भेजने या भुगतान की मांग",
        "te": "డబ్బు పంపాలని లేదా చెల్లించాలని డిమాండ్",
    },
    "prize": {
        "en": "Fake lottery / prize claim",
        "hi": "फर्जी लॉटरी / इनाम का दावा",
        "te": "నకిలీ లాటరీ / బహుమతి వాదన",
    },
    "urgency": {
        "en": "Pressure to act immediately",
        "hi": "तुरंत काम करने का दबाव",
        "te": "వెంటనే చేయాలని ఒత్తిడి",
    },
    "link_grab": {
        "en": "Suspicious link or shortener",
        "hi": "संदिग्ध लिंक या शॉर्टनर",
        "te": "అనుమానాస్పద లింక్ లేదా షార్ట్‌నర్",
    },
}

BAND_LABELS: dict[str, dict[str, str]] = {
    "LOW": {
        "en": "Likely safe",
        "hi": "संभवतः सुरक्षित",
        "te": "బహుశా సురక్షితం",
    },
    "MODERATE": {
        "en": "Be careful",
        "hi": "सावधान रहें",
        "te": "జాగ్రత్తగా ఉండండి",
    },
    "HIGH": {
        "en": "Likely scam",
        "hi": "घोटाला होने की संभावना",
        "te": "మోసం అయ్యే అవకాశం ఎక్కువ",
    },
    "CRITICAL": {
        "en": "Almost certainly a scam",
        "hi": "लगभग निश्चित रूप से घोटाला",
        "te": "దాదాపు నిశ్చయంగా మోసం",
    },
}

BAND_ADVICE: dict[str, dict[str, str]] = {
    "LOW": {
        "en": "No scam signals found. Stay alert anyway — this check only knows the patterns listed in EVALS.md.",
        "hi": "कोई घोटाले का संकेत नहीं मिला। फिर भी सतर्क रहें — यह जांच केवल ज्ञात पैटर्न को पहचानती है।",
        "te": "మోసపు సూచనలు కనపడలేదు. అయినా జాగ్రత్తగా ఉండండి — ఈ తనిఖీ తెలిసిన ప్యాటర్న్‌లను మాత్రమే గుర్తిస్తుంది.",
    },
    "MODERATE": {
        "en": "Some risky words were found. Do not share OTP, PIN or money. Verify by calling the official number printed on your card or bill.",
        "hi": "कुछ जोखिम भरे शब्द मिले। OTP, PIN या पैसे साझा न करें। कार्ड या बिल पर छपे आधिकारिक नंबर पर कॉल करके जांचें।",
        "te": "కొన్ని ప్రమాదకర పదాలు కనపడ్డాయి. OTP, PIN, డబ్బు షేర్ చేయకండి. మీ కార్డు లేదా బిల్లుపై ఉన్న అధికారిక నంబర్‌కు కాల్ చేసి తెలుసుకోండి.",
    },
    "HIGH": {
        "en": "This looks like a known scam script. Do not reply, do not pay, do not share OTP or PIN. Report to 1930 (cyber fraud helpline).",
        "hi": "यह ज्ञात घोटाले के पैटर्न जैसा दिखता है। जवाब न दें, पैसे न भेजें, OTP या PIN साझा न करें। 1930 (साइबर फ्रॉड हेल्पलाइन) पर रिपोर्ट करें।",
        "te": "ఇది తెలిసిన మోసపు స్క్రిప్టు లాగా ఉంది. స్పందించకండి, డబ్బు పంపకండి, OTP లేదా PIN షేర్ చేయకండి. 1930కు నివేదించండి.",
    },
    "CRITICAL": {
        "en": "This is almost certainly a scam script. Do not reply, do not pay, do not share OTP or PIN. Report to 1930 and warn your family.",
        "hi": "यह लगभग निश्चित रूप से घोटाले का पैटर्न है। जवाब न दें, पैसे न भेजें, OTP या PIN साझा न करें। 1930 पर रिपोर्ट करें और परिवार को चेतावनी दें।",
        "te": "ఇది దాదాపు నిశ్చయంగా మోసపు స్క్రిప్టు. స్పందించకండి, డబ్బు పంపకండి, OTP లేదా PIN షేర్ చేయకండి. 1930కు నివేదించండి, కుటుంబాన్ని కూడా హెచ్చరించండి.",
    },
}


def reason_text(code: ReasonCode, lang: str = "en", phrase: str | None = None) -> str:
    """Render a citizen-facing reason sentence in the requested language.

    ``phrase`` is interpolated into the ``{phrase}`` slot. Unknown languages
    fall back to English; unknown codes raise ``KeyError`` (a missing code is a
    contract bug, not something to hide).
    """
    lang = lang if lang in LANGS else "en"
    template = REASON_TEMPLATES[code][lang]
    return template.format(phrase=phrase if phrase else "-")


def display_lang(lang: str) -> str:
    """Map a corpus/detector language tag to a display language.

    ``hinglish`` (Hindi written in Latin script) citizens are shown Hindi text.
    """
    if lang == "hinglish":
        return "hi"
    return lang if lang in LANGS else "en"
