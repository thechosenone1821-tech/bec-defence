# RAKSHA — Problem Statement

> **Status:** Final draft for stage/PRD use pending verification of tagged figures.
> **Last updated:** 2026-11-20 · [VERIFY] = must be checked against the primary
> source before appearing on stage, in slides, or in press.

---

## Part I — Formal problem statement (advisory register)

**RAKSHA/2026/01 — India's critical digital systems and its citizens are under
continuous, AI-accelerated attack, and no integrated, layered, minimum-
disruption defence exists.**

### 1. What is at stake

India runs its economy, healthcare, electricity, payments settlement, logistics
and public administration on connected digital infrastructure. Attacks on
these systems are no longer nuisance crime. They strike **protected systems** —
infrastructure designated critical under Section 70 of the IT Act, 2000, overseen
by NCIIPC — and they reach every layer of society at the same time:

- **Healthcare and life safety.** Hospitals have been encrypted mid-treatment
  (most recently and publicly, AIIMS Delhi, November 2022 — clinical services
  disrupted for days, with workarounds on paper). A defender that can only
  "block everything" is itself a danger to the ICU.
- **Payments and financial rails.** The national payments system moves daily
  commerce. Per figures cited in this project's brief: 24,02,579 financial
  cyber-fraud complaints and ₹22,495 crore in reported amounts for 2025
  [PIB — **VERIFY**]; 2024 losses cited at ₹22,845 crore, up 206%
  year-on-year [**VERIFY**].
- **The state and its citizens.** Voice-clone extortion impersonating police
  and investigative officers ("digital arrest"), AI-personalized phishing and
  UPI mule networks. CERT-In's October 2026 advisory is said to document
  AI agents exceeding their assigned authorisations on live systems of Indian
  organisations, alongside agentic offensive tooling in financially motivated
  intrusions [CERT-In — **VERIFY advisory number and date**].
- **The AI layer itself.** AI agents with legitimate tool access read
  documents, call APIs and move money. One injected instruction inside a
  poisoned document can convert an authorized assistant into an unauthorized
  actor — inside the victim's own network, with the victim's own
  permissions and audit trail.

### 2. Why the current posture fails

| Gap | Consequence |
| --- | --- |
| Fragmented tooling (EDR, IAM, CASB, email, AI governance) | A multi-stage campaign looks like five minor alerts; no one stops it as one attack |
| Human-speed triage | Automation scales attacker effort; correlation happens after exfiltration |
| Binary response levers | "Block" or "shut down the whole platform" — both are losses when it's an ICU or a payment switch |
| No citizen-layer immunity | The phone — the actual front door of most Indian cybercrime — has no defensive infrastructure at all |
| No counterfactual planning | Defences act before simulating side-effects; legitimate services die with the attack path |

### 3. What an answer must do

One defence fabric — from the citizen's phone to the hospital's ICU VLAN to
national payment and identity infrastructure — that:

1. Sees attacks spanning layers as **single campaigns** (one attack graph,
   one campaign identity, one evidence ledger).
2. Chooses the **smallest set of defensive actions** that provably
   disconnects the attacker from critical assets
   (`Reach_{G−A}(Attacker, Critical) = ∅`), weighting intervention cost,
   disruption and recovery risk.
3. Executes under **deterministic safety constraints** — Tier-0 cuts are
   structurally impossible without a verified human step-up, regardless of
   what any AI proposes.
4. **Recovers** services measurably faster than isolation-first response.
5. Works for a **district hospital with intermittent internet** and for a
   national payment operator — same doctrine, different scale.

### 4. What RAKSHA is

- **RAKSHA Citizen** — citizen-facing: on-device voice-clone screening of
  calls, multilingual scam-message defence, one-tap reporting into the
  shared graph. For the ordinary Indian phone.
- **RAKSHA Sentinel** — infrastructure-facing: Endpoint, Identity, Cloud/Data
  and AI-Agent shields on one attack graph; counterfactual minimum-
  disruption containment; a deterministic safety Governor; hash-chained
  forensic evidence.

Shared spine: **attack graph · campaign identity · evidence ledger · Governor.**
Red-team: **RAAVAN**, a ten-technique AI adversary, sandbox-only.

### 5. Scope truth

RAKSHA is a stage-grade reference build, not an audited national product.
Autonomous responses are dry-run/sandboxed in this release; measurement is
real; marketing is not. Limits are documented, not buried.

---

## Part II — The 90-second problem statement (spoken)

> Every day in India, an attack no human army can out-run walks in through a
> phone call, a poisoned invoice, an AI agent doing its job a little too
> well — and it ends inside a hospital, a payment switch, or a citizen's
> life savings.
>
> Indians reported cyber-fraud losses measured in the tens of thousands of
> crores last year [VERIFY]. AIIMS Delhi was held hostage for days. CERT-In
> has now documented AI agents exceeding their authorisation on live Indian
> systems. The attacker is AI. The industry serving the attacker is AI.
> And our defence is a human reading alerts at midnight.
>
> This is not a crime problem anymore. This is an infrastructure problem —
> healthcare infrastructure, payment infrastructure, identity infrastructure,
> national infrastructure. When those fail, the failure is measured in
> bodies, not inconvenience.
>
> What India has never had is an immune system: one fabric, from the
> grandmother's handset to the ICU network — that sees the whole attack as
> one attack, and cuts it without cutting the heart it protects.
>
> That is what we built. RAKSHA. Two apps. One doctrine.

---

## Verification checklist (do before any stage/press use)

- [ ] Cyber-fraud complaints & crore figures — PIB release for 2025, and the 2024 baseline.
- [ ] ₹22,845 crore / 206% YoY figure — primary source.
- [ ] CERT-In October 2026 advisory — number, date, exact claims (AI agents exceeding authorisation).
- [ ] AIIMS Delhi — incident date and duration of disruption.
- [ ] Section 70 / Section 70A IT Act, 2000 + NCIIPC designation role.
- [ ] Any "digital arrest" loss figure before citing one.

## Non-negotiable stage claims

1. No number above appears on stage unverified.
2. The Act-2 live containment is binary: it cuts visibly, or we don't claim it.
3. "Critical infrastructure" refers to the simulated hospital + payments VLAN,
   honestly labeled as a simulation until a real pilot signs.
4. Open-source release is a promise, not a marketing line.
