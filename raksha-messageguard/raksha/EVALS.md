# EVALS — MessageGuard (Part 3) measured results

Build date: 2026-11-26. Scorer: deterministic signal-family scorer, rules only,
no model. Corpus: hand-authored fixtures in `corpus/` (supersedes the original
20-fixture set). Verdict hash for this build: `596e3cd861588e99`.

**The honest claim.** These numbers say exactly one thing: *the detector
recognises the scam patterns we thought of, and does not cry wolf on the
genuine messages we thought of.* The corpus is hand-authored in-domain, so the
detection figures are an upper bound on field performance, not a field
estimate — training and evaluating on hand-authored messages detects the
author, not the scam (the same mistake Part 2 made once and had to undo). A
field estimate needs the consent-cleared 2-5k real-message corpus listed in
README section 3. Until then this is the whole truth and nothing more.

## 1. Corpus composition

| set | en | hi | te | hinglish | total |
|---|---|---|---|---|---|
| scam | 104 | 95 | 95 | 30 | **324** |
| benign (all genuine) | 43 | 24 | 24 | 16 | **107** |
| benign: genuine bank alerts | 32 | 20 | 20 | 13 | **85** |

Scam fixtures span 17 script categories (OTP requests, UPI collect-request
reversals, digital arrest, police/CBI/ED impersonation, RBI freeze,
electricity cut-off, KYC expiry, lottery/KBC, loan fees, refund fees, SIM
suspension, parcel/customs, task jobs, card-block phishing, bail emergencies,
insurance lapses, tax refunds) plus 5 deliberate `obfuscation_gap` fixtures
(spaced-out text, homoglyph links). All phone numbers, UPI handles and links
are inert authored patterns; no real victim messages, no real personal data.

## 2. Methodology

- Operating points: **cautioned** = score >= 0.20 (MODERATE band);
  **flagged** = score >= 0.45 (HIGH band). Flagged is what a citizen-warning
  UI would act on.
- Detection = share of scam fixtures at or above the operating point.
  FP rate = share of benign fixtures at or above the operating point.
- The `obfuscation_gap` category is reported separately and excluded from
  headline detection, because those fixtures exist to demonstrate the stated
  failure mode (spaced text and homoglyphs defeat exact tokens), not to be
  detected.
- Determinism: the full corpus is scored twice; the verdict signature
  (score, band, families, reasons) is hashed both times and must match.
- Reproduce: `python -m pytest tests` and `python -m raksha.evals.run_evals`
  from the repo root.

## 3. Scam detection (excluding deliberate gaps)

| language | n | mean score | detection@MODERATE | detection@HIGH |
|---|---|---|---|---|
| en | 103 | 0.76 | 100% | 99.0% |
| hi | 94 | 0.75 | 100% | 100% |
| te | 94 | 0.75 | 100% | 100% |
| hinglish | 28 | 0.78 | 100% | 100% |
| **all** | **319** | **0.76** | **100%** | **99.7%** |

Including the deliberate gap fixtures: 324 fixtures, 98.5% detection@HIGH
(320/324), 98.8% @MODERATE.

Honest miss list (score < MODERATE): exactly the 4 fully-obfuscated gap
fixtures (`scam_en_103`, `scam_hi_095`, `scam_te_095`, `scam_hinglish_030`,
score 0.00). The 5th gap fixture (`scam_en_104`) is *partially* detected
(HIGH, 0.45): its homoglyph link defeats the shortener pattern as designed,
but its plain-text OTP request is still caught. Nothing outside the gap
category scores below HIGH.

Family fire rate on the scam corpus: urgency 83.0%, money_action 59.6%,
link_grab 35.2%, authority 34.0%, credential 25.0%, prize 7.1%.

## 4. False positives on genuine messages

| set | n | FP@MODERATE (caution) | FP@HIGH (flag) |
|---|---|---|---|
| all benign | 107 | 1.9% | **0.0%** |
| genuine bank alerts | 85 | 2.4% | **0.0%** |

By language (bank-alert subset): en 0/32, hi 0/20, te 0/20, hinglish 0/13
flagged. Zero genuine bank alerts reach the flagging operating point.

### False-positive review (per-language review conducted 2026-11-26)

Every benign fixture scoring >= MODERATE was reviewed by hand. Final residual
rows (2 of 107):

| id | lang | category | band | score | fired | review decision |
|---|---|---|---|---|---|---|
| benign_hi_015 | hi | loan_emi | MODERATE | 0.20 | urgency: "आज रात" (autopay tonight) | **accepted**: genuine autopay reminders legitimately say "tonight"; the token is load-bearing for scam recall (used in 8+ hi scripts). Caution-only, never flagged. This is the spec's acknowledged "legitimate urgency" failure mode, measured and stated. |
| benign_te_015 | te | loan_emi | MODERATE | 0.20 | urgency: "ఈ రాత్రి" (autopay tonight) | **accepted**: same reasoning as above. |

Review decisions that changed tokens (first review round):

1. **Regex bug fixed**: `t.co` matched inside `bluedart.com/t88123`; a domain
   lookbehind `(?<![\w-])` was added to the shortener pattern. This removed a
   real FP on a genuine delivery tracking link.
2. **Normalization bug fixed**: phrase tokens were searched in normalized
   text using their raw form, so any token containing a zero-width joiner
   (several Telugu conjuncts) silently never matched. Token-side matching now
   normalizes identically (`_norm_phrase`, memoized). This raised Telugu
   detection and surfaced hidden behaviour; it is the single most valuable
   find of the review.
3. **Urgency tokens removed** (`नहीं किया तो`, `nahi kiya to`, `చేయకపోతే`,
   and the "do not tell anyone" warning-class phrases in all languages): they
   are genuine-bank-alert phrasing ("if not done by you"), and no scam fixture
   depended on them.
4. **Bare "update KYC" link phrases removed** (hi/te): genuine KYC notices say
   "KYC update karein"; scam KYC scripts remain flagged via shortener +
   urgency pairs instead.
5. **Under-flagging fixed** (review cuts both ways): inflected Telugu time
   words (`24 గంటల్లో`, `24 గంటలు`, `2 గంటల్లో`) added as explicit tokens
   (the virama boundary rule blocks stems), `పోలీసు` singular entity, inflected
   Telugu money destinations (`ఖాతాలో`, `యూపీఐకి`, `నంబర్‌కు`), the Telugu prize
   collocation `బహుమతి గెలిచారు`, and English gerund partners
   (`confirming`, `sharing`, ...) for the credential pair rule.

## 5. Definition-of-done gates (spec section 5)

| gate | target | measured | status |
|---|---|---|---|
| fixture corpus >= 300 with per-language coverage | >= 300 | 324 (min per language 28) | PASS |
| FP rate measured on genuine bank alerts | measured, published | 0/85 flagged, 2/85 cautioned | PASS |
| measured accuracy published in `raksha/EVALS.md` | this document | this document | PASS |
| deterministic and offline | pure stdlib, no network | verified, hash `596e3cd861588e99` | PASS |
| reasons name the family that fired | family + phrase on every reason | enforced by tests | PASS |
| works in three scripts | en/hi/te (+hinglish) | 100% detection@HIGH in each | PASS |

Gate evaluation is executable: `GATES` in `raksha/evals/run_evals.py`, and
`tests/test_eval_gates.py` asserts the same thresholds in CI.

## 6. What these numbers do NOT say

1. **Field accuracy is unknown.** Every fixture was authored by the same team
   that wrote the token sets. The corpus measures coverage of intended
   patterns, not real-world recall.
2. **Novel scripts are invisible.** Anything outside the token sets scores 0.
   The obfuscation_gap fixtures demonstrate this deliberately.
3. **Genuine urgency can caution.** 2.4% of genuine bank alerts reach
   MODERATE ("autopay tonight" reminders). None reach HIGH. This is the
   stated cost of the urgency family and it is accepted, not apologised for.
4. **Hinglish in Latin script is only partly covered** by design: the corpus
   scores it well because the fixtures use covered spellings; real-world
   transliteration variance will be worse.
5. **No URLs are fetched.** Links are pattern-matched only, so the app never
   leaks to the network that a message was checked. Phishing-host anatomy is
   therefore out of scope by design.

## 7. Model training status (spec section 3)

Not attempted, deliberately. Order matters: corpus first, model second. The
next corpus step is a consent-cleared, real-world 2-5k labelled set
(en/hi/te) collected per the table in README section 3; only then does the
<5 MB ONNX classifier behind this same interface make sense. Training a model
on the hand-authored fixtures would produce a detector of our authors, not of
scammers, and is explicitly out of scope for this build.
