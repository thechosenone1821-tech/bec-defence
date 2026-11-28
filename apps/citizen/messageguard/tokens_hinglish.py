"""Explicit Hinglish-Latin token set (Phase 5 port).

Each row is ``(family, MSG-* code, lang, [regex, ...])``. Rows are tagged
``"hinglish"`` and therefore only run when ``analyze(..., lang="hinglish")``
or ``score_message(..., lang="hinglish")`` asks for them; ``lang="auto"``
keeps the original en/hi/te + ``any`` universe unchanged. This preserves the
published en/hi/te numbers while measuring the ported hand-authored Hinglish
corpus through one scorer and one reason catalogue.

Regexes run against ``normalize.normalize()`` output. They are deliberately
request-direction: a bank notice saying "OTP share mat karo" must not become
a credential request. All numbers produced from these rows are in-distribution
and hand-authored; real-world recall/FPR remain UNMEASURED.
"""

PATTERNS = [
    # --- credential -------------------------------------------------
    ("credential", "MSG-CRED-OTP-SHARE", "hinglish", [
        r"\botp\b[^\n]{0,30}\b(?:batao|bhejo|bhej\s+do|confirm\s+karo|submit\s+karo|share\s+karo|daalo|do)\b",
        r"\b(?:batao|bhejo|confirm\s+karo|submit\s+karo)\b[^\n]{0,20}\botp\b",
        r"\botp\s+(?:batao|bhejo|bhej\s+do|confirm\s+karo)\b",
        r"\botp\b[^\n]{0,20}\bb\s*h\s*e\s*j\s*o\b",
    ]),
    ("credential", "MSG-CRED-CVV-SHARE", "hinglish", [
        r"\bcvv\b[^\n]{0,35}\b(?:confirm\s+karo|batao|bhejo|ready\s+rakho|share\s+karo)\b",
        r"\b(?:confirm\s+karo|batao|bhejo)\b[^\n]{0,20}\bcvv\b",
    ]),
    ("credential", "MSG-CRED-UPI-PIN-ENTRY", "hinglish", [
        r"\bupi\s+pin\b[^\n]{0,35}\b(?:batao|bhejo|daalo|confirm\s+karo|ready\s+rakho|enter\s+karo)\b",
        r"\b(?:batao|daalo|confirm\s+karo)\b[^\n]{0,20}\bupi\s+pin\b",
    ]),
    ("credential", "MSG-CRED-UPI-COLLECT-REQUEST", "hinglish", [
        r"\bcollect\s+request\b[^\n]{0,45}\b(?:approve|accept|swikar)\b(?:\s+karo)?",
        r"\b(?:approve|accept)\b[^\n]{0,45}\bcollect\s+request\b",
    ]),
    # --- authority --------------------------------------------------
    ("authority", "MSG-AUTH-DIGITAL-ARREST", "hinglish", [
        r"\bdigital\s+arrest\b",
    ]),
    ("authority", "MSG-AUTH-AGENCY-THREAT", "hinglish", [
        r"\b(?:cbi|ed\s+officer|police|crime\s+branch|cyber\s+cell|customs|narcotics|rbi|bijli\s+vibhag|power\s+corp)\b",
    ]),
    ("authority", "MSG-AUTH-PARCEL-SEIZED", "hinglish", [
        r"\b(?:parcel|fedex|courier)\b[^\n]{0,60}\b(?:seized|customs|drugs|contraband|clearance)\b",
    ]),
    ("authority", "MSG-AUTH-RBI-ACTION", "hinglish", [
        r"\brbi\b[^\n]{0,50}\b(?:freeze|block|suspend|kyc|upi\s+pin)\b",
    ]),
    ("authority", "MSG-AUTH-POWER-DISCONNECT", "hinglish", [
        r"\b(?:bijli\s+vibhag|power\s+corp|power\s+cut|meter\s+hata|connection\s+band)\b",
    ]),
    ("authority", "MSG-AUTH-CASE-AGAINST-YOU", "hinglish", [
        r"\b(?:fir|case|complaint)\b[^\n]{0,40}\b(?:darj|file|registered|linked|band)\b",
        r"\bwarrant\b|\barrest\s+karegi\b",
    ]),
    # --- money_action -----------------------------------------------
    ("money_action", "MSG-MONEY-FEE-DEMAND", "hinglish", [
        r"\b(?:processing|registration|verification|activation|clearance|gst|token|claim|bail|escrow|settlement)\s+(?:fee|charge|charges|amount|paise|paisa)\b",
        r"(?:rs\.?|₹)\s*\d[\d,]*[^\n]{0,100}\b(?:transfer\s+karo|jama\s+karo|bhejo|bhej\s+do|deposit\s+karo|bharo|pay\s+karo|payment\s+karo|dena|de\s+do)\b",
        r"\b(?:transfer\s+karo|jama\s+karo|bhejo|bhej\s+do|deposit\s+karo|bharo|pay\s+karo|payment\s+karo|dena|de\s+do)\b[^\n]{0,40}(?:rs\.?|₹)\s*\d[\d,]*",
        r"\b(?:payment|pay)\s+karo\b",
    ]),
    ("money_action", "MSG-MONEY-BAIL", "hinglish", [
        r"\bbail\s+ke\s+paise\b|\bbail\s+amount\b",
    ]),
    # --- prize ------------------------------------------------------
    ("prize", "MSG-PRIZE-LOTTERY", "hinglish", [
        r"\b(?:lucky\s+draw|lottery|kbc|jackpot|prize\s+claim|jeet\s+gaye|jeeta\s+hai|jeete\s+hain|chuna\s+gaya)\b",
    ]),
    ("prize", "MSG-PRIZE-WON-AMOUNT", "hinglish", [
        r"(?:rs\.?|₹)\s*\d[\d,]*[^\n]{0,40}\b(?:jeeta|jeete|won|prize|lucky\s+draw)\b",
    ]),
    # --- urgency ----------------------------------------------------
    ("urgency", "MSG-URG-ELSE-CLAUSE", "hinglish", [
        r"\bwarna\b|\bvarana\b|\bnahi\s+to\b",
    ]),
    ("urgency", "MSG-URG-DEADLINE-HOURS", "hinglish", [
        r"\b(?:24|2)\s+ghante\b",
        r"\baaj\s+raat\b",
        r"\bsirf\s+24\s+ghante\b",
    ]),
    ("urgency", "MSG-URG-LAST-WARNING", "hinglish", [
        r"\baakhri\s+chetavni\b|\bfinal\s+notice\b|\bfinal\s+warning\b",
    ]),
    ("urgency", "MSG-URG-IMMEDIATELY", "hinglish", [
        r"\b(?:abhi|turant|jaldi|aaj\s+hi|bolo\s+jaldi)\b",
    ]),
    # --- link_grab --------------------------------------------------
    ("link_grab", "MSG-LINK-VERIFY-NOW", "hinglish", [
        r"\b(?:verify|update|complete|reactivate|submit)\s+(?:karo|karein)\b[^\n]{0,60}(?:bit\.ly|tinyurl\.com|\.xyz|\.online|\blink\b)",
        r"(?:bit\.ly|tinyurl\.com|\.xyz|\.online)[^\n]{0,60}\b(?:verify|update|complete|submit)\b",
    ]),
]
