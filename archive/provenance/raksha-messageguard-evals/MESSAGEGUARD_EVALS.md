# MessageGuard — single-source measured evaluation

_Generated from `raksha-code/evals/messageguard/results.json` by `raksha-code/evals/messageguard/run_evals.py`; regenerate with `cd raksha-code && python evals/messageguard/run_evals.py && python evals/messageguard/gen_evals_md.py`. All numbers below are computed, not quoted from memory. They are **hand-authored / in-distribution**, never field measurements._

## 1. What was measured

Phase 5 leaves one corpus, one generated eval document, one reason catalogue and one detector interface. The shipped deterministic scorer in `apps/citizen/messageguard/scorer.py` scored every committed fixture with no model, no network and no randomness — the same input produces the same numbers on every machine. `run_evals.py --check` verifies that this document's source JSON still matches the scorer and fixtures. en/hi/te rows use `lang="auto"`; the 46 unique ported Hinglish rows use the explicit `lang="hinglish"` interface, so the dedicated Latin-Hindi token set is measured without changing the published en/hi/te `auto` results.

The corpus holds **402 scam messages** (120 English, 132 Hindi, 120 Telugu, 30 Hinglish) and **136 genuine-alert fixtures** (40 / 40 / 40 / 16): OTP deliveries with 'do not share' phrasing, transaction and balance alerts, EMI reminders, utility bills, FASTag/toll notices, fraud advisories from banks and police, and marketing SMS. The 46 Hinglish rows are unique hand-authored ports from the archived alternative Part 3 corpus; every normalized text differs from the earlier 492 fixtures. These messages are **hand-authored fixtures**, not consent-cleared device traffic, and contain no personal data. Every scam fixture carries the signal families it was written to trigger, so family-level recall is measured, not eyeballed.

## 2. Headline numbers

| Metric | Value |
| --- | --- |
| Scam detection (verdict ≥ MODERATE) | **99.2%** (399/402) |
| False-positive rate on genuine-alert fixtures (≥ MODERATE) | **10.3%** (14/136) |
| Overall accuracy (≥ MODERATE operating point) | **96.8%** |
| Precision at that operating point | 96.6% |
| Scam detection (score ≥ 0.70, i.e. CRITICAL) | 55.5% |

The 3 scam messages the scorer misses are the deliberately benign-like calibration fixtures (one per en/hi/te) that carry no token-set vocabulary at all. They stay in the corpus to keep failure mode 1 visible: a scam script written outside the catalogue is invisible, and no corpus number should be read as a promise against novel scripts. All 30 ported Hinglish scam rows are detected at ≥MODERATE. Detection at the 0.70/CRITICAL threshold is deliberately lower — most single-family messages (a lone deadline, a lone prize claim) land in LOW/MODERATE, which is the intended conservative behaviour for a tool that shows a warning on a person's own phone. **Real-world recall and false-positive rate remain UNMEASURED.**

## 3. Per-language results

| Language | Scam | Det ≥ MOD | Det ≥ 0.70 | Genuine | FP ≥ MOD | FPR |
| --- | --- | --- | --- | --- | --- | --- |
| English | 120 | 99.2% | 54.2% | 40 | 5 | 12.5% |
| Hindi | 132 | 99.2% | 56.1% | 40 | 4 | 10.0% |
| Telugu | 120 | 99.2% | 54.2% | 40 | 5 | 12.5% |
| Hinglish | 30 | 100.0% | 63.3% | 16 | 0 | 0.0% |

The en/hi/te token sets behave nearly identically on scam detection because each was written against the same twelve scam scripts (lottery/KBC, digital arrest, parcel-seized, KYC-expiry, card-blocked phishing, OTP requests, UPI collect/PIN-to-receive, telecom disconnection, electricity disconnection, fee-demand job/loan schemes, bail emergencies, and single-family calibration messages). The explicit Hinglish token set covers only the ported hand-authored rows; its numbers are catalogue coverage, not a field claim. The false-positive side differs slightly by language: English adds one FP class the others do not contain (a broker market-open time) and Telugu adds another (a genuine-looking toll pay-instruction), which is a statement about which genuine messages were authored, not about the language itself. The ported Hinglish benign rows add no ≥MODERATE false positives.

## 4. Family-level recall

| Family (weight) | English | Hindi | Telugu | Hinglish |
| --- | --- | --- | --- | --- |
| credential (0.45) | 100.0% (27/27) | 100.0% (30/30) | 100.0% (27/27) | 100.0% (12/12) |
| authority (0.40) | 100.0% (46/46) | 100.0% (53/53) | 100.0% (47/47) | 100.0% (11/11) |
| money_action (0.30) | 100.0% (67/67) | 100.0% (74/74) | 100.0% (68/68) | 100.0% (16/16) |
| prize (0.30) | 100.0% (17/17) | 100.0% (19/19) | 100.0% (17/17) | 100.0% (3/3) |
| urgency (0.20) | 100.0% (72/72) | 100.0% (91/91) | 100.0% (79/79) | 100.0% (27/27) |
| link_grab (0.25) | 100.0% (38/38) | 100.0% (40/40) | 100.0% (36/36) | 100.0% (10/10) |

Every labelled family fires on every fixture that was written to trigger it — 100% in-distribution recall. That number must be read honestly: the fixtures were authored against the same phrase catalogue the scorer uses, so this table proves the catalogue is covered by its token sets, **not** that real-world scams are caught at 100%. The honest claim, unchanged from the Part 3 spec, is *"it recognises the scam patterns we thought of"* — what this evaluation adds is the proof that the patterns we thought of are all actually wired up, plus a measured cost on genuine-alert fixtures that was previously unknown.

## 5. False-positive review on genuine-alert fixtures

The benign corpus produced 14 flagged messages at the ≥MODERATE threshold (10.3% of all genuine-alert fixtures). Every one is listed below with the families that fired, because an FP list you cannot inspect is a number you cannot trust. None of them reaches CRITICAL; the worst score is 0.45 (HIGH).

| ID | Kind | Score | Families fired | Why it fires |
| --- | --- | --- | --- | --- |
| BN-EN-024 (EN) | genuine_bank_kyc_alert | 0.45 | link_grab, urgency | Hand-authored bank KYC-update alert — documented failure mode 2; needs a sender-ID allowlist at the app layer, not more tokens. |
| BN-EN-025 (EN) | genuine_bank_kyc_alert | 0.25 | link_grab | Hand-authored bank KYC-update alert — documented failure mode 2; needs a sender-ID allowlist at the app layer, not more tokens. |
| BN-EN-026 (EN) | genuine_bank_kyc_alert | 0.45 | link_grab, urgency | Hand-authored bank KYC-update alert — documented failure mode 2; needs a sender-ID allowlist at the app layer, not more tokens. |
| BN-EN-031 (EN) | marketing_offer | 0.30 | prize | Marketing SMS with 'lucky draw' wording — matches the prize family by design. |
| BN-EN-033 (EN) | broker_market_info | 0.20 | urgency | Broker SMS quoting a market-open time ('9:15 AM today') matches the deadline token. |
| BN-HI-024 (HI) | genuine_bank_kyc_alert | 0.45 | link_grab, urgency | Hand-authored bank KYC-update alert — documented failure mode 2; needs a sender-ID allowlist at the app layer, not more tokens. |
| BN-HI-025 (HI) | genuine_bank_kyc_alert | 0.25 | link_grab | Hand-authored bank KYC-update alert — documented failure mode 2; needs a sender-ID allowlist at the app layer, not more tokens. |
| BN-HI-026 (HI) | genuine_bank_kyc_alert | 0.45 | link_grab, urgency | Hand-authored bank KYC-update alert — documented failure mode 2; needs a sender-ID allowlist at the app layer, not more tokens. |
| BN-HI-031 (HI) | marketing_offer | 0.30 | prize | Marketing SMS with 'lucky draw' wording — matches the prize family by design. |
| BN-TE-024 (TE) | genuine_bank_kyc_alert | 0.45 | link_grab, urgency | Hand-authored bank KYC-update alert — documented failure mode 2; needs a sender-ID allowlist at the app layer, not more tokens. |
| BN-TE-025 (TE) | genuine_bank_kyc_alert | 0.25 | link_grab | Hand-authored bank KYC-update alert — documented failure mode 2; needs a sender-ID allowlist at the app layer, not more tokens. |
| BN-TE-026 (TE) | genuine_bank_kyc_alert | 0.45 | link_grab, urgency | Hand-authored bank KYC-update alert — documented failure mode 2; needs a sender-ID allowlist at the app layer, not more tokens. |
| BN-TE-029 (TE) | toll_challan | 0.30 | money_action | Genuine-looking toll/e-challan SMS containing an amount plus a pay instruction — same shape as a transfer demand. |
| BN-TE-031 (TE) | marketing_offer | 0.30 | prize | Marketing SMS with 'lucky draw' wording — matches the prize family by design. |

The en/hi/te FPs come from four documented failure classes. First and largest: **fixtures written to look like genuine bank KYC-update SMS** (one per language) — a message saying 'update your KYC immediately' with a link is indistinguishable from a phishing script on text alone, which is failure mode 2 exactly as stated in the module docstring. The correct mitigation is not more tokens but a sender-ID allowlist at the app layer (Indian transactional SMS carry verified headers like SB-BANK); the message-only detector deliberately never resolves senders or links so that checking a message never leaks that it was checked. Second: **marketing SMS that say 'lucky draw'** — the prize family matches real brand campaigns. Third, single-language classes: a **broker market-open time** in English and a **toll pay-instruction** in Telugu. Fourth: a Telugu bill reminder where date digits sat inside the transfer-demand window, fixed during corpus construction by requiring an explicit ₹/రూ currency marker on amounts — a fix that also protects every language's amount tokens from phone numbers and dates. The ported Hinglish benign rows add no new >=MODERATE false positives.

What we chose NOT to fix, and why: the KYC-alert FPs could be suppressed by dropping the 'verify/update now' token, but that token is what catches the card-blocked and YONO-phishing scam classes in all three script languages, and the corpus shows those classes score CRITICAL without it. Until the app layer can vouch for sender IDs, flagging a genuine-looking KYC SMS as HIGH and explaining why is the safer error than silently passing a credential-harvesting page as LOW. The FP rate must be re-measured on consent-cleared device corpora once sender metadata is available.

## 6. Method and caveats

Every fixture is scored with the one shipped scorer through `citizen.messageguard.analyze()`: en/hi/te use the default `auto` universe, and Hinglish uses explicit `lang="hinglish"`. The eval runner adds no tuning, no per-fixture overrides and no post-processing. Scores are compared against the fixed band edges from the spec (<0.20 LOW, <0.45 MODERATE, <0.70 HIGH, ≥0.70 CRITICAL) with the ≥3-family ×1.3 boost and the 1.0 cap applied exactly as in the Citizen API. `raksha-code/evals/messageguard/results.json` contains every per-language aggregate and every benign false-positive case for audit; all fixture texts are committed under `raksha-code/citizen/fixtures/messageguard/`. The one reason catalogue is `packages/contracts/reasons.py`; the one generated document is this file. No model, no network and no AI inference are used.

Three caveats bound every number above. First, this is an **in-distribution** evaluation: recall numbers measure catalogue coverage, not field performance, and the corpus is hand-authored, so a model trained on it would learn the author, not the scam — which is why the spec's order (corpus first, model second) is preserved and the classifier remains optional and unbuilt. Second, the benign corpus is authored to *look* like genuine Indian bank/telco/utility traffic but is not a dump of real devices; the FP rate is a floor estimate until consent-cleared device corpora are measured. Third, transliteration coverage remains partial (failure mode 3): the explicit Hinglish token set covers exactly the 46 hand-authored ported rows plus common Latin-script verbs shared with en/hi; the long tail of transliteration variants is not covered and is not measured by any number in this file. Measurement scope: **hand-authored / in-distribution; real-world recall and FPR UNMEASURED**.

## 7. Definition of done — status after this run

- [x] Deterministic and offline (stdlib only; asserted by tests; no AI model invoked)
- [x] Reasons name the family that fired (one `MSG-*` catalogue, no matched phrases in citizen copy)
- [x] Works in en / hi / te plus an explicit Hinglish-Latin port (measured separately above)
- [x] One corpus, one generated eval document, one reason catalogue, one detector interface
- [x] Fixture corpus ≥ 300 messages with per-language coverage — **402 scam + 136 genuine = 538 hand-authored fixtures**
- [x] False-positive rate measured on genuine-alert fixtures — **10.3%** at ≥MODERATE (14/136), every case listed in §5
- [x] Measured accuracy published — **96.8%** overall at the ≥MODERATE operating point (this file and `raksha/EVALS.md`)
- [x] All published numbers explicitly hand-authored / in-distribution; real-world UNMEASURED

The independent alternative Part 3 package and the standalone snapshot are archived under `archive/provenance/` with provenance notes; they are not runtime imports. The 20-item M3 smoke corpus remains for API regression only; it is not the basis of any published accuracy figure. This document is generated and must never be hand-edited.