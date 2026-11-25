# PART 7 — THE SPINE (shared by both apps)

> **What this is.** The single shared core that every other part depends on.
> Part 1–3 (Citizen) and Part 4–6 (Infrastructure) all talk to this, and nothing
> talks to anything else across the boundary.
>
> **Why it is one part and not six.** Campaign correlation, the evidence ledger
> and the Governor are only meaningful if *both* halves write to the same one.
> Splitting them per-app would produce two ledgers that cannot be reconciled and
> two Governors that can disagree — which is exactly the failure this design exists
> to prevent.
>
> **Team size.** 2–3 people. It is the critical path: Parts 1–6 can be developed
> against stubs, but nothing demos end-to-end until this is real.

---

## 1. What the Spine owns

| Component | Responsibility | Real today? |
|---|---|---|
| **Sanitizer + tokenizer** | Normalise untrusted input, HMAC entity keys into stable tokens, scrub injection patterns | ✅ built |
| **Telemetry verify** | Per-event HMAC; unsigned events are *visible but inert* | ✅ built |
| **Telemetry bus** | FastAPI + WebSocket; ingest, buffer, fanout | ✅ built |
| **Attack graph** | Temporal multigraph over Users / Devices / Agents / Tokens / Services / Assets, with typed edges and a 10-minute sliding window | ✅ built |
| **Campaign identity** | Deterministic correlation (entity overlap + temporal kernel) → stable `campaign_id` linking a citizen leg to an infra leg | ⚠️ partial |
| **Evidence ledger** | Append-only, SHA-256 chained, HMAC-anchored | ✅ built |
| **Governor** | Deterministic policy: 10-tool allowlist, crown-jewel lock, blast-radius budgets, FIDO2 step-up | ✅ built |
| **Containment planner** | Minimum-disruption cut, exhaustive over a small graph | ✅ built |
| **Commander** | Local SLM proposes actions; deterministic fallback offline | ⚠️ fallback only |
| **Executor** | Applies approved actions | ⚠️ dry-run by construction |

**That last row is a promise, not an apology.** Nothing in this system touches a
real host. Every action is simulated. It must stay that way until there is a
written MoU with a real pilot site.

---

## 2. The contract every part must honour

These are not style preferences. Each one has a test, and a part that breaks one
does not merge.

### 2.1 Nothing is trusted until it is signed

An event arrives at `POST /api/ingest` with an HMAC. Invalid signature ⇒ the
event is stored for forensics but is **inert**: it cannot move the graph, cannot
trigger the planner, cannot reach the Commander. A missing signature is not a
warning; it is a wall.

### 2.2 The AI proposes, the Governor disposes

Two independent validation passes, deliberately redundant:

1. `orchestrator.validate_action()` — schema lock against the 10-tool allowlist.
2. `governor.evaluate()` — policy, budgets, crown-jewel lock, human step-up.

The Commander cannot execute. The Governor has no AI in it. This is the single
most important invariant in the codebase: **no model, however compromised, can
isolate the ICU.** If you are contributing to any part, do not create a path
around it.

### 2.3 Three locks, never one

Every disruptive action passes: planner → Governor → TCB re-derivation. Test
`test_m5_containment.py` asserts all three. A "temporary" bypass is how
safety systems die.

### 2.4 Fail closed

Any exception in the decision path denies the action. It never approves by
accident. `tcb_core` and `tcb_mirror` are N-version twins that must agree; if
they disagree, the action is refused.

### 2.5 The ledger is the alibi

Every decision — approved, refused, escalated — is appended. The chain is
verifiable with `python -m spine.ledger_cli verify`. If a demo step cannot be
shown in the ledger, it did not happen.

### 2.6 No unverified number

Every figure in a payload is labelled measured or fixture. There is no
"assume 99% accuracy" anywhere. Parts that want to add a metric must add the
harness that produces it, in the same PR.

---

## 3. Interfaces the other six parts code against

```
POST /api/ingest        signed organ event → sanitize → graph → buffer → broadcast
GET  /api/state         current graph + campaign list (poll fallback)
POST /api/containment   run the planner, get a proposal (does NOT execute)
POST /api/orchestrate   run full pipeline: Commander → Governor → executor
WS   /ws/telemetry      live event stream
```

**Citizen side** (Part 1–3) reaches the Spine through the report rail only:
a signed, tokenised report carrying category + verdict band. No audio, no
message text, no phone number. `citizen/api.py` enforces this and
`test_maya_phase5.py::test_no_audio_is_echoed_back` proves it.

**Infrastructure side** (Part 4–6) reaches the Spine through `/api/ingest` with
organ-signed telemetry.

Both land on the same graph. The `campaign_id` is what proves a phone call and a
network intrusion are the same attack.

---

## 4. Build order

1. **Sanitizer + ledger** — smallest pieces, everything else depends on them.
2. **Bus + verify** — get a signed event from a stub organ into a buffer.
3. **Attack graph** — the window and the typed edges.
4. **Governor** — must exist *before* the planner, so the planner is never tested
   against an unguarded executor. Order matters.
5. **Containment planner** — exhaustive over the fixture topology.
6. **Campaign identity** — the fusion that links both apps.
7. **Commander** — last, and optional. Everything works without it.

---

## 5. Definition of done

- [ ] An unsigned event is stored and provably inert
- [ ] A signed event reaches the graph and appears in `/api/state`
- [ ] The planner proposes a cut; the Governor can refuse it; both appear in the ledger
- [ ] A Tier-0 cut is refused **without** human step-up, and the refusal is in the ledger
- [ ] `ledger_cli verify` passes after a full campaign
- [ ] One citizen report and one organ event share one `campaign_id`
- [ ] Two TCB twins disagree ⇒ action refused

---

## 6. What this part does **not** do

- It does not detect anything. Detection lives in Parts 1–6.
- It does not execute anything real.
- It does not have a UI. Part 6 owns the console.
- It cannot be split further. If you are tempted to split the Governor out,
  read §2.2 again.
