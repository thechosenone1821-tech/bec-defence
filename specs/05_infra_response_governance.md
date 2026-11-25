# PART 5 — INFRA: RESPONSE & GOVERNANCE
## (containment planner · Governor · commander · executor)

> **What this is.** What happens after a detector fires. This is the part that
> makes RAKSHA different from a SIEM: a minimum-disruption containment plan, a
> deterministic safety gate, and a tamper-evident record of every decision.
>
> **Team size.** 2–3 people. **Depends on:** Part 7 (ledger, TCB, graph).
> **This is the research core of the project.**

---

## 1. The chain, in order

```
detections → attack graph → planner proposes a cut → commander ranks options
                                        ↓
                              GOVERNOR (deterministic)
                          allowlist · budgets · crown-jewel · FIDO2
                                        ↓
                              TCB twins must agree
                                        ↓
                              executor (DRY-RUN)
                                        ↓
                                  evidence ledger
```

**Every arrow is a place the action can stop.** That is the design.

---

## 2. The containment planner ✅ built

Given the attacker's apparent position, compute the minimum-disruption cut that
severs reach from the compromised side to every Tier-0 (crown) asset.

```
minimise   J = C + λD + μR + νA
  C = cut size (edges severed)
  D = fraction of non-crown flow severed
  R = mission-critical flow still reachable
  A = severed edges touching Tier-0
constraint reach(seeds → Tier-0) = ∅
```

**Two honest notes:**

1. **It proposes; it never executes.** Three independent locks stand between this
   and any real action.
2. **The optimiser is exhaustive, not clever.** The candidate space is ten
   non-crown edges, so every subset is scored and the best feasible one wins.
   Deterministic, no randomness, no ML. Calling it "AI-optimised" would be a lie.

**All flow numbers are fixture-measured**, derived from the topology's edge
weights. There is no live NetFlow in the sandbox.

---

## 3. The Governor ✅ built

The single most important component in RAKSHA. It contains **no AI**.

| Invariant | Effect |
|---|---|
| 10-tool schema lock | malformed or unlisted tools are dropped, not repaired |
| Crown-jewel lock | the ICU VLAN can **never** be isolated by the AI under any plan |
| Blast-radius budget | max cuts / quarantines / splices per 5 minutes |
| FIDO2 step-up | Tier-0 override requires cryptographic human sign-off |
| Uptime watchdog | force-reverts any change that drops critical uptime below the floor |

**Why a separate part should never bypass it:** the Commander is an LLM. It can be
prompt-injected, confused, or simply wrong. The Governor is a few hundred lines of
deterministic Python a hospital IT generalist can read. If you are contributing to
any part and find yourself writing "temporarily skip the governor here", stop —
that is the one change that makes the whole product unsafe.

---

## 4. The commander ⚠️ fallback only

A local small language model (Ollama, e.g. `qwen3.5:4b`) proposes actions as
grammar-constrained JSON against a 10-tool allowlist. If no local model is
reachable, it **degrades to a deterministic rule engine** and says so in every
response via `commander_mode`.

**Current reality: no model is running. Everything demos through the fallback.**
The "AI commander" on a slide is a rule table until someone pulls a model and
runs it.

### 4.1 What requires model training here

**Nothing needs training — only running.** It is a pre-trained local model. The
work is:

| Task | Effort |
|---|---|
| Pull a model, run it, verify grammar-constrained output | 1 day |
| Build a prompt-injection test suite against the Commander | 1 week |
| Confirm the fallback is never worse than the model on the allowlist | 2 days |

Note the asymmetry with Part 2: there, training is the blocker. Here, **not
training** is the point — a fine-tuned commander would be a *worse* safety story,
and the Governor's determinism is the selling proposition.

---

## 5. The executor ⚠️ dry-run

Every disruptive action returns `dry_run: true`. There is no `os.kill`, no host
isolation, no VLAN change. This is deliberate and must remain until a signed MoU
exists with a pilot site.

When it does become real, it must be the *last* thing to change, behind a
feature flag, with the watchdog tested first.

---

## 6. Build order

1. Governor — **before** the planner, so the planner is never developed against an
   unguarded executor
2. TCB twins + ledger
3. Planner (exhaustive over the fixture topology)
4. Commander + grammar lock
5. Executor (stays dry-run)
6. Adversarial test suite against the Commander

---

## 7. Definition of done

- [x] Tier-0 cut refused without FIDO2, with the refusal in the ledger
- [x] Budgets enforced across a 5-minute window
- [x] Planner produces a reach-empty cut preserving 100% critical weight
- [x] TCB disagreement ⇒ refusal
- [x] Every decision appended to the hash chain
- [ ] A local model actually running and grammar-verified
- [ ] Prompt-injection suite proving the Commander cannot be steered into a
      disallowed tool

---

## 8. Known gaps

1. **No real model running** — fallback only.
2. **Executor is simulated**, so "we blocked it" always means "we would have".
3. **Thresholds and weights (λ, μ, ν) are hand-chosen**, not tuned against
   outcomes.
4. **No adversarial testing of the Commander** — nobody has tried to jailbreak it
   into proposing a crown-jewel cut. The Governor should catch it; that has not
   been proven.
