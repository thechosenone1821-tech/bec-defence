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

- [x] All 8 organs emit signed events
- [x] All 8 expose Governor-gated RPCs rather than acting directly
- [x] All 8 are deterministic
- [ ] Each organ has a fixture corpus and a published detection rate
- [ ] Each organ's threshold is calibrated against real traffic
- [ ] False-positive behaviour under normal load is characterised

---

## 7. What this part does not do

- It does not decide anything. Detection only; Part 5 decides.
- It does not touch a real host or a real network.
- It does not have a UI. Part 6 owns the console.
