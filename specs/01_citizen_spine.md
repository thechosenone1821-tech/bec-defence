# PART 1 — CITIZEN SPINE
## (shared risk engine, multilingual layer, capture & privacy, report rail)

> **What this is.** The spine of the three-feature Citizen app. It is the thing
> every citizen feature plugs into, and the thing that guarantees the app is
> honest, private, and speaks the user's language.
>
> **Why it is its own part.** Parts 2 and 3 are detectors. This part decides what
> a *person* is told, in what language, with what action. Those are different
> skills, different bugs, and — critically — different failure modes. A detector
> that is 60% right is a weak detector. A risk engine that reassures someone
> wrongly is a dangerous product.
>
> **Team size.** 2 people. **Depends on:** Part 7 (report rail only).

---

## 1. What this part owns

| Component | Responsibility | Real today? |
|---|---|---|
| **Citizen Risk Engine** | Fuses voice + message + campaign link + repeat contact + user doubt into **one** verdict with plain-language reasons | ✅ built |
| **Multilingual layer** | Every reason code renders a real sentence in en / hi / te; every non-trivial verdict ends with an action | ✅ built |
| **Capture & privacy** | 3-second ring buffer, consent gate, visible recording indicator, zero retention | ✅ built |
| **Report rail** | Signed, tokenised, minimal report into the shared graph | ✅ built |
| **Panic button** | Lock the screen → stop capture → dial 1930 | ✅ built (Phase 2) |
| **Family mode** | Stricter defaults and louder warnings for elders | ✅ built (Phase 2) |

**Correction (Phase 1), now resolved (Phase 2).** This table previously marked the
panic button ✅ and described it as *"one tap to 1930 with the screen locked behind
it"* when `index.html` contained a `tel:1930` link and nothing else. Phase 2 built
it for real, in the only safe order: **lock → stop capture → dial**. If the dialler
opened first, the phone app would cover the scam screen and the user would return
to an unchanged, still-convincing page.

**What the panic button cannot do, and why.** It cannot end the scammer's call,
kill other apps, or "close the session". That requires Android accessibility
permissions, which §8 of this document forbids (no IME or keystroke access).
The original spec promised it anyway. A privacy rule that is abandoned the moment
it becomes inconvenient is not a privacy rule.

---

## 2. The rule that governs everything here

> **"Nothing found" is not "nothing wrong".**

There is **no `SAFE` verdict anywhere in this part.** The lowest band is
`LOW_CONFIDENCE`, and its copy says so:

> *"Not enough information to judge. Trust your instinct. If they ask for money
> or OTP, hang up and call 1930."*

A system that says "this is safe" when it merely has no information is worse than
no system, because it transfers the victim's judgement to software that has not
earned it. If you contribute here and add a reassuring state, the PR will be
refused — not because of style, but because that is the exact bug this part exists
to prevent.

### 2.1 Bounded fusion, declared weights

Signals combine by bounded noisy-OR, so the score can never exceed 1.0 and no
single signal dominates. The weights are **constants in source**, not learned,
because a district hospital's IT generalist must be able to read the file and
disagree with it in a meeting.

| Signal | Weight |
|---|---|
| Voice: likely synthetic | 0.65 |
| Voice: suspicious | 0.40 |
| Message: critical | 0.60 |
| Message: high | 0.35 |
| Campaign link (same pattern reported before) | 0.45 |
| Repeat contact (≥3 attempts) | 0.20 |
| User's own doubt | 0.15 |

**Corroboration rule.** A band above `LOW_CONFIDENCE` requires *either* one
standalone source (voice / message / campaign) *or* at least two contributing
signals. A single weak nudge — someone's own unease at 0.15 — stays
`LOW_CONFIDENCE`. This was a real bug: it previously told a nervous person
"no known fraud warning signs found" on the strength of their own doubt.

### 2.2 Never show a raw score

A citizen cannot act on "0.83". The UI shows a headline, an action, and
sentences. The score exists for diagnostics and never reaches the screen.

---

## 3. Multilingual is a correctness requirement, not a feature

Three languages: **English, Hindi, Telugu.** Non-negotiable rules:

1. Every reason code has a real translation. A missing string on a scam warning
   is a real-world failure.
2. Tests assert the hi/te text is **actually Devanagari / Telugu script**. Pasting
   English into the Hindi column passes a naive parity test and fails a real
   citizen.
3. Unknown language falls back to English — never renders a raw key.
4. Every verdict's action mentions a concrete step: hang up, call 1930, call the
   official number on your card.

**Known gap:** the *voice model* has no phonetic model, so it cannot claim
anything about accented speech. Only the UI is multilingual. Do not conflate
these in a demo.

---

## 4. Capture and privacy

| Guarantee | How it is enforced |
|---|---|
| Consent before any recording | `CaptureSession` raises `RetentionError` without consent |
| 3-second rolling buffer | `RING_SECONDS = 3.0`; older audio is overwritten, not stored |
| Visible indicator | `indicatorVisible` is true **only** while state is `CAPTURING` |
| Buffer zeroed on stop | Worklet zeroes the ring on `"stop"` |
| Audio never leaves the device | API accepts samples, returns a verdict, echoes nothing back |

The indicator bug is worth reading: it was set from "not idle" rather than
"capturing", so it stayed lit after a stop. A recording light that is on when
nothing is recording trains people to ignore the light.

---

## 5. Interfaces

**Exposes (to Parts 2 and 3):**
```
assess(voice=…, message=…, campaign_linked=…, repeat_contacts=…, user_doubt=…, lang=…)
   → { band, score, signals, headline, action, helpline, degraded }
explain(score_voice_result, lang) → { title, action, reasons[], actionable }
```

**Consumes from Part 7:** the report rail only.

**Owns these endpoints:** `POST /api/citizen/assess`, `GET /api/citizen/languages`,
`POST /api/citizen/report`, `GET /api/citizen/retention`.

---

## 6. Build order

1. Reason catalogue + three languages (nothing else can render without it)
2. `explain()` and the "no reassurance" copy
3. Risk engine + the corroboration rule
4. Capture, consent, indicator
5. Report rail
6. Family mode — **built in Phase 2** (`citizen/app/family.js`, 123 lines, 15 assertions in `panic_family.test.js`)

---

## 7. Definition of done

- [ ] Empty assessment returns `LOW_CONFIDENCE`, never `LOW`
- [ ] A single weak signal stays undecided
- [ ] No `SAFE` band exists in the module
- [ ] Every reason code renders in three languages, verified by script range
- [ ] `INCONCLUSIVE` copy tells the user to hang up if money is mentioned
- [ ] Recording is impossible without consent; the indicator is off when stopped
- [ ] Audio is never echoed in any response

---

## 8. What this part does not do

- It does not detect voices (Part 2) or scam text (Part 3).
- It does not claim any accuracy — it has none of its own to claim.
- It does not store, upload, or retain audio under any configuration.

---

## 9. Family mode (Phase 2)

The people who most need this app are the least able to judge a verdict.

| Behaviour | Effect |
|---|---|
| **Stricter** | A `MODERATE` band becomes actionable on screen instead of staying advisory |
| **Louder** | Larger type, roomier targets (≥52 px), no auto-dismiss |
| **Simpler** | The severity slider is hidden on the report screen |

**The hard rule: family mode changes presentation, never a verdict.** The same
clip must receive the same answer regardless of who is holding the phone. The
escalation is *labelled* on screen ("· FAMILY MODE") so the user is never told the
detector said something it did not.

Stored in `localStorage` only. No account, no sync, no server-side profile — this
is §8, not a TODO. Default is **off**; a mode that activates without the user
asking would be its own false claim.
