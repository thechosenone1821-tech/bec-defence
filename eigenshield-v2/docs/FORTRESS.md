# EIGENSHIELD FORTRESS — v2.1 Hardening Layer

**Design premise.** In v2.0 every guarantee ultimately rested on one process
behaving: one Governor, one policy file, one ledger, one Python interpreter.
FORTRESS removes single points of trust. No *single* compromise — a hijacked
AI, a forged telemetry feed, a mis-merged config, a lying Governor, even a
defect in one implementation of the decision logic — may produce a Tier-0
catastrophe. Every failure path resolves to **fail closed**, never fail open.

FORTRESS is additive. It does not replace the four planes; it wraps them in a
verification shell and adds an independent decision lineage.

---

## 1. Threat model — what we defend against

| # | Attacker capability | Neutralized by |
|---|--------------------|----------------|
| T1 | Forged/spoofed telemetry injected into the bus | Organ-signed evidence (`fortress/telemetry_mac.py`); the Commander never sees unsigned telemetry; `/api/orchestrate` returns `HELD_UNVERIFIED_EVIDENCE` |
| T2 | Replay of genuine captured organ events | `SeenEventCache` (600 s sliding window, constant-work lookup) drops replays before they reach the graph or the AI |
| T3 | Hijacked/prompt-injected Commander exfiltrating context or steering actions | Canary tokens in the Commander context (`fortress/canaries.py`); any appearance in output ⇒ all actions dropped + `canary_hit` tripwire |
| T4 | Prompt-injection storm / probing the Governor (many blocked requests) | `fortress/tripwire.py` — freeze AI path after ≥4 BLOCKED (or ≥3 injection markers, or ≥2 unverified-disruptive) inside 60 s; reset needs a human step-up |
| T5 | Governor bugs / subtle logic defects in one decision implementation | N-version re-derivation: `fortress/tcb_core.py` + `fortress/tcb_mirror.py` decide independently; **any disagreement ⇒ BLOCKED** |
| T6 | Policy/config tampering (policy.yaml, tool schemas, system prompt, topology) | `fortress/boot_manifest.py` — SHA-256 pins; tamper ⇒ boot refused (`ConfigIntegrityError`); runtime status exposed at `/api/state` (`config_integrity`) |
| T7 | Retroactive edit/truncation of the audit ledger | `fortress/ledger_anchor.py` — HMAC-sealed `(seq, head_hash)` side file; `verify()` cross-checks chain length and head |
| T8 | Core bug / weird-input DoS in the decision path itself | TCB invariants run on a **pure-stdlib, allocation-bounded, non-recursive** code path (`tcb_core`); `decide()` never raises; optional subprocess isolation via `fortress/sandbox_runner.py` (rlimits, `python -I`) |
| T9 | Insider organ emitting insane-but-signed garbage | The Governor's stateful invariants (blast-radius budgets, FIDO2 gate, crown-jewel lock) still apply to *verified* events; signing proves origin, not wisdom |

Out of scope (honest limits — see §5): a fully root-compromised host, an
attacker who holds BOTH the telemetry key and the operator keys, and
physically induced sensor manipulation.

## 2. The layers

```text
organ ──sign──▶ bus ──verify/drop replay──▶ buffer ──verified only──▶ Commander ──plan──▶ Governor
                     │                        (canary-tagged context)        │                 │
                     │                                                          │                 ├─ engine invariants
                     │                                                          │                 ├─ TCB-core  (independent)
                     ▼                                                          ▼                 ├─ TCB-mirror (independent)
              /api/state (quarantine counters, tripwire)            canary scan of output    all must agree → APPROVED
                                                                        (hit ⇒ drop all)      else BLOCKED (+tcb_mismatch trip)
                                                                                                                │
                                                                              ledger append ◀── audit ◀────────┘
                                                                                    + anchor pin (seq, head)
```

### fortress/tcb_core.py — decision, lineage 1
The stateless Governor invariants re-derived from the spec: 10-tool allowlist,
argument shape (≤8 KB, ≤512 JSON nodes, ≤32 depth, ≤2048-char strings),
required args, bool/int/enum/range checks, `preserve_tier0_vlans=true`,
crown-jewel lock (any Tier-0 identifier anywhere in the argument blob ⇒
BLOCKED unless human step-up). Pure `json`/`hashlib`/`hmac`/`re`-class code,
no recursion, explicit stack, bounded loops — designed to be auditable in
about fifteen minutes.

### fortress/tcb_mirror.py — decision, lineage 2
Same specification, independently structured: table-driven predicate folding,
recursive descent instead of a stack machine, canonical-size estimation
instead of byte-compare. Defect classes shared by both lineages are
vanishingly rarer than in either alone; any disagreement fails closed at the
Governor (`fortress_tcb: "tcb_mismatch"`) and trips the wire.

The two TCBs are kept deliberately different. Resist "deduplicating" them —
N-version design *is* the control.

### fortress/telemetry_mac.py — signed telemetry
Every event emitted by an internal organ carries `mac = HMAC-SHA256(key,
canonical(event))`. The bus verifies on ingest. Unverifiable events are
accepted for **visibility** (they are themselves attack evidence) but are
marked `verified: false`, never reach the Commander, never reach the entity
graph, and never trigger auto-orchestration. Keys come from
`EIGENSHIELD_BUS_KEY` (dev default is documented; production must inject).

### fortress/boot_manifest.py — config pinning
Pinning command (run after any legitimate, reviewed config change):

```bash
python -m fortress.boot_manifest --pin config/manifest.json
python -m fortress.boot_manifest --check config/manifest.json   # exit 2 on tamper
```

Pinned files: `config/policy.yaml`, `config/company_topology.json`,
`commander/tool_schemas.json`, `commander/system_prompt.txt`. If no manifest
exists the system boots with `config_integrity: "UNVERIFIED"` in `/api/state` —
it never boots *silently*.

### fortress/canaries.py — context tripwires
`ESH_CANARY_<10 hex>` tokens derived from `EIGENSHIELD_CANARY_KEY` + UTC date
(yesterday accepted during rotation). Embedded in the Commander context as a
SYSTEM_CANARY_NOTE; `scan_text()`/`is_compromised()` runs on the model output.
Any hit ⇒ output discarded, actions dropped, `canary_hit` trip.

### fortress/tripwire.py — anti-probing freeze
Process-wide singleton (`shared()`) fed by bus, Commander and Governor.
Instant trip: canary hit or TCB mismatch. Threshold trip (60 s window):
≥4 BLOCKED, ≥3 injection markers, ≥2 unverified disruptive requests. While
tripped, the Governor returns BLOCKED for everything (`fortress_tcb:
"frozen"`). `reset(human_stepup=True, note=...)` — only a human reopens it.

### fortress/ledger_anchor.py — ledger tail anchor
HMAC-sealed side file `(seq, head_hash)` re-pinned on every append. The
hash chain alone detects edits; the anchor additionally detects
**truncation + re-forgery of a valid shorter prefix**. `AuditLedger.verify()`
cross-checks both and reports `valid: false` on mismatch.

### fortress/sandbox_runner.py — subprocess isolation
`run_isolated(task)` with a strict task whitelist
(`policy_selftest | ledger_verify | noop_revert`), `python -I`, rlimits
(512 MB address space, 10 s CPU, 256 fds, no core dumps), 15 s wall timeout.
Non-Linux degrades loudly, never silently.

## 3. What the evidence shows (this checkout)

* `pytest -q` — **34 passed** (23 v2.0 + 11 FORTRESS, incl. exhaustive abstract
  sweep of the crown-invariant over the full tool × arg-variant × human-step-up
  space for BOTH TCB lineages: 960 combinations, zero Tier-0 approvals
  without human step-up, zero core↔mirror disagreements).
* `simulator/demo_06_fortress_breach_drill.py` — **6/6 drills pass**:
  1. forged telemetry POSTed to the bus ⇒ AI path held closed; signed
     organ telemetry executes (dry-run);
  2. canary-leaking hijacked Commander ⇒ every action dropped;
  3. one-byte policy.yaml edit ⇒ boot refused;
  4. exhaustive invariant sweep (960 combos) ⇒ zero violations;
  5. 4 blocked decisions in 60 s ⇒ AI path frozen; unauthenticated reset
     refused; human reset opens it;
  6. truncated/re-forged ledger tail ⇒ anchor cross-check fails.
* Live bus check (`python -m bus.event_server … --port 8081`): unsigned batch ⇒
  `{"accepted": 7, "unverified": 7}` ⇒ `/api/orchestrate` ⇒
  `HELD_UNVERIFIED_EVIDENCE`; signed batch ⇒ `unverified: 0` ⇒ full
  correlation + Governor execution (dry-run), `config_integrity` reported in
  `/api/state`.

## 4. Operating FORTRESS

| Situation | Action |
|---|---|
| First boot / legit config change | re-pin: `python -m fortress.boot_manifest --pin config/manifest.json`, commit manifest |
| CI gate | `python -m fortress.boot_manifest --check config/manifest.json` (exit 2 = fail build) |
| Suspected probing | watch `/api/state → fortress.tripwire`; if frozen, find the cause before any `reset(human_stepup=True)` |
| Canary hit | treat as active intrusion: isolate the Commander host, rotate `EIGENSHIELD_BUS_KEY`/`EIGENSHIELD_CANARY_KEY`, audit ledger vs anchor |
| Ledger mismatch | do **not** restart the bus; preserve files, escalate — the tail was rewritten or replaced |
| Key rotation | rotate bus key on organs + bus together; canaries self-rotate daily; re-pin manifest after any change |

## 5. Honest limits — read before trusting

1. **This is defense-in-depth, not a proof.** Python itself is not verified.
   The TCB pair removes *accidental* common-mode defects; it does not remove
   the interpreter, libc, or the CPU from the TCB. For that you need seL4-style
   separation or HSMs.
2. **HMAC in-process is an integrity tag, not a boundary.** Anyone who can
   read the process key can forge events. Real deployments need the telemetry
   key on the organs only, mTLS, and ideally a separate UID/HSM unseal — not
   an env var on the bus host.
3. **The anchor is same-filesystem.** An attacker who can rewrite both the
   ledger and the `.anchor` file can re-seal both. WORM/object storage or a
   notarized remote copy is the production answer.
4. **Batch-level verified gate.** The Commander consumes verified events
   only; if one verified event is present, one forged event in the same
   window still cannot steer it — but per-action evidence *binding* (which
   event justified which action) is v2.2 work.
5. **rlimits are Linux-specific**; on other platforms the sandbox runs with
   degraded isolation and says so.
6. **Tripwire is heuristic.** Determined attackers spread blocked requests
   over hours; that is what the blast-radius budgets and human gates are for.
7. **Signing proves origin, not sanity.** A compromised-but-signed organ can
   still emit authorized-shaped garbage; the crown-jewel lock and budgets
   bound the damage.
8. **Canned keys in this repo are development keys.** Production must inject
   `EIGENSHIELD_BUS_KEY`, `EIGENSHIELD_CANARY_KEY`, `EIGENSHIELD_SALT`.
