# PART 3 — CITIZEN FEATURE: MESSAGEGUARD
## (scam-script detection, multilingual)

> **What this is.** The detector that reads a suspicious SMS / WhatsApp message and
> tells the person whether it looks like a known scam script.
>
> **Status:** integrated into `raksha-code/` on 2026-11-26. **Team size (spec):** 2
> people. **Depends on:** Part 1's reason-code and i18n contract. **Completely
> independent of Part 2** — no shared model, no shared features.

---

## 1. What exists

| Piece | State |
|---|---|
| Deterministic signal-family scorer | ✅ built — `raksha-code/citizen/messageguard/scorer.py` |
| English / Hindi / Telugu token sets | ✅ built — `tokens_en.py`, `tokens_hi.py`, `tokens_te.py` |
| Six weighted signal families | ✅ built |
| Verdict bands, `MSG-*` reasons, legacy organ band map | ✅ built |
| Fixture corpus | ✅ **372 scam + 120 genuine = 492 hand-authored, labelled JSONL fixtures** |
| False-positive review | ✅ measured, every FP case listed in `raksha/MESSAGEGUARD_EVALS.md` |
| Reproducible measurement | ✅ `raksha-code/evals/messageguard/run_evals.py --check` + generator |
| Runtime integration | ✅ Citizen `screen_message` endpoint and i18n explanation layer |
| Trained classifier | ❌ not attempted (deliberate) |
| Real-device / field evaluation | ❌ absent; all published numbers remain in-distribution |

The original 20-message M3 corpus is retained only as a smoke regression, not
as a measurement corpus.

### 1.1 How it works

Six signal families, weighted:

| Family | Weight | Catches |
|---|---|---|
| `credential` | 0.45 | OTP / CVV / PIN / UPI-PIN requests, collect-request acceptance |
| `authority` | 0.40 | Police / CBI / ED / RBI / TRAI impersonation, "digital arrest" |
| `money_action` | 0.30 | transfer, fine, bail, processing fee |
| `prize` | 0.30 | lottery, lucky draw |
| `urgency` | 0.20 | 24 hours, last warning, else-clause |
| `link_grab` | 0.25 | shorteners, click / verify now, lookalike domains |

A family contributes its weight once, however many phrases match. Three or
more families hit ⇒ ×1.3 boost, capped at 1.0.
Bands: `<0.20` LOW · `<0.45` MODERATE · `<0.70` HIGH · `≥0.70` CRITICAL.
`bandmap.py` applies the 0.25–0.99 float the Governor's legacy organ RPC
expects. `normalize.py` performs NFKC, casefold, zero-width stripping and
limited acronym de-obfuscation; negation guards stop genuine "do not share
your OTP" deliveries from being treated as credential requests.

---

## 2. Why it is rules, not a model

This is a **deliberate** choice, and it should be defended rather than
apologised for:

1. It runs **offline on a low-end phone** with no download, no GPU, no battery
   cost.
2. It is **explainable** — every hit names the family, a stable `MSG-*` code
   and the matched phrase; the citizen sees a translated sentence, never a raw
   score or the matched scam phrase.
3. It has **zero training data requirement**, so it can ship today.

**The cost:** it misses novel scripts and will false-positive on genuine urgent
bank messages. The measured 11.7% false-positive rate on hand-authored
genuine-alert fixtures is published with every false-positive case in
`raksha/MESSAGEGUARD_EVALS.md §5`. Real-world recall and false-positive rate
remain UNMEASURED.

---

## 3. What requires model training

Optional, and only after a real corpus exists. Training on hand-authored
messages would produce a model that detects the author, not the scam — this is
exactly the mistake Part 2 already made once and had to undo.

| Task | Data needed | Status |
|---|---|---|
| Consent-cleared Indian scam-message corpus | 2–5k labelled, hi/te/en, real-device traffic with sender metadata | ❌ not collected |
| Small text classifier (ONNX, <5 MB) | — | ❌ not attempted |
| Per-language field evaluation | — | ❌ blocked on corpus |

**Order matters: corpus first, model second.** The optional classifier stays
behind the same interface and behind the corpus.

---

## 4. Build order

1. [x] Signal families + weights
2. [x] Three-language token sets
3. [x] Fixture corpus expanded from 20 to 492 messages with per-language coverage
4. [x] Per-language false-positive review
5. [x] Runtime integration into the Citizen API and shared i18n reason layer
6. [x] Reproducible eval runner and generated published report
7. [ ] *(Optional)* trained classifier behind the same interface, after a real corpus

---

## 5. Definition of done

- [x] Deterministic and offline (stdlib only; asserted by tests)
- [x] Reasons name the family that fired and use stable `MSG-*` codes
- [x] Works in three scripts (en / hi / te token sets; measured separately)
- [x] Fixture corpus ≥ 300 messages with per-language coverage — **492 fixtures**
- [x] False-positive rate measured on genuine-alert fixtures — **11.7%** at ≥MODERATE
- [x] Measured accuracy published — **96.5%** overall at the ≥MODERATE operating point

The honest claim is still *"it recognises the scam patterns we thought of"*
plus a measured false-positive cost on hand-authored genuine-alert fixtures. It
is **not** a field accuracy claim.

---

## 6. Known failure modes

1. **Novel scripts.** Anything not in the token catalogue is invisible; three
   deliberately benign-like calibration fixtures keep this visible in the eval.
2. **Legitimate urgency.** A genuine-looking bank KYC-update alert with a link
   and "immediately" scores like phishing. A sender-ID allowlist at the app
   layer is the mitigation; more tokens are not.
3. **Transliteration.** Hinglish in Latin script is only partly covered.
4. **Obfuscation.** Spaced `O T P` is partially mitigated; homoglyphs defeat
   exact tokens.
5. **No URLs fetched.** Links are pattern-matched, never resolved — deliberate,
   so the app never leaks that a message was checked.

---

## 7. Independence and integration note

The standalone Part 3 tree at
`../random project that ew need to integrate/raksha/` has been folded into the
main application. It is retained as a provenance snapshot; the runtime source
of truth is `raksha-code/citizen/messageguard/`. Part 2 and Part 3 still share
**no scoring code**. They do share the Citizen presentation layer:
`citizen/voiceguard/i18n.py` translates the stable `MSG-*` codes, and an
integration test asserts that map cannot drift from
`citizen/messageguard/reasons.py`.
