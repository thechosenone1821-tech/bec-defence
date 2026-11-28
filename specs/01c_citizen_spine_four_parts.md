> Historical provenance: the retired voice-scorer code was removed from executable paths. Active status lives in [docs/STATUS.md](../docs/STATUS.md); see the [retired code note](../archive/provenance/RETIRED.md). Real-world privacy efficacy remains UNMEASURED.

# CITIZEN SPINE — REBUILT IN FOUR PARTS

> **Why rebuild?** The spine went through three phases and is green, but an audit
> against its own definition of done found three things a phase-based plan hid:
>
> 1. The fusion core works and **no test would notice if its arithmetic changed**.
> 2. `assess()` returns **internal codes** (`LIKELY_SYNTHETIC`,
>    `"same pattern already reported"`) as `reasons` — the exact thing Phase 1
>    fixed for the message tab, still present here.
> 3. The spec's own status table still says **family mode "❌ not built"** when
>    Phase 2 built it.
>
> The four parts below are a **capability split**, not a sequence of bug fixes.
> Each part is independently ownable: one team member can take Part 2 and another
> Part 3 without touching the same files.

---

## The four parts

| Part | Name | Owns | Files |
|---|---|---|---|
| **1** | **Signal Fusion Core** | How signals become one score and one band. Deterministic, testable, no text. | `citizen/risk/*.py` |
| **2** | **Explanation Layer** | Turning a score into sentences a frightened person can act on, in three languages. | `citizen/voiceguard/i18n.py` |
| **3** | **Capture & Consent** | Getting audio safely, or not at all. | `voiceguard/capture.py`, `app/*capture*` |
| **4** | **Delivery & Offline** | Report rail, panic, family mode, offline queue, service worker. | `api.py`, `app/panic.js`, `queue.js`, `sw.js` |

### Why this split and not another

- **1 and 2 are separated by a hard boundary:** Part 1 must never contain an
  English word, Part 2 must never contain a weight. That boundary is what lets one
  person rewrite fraud copy without risking the scoring maths, and another retune
  weights without re-translating three languages.
- **3 is separate** because privacy is a different discipline from scoring, and
  its bugs are the ones that cannot be undone.
- **4 is the only part that touches the network**, so it is the only part where
  "did it send?" is a question. Everything else is pure.

---

# PART ONE — SIGNAL FUSION CORE

**Goal:** the scoring decision, isolated, declared, and impossible to change by
accident.

### What Part One must deliver

| # | Task |
|---|---|
| 1.1 | Extract fusion from `assess()` into a pure module with no presentation |
| 1.2 | Make every source a **declared rule** in one table, not an if-block |
| 1.3 | Make every result **auditable**: which rules fired, which did not, and why |
| 1.4 | Pin the arithmetic — a weight change must break a test, not a demo |
| 1.5 | Prove the monotonicity properties that make the score trustworthy |

### The properties Part One must hold

These are the invariants a fraud screen needs, and each becomes a test:

1. **Monotone** — adding evidence never lowers the score.
2. **Bounded** — the score is always in `[0, 1]`, whatever is thrown in.
3. **Order-independent** — the same signals in a different order give the same score.
4. **Total** — every input produces a result with a band and a reason; nothing raises.
5. **Conservative** — absence of evidence never produces a band above `LOW_CONFIDENCE`.
6. **Traceable** — every band names the rules that produced it.

---

## Execution log — Part One

*(written as it was done; corrections are recorded rather than silently applied)*
### 1.1 Extract fusion from `assess()` — done

`citizen/risk/fusion.py` is new and pure: no text, no language, no I/O, no
`print`. `evaluate(voice, message, campaign_linked, repeat_contacts, user_doubt)`
returns a plain dict. `citizen/risk/engine.py` is now a thin adapter: it calls
`fusion.evaluate()` and adds presentation, keeping every public key it had.
Nothing above the adapter changed shape, which is why the 555 pre-existing
tests still pass untouched.

The split is enforced by test, not by convention:
`test_fusion_module_contains_no_citizen_facing_sentences` and
`test_fusion_module_has_no_io` read the source of `fusion.py` and fail if a
word like `lang` or a call like `open(` appears in it.

### 1.2 Sources as a declared rule table — done

`RULES` is a dict of five named callables. `SOURCE_WEIGHTS` holds every
numeric weight. Nothing is buried in an if-block, so a weight is a value you
can read, diff, and pin. `test_each_rule_is_a_callable_in_the_table` fails if a
rule exists without a declared weight, and
`test_applied_weights_match_the_declared_table` fails if the table and the
arithmetic ever disagree.

### 1.3 Auditable results — done

Every result carries `signals` (what fired, with weight and detail),
`skipped` (what did not, **with a reason**), `weights_used`,
`sources_evaluated`, `sources_fired`, and `band_reason`. The skip reasons are
the useful part, and they distinguish *why* a source was silent rather than
collapsing everything to "no signal":

| Situation | Skip reason |
|---|---|
| No clip supplied at all | `no voice reading supplied` |
| Clip supplied, verdict unclear | `voice reading was INCONCLUSIVE — absence of evidence` |
| Campaign never checked | `no campaign linkage` |
| Source threw an exception | `rule error: TypeError` |

Those first four strings are copied from a live `evaluate()` call, not paraphrased.

### 1.4 Arithmetic pinned — done

Six weight values are asserted individually. Separately, four mutants were
injected into `fusion.py` and each had to break the suite: capping the score at
0.5 (**killed**), short-circuiting to the first signal (**killed**), reversing
the band table (**killed**), and dropping the single-weak-signal rule
(**killed**).

### 1.5 Monotonicity properties — done

All six invariants are executable. Two of them were only trusted after
mutation testing showed the first drafts could not fail — see below.

---

## What mutation testing found

The Part One tests passed on their first run. Tests that pass first time,
written by the same person who wrote the code, are worth exactly nothing until
you try to break them. So five deliberate bugs were injected into `fusion.py`
one at a time, each run in a subprocess against the real suite.

| Injected bug | Outcome |
|---|---|
| Cap the fused score at 0.5 | **survived**, then killed after a test was added |
| Short-circuit: fuse only the first signal | killed |
| Reverse the band table | killed |
| Drop the "one weak signal is not enough" rule | killed |
| Globally reorder the `RULES` dict | survived — *correctly* (see below) |

**Two real findings came out of this.**

**1. The band `LOW` is unreachable.** The input space is finite — five sources
with fixed weights — so the set of attainable scores can be enumerated
exactly, and it was: 72 input states, **72 distinct scores**. The cheapest
*corroborated* evidence is `user_doubt` (0.15) unioned with
`repeat_contact` (0.20), which fuses to **0.32**. `LOW`'s ceiling is **0.20**.
So no combination of evidence can ever land in `LOW`, and the ladder jumps
`LOW_CONFIDENCE` → `ELEVATED` with a whole rung missing. A citizen never sees
a mild warning; mild evidence either reads as "nothing" or as "elevated".

This is recorded as `test_every_declared_band_is_reachable`, marked
`xfail(strict=True)`. It documents the defect, and the moment someone retunes
the thresholds the strict marker turns red and forces the marker to be
removed rather than quietly forgotten.

The fix is a one-line change to `_BAND_TABLE`, and it was **verified before
being recommended**: ceilings of `0.40 / 0.60 / 0.80 / 1.01` make every band
reachable, and they do not downgrade any single-source verdict — a
`LIKELY_SYNTHETIC` voice alone still reads `HIGH` (0.65), a `CRITICAL` message
alone still reads `HIGH` (0.60). Only mild *corroborated* evidence gains a
rung. It was not applied here because it reclassifies citizen-facing severity,
and that is a decision for the owner, not a silent edit during a refactor.

**2. One of the six invariant tests was a tautology.** The order-freedom test
asserted that `evaluate(voice=..., campaign_linked=True)` equals
`evaluate(campaign_linked=True, voice=...)`. In CPython those build the
identical kwargs dict, so the assertion cannot fail on any implementation. It
looked like a property test and verified nothing.

It was replaced with the ordering the core actually depends on: the iteration
order of `RULES`. `test_shuffling_the_rule_table_cannot_change_verdicts`
monkeypatches every permutation of the rule table (120 of them) and requires
identical score, band, fired sources, and weight multiset. The original
tautology is retained under an honest name —
`test_kwarg_order_is_meaningless_and_not_worth_testing` — purely to record why
the obvious version is useless.

The final surviving mutant, globally reversing `RULES`, is **equivalent, not a
gap**: order-independence means the reversal must produce identical verdicts,
and it does. An equivalent mutant that survives confirms the property; it does
not weaken it.

**The general lesson.** "Bounded above" is not "able to reach the top". A
ceiling on the fused score satisfies `0 ≤ score ≤ 1` and would have kept every
other test green while making `CRITICAL` unreachable — a crisis tool failing in
the one direction that hurts most. `test_the_scale_is_reachable_not_just_bounded`
now pins the top of the scale from below, with the floor derived from
`_BAND_TABLE` rather than hard-coded, so it survives a retune.

### Result

| Check | Before Part One | After Part One |
|---|---|---|
| pytest | 555 passed | **655 passed, 1 xfailed** |
| node | 71 passed, 0 failed | 71 passed, 0 failed (untouched) |
| Part One tests | — | **100 passed + 1 documented defect** |

655 = 555 + 100. The pre-existing tests were not edited, so the +100 is
entirely new coverage and the old behaviour is intact.

The `1 xfailed` is the unreachable-`LOW` defect. It is not a failure being
hidden: `strict=True` means the suite fails the moment the code changes
underneath it, in either direction.

---

# PART TWO — EXPLANATION LAYER

**Goal:** one path from a verdict to a sentence. If a citizen can read a word on
screen, that word came from this file.

### What Part Two must deliver

| # | Task |
|---|---|
| 2.1 | Move band copy out of the risk engine: `engine.py` must contain no citizen-facing English |
| 2.2 | Localise the honesty label — `advisory` is English-only today and it is the one sentence that must never be lost in translation |
| 2.3 | Make the fallback audible: a missing translation must leave a trace, not fail silently forever |
| 2.4 | Every sentence must be renderable in all three languages from the catalogue alone |
| 2.5 | Copy invariants as tests: no codes, no raw scores, no accusations, no numbers we cannot measure |

### The properties Part Two must hold

1. **Total** — every band, verdict and reason code renders in en/hi/te.
2. **Code-free** — no citizen-facing string contains `_` or `UPPER_SNAKE` internal names.
3. **Honest** — no sentence claims accuracy, certainty or validation we do not have.
4. **Actionable** — any non-trivial verdict carries something the person can *do*.
5. **Single-pathed** — the only module that produces citizen sentences is `i18n.py`.

---

# PART THREE — CAPTURE & CONSENT

**Goal:** get audio safely, or not at all — and be able to prove which one
happened.

### What Part Three must deliver

| # | Task |
|---|---|
| 3.1 | Consent must be enforced where the audio actually arrives, not only in a class nobody calls |
| 3.2 | Zero retention must be *auditable*: `destroy()` must report on the buffer that really held the samples |
| 3.3 | Refusal must be a first-class state with a reason a UI can show, not a raised exception |
| 3.4 | Retention accounting must survive many screens and repeated destroys |

### The properties Part Three must hold

1. **Consent-first** — no sample is processed before consent, and the refusal is reported.
2. **Auditable** — `destroy()` reports the real buffer, and says so when it cannot.
3. **Bounded** — nothing larger than the documented window is ever accepted.
4. **Total** — a malformed request produces a refusal, never a 500 or a traceback.

---

# PART FOUR — DELIVERY & OFFLINE

**Goal:** the only part that touches the network, so the only part where "did it
send?" is a question. It must never answer that question wrongly.

### What Part Four must deliver

| # | Task |
|---|---|
| 4.1 | `flush` must not treat `Response`-like values as success — a 500 must not delete a report |
| 4.2 | Offline prediction must be a tested rule, not an inference from a missing error |
| 4.3 | The panic path must be proven independent of the network and of a full queue |
| 4.4 | The service worker must never serve a stale shell after a deploy |

### The properties Part Four must hold

1. **Never lies** — a report is reported sent only when the server accepted it.
2. **Loses nothing** — a failed flush keeps the backlog.
3. **Offline-first** — panic works with no network, no queue space and no server.
4. **No stale shell** — a version bump invalidates every old cache.

---

## Execution log — Part Two

### 2.1 Band copy leaves the risk engine — done

`_BAND_COPY` lived in `citizen/risk/engine.py`: five bands × three languages of
citizen-facing copy inside the module that is supposed to hold no English at
all. It moved to `i18n.render_band()`. `engine.py` now calls the catalogue and
holds no sentences of its own. A test greps `engine.py` for the removed strings
and fails if any of them come back.

### 2.2 The honesty label was English-only — **defect, fixed**

Measured before the fix:

```
en  advisory: Judgement-based weighting, not calibrated against real fraud ...
hi  advisory: Judgement-based weighting, not calibrated against real fraud ...
te  advisory: Judgement-based weighting, not calibrated against real fraud ...
```

A Hindi or Telugu reader got a Telugu headline and an English disclaimer, on the
sentence that says *this is an aid, not a verdict*. The disclaimer is the one
piece of copy that must survive translation, because it is the copy that stops
the app being trusted more than it deserves. Now in the catalogue as
`render_advisory()`, in three languages.

### 2.3 The fallback was silent — **defect, fixed**

`render_reason` fell back to English and said nothing. A missing Telugu string
was therefore invisible: the app kept working, kept looking finished, and served
English to a Telugu reader forever. The fallback is now *recorded* on the
result — `explanation["fallbacks"]` names the codes that had to borrow English —
so a coverage gap can be asserted to be empty rather than assumed.

### 2.4 The citizen view was incomplete — **defect, fixed**

`assess()` computed `band_reason` (Part One's explanation of *why* the band is
what it is: "a single weak signal is not enough without corroboration") and the
UI never showed it, because it is an English developer string. `render_band_reason()`
now turns the three possible shapes of it into a citizen sentence, so the most
useful sentence in the payload is no longer the one nobody can read.

---

## Execution log — Part Three

### 3.1 Consent was enforced in a class nothing calls — **defect, fixed**

`/retention` advertised `"consent_required": true`. `/screen_voice` never
checked it. `CaptureSession` does check, and nothing outside the tests
constructs one, so the guarantee lived only in the tests. The API now requires
an explicit `consent` field and refuses without one.

**This changes a public contract**, so it was done loudly rather than silently:
the refusal is a `403` carrying a `detail` shaped like a citizen explanation
(`title`, `action`, `lang`, `helpline`), so a client can show it instead of
parsing an error string. Every existing test that posted samples without consent
was updated to post `"consent": true` — 4 call sites — and the old behaviour is
now pinned as *forbidden* by a new test rather than deleted.

### 3.2 `destroy()` reported on a buffer that never held the samples — **defect, fixed**

Measured before the fix:

```
ingest() returned array: 128000 bytes, size 16000
ring zero_count after 5 screens: 0
destroy(): {'destroyed': True, 'zero_passes': 1, 'screens': 5}
```

`ingest()` never wrote to `self.ring`, so `zero_passes: 1` was a true statement
about an empty buffer and a false impression about the audio. The samples that
were screened were handed back to the caller and held nowhere this object could
reach. That is not a retention bug in the sense of "we kept too much": it is
worse in one way, because the accounting *claimed* a wipe.

`ingest()` now copies the window into the ring before returning, so `destroy()`
zeroes the memory that actually held it. The returned array is the caller's
working copy and is documented as such — this build cannot reach into a caller's
`numpy` array, and pretending otherwise would be the same lie in a new place.

### 3.3 Refusal is now a state, not just an exception — done

`screen_with_consent()` returns `{"accepted": bool, "reason": str, "explanation":
{...}}` for the refusal paths (no consent, no audio, oversized window) instead of
raising, because a UI that has to catch an exception to find out *why* it was
refused will show the wrong copy. `RetentionError` still exists for the class
API, so nothing that relied on it breaks.

---

## Execution log — Part Four

### 4.1 `flush` deleted reports on a 500 — **defect, fixed**

Measured before the fix:

```
all-fail flush: {"sent":0,"remaining":2}      correct
500 sent as success?: {"sent":1,"remaining":0}   WRONG — report deleted
```

`flush` treated any truthy return as success. The obvious call site —
`flush(store, e => fetch(...))` — passes a `Response`, which is truthy even when
the status is 500. The report was removed from the queue and reported as sent.

The existing call site in `app.js` was careful (`await api(...)`, which throws on
`!r.ok`), so this was a loaded gun rather than a fired one. It has been made
impossible to fire: a `Response`-like return is now read by its `status`, and
only 2xx counts. The boolean contract that 8 existing tests rely on is
unchanged, so nothing was rewritten to accommodate the fix.

### 4.2 Offline was inferred, not decided — done

`api()` threw on a 500 and the caller read *any* throw as "offline", so a server
rejection and a dead network produced the same citizen-facing sentence: "saved
on this phone". A server that rejected the report as invalid is not the same
thing as a phone with no signal, and only one of them is worth retrying.

There is now one classification function, `classifySend()`, with four outcomes —
`sent`, `retry` (network), `rejected` (a 4xx that will never succeed) and
`unknown`. Only `retry` keeps the entry. `rejected` stops the flush and keeps the
entry *visible* rather than silently dropping it, because a report the server
refuses is a bug the user should not pay for.

### 4.3 Panic was never tested against a full queue or a dead network — done

The panic path calls no network at all, which was true and unproven. Tests now
assert the property directly: `runPanic` issues no `fetch`, resolves under a
`fetch` that throws, and completes with a queue at its 50-entry cap. The panic
button is the one control that must work when everything else does not, so
"it probably does not touch the network" is not good enough.

### 4.4 The worker could serve a shell from a previous deploy — **defect, fixed**

`activate` deleted every cache except the current one, which is correct. But
`install` called `skipWaiting()` and `activate` called `clients.claim()`, so a
new worker took over *without a reload*: an already-open page kept running the
old scripts against a cache the new worker had just deleted. The page would then
fetch assets that were no longer cached, mid-session, while offline.

`clients.claim()` is now gated on the page having no controller (`navigator
.serviceWorker.controller == null`), so a first install claims immediately and an
update waits for the next navigation — the standard, boring, correct behaviour.
`CACHE` was bumped as part of this change, which is the mechanism the file
documents for invalidating a stale shell.

---

## Part Two to Four — result

| Check | Before 2/3/4 | After |
|---|---|---|
| pytest | 655 passed, 1 xfailed | **732 passed, 1 xfailed** |
| node | 71 passed | **90 passed** |
| live assets | 10/10 200 | **11/11 200** (send-state.js added) |
| live consent gate | never enforced | **403 without, 200 with** |

732 = 655 + 77 new (33 Part Two + 44 Part Three). Node 90 = 71 + 19 (Part Four
is JavaScript). `send-state.js` is new and is both loaded by `index.html` and
listed in the service-worker asset set — the two mechanisms that must agree, and
the exact pair that drifted in Phase 3.

### Defects found and fixed

| # | Part | Defect | Severity |
|---|---|---|---|
| 1 | 2 | `advisory` (the honesty label) was English-only in all three languages | high — it is the sentence that stops over-trust |
| 2 | 2 | `engine.py` carried `_BAND_COPY`: citizen copy inside the scoring adapter | medium — boundary erosion |
| 3 | 2 | The English fallback was silent, so a coverage gap was invisible | medium |
| 4 | 2 | `band_reason` reached the UI as English developer text, so the most useful sentence was shown to nobody | medium |
| 5 | 3 | Consent advertised (`"consent_required": true`) and never enforced in the API | **high — a privacy claim that was false** |
| 6 | 3 | `destroy()` reported a wipe of a buffer that never held the samples | **high — a retention claim that was false** |
| 7 | 4 | `flush` deleted a report on a 500 if the sender returned a `Response` | **high — silent loss of a fraud report** |
| 8 | 4 | A 4xx rejection and a dead network produced the same copy ("saved on this phone") | high — a promise retrying cannot keep |
| 9 | 4 | The worker claimed an already-open page, deleting the caches it was using | medium |
| 10 | 4 | **Found live, not by a test:** a report the server accepted but never forwarded was titled "Report sent" | **high — the exact lie Part Four exists to prevent** |

Defect 10 is the one worth reading. Every unit test passed. It surfaced only from
running the app and reading the JSON a citizen would actually see: `status:
"REPORTED"`, `forwarded: {"forwarded": false, "reason": "RAKSHA_BUS_URL not
configured"}`, and `title: "Report sent"`. The API had chosen its copy from
*local* forwarding success. A report that reached nobody was described as sent.

It now has its own state — "Received, but not passed on … Call 1930 so a person
hears it now" — and its own regression test, which was proven by reverting the
fix (2 failures) and re-applying it (5 passes). The test also pins the opposite
case, so the fix cannot degrade into "never say sent", which would make a
working rail look broken.

### Where I was wrong

The Part Three gate I first wrote rejected any payload containing a non-finite
sample. That would have turned a real clip with one `NaN` into "no audio",
denying a citizen the verdict they came for — reintroducing a fixed bug in a new
place. A pre-existing test caught it. The gate now decides **consent and size
only**, and data quality stays with the boundary that already handled it.

The same pass found my refusal codes collapsing 403/413/422 into one 403. Three
different problems, three different next steps; the codes were restored.

### Mutation testing, Parts Two to Four

14 mutants injected, 14 killed. Each was a plausible mistake, not a strawman.
(One injection failed to apply on the first attempt because the string I was
targeting did not match the file; it was retried against the real text and
killed. A mutant that never applied is not a passing mutant, so it is not
counted.)

| Mutant | Killed by |
|---|---|
| Stop recording translation fallbacks | Part Two fallback tests |
| De-translate the honesty label (te → English) | 5 Part Two tests |
| Never render band explanations | Part Two traceability |
| Unknown band renders as "all clear" | Part Two safe-fallback |
| Remove the consent gate from the API | Part Three consent tests |
| `ingest` stops filling the ring | Part Three retention accounting |
| `if not consented` (truthy junk accepted) | Part Three consent-string test |
| No size ceiling at the gate | Part Three bounded tests |
| Treat every `Response` as success | Part Four never-lies |
| Never classify a 4xx as rejected | Part Four classifySend |
| 429 treated as give-up | Part Four retryable-4xx |
| Offline counted as sent | Part Four classifySend |
| Claim an open page mid-session | Part Four stale-shell |
| Drop `send-state.js` from the offline cache | Part Four asset/cache parity |

The last one is the Phase 3 panic-button bug in its modern form, and it is the
reason the asset test is derived from `index.html` rather than maintained by hand.

