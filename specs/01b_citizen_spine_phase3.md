# PART 1 — PHASE 3 · HARDEN & SHIP ✅ COMPLETE

> **This file is the Phase 3 build plan and build log.** Phase 3 is where the
> spine stops being a demo and becomes something a district hospital could hand
> to a patient.
>
> Parent: [`01_citizen_spine.md`](01_citizen_spine.md) ·
> Roadmap: [`01a_citizen_spine_roadmap.md`](01a_citizen_spine_roadmap.md)
> **Team:** 2 people. **Depends on:** Phases 1–2 (both complete).

---

## The one-sentence goal

Phases 1 and 2 made the spine **true and complete**. Phase 3 makes it **survive**:
hostile input, a cold audit, a phone with no network, and a person using a screen
reader.

---

## Scope

| # | Task | Why it matters |
|---|---|---|
| 3.1 | **Offline correctness** — the service worker caches what the app actually needs | found broken: 4 of 7 assets missing |
| 3.2 | **Fuzz the risk engine** — NaN, missing keys, huge strings, Unicode confusables | a crash at the wrong moment is a missed warning |
| 3.3 | **Golden-file copy tests** for all three languages | any wording change must be deliberate |
| 3.4 | **Accessibility pass** — labels, targets, contrast, focus | elders are the primary user |
| 3.5 | **Cold audit** — every claim traced to a test, mechanically | the spine's whole value is that claims are checkable |
| 3.6 | **Offline report queue** — a report made with no signal is not lost | the network is worst exactly when fraud happens |

---

## Execution log — Phase 3

### 3.1 Offline correctness — found broken before the plan was written

The service worker's `ASSETS` list was written in Phase 2 of the *original* build
and never updated as modules were added:

```
cached : app.js, index.html, manifest.json, styles.css
needed : + panic.js, family.js, maya-capture.js, maya-capture-worklet.js
MISSING: 4 of 7
```

**The consequence is worse than a missing icon.** With no network:

- `panic.js` fails to load ⇒ **the panic button does nothing at all.** The safety
  feature silently degrades to a dead control on the one screen where it matters.
- `maya-capture.js` fails ⇒ the voice tab reports "microphone not available" on a
  phone that has one — the exact false message Phase 5 already fixed once.
- `family.js` fails ⇒ family mode resets to off for an elder mid-session.

A cache list that drifts from the page is a recurring bug class, so the fix is not
"add four strings". It is a **test that derives the asset list from `index.html`**
and fails when the cache falls behind. Manual lists drift; derived ones do not.

### 3.2 Fuzzing

The risk engine and the two scorers receive untrusted input from a phone that
may be offline, mid-update, or running a stale payload. The contract is: **never
raise, always return a verdict with a reason.** A fuzz test asserts that across
hundreds of malformed inputs, and separately asserts that
`json.dumps(..., allow_nan=False)` succeeds on every result — because a NaN in a
response is a crash at the boundary, which the Phase-5 work already hit once.

### 3.3 Golden files

Eighteen strings per language × 3 languages, plus every verdict headline and
action. The point is not to freeze copy forever; it is that **changing a scam
warning must be a deliberate, reviewable diff**, not an accident of a refactor.
A test that regenerates the file on mismatch would defeat this, so the golden file
is committed and compared exactly.

### 3.4 Accessibility

Screen-reader labels on every control, 48 px minimum targets, focus moved to
Cancel when the panic overlay opens, and contrast checked on all four verdict
bands. Colour-only differentiation was already fixed in the voiceguard work;
this pass covers the rest of the app.

### 3.5 Cold audit

A script walks `01_citizen_spine.md`, extracts every status claim, and checks each
one resolves to a test that exists and passes. The output is a table a stranger
can read. **This is the deliverable that makes the other five phases checkable by
someone who does not trust us.**

### 3.6 Offline report queue

A report queued with no signal must not be lost and must not be silently claimed
as sent. The existing copy already distinguishes "sent" from "saved on this
phone", so the queue is what makes that second sentence true.


---

## Phase 3 result — ✅ COMPLETE

```
pytest tests/test_part1_phase3.py   → 196 passed
node --test tests/queue.test.js     → 18 passed
pytest tests/ -q                    → 555 passed
node (all three suites)             → 71 passed
```

**626 checks, 0 failures.**

### Live verification

Every asset the service worker intends to cache was fetched from a running
server: **11/11 returned 200**, so `install` would succeed and the app opens with
no network.

The offline queue was exercised end to end against the live API:

```
queued while offline : 3
content leaked?      : false
flush result         : {sent: 3, remaining: 0}
server statuses      : 200, 200, 200
queue after flush    : 0
```

A report containing an extra `text` field was queued; the field never reached
storage, was never sent, and all three reports were accepted on reconnect.

### Bugs found in Phase 3

| # | Bug | Why it mattered |
|---|---|---|
| 1 | **Service worker cached 4 of 7 assets** | Offline, `panic.js` never loads ⇒ **the panic button does nothing**. The safety feature silently dies on the one screen where it matters. |
| 2 | `score_voice(["a"])` **raised** despite a documented never-raise contract | The array cast sat above the try/except that was supposed to protect it. An API crash at the moment of a warning. |
| 3 | `repeat_contacts="abc"` → **HTTP 500** | A half-formed payload from a phone mid-update could take the endpoint down. |
| 4 | `campaign_linked="nope"` → band **HIGH** | A non-empty string is truthy, so junk added the full 0.45 campaign weight and escalated a clean assessment on evidence that did not exist. |
| 5 | Nav tabs and report chips had **no accessible names** | The primary audience is elders, many using screen readers. |
| 6 | Three reason codes had **no test at all** | Found by the cold audit, which is the point of the cold audit. |

Bug 4 is the instructive one: it was not a crash, it was **an accusation produced
from a type error**. Nothing in the UI would have looked wrong.

### What the cold audit taught

The audit initially excluded its own test file to avoid self-reference. Then the
fixes for the audit were written *into* that file — so the audit could no longer
see its own remediation. That is a general trap with self-checking scripts:
**exclude yourself and you cannot verify your own effect.** Fixed by scanning
every test file.

### Task status

| # | Task | Outcome |
|---|---|---|
| 3.1 | Offline correctness | ✅ derived-asset test + version bump + stale-cache purge |
| 3.2 | Fuzzing | ✅ 3 crashes and 1 false-accusation path fixed |
| 3.3 | Golden files | ✅ 308 strings × 3 languages, committed and compared exactly |
| 3.4 | Accessibility | ✅ labels, targets, live regions, non-colour bands |
| 3.5 | Cold audit | ✅ every reason code resolves to a test |
| 3.6 | Offline report queue | ✅ bounded, content-free, never claims "sent" |

### Phase 3 is complete. Part 1 is complete.
