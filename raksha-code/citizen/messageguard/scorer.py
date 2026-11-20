"""MessageGuard — deterministic scam-script scorer (en / hi / te).

HONESTY LABEL: this is a rule+signal scorer, NOT a trained classifier. It
detects known signal families common in Indian scam scripts. It will miss
novel scripts and will false-positive on some legitimate urgent payment
messages (a bank's genuine fraud alert). Accuracy is measured ONLY against
citizen/fixtures/message_fixtures.json (synthetic, hand-authored). Do not
present it as anything stronger.

Signal families (weighted):
  credential   0.45  OTP/CVV/PIN/password requests, UPI PIN, collect-request acceptance
  authority    0.40  police/CBI/income-tax/ED/RBI/Supreme Court impersonation, "digital arrest"
  money_action 0.30  transfer/fine/bail/processing-fee/deposit/collect-request
  prize        0.30  lottery/lucky draw/prize money
  urgency      0.20  24 hours / immediately / last warning / else-clause
  link_grab    0.25  shorteners & "click/verify now" links

Verdict bands:  score < 0.20 LOW · < 0.45 MODERATE · < 0.70 HIGH · ≥ 0.70 CRITICAL
≥3 families hit anywhere ⇒ ×1.3 boost (capped 1.0).
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List

_FAMILIES: Dict[str, Dict[str, Any]] = {
    "credential": {
        "weight": 0.45,
        "tokens": [
            "share otp", "share your otp", "otp share", "send otp", "otp बताएं",
            "cvv", "upi pin", "card pin", "atm pin", "upi పిన్", "otp పంచుకోండి",
            "pin सबमिट", "pin दे दें", "cvv और otp", "cvv, otp",
            "enter your password", "password share", "पिन सबमिट", "पिन बताएं",
        ],
    },
    "authority": {
        "weight": 0.40,
        "tokens": [
            "digital arrest", "डिजिटल अरेस्ट", "డిజిటల్ అరెస్ట్",
            "cbi", "सीबीआई", "चेकपोस्ट",
            "cyber crime branch", "సైబర్ క్రైమ్ బ్రాంచ్", "साइबर क्राइम ब्रांच",
            "arrest warrant", "అరెస్ట్ వారెంట్", "गिरफ्तारी वारंट",
            "income tax department", "enforcement directorate", "ed officer",
            "supreme court", "rbi officer", "रिजर्व बैंक अधिकारी",
            "police station", "पुलिस स्टेशन", "పోలీస్ స్టేషన్",
            "fir दर्ज", "fir registered", "కేసు నమోదు",
        ],
    },
    "money_action": {
        "weight": 0.30,
        "tokens": [
            "collect request", "कलेक्शन रिक्वेस्ट", "collect request स्वीकार",
            "collect request అంగీకరించి", "स्वीकार करें", "accept the request",
            "accept this", "అంగీకరించండి",
            "transfer immediately", "तुरंत ट्रांसफर", "तुरंत जमा",
            "వెంటనే బదిలీ", "వెంటనే జరిమానా", "ट्रांसफर करें",
            "fine amount", "जुर्माना", "జరిమానా", "processing fee",
            "bail amount", "ज़मानत राशि", "బెయిల్", "pay the penalty",
        ],
    },
    "prize": {
        "weight": 0.30,
        "tokens": [
            "you won", "you have won", "lucky draw", "lucky draw", "lottery",
            "लॉटरी", "లాటరీ", "లాటరీ గెలుచుకున్నారు", "ईनाम पाने", "बधाई हो!",
            "congratulations! you", "prize money", "इनाम", "బహుమతి",
            "unclaimed", "₹25 lakh", "25 लाख", "25 లక్షల", "25 lakh",
        ],
    },
    "urgency": {
        "weight": 0.20,
        "tokens": [
            "24 hours", "24 घंटे", "24 గంటల్లో", "within 24",
            "immediately", "तुरंत", "వెంటనే", "अभी", "last warning", "final notice",
            "act now", "do it now", "आज रात", "ఈ రాత్రి", "or else", "वरना", "లేకపోతే",
            "no action", "urgent", "urgent:", "now or",
        ],
    },
    "link_grab": {
        "weight": 0.25,
        "tokens": [
            "bit.ly/", "tinyurl", "t.co/", "rb.gy/", "shorturl", "verify your account",
            "verify now", "सत्यापन करें", "ధృవీకరణ చేసి", "click the link", "click below",
            "kyc सत्यापन", "kyc ధృవీకరణ", "kyc verification", "kyc expired", "kyc update",
            "account will be blocked", "खाता बंद", "खाता 24 घंटे में बंद",
            "ఖాతా నిలిపివేయబడుతుంది", "account suspended", "account will be suspended",
        ],
    },
}

_BANDS = ((0.20, "LOW"), (0.45, "MODERATE"), (0.70, "HIGH"), (1.01, "CRITICAL"))
_ORDER = {"LOW": 0, "MODERATE": 1, "HIGH": 2, "CRITICAL": 3}


def score_message(text: str) -> Dict[str, Any]:
    raw = (text or "").strip()
    if not raw:
        return {"verdict": "LOW", "score": 0.0, "hits": {}, "families_hit": [],
                "reasons": ["empty input"], "engine": "messageguard-rules-v0 (synthetic-tuned)"}
    lowered = raw.lower()
    hits: Dict[str, List[str]] = {}
    total = 0.0
    for family, spec in _FAMILIES.items():
        matched = [tok for tok in spec["tokens"] if tok.lower() in lowered]
        if matched:
            hits[family] = matched[:4]
            total += spec["weight"] * min(1.0, 0.6 + 0.4 * len(matched))
    families_hit = list(hits)
    if len(families_hit) >= 3:
        total *= 1.3
    score = round(min(1.0, total), 3)
    verdict = next(band for limit, band in _BANDS if score < limit)
    reasons = [f"{fam}: {len(toks)} signal(s)" for fam, toks in hits.items()]
    return {"verdict": verdict, "score": score, "hits": hits,
            "families_hit": families_hit,
            "reasons": reasons or ["no known scam signals present"],
            "engine": "messageguard-rules-v0 (synthetic-tuned)"}


def verdict_at_least(verdict: str, minimum: str) -> bool:
    return _ORDER[verdict] >= _ORDER[minimum]


def evaluate_fixtures(path: str) -> Dict[str, Any]:
    data = json.load(open(path, encoding="utf-8"))
    rows, passed = [], 0
    for item in data["scam"]:
        v = score_message(item["text"])
        ok = verdict_at_least(v["verdict"], item["expect_at_least"])
        passed += ok
        rows.append({"lang": item["lang"], "expect": f">={item['expect_at_least']}",
                     "got": v["verdict"], "ok": ok})
    for item in data["clean"]:
        v = score_message(item["text"])
        ok = v["verdict"] == "LOW"
        passed += ok
        rows.append({"lang": item["lang"], "expect": "LOW",
                     "got": v["verdict"], "ok": ok})
    total = len(rows)
    return {"passed": passed, "total": total,
            "accuracy": round(passed / total, 3) if total else 0.0,
            "rows": rows}
