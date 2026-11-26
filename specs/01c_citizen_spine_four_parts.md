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
