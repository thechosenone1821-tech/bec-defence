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

---

## Execution log — Phase 2: Organ 1, end to end

**Deliverable (§ table):** Organ 1 through the real bus → sanitizer → Commander,
with a signed event and a Governor-gated RPC round trip.

**Done.** The chain runs, and the two defects found on the way were both about a
guarantee existing somewhere other than where it could be used.

### 2.1 The actuator bypassed the organ's signature gate — **defect, fixed**

This is the defect Phase 2 exists for.

```
executor("drop_bec_cluster", {...})   -> CLUSTER_DROPPED        (no signature anywhere)
organ.handle_rpc(unsigned envelope)   -> REJECTED bad_signature
organ.handle_rpc(signed envelope)     -> OK CLUSTER_DROPPED
```

The organ implemented the gate correctly. The executor — the only code path that
can actually *act* — called `bec._rpc_drop_cluster(args)` directly, a private
method, so the gate was never consulted. A gate that exists only where nothing
can reach it is a comment.

`bus.py`'s own docstring said *"In production this crosses a signed-RPC boundary
(see reflexes.base_organ.sign_rpc)"*. The production path is the code, and the
code did not.

The executor now holds a table of `tool -> organ` and dispatches every
organ-owned tool through `sign_rpc()` + `organ.handle_rpc()`. `set_service_readonly`
and `escalate_human_stepup` have no organ behind them and are marked
`platform_local` rather than pretending otherwise. Every result now carries
`dispatch` (`signed_rpc` / `platform_local` / `dry_run`) and, for organ tools,
`organ`, so the audit trail says who acted rather than only what happened.

### 2.2 An organ refusal was indistinguishable from success — **gap, closed**

With the gate on the path, the refusal path had to become visible. A rejected
RPC now returns `RPC_REJECTED` carrying the organ's reason, instead of the
executor having nothing to say. Otherwise the gate could reject every call and
the SOC log would still read clean.

### 2.3 Organ 1's reason said nothing — **gap, closed**

Phase 1 guaranteed every event *has* a reason. Running the chain showed what
Organ 1's actually was:

```
BEC_SPECTRAL_PROJECTOR reported RANK1_CONDENSATION_DETECTED at severity 0.773
```

True, and useless: it restates the signal name. It now states the measurement:

```
400 of 700 sessions collapse onto one direction (sigma1 share 0.773, threshold
0.72); mean projection gap 8.08 between the two groups
```

This one is worth dwelling on. The Phase 1 test asserted that the reason
contained "condensation" — which the *generic fallback already did*. The test
passed, and the reason was worthless. A test that accepts the fallback as
evidence cannot tell a real reason from a placeholder.

### 2.4 Dry-run provenance — **gap, closed**

The dry-run executor reported `DRY_RUN_<TOOL>` with `dry_run: true`, which was
already honest, but nothing on the orchestration bundle distinguished a dry
dispatch from a real one at a glance. It now sets `dispatch: "dry_run"`, the same
field the organ path uses with a value that cannot be confused for it.

### What mutation testing found — including a survivor that mattered

Six mutants, and the first run had **one survivor: the defect itself**. A mutant
that restored the exact bypass *while still setting `dispatch: "signed_rpc"` on
the result* passed all 25 tests.

That is the most useful result of the phase. The original test asserted a
self-reported label:

```python
assert out["dispatch"] == "signed_rpc"   # verifies the label, not the mechanism
```

The fix was to observe the mechanism instead — patch `BaseOrgan.handle_rpc` and
assert the executor actually entered it, with a signature on the envelope:

| Mutant | First run | After strengthening |
|---|---|---|
| Executor bypasses the signed gate (the bug) | **SURVIVED** | killed (3 failures) |
| Execute actions the Governor blocked | killed | killed |
| Let unverified events reach the Commander | killed | killed |
| Commander stops reacting to Organ 1 | killed | killed |
| Organ renames its signal | killed | killed |
| Dry-run claims a real dispatch | killed | killed |

A second bug came out of the same work, in the tests themselves: the recording
test patched `BECSpectralFilter.handle_rpc` — a *subclass* attribute — which
shadowed the base-class patch a later test installed. The suite passed when that
test ran alone and failed when it ran after. Patching is now done at
`BaseOrgan` only, and the reason is written into the test, because a
pass-alone-fail-together test is worse than no test: it trains people to re-run
until green.

### Live verification

Against a running `uvicorn spine.bus:create_app` on `:8099`:

```
POST /api/ingest  (forged 0.99 event)  -> {accepted:1, verified:0, unverified:1}
GET  /api/state                        -> the forgery is visible, verified:False
POST /api/orchestrate                  -> HELD_UNVERIFIED_EVIDENCE, actions:null
```

and the trusted chain, driven through the same app object:

```
1. ORGAN  ratio=0.773 rank1=True sealed=True
2. BUS    verified=True organ=BEC_SPECTRAL_PROJECTOR signal=RANK1_CONDENSATION_DETECTED
3. CMD    mode=fallback_rules actions=['drop_bec_cluster']
4. GOV    ['APPROVED']
5. EXEC   drop_bec_cluster -> {'status':'CLUSTER_DROPPED','dispatch':'signed_rpc',
                               'organ':'BEC_SPECTRAL_PROJECTOR'}
```

### Phase 2 result

| Check | Before | After |
|---|---|---|
| pytest | 1010 passed | **1036 passed** (+26) |
| Mutants | — | **6 injected, 6 killed** (1 needed a test rewrite first) |
| Organ tools through the signed gate | 0 of 8 | **8 of 8** |
| Live forged event reaching a plan | 0 | 0 (unchanged, now asserted) |

### Not done, and not pretended

- The SLM is unreachable in this environment, so every live run above is
  `commander_mode: fallback_rules`. The **SLM path through the seam is untested.**
  Phase 3 should not assume the model path behaves like the rule path.
- The signed-RPC secret is a dev default (`EIGENSHIELD_RPC_SECRET`). In one
  process, as `telemetry_mac.py` already says of the bus key, this is an
  integrity tag and not a boundary. Phase 7 owns making that a real boundary.
- `page_curve_trap` is still constructed with `allow_real_kill` False by the bus;
  the capability remains, and Phase 7 owns the kill switch.
- No fixture corpus, no detection rate. Unchanged from Phase 1.

---

# Phase 3 execution log — the remaining seven organs

**Status: complete.** Every organ in Part 4 now emits a signal the Commander
acts on, that action passes the Governor, and the organ is reached through a
signed RPC. Suite: `raksha-code/tests/test_organs_phase3_e2e.py`, 35 tests.

The audit at the start of this phase drove all seven organs with real inputs
and pushed the resulting events through the real chain
(bus → sanitiser → Commander → Governor → executor). It produced 6 events and 8
actions, all APPROVED, 7 executed via `signed_rpc`. That reading was **too
good**: three of those eight actions were defective, and the tests I had
intended to write would have blessed them. What follows is what the audit
actually found.

## 3.1 Defect #11 was systemic, not local

Phase 2 fixed Organ 1's reason from

    BECSpectralFilter reported RANK1_CONDENSATION_DETECTED at severity 0.94

to

    400 of 700 sessions collapse onto one direction (sigma1 share 0.773,
    threshold 0.72); mean projection gap 8.08 between the two groups

The audit showed `PageCurveTrap` doing the same thing — *"ENDPOINT_PAGE_CURVE
reported PARITY_ENTROPY_COLLAPSE at severity 0.960"*. Counting `reason=`
keyword arguments across the organ tree found that **six of the seven remaining
organs** used the generic `BaseOrgan` fallback. Organ 1 was not a one-off; it
was the only one anybody had looked at.

Why this matters more than it sounds: the fallback sentence is *true*. Nothing
is misreported, no assertion can fail on a lie. It is useless, which is worse,
because it passes every check while telling an operator nothing they could act
on. A reviewer reading the log learns that the organ fired and nothing else.

All six now state the measurement. Examples taken from an actual run:

| Organ | Reason now emitted (verbatim) |
|---|---|
| `COOKIE_FLUID_TURBULENCE` | `Re_beh 1375000 over critical 2300 (ratio 597.83): cursor velocity 4000 px/s with navigation length 2000 px departed the calibrated baseline, so the session is replayed rather than driven by a person` |
| `BRAGG_FFT_FIREWALL` | `Bragg peak ratio 1.000 against threshold 0.320; Fiedler lambda2 0.000 below 0.050 — periodic instruction structure in sha256:abc, flags ['BRAGG_PEAK', 'FIEDLER_FRACTURE']` |
| `HESSIAN_LYAPUNOV_GUARD` | `Directional curvature +11.000 exceeded the jailbreak cliff 2.500 at step 8; restoring vector norm 1.540 applied against the adversarial direction` |
| `LANDAUER_THERMAL_AUDITOR` | `55.0 W measured against 40.0 W predicted from IPC 2.00 and die temp 50.0 C, over threshold 8.0 W for 5 consecutive samples` |
| `ENDPOINT_PAGE_CURVE` | `Honey block .honey_a_00.bin failed its mutual-information parity check after 4096 bytes were written by pid 777: 16272 of 32768 parity bits flipped (49.66% of the block), verified in 0.20 ms. Legitimate readers never write here.` |
| `MUTS_EBPF_REPAIR` | `svc_web tripped invariant inv_svc_web_1795672236193 (bounds_violation); bounds_check_v1 spliced in 0.013 ms against a 50.0 ms budget (within budget), freeze window 0.021 ms` |

## 3.2 Constants wearing the costume of measurements

Chasing the reasons turned up numbers that were never measured. Each was a
constant in production code, presented to the operator as an observation:

| Location | Was | Is now |
|---|---|---|
| `PageCurveTrap.on_write` | `parity_delta: 0.994`, always | counted from recomputed vs sealed parity (`flipped_bits / 32768`) |
| `PageCurveTrap.on_write` | `latency_ms: 0.9` | `time.perf_counter()`, and the label `PID_TERMINATED_0.9MS` no longer publishes it |
| `PageCurveTrap.on_write` | `severity: 0.96`, always | derived from measured parity delta (§3.2.1) |
| `HashimotoPercolation` | `severity: 0.85`, always | derived from `rho_before - rho_after` |
| `HashimotoPercolation` | `tier0_edges_cut: 0` (literal) | counted against the organ's own tier-0 set |
| `MutsEbpfRepair` | `severity: 0.9`, always | derived from splice overrun against budget |
| `CookieFluidTurbulence` | `reason` | states `Re_beh`, critical value, ratio, and the observed cadence |

### 3.2.1 The severity scale has to match the measurement's range

The first attempt scaled PageCurve severity as `0.5 + parity_delta / 2`. That
looks reasonable and is wrong, because of the organ's own arithmetic:
`P = A XOR H(B, salt)` with random `B` means an overwrite of an *entire* block
changes only ~50 % of parity bits, not 100 %. So `parity_delta` saturates near
0.5 and the formula could never exceed 0.75.

The Commander escalates to a human at severity ≥ 0.9. A full 4 KB cipher pass
would therefore have been filed as a *trap refresh* instead of ransomware. The
regression appeared immediately as a dropped action in the end-to-end drive —
8 actions became 7 — and that is how it was caught. The scale is now anchored
on the measurable range: 1 bit → 0.500, 512 B → 0.559, full block → 0.960.

Measured over five independent runs. The honey blocks are fresh random bytes
each time, so the exact bit counts vary within a band — the ranges below are
the observed spread, not one lucky sample:

| Overwrite | `flipped_bits` (5 runs) | severity range |
|---|---|---|
| 1 bit | `1` every run | 0.500 – 0.500 |
| first 512 B | 1961 – 2023 | 0.555 – 0.557 |
| full 4096 B | 16257 – 16510 | 0.956 – 0.964 |

A one-bit break is exactly one bit, deterministically: because
`P = A XOR H(B, salt)`, the parity difference is precisely the bits of `A` that
changed. Only the *cipher* rows have spread, and that spread is the measurement
working — it is `~50 %` of a random overwrite, as the arithmetic predicts.

## 3.3 Fabricated attribution — organs inventing hosts

Five organs stamped a host id they had no way to know:

| Organ | Stamped | Why it is wrong |
|---|---|---|
| `CookieFluidTurbulence` | `HOST_UNKNOWN` | behaviour telemetry has no host at all |
| `BraggFFTFirewall` | `HOST_APP_SRV_07` | reads a *document*; nothing has opened it |
| `HessianLyapunovGuard` | `HOST_APP_SRV_07` | a hidden-state trajectory belongs to a model, not a machine |
| `MutsEbpfRepair` | `HOST_APP_SRV_07` | runs *inside* a service, unknown to itself |
| `HashimotoPercolation` | `VLAN_FABRIC` | a VLAN id placed in a host field |

`HOST_APP_SRV_07` is a **real id from `company_topology.json`**, which is what
made this invisible: nothing in the log said "guessed", and a plausible id
reads as evidence. All five now take `host_id` as an argument defaulting to
`None`; the sanitiser's whitelist drops `None`, so a host the organ does not
know becomes an *absent key* rather than an invented one. Verified directly:
`sanitize_event` on `{"host_id": None, "vlan_id": ..., "session_id": ...}`
returns an entity dict without `host_id`.

### 3.3.1 `HOST_UNKNOWN` was being dispatched as a successful action

The worse half of the same defect. `Orchestrator._fallback_rules` fell back to
`"HOST_UNKNOWN"` / `"SESS_UNKNOWN"` when an event carried no entity, so:

    arm_page_curve_traps   args={'host_id': 'HOST_UNKNOWN', 'density_level': 'high'}
                           -> TRAP_DENSITY_BOOSTED  signed_rpc

The organ armed traps on a host that does not exist, reported success, and the
action consumed blast-radius budget. The Commander now refuses to propose a
target it does not have, and records why:

    actions: [escalate_human_stepup]
    skipped_actions: [{tool: arm_page_curve_traps,
                       reason: "no host_id in the event; traps cannot be armed on an unknown host"}]

`skipped_actions` is part of the `/api/orchestrate` bundle. A rule that wanted
to act and could not is not the same as a rule that matched nothing, and the
two were previously indistinguishable in the response.

## 3.4 Ring 4's only RPC was a status string

`HashimotoPercolation._rpc_execute_cut` returned
`{"status": "PERCOLATION_CUT_APPROVED"}`. It did not cut anything and did not
emit an event. In the running system `containment_plan()` — the method that
does the work and emits `PERCOLATION_CUT_EXECUTED` — **is never called by
anything except tests**; the bus uses its own exhaustive planner in
`spine/containment.py`. So the organ was reachable, signed, gated, and inert.

Two things were deliberately *not* done:

* **It does not compute its own cut.** The first attempt had the RPC re-derive
  a cut from the topology. That put policy in the actuator, and it produced a
  *different, more disruptive* cut than the one the Governor approved —
  including `VLAN_CORP_IT↔VLAN_CORE_AUTH`, an edge incident to a crown jewel.
  An actuator executes the approved plan; it does not improve on it. The edges
  arrive in `args["cut_edges"]`.
* **It does not take the protected set from the caller.** A list of crown
  jewels supplied as an argument is a list the caller can shorten. The organ
  reads tier-0 from its own `company_topology.json` and fails closed.

It now executes the plan and emits what it did:

    Severed 3 edge(s): VLAN_MAINT_03<->VLAN_GUEST_WIFI, VLAN_GUEST_WIFI<->VLAN_CORP_IT,
    VLAN_CORP_IT<->VLAN_LAB_DEV; spectral radius 2.423 -> 0.990, 100.0% of
    critical-weight flow preserved, 0 tier-0 edges cut, 0 tier-0-adjacent edge(s) severed

Recursion check: `emit()` appends to the organ's local buffer and calls
`event_sink` only if one exists. `create_app` constructs
`HashimotoPercolation()` bare, so an event emitted inside an RPC cannot
re-enter the pipeline. Asserted by
`test_the_rpc_executes_the_approved_cut_and_emits`.

## 3.5 `/api/containment`: a silently overridden safety request

The route hardcoded `preserve_tier0_vlans: True` and ignored the body. So:

    POST /api/containment {"seeds": ["VLAN_GUEST_WIFI"], "preserve_tier0_vlans": false}
    -> status: OK | governor: APPROVED | executor: PERCOLATION_CUT_APPROVED

The system did the safe thing and **reported a decision the caller had
explicitly overridden**. That teaches an operator that their input is advisory,
which is the opposite of what a safety flag is for. It now honours the request
and refuses visibly:

    -> status: HELD_EXECUTION_BLOCKED | governor: BLOCKED
       reason: execute_percolation_cut requires preserve_tier0_vlans=true

The refusal ladder, measured on a live server (port 8124) across all nine VLANs:

| Seed | Outcome | Reason |
|---|---|---|
| `VLAN_CORE_AUTH`, `VLAN_ICU_CLINICAL`, `VLAN_COLDCHAIN_TELEMETRY` | `REFUSED` | seed sits on Tier-0 — no cut can protect a breached crown asset |
| `VLAN_CORE_DB` | `INFEASIBLE` | no cut severs reachability without cutting it |
| `VLAN_ER_OPS` | `HELD_EXECUTION_BLOCKED` | preserved uptime 44.44 % below floor 90 % |
| `VLAN_CORP_IT` | `HELD_EXECUTION_BLOCKED` | tier-0-adjacent edge (`VLAN_CORE_AUTH`) in the plan; human step-up required |
| `VLAN_GUEST_WIFI`, `VLAN_LAB_DEV` | `OK` / `APPROVED` | 3 edges cut, 100 % critical-weight flow preserved |

Live HTTP, `VLAN_GUEST_WIFI`:

    status: OK | gov: APPROVED
    executor: PERCOLATION_CUT_APPROVED | edges_cut: 3 | dispatch: signed_rpc
    rho: 2.4227 -> 0.99

## 3.6 The Phase 3 suite

`raksha-code/tests/test_organs_phase3_e2e.py` — 35 tests, 8 classes, one per
organ plus `TestFleetInvariants`. Mechanism assertions only: each end-to-end
test patches `BaseOrgan.handle_rpc`, records entry, and asserts a `signature`
was present on the envelope. No test asserts `dispatch == "signed_rpc"`; the
Phase 2 mutant that proved that label worthless is the reason.

### 3.6.1 Three bugs found in the suite itself, by running it

The suite failed 11 times on first run. Every failure was a defect in the
*test*, not the code — which is the outcome that should be expected, and the
reason a green first run is not evidence of anything:

1. **A callable object does not bind as a method.** `GateSpy` was an instance
   whose `__call__` was assigned to `BaseOrgan.handle_rpc`. A callable instance
   has no descriptor protocol, so Python did not pass `self` and every call
   raised `missing 1 required positional argument`. Returning `self.__call__`
   failed the same way because it is already bound. The fixture now returns a
   plain closure.
2. **`CookieFluidTurbulence` emits per sample, not per session.** The organ
   emits on *every* turbulent sample, so a 6-sample window yields several
   events. The test asserted exactly one. It now asserts the set of signal
   types.
3. **The Lyapunov fixture did not deflect.** `kappa = <v_t - v_prev, v_t> /
   |v_t|²` measures how sharply the velocity turns; a sequence of equal steps
   gives kappa = 2.0, below the 2.5 cliff. The organ was right and the fixture
   was wrong. A *deceleration* (a long move then a near-stop) is the shape that
   trips it: kappa = 3.17 and 179 for the two fixtures.

## 3.7 Mutation testing — 10 mutants, 10 killed

`/tmp/mut_p3.py` reintroduced each defect into production code and verified the
pattern matched exactly once before running the suite (a `str.replace` that
does not match is a silent no-op, and a mutant that never applied is not a
killed mutant).

| # | Mutant | Killed by |
|---|---|---|
| M1 | executor calls the organ directly, bypassing `handle_rpc` | all 7 mechanism tests |
| M2 | `CookieFluidTurbulence` emits a different signal type | Ring 1 test |
| M3 | `PageCurveTrap` reverts to the generic reason | `test_the_reason_states_the_measurement` |
| M4 | `BraggFFTFirewall` re-invents `HOST_APP_SRV_07` | `test_the_organ_does_not_invent_a_host` |
| M5 | `parity_delta` reverts to the constant `0.994` | `test_a_one_bit_break_is_measured_as_one_bit` |
| M6 | the organ invents a cut instead of executing the plan | `test_the_organ_refuses_a_cut_it_was_not_given` |
| M7 | the tier-0 guard is removed from the cut RPC | `test_the_organ_refuses_a_cut_that_would_touch_tier0` |
| M8 | the route overrides the caller's tier-0 opt-out again | `test_the_api_path_honours_an_explicit_tier0_opt_out` |
| M9 | a hostless event is dispatched as `HOST_UNKNOWN` | `test_a_hostless_event_is_skipped_visibly_not_dispatched` |
| M10 | MUTS severity is a constant again | `test_a_zero_budget_does_not_raise` |

Result: **10/10 killed.**

## 3.8 Live verification

Server: `uvicorn spine.bus:create_app --factory`, port 8124, fresh process.
Eleven events were produced by driving six organs with real inputs, signed with
the bus key, and POSTed to `/api/ingest` over HTTP (`accepted: 1, received: 1,
unverified: 0`). `/api/orchestrate`, over HTTP:

    7 actions
      revoke_turbulent_session     -> SESSION_REVOKED        [signed_rpc]
      quarantine_ai_document       -> DOCUMENT_QUARANTINED   [signed_rpc]
      clamp_lyapunov_steering      -> STEERING_CLAMPED       [signed_rpc]
      isolate_thermal_anomaly_host -> HOST_ISOLATED          [signed_rpc]
      arm_page_curve_traps         -> TRAP_DENSITY_BOOSTED   [signed_rpc]
      escalate_human_stepup        -> HUMAN_STEPUP_REQUESTED [platform_local]
      deploy_muts_ebpf_shield      -> SHIELD_DEPLOYED        [signed_rpc]

Six of seven through the signed gate; `escalate_human_stepup` is correctly
`platform_local` (it notifies a human, it does not command an organ).

**A defect I found and did not fix, because it is not a defect:**
before the clean run I POSTed *unsigned* events to the same server. They were
held (`HELD_UNVERIFIED_EVIDENCE`, `unverified_events: 11`) — correctly. But the
two forged severity-0.99 events had also tripped the FORTRESS tripwire, which
then froze the AI path:

    revoke_turbulent_session -> BLOCKED
      FORTRESS tripwire frozen — 2 unverified disruptive-action requests inside
      60s; human step-up required

Every subsequent action was blocked. That is the tripwire doing exactly its
job: unverified disruptive traffic freezes autonomous action. It is recorded
here because a reader who saw only the second run would not know why a fresh
process was required.

## 3.9 Full-suite state

| Check | Result |
|---|---|
| `pytest tests/` | **1071 passed, 1 skipped, 1 xfailed** |
| `pytest tests/ --collect-only` | **1073 collected** (1071 + 1 + 1) |
| `test_organs_phase3_e2e.py` | 35 passed |
| `node --test tests/*.test.js` | **90 pass, 0 fail** |

The Phase 2 baseline was 1036 passed / 1038 collected. Phase 3 adds 35 tests:
1036 + 35 = 1071, and 1038 + 35 = 1073. Both reconcile.

Also re-pinned: `spine/config/manifest.json`. `tool_schemas.json` gained the
five optional arguments `execute_percolation_cut` now takes (`cut_edges`,
`rho_before`, `rho_after`, `preserved_critical_weight_pct`, `seeds`), so the
FORTRESS integrity check correctly reported `TAMPERED` until the manifest was
re-sealed with `python3 spine/boot_manifest.py --pin spine/config/manifest.json`
and verified with `--check` (`INTEGRITY OK — 4 security-critical file(s)
verified`). The check working is the point; re-pinning after a deliberate
change is the documented workflow.

## 3.10 Not done, and not pretended

* **No detection rate is quoted anywhere in this log.** Phase 4 owns the
  fixture corpus and the published rates. Every number above is a measurement
  of a *mechanism* (bits flipped, milliseconds, spectral radius), not a claim
  about detection efficacy.
* **The Commander is still `fallback_rules`.** `/api/health` reports
  `commander_mode: fallback_rules` on every run. The SLM path remains untested.
* **`PageCurveTrap` still does not kill.** `allow_real_kill` stays `False`;
  every `on_write` returns `dry_run: True`. Phase 7 owns real enforcement.
* **The RPC secret is still the dev default.** The signature is an in-process
  integrity tag, not a cryptographic boundary against a local attacker.
* **`HashimotoPercolation.containment_plan()` is still test-only.** The bus
  plans via `spine/containment.py`; the organ plans nothing in production and
  that is now explicit rather than accidental. Whether the two should be
  reconciled into one implementation is a Phase 5/7 question, not a Phase 3 one.
* **The tripwire freeze is per-process and time-based** (60 s window). It has
  no operator reset endpoint; a fresh process was needed to continue. That is
  arguably correct for Phase 3 and is left for Phase 6 (fatigue/drift).

---

# Phase 4 execution log — the fixture corpus, and the rates it earns

**Status: complete, and it changed what I believe about three of the eight
organs.** Every organ now has a labelled corpus, a committed runner, and a
published detection rate, false-positive rate and precision. The numbers are
worse than the roadmap assumed and better than an adjective.

## 4.1 The design decision that makes the numbers mean anything

A fixture corpus has an obvious failure mode, and it is not instability. It is
that **the person who writes the attack cases also wrote the detector.** Hand-
author a botnet as "many sessions sharing one direction" and Organ 1, which
computes the variance share along one direction, scores 100 %. That number
measures consistency, not detection.

So no case is a recorded sample. Every case is a **seeded generator expression**
in the corpus file, compiled by one shared routine
(`corpora/harness.py::_build_sessions`), with the parameters visible:

    {"id": "A2-small-offset-bots", "label": "attack",
     "generator": "10 benign ~ N(0,1)_5 ; 30 bots ~ N(0,0.02)_5 + [3,0,0,0,0]",
     "bot_offset": [3.0,0,0,0,0], "bot_std": 0.02, ...}

A reader who doubts "offset 3" can ask what happens at offset 1 without
trusting the author. Every case also carries a `rationale` explaining why it is
in the corpus, and a `family` so the report can be broken down.

Three structural safeguards follow from the same reasoning:

* **The oracle is the generator, not the detector.** `oracle_expected()` reads
  the case's label. No rate is derived from anything the organ reports about
  itself.
* **Every organ is scored by observing emission**, via its real entry point,
  never by reading a verdict field. `run_organ1` asserts
  `fired == result["is_rank1_botnet"]` and then returns the *emission*.
* **Every corpus must contain benign cases, and hard ones.** A corpus of only
  attacks scores 1.00 against any always-fire detector. The suite fails a
  corpus with one label only, and requires named adversarial-benign families
  (`homogeneous-fleet`, `human-expert`, `procedural`, …).

## 4.2 The published rates

Measured by `python3 corpora/run_corpus.py`. 52 cases: 23 attack, 27 benign,
2 identifiability controls (excluded from every rate — see §4.3).

| Organ | A/B | Detection rate | FPR | Precision |
|---|---|---|---|---|
| `BEC_SPECTRAL_PROJECTOR` | 6/5 | 0.83 | **0.60** | 0.62 |
| `COOKIE_FLUID_TURBULENCE` | 3/3 | 0.67 | **0.67** | 0.50 |
| `BRAGG_FFT_FIREWALL` | 3/4 | 1.00 | **0.75** | 0.50 |
| `HESSIAN_LYAPUNOV_GUARD` | 2/4 | 1.00 | 0.00 | 1.00 |
| `LANDAUER_THERMAL_AUDITOR` | 2/3 | 1.00 | 0.33 | 0.67 |
| `ENDPOINT_PAGE_CURVE` | 3/3 | 1.00 | 0.00 | 1.00 |
| `MUTS_EBPF_REPAIR` | 2/2 | 1.00 | 0.00 | 1.00 |
| `HASHIMOTO_PERCOLATION` | 2/3 | 1.00 | 0.00 | 1.00 |

**Reference point, and it is the reason FPR is in this table at all:** a
detector that always fires scores detection 1.00 and FPR 1.00 on any balanced
corpus. Four organs report 1.00 detection; only two of those also report 0.00
FPR, and those two are *mechanistic* — a tripwire and a refusal — not
classifiers.

Precision is published because a high detection rate with useless precision is
how a detector gets switched off in month two (Phase 6's subject).

## 4.3 Finding: Organ 1's threshold is not measuring what it claims

Organ 1's docstring says the statistic separates a botnet ("many sessions
condensing onto one direction") from a population. The corpus says otherwise.

**The decisive experiment.** Build two populations from the *same* law — all
rows `outer(N(0,6), [1,0,0,0,0]) + N(0,0.05)` — and call some of them hostile:

| Composition | Condensation ratio |
|---|---|
| 5 "bots" of 40 | 1.000 |
| 10 of 40 | 1.000 |
| 20 of 40 | 1.000 |
| 30 of 40 | 1.000 |
| 35 of 40 | 1.000 |

The ratio does not move with the label, because the input does not change.
Relabelling the same matrix gives bit-identical output. **A homogeneous fleet
of managed devices condenses to 1.0 regardless of how many members are
compromised**, and this is not a bug in the organ — it is the definition of a
variance share. There is no function of a session × feature matrix that can
recover a label the matrix does not contain.

Those two cases are committed as `X1-identifiability-setup` and
`A7-identical-law-enemy-label`, with `role: "control"`, and excluded from every
rate. Counting a miss on them as a detector failure would understate the organ
while concealing the reason.

**What the organ actually keys on** is population homogeneity, not malice:

| Case | Ratio | Fires (thr 0.72) |
|---|---|---|
| 40 independent humans | 0.39 | no |
| 30 bots at offset 15 | 0.98 | yes |
| 30 bots at offset 3 | 0.74 | yes (barely) |
| 30 bots at offset 1 | 0.38 | **no** |
| 40 clean fleet devices | 1.000 | **yes** |
| 20 heterogeneous humans | 0.78 | **yes** |

A homogeneous benign fleet and a stealthy botnet are the same number. The
threshold sits at 0.72, which is inside the range *both* spans.

**So the published 0.83 / 0.60 is not "Organ 1 is mediocre."** It is "Organ 1
detects offset-separated botnets perfectly (1.00 on that family), misses
population-matched ones (0.00), and fires on most benign homogeneity (0.60)."
The aggregate hides the mechanism; the per-family table in the JSON report does
not. Concretely, the fix is not a threshold — it is a statistic that uses
something the matrix does lack: shared *timing* or shared *target choice*
across sessions, which the organ does not ingest.

## 4.4 Finding: Organ 3's threshold is inert, and its second rule carries the work

Bragg fires when `bragg_peak_ratio > 0.32` **or** `fiedler_lambda2 < 0.05`.

| Case | peak | λ₂ | Peak rule | Fiedler rule |
|---|---|---|---|---|
| A1 direct injection | 0.667 | 0.0000 | BLOCK | BLOCK |
| A2 nested override | 0.227 | 0.0000 | pass | BLOCK |
| A3 fragment set | 0.228 | 0.0000 | pass | BLOCK |
| B1 normal prose | 0.157 | 0.2187 | pass | pass |
| B2 listicle | 0.647 | 0.0000 | **BLOCK** | **BLOCK** |
| B3 repeated boilerplate | 0.946 | 0.0000 | **BLOCK** | **BLOCK** |
| B4 markdown headings | 0.446 | 0.0000 | **BLOCK** | **BLOCK** |

Two things fall out of that table.

1. **The peak rule is not doing the detecting.** Both real injections score
   *below* the 0.32 peak threshold (0.227 and 0.228) — they are blocked by the
   Fiedler rule. Sweeping the peak threshold from 0.32 to 0.99 changes no
   verdict on any case: the organ's published "Bragg peak" tuning knob is
   inert for detection.
2. **Lists repeat, and repetition is the trigger.** Listicles, boilerplate and
   markdown headings all fire. There is no peak threshold that keeps injections
   and drops listicles, because an injection *is* periodic text — the premise
   that periodicity distinguishes hostile from procedural instruction is false
   on this corpus.

The Fiedler rule also fires on every non-prose case including the fragment set,
so the organ is closer to "is this prose?" than "is this an injection?".

## 4.5 Finding: /tmp was right about Organ 2

`COOKIE_FLUID_TURBULENCE` publishes **0.67 detection and 0.67 FPR** — the same
number, which is the signature of a statistic correlated with *activity* rather
than with *scripting*:

| Case | Re_beh | Verdict | Correct? |
|---|---|---|---|
| Human browsing | 1 100 | laminar | yes |
| Human brisk (300 px/s) | 6 187 | **turbulent** | **no** |
| Human erratic (450 px/s) | 9 000 | **turbulent** | **no** |
| Script, linear scan | 185 625 | turbulent | yes |
| Script, fast harvester | 98 400 | turbulent | yes |
| **Script, throttled** | 619 | **laminar** | **no** |

A fast human is flagged; a script that throttles itself is not. `re_crit =
2300` sits between "brisk human" and "brisk human", not between human and
machine. The corpus's `human-expert` family is what makes this visible — a
corpus of only `human browsing` would have scored this organ 1.00 / 0.00.

## 4.6 Organ 5's false positive is a data limitation, stated as one

`B2-real-hot-workload` (50 W at IPC 1.2) is flagged: the fitted model predicts
40.0 W, so residual 10.0 W exceeds the 8 W threshold. The calibration is
**twelve identical points**, which yields `coef_ipc_w = 0.032` — the IPC term
is almost irrelevant, so the model cannot attribute IPC-driven draw at all.
This is a corpus limitation, not a code defect, and it is exactly what Phase 5
(captured traffic, a real power model) exists to fix. It is recorded rather
than papered over.

## 4.7 What the two clean organs have in common

`ENDPOINT_PAGE_CURVE` and `MUTS_EBPF_REPAIR` both score 1.00 / 0.00 / 1.00. It
would be easy to present that as the best result in the table. It is the
*least* informative result:

* Page-Curve is a **tripwire** — a write to a file no legitimate process should
  touch. There is no classification to get wrong, so 1.00 is expected once the
  hook is correct.
* MUTS is a **refusal** — a service with no registered invariant is declined by
  construction.

Neither is a detector in the statistical sense. Their 1.00 says the plumbing is
right; it says nothing about whether they would catch a real attacker who has
read this file. `HESSIAN_LYAPUNOV_GUARD` and `HASHIMOTO_PERCOLATION` also score
cleanly, but on 2 attack cases each — a corpus that small cannot distinguish
0.8 from 1.0.

## 4.8 The Phase 4 suite

`tests/test_phase4_corpus.py` — 21 tests, 5 classes:

| Class | Guards |
|---|---|
| `TestEveryCorpusIsHonest` | 8 corpora, 8 adapters, `synthetic` provenance, both labels present, adversarial-benign families present, real rationales |
| `TestDeterminism` | every matrix case builds byte-identically twice; a different seed gives a different matrix; the whole report is reproducible |
| `TestScoringIsNotGameable` | always-fire scores detection 1.00 *and* FPR 1.00; never-fire scores 0; perfect is distinguishable from lazy; controls are excluded; flipping a control's label changes nothing |
| `TestIdentifiability` | the §4.3 claim, executable: ratio invariant to bot fraction, relabelling changes nothing, the two controls fire identically |
| `TestPublishedRates` | all 8 organs scored; a corpus without provenance is refused *by the loader*; Organ 1's FPR is recorded as ≥ 0.4; Organ 3's FPR ≥ 0.5; the two mechanistic organs are clean |

Tests assert **properties, not the numbers.** Pinning "Organ 1 = 0.83" would
break on every corpus addition and tell a reader nothing. The two exceptions
are deliberate tripwires: `test_organ1_publishes_a_high_false_positive_rate`
and `test_organ3_cannot_separate_injection_from_procedural_text` fail if a
future fix changes the finding, with a message saying to update the spec and
the test together rather than leave the table stale.

### 4.8.1 Five defects found in the Phase 4 work itself

1. **The corpus validator demanded matrix-only fields from every case.** Loading
   an Organ 2 text/cadence corpus raised "missing `bot_direction_spread`". The
   schema described one corpus shape, not all of them; validation is now
   kind-aware.
2. **`score_corpus` built its own payloads.** It called `build_case` directly,
   so seven of eight corpora raised "unknown case kind". It now accepts a
   compiler from the caller.
3. **A test asserted `precision == 0.5` on an always-fire detector.** True for a
   5-and-5 corpus, wrong for 6-and-5. The arithmetic was mine, not the code's.
4. **A test could not fail.** The provenance test deleted a field from an
   in-memory dict and then asserted a raise from a call that never read it.
   Rewritten as `test_a_corpus_without_provenance_is_refused`: it writes a real
   broken file and monkeypatches the corpus directory, so the refusal comes
   from the loader that actually enforces it.
5. **I generated filler rationales.** Faced with a "rationale too thin" failure,
   the first fix appended `"— included because X is a case the organ must handle
   correctly for its rate to mean anything."` to three cases. That is exactly
   the substantiation-shaped noise this phase exists to remove. All three were
   rewritten by hand to say what the case actually tests.

Defect 5 is the one worth naming: the failure mode of an evidence phase is not
a wrong number, it is a number surrounded by text that looks like justification.

## 4.9 Mutation testing — 8 mutants, 8 killed

`/tmp/mut_p4.py`. Each mutant makes the evidence untrustworthy in a different
way; the suite must catch all of them.

| # | Mutant | Killed by |
|---|---|---|
| M1 | a corpus drops its `provenance` stamp | 18 failures (`load_corpus` refuses) |
| M2 | a corpus contains only attack cases | `test_both_labels_are_present_in_every_corpus` |
| M3 | a case carries a one-word rationale | `test_every_case_carries_a_generator_and_a_rationale` |
| M4 | control cases relabelled as scored | `test_controls_are_excluded_from_every_rate` |
| M5 | two cases share an id | `load_corpus` duplicate-id check (12 failures) |
| M6 | every case loses its `family` tag | `test_every_corpus_has_at_least_one_adversarial_benign_case` |
| M7 | the loader stops requiring `provenance` | `test_a_corpus_without_provenance_is_refused` |
| M8 | controls are counted in the rates | `test_a_control_case_cannot_improve_a_score` |

Result: **8/8 killed.**

## 4.10 Full-suite state

| Check | Result |
|---|---|
| `pytest tests/` | **1092 passed, 1 skipped, 1 xfailed** |
| `pytest tests/ --collect-only` | **1094 collected** (1092 + 1 + 1) |
| `test_phase4_corpus.py` | 21 passed |
| `node --test tests/*.test.js` | **90 pass, 0 fail** |

Phase 3 was 1071 passed / 1073 collected. 1071 + 21 = 1092 and
1073 + 21 = 1094. Both reconcile.

## 4.11 What this phase does and does not settle

**The §6 checkbox "each organ has a fixture corpus and a published detection
rate" is now true in the narrow, literal sense** — and the honest summary is
that four of eight organs are statistical classifiers with FPR at or above
0.33, and of those, two have a threshold that does not do what its name says.

**It does not settle calibration.** Every corpus is synthetic. The thresholds
(0.72, 2300, 0.32/0.05, 2.5) have not been tested against traffic from a real
network or a real model, and §4.3 is evidence that at least two of them are
misplaced relative to *synthetic* data, let alone real data. Phase 5's job.

**It does not settle false-positive behaviour under load.** One benign case per
family is a demonstration that a failure mode exists, not a rate. Phase 6.

**And it does not license a demo claim.** No sentence in any demo may say
"detects 83 % of botnets". The defensible sentence is: *"on a 13-case synthetic
corpus authored in this repository, Organ 1 fires on 5 of 6 attack vectors and
3 of 5 benign populations, and the two failures share one cause."*
