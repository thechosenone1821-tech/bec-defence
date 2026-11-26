# RAKSHA — Consolidated Build State

> **What this file is.** One page describing everything actually built, what is
> half-built, and what does not exist. Every figure here was produced by running
> something today. Nothing is carried forward from a plan, a slide, or an earlier
> version of this document.
>
> **Verified:** 2026-11-25 · branch `arena/f36c9305-bec-defence` @ `46f0707`
>
> **Scope:** the whole app. **MessageGuard is deliberately excluded** from this
> consolidation — it is a small rules-based scorer with a 20-message fixture set,
> and its state is unchanged since the original build.

---

## 1. Where the work actually stands

| | |
|---|---|
| Python tests | **555 passed**, 0 failed |
| Browser tests (Node) | **71 passed**, 0 failed |
| **Total** | **626 checks, 0 failures** |
| Source under test | ~8,300 lines (`citizen/`, `spine/`, `sentinel/`, `raavan/`, `evals/`) |
| Running services | 2 (Citizen app on `:8095`, Spine bus on `:8090`) |

The suite is green. That is necessary and not sufficient — §5 lists what no test
can currently prove.

---

## 2. What is built and working

### 2.1 Citizen app — complete through three phases

Verified live against a running server today.

**VoiceGuard (Maya) — synthetic-speech screening**

| | |
|---|---|
| Model | `maya-lr-v1`, numpy logistic regression, 2 features |
| Artefact | 732 bytes, `sha256[0:16] = 8b140095e5f8599e` |
| Gate flags | `TRAINED_MODEL_PRESENT=True`, `MEASURED_ON_REAL_SPEECH=**False**` |
| `may_claim_clone_detection()` | **`False`** |

Live verdicts observed in this session:

```
synthetic   LIKELY_SYNTHETIC   p=0.978   MODEL_FLAGGED_SYNTHETIC
bona fide   INCONCLUSIVE       p=0.547   MODEL_FOUND_NOTHING
silence     SILENT             p=—       SILENT_AUDIO
```

Silence correctly **never reaches the model** — that was a real bug (digital zero
scored P(spoof)=0.94 and accused a recording containing no voice) and it is now
gated.

**Citizen Risk Engine**

- Bounded noisy-OR fusion over five signals with declared, readable weights
- **No `SAFE` verdict exists anywhere in the codebase** — asserted by a repo-wide scan
- Corroboration rule: a band above `LOW_CONFIDENCE` needs a standalone source or
  two contributing signals
- Junk input cannot fabricate evidence: `campaign_linked="nope"` yields no signal

**Multilingual (en / hi / te)**

- 308 strings across three languages, committed to a golden file
- Tests assert the Hindi is Devanagari and the Telugu is Telugu script — pasted
  English would pass a naive parity check and fail a real citizen

**Capture, privacy, safety**

- 3-second ring buffer, consent-gated, zeroed on stop / blur / hide / teardown
- `retention_policy()`: `storage: memory only`, `uploads: never`
- Panic: **`LOCK → STOP_CAPTURE → DIAL`** — order enforced positionally by test
- Family mode: `MODERATE` becomes actionable; **`LOW` stays non-actionable**
- Offline queue: capped at 50, stores only `category / severity / lang / case_id`,
  never claims "sent"

**Service worker** — caches 11/11 assets (verified by fetching each one). It
previously cached 4 of 7, which meant **offline the panic button did nothing**.

### 2.2 Company platform — engine built, presentation absent

| Component | State |
|---|---|
| Spine bus (ingest → sanitise → graph → broadcast) | ✅ running |
| Attack graph, 10-min window, typed edges | ✅ |
| Campaign identity (entity overlap + temporal kernel) | ⚠️ partial |
| Evidence ledger (SHA-256 chain + HMAC anchor) | ✅ |
| Governor (allowlist, crown-jewel, budgets, FIDO2) | ✅ |
| Containment planner (exhaustive min-disruption cut) | ✅ |
| Commander (local SLM with deterministic fallback) | ⚠️ fallback only |
| Executor | ⚠️ dry-run by construction |
| **8 detection organs** (BEC spectral, cookie turbulence, Bragg FFT, Hessian-Lyapunov, Page-Curve trap, Landauer audit, Hashimoto percolation, MutS repair) | ✅ all 8 coded |
| RAAVAN kill chain | ✅ replays 5 stages as signed telemetry |
| **SOC console / dashboard** | ❌ **does not exist** |

Spine endpoints live: `/api/health`, `/api/state`, `/api/ingest`,
`/api/containment`, `/api/orchestrate`, `WS /ws/telemetry`.

---

## 3. Test inventory

| Suite | Tests |
|---|---|
| `test_part1_phase3.py` | 196 |
| `test_maya_phase1.py` | 61 |
| `test_maya_phase4.py` | 55 |
| `test_maya_phase3.py` | 47 |
| `test_part1_citizen_spine.py` | 40 |
| `test_maya_phase5.py` | 38 |
| `test_maya_phase2.py` | 30 |
| `test_part1_phase2.py` | 21 |
| platform tests (fortress, organs, governor, ledger, RAAVAN, …) | 67 |
| **pytest total** | **555** |
| `maya_capture.test.js` | 30 |
| `panic_family.test.js` | 23 |
| `queue.test.js` | 18 |
| **node total** | **71** |

---

## 4. Bugs this build found and fixed

Recorded because most were invisible to a passing suite.

| # | Bug | Why tests missed it |
|---|---|---|
| 1 | Silence scored P(spoof)=0.94 → accused a silent recording of being AI | nothing asserted silence stays out of the model's domain |
| 2 | Two probability paths (calibrated vs raw) disagreed about the same clip | each tested in isolation |
| 3 | Threshold search returned the *least* sensitive qualifying threshold (recall 78%→6%) | EER was unchanged, so the headline metric looked fine |
| 4 | Served page could not load its own assets | unit tests never fetched the page's assets |
| 5 | Service worker cached 4 of 7 assets → **panic button dead offline** | nothing compared the cache list to the page |
| 6 | `campaign_linked="nope"` produced band **HIGH** | a type error producing an *accusation* — nothing looks wrong in the UI |
| 7 | `score_voice(["a"])` raised despite a never-raise contract | the cast sat above its own guard |
| 8 | Panic button was documented as locking the screen when it was a `tel:` link | the spec was never checked against the code |
| 9 | Message tab printed a raw score to a citizen | violated the spine's own rule |
| 10 | Empty-message case rendered *"This clip does not give a clear answer"* | voice wording leaking onto a text screen |

Bug 6 is the one to remember: **not a crash — an accusation produced from a type
error**, and nothing in the interface would have looked wrong.

---

## 5. What no test can currently prove

This is the honest part, and it is the part that decides what this is worth.

| Gap | Consequence |
|---|---|
| **No real recorded speech** | The voice model has never seen a human voice. Every accuracy figure is synthetic-corpus only. |
| **No neural clone** | No modern TTS in the corpus. A good clone is expected to pass as `INCONCLUSIVE`. |
| **Telephony is simulated** | Recall falls 72% → **39%** on narrowband audio. Real codecs (G.729/AMR/Opus) are not tested at all. |
| **No real telemetry** | Zero organs have seen captured attack traffic. Thresholds are physically motivated, not validated. |
| **Nothing executes** | Every action is dry-run. "We blocked it" always means "we would have". |
| **Commander is a rule table** | No local model is running; the "AI commander" demos through its fallback. |
| **No console UI** | Everything the company side does is visible only through `curl`. |
| **Per-organ detection rates** | "8 organs" is a count, not a measurement. No false-positive characterisation exists. |

---

## 6. The seven-part split and its true status

| Part | What it is | Status |
|---|---|---|
| **1 · Citizen spine** | Risk fusion, i18n, capture, report rail, panic, family mode | ✅ **100%** — all 3 phases, +257 tests |
| **2 · VoiceGuard** | Synthetic-speech screening | 65% — real pipeline, fake data |
| **3 · MessageGuard** | Scam-script detection | *excluded from this consolidation* |
| **4 · Detection rings** | The 8 shield organs | 70% — 8/8 coded, 0 fed real traffic |
| **5 · Response & governance** | Planner, Governor, commander | 75% — strongest part; no live model, dry-run |
| **6 · Console & red-team** | SOC UI, RAAVAN, measurement | **30% — no UI at all** |
| **7 · Shared spine** | Bus, graph, ledger, safety core | 85% — campaign fusion is the seam |

**Overall: ~72%** of a judged demo. The engine is far ahead of the presentation.

---

## 7. What requires model training

Only three things, and only one is on the critical path:

| Thing | Part | Blocks |
|---|---|---|
| **Voice model on real speech + real clones** (8–10k clips, Indian-accented) | 2 | any accuracy claim; the word "clone" |
| On-device quantisation (ONNX INT8) | 2 | shipping to a phone |
| Message classifier on a real corpus | 3 | excluded here |

Everything in Parts 4, 5, 6 and 7 is **deterministic mathematics by design** —
that is the safety argument, not a shortcut. Part 5's commander needs a model
*running*, not *training*.

---

## 8. Seven documents, one consistent story

| File | Contains |
|---|---|
| [`specs/00_INDEX.md`](specs/00_INDEX.md) | The 7-part split and status board |
| [`specs/01_citizen_spine.md`](specs/01_citizen_spine.md) | Part 1 spec + Definition of Done |
| [`specs/01a_citizen_spine_roadmap.md`](specs/01a_citizen_spine_roadmap.md) | Part 1, 3-phase roadmap + build log |
| [`specs/01b_citizen_spine_phase3.md`](specs/01b_citizen_spine_phase3.md) | Phase 3 hardening log |
| [`specs/02_citizen_voiceguard.md`](specs/02_citizen_voiceguard.md) | Part 2 spec, measured results |
| [`specs/04–07`](specs/) | Parts 4, 5, 6, 7 specs |
| `raksha/EVALS.md` | Every measured number with its condition |
| `raksha-code/citizen/voiceguard/MODEL_CARD.md` | Model limitations |

---

## 9. The three rules that hold everywhere

1. **The AI proposes, the Governor disposes.** No part may create a path around
   the deterministic safety gate.
2. **No unverified number.** A figure appears only if a harness in this repo
   produced it, carrying its condition (fixture / synthetic / measured).
3. **Nothing found is not nothing wrong.** No part may emit a reassuring verdict
   from an absence of evidence.

---

## 10. Highest-value next work

| Rank | Task | Why |
|---|---|---|
| 1 | **Build the SOC console (Part 6)** | ~400–600 lines turns ~80% of a finished engine into something a judge can watch. Currently demos via `curl`. |
| 2 | **Real voice corpus (Part 2)** | Unlocks every accuracy claim and the word "clone". Needs data collection, not coding. |
| 3 | Per-organ fixture corpora | Turns "8 organs" into 8 measured detection rates. |

> Consolidation note: this document supersedes the status sections of any earlier
> file. Where they disagree, this one was produced by execution today.
