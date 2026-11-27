# RAKSHA — Project Context for AI Collaborators

> **Read this first. Then `AI_HANDOFF.md`. Then your task file.**
> **Last updated:** 2026-11-26 · **Owner of record:** repo maintainer (human).
> **Phase 3/4 note:** `../packages/contracts/` now owns one canonical JSON rule,
> one signed-envelope contract and shared i18n rendering; Citizen sentences live
> in `../apps/citizen/copy.py`. VoiceGuard/MAYA remain a frozen, disabled seam.
> See [`PHASE3_CONTRACT_SPINE.md`](PHASE3_CONTRACT_SPINE.md) and
> [`PHASE4_CITIZEN_CONSOLIDATION.md`](PHASE4_CITIZEN_CONSOLIDATION.md).
> This file exists so an AI that has never seen this project can act like a
> senior teammate by the end of one read. If you change facts here, you MUST
> update `CHANGELOG.md`.
>
> **Phase 1 note:** the original Citizen scope below includes voice screening.
> The combined-system 10-phase plan parks VoiceGuard / MAYA as a frozen seam;
> see [`PHASE1_ARCHITECTURE_FREEZE.md`](PHASE1_ARCHITECTURE_FREEZE.md) and
> [`adr/ADR-009-voiceguard-frozen-seam.md`](adr/ADR-009-voiceguard-frozen-seam.md).

---

## 1. What RAKSHA is

An AI-native, cross-layer cyber-defence ecosystem for India, built as
**two apps, one doctrine**:

- **RAKSHA Citizen** — voice-clone call screening, multilingual scam-message
  defence, one-tap incident reporting. Runs on an ordinary phone, works
  offline-first, built for low-literacy UX.
- **RAKSHA Sentinel** — infrastructure-facing defence for hospitals, payment
  and identity platforms, cloud and AI-agent estates. Endpoint / Identity /
  Cloud-Data / AI-Agent shields, one attack graph, counterfactual
  minimum-disruption containment, deterministic safety Governor, hash-chained
  evidence ledger.

Red-team: **RAAVAN** — ten-technique AI adversary, **sandbox-only**, used to
prove the defence on stage and in CI. Never pointed at real systems.

The name: **Raksha** (रक्षा) = protection/defence. The stage story: RAAVAN
(ten heads) vs RAKSHA — but all stage copy follows the serious
critical-infrastructure register in `PROBLEM_STATEMENT.md`. Mythology in the
*demo theatre*, advisory gravity in the *substance*.

## 2. Who it serves and why now

India's digital economy is the most-attacked major economy. Citizens are
drained by AI-personalized fraud; critical estates (AIIMS-class hospitals,
payment rails, identity platforms) are encrypted or exfiltrated by AI-driven
crews; the newest vector is the AI agent itself — a poisoned document that
makes a helpful assistant into an unauthorized insider with perfect
credentials. Existing tools fire independent alerts; nobody reconstructs the
campaign; nobody simulates the containment before acting. See
`PROBLEM_STATEMENT.md` for the full articulation and the verification
checklist. **No number may be quoted without its source.**

## 3. Lineage — what already exists in this repository

This repo contains **EIGENSHIELD v2.0 → v2.1 FORTRESS** (`eigenshield-v2/`,
PR #1), a runnable, test-covered 4-plane reference defence build (23 → 34
tests, 6 demos, hash-chained ledger). RAKSHA is its successor and reuses
its battle-tested parts. Nothing below is aspirational vapor — it runs.

| eigenshield-v2 asset | path | RAKSHA destination |
| --- | --- | --- |
| 10-tool allowlist Governor + FIDO2 gate + crown-jewel lock | `governor/policy_engine.py`, `governor/watchdog.py` | Sentinel **Governor** (hard constraints for all autonomous action) |
| N-version TCB twins (fail-closed cross-check) | `fortress/tcb_core.py`, `fortress/tcb_mirror.py` | Governor integrity lineage; also used by CI gates |
| Hash-chained SHA-256 audit ledger + HMAC side anchor | `governor/audit_ledger.py`, `fortress/ledger_anchor.py` | Sentinel **evidence ledger** (prosecution-grade chain of custody) |
| Zero-trust sanitizer + HMAC-signed telemetry + replay defense | `bus/sanitizer.py`, `fortress/telemetry_mac.py` | Both apps: untrusted input normalization + signed evidence |
| Percolation containment (NetworkX, ρ-criticality) | `reflexes/ring4_network_healing/` | Sentinel **containment engine** core |
| Page-Curve ransomware parity traps | `reflexes/ring3_endpoint_silicon/` | Sentinel **Endpoint shield** ransomware trap |
| Bragg/Fiedler injection gates | `reflexes/ring2_ai_defense/` | Architectural lineage for input screening. The shipped Citizen **MessageGuard** is deterministic regex rules, not embeddings or a trained model |
| Rank-1 botnet condensation detector | `reflexes/ring1_perimeter_identity/` | Sentinel **Identity shield** (botnet/session drift) |
| Lyapunov jailbreak steering clamp | `reflexes/ring2_ai_defense/` | Sentinel **AI-Agent shield** (agent behavioral bounds) |
| Inter-organ N-version resilience doctrine | `fortress/` | Whole-architecture principle (see `AI_HANDOFF.md` rules) |
| 5-act demo harness + breach drills | `simulator/` | Demo theatre patterns; RAAVAN harness extends this |
| Contract discipline | `docs/INTERFACE_CONTRACT.md` | Both apps' integration seams |

What does **not** port: the hackathon stage framing, "physics" branding,
unverified math claims, and anything without tests. RAKSHA replaces
speculative claims with measured detection (see `BUILD_GUIDE.md` §6).

## 4. Doctrine (the five rules that outrank every other opinion)

1. **Minimum disruption, always.** Containment must be provably minimal:
   disconnect the attacker, preserve legitimate service. "Shut it all down"
   is a failure mode, not a control.
2. **Fail closed.** Any uncertainty, disagreement, tamper-signal or missing
   human authorization ⇒ the action does not happen. No silent downgrades.
3. **Human sovereignty.** Tier-0 assets (ICU, payment switching, identity
   roots) can only be acted on with verified human step-up. AI can propose;
   only the deterministic Governor disposes — and it can be overridden only
   by a human, never by another AI.
4. **Evidence by construction.** Every detection, decision and action lands
   in the ledger. If it isn't logged, it didn't happen.
5. **Honesty over theatre.** Measured numbers only; limits published; stage
   claims verifiable. The project that reports its failures credibly is the
   one worth deploying.

## 5. Verified-facts discipline

| Claim in play | Status | Source action needed |
| --- | --- | --- |
| Cyber-fraud 2025: 24,02,579 complaints; ₹22,495 crore | **USER-SUPPLIED, UNVERIFIED** | PIB release (MeitY/MHA) — pull before stage use |
| 2024 losses ₹22,845 crore, +206% YoY | **USER-SUPPLIED, UNVERIFIED** | PIB/MHA 2024 report |
| CERT-In Oct 2026 AI-agent advisory | **USER-SUPPLIED, UNVERIFIED** | cert-in.org.in advisory number + date |
| AIIMS Delhi ransomware, Nov 2022 | **Well-reported public event** | Use cautiously; cite press, not "two weeks" precision |
| Digital-arrest scam wave (voice-clone KYC) | **Well-reported public phenomenon** | PIB/MeitY 2024–26 communications; no unverified ₹ figure |
| Section 70/70A IT Act, NCIIPC | **Stable law fact** | MeitY — fine to state |
| IT/OT hospital threat modelling | **Engineering inference** | Present as analysis, not incident |

Rule for every doc in this directory: a number without a source tag is a
bug. Fix it on sight.

## 6. Constraints

- **Everything runs locally.** Ollama + Python. "Works in a district hospital
  with no internet" is a requirement, not a slogan.
- **Two apps in parallel** by construction — separate code, separate UX, one
  shared spine (`CONSTANTS`, attack-graph schema, evidence ledger format).
- **No live weapons.** RAAVAN exists in sandboxes, simulators and fixtures.
  CI never has real credentials, real PII, real hospital networks.
- **India-first UX.** Citizen app: multilingual (hi/te/en at minimum), icon-
  and voice-forward; Sentinel UI: SOC-console density.
- **Budget realism.** District hospitals have one IT generalist, not a SOC.
  Install must be `docker compose up` or a single binary story eventually.

## 7. Glossary

| Term | Meaning |
| --- | --- |
| Attack graph | Live temporal graph: users, devices, agents, tokens, services, data assets + typed edges |
| Campaign | Attack chain reconstructed as one identity across layers/time |
| Containment (counterfactual) | Solved cut set A: `Reach_{G−A}(attacker, critical)=∅` minimizing cost + disruption + recovery risk |
| Governor | Deterministic policy engine; sole authority below human step-up for Tier-0 actions |
| Canary / token trap | Planted early-warning assets (doc, credential); touch ⇒ high-confidence signal |
| Tier-0 asset | ICU/life-safety, payment switching, identity roots; untouchable without verified human |
| RAAVAN | Sandboxed red-team agent, 10 techniques; never leaves the lab |
| FORTRESS | v2.1 resilience doctrine: signed evidence, N-version checks, tripwire, fail-closed |
| Verified evidence | Telemetry carrying valid producer signature; unsigned ⇒ visible but inert |
| Digital arrest (scam class) | Voice-clone impersonation forcing fake "arrest" payments; India-specific mass fraud |

## 8. The open questions (park them here, not in code)

1. Citizen app form factor for pilots — PWA on Android vs native (default: PWA).
2. Sentinel pilot target for the stage demo — simulated hospital+VLAN only until a real estate signs.
3. Cloud vs on-prem reference deployment — both docs exist; pick per pilot.
4. Which eBPF/LSM work is honest to show live vs dry-run (default: dry-run).
5. Data-sharing between Citizen app telemetry and national helpline 1930 — legal review before any real data leaves a device.
