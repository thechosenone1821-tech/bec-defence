# PART 3 — CITIZEN FEATURE: MESSAGEGUARD
## (scam-script detection, multilingual)

> **What this is.** The detector that reads a suspicious SMS / WhatsApp message and
> tells the person whether it looks like a known scam script.
>
> **Team size.** 2 people. **Depends on:** Part 1 (reasons, i18n).
> **Completely independent of Part 2** — no shared model, no shared features.

---

## 1. What exists

| Piece | State |
|---|---|
| Deterministic signal-family scorer | ✅ built |
| English / Hindi / Telugu token sets | ✅ built |
| Six weighted signal families | ✅ built |
| Verdict bands + reasons | ✅ built |
| Fixture corpus | ⚠️ 20 hand-authored messages — **small** |
| Trained classifier | ❌ not attempted (deliberate) |

### 1.1 How it works

Six signal families, weighted:

| Family | Weight | Catches |
|---|---|---|
| `credential` | 0.45 | OTP / CVV / PIN / UPI-PIN requests, collect-request acceptance |
| `authority` | 0.40 | Police / CBI / ED / RBI impersonation, "digital arrest" |
| `money_action` | 0.30 | transfer, fine, bail, processing fee |
| `prize` | 0.30 | lottery, lucky draw |
| `urgency` | 0.20 | 24 hours, last warning, else-clause |
| `link_grab` | 0.25 | shorteners, "click / verify now" |

Three or more families hit ⇒ ×1.3 boost, capped at 1.0.
Bands: `<0.20` LOW · `<0.45` MODERATE · `<0.70` HIGH · `≥0.70` CRITICAL.

Code applies the 0.25–0.99 band the Governor's legacy organ RPC expects, so the
same scorer can feed the shared graph without a contract change.

---

## 2. Why it is rules, not a model

This is a **deliberate** choice, and it should be defended rather than apologised
for:

1. It runs **offline on a low-end phone** with no download, no GPU, no battery
   cost.
2. It is **explainable** — every hit names the family and the matched phrase.
   A person can see *why* it fired, which matters more than 3% accuracy.
3. It has **zero training data requirement**, so it can ship today.

**The cost:** it misses novel scripts and will false-positive on a genuine urgent
payment message from a real bank. That is stated in the module docstring and must
stay stated.

---

## 3. What requires model training

Optional, and only after the rules have a real corpus to be measured against.

| Task | Data needed | Effort |
|---|---|---|
| Indian scam-message corpus | 2–5k labelled, hi/te/en, consent-cleared | 2–3 weeks |
| Small text classifier (ONNX, <5 MB) | — | 1 week |
| Per-language evaluation | — | 3 days |

**Order matters: corpus first, model second.** Training on hand-authored messages
produces a model that detects the author, not the scam — this is exactly the
mistake Part 2 already made once and had to undo.

---

## 4. Build order

1. Signal families + weights (done)
2. Three-language token sets (done)
3. Fixture corpus — **expand from 20 to several hundred** ← start here
4. Per-language false-positive review
5. *(Optional)* trained classifier behind the same interface

---

## 5. Definition of done

- [x] Deterministic and offline
- [x] Reasons name the family that fired
- [x] Works in three scripts
- [ ] Fixture corpus ≥ 300 messages with per-language coverage
- [ ] False-positive rate measured on **genuine** bank alerts (not scam messages)
- [ ] Measured accuracy published in `raksha/EVALS.md`

The last three are missing. Right now the only honest claim is *"it recognises
the scam patterns we thought of."*

---

## 6. Known failure modes

1. **Novel scripts.** Anything not in the token set is invisible.
2. **Legitimate urgency.** A real bank fraud alert ("your card is blocked, call
   this number") looks like `authority` + `urgency`.
3. **Transliteration.** Hinglish written in Latin script is only partly covered.
4. **Obfuscation.** Spaced-out text (`O T P`) or homoglyphs defeat exact tokens.
5. **No URLs fetched.** Links are pattern-matched, never resolved — deliberate, so
   the app never leaks that a message was checked.

---

## 7. Independence note

Parts 2 and 3 share **no code** beyond Part 1's reason catalogue. They can be
built in parallel by separate people with no coordination beyond the reason-code
enum. This is intentional: it is the cheapest way for two teams to work without
blocking each other.
