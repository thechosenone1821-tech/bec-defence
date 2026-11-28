> Historical provenance: the retired voice-scorer code was removed from executable paths. Active status lives in [docs/STATUS.md](../docs/STATUS.md); see the [retired code note](../archive/provenance/RETIRED.md). Real-world privacy efficacy remains UNMEASURED.

# PART 1 — CITIZEN SPINE · THREE-PHASE BUILD ROADMAP

> **This file is the build plan AND the build log for Part 1.** Each phase is
> executed here, with what actually happened written underneath it — including
> the things that turned out to be false.
>
> **Part 1 file:** [`01_citizen_spine.md`](01_citizen_spine.md)
> **Depends on:** Part 7 (report rail only). **Team:** 2 people.

---

## Why this roadmap exists in this shape

Read against the definition of done in `01_citizen_spine.md` before planning, and
three things were already true that the spec had not accounted for:

1. Most of the spine **already works**. A roadmap that "builds the risk engine"
   would be fiction.
2. One row in the spec's own table claims something **that is not true** —
   Part 1 does not own the panic button's behaviour; there is only a `tel:` link.
3. The Definition of Done listed seven checkboxes, **none of which had a
   corresponding test**. "Built" and "verified" were being conflated.

So the phases are organised around **making claims true and tested**, not around
writing new modules.

---

## The three phases

| Phase | Theme | Question it answers |
|---|---|---|
| **1** | **Truth & verification** | Is every claim in Part 1 actually true, and does a test prove it? |
| **2** | **Complete the spine** | Are the missing behaviours (panic, family mode) real? |
| **3** | **Harden & ship** | Does it survive hostile input, sensors, and a cold audit? |

---

# PHASE 1 — TRUTH & VERIFICATION

**Goal:** no claim in Part 1 without a test that would fail if it were false.

### Scope

| # | Task | Why |
|---|---|---|
| 1.1 | Audit every row of the Part 1 status table against the code | two rows were wrong |
| 1.2 | Make the DoD executable — one test per checkbox | 7 claims, 0 tests |
| 1.3 | Fix "never show a raw score" — the message tab shows one | direct contradiction of §2.2 |
| 1.4 | Make the message tab speak three languages | §3 says it must; it was English-only |
| 1.5 | Give the report rail a citizen-facing wrapper | raw event jargon was reaching the screen |
| 1.6 | Report the truth about the panic button | spec claimed behaviour that does not exist |

### Out of scope for Phase 1

Building the panic *behaviour* (Phase 2), family mode (Phase 2), any new model.

---

## Execution log — Phase 1

*(written as it was done)*

### 1.1 Audit result

| Part 1 row | Spec claim | Reality found |
|---|---|---|
| Citizen Risk Engine | ✅ built | ✅ true |
| Multilingual layer | ✅ built | ✅ **half ** true — voice was translated, **message was not** |
| Capture & privacy | ✅ built | ✅ true |
| Report rail | ✅ built | ✅ true (tokenised, signed) |
| **Panic button** | ✅ built, *"one tap to 1930 **with the screen locked behind it**"* | ❌ **false** — a `tel:1930` link and nothing else |
| Family mode | ❌ not built | ✅ true (confirmed absent) |

The panic row is the notable one: the spec asserted a safety behaviour that had
never been written. That is now corrected in both files rather than quietly
deleted.

### 1.2 The DoD made executable

Every checkbox in `01_citizen_spine.md` §7 now has a test in
`tests/test_part1_citizen_spine.py`. Several were **already true and already
tested** (the SAFE-band ban, the corroboration rule) — those tests were
referenced rather than rewritten, because duplicating a test teaches nothing and
doubles what has to be maintained.

### 1.3 "Never show a raw score" — violated

The message tab rendered `Score 0.65 · credential, urgency`. §2.2 says a citizen
cannot act on a number. Replaced with verdict + matched phrases + a single action
line, in the user's language.

### 1.4 The message tab was English-only

`screen_message` accepted `lang` and ignored it for the *rendering* — the API
returned a translated disclaimer but the tab printed raw reason strings like
`credential: 1 signal(s)`. Now the client requests `lang`, the server returns
translated sentences, and the raw diagnostic keys stay in the payload for
developers but never reach the screen.

### 1.5 Report rail: a citizen wrapper

Added `citizen/voiceguard/i18n.render_report()` so the report screen says
*"Report sent. Nothing personal was included."* instead of `Event evt_cit_ab12 ·
severity 0.85`.

### 1.6 Panic claim corrected

`01_citizen_spine.md` now reads **⚠️ partial — helpline link only**, with "lock the
screen, kill known-scam sessions" explicitly moved to Phase 2. A false ✅ is
worse than an honest ⚠️.

### Phase 1 result — ✅ COMPLETE

```
pytest tests/test_part1_citizen_spine.py   → 40 passed
pytest tests/ -q                           → 338 passed
node --test tests/maya_capture.test.js     → 30 passed
```

**368 checks, 0 failures.**

Verified against a **live server**, not only the test client:

| Check | Result |
|---|---|
| Message tab in en / hi / te | "This looks like a scam message" / "यह धोखाधड़ी का संदेश लगता है" / "ఇది మోసపు సందేశంలా ఉంది" |
| Raw score in the explanation | **absent** (`score` still in the payload for diagnostics) |
| Report wrapper in Telugu | "నివేదిక పంపబడింది" with the what-did-not-leave-the-phone sentence |
| Event id leaked to the citizen | **no** |

### What Phase 1 actually changed

| Task | Outcome |
|---|---|
| 1.1 Audit | 2 of 6 status rows were wrong or half-wrong |
| 1.2 DoD executable | +40 tests, one per checkbox |
| 1.3 Raw score | removed from the message tab; `explain_message()` added |
| 1.4 Three languages | message tab now translated end to end |
| 1.5 Report wrapper | `explain_report()`; event ids no longer reach the screen |
| 1.6 Panic honesty | spec corrected from ✅ to ⚠️ |

### Bugs found while doing Phase 1

1. **`Explain_message` fell back to voice wording.** The empty-message case
   rendered *"This clip does not give a clear answer"* — a sentence about audio on
   a text-message screen. Replaced with message-specific copy that also refuses to
   imply safety.
2. **The panic button in the spec was fiction.** Asserted a screen lock that has
   never existed. Now ⚠️ with the missing behaviour moved to Phase 2.
3. **Three of my own new tests were wrong** before they were right — a substring
   check that flagged the ordinary English word "prize", a `CaptureSession`
   constructor signature I guessed instead of reading, and a report assertion on
   the wrong noun. They were fixed by reading the code, not by weakening the
   assertion.

**Phase 1 closed the gap between "we wrote it" and "we proved it". Phase 2 builds
the two things that are genuinely missing.**


---

# PHASE 2 — COMPLETE THE SPINE ✅ COMPLETE

**Goal:** the two behaviours Part 1 claims are still missing.

| # | Task | Why it matters |
|---|---|---|
| 2.1 | **Panic button: real behaviour** — confirm-first flow, screen lock overlay, end active capture, then dial 1930 | A helpline link is not a panic button |
| 2.2 | **Family mode** — stricter defaults for elders | The people who most need the app are least able to judge a verdict |
| 2.3 | On-device preference storage for family mode (no account, no server) | Privacy constraint from §8 |
| 2.4 | Voice tab in three languages end to end | Partially done; verify the action copy in all three |

### 2.1 Panic button design (decided, not yet built)

Three steps, in this order, because the wrong order is dangerous:

1. **Lock** — a full-screen overlay that dismisses the scam screen
2. **Stop** — end any active capture and zero the buffer
3. **Dial** — `tel:1930`

The lock comes first. If dialling opens the phone app *over* the scam screen and
the user comes back to an unchanged screen, nothing was achieved.

**Explicit non-goal:** the panic button cannot "kill known-scam sessions" on
Android without accessibility permissions that Part 1 §8 forbids. That sentence in
the original spec was not implementable under this project's own privacy rules —
which is another reason it should never have been marked ✅.

### Phase 2 result — ✅ COMPLETE

```
pytest tests/test_part1_phase2.py   → 21 passed
node --test tests/panic_family.test.js → 23 passed
pytest tests/ -q                    → 359 passed
node tests (both suites)            → 53 passed
```

**412 checks, 0 failures.**

Verified against a live server: `/app/panic.js` and `/app/family.js` both 200,
and the page loads them before `app.js`.

**Panic, traced end to end in a simulated tap:**

```
steps   : LOCK -> STOP_CAPTURE -> DIAL
mic off : true   buffer cleared: true   dialled: 1930
```

**Family mode on a `MODERATE` verdict:**

| | actionable | band |
|---|---|---|
| family off | false | MODERATE |
| family on | **true** | MODERATE *(unchanged)* |

And `LOW` stays **non-actionable** with family mode on — escalation makes the app
more cautious, never more accusatory.

### What Phase 2 built

| Task | Outcome |
|---|---|
| 2.1 Panic button | `citizen/app/panic.js` — lock → stop capture → dial, order enforced by test |
| 2.2 Family mode | `citizen/app/family.js` — stricter / louder / simpler, presentation only |
| 2.3 Storage | `localStorage` boolean only; no account, no sync, no server |
| 2.4 Voice tab languages | verified present from Phase 1 |

### Design decisions worth recording

1. **No confirmation dialog on panic.** In the situation this button exists for,
   "are you sure?" costs the seconds that matter. A single large Cancel is
   offered on the overlay instead.
2. **Every panic step is attempted even if an earlier one throws.** A failed
   overlay must not stop the call to 1930; a failed buffer-zero must not stop the
   overlay. Tested in both directions.
3. **The overlay is fully opaque.** If any of the scam screen showed through, the
   scammer's instructions would still be readable, which defeats the purpose.
   A test asserts `opacity` is absent from the overlay rule.
4. **Family mode is labelled on screen** ("· FAMILY MODE") so the user is never
   told the detector said something it did not.
5. **The panic button still cannot end the caller's session.** That needs Android
   accessibility permissions, which §8 forbids. The spec now says so explicitly.

### Tests that deliberately inverted

Two Phase 1 tests asserted the panic button was *partial* — that the spec must
**not** claim a screen lock:
- `test_panic_button_is_documented_as_partial`
- `test_helpline_link_exists_in_the_page` (checked for a bare `tel:` anchor)

Phase 2 made both assertions obsolete. Rather than deleting them, they were
rewritten to assert the *stronger* thing: a status row may only claim a behaviour
that has a module, an order guarantee and a passing test — all three are now
checked. A false assertion evolving into a true one is the system working.

### 2.2 Family mode design

- Stricter: a `MODERATE` band becomes actionable on screen rather than staying
  advisory
- Louder: larger type, slower transitions, no auto-dismiss
- Simpler: hides the severity slider on the report screen
- Stored only in `localStorage`; never sent anywhere

---

# PHASE 3 — HARDEN & SHIP ✅ COMPLETE

> Full plan and build log: [`01b_citizen_spine_phase3.md`](01b_citizen_spine_phase3.md)

**Goal:** survives hostile input, real sensors and a cold audit.

| # | Task |
|---|---|
| 3.1 | Fuzz the risk engine: NaN, missing keys, huge strings, Unicode confusables |
| 3.2 | Golden-file tests for all three languages (any copy change must be deliberate) |
| 3.3 | Offline behaviour: service worker serves the app with no network; report queues |
| 3.4 | Cold-audit checklist: every claim in `01_citizen_spine.md` traced to a test |
| 3.5 | Wire real sensors where available: notification-listener message capture, call-state detection |
| 3.6 | Accessibility pass: screen-reader labels, 48 px targets, contrast on all bands |
| 3.7 | Measured false-positive review of the report rail with real volunteers |

Phase 3 is where the spine stops being a demo and starts being something a
district hospital could hand to a patient.

---

## Status board

| Phase | Status | Tests |
|---|---|---|
| 1 — Truth & verification | ✅ **complete** | +40 (368 total) |
| 2 — Complete the spine | ✅ **complete** | +44 (412 total) |
| 3 — Harden & ship | ✅ **complete** | +196 (626 total) |

> Test counts are runner-reported, never aspirational.
