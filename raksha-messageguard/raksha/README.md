# Raksha — Part 3: MessageGuard

The citizen feature that reads a suspicious SMS / WhatsApp message and tells
the person whether it looks like a known scam script, with the reason shown
in their own language. Team size: 2. Depends on Part 1 (reasons, i18n) only;
completely independent of Part 2 — no shared model, no shared features.

```
raksha/
├── EVALS.md                  measured accuracy, false-positive review, gates
├── pyproject.toml
├── raksha/
│   ├── reasons/              Part 1 contract: reason-code enum + citizen i18n (en/hi/te)
│   ├── messageguard/         the detector: tokens, families, scorer, legacy organ RPC adapter, CLI
│   └── evals/                evaluation harness + generated results (results/latest.json, .md)
├── corpus/                   324 scam + 107 genuine fixtures (en/hi/te/hinglish) — see corpus/README.md
└── tests/                    990 pytest tests incl. corpus-integrity and DoD gates
```

## 1. How it works

Six deterministic signal families, weighted:

| Family | Weight | Catches |
|---|---|---|
| `credential` | 0.45 | OTP / CVV / PIN / UPI-PIN requests, collect-request acceptance |
| `authority` | 0.40 | Police / CBI / ED / RBI impersonation, "digital arrest" |
| `money_action` | 0.30 | transfer, fine, bail, processing fee |
| `prize` | 0.30 | lottery, lucky draw |
| `urgency` | 0.20 | 24 hours, last warning, else-clause |
| `link_grab` | 0.25 | shorteners, "click / verify now" |

Raw score = sum of the weights of the distinct families that fired. Three or
more families hit => x1.3 boost, capped at 1.0. Bands:
`< 0.20` LOW | `< 0.45` MODERATE | `< 0.70` HIGH | `>= 0.70` CRITICAL.

The adapter in `raksha/messageguard/legacy_organ.py` maps every verdict into
the 0.25-0.99 numeric band the Governor's legacy organ RPC expects
(band-consistent, monotone, label-authoritative), so the same scorer can feed
the shared graph without a contract change.

Matching details that matter:

- Requests, not mentions. "Never share your OTP" (a genuine bank warning)
  does not fire; "share your OTP" (a request) does. A negation-guard list
  suppresses the credential family when genuine bank warning phrasing is
  present.
- Impersonation is entity-plus-role pairing ("CBI" + "officer"), so "as per
  RBI guidelines" cannot fire the authority family.
- Only shortener domains and scam-favourite TLDs are link signals; a genuine
  bank URL on its own domain does not fire.
- English tokens are merged into the Hindi/Telugu universes, because real
  scam SMS mix scripts freely ("आपका OTP बताइए").

## 2. Why it is rules, not a model

This is a deliberate choice, and it should be defended rather than
apologised for:

1. It runs **offline on a low-end phone** with no download, no GPU, no
   battery cost (pure Python stdlib; a corpus-wide pass takes ~0.2 s).
2. It is **explainable** — every hit names the family and the matched phrase.
   A person can see *why* it fired, which matters more than 3% accuracy.
3. It has **zero training data requirement**, so it can ship today.

**The cost:** it misses novel scripts and will false-positive on genuine
urgent payment messages from a real bank. That is stated in the module
docstring (`raksha/messageguard/scorer.py`) and measured and published in
[EVALS.md](EVALS.md) — it must stay stated.

### Known failure modes (spec section 6, kept verbatim in spirit)

1. **Novel scripts.** Anything not in the token set is invisible.
2. **Legitimate urgency.** A real bank fraud alert ("your card is blocked,
   call this number") looks like `authority` + `urgency`. Measured: 2.4% of
   genuine bank alerts reach MODERATE caution, 0% reach HIGH flag.
3. **Transliteration.** Hinglish written in Latin script is only partly
   covered.
4. **Obfuscation.** Spaced-out text (`O T P`) or homoglyphs defeat exact
   tokens. The `obfuscation_gap` corpus category demonstrates this and the
   eval reports it separately.
5. **No URLs fetched.** Links are pattern-matched, never resolved —
   deliberate, so the app never leaks that a message was checked.

## 3. What requires model training

Optional, and only after the rules have a real corpus to be measured against.

| Task | Data needed | Effort |
|---|---|---|
| Indian scam-message corpus | 2-5k labelled, hi/te/en, consent-cleared | 2-3 weeks |
| Small text classifier (ONNX, < 5 MB) | — | 1 week |
| Per-language evaluation | — | 3 days |

**Order matters: corpus first, model second.** Training on hand-authored
messages produces a model that detects the author, not the scam — exactly the
mistake Part 2 already made once and had to undo. Until that corpus exists,
the trained classifier is not attempted; the seam for it is the same
`assess(text, lang) -> Verdict` interface.

## 4. Build order (spec section 4) — status after this build

1. Signal families + weights — **done** (reference implementation in
   `raksha/messageguard/families.py`).
2. Three-language token sets — **done** (`raksha/messageguard/tokens.py`,
   en/hi/te + hinglish, with mixed-script phrases).
3. Fixture corpus expansion from 20 to several hundred — **done**: 324 scam +
   107 genuine fixtures, per-language coverage (en 104/43, hi 95/24,
   te 95/24, hinglish 30/16).
4. Per-language false-positive review — **done**: every FP reviewed; 2
   accepted caution-level FPs documented, 2 real bugs found and fixed
   (shortener domain lookbehind; zero-width-joiner token normalization), 4
   token sets tuned. Full trail in [EVALS.md](EVALS.md) section 4.
5. *(Optional)* trained classifier behind the same interface — **not
   attempted**, deliberately (see section 3 above).

## 5. Definition of done (spec section 5)

- [x] Deterministic and offline — verified by test; verdict hash recorded in EVALS.md
- [x] Reasons name the family that fired — family + matched phrase on every reason
- [x] Works in three scripts — en / hi / te (+ hinglish), 100% detection@HIGH in each
- [x] Fixture corpus >= 300 messages with per-language coverage — 324 scam fixtures (min 28 per language)
- [x] False-positive rate measured on genuine bank alerts — 0/85 flagged, 2/85 cautioned
- [x] Measured accuracy published in `EVALS.md` — [EVALS.md](EVALS.md)

## 6. Independence note (spec section 7)

Parts 2 and 3 share **no code** beyond Part 1's reason catalogue
(`raksha/reasons/` — the reason-code enum and citizen i18n). They can be
built in parallel by separate people with no coordination beyond the
reason-code enum. This tree contains only Part 3 and the Part 1 contract
stand-in; Part 2 is absent by design. In the monorepo, replace
`raksha/reasons/` with Part 1's package — the interface is
`ReasonCode`, `reason_text(code, lang, phrase)`, `BAND_LABELS`,
`BAND_ADVICE`, `FAMILY_LABELS`.

## 7. Usage

```python
from raksha.messageguard import assess, to_legacy_organ_payload

v = assess("आपका KYC आज समाप्त, वरना खाता ब्लॉक हो जाएगा — bit.ly/kyc9")
v.band            # Band.HIGH
v.score           # 0.45
v.families        # ('link_grab', 'urgency')
v.citizen("hi")   # Hindi band label + advice + per-hit reason sentences
to_legacy_organ_payload(v).confidence   # 0.70 — inside the legacy 0.25-0.99 band
```

CLI:

```
python -m raksha.messageguard "your message text"
python -m raksha.messageguard --lang hi --legacy "..."
python -m raksha.messageguard --json "..."
```

Evaluation and tests:

```
python -m pytest tests                     # 990 tests incl. DoD gates
python -m raksha.evals.run_evals           # tables + results/ files
python -m raksha.evals.run_evals --review  # full false-positive listing
```

Requires Python >= 3.9. Zero runtime dependencies. No network access anywhere
in the detector.
