# RAKSHA — Architecture

> **Last updated:** 2026-11-26 · **Status:** target architecture; implemented modules are noted in §3.
> Anything marked *(ports eigenshield-v2)* already exists in working form
> under `../eigenshield-v2/` and is listed with paths in `CONTEXT.md §3`.

---

## 1. One-picture view

```text
              CITIZEN LAYER                          INFRASTRUCTURE LAYER
   ┌──────────────────────────────┐      ┌───────────────────────────────────┐
   │  RAKSHA Citizen (app)        │      │  RAKSHA Sentinel (app)            │
   │  ┌─────────┐ ┌─────────────┐ │      │  ┌──────────┐ ┌────────────────┐  │
   │  │VoiceGun.│ │MessageGuard │ │      │  │Endpoint  │ │ Identity       │  │
   │  │(synthetic)│ │(scam scr.) │ │      │  │  Shield   │ │ Shield         │  │
   │  └────┬────┘ └──────┬──────┘ │      │  └────┬─────┘ └───────┬────────┘  │
   │  ┌────▼─────────┐   │        │      │  ┌────▼─────────┐ ┌───▼─────────┐  │
   │  │ Citizen risk │   │        │      │  │ Cloud/Data   │ │ AI-Agent    │  │
   │  │  engine +    │   │        │      │  │ Shield       │ │ Shield      │  │
   │  │  1-tap report│   │        │      │  └────┬─────────┘ └───┬─────────┘  │
   │  └────┬─────────┘   │        │      │       └───────┬────────┘            │
   └───────┼─────────────┼────────┘      └───────────────┼───────────────────┘
           │   signed events                signed events │
           ▼            ▼                                ▼
   ┌──────────────────────────────────────────────────────────────┐
   │              SHARED SPINE (both apps, one schema)             │
   │  attack-graph service · campaign identity · evidence ledger   │
   │  sanitizer/verify · telemetry bus · Governor (deterministic)  │
   └───────────────┬───────────────────────────────┬───────────────┘
                   │              proposals          │
                   ▼                                 ▼
        ┌────────────────────┐            ┌──────────────────────┐
        │  AI COMMANDER      │            │  CONTAINMENT PLANNER │
        │  local SLM, plans  │───────────▶│  min-disruption cut: │
        │  actions           │  options   │  argmin(C+λD+μR) s.t.│
        └────────────────────┘            │  Reach=∅             │
                                          └──────────┬───────────┘
                                                     ▼
                                        ┌─────────────────────────┐
                                        │  GOVERNOR (final + veto)│
                                        │  then Executor (dry-run)│
                                        └─────────────────────────┘
```

RAAVAN (red-team agent, sandbox-only) feeds both layers nothing directly —
it exists to *attack* the sandboxed copies so the defence can be measured.

## 2. The shared spine (both apps)

| Component | Role | Heritage |
| --- | --- | --- |
| Sanitizer + tokenizer | Normalize untrusted input; HMAC tokens; injection scrubbing | `eigenshield-v2/bus/sanitizer.py` |
| Telemetry verify | HMAC per event; unsigned ⇒ visible, inert | `fortress/telemetry_mac.py` |
| Telemetry bus | FastAPI + WS; org→graph ingest; CORS; fanout | `eigenshield-v2/bus/event_server.py` |
| Attack graph | Temporal multigraph: Users / Devices / Agents / Tokens / Services / Assets; typed edges (auth, access, call, read, write, exfil); 10-min sliding window + campaign labels | `bus/entity_graph.py` (evolved) |
| Campaign identity | Deterministic campaign correlation (entity overlap + temporal kernel); stable `campaign_id` | new (Ring-1/Breach-chain logic) |
| Evidence ledger | Append-only JSONL, SHA-256 chain + HMAC anchor | `governor/audit_ledger.py` |
| Governor | Deterministic policy; allowlist; budgets; crown-jewel lock; FIDO2 gate for Tier-0 | `governor/policy_engine.py` |
| Containment planner | Solved cut-set, heuristics first (min-cut), optional ILP; dry-run always in this release | new on `reflexes/ring4_network_healing/` |
| Commander | Local SLM (Ollama) plan proposer; falls back to deterministic rules offline | `commander/orchestrator.py` |

## 3. RAKSHA Citizen — internals

**Form:** offline-first mobile app (PWA on Android default); all inference on-device where feasible; reports are push-signed, anonymous-by-default.

| Module | Function |
| --- | --- |
| **VoiceGuard** | 2-second screening of caller audio streams: MAYA synthetic-speech features and an explicitly labelled synthetic-corpus model. Never uploads audio without consent; `may_claim_clone_detection()` is `False` |
| **MessageGuard** | Implemented v1: deterministic, offline, explainable hi/te/en scam-script detection — UPI collect-requests, KYC/digital-arrest scripts, phishing URLs. Six weighted rule families, `MSG-*` reason codes, 492 hand-authored measurement fixtures; real-world accuracy UNMEASURED. No trained classifier |
| **Citizen Risk Engine** | Combines voice + message + (optional) SMS/UPI-notify signals into one risk verdict with plain-language reasons ("This caller is likely a synthetic voice speaking like a DSP rank officer") |
| **One-tap Report** | Signed, minimal report: verdict, category, redacted entities (tokens only). No raw audio/SMS persisted without explicit consent |
| **Panic button** | Lock the screen, kill known-scam sessions, call 1930/chosen helpline |
| **Family mode** | Likely-next targets (elders, first-time digital users) get stricter defaults, louder warnings |

**Non-goals:** no call recording retention, no IME/keystroke access, no
mandatory account, no silent data exfiltration to any server including ours.

## 4. RAKSHA Sentinel — internals

**Form:** on-prem appliance (Docker Compose) + optional SOC console; kattajn hospital VLAN profile included.

| Shield | Detects | Built on |
| --- | --- | --- |
| **Endpoint** | Ransomware parity traps, anomalous writes, script-injection chains, suspicious child-process trees | Page-Curve traps (Ring 3) + EDR event intake |
| **Identity** | Session replay, impossible travel, privilege jumps, token reuse anomalies, botnet condensation | Ring 1 (BEC/Cookie filters) |
| **Cloud/Data** | Bulk reads, off-hours exports, new egress paths, signed-URL abuse, API-key drift | Cloud audit logs (CloudTrail-class), DLP-lite heuristics |
| **AI-Agent** | Agent tool-call drift vs task intent; injected-context execution; unauthorized data access; canary-doc access | Ring 2 (Lyapunov clamp) + FORTRESS canaries |

The shields emit **verified** events only (signed). The graph fuses them per
campaign. The planner computes the minimal cut. The Governor disposes. The
ledger seals. The watchdog force-reverts anything unwatched.

**Deployment profiles:** `hospital` (ICU VLAN protected, IT VLAN quarantinable),
`payments` (switch isolated from office LAN), `campus` (seed profile for demo).

## 5. Counterfactual containment (the research core)

Given live attack graph G with attacker source s and critical asset set K:

```
A* = argmin_{A ⊆ 𝒜} [ C(A) + λ·D(A) + μ·R(A) ]
s.t. Reach_{G−A}(s, K) = ∅
```

- `𝒜`: candidate defensive actions (revoke token, disable permission, isolate host,
  block egress, quarantine doc, tighten ACL, force re-auth).
- `C`: intervention cost (operator effort, license, breakage risk).
- `D`: disruption (fraction of legitimate flows severed — measured by graph
  difference of the protected mission flows).
- `R`: recovery risk (time-to-restore distribution).
- λ, μ configurable per deployment; `hospital` profile weights life-safety D highest.

**Implementation:** min-cut seeding → local search with hard constraint check;
optional OR-tools ILP for small graphs; always dry-run first; Governor gate.

**Evaluation baselines (all run on the same seeded RAAVAN scenarios):**
none / static-perms / rules-block / RAKSHA. Metrics: attack success rate,
time-to-contain, % sensitive data reached pre-containment, false-positive
containment rate, % legitimate flows preserved (target ≥ 90%), recovery time.

## 6. RAAVAN — the adversary (scoped)

Ten techniques, fixed and versioned in `raavan/playbook.yaml` (to be written):
voice-clone vishing, UPI mule drain, doc-borne indirect injection, vendor-phish
lateral move, ransomware encryptor, cloud token theft, bulk exfil, agent
permission abuse, living-off-the-land persist, canary-credential fishing.
Executes only inside sandboxes seeded by the eval harness. Emits a full
kill-chain transcript to the ledger for scoring.

## 7. Data flow — one campaign, end to end

1. Victim gets cloned call → VoiceGuard verdict → Citizen report (signed,
   tokenized) enters the graph.
2. Same campaign's vendor-phish payload lands on Sentinel's Endpoint shield
   → Ring-3 trap fires → verified event.
3. Campaign correlator fuses Citizen + Endpoint (shared doc_hash/token overlap).
4. Planner proposes `{quarantine_doc, revoke_token, isolate_host}` vs alternatives;
   Governor approves cut A*; Watchdog holds rollback.
5. Executor (dry-run) "performs" actions; dashboard shows attack path being
   severed; ICU stays green; ₹-loss counter freezes; ledger lists every step.

## 8. Surfaces

- Citizen app UI (owner: product/design pair — not this doc set)
- Sentinel SOC console: WS `event | action_plan | governor_decision | tool_result`
  (contract v1.0.0 + v2.1 addendum in `eigenshield-v2/docs/INTERFACE_CONTRACT.md`)
- Both apps: `/api/health`, `/api/state`, `/api/ingest`, `/api/orchestrate`

## 9. Explicit non-goals

- No real-world offensive tooling leaves the sandbox. Ever.
- No universal "AI police" — Governor can only veto/limit, never initiate
  offensive actions.
- No mass surveillance features anywhere in Citizen.
- No closed-source dependency that district hospitals cannot audit.
