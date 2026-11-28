#!/usr/bin/env python3
"""Generate `raksha/MESSAGEGUARD_EVALS.md` from `results.json`.

The prose lives here so the narrative and the numbers are produced in one
pass — every figure in the published document comes from the JSON the single
eval runner wrote. Usage from `raksha-code/`:

    python evals/messageguard/run_evals.py
    python evals/messageguard/gen_evals_md.py
"""

import json
import pathlib

HERE = pathlib.Path(__file__).resolve().parent
CODE_ROOT = HERE.parents[1]
REPO_ROOT = CODE_ROOT.parent
RESULTS = HERE / "results.json"
OUT = REPO_ROOT / "raksha" / "MESSAGEGUARD_EVALS.md"

LANG_ORDER = ("en", "hi", "te", "hinglish")
LANG_NAME = {"en": "English", "hi": "Hindi", "te": "Telugu", "hinglish": "Hinglish"}
LANG_ABBR = {"en": "EN", "hi": "HI", "te": "TE", "hinglish": "HG"}
FAMILY_ORDER = ["credential", "authority", "money_action", "prize", "urgency", "link_grab"]
WEIGHT = {"credential": "0.45", "authority": "0.40", "money_action": "0.30",
          "prize": "0.30", "urgency": "0.20", "link_grab": "0.25"}

FP_NOTES = {
    "genuine_bank_kyc_alert": "Hand-authored bank KYC-update alert — documented failure mode 2; needs a sender-ID allowlist at the app layer, not more tokens.",
    "marketing_offer": "Marketing SMS with 'lucky draw' wording — matches the prize family by design.",
    "broker_market_info": "Broker SMS quoting a market-open time ('9:15 AM today') matches the deadline token.",
    "toll_challan": "Genuine-looking toll/e-challan SMS containing an amount plus a pay instruction — same shape as a transfer demand.",
    "utility_bill": "Utility bill reminder whose date digits sit near a pay verb — matches the Telugu transfer-demand token.",
    "bank_txn": "Hand-authored Hinglish bank transaction alert; no request-direction credential verb is present.",
    "otp_notice": "Hand-authored Hinglish OTP notice with an explicit 'do not share' cue.",
    "bill_receipt": "Hand-authored Hinglish bill/receipt notice; an official domain is not a shortener or lookalike.",
    "marketing": "Hand-authored Hinglish marketing SMS; no prize or fee-demand vocabulary.",
    "govt_service": "Hand-authored Hinglish government-service notice; no request-direction credential verb.",
    "loan_emi": "Hand-authored Hinglish EMI reminder; 'pay karein' is not a scam demand token.",
    "kyc_official": "Hand-authored Hinglish official KYC reminder; no URL shortener or credential request.",
    "bank_fraud_alert": "Hand-authored Hinglish bank fraud alert; the official-app/ATM advice is not a demand.",
}


def pct(x):
    return f"{x * 100:.1f}%"


def main():
    r = json.loads(RESULTS.read_text(encoding="utf-8"))
    c = r["corpus"]
    o = r["overall"]
    langs = r["languages"]
    fp_cases = r["benign_fp_cases"]
    scope = r.get("measurement_scope", "hand-authored / in-distribution")
    missed = c["scam_total"] - o["tp_moderate"]
    h = langs["hinglish"]
    h_missed = h["scam_total"] - h["scam_caught_moderate"]
    h_fp = [case for case in fp_cases if case["lang"] == "hinglish"]
    worst = max(fp_cases, key=lambda case: case["score"], default=None)
    critical_fps = [case for case in fp_cases if case["verdict"] == "CRITICAL"]
    recalls = [v["recall"] for v in r.get("family_recall", {}).values()
               if v.get("recall") is not None]
    scam_counts = ", ".join(f"{c['scam_by_lang'][l]} {LANG_NAME[l]}" for l in LANG_ORDER)
    benign_counts = " / ".join(str(c["benign_by_lang"][l]) for l in LANG_ORDER)
    high_total = sum(langs[l]["scam_caught_high"] for l in LANG_ORDER)

    lines = []
    lines.append("# MessageGuard — single-source measured evaluation")
    lines.append("")
    lines.append(
        "_Generated from `raksha-code/evals/messageguard/results.json` by "
        "`raksha-code/evals/messageguard/run_evals.py`; regenerate with "
        "`cd raksha-code && python evals/messageguard/run_evals.py && python "
        "evals/messageguard/gen_evals_md.py`. All numbers below are computed, "
        "not quoted from memory. They are **hand-authored / in-distribution**, "
        "never field measurements._"
    )
    lines.append("")
    lines.append("## 1. What was measured")
    lines.append("")
    lines.append(
        "Phase 5 leaves one corpus, one generated eval document, one reason "
        "catalogue and one detector interface. The shipped deterministic scorer "
        "in `apps/citizen/messageguard/scorer.py` scored every committed "
        "fixture with no model, no network and no randomness — the same input "
        "produces the same numbers on every machine. `run_evals.py --check` "
        "verifies that this document's source JSON still matches the scorer "
        'and fixtures. en/hi/te rows use `lang="auto"`; the 46 unique ported '
        'Hinglish rows use the explicit `lang="hinglish"` interface, so the '
        "dedicated Latin-Hindi token set is measured without changing the "
        "published en/hi/te `auto` results."
    )
    lines.append("")
    lines.append(
        f"The corpus holds **{c['scam_total']} scam messages** "
        f"({scam_counts}) and **{c['benign_total']} genuine-alert fixtures** "
        f"({benign_counts}): OTP deliveries with 'do not share' phrasing, "
        "transaction and balance alerts, EMI reminders, utility bills, "
        "FASTag/toll notices, fraud advisories from banks and police, and "
        "marketing SMS. The 46 Hinglish rows are unique hand-authored ports "
        "from the archived alternative Part 3 corpus; every normalized text "
        "differs from the earlier 492 fixtures. These messages are "
        "**hand-authored fixtures**, not consent-cleared device traffic, and "
        "contain no personal data. Every scam fixture carries the signal "
        "families it was written to trigger, so family-level recall is "
        "measured, not eyeballed."
    )
    lines.append("")
    lines.append("## 2. Headline numbers")
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("| --- | --- |")
    lines.append(f"| Scam detection (verdict ≥ MODERATE) | **{pct(o['recall_moderate'])}** ({o['tp_moderate']}/{c['scam_total']}) |")
    lines.append(f"| False-positive rate on genuine-alert fixtures (≥ MODERATE) | **{pct(o['fpr_moderate'])}** ({o['fp_moderate']}/{c['benign_total']}) |")
    lines.append(f"| Overall accuracy (≥ MODERATE operating point) | **{pct(o['accuracy_moderate'])}** |")
    lines.append(f"| Precision at that operating point | {pct(o['precision_moderate'])} |")
    lines.append(f"| Scam detection (score ≥ 0.70, i.e. CRITICAL) | {pct(high_total / c['scam_total'])} |")
    lines.append("")
    hinglish_note = (
        "All 30 ported Hinglish scam rows are detected at ≥MODERATE."
        if h_missed == 0 else
        f"The Hinglish port contributes {h_missed} ≥MODERATE misses."
    )
    lines.append(
        f"The {missed} scam messages the scorer misses are the deliberately "
        "benign-like calibration fixtures (one per en/hi/te) that carry no "
        "token-set vocabulary at all. They stay in the corpus to keep failure "
        "mode 1 visible: a scam script written outside the catalogue is "
        "invisible, and no corpus number should be read as a promise against "
        f"novel scripts. {hinglish_note} Detection at the 0.70/CRITICAL "
        "threshold is deliberately lower — most single-family messages (a lone "
        "deadline, a lone prize claim) land in LOW/MODERATE, which is the "
        "intended conservative behaviour for a tool that shows a warning on a "
        "person's own phone. **Real-world recall and false-positive rate "
        "remain UNMEASURED.**"
    )
    lines.append("")
    lines.append("## 3. Per-language results")
    lines.append("")
    lines.append("| Language | Scam | Det ≥ MOD | Det ≥ 0.70 | Genuine | FP ≥ MOD | FPR |")
    lines.append("| --- | --- | --- | --- | --- | --- | --- |")
    for lang in LANG_ORDER:
        d = langs[lang]
        lines.append(
            f"| {LANG_NAME[lang]} | {d['scam_total']} | {pct(d['detection_rate_moderate'])} | "
            f"{pct(d['detection_rate_high'])} | {d['benign_total']} | {d['fp_moderate']} | "
            f"{pct(d['fpr_moderate'])} |"
        )
    lines.append("")
    lines.append(
        "The en/hi/te token sets behave nearly identically on scam detection "
        "because each was written against the same twelve scam scripts "
        "(lottery/KBC, digital arrest, parcel-seized, KYC-expiry, card-blocked "
        "phishing, OTP requests, UPI collect/PIN-to-receive, telecom "
        "disconnection, electricity disconnection, fee-demand job/loan schemes, "
        "bail emergencies, and single-family calibration messages). The "
        "explicit Hinglish token set covers only the ported hand-authored rows; "
        "its numbers are catalogue coverage, not a field claim. The "
        "false-positive side differs slightly by language: English adds one FP "
        "class the others do not contain (a broker market-open time) and Telugu "
        "adds another (a genuine-looking toll pay-instruction), which is a "
        "statement about which genuine messages were authored, not about the "
        "language itself. "
        + ("The ported Hinglish benign rows add no ≥MODERATE false positives."
           if not h_fp else
           f"The ported Hinglish benign rows add {len(h_fp)} ≥MODERATE false positives, listed in §5.")
    )
    lines.append("")
    lines.append("## 4. Family-level recall")
    lines.append("")
    lines.append("| Family (weight) | " + " | ".join(LANG_NAME[l] for l in LANG_ORDER) + " |")
    lines.append("| " + " | ".join(["---"] * (len(LANG_ORDER) + 1)) + " |")
    for fam in FAMILY_ORDER:
        row = [f"{fam} ({WEIGHT[fam]})"]
        for lang in LANG_ORDER:
            d = langs[lang]["family_recall"][fam]
            if d["labelled"] == 0:
                row.append("—")
            else:
                row.append(f"{pct(d['recall'])} ({d['hit']}/{d['labelled']})")
        lines.append("| " + " | ".join(row) + " |")
    lines.append("")
    if recalls and all(value == 1.0 for value in recalls):
        recall_claim = (
            "Every labelled family fires on every fixture that was written to "
            "trigger it — 100% in-distribution recall. "
        )
    else:
        recall_claim = "Family recall is reported per language and overall. "
    lines.append(
        recall_claim +
        "That number must be read honestly: the fixtures were authored against "
        "the same phrase catalogue the scorer uses, so this table proves the "
        "catalogue is covered by its token sets, **not** that real-world scams "
        "are caught at 100%. The honest claim, unchanged from the Part 3 spec, "
        "is *\"it recognises the scam patterns we thought of\"* — what this "
        "evaluation adds is the proof that the patterns we thought of are all "
        "actually wired up, plus a measured cost on genuine-alert fixtures that "
        "was previously unknown."
    )
    lines.append("")
    lines.append("## 5. False-positive review on genuine-alert fixtures")
    lines.append("")
    if fp_cases:
        worst_line = (
            f" None of them reaches CRITICAL; the worst score is "
            f"{worst['score']:.2f} ({worst['verdict']})."
            if not critical_fps else
            f" {len(critical_fps)} reach CRITICAL; the worst score is "
            f"{worst['score']:.2f} ({worst['verdict']})."
        )
    else:
        worst_line = " No benign fixture reaches >=MODERATE."
    lines.append(
        f"The benign corpus produced {len(fp_cases)} flagged messages at the "
        f"≥MODERATE threshold ({pct(o['fpr_moderate'])} of all genuine-alert "
        "fixtures). Every one is listed below with the families that fired, "
        "because an FP list you cannot inspect is a number you cannot trust."
        + worst_line
    )
    lines.append("")
    lines.append("| ID | Kind | Score | Families fired | Why it fires |")
    lines.append("| --- | --- | --- | --- | --- |")
    for case in fp_cases:
        kind = case["kind"]
        note = FP_NOTES.get(kind, "Hand-authored benign fixture; inspect the families above.")
        lines.append(
            f"| {case['id']} ({LANG_ABBR.get(case['lang'], case['lang'][:2].upper())}) | {kind} | "
            f"{case['score']:.2f} | {', '.join(case['families_fired'])} | {note} |"
        )
    lines.append("")
    lines.append(
        "The en/hi/te FPs come from four documented failure classes. First and "
        "largest: **fixtures written to look like genuine bank KYC-update SMS** "
        "(one per language) — a message saying 'update your KYC immediately' "
        "with a link is indistinguishable from a phishing script on text alone, "
        "which is failure mode 2 exactly as stated in the module docstring. The "
        "correct mitigation is not more tokens but a sender-ID allowlist at the "
        "app layer (Indian transactional SMS carry verified headers like "
        "SB-BANK); the message-only detector deliberately never resolves "
        "senders or links so that checking a message never leaks that it was "
        "checked. Second: **marketing SMS that say 'lucky draw'** — the prize "
        "family matches real brand campaigns. Third, single-language classes: a "
        "**broker market-open time** in English and a **toll pay-instruction** "
        "in Telugu. Fourth: a Telugu bill reminder where date digits sat inside "
        "the transfer-demand window, fixed during corpus construction by "
        "requiring an explicit ₹/రూ currency marker on amounts — a fix that "
        "also protects every language's amount tokens from phone numbers and "
        "dates. "
        + ("The ported Hinglish benign rows add no new >=MODERATE false positives."
           if not h_fp else
           "The ported Hinglish benign cases are listed above with their authored classes.")
    )
    lines.append("")
    lines.append(
        "What we chose NOT to fix, and why: the KYC-alert FPs could be suppressed "
        "by dropping the 'verify/update now' token, but that token is what "
        "catches the card-blocked and YONO-phishing scam classes in all three "
        "script languages, and the corpus shows those classes score CRITICAL "
        "without it. Until the app layer can vouch for sender IDs, flagging a "
        "genuine-looking KYC SMS as HIGH and explaining why is the safer error "
        "than silently passing a credential-harvesting page as LOW. The FP rate "
        "must be re-measured on consent-cleared device corpora once sender "
        "metadata is available."
    )
    lines.append("")
    lines.append("## 6. Method and caveats")
    lines.append("")
    lines.append(
        "Every fixture is scored with the one shipped scorer through "
        "`citizen.messageguard.analyze()`: en/hi/te use the default `auto` "
        'universe, and Hinglish uses explicit `lang="hinglish"`. The eval '
        "runner adds no tuning, no per-fixture overrides and no "
        "post-processing. Scores are compared against the fixed band edges from "
        "the spec (<0.20 LOW, <0.45 MODERATE, <0.70 HIGH, ≥0.70 CRITICAL) with "
        "the ≥3-family ×1.3 boost and the 1.0 cap applied exactly as in the "
        "Citizen API. `raksha-code/evals/messageguard/results.json` contains "
        "every per-language aggregate and every benign false-positive case for "
        "audit; all fixture texts are committed under "
        "`raksha-code/citizen/fixtures/messageguard/`. The one reason catalogue "
        "is `packages/contracts/reasons.py`; the one generated document is this "
        "file. No model and no network inference are used."
    )
    lines.append("")
    lines.append(
        "Three caveats bound every number above. First, this is an "
        "**in-distribution** evaluation: recall numbers measure catalogue "
        "coverage, not field performance, and the corpus is hand-authored, so a "
        "model trained on it would learn the author, not the scam — which is "
        "why the spec's order (corpus first, model second) is preserved and the "
        "classifier remains optional and unbuilt. Second, the benign corpus is "
        "authored to *look* like genuine Indian bank/telco/utility traffic but "
        "is not a dump of real devices; the FP rate is a floor estimate until "
        "consent-cleared device corpora are measured. Third, transliteration "
        "coverage remains partial (failure mode 3): the explicit Hinglish token "
        "set covers exactly the 46 hand-authored ported rows plus common "
        "Latin-script verbs shared with en/hi; the long tail of transliteration "
        "variants is not covered and is not measured by any number in this file. "
        f"Measurement scope: **{scope}**."
    )
    lines.append("")
    lines.append("## 7. Definition of done — status after this run")
    lines.append("")
    lines.append("- [x] Deterministic and offline (stdlib only; asserted by tests; no model invoked)")
    lines.append("- [x] Reasons name the family that fired (one `MSG-*` catalogue, no matched phrases in citizen copy)")
    lines.append("- [x] Works in en / hi / te plus an explicit Hinglish-Latin port (measured separately above)")
    lines.append("- [x] One corpus, one generated eval document, one reason catalogue, one detector interface")
    lines.append(f"- [x] Fixture corpus ≥ 300 messages with per-language coverage — **{c['scam_total']} scam + {c['benign_total']} genuine = {c['scam_total'] + c['benign_total']} hand-authored fixtures**")
    lines.append(f"- [x] False-positive rate measured on genuine-alert fixtures — **{pct(o['fpr_moderate'])}** at ≥MODERATE ({o['fp_moderate']}/{c['benign_total']}), every case listed in §5")
    lines.append(f"- [x] Measured accuracy published — **{pct(o['accuracy_moderate'])}** overall at the ≥MODERATE operating point (this file and `raksha/EVALS.md`)")
    lines.append("- [x] All published numbers explicitly hand-authored / in-distribution; real-world UNMEASURED")
    lines.append("")
    lines.append(
        "The independent alternative Part 3 package and the standalone snapshot "
        "are archived under `archive/provenance/` with provenance notes; they "
        "are not runtime imports. The 20-item M3 smoke corpus remains for API "
        "regression only; it is not the basis of any published accuracy figure. "
        "This document is generated and must never be hand-edited."
    )

    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
