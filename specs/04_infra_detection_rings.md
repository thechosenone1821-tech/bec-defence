# PART 4 — INFRA SPINE: SENTINEL DETECTION RINGS
## (the 8 shield organs — Rings 1–4)

> **What this is.** The company-side detection layer. Eight independent "organs"
> watch perimeter, AI agents, endpoints and the network fabric, and emit
> **signed** events into the shared spine.
>
> **Team size.** 4 people — two organs each. **Depends on:** Part 7 (bus, verify).
> **Can be built in parallel?** Yes. The eight organs share only the `BaseOrgan`
> contract.

---

## 1. The four rings

The rings are a defence-in-depth story, not a sequence. Each ring assumes the
previous one failed.

| Ring | Watches | Assumes already breached |
|---|---|---|
| **1 — Perimeter & Identity** | entry, sessions, MFA | — |
| **2 — Corporate AI & Agents** | what the company's AI is told | someone got in |
| **3 — Endpoint & Silicon** | what runs on the host | malware is running |
| **4 — Network & Healing** | how far it spreads | malware is moving |

---

## 2. The eight organs

### Ring 1 — Perimeter & Identity

**Organ 1 · BEC Spectral Traffic Projector** ✅ built
Maps active sessions into a matrix and takes its leading singular values. A
scripted botnet condenses into a rank-1 structure; humans spread out.
`R = σ₁² / Σσᵢ²`, threshold 0.72. *Mean-centred, deliberately not z-scored* —
per-feature scaling would erase the variance concentration that *is* the signal.

**Organ 2 · Fluid Boundary-Layer Cookie Killer** ✅ built
Models a user's scroll/cursor/inertia cadence as laminar flow. A rolling
behavioural Reynolds number separates laminar humans from turbulent replayed
cookies. Threshold 2300 — the pipe-flow constant, kept because the physics
analogy should read honestly rather than be tuned to look good.

### Ring 2 — Corporate AI & Agents

**Organ 3 · Bragg Crystallography Input Firewall** ✅ built
Two sub-millisecond gates on untrusted text before it reaches an agent's tool
loop: an FFT over the token stream to find the periodic peaks created by repeated
adversarial suffixes, plus the Fiedler eigenvalue of the token graph (injections
fracture connectivity between system prompt and document).

**Organ 4 · Hessian-Curvature Lyapunov Guardrail** ✅ built
Estimates directional curvature along the activation trajectory. Aligned
inference sits in a flat valley; jailbreaks push onto sharp cliffs. A restoring
vector nudges the trajectory back.

### Ring 3 — Endpoint & Silicon

**Organ 5 · Page-Curve 4 KB Ransomware Trap** ✅ built
Honey-block pairs woven into high-value directories, with an XOR parity
invariant per 4 KB chunk. Any unauthorised cipher pass breaks the invariant on its
**first** write and kills the offending process. Catches intermittent and
polymorphic encryptors that a file-extension heuristic misses.

**Organ 6 · Landauer Thermodynamic Spyware Auditor** ✅ built
Single-bit dissipation is below thermal noise, so this audits *macroscopic*
telemetry instead: predicts package power from instruction rate and die
temperature, and flags unexplained residuals — covert threads stay visible even
when every userspace hook is blinded.

### Ring 4 — Network & Healing

**Organ 7 · Hashimoto/Bethe Percolation Switch** ✅ built
Non-backtracking spectral radius as the cascade criterion. **Documented
deviation:** the classical result `ρ(B) < 1` is asymptotic. On *any* finite graph
containing one cycle, `ρ(B) ≥ 1`. An un-cuttable crown-jewel triangle therefore
pins it at exactly 1.0 no matter what the AI proposes — which is precisely
what a hospital wants. The 0.90 target is treated as an aspiration, never
falsified.

**Organ 8 · MutS/MutL Mismatch-Repair Runtime** ✅ built
Modelled on DNA mismatch repair: services register integrity signatures, and a
repeated exploit is "repaired" so the second attempt fails.

---

## 3. What every organ must do

Contributing an organ means honouring this contract — it is short and enforced.

| Rule | Why |
|---|---|
| Inherit `BaseOrgan`, emit **signed** telemetry | unsigned events are inert in the spine |
| Never perform the disruptive action itself — register an RPC and let the Governor gate it | the organ proposes, the Governor disposes |
| Return a **reason**, never only a score | a SOC analyst needs to know why |
| Be deterministic | a demo that differs each run is not a demo |
| Label fixture-measured numbers as fixtures | never quote them as production SLOs |
| Fail closed on malformed input | an organ that crashes must not silently pass traffic |

---

## 4. Honest status

| | |
|---|---|
| Organs implemented | **8 of 8** |
| Organs tested | 8, but only **5 test files / ~20 tests** cover all of them |
| Organs receiving real data | **0** |
| Organs actuating anything real | **0** — dry-run by construction |

**The gap is not code, it is evidence.** Each organ has real mathematics and a
plausible story, but none has been run against captured attack traffic. The
thresholds (0.72, 2300, 0.90) are physically motivated, not empirically validated.
Anyone continuing this work should say so before showing a slide.

---

## 5. Build order

1. `BaseOrgan` contract + signing (Part 7 owns this)
2. One organ end-to-end through the bus — Organ 1 is simplest
3. The remaining seven, two per person
4. **Fixture replay corpus per organ** ← current gap
5. Threshold calibration against captured traffic *(post-hackathon)*

---

## 6. Definition of done

**Corrected 2026-11-23 (Phase 1).** Three of these boxes were ticked before
anything tested them; the audit found them either false or unprovable. Each box
now names the test that earns it, or the phase that will.

| | Item | Status | Earned by |
|---|---|---|---|
| [x] | All 8 organs emit **signed** events | ✅ **true as of Phase 1** | `test_a_fresh_event_is_sealed` (×8). Before Phase 1 this was false: `emit()` returned 8 keys and no signature, and events were signed only in transit by `bus.ingest_trusted()`. |
| [x] | All 8 expose Governor-gated RPCs rather than acting directly | ✅ true with one caveat | `test_every_organ_registers_at_least_one_governor_gated_rpc` (×8). Caveat: `page_curve_trap` *can* call `os.kill` behind `allow_real_kill`, which defaults to False — now pinned by `test_no_organ_kills_a_process_by_default`. |
| [x] | All 8 are deterministic | ✅ **now tested** | `test_emit_is_deterministic` (×8) + `test_organs_produce_stable_verdicts_on_identical_input`. Before Phase 1 nothing checked this. |
| [x] | Every event carries a **reason**, not only a score | ✅ **true as of Phase 1** | `test_every_event_carries_a_reason` (×8). §3 required it; no event had a `reason` field. |
| [x] | Every organ **fails closed** on malformed input | ✅ **true as of Phase 1** | `test_emit_never_raises_on_a_bad_severity` (×8). Before Phase 1, `emit(nan)` became severity **1.0** and `emit(None)` raised. |
| [ ] | Each organ has a fixture corpus and a published detection rate | ⬜ Phase 4 | — |
| [ ] | Each organ's threshold is calibrated against real traffic | ⬜ Phase 5 | — |
| [ ] | False-positive behaviour under normal load is characterised | ⬜ Phase 6 | — |

**The honest summary of §4 needs no apology but does need one correction.** It
said "5 test files / ~20 tests cover all of them". Measured: **13 tests in 4
files, and three organs — Cookie, Landauer, MutS — had none at all.** §4's
sentence "organs tested: 8" was wrong. It is true now: 278 tests hold all eight
to a single conformance suite.

---

## 7. What this part does not do

- It does not decide anything. Detection only; Part 5 decides.
- It does not touch a real host or a real network.
- It does not have a UI. Part 6 owns the console.

---

# PHASE ROADMAP — SEVEN PHASES

> **Why seven, not five.** §5 above lists a build order that ends at "calibrate
> against captured traffic". That is a five-phase plan for a system whose real
> problem is not the maths. An audit of the eight organs found the roadmap
> stopped exactly where the evidence should start, and the checklist in §6
> claimed things the code does not do.
>
> The seven phases below keep the build order intact and put the missing
> guarantees *first*, because a contract that is wrong is cheap to fix now and
> expensive after 8 organs and 4 people depend on it.

## What the audit found (measured, 2026-11-23)

Run against `f701bfe`, before any Phase 1 work:

| Claim in §4/§6 | Measured |
|---|---|
| "8, but only 5 test files / ~20 tests cover all of them" | **3 organs have no test at all**: `CookieFluidTurbulence`, `LandauerThermalAudit`, `MutsEbpfRepair`. 4 files reference organs; 13 organ tests exist. |
| "[x] All 8 organs emit **signed** events" | `BaseOrgan.emit()` produces **8 keys and no `signature`**. Signing happens later in `bus.ingest_trusted()`. True only if every event travels through the bus — which the organ cannot guarantee and does not check. |
| "[x] … rather than acting directly" | `page_curve_trap.py:120` calls **`os.kill(pid, 9)`**, gated by `allow_real_kill` and off by default. The spirit holds; the letter of "[x]" does not. |
| "Fail closed on malformed input" | `emit(severity=float('nan'))` is **accepted and becomes `1.0`** — a NaN reads as maximum severity. `severity=None` raises. Neither is failing closed. |
| "Return a reason, never only a score" | Not verified. No test asserts a `reason` field exists on any verdict. |
| "Be deterministic" | Not verified. No test asserts two identical runs agree. |
| "Label fixture-measured numbers as fixtures" | No fixture corpus exists at all, so none are labelled. |

None of these is a catastrophe. Every one of them is the kind of thing a
hackathon demo survives and a pilot does not.

## The seven phases

| # | Phase | Deliverable | Why here |
|---|---|---|---|
| **1** | **Contract truth** | `BaseOrgan` fails closed, always emits a reason, and signs at the source. 3 untested organs get tests. Every §6 checkbox is either made true or has its `[x]` removed. | Nothing else can be trusted until the shared contract means what it says. Cheap now, expensive after 8 organs depend on it. |
| **2** | **One organ, end to end** | Organ 1 through the real bus → sanitizer → Commander, with a signed event and a Governor-gated RPC round trip. | Proves the seam exists before seven more organs lean on it. §5 step 2. |
| **3** | **The remaining seven, in ring order** | Rings 1→4, two per person. Each organ gets a contract-conformance suite as it lands. | §5 step 3. Ring order matters: Ring 1 assumes nothing was breached. |
| **4** | **Fixture replay corpus** | A labelled corpus per organ (attack + benign), a committed fixture loader, and a **published detection rate and false-positive rate** per organ. | §5 step 4 — the current gap. Numbers stop being adjectives. |
| **5** | **Calibration against captured traffic** | Real traffic, not fixtures. Thresholds (0.72, 2300, 0.90) either earn their values or are replaced. | §5 step 5. Post-hackathon; needs data that does not exist yet. |
| **6** | **Load, fatigue and drift** | False-positive behaviour under normal load, alert fatigue budget, threshold drift over time, and what happens when an organ is fed garbage for an hour. | §6's third unchecked box. A detector nobody can live with is a detector that gets switched off. |
| **7** | **Organ fleet operations** | Health of the organ fleet itself: liveness, event-rate anomalies per organ, an organ that has gone silent, and a kill switch per organ that the Governor can pull. | Eight organs are eight things that can quietly die. Silence must not look like safety. |

## The invariant that spans all seven

**An organ that crashes must not pass traffic.** §3 says it; no phase above
proves it for all eight. Phase 1 makes `BaseOrgan` total, and each later phase
adds its organ to the same proof. The failure this prevents is subtle: a
detector that throws and is caught by a caller that defaults to "allow" is worse
than no detector, because the dashboard still shows it green.

---

## Execution log — Phase 1: contract truth

### 1.1 `emit()` fails closed on malformed severity — **defect, fixed**

Measured before the fix:

```
severity=nan   -> accepted, severity=1.0     <- NaN becomes MAXIMUM severity
severity=None  -> RAISED TypeError
severity='x'   -> RAISED TypeError
```

Two bugs in one function.

**A NaN was promoted to `1.0`.** `max(0.0, min(1.0, nan))` in Python does not
raise, does not return NaN, and does not return 0 — it returns `1.0`, because
both comparisons against NaN are False so `min` returns its first argument and
`max` then picks the larger. So a corrupt float silently became the most severe
possible event. A detector that turns "I don't know" into "highest alarm" is
worse than one that stays quiet: it both cries wolf and hides the corruption.
The rule is now the same one the rest of this codebase uses — **unknown becomes
a stated default, never a fabricated extreme**.

**A `None` severity raised.** A crash inside an organ is exactly the case §3
says must never pass traffic. `emit` is now total: it never raises, and a
malformed severity is coerced with a recorded reason rather than an exception.

### 1.2 Every event carries a reason — **gap, closed**

§3 requires "a reason, never only a score". No event had one: `emit()` produced
8 keys and `reason` was not among them. Every event now carries `reason` and
`severity_source`, so a SOC analyst reading an event can see *what* the organ
decided and *why it used that number*. An organ may pass its own reason;
`BaseOrgan` guarantees the field exists either way.

### 1.3 Signing at the source, not only at the bus — **gap, closed**

§6's checkbox "[x] All 8 organs emit signed events" was true only in transit:
`BaseOrgan.emit()` returned an unsigned dict and `bus.ingest_trusted()` signed it
on the way in. An organ whose events are read from `drain_events()` — which is
how the demos and the tests read them — got unsigned events.

That matters because of what §3 asks for: "unsigned events are inert in the
spine". An organ cannot promise its event is signed if a caller can hold it
unsigned. So the event is now sealed at the moment it is created, carrying `mac`
and `signature` (HMAC-SHA256 over the canonical body). An event stripped of its
signature is now **rejected on the way in** rather than silently re-signed.

This does not replace `bus.ingest_trusted()`'s own signing — belt and braces are
correct here — but it means the guarantee holds at the organ's own boundary.

### 1.4 The three untested organs — **gap, closed**

`CookieFluidTurbulence`, `LandauerThermalAudit` and `MutsEbpfRepair` had no test
of any kind. All three now have behavioural tests, plus a shared conformance
suite that every one of the eight must pass. Adding a ninth organ without adding
it to that list is now a test failure.

### 1.5 Determinism, as a test — **gap, closed**

§3 requires deterministic organs and §6 claims it. Nothing tested it. Every
organ is now run twice on identical input and must produce identical events
modulo the event id and timestamp. This is the cheapest possible test of a claim
that a demo depends on and that nothing was checking.


### Phase 1 result

| Check | Before | After |
|---|---|---|
| pytest | 732 passed | **1010 passed** (+278) |
| Organ test files | 3 | **4** |
| Organs with zero tests | **3** (Cookie, Landauer, MutS) | **0** |
| Mutants injected | — | **8 injected, 8 killed** |
| §6 boxes ticked | 3 (2 of them unearned) | **5, each naming its test** |

1010 = 732 + 278. Nothing pre-existing was edited: `test_organs.py`,
`test_hashimoto.py` and `test_page_curve.py` pass untouched, which is the
evidence that the `BaseOrgan` changes were backwards-compatible rather than a
rewrite dressed as a fix.

### Defects found and fixed

| # | Defect | Severity |
|---|---|---|
| 1 | `emit(severity=nan)` produced severity **1.0** — a corrupt float became the maximum possible alarm | **high** — cries wolf and hides the corruption simultaneously |
| 2 | `emit(severity=None)` **raised**, so a malformed input could crash an organ | high — §3 says a crashing organ must never pass traffic |
| 3 | No event carried a **reason**, though §3 requires one | medium |
| 4 | Events were **not signed at source**; only in transit via the bus | medium — §6 claimed this was done |
| 5 | `MutsEbpfRepair.second_attempt_blocked` was hard-coded `True` on **every** call, so the first attempt and the repeat were indistinguishable | **high** — the organ's stated purpose, unimplemented |
| 6 | `MutsEbpfRepair.within_budget` was **unfalsifiable**: `splice_ms` was clamped to the budget before being compared with it, so it was True even for a zero budget | high — a measurement that cannot fail |
| 7 | Three organs had **no test at all** | high — §4 claimed otherwise |
| 8 | `sanitize_event` **deleted `reason`**, so the "why" never reached the Commander | **high** — §3's core requirement, lost in transit |
| 9 | *(not a defect)* In-process ingest re-signs unsealed events | documented design — pinned by test, explained above |

Defects 5 and 6 are the interesting pair. Both are in an organ whose selling
point is that it *notices and repairs*, and both are the same failure: a field
that reported a reassuring value without being connected to anything. The tests
that now guard them are written as behavioural claims ("the first attempt is not
a second attempt"; "a zero budget cannot be met"), not as assertions about the
implementation.

### Two more found by running the bus, not by reading the organ

Both surfaced only from pushing a real organ event through `create_app()` and
reading what the Commander would actually receive.

**8. The sanitiser deleted the reason.** `sanitize_event` whitelists its output,
so any field it does not name is removed. `reason` was not named. The contract
survived the organ and died in the sanitiser:

```
organ.emit(...)                            -> 12 keys, reason present
sanitize_event(sign_event(organ.emit(...))) ->  8 keys, reason GONE
```

The one field a SOC analyst needs — *why* — was the one field the pipeline
threw away. It is now carried, sanitised rather than trusted: printable ASCII
only, control characters collapsed, bounded to 240 characters. `severity_source`
travels with it, so the reason for a defaulted severity is visible too.

This could not be fixed by routing the reason through `_clean_metrics`: that
function digests every string ("zero raw strings"), and a digested reason is
unreadable. A reason has to be legible, which means it needs its own sanitiser
with its own shape constraint.

**9. An unsealed event is re-signed in process — and that is correct.** A forged
0.99-severity event POSTed to `/api/ingest` came back `verified: True` after an
in-process round trip. That looks alarming and is not: `spine/telemetry_mac.py`
states plainly that inside one process the MAC "is an integrity tag, not a
boundary; the boundary is created when the bus runs as a separate UID". The
external HTTP path is the boundary, and it behaved correctly — the forgery was
accepted as `unverified`, stayed visible in `/api/state`, and produced **no
plan and no containment**, because `maybe_auto_orchestrate` requires
`event["verified"]`.

So no code changed for #9. It is recorded here (and pinned by
`test_the_bus_still_re_signs_in_process_by_design`) because "the bus re-signs
events" is a sentence that will otherwise be rediscovered as a vulnerability by
whoever runs the same experiment next.

### What mutation testing proved

Eight deliberate bugs were injected into the new contract code; all eight were
killed. The important one is the first: re-introducing the exact NaN bug that
Phase 1 was written to fix is caught by two tests. A regression test that has
not been shown to fail is a comment with extra steps.

### Not done, and not pretended

- Phase 4's fixture corpus does not exist. **No detection rate is published
  anywhere in this repository**, and none should be quoted in a demo.
- Thresholds (0.72, 2300, 0.90, 8.0 W) remain physically motivated and
  empirically unvalidated. Phase 1 changed no threshold.
- `page_curve_trap` can still call `os.kill` behind `allow_real_kill`. The
  default is now pinned by a test; the capability was not removed, because
  removing it would have been a behaviour change outside Phase 1's brief. It is
  Phase 7's job to give every organ a Governor-pulled kill switch.
