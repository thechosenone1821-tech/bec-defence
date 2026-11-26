"""Token sets for the six signal families in English, Hindi, Telugu + Hinglish.

Matching philosophy (mirrors the spec's design):

- Match REQUESTS, not mentions. Genuine bank messages say "never share your
  OTP"; scammers say "share your OTP". So credential tokens are verb phrases
  (share/send/tell/confirm/batao/cheppandi + OTP/PIN/CVV) and approve/accept
  collect-request phrases — a bare mention of "OTP" never fires anything.
- Impersonation is an entity-plus-role pairing ("CBI" + "officer"), so a
  genuine "as per RBI guidelines" line cannot fire the authority family.
- Links are PATTERN-MATCHED, never fetched (spec failure-mode 5): only
  shortener domains and scam-favourite TLDs are treated as link_grab signals.
  A genuine bank URL (official domain, no shortener) does not fire.
- A negation-guard list ("do not share", "शेयर न करें", "షేర్ చేయవద్దు" ...)
  suppresses the credential family when the classic genuine bank warning is
  present. This trades a little recall (a scam that also repeats the bank's
  warning phrasing may slip past credential) for a big FP win.

Normalization is casefold + NFKC + zero-width strip + whitespace collapse —
no de-obfuscation. Spaced-out text ("O T P") and homoglyphs remain known
failure modes, stated in the module docstring and measured in EVALS.md.

Matching universes (real scam SMS mix scripts, e.g. "आपका OTP बताइए"):
    en / hinglish -> en + hinglish sets
    hi            -> hi + en sets
    te            -> te + en sets
"""

from __future__ import annotations

import re
import unicodedata
from functools import lru_cache
from functools import lru_cache

FAMILIES: tuple[str, ...] = (
    "credential",
    "authority",
    "money_action",
    "prize",
    "urgency",
    "link_grab",
)

LANG_UNIVERSES: dict[str, tuple[str, ...]] = {
    "en": ("en", "hinglish"),
    "hinglish": ("en", "hinglish"),
    "hi": ("hi", "en"),
    "te": ("te", "en"),
}

__all__ = [
    "FAMILIES",
    "LANG_UNIVERSES",
    "normalize",
    "iter_phrase_hits",
    "iter_pattern_hits",
    "GUARDS",
    "PHRASES",
    "PATTERNS",
    "PAIR_RULES",
]

# --------------------------------------------------------------------------
# normalization + matching helpers
# --------------------------------------------------------------------------

_ZERO_WIDTH = dict.fromkeys(map(ord, "\u200b\u200c\u200d\u200e\u200f\u2060\ufeff"))


def normalize(text: str) -> str:
    """Casefold + NFKC, strip zero-width characters, collapse whitespace."""
    text = unicodedata.normalize("NFKC", text).casefold()
    text = text.translate(_ZERO_WIDTH)
    return " ".join(text.split())


def _is_word_char(ch: str) -> bool:
    """Letters, digits and Indic combining marks count as word characters.

    Using marks as word characters means inflected forms must be authored as
    separate tokens ("भेजें", "भेजो", "भेजिए") — prefix stems like "भेज" will
    not match "भेजें". That is deliberate: it prevents accidental stem matches
    across unrelated words.
    """
    return ch.isalnum() or unicodedata.category(ch) in ("Mn", "Mc", "Me")


@lru_cache(maxsize=None)
def _norm_phrase(phrase: str) -> str:
    """Normalize a token once, memoized.

    Tokens are stored verbatim (including zero-width joiners used inside
    Telugu conjuncts); matching runs against the normalized message, so the
    token side must be normalized identically or those tokens silently
    never match. This was a real bug found by the corpus FP review.
    """
    return normalize(phrase)


def iter_phrase_hits(text: str, phrases: tuple[str, ...]) -> list[tuple[int, int, str]]:
    """Find word-bounded occurrences of any phrase. Returns (start, end, phrase)."""
    hits: list[tuple[int, int, str]] = []
    for phrase in phrases:
        phrase = _norm_phrase(phrase)
        n = len(phrase)
        if n == 0:
            continue
        pos = text.find(phrase)
        while pos != -1:
            before_ok = pos == 0 or not _is_word_char(text[pos - 1])
            after = pos + n
            after_ok = after >= len(text) or not _is_word_char(text[after])
            if before_ok and after_ok:
                hits.append((pos, pos + n, phrase))
            pos = text.find(phrase, pos + 1)
    hits.sort(key=lambda h: (h[0], h[1], h[2]))
    return hits


def iter_pattern_hits(text: str, patterns: tuple[re.Pattern, ...]) -> list[tuple[int, int, str]]:
    hits: list[tuple[int, int, str]] = []
    for pat in patterns:
        for m in pat.finditer(text):
            hits.append((m.start(), m.end(), m.group(0)))
    hits.sort(key=lambda h: (h[0], h[1], h[2]))
    return hits


# --------------------------------------------------------------------------
# negation guards (genuine-bank-warning suppressors)
# --------------------------------------------------------------------------

GUARDS: dict[str, tuple[str, ...]] = {
    "en": (
        "do not share",
        "don't share",
        "do not disclose",
        "never share",
        "never ask",
        "we never",
        "should not be shared",
        "not to be shared",
        "no one from the bank",
        "ignore if",
        "share it with anyone",
    ),
    "hi": (
        "शेयर न करें",
        "शेयर ना करें",
        "साझा न करें",
        "किसी के साथ शेयर न",
        "किसी को न बताएं",
        "किसी को नहीं बताएं",
        "नहीं बताएं",
        "बताएं नहीं",
        "बताना मना है",
        "कभी साझा न",
        "कभी नहीं पूछते",
        "गोपनीय रखें",
    ),
    "te": (
        "షేర్ చేయవద్దు",
        "షేర్ చేయకండి",
        "ఎవరితో షేర్",
        "ఎవరికీ చెప్పవద్దు",
        "ఎవరికీ చెప్పొద్దు",
        "చెప్పకండి",
        "చెప్పవద్దు",
        "డిస్‌క్లోజ్ చేయవద్దు",
        "ఎవరూ అడగరు",
        "ఎవరినీ అడగరు",
    ),
    "hinglish": (
        "share na karein",
        "share mat karo",
        "share na kare",
        "kisi ko na batayein",
        "kisi ko nahi batana",
        "kabhi share na",
    ),
}


def guard_active(langs: tuple[str, ...], norm_text: str) -> bool:
    """True if any known genuine-warning guard phrase is present."""
    for lang in langs:
        for g in GUARDS.get(lang, ()):
            if _norm_phrase(g) in norm_text:
                return True
    return False


# --------------------------------------------------------------------------
# phrase tokens, per family, per language
# --------------------------------------------------------------------------

PHRASES: dict[str, dict[str, tuple[str, ...]]] = {
    "credential": {
        "en": (
            "share your otp",
            "share the otp",
            "share otp",
            "send your otp",
            "send the otp",
            "send otp",
            "tell me the otp",
            "tell the otp",
            "tell me your otp",
            "give your otp",
            "give the otp",
            "confirm your otp",
            "confirm the otp",
            "share your cvv",
            "share your pin",
            "share the cvv",
            "tell me your pin",
            "enter your upi pin",
            "enter your pin at",
            "otp needed to release",
            "otp to release",
            "otp confirm karein",
            "approve the collect request",
            "approve this collect request",
            "accept the collect request",
            "accept this collect request",
            "approve the payment request",
            "accept the payment request",
            "approve the request to receive",
            "accept the request to receive",
            "approve the request and receive",
        ),
        "hi": (
            "ओटीपी बताइए",
            "ओटीपी बताओ",
            "ओटीपी भेजिए",
            "ओटीपी भेजो",
            "ओटीपी शेयर करें",
            "ओटीपी शेयर करो",
            "ओटीपी दीजिए",
            "ओटीपी चाहिए",
            "ओटीपी कन्फर्म करें",
            "ओटीपी डालिए",
            "पिन बताइए",
            "पिन बताओ",
            "पिन डालिए",
            "पिन शेयर करें",
            "सीवीवी बताइए",
            "सीवीवी भेजिए",
            "सीवीवी शेयर करें",
            "यूपीआई पिन बताइए",
            "यूपीआई पिन डालिए",
            "यूपीआई पिन शेयर करें",
            "कलेक्ट रिक्वेस्ट अप्रूव करें",
            "कलेक्ट रिक्वेस्ट स्वीकार करें",
            "रिक्वेस्ट अप्रूव करके पैसे पाएं",
            "अप्रूव करके पैसे पाएं",
            # mixed-script variants (real SMS write "OTP" in Latin inside Hindi)
            "otp बताइए",
            "otp बताओ",
            "otp भेजिए",
            "otp भेजो",
            "otp शेयर करें",
            "otp चाहिए",
            "otp कन्फर्म करें",
        ),
        "te": (
            "ఓటీపీ చెప్పండి",
            "ఓటీపీ పంపండి",
            "ఓటీపీ షేర్ చేయండి",
            "ఓటీపీ ఇవ్వండి",
            "ఓటీపీ కావాలి",
            "ఓటీపీ కన్ఫర్మ్ చేయండి",
            "ఓటీపీ నమోదు చేయండి",
            "పిన్ చెప్పండి",
            "పిన్ షేర్ చేయండి",
            "సీవీవీ చెప్పండి",
            "సీవీవీ పంపండి",
            "యూపీఐ పిన్ చెప్పండి",
            "యూపీఐ పిన్ నమోదు చేయండి",
            "యూపీఐ పిన్ షేర్ చేయండి",
            "కలెక్ట్ రిక్వెస్ట్ అప్రూవ్ చేయండి",
            "కలెక్ట్ రిక్వెస్ట్ స్వీకరించండి",
            "రిక్వెస్ట్ అప్రూవ్ చేసి డబ్బు",
            "అప్రూవ్ చేసి డబ్బు పొందండి",
            # mixed-script variants
            "otp చెప్పండి",
            "otp షేర్ చేయండి",
            "otp పంపండి",
            "otp కావాలి",
        ),
        "hinglish": (
            "otp batao",
            "otp bata do",
            "otp bhejo",
            "otp do mujhe",
            "otp chahiye",
            "otp share karo",
            "otp confirm karo",
            "pin batao",
            "cvv batao",
            "cvv share karo",
            "upi pin batao",
            "upi pin daalo",
            "collect request approve karo",
            "collect request accept karo",
            "request approve karke paisa",
            "approve karke paise",
        ),
    },
    "authority": {
        "en": (
            "digital arrest",
            "arrest warrant",
            "arrest warrant issued",
            "warrant issued against you",
            "non-bailable warrant",
            "non-bailable offence",
            "cbi officer",
            "cbi team",
            "cbi notice",
            "ed officer",
            "ed notice",
            "ed summons",
            "enforcement directorate",
            "rbi officer",
            "rbi agent",
            "rbi digital fraud",
            "rbi fraud cell",
            "account frozen by rbi",
            "rbi is freezing",
            "cyber police",
            "cyber cell",
            "crime branch",
            "narcotics control bureau",
            "narcotics case",
            "customs officer",
            "parcel seized",
            "parcel is seized",
            "parcel contains drugs",
            "parcel contains undeclared",
            "money laundering case",
            "hawala transaction",
            "supreme court notice",
            "court notice",
            "virtual hearing",
            "video hearing",
            "video inquiry",
            "police officer is coming",
            "police will arrest",
            "police custody",
            "fir filed against",
            "fir against your",
            "custody till",
            "trai notice",
        ),
        "hi": (
            "डिजिटल अरेस्ट",
            "गिरफ्तारी वारंट",
            "वारंट जारी हो चुका",
            "वारंट जारी",
            "गैर-जमानती वारंट",
            "गैर जमानती",
            "सीबीआई अधिकारी",
            "सीबीआई टीम",
            "सीबीआई नोटिस",
            "ईडी अधिकारी",
            "ईडी समन",
            "प्रवर्तन निदेशालय",
            "आरबीआई अधिकारी",
            "आरबीआई एजेंट",
            "आरबीआई डिजिटल धोखाधड़ी",
            "आरबीआई धोखाधड़ी सेल",
            "खाता फ्रीज",
            "खाता फ्रोजन",
            "आरबीआई फ्रीज",
            "साइबर पुलिस",
            "साइबर सेल",
            "क्राइम ब्रांच",
            "नारकोटिक्स कंट्रोल ब्यूरो",
            "नारकोटिक्स केस",
            "कस्टम अधिकारी",
            "पार्सल जब्त",
            "पार्सल ज़ब्त",
            "मनी लॉन्ड्रिंग केस",
            "हवाला लेनदेन",
            "सुप्रीम कोर्ट नोटिस",
            "कोर्ट नोटिस",
            "वर्चुअल सुनवाई",
            "वीडियो सुनवाई",
            "वीडियो जांच",
            "पुलिस गिरफ्तार",
            "पुलिस हिरासत",
            "एफआईआर दर्ज",
            "ट्राई नोटिस",
            # mixed-script
            "cbi अधिकारी",
            "rbi अधिकारी",
            "ed अधिकारी",
        ),
        "te": (
            "డిజిటల్ అరెస్ట్",
            "డిజిటల్ అరెస్ట్లో",
            "అరెస్ట్ వారెంట్",
            "వారెంట్ జారీ",
            "నాన్-బెయిలబుల్",
            "సీబీఐ అధికారి",
            "సీబీఐ టీమ్",
            "సీబీఐ నోటీసు",
            "ఈడీ అధికారి",
            "ఈడీ సమన్లు",
            "ఎన్‌ఫోర్స్‌మెంట్ డైరెక్టరేట్",
            "ఆర్బీఐ అధికారి",
            "ఆర్బీఐ ఏజెంట్",
            "ఖాతా ఫ్రీజ్",
            "ఖాతా ఫ్రోజన్",
            "ఆర్బీఐ ఫ్రీజ్",
            "సైబర్ పోలీసులు",
            "సైబర్ సెల్",
            "క్రైమ్ బ్రాంచ్",
            "నార్కోటిక్స్ కంట్రోల్ బ్యూరో",
            "నార్కోటిక్స్ కేసు",
            "కస్టమ్స్ అధికారి",
            "పార్సెల్ సీజ్",
            "పార్సెల్ స్వాధీనం",
            "మనీ లాండ్రింగ్ కేసు",
            "హవాలా లావాదేవీ",
            "సుప్రీం కోర్టు నోటీసు",
            "కోర్టు నోటీసు",
            "వర్చువల్ హెయరింగ్",
            "వీడియో హెయరింగ్",
            "వీడియో విచారణ",
            "పోలీసులు అరెస్ట్",
            "పోలీసు కస్టడీ",
            "ఎఫ్ఐఆర్ నమోదు",
            "ట్రాయ్ నోటీసు",
            # mixed-script
            "cbi అధికారి",
            "rbi అధికారి",
        ),
        "hinglish": (
            "digital arrest",
            "arrest warrant",
            "cbi officer",
            "cbi team",
            "ed officer",
            "rbi officer",
            "police warrant",
            "police case",
            "police aayegi",
            "police pakad",
            "cyber cell",
            "crime branch",
            "parcel seized",
            "customs officer",
            "account freeze",
            "bank freeze",
            "narcotics case",
        ),
    },
    "money_action": {
        "en": (
            "processing fee",
            "processing charge",
            "registration fee",
            "documentation fee",
            "advance fee",
            "clearance fee",
            "clearance charge",
            "delivery charge",
            "delivery fee",
            "membership fee",
            "transfer charge",
            "transfer fee",
            "verification charge",
            "verification fee",
            "activation fee",
            "reactivation charge",
            "reactivation fee",
            "token amount",
            "bail money",
            "bail amount",
            "pay bail",
            "fine of rs",
            "pay the fine",
            "penalty of rs",
            "customs duty",
            "customs fine",
            "gst charge",
            "gst fee",
            "income tax charge",
            "release your refund",
            "release the refund",
            "release the amount",
            "refund processing",
            "validation charge",
            "correction fee",
            "settlement amount",
            "settlement of rs",
            "deposit rs",
            "deposit the amount",
            "send rs",
            "send money to",
            "transfer the amount",
            "transfer rs",
            "pay the fee",
            "pay the charge",
            "pay the amount",
            "must be transferred",
            "must be deposited",
            "fee must be paid",
        ),
        "hi": (
            "प्रोसेसिंग फीस",
            "प्रोसेसिंग चार्ज",
            "रजिस्ट्रेशन फीस",
            "डॉक्यूमेंटेशन फीस",
            "एडवांस फीस",
            "क्लीयरेंस फीस",
            "क्लीयरेंस चार्ज",
            "डिलीवरी चार्ज",
            "मेंबरशिप फीस",
            "ट्रांसफर चार्ज",
            "वेरिफिकेशन चार्ज",
            "वेरिफिकेशन फीस",
            "एक्टिवेशन फीस",
            "टोकन अमाउंट",
            "जमानत",
            "जमानत राशि",
            "जमानत के पैसे",
            "जुर्माना",
            "जुर्माना भरें",
            "पेनल्टी",
            "कस्टम ड्यूटी",
            "कस्टम जुर्माना",
            "जीएसटी चार्ज",
            "इनकम टैक्स चार्ज",
            "रिफंड जारी करने",
            "रिफंड प्रोसेसिंग",
            "राशि जमा करें",
            "रकम जमा करें",
            "रुपये भेजें",
            "रुपए भेजें",
            "पैसे भेजें",
            "पैसे ट्रांसफर करें",
            "रकम ट्रांसफर",
            "फीस भरनी होगी",
            "फीस जमा करें",
            "चार्ज भरना होगा",
            "शुल्क भरें",
            "राशि भेजें",
        ),
        "te": (
            "ప్రాసెసింగ్ ఫీజు",
            "ప్రాసెసింగ్ ఛార్జ్",
            "రిజిస్ట్రేషన్ ఫీజు",
            "డాక్యుమెంటేషన్ ఫీజు",
            "అడ్వాన్స్ ఫీజు",
            "క్లియరెన్స్ ఫీజు",
            "క్లియరెన్స్ ఛార్జ్",
            "డెలివరీ ఛార్జ్",
            "మెంబర్‌షిప్ ఫీజు",
            "ట్రాన్స్‌ఫర్ ఛార్జ్",
            "వెరిఫికేషన్ ఛార్జ్",
            "వెరిఫికేషన్ ఫీజు",
            "యాక్టివేషన్ ఫీజు",
            "టోకెన్ మొత్తం",
            "బెయిల్ డబ్బు",
            "బెయిల్ మొత్తం",
            "జరిమానా",
            "జరిమానా చెల్లించండి",
            "జరిమానా కట్టండి",
            "పెనాల్టీ",
            "కస్టమ్స్ డ్యూటీ",
            "కస్టమ్స్ జరిమానా",
            "జీఎస్టీ ఛార్జ్",
            "ఇన్‌కమ్ ట్యాక్స్ ఛార్జ్",
            "రీఫండ్ ప్రాసెసింగ్",
            "మొత్తం జమ చేయండి",
            "డబ్బు పంపండి",
            "రూపాయలు పంపండి",
            "డబ్బు ట్రాన్స్‌ఫర్ చేయండి",
            "ఫీజు కట్టాలి",
            "ఫీజు జమ చేయండి",
            "ఛార్జ్ కట్టాలి",
            "డిపాజిట్ చేయండి",
            "రకం పంపండి",
        ),
        "hinglish": (
            "processing fee",
            "paisa bhejo",
            "paise bhejo",
            "paisa transfer karo",
            "paise transfer karo",
            "rupaye bhejo",
            "fee jama karo",
            "fee bhejo",
            "bail ke paise",
            "jurmana bharo",
            "fine bharo",
            "customs duty",
            "verification charge",
            "token amount",
            "settlement amount",
            "paise jama karo",
        ),
    },
    "prize": {
        "en": (
            "you have won",
            "you are the winner",
            "won the lottery",
            "lottery winner",
            "lucky draw",
            "your number won",
            "your number has been selected",
            "your name has been selected",
            "your number is selected",
            "kbc lottery",
            "kbc winner",
            "jio lucky draw",
            "whatsapp lucky draw",
            "sim card lucky draw",
            "prize of rs",
            "prize amount of",
            "claim your prize",
            "claim the prize",
            "jackpot of",
            "crore jackpot",
            "prize money of",
        ),
        "hi": (
            "आपने जीता",
            "आप जीते हैं",
            "आप विजेता",
            "आपका नंबर चुना गया",
            "आपका नंबर जीता",
            "आपका नाम चुना गया",
            "लकी ड्रॉ",
            "जियो लकी ड्रॉ",
            "व्हाट्सएप लकी ड्रॉ",
            "केबीसी लॉटरी",
            "केबीसी विजेता",
            "लॉटरी विजेता",
            "इनाम राशि",
            "इनाम का दावा",
            "करोड़ का जैकपॉट",
            "बधाई हो आपने",
            "पुरस्कार राशि",
            "लॉटरी में जीत",
        ),
        "te": (
            "మీరు గెలిచారు",
            "బహుమతి గెలిచారు",
            "మీరు విజేత",
            "మీ నంబర్ గెలిచింది",
            "మీ నంబర్ ఎంపిక",
            "మీ పేరు ఎంపిక",
            "లక్కీ డ్రా",
            "లక్కీ డ్రాలో",
            "జియో లక్కీ డ్రా",
            "వాట్సాప్ లక్కీ డ్రా",
            "కెబిసి లాటరీ",
            "కెబిసి విజేత",
            "లాటరీ విజేత",
            "బహుమతి మొత్తం",
            "బహుమతి క్లెయిమ్",
            "కోట్ల జాక్‌పాట్",
            "అభినందనలు మీరు గెలిచారు",
            "లాటరీలో గెలుపు",
        ),
        "hinglish": (
            "aap jeet gaye",
            "aap jeete hain",
            "aapka number jeeta",
            "aapka number chuna gaya",
            "lucky draw",
            "kbc lottery",
            "kbc winner",
            "lottery jeeti hai",
            "jio lucky draw",
            "prize claim karein",
            "25 lakh prize",
        ),
    },
    "urgency": {
        "en": (
            "within 24 hours",
            "in 24 hours",
            "next 24 hours",
            "24 hours or",
            "24 hours left",
            "only 24 hours",
            "24 hours",
            "within 2 hours",
            "within 1 hour",
            "last warning",
            "final warning",
            "final notice",
            "last notice",
            "final reminder",
            "will be blocked",
            "will be deactivated",
            "will be suspended",
            "will be disconnected",
            "will be closed",
            "will be frozen",
            "will be cancelled",
            "will be terminated",
            "will be cut",
            "power will be cut",
            "connection will be cut",
            "else your",
            "otherwise your",
            "or your account will",
            "act now",
            "act immediately",
            "immediately or",
            "expires today",
            "expiring today",
            "expires tonight",
            "expires in 24",
            "do not call",
        ),
        "hi": (
            "24 घंटे",
            "24 घंटे के भीतर",
            "2 घंटे के भीतर",
            "अंतिम चेतावनी",
            "आखिरी चेतावनी",
            "अंतिम नोटिस",
            "आखिरी मौका",
            "ब्लॉक हो जाएगा",
            "ब्लॉक होने वाला",
            "बंद हो जाएगा",
            "बंद कर दिया जाएगा",
            "निलंबित कर दिया",
            "डिस्कनेक्ट",
            "काट दिया जाएगा",
            "काट दी जाएगी",
            "फ्रीज हो जाएगा",
            "रद्द कर दिया जाएगा",
            "वरना",
            "नहीं करते तो",
            "आज रात",
            "आज ही रात",
            "आज शाम तक",
            "आज ही नहीं तो",
            "स्थायी रूप से बंद",
            "कॉल न करें",
        ),
        "te": (
            "24 గంటలు",
            "24 గంటల",
            "24 గంటల్లో",
            "24 గంటల లోపు",
            "2 గంటల్లో",
            "2 గంటల్లోపు",
            "చివరి హెచ్చరిక",
            "చివరి నోటీసు",
            "చివరి అవకాశం",
            "బ్లాక్ అవుతుంది",
            "బ్లాక్ చేస్తారు",
            "మూసివేయబడుతుంది",
            "నిలిపివేయబడుతుంది",
            "డిస్‌కనెక్ట్",
            "తెగించబడుతుంది",
            "తెగించి వేస్తారు",
            "కట్ చేస్తారు",
            "ఫ్రీజ్ అవుతుంది",
            "రద్దు చేయబడుతుంది",
            "రద్దు చేస్తారు",
            "లేదంటే",
            "చెల్లించకపోతే",
            "ఈ రాత్రి",
            "ఈ రోజు సాయంత్రం",
            "ఈ రోజే",
            "శాశ్వతంగా మూసివేయబడుతుంది",
            "కాల్ చేయకండి",
        ),
        "hinglish": (
            "24 ghante",
            "24 ghante ke andar",
            "2 ghante ke andar",
            "aakhri chetavni",
            "last warning",
            "final notice",
            "account block",
            "block ho jayega",
            "band ho jayega",
            "warna",
            "aaj raat",
            "aaj raat tak",
            "aaj hi nahi to",
            "call mat karo",
        ),
    },
    "link_grab": {
        "en": (
            "click here",
            "click the link",
            "click on the link",
            "click this link",
            "click below",
            "tap here",
            "tap the link",
            "open the link",
            "verify now",
            "verify immediately",
            "update now",
            "reactivate now",
            "login now",
            "log in now",
            "sign in now",
            "fill the form at",
            "form at the link",
            "download from the link",
            "click to update",
            "click to verify",
            "click to unblock",
            "click to reactivate",
            "link below to",
            "at the link below",
        ),
        "hi": (
            "यहां क्लिक करें",
            "लिंक पर क्लिक करें",
            "नीचे लिंक",
            "नीचे दिए लिंक",
            "लिंक खोलें",
            "यह लिंक खोलें",
            "तुरंत वेरिफाई करें",
            "वेरिफाई करें",
            "लॉगिन करें",
            "फॉर्म भरें",
            "लिंक से फॉर्म भरें",
            "क्लिक करके अपडेट",
            "क्लिक करके सत्यापित",
            "क्लिक करें और",
        ),
        "te": (
            "ఇక్కడ క్లిక్ చేయండి",
            "లింక్ పై క్లిక్ చేయండి",
            "లింక్‌పై క్లిక్ చేయండి",
            "క్రింద లింక్",
            "లింక్ ఓపెన్ చేయండి",
            "ఈ లింక్ ఓపెన్ చేయండి",
            "వెంటనే వెరిఫై చేయండి",
            "వెరిఫై చేయండి",
            "లాగిన్ చేయండి",
            "ఫారం నింపండి",
            "లింక్‌లో ఫారం",
            "క్లిక్ చేసి అప్‌డేట్",
            "క్లిక్ చేసి వెరిఫై",
        ),
        "hinglish": (
            "click karo",
            "link par click",
            "link pe click",
            "link kholo",
            "verify karo",
            "abhi verify karo",
            "login karo",
            "form bharo",
            "yahan click karo",
            "abhi click karo",
        ),
    },
}

# --------------------------------------------------------------------------
# regex patterns (script-agnostic)
# --------------------------------------------------------------------------

_SHORTENER_RE = re.compile(
    r"(?<![\w-])(?:bit\.ly|tinyurl\.com|cutt\.ly|rb\.gy|tiny\.cc|is\.gd|goo\.gl|ow\.ly|"
    r"t\.ly|bit\.do|rebrand\.ly|shorturl\.at|urlz\.fr|clck\.ru|t\.co)(?:/\S*)?"
)

# scam-favourite vanity TLDs; dot-anchored so the plain word "online" never matches
_SCAM_TLD_RE = re.compile(r"\b\S*\.(?:xyz|top|icu|club)(?:/\S*)?\b")

PATTERNS: dict[str, tuple[re.Pattern, ...]] = {
    "credential": (),
    "authority": (),
    "money_action": (),
    "prize": (),
    "urgency": (),
    "link_grab": (_SHORTENER_RE, _SCAM_TLD_RE),
}

# --------------------------------------------------------------------------
# pair rules, per family, per language:
#     PAIR_RULES[family][lang] = ((entities), (partners))
# Both an entity and a partner must appear (word-bounded) for the family to
# fire via a pair. Keeping the rules family-keyed prevents, for example, the
# credential "otp + share" pair from being attributed to authority.
# --------------------------------------------------------------------------

PAIR_RULES: dict[str, dict[str, tuple[tuple[tuple[str, ...], tuple[str, ...]], ...]]] = {
    "credential": {
        "en": (
            (
                ("otp", "cvv", "pin", "upi pin", "one time password"),
                (
                    "share",
                    "send",
                    "tell",
                    "give",
                    "confirm",
                    "confirming",
                    "sharing",
                    "sending",
                    "telling",
                    "giving",
                    "entering",
                    "share karo",
                    "batao",
                    "bata do",
                ),
            ),
            (("collect request", "payment request"), ("approve", "accept", "approving", "accepting")),
        ),
        "hi": (
            (
                ("ओटीपी", "सीवीवी", "पिन", "यूपीआई पिन", "otp"),
                ("शेयर", "भेजें", "भेजो", "भेजिए", "बताइए", "बताओ", "दीजिए", "चाहिए", "कन्फर्म"),
            ),
            (("कलेक्ट रिक्वेस्ट", "पेमेंट रिक्वेस्ट"), ("अप्रूव", "स्वीकार")),
        ),
        "te": (
            (
                ("ఓటీపీ", "సీవీవీ", "పిన్", "యూపీఐ పిన్", "otp"),
                ("షేర్", "పంపండి", "చెప్పండి", "ఇవ్వండి", "కావాలి", "కన్ఫర్మ్"),
            ),
            (("కలెక్ట్ రిక్వెస్ట్", "పేమెంట్ రిక్వెస్ట్"), ("అప్రూవ్", "స్వీకరించ")),
        ),
        "hinglish": (
            (("otp", "cvv", "pin", "upi pin"), ("share", "batao", "bhejo", "do mujhe", "chahiye", "confirm")),
            (("collect request", "payment request"), ("approve", "accept")),
        ),
    },
    "authority": {
        "en": (
            (
                ("cbi", "ed", "rbi", "police", "narcotics", "customs", "trai", "court", "cyber cell"),
                (
                    "officer",
                    "agent",
                    "team",
                    "warrant",
                    "arrest",
                    "arrested",
                    "arresting",
                    "raid",
                    "freeze",
                    "frozen",
                    "freezing",
                    "seized",
                    "custody",
                    "summons",
                    "investigation",
                    "inquiry",
                    "suspend",
                    "suspended",
                    "deactivate",
                    "deactivated",
                    "disconnected",
                    "chargesheet",
                ),
            ),
            (
                ("aadhaar", "pan", "number", "sim", "account"),
                (
                    "money laundering",
                    "fraud case",
                    "illegal activity",
                    "used in fraud",
                    "linked to fraud",
                    "hawala",
                    "betting",
                    "illegal betting",
                ),
            ),
        ),
        "hi": (
            (
                (
                    "पुलिस",
                    "सीबीआई",
                    "ईडी",
                    "आरबीआई",
                    "नारकोटिक्स",
                    "कस्टम",
                    "कोर्ट",
                    "अदालत",
                    "ट्राई",
                    "cbi",
                    "ed",
                    "rbi",
                ),
                (
                    "अधिकारी",
                    "एजेंट",
                    "टीम",
                    "वारंट",
                    "गिरफ्तार",
                    "गिरफ्तारी",
                    "छापा",
                    "फ्रीज",
                    "फ्रोजन",
                    "जब्त",
                    "हिरासत",
                    "जांच",
                    "समन",
                    "निलंबित",
                    "डिस्कनेक्ट",
                ),
            ),
            (
                ("आधार", "पैन", "नंबर", "सिम", "खाता"),
                ("मनी लॉन्ड्रिंग", "धोखाधड़ी केस", "धोखाधड़ी का", "हवाला", "अवैध", "सट्टा", "गैर कानूनी"),
            ),
        ),
        "te": (
            (
                (
                    "పోలీసులు",
                    "పోలీసు",
                    "పోలీస్",
                    "సీబీఐ",
                    "ఈడీ",
                    "ఆర్బీఐ",
                    "నార్కోటిక్స్",
                    "కస్టమ్స్",
                    "కోర్టు",
                    "ట్రాయ్",
                    "cbi",
                    "ed",
                    "rbi",
                ),
                (
                    "అధికారి",
                    "ఏజెంట్",
                    "టీమ్",
                    "వారెంట్",
                    "అరెస్ట్",
                    "దాడి",
                    "ఫ్రీజ్",
                    "సీజ్",
                    "కస్టడీ",
                    "విచారణ",
                    "సమన్లు",
                    "నిలిపివేత",
                    "డిస్‌కనెక్ట్",
                ),
            ),
            (
                ("ఆధార్", "పాన్", "నంబర్", "సిమ్", "ఖాతా"),
                ("మనీ లాండ్రింగ్", "మోసం కేసు", "మోసపు కేసు", "హవాలా", "చట్టవిరుద్ధ", "బెట్టింగ్"),
            ),
        ),
        "hinglish": (
            (
                ("cbi", "police", "rbi", "court", "customs", "trai"),
                (
                    "officer",
                    "warrant",
                    "arrest",
                    "case",
                    "freeze",
                    "seized",
                    "custody",
                    "team",
                    "suspend",
                    "deactivate",
                ),
            ),
            (
                ("aadhaar", "pan", "sim", "number", "account"),
                ("fraud case", "illegal", "betting", "scam case", "money laundering"),
            ),
        ),
    },
    "money_action": {
        "en": (
            (
                ("send", "transfer", "deposit"),
                (
                    "this upi",
                    "to this upi",
                    "this account",
                    "to this account",
                    "this number",
                    "to this number",
                    "upi id",
                    "the agent",
                    "our agent",
                    "the courier",
                    "courier boy",
                    "the lawyer",
                    "escrow",
                    "this handle",
                ),
            ),
        ),
        "hi": (
            (
                ("भेजें", "भेजो", "ट्रांसफर", "जमा करें", "deposit", "send"),
                ("इस यूपीआई", "इस खाते", "इस खाता", "इस नंबर", "एजेंट", "अधिवक्ता", "escrow"),
            ),
        ),
        "te": (
            (
                ("పంపండి", "ట్రాన్స్‌ఫర్", "జమ చేయండి", "send", "transfer"),
                (
                    "ఈ యూపీఐ",
                    "ఈ యూపీఐ ఐడీకి",
                    "యూపీఐకి",
                    "యూపీఐకు",
                    "ఈ ఖాతా",
                    "ఖాతాలో",
                    "ఈ నంబర్",
                    "నంబర్‌కు",
                    "ఏజెంట్",
                    "న్యాయవాది",
                    "escrow",
                ),
            ),
        ),
        "hinglish": (
            (
                ("bhejo", "transfer", "jama karo", "deposit", "send"),
                (
                    "this upi",
                    "is upi",
                    "is account",
                    "is number",
                    "this account",
                    "this number",
                    "agent",
                    "lawyer",
                    "escrow",
                ),
            ),
        ),
    },
    "prize": {
        "en": ((("congratulations", "congrats"), ("won", "winner", "lottery", "lucky draw", "prize", "jackpot")),),
        "hi": ((("बधाई हो", "मुबारक", "बधाई"), ("जीता", "जीते", "लॉटरी", "लकी ड्रॉ", "इनाम", "जैकपॉट")),),
        "te": ((("అభినందనలు",), ("గెలిచారు", "లాటరీ", "లక్కీ డ్రా", "బహుమతి", "జాక్‌పాట్")),),
        "hinglish": (
            (("badhai ho", "mubarak", "congrats"), ("jeeta", "jeete", "lottery", "lucky draw", "prize", "jackpot")),
        ),
    },
    "urgency": {},
    "link_grab": {},
}
