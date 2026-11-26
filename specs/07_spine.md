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
| **Governor** | Deterministic policy: 10-tool allowlist, crown-jewel lock, blast-radius budgets, FIDO2 step-up | ✅ built (crown-jewel lock **fixed** this part — it did not cover service ids) |
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

All seven were checked against the real code in this part's execution log (below).
Six were already true. **Box 4 was false**, and the fix is in `spine/governor.py`
and both TCB twins.

- [x] An unsigned event is stored and provably inert — `TestBox1UnsignedIsInert`.
      Inert means three things and all three are tested: accepted, does not build
      graph edges, does not move a budget. A post-signature edit counts as unsigned.
- [x] A signed event reaches the graph and appears in `/api/state` — `TestBox2SignedReachesTheGraph`.
- [x] The planner proposes a cut; the Governor can refuse it; both appear in the ledger
      — `TestBox3PlannerAndGovernor`. Same planner, three dispositions
      (approved / blocked / infeasible), and the refusal carries its reasons into
      the ledger, not just its verdict.
- [x] A Tier-0 cut is refused **without** human step-up, and the refusal is in the ledger
      — `TestBox4Tier0`. ⚠️ **This box was false until this part.** The lock matched
      VLAN and host ids only, so `set_service_readonly(SVC_COLDCHAIN)` was APPROVED
      while the host it runs on was BLOCKED. Fixed in the Governor and in both TCB
      twins; service ids now resolve through the topology to their owning host.
- [x] `ledger_cli verify` passes after a full campaign — `TestBox5LedgerVerify`.
      Also tested the other way: editing a record breaks verification and the CLI
      exits 2.
- [x] One citizen report and one organ event share one `campaign_id` — `TestBox6CampaignFusion`.
      ⚠️ Requires the operator to supply the `case_id` fusion token. Without it the
      two events correctly do **not** fuse, and a test pins that so the limit cannot
      later be mistaken for a bug.
- [x] Two TCB twins disagree ⇒ action refused — `TestBox7TwinVeto`. A twin that
      raises also fails closed, with a stated reason.

---

## 6. What this part does **not** do

- It does not detect anything. Detection lives in Parts 1–6.
- It does not execute anything real.
- It does not have a UI. Part 6 owns the console.
- It cannot be split further. If you are tempted to split the Governor out,
  read §2.2 again.

---

# Execution log — the seven DoD boxes, earned one at a time

**Status: six earned, one earned with a defect found and fixed on the way.**
Part 7 is structured differently from Parts 4–6: it is a contract with a
seven-item Definition of done, not a phase table. So the work here was to prove
each box against the real code rather than to build new phases.

Every box below was driven through the real path — a signed POST at the bus, the
real Governor, the real ledger — not by calling an internal helper and checking
it returned something. `tests/test_part7_spine_dod.py` holds 39 tests, one
group per box, and **10 mutants were killed** against it.

## Box 1 — an unsigned event is stored and provably inert ✅

    unsigned POST -> {'accepted': 1, 'received': 1, 'unverified': 1}
    fortress.unverified_held: 1
    graph node_count: UNCHANGED
    blast-radius budget: UNCHANGED

"Stored but inert" is three separate claims and all three are tested: it is
accepted, it does **not** build graph edges, and it does **not** move a budget.
A stored event that still builds edges is visible *and* dangerous, which is
precisely the failure the MAC exists to prevent.

A post-signature edit is also treated as unsigned — the tamper test changed
`severity` after signing and the bus counted it unverified rather than verified.

## Box 2 — a signed event reaches the graph and appears in `/api/state` ✅

    signed POST -> {'accepted': 1, 'unverified': 0}
    graph: node_count 2, edge_count 1
    recent_events: [('sig-1', 'ENDPOINT_PAGE_CURVE')]

## Box 3 — the planner proposes; the Governor can refuse; both in the ledger ✅

The same planner, three dispositions:

| Seed VLAN | Planner | Governor | Why |
|---|---|---|---|
| `VLAN_GUEST_WIFI` | `PLAN_PROPOSED` | `APPROVED` | 91.18 % flow preserved |
| `VLAN_CORP_IT` | `PLAN_PROPOSED` | **`BLOCKED`** | references `VLAN_CORE_AUTH` **and** 55.56 % preserved flow < 90 % floor |
| `VLAN_CORE_DB` | `INFEASIBLE` | — | no cut meets the floor |

Both the approval and the refusal are appended to the ledger, and the refusal
carries its reasons into it:

    governor_decision | BLOCKED | ["tier-0 protected asset(s) referenced: ..."]

**A refusal with no reason in the ledger is not an audit trail**, so there is a
test for the reason specifically, not just the decision.

## Box 4 — a Tier-0 cut is refused without human step-up ❌ → ✅ **defect found and fixed**

This box was **false** when I started checking it, and not in a subtle way.

The crown-jewel lock matched Tier-0 **VLAN ids and host ids** only. Service ids
were not in the protected set at all. So:

| Action | Result |
|---|---|
| `set_service_readonly(HOST_BLOODBANK_CTRL_01)` | **BLOCKED** |
| `set_service_readonly(SVC_COLDCHAIN)` | **APPROVED** ← runs on that exact host |
| `deploy_muts_ebpf_shield(HOST_ER_DB_PRIMARY)` | **BLOCKED** |
| `deploy_muts_ebpf_shield(SVC_SSO)` | **APPROVED** |

`SVC_COLDCHAIN` runs on `HOST_BLOODBANK_CTRL_01`, which the policy lists as
Tier-0. The Governor's §2.2 claim — *"no model, however compromised, can isolate
the ICU"* — was false through the service path. The lock could be evaded by
renaming the target, which means it was not a lock.

**The fix** resolves service → host through the topology the rest of the system
already reads, and matches three id spaces instead of two:

* VLAN ids, host ids (as before)
* **service ids, resolved to their owning host**

The topology is read, never hardcoded: a topology edit must not require a
Governor edit, and a hardcoded map would silently rot.

**The same hole existed in both TCB twins** — they each matched VLAN and host
ids. That matters more than the Governor bug: the twins are the *third* lock, and
they were blind in the same place. Both are patched, in their own idiom rather
than by sharing code, because they exist to disagree when one is wrong — a
shared resolver would let a single edit move both.

The fix does not over-block: `APP_SRV_07` on a normal host still approves.

    SVC_COLDCHAIN  -> BLOCKED: ["tier-0 protected asset(s) referenced:
                                ['SVC_COLDCHAIN (on tier-0 host HOST_BLOODBANK_CTRL_01)']"]
    APP_SRV_07     -> APPROVED: ['all invariants satisfied']

Human step-up still works, and a fabricated one does not: `"VERIFIED"` approves,
`"yes please"` is refused by the Governor's own check.

## Box 5 — `ledger_cli verify` passes after a full campaign ✅

    verify: {'valid': True, 'entries': 12}

Tamper-evidence is tested, not assumed: editing one record's payload breaks
verification, and the CLI returns **exit code 2** on a broken chain. An empty
ledger verifies rather than erroring — empty is not corrupt.

## Box 6 — one citizen report and one organ event share one `campaign_id` ✅

The mechanism is the `case_id` fusion key: the sanitizer digests it to a stable
opaque token, so the same case on two rails lands on one graph node.

    citizen -> entities: {'case_id': 'sha256:6df39c00d1e0c3261f3dfbb2ff672151'}
    infra   -> entities: {'host_id': 'HOST_042', 'case_id': 'sha256:6df39c00d1e0c326...'}
    same token: True   ->  campaigns: 1, size 2

**The honest limit, pinned by a test so it cannot be mistaken for a bug later:**
correlation is entity overlap. A citizen report with **no** `case_id` cannot be
joined to a network event by this mechanism, and the test asserts that it does
not try. §1's "⚠️ partial" is accurate for that reason — the fusion works, but it
requires the operator to supply the linking token.

A bug in my own first version of this test: I used `event_id` values `"a"` and
`"b"`, which fail the sanitizer's `^[A-Za-z0-9_-]{4,64}$` rule and are **replaced
with random ids** — so the campaign hash differed between runs and I briefly
thought the correlator was nondeterministic. It is deterministic; the test was
wrong. Two tests now pin that behaviour in both directions.

## Box 7 — two TCB twins disagree ⇒ action refused ✅

    forced mirror BLOCKED -> core=APPROVED mirror=BLOCKED
    decision: BLOCKED
    reason: FORTRESS TCB disagreement (core=APPROVED mirror=BLOCKED) — fail closed

A twin that **raises** also fails closed, and the failure is recorded as a stated
reason rather than silence.

## §2.6 — no unverified number ✅

`containment.propose()` returns its figures with a note saying they are
fixture-measured on the synthetic graph and not a production SLO, and a test
asserts no payload claims an assumed accuracy figure.

## Mutation: 10 mutants, 10 killed — after three survivors taught me something

The first run killed 7 of 10. **Every survivor was a weak test of mine, not a
weak fix**, and two of them were the same weakness:

1. **S7-M1 (Governor's own tier-0 check reverted)** survived because the TCB
   twins independently block the same action. My test asserted the final
   `decision`, which the twins deliver either way — so it could not tell the
   Governor's guard from the twins' guard. A defence-in-depth claim needs one
   test per layer, or "redundant" is an assumption. There is now a test that
   calls the Governor's own check directly.
2. **S7-M7 (`human_stepup` accepting any non-empty string)** survived for the
   same reason. The distinguishing observable turned out to be `fortress_tcb`:
   with the mutated Governor the refusal is `tcb_override` (the twins caught it);
   with the real one it is `ok` (the Governor caught it).
3. **S7-M5** was my own bad mutant — `except Exception` appears twice in the
   Governor and I patched the wrong one.

This is the third phase in a row where the mutation run found a test that could
not fail. The pattern is consistent enough to state plainly: **a test that
asserts a final boolean is not testing the layer it names.**

## Suite state

| Check | Result |
|---|---|
| `pytest tests/` | **1218 passed, 1 skipped, 1 xfailed** |
| `pytest tests/ --collect-only` | **1220 collected** |
| `test_part7_spine_dod.py` | 39 passed |
| `node --test tests/*.test.js` | **90 pass, 0 fail** |
| `boot_manifest --check` | **INTEGRITY OK — 4 files** |

1179 + 39 = 1218 and 1181 + 39 = 1220. Both reconcile with Part 4 Phase 7.

## What this part still does not have

* **The Commander is fallback-only.** `SLMClient().is_available()` returns
  `False` here — there is no local model — and the orchestrator reports
  `commander_mode: fallback_rules`. §1's "⚠️ fallback only" is accurate. The
  model-driven path is unexercised in this environment, so nothing here proves
  it works.
* **The executor is dry-run by construction.** That is the §1 promise, not a gap.
* **Box 6 needs an operator-supplied `case_id`.** Automatic fusion across the
  two apps — deciding that report X is about the same person as event Y — is not
  implemented and the test says so.
* **No UI.** Part 6 owns the console.
