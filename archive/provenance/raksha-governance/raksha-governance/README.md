# RAKSHA Governance — Response & Governance (Part 5), Final Consolidated Build

> **The AI proposes, the Governor disposes.** No part of RAKSHA may create a
> path around the Governor. The Governor was built **first**, so nothing is
> ever developed against an unguarded executor. Every destructive action in
> this build is **dry-run**: "we blocked it" actually means "we would have
> blocked it".

This repository is the **final consolidated form** of the governance build:
the four independently-workable parts of Part 5 merged into one deterministic,
fully tested Python package.

| Part | Owns | Status | Modules |
|---|---|---|---|
| **1 — Governor safety core** | 10-tool schema lock, crown-jewel lock, blast-radius budgets, FIDO2 step-up, uptime watchdog, TCB twin arbitration, fail-closed pipeline | **BUILT** | `governor.py` `tools.py` `decisions.py` `policy.py` `budgets.py` `fido2.py` `tcb.py` `watchdog.py` `fixtures.py` |
| **2 — Evidence (reference)** | tamper-evident hash chain, JSONL export; Part 2 hardening swaps the implementation, not the interface | **BUILT (reference)** | `ledger.py` |
| **3 — Containment planner** | exhaustive minimum-disruption cut over the fixture topology, `J = C + λD + μR + νA`, constraint `reach(seeds → Tier-0) = ∅` | **BUILT** | `planner.py` |
| **4 — Commander + dry-run executor** | deterministic fallback rules engine, Ollama adapter (`commander_mode` in every response), feature-flag-ready dry-run executor, Governor-side injection suite | **BUILT** (model runtime task open) | `commander.py` `executor.py` |

**82 tests passing.** Run everything below.

---

## Quickstart

```bash
pip install -r requirements.txt        # cryptography, pytest
python -m pytest tests -q              # 82 tests
python demo.py                         # full pipeline + adversarial hour
```

The demo writes a JSONL evidence export to `demo_state/evidence.jsonl`.

## Pipeline

```
incident ──► Commander ──► Containment Planner ──► GOVERNOR ──► Dry-run Executor
            (AI optional,      (exhaustive,           (five invariants,   (simulated,
             rules default)     deterministic)         fail-closed)        always)
                                                      │
                                                      └──► evidence hash chain
```

The commander proposes raw action envelopes; the planner proposes raw
`edge.sever` envelopes. **Every** proposal is judged per-action by the
Governor — nothing moves without an `ALLOW`, and the executor refuses to
act on anything else.

## The five invariants (all enforced, in fixed order)

| # | Invariant | Where | Proven by |
|---|---|---|---|
| I1 | **10-tool schema lock** — closed world, drop never repair, targets must exist | `tools.py` | `test_tools.py` |
| I2 | **Crown-jewel lock** — the ICU VLAN is never disrupted; **no sign-off can buy it** | `tcb.py` (policy), `governor.py` | `test_crown_lock.py` |
| I3 | **Blast-radius budgets** — max cuts / quarantines / splices per rolling 5-min window; refusals consume nothing | `budgets.py` | `test_budgets.py` |
| I4 | **FIDO2 step-up** — Tier-0 actions parked (`ESCALATE`) until a fresh, replay-proof, action-bound Ed25519 assertion arrives | `fido2.py`, `governor.py` | `test_fido2.py` |
| I5 | **Uptime watchdog** — projected critical uptime must stay above the floor (no override exists); below floor ⇒ force-revert of the latest change, or `HUMAN_REQUIRED` | `watchdog.py`, `policy.py` | `test_watchdog.py` |

Plus the TCB rule: the same action runs through **two independently written
twins** (`TwinA` rule-table, `TwinB` independent control flow). Any
disagreement — including a metadata disagreement — is `DENY/TCB_DISAGREEMENT`
(`test_tcb.py`). Fail-closed rule: any internal error anywhere in the pipeline
produces `DENY/INTERNAL_GUARD_FAILURE` and is still recorded
(`test_fail_closed.py`).

## Containment planner (Part 3)

```
minimise   J = C + λD + μR + νA        λ=2, μ=10, ν=8  (hand-picked — known gap)
  C = cut size                        D = non-Tier-0 candidate flow severed (share)
  R = critical flow still seed-reachable        A = severed edges touching Tier-0
constraint  reach(seeds → Tier-0) = ∅
```

The candidate space is the fixture's **ten** cuttable non-crown edges the
twins would not outright refuse (crown-adjacent edges are excluded by the
crown lock; floor-fatal edges excluded because no sign-off can buy the floor;
sign-off-requiring edges stay in the space and are priced by `ν·A`). The
optimiser is **exhaustive over all 2^10 subsets** — deterministic, no ML, no
randomness. For the demo incident (seeds `prn-01` + `ws-11`, lateral movement
across `x1/x2/x3`) the unique optimum is `{e_prn1, e_ws, x2, x3}`,
`J = 4.9375`, zero Tier-0 contact, zero critical flow lost.

**Honesty (binding rule 2):** all flow numbers are fixture measurements
(`fixtures.py`); λ, μ, ν are hand-picked, not yet tuned from outcomes. The
consolidated fixture documents its two deliberate changes in its docstring
(east-west links `x1..x4` added; nurse-call flow `e_ncs` reclassified
non-critical).

## Commander (Part 4)

- `fallback_rules` — deterministic template emitter; incident fields reach
  only inert justification text, never the `tool` name. **Always available.**
- `ollama_local` — adapter for a local model proposing grammar-constrained
  JSON against the same 10-tool allowlist. Wire it by setting
  `RAKSHA_OLLAMA_MODEL` (e.g. `qwen3.5:4b`); unreachable model ⇒ fallback,
  and every response declares its `commander_mode`.
- **Nothing here needs training — only running.** Open runtime items, stated
  plainly in the demo footer: no model was actually run in this build; the
  commander-side injection suite needs that model. The Governor-side suite
  (82 tests) already proves a jailbroken or malformed proposal cannot act
  outside the whitelist.

## Executor (Part 4)

`executor.py` imports **no `os`, no `subprocess`, no sockets** — it cannot
reach a machine by construction. It refuses non-`ALLOW` statuses. Going live
requires, in order: a signed MoU with a pilot site, the feature flag, and the
watchdog proven in drills first. It is the last module that would ever change.

## Evidence ledger (Part 2 interface)

`HashChainLedger.append(...) -> LedgerEntry` and
`HashChainLedger.verify() -> (ok, first_bad_seq | None)`, JSONL export,
optional file sink. Every terminal outcome — allow, deny, escalate, forced
revert, internal failure — lands in the chain before the caller sees it.
Editing one historical entry breaks verification at exactly that sequence
number. The hardened spine (dual write, checkpoints, cross-process budgets,
twins in separate processes) replaces the implementation behind this same
interface — that is governance Part 2's remaining work.

## Known gaps (kept honest, from the spec)

1. **No real model run yet** — commander runs on the deterministic fallback;
   the adapter is shipped and the contract is testable without a model.
2. **Executor is simulation** — by design, until MoU + flag + drill.
3. **λ/μ/ν and budget caps are hand-picked** — not yet tuned from outcomes;
   all live in `planner.py` / `BudgetConfig` and changing them is a
   governance act.
4. **Commander-side adversarial suite** — needs the running model; the
   Governor-side suite already covers the "model misbehaves" cases.
5. **Twins share impact arithmetic** (documented Part-1 scope decision) —
   Part 2 duplicates the math and separates the processes.

## Layout

```
raksha/            the consolidated package (15 modules, ~2.3k lines)
tests/             82 tests: per-invariant suites + planner + commander +
                   executor + end-to-end + fail-closed + DoD scenarios
demo.py            the whole story in one console run
requirements.txt   cryptography, pytest
```

Run the demo. Read `governor.py` — a few hundred lines a hospital IT
generalist can audit. If you ever find yourself writing "temporarily skip
the governor here", stop: that is the one change that makes the whole
product unsafe.
