"""English token set (+ language-agnostic link tokens).

Each row: (family, reason_code, lang, [regex, ...]).

`lang` is one of:
  - "en"  : English-only phrasing
  - "any" : language-agnostic (URLs, shorteners, apk) — always applied

Regexes run against normalize.normalize() output (casefolded, NFKC,
zero-width stripped, acronym de-obfuscation applied), so they are
written lowercase.

Design rules baked in (see EVALS.md):
- credential patterns are REQUEST-direction: verb ("share/send/tell")
  plus the token, never the bare word — a bank delivering an OTP must
  not fire;
- negation guards ("do not share", "never share") are applied by the
  scorer around every match window.
"""

PATTERNS = [
    # --- credential -------------------------------------------------
    ("credential", "MSG-CRED-OTP-SHARE", "en", [
        r"\b(share|send|sending|give|provide|confirm|tell|read|repeat|verify)\b.{0,24}\botp\b",
        r"\botp\b.{0,20}\b(share|send|give|provide|tell|batao|bhejo)\b",
        r"\botp\s+for\s+(the\s+)?(verification|validation|confirmation)\b.{0,20}\b(share|send|tell|provide|confirm)\b",
    ]),
    ("credential", "MSG-CRED-CVV-SHARE", "en", [
        r"\b(share|send|sending|give|provide|confirm|tell|read)\b.{0,24}\bcvv\b",
        r"\bcvv\b.{0,14}\b(share|send|give|tell|batao)\b",
    ]),
    ("credential", "MSG-CRED-UPI-PIN-RECEIVE", "en", [
        r"\b(enter|dial|put|type)\s+(in\s+)?(your\s+)?upi\s+pin\b",
        r"\bupi\s+pin\b.{0,25}\b(receive|receiving|get|accept|credited)\b",
    ]),
    ("credential", "MSG-CRED-UPI-COLLECT-REQUEST", "en", [
        r"\bcollect\s+request\b",
        r"\b(approve|accept)\s+(the\s+)?(collect\s+)?request\b",
    ]),
    ("credential", "MSG-CRED-BANK-DETAILS", "en", [
        r"\b(send|share|give|provide|confirm|verify|bhejo|bhej)\b.{0,20}\b(bank|account)\s+(details|number|statement)\b",
    ]),
    # --- authority --------------------------------------------------
    ("authority", "MSG-AUTH-DIGITAL-ARREST", "en", [
        r"\bdigital\s+arrest\b",
        r"\barrest(ed)?\s+you\s+digitally\b",
    ]),
    ("authority", "MSG-AUTH-ARREST-WARRANT", "en", [
        r"\barrest\s+warrant\b",
        r"\bwarrant\b.{0,25}\b(your\s+name|against\s+you)\b",
    ]),
    ("authority", "MSG-AUTH-CASE-AGAINST-YOU", "en", [
        r"\b(case|fir|complaint)\s+(has\s+been\s+)?(registered|filed|lodged)\b.{0,40}\bagainst\s+(you|your)\b",
        r"\ba\s+case\s+against\s+you\b",
    ]),
    ("authority", "MSG-AUTH-AGENCY-THREAT", "en", [
        r"\b(cbi|narcotics|customs|enforcement\s+directorate|ed\s+officer|trai|rbi|police|income\s+tax|crime\s+branch)\b.{0,60}\b(arrest\w*|warrant|raid|summon\w*|seiz\w+|suspend\w*|block\w*|freeze\w*|custody|held|detain\w*|deactivat\w+)\b",
        r"\b(arrest|raid)\b.{0,40}\b(cbi|narcotics|customs|police)\s*(team|officer|wing|cell)?\b",
    ]),
    ("authority", "MSG-AUTH-PARCEL-SEIZED", "en", [
        r"\b(parcel|courier|shipment|package)\b.{0,50}\b(seized|seizure|illegal|drugs|contraband|customs|narcotics)\b",
    ]),
    ("authority", "MSG-AUTH-TELECOM-BLOCK", "en", [
        r"\b(trai|telecom\s+ministry|department\s+of\s+telecom)\b.{0,50}\b(block\w*|disconnect\w*|suspend\w*|bar\b)\b",
        r"\byour\s+[\w\s]{0,10}?(number|sim|connection|mobile)\b.{0,30}\b(block\w*|disconnect\w*|suspend\w*|bar\b|deactivat\w+)\b",
    ]),
    ("authority", "MSG-AUTH-RBI-ACTION", "en", [
        r"\b(suspend\w*|block\w*|freeze\w*|deactivat\w+)\b.{0,40}\brbi\b|\brbi\b.{0,40}\b(suspend\w*|block\w*|freeze\w*|deactivat\w+)\b",
        r"\b(suspend\w*|block\w*|freeze\w*|deactivat\w+)\b.{0,40}\breserve\s+bank\b|\breserve\s+bank\b.{0,40}\b(suspend\w*|block\w*|freeze\w*|deactivat\w+)\b",
    ]),
    ("authority", "MSG-AUTH-POWER-DISCONNECT", "en", [
        r"\b(electricity|power)\b.{0,60}\b(disconnect\w*|cut\s*off|cut)\b.{0,25}\b(today|tonight|now|immediately|evening|right\s+now)\b",
        r"\bpower\s+supply\s+(will\s+be\s+)?(cut|disconnected)\b",
        r"\bpower\s+(connection|will\s+be\s+cut)\b.{0,25}\b(today|tonight|now)\b",
    ]),
    # --- money_action -----------------------------------------------
    ("money_action", "MSG-MONEY-FEE-DEMAND", "en", [
        r"\b(processing|registration|verification|activation|re-?activation|transfer|documentation|kyc\s+update|claim|membership|revival|annual|connection|installation|inspection|investigation|re-?booking|scanning|clearance)\s+(fee|charge|charges)\b",
        r"\b(customs\s+duty|customs\s+charge|clearance\s+charge|gst\s+charge|gst\s+amount)s?\b",
        r"\b(customs\s+duty|gst\s+(charge|amount)|clearance\s+charge)s?\b.{0,20}₹?\s*\d",
        r"\b(fee|charge|charges|duty)\s+of\s+(₹|rs\.?|inr)?\s*[\d][\d,]*",
        r"\bfee\s+of\s+₹?\s*\d",
    ]),
    ("money_action", "MSG-MONEY-FINE-PENALTY", "en", [
        r"\b(fine|penalty)\s+(of\s+)?(₹|rs\.?|inr)?\s*[\d][\d,]*",
    ]),
    ("money_action", "MSG-MONEY-BAIL", "en", [
        r"\bbail\b",
    ]),
    ("money_action", "MSG-MONEY-TRANSFER-DEMAND", "en", [
        r"\b(send|transfer|pay|deposit)\s+₹\s*[\d][\d,]*",
        r"\b(needs?|requires?)\s+(₹|rs\.?)\s*[\d][\d,]*",
        r"\b(send|transfer|pay|deposit)\s+(₹|rs\.?|inr)?\s*[\d][\d,]*\s*(.{0,16}?\s)?(to|into)\s+(the\s+)?[\w\s]{0,20}?(agent|officer|manager|official|clerk|upi|account|number|lawyer|advocate|lineman|collector|coordinator|admin|wallet)\b",
        r"\b(send|transfer)\s+(the\s+)?(money|amount|payment|fee|bail)\b.{0,20}\b(now|today|immediately|urgently)\b",
    ]),
    # --- prize ------------------------------------------------------
    ("prize", "MSG-PRIZE-LOTTERY", "en", [
        r"\b(lottery|lucky\s*draw|jackpot|kbc|prize\s+(money|of|draw))\b",
    ]),
    ("prize", "MSG-PRIZE-WON-AMOUNT", "en", [
        r"\b(won|win)\s+₹?\s*[\d][\d,]*",
        r"₹?\s*[\d][\d,]*\s*(lakh|crore)s?\b.{0,25}\b(won|win|prize|lottery)\b",
        r"\bprize\s+of\s+₹?\s*[\d][\d,]*",
    ]),
    # --- urgency ----------------------------------------------------
    ("urgency", "MSG-URG-DEADLINE-HOURS", "en", [
        r"\bwithin\s+\d+\s*(hours?|hrs|minutes?|mins)\b",
        r"\b\d+\s*(hours?|hrs)\b.{0,25}\b(or|before|else|failing)\b",
        r"\bby\s+(today|tonight|tomorrow|today\s+evening)\b",
        r"\b\d{1,2}(:\d{2})?\s*(am|pm)\s+today\b",
        r"\b(today\s+evening|tonight)\b",
    ]),
    ("urgency", "MSG-URG-LAST-WARNING", "en", [
        r"\b(last|final)\s+warning\b",
    ]),
    ("urgency", "MSG-URG-IMMEDIATELY", "en", [
        r"\bimmediately\b",
        r"\bright\s+now\b",
        r"\burgent(?:ly)?\b.{0,25}\b(send|pay|call|reply|respond|act|contact|transfer|deposit)\b",
        r"\b(send|pay|call|reply|respond|act|contact|transfer|deposit)\b.{0,25}\burgent(?:ly)?\b",
    ]),
    ("urgency", "MSG-URG-ELSE-CLAUSE", "en", [
        r"\belse\b",
        r"\botherwise\b",
        r"\bfailing\s+which\b",
        r"\bor\s+your\s+(account|number|card|connection|sim)\b",
    ]),
    # --- link_grab --------------------------------------------------
    ("link_grab", "MSG-LINK-SHORTENER", "any", [
        r"\b(bit\.ly|tinyurl\.com|cutt\.ly|rb\.gy|t\.co|goo\.gl|is\.gd|tiny\.cc|shorturl\.at|bit\.do|rebrand\.ly|bitly\.com)\b",
    ]),
    ("link_grab", "MSG-LINK-CLICK-HERE", "en", [
        r"\b(click|tap)\s+(here|on\s+the\s+link|below|this\s+link)\b",
    ]),
    ("link_grab", "MSG-LINK-VERIFY-NOW", "en", [
        r"\b(verify|update|confirm|activate|reactivate|resume|complete)\s+(your\s+)?[\w\s]{0,14}(kyc|pan\s*card|aadhaar|account|card|details|profile|number|wallet)\s*(now|immediately|here|today| urgently)?\b",
        r"\bverify\s+now\b",
    ]),
    ("link_grab", "MSG-LINK-LOOKALIKE-DOMAIN", "any", [
        r"\b[\w-]{2,30}-(kyc|update|verify|refund|job|result|yono|secure|login|alert|block|disconnect|recharge|offer|loan|fastag|electricity|bill|liveness|kbc|lottery|claim|winner)[\w-]*\.(com|co\.in|in|net|org|xyz|online|site|info|icu|top|club)\b",
        r"\b(sbi|hdfc|icici|axis|kotak|paytm|phonepe|gpay|googlepay|amazon|flipkart)-[\w-]{2,30}\.(com|co\.in|in|net|xyz|online|site|info|icu|top)\b",
        r"\b\w+\.(xyz|icu|top|club|online|site)\b(/\S*)?",
    ]),
    ("link_grab", "MSG-LINK-APK", "any", [
        r"\.apk\b",
        r"\bdownload\s+the\s+(app|apk)\s+(from\s+the\s+)?(link|below|attached)\b",
    ]),
]
