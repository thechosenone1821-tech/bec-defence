# RAKSHA Sentinel (Infrastructure) — what is built, what to build, how to build it

> **Last updated:** 2026-11-23 · **Owner of record:** repo maintainer (human)
> **Evidence base:** `raksha-code/spine/`, `raksha-code/sentinel/`, `raksha-code/raavan/`,
> `raksha-code/evals/`, `raksha-code/tests/`, plus a live audit on 2026-11-23:
> `pytest -q` → **67 passed**; `python evals/run_evals.py` → table reproduced
> (1 fused campaign from 5 signed alerts; 14.71 % fixture flow severed with
> 100 % mission-critical weight preserved; deep-implant cut **BLOCKED** at the
> 90 % floor; forged probes 5/5 rejected).
> **Companion docs:** `CITIZEN_APP_BUILD.md` · `MAYA_BUILD.md` ·
> `raksha/ARCHITECTURE.md §2, §4, §5` · `raksha/BUILD_GUIDE.md` (M1, M2, M5, M6) ·
> `raksha/EVALS.md`.
> **Note:** `features.md` is not present in this repository (verified across the
> working tree, all commits, all branches, and the deleted
> `spectral-defence-poc (1).zip`). Requirements below are taken from
> `ARCHITECTURE.md §2/§4/§5`, `BUILD_GUIDE.md §2/§3`, `ROADMAP.md` and the
> `CHANGELOG.md` park list.

**Status vocabulary:** `BUILT` · `PARTIAL` · `STUB` (labelled) · `ABSENT`.

---

## 1. Scope

**Sentinel** is the infrastructure-facing app: an on-prem appliance for
hospitals, payment platforms, identity and cloud/AI-agent estates. Four shields
(**Endpoint · Identity · Cloud/Data · AI-Agent**) emit signed evidence into one
attack graph; a deterministic **Governor** disposes; a **hash-chained ledger**
seals; a **containment planner** computes the minimum-disruption cut.

**Non-negotiable for this entire document:** nothing here may touch a real host.
The executor is dry-run/organ-simulated by construction, the four shields run
against synthetic fixtures, and RAAVAN never leaves `evals/`. If a task appears
to require pointing code at a live target — stop and escalate
(`AI_HANDOFF.md §7`).

---

## 2. Verified built state

### 2.1 Shared spine (`spine/`)

| # | Component | Status | Evidence | Honest limit |
|---|---|---|---|---|
| S-01 | Zero-trust sanitizer — HMAC opaque tokens, fixed enums, `[0,1]` clamp, injection scrub | BUILT | `spine/sanitizer.py` (162 LOC); `tests/test_sanitizer.py` (3) | Salt defaults to a dev constant (`EIGENSHIELD_SALT`); no key rotation |
| S-02 | Telemetry MAC — HMAC-SHA256 at birth, replay cache, unsigned ⇒ visible but inert | BUILT | `spine/telemetry_mac.py`; `tests/test_fortress.py` | Dev key default. **Integrity tag, not a boundary** — the module says so itself; the boundary appears only when the bus runs as a separate UID |
| S-03 | 10-minute attack graph + campaign correlator v0 (union-find over shared tokens) | PARTIAL | `spine/entity_graph.py` (119 LOC) | **No temporal kernel, no weighted fingerprint** — this is the single biggest research gap; see **I-02** |
| S-04 | SHA-256 hash-chained ledger + HMAC side anchor | BUILT | `spine/ledger.py`, `spine/ledger_anchor.py`; `tests/test_audit_ledger.py` (2) | Anchor lives on the same writable FS — raises the bar, is not a boundary (module states this) |
| S-05 | Governor — 10-tool schema lock, crown-jewel lock, blast-radius budgets, uptime floor, FIDO2 gate | BUILT | `spine/governor.py` (243 LOC); `tests/test_policy_engine.py` (6) | The "FIDO2" gate is currently a **string check** on `context["human_stepup"] ∈ {VERIFIED, TRUE, APPROVED}` — no cryptography. See **I-03** |
| S-06 | N-version stateless TCB twins, fail-closed cross-check | BUILT | `spine/tcb_core.py`, `spine/tcb_mirror.py`; `tests/test_tcb_exhaustive.py` — exhaustive over the abstract input domain | Not a proof about the Python interpreter; docstring says exactly that |
| S-07 | FORTRESS tripwire (freeze AI path on probe/abuse), canary tokens in Commander context | BUILT | `spine/tripwire.py`, `spine/canaries.py`; `tests/test_fortress.py` (9) | Canary regex + HMAC key default to dev constants |
| S-08 | Boot manifest — SHA-256 config pinning (`--pin` / `--check`) | BUILT | `spine/boot_manifest.py`; surfaced in `Governor.status().config_integrity` | Must be re-pinned after *any* legitimate config edit (documented) |
| S-09 | FastAPI + WebSocket bus: verified-only ingest, `/api/health`, `/api/state`, `/api/ingest`, `/api/orchestrate`, `/api/containment`, `/ws/telemetry` | BUILT | `spine/bus.py` (472 LOC); `tests/test_m1_campaign_flow.py` | **No authentication of any kind** on any endpoint; CORS `allow_origins=["*"]` |
| S-10 | Local SLM client with JSON mode + automatic deterministic fallback | PARTIAL | `spine/slm_client.py`, `spine/orchestrator.py` | **No model has ever been run.** Every green run in this repo used `fallback_rules`. `commander_mode` reports which — trust that field |
| S-11 | Uptime auto-rollback watchdog (3 s probes, 15 s failure window) | PARTIAL | `spine/watchdog.py` (73 LOC) | **Not wired into the bus.** Nothing calls `RollbackWatchdog.watch()` outside tests. Governor docstring references `rollback_watchdog.py`, which does not exist |
| S-12 | Containment planner — exhaustive min-disruption cut, `J = C + λD + μR + νA`, `Reach→Tier-0 = ∅` | BUILT | `spine/containment.py` (163 LOC); `tests/test_m5_containment.py` (7) | Exhaustive over the **11 non-crown edges** of a synthetic 9-VLAN / 14-edge graph (3 crown edges excluded from candidacy). Fixture-measured weights, no NetFlow. `CHANGELOG.md` v0.6.0 says 10 — stale, fix it |
| S-13 | Sandbox runner — whitelist subprocess isolation | BUILT | `spine/sandbox_runner.py` | — |
| S-14 | Ledger CLI — verify / tail / replay | BUILT | `spine/ledger_cli.py` | — |

### 2.2 Shields (`sentinel/shields/`)

All eight organs from EIGENSHIELD were ported and are organ-backed in the
executor (`executor_mode: "organ"` at `/api/state`).

| # | Shield | Organ | Status | Honest limit |
|---|---|---|---|---|
| S-15 | Endpoint | `page_curve_trap.py` — 4 KB parity honey-blocks | BUILT (simulated) | Runs against fixture FS. Never calls `os.kill` — PID termination is a **reported status**, not an action. Real `fanotify`/eBPF hook is out of scope and labelled |
| S-16 | Endpoint (silicon) | `landauer_thermal_audit.py` — power-vs-IPC residual | BUILT (simulated) | Synthetic telemetry; no Intel RAPL/NVML reader wired |
| S-17 | Identity | `bec_spectral_filter.py` — rank-1 SVD condensation; `cookie_fluid_turbulence.py` — behavioural Reynolds | BUILT | Operates on synthetic session matrices; no live TLS/HTTP tap |
| S-18 | AI-Agent | `bragg_fft_firewall.py` — 1D FFT peak + Fiedler λ₂; `hessian_lyapunov_guard.py` — curvature probe + restoring vector | BUILT (as gates over supplied embeddings) | No real model residual stream is instrumented — the hooks are simulated |
| S-19 | Network / self-heal | `hashimoto_percolation.py` — non-backtracking ρ(B) minimal cut; `muts_ebpf_repair.py` — 50 ms shield splice | BUILT (control-surface simulation) | Cuts are **virtual** (graph edits), splices are simulated. Real CAP_BPF/eBPF is explicitly out of scope |

### 2.3 Red team, evals, deployment

| # | Component | Status | Evidence | Gap |
|---|---|---|---|---|
| S-20 | RAAVAN playbook (10 techniques, 6-stage sequence) + replay player feeding **signed** organ telemetry through the real pipeline | BUILT | `raavan/playbook.yaml`, `raavan/killchain.py`; `tests/test_raavan_killchain.py` (6) | **T06 cloud-audit fixture missing** — `playbook.yaml` literally says "pending — M6". So the Cloud/Data shield has **no adversary** |
| S-21 | Measured eval table, baselines B1/B2/B3 vs RAKSHA | BUILT | `evals/run_evals.py`; frozen in `raksha/EVALS.md` | Single machine, fixture weights, synthetic corpus — all correctly labelled |
| S-22 | Sentinel SOC console | **ABSENT** | `sentinel/` contains only `shields/`. No `console/` | The bus *prints* a root card saying "dashboard served separately — see `docs/UI_UX_BRIEF.md`", and `bus.py` line 169 references the same file. **That file does not exist.** See **I-01** |
| S-23 | Deployment (`deploy/`, Dockerfiles, compose profiles `hospital|payments|campus`) | **ABSENT** | No `deploy/`, no Dockerfile, no compose file anywhere in the repo | `BUILD_GUIDE.md §2` and `CONTEXT.md §6` require `docker compose up` installs |
| S-24 | CI (pytest gate, ledger golden vectors, secret scan) | **ABSENT** | No `.github/` at all | `BUILD_GUIDE.md §6` says pytest green before merge — currently enforced by humans only |
| S-25 | Attack-timeline replay UI, ₹-lost-vs-₹-saved counter | **ABSENT** | `ROADMAP.md` Day-2 boxes still unchecked | Stage value is high, cost is low |
| S-26 | `EIGENSHIELD_*` → `RAKSHA_*` env rename | **ABSENT** | `services.py`, `telemetry_mac`, `canaries`, `ledger_anchor`, `sanitizer`, `slm_client` all read `EIGENSHIELD_*` | Parked in `CHANGELOG.md` v0.2.0 "branding sweep — do it in one sweep, not piecemeal" |
| S-27 | Real agent integration (eBPF/LSM), RBAC, admin console | **ABSENT** | `ROADMAP.md` Phase 2 | Correctly out of scope for the demo, must stay labelled as such |

### 2.4 The four numbers you may quote (and no others)

From `evals/run_evals.py` on this machine, 2026-11-23:

| Metric | Value | Label |
|---|---|---|
| Campaigns fused from 5 signed organ alerts | **1** (`cmp_…`, size 5) vs 5 separate alerts | fixture replay |
| Fixture flow severed (ingress seeds) | **14.71 %** (85.29 % preserved) | fixture-weighted |
| Mission-critical fixture weight preserved | **100.00 %** (tier-0 edges cut: 0, ICU INTACT) | fixture-weighted |
| Deep-implant cut autonomy | **BLOCKED** — preserved uptime 55.56 % < 90 % floor | by design |
| Forged (unsigned) probes rejected | **5/5**, orchestrate → `HELD_UNVERIFIED_EVIDENCE` | measured |
| Sandbox ingest→decision | ~115–208 ms | wall-clock, **not an SLA** |

---

## 3. Gap register (build order)

| Priority | ID | Work item | Why now |
|---|---|---|---|
| **P0** | I-03 | Real human step-up: FIDO2/WebAuthn assertion + signed approval record in the ledger | Today a string field decides whether crown-jewel action is allowed. This is the doctrine's weakest real point |
| **P0** | I-11 | Wire `RollbackWatchdog` into the bus for every approved disruptive action | Advertised as invariant 5; currently dead code outside tests |
| **P0** | I-10 | Prompt-injection-aware handling of `summary` (see SEC-2) | The 10-tool schema allows free text into the AI path |
| **P0** | I-01 | `docs/UI_UX_BRIEF.md` + minimal SOC console | Bus already references a file that does not exist; no way to *see* the system |
| **P0** | I-23 | `deploy/` compose profiles + Dockerfile | District-hospital install story is `docker compose up` or nothing |
| **P0** | I-24 | CI: pytest, ledger golden vectors, secret scan | `BUILD_GUIDE.md §6` gate is unenforced |
| **P1** | I-02 | Campaign correlator v1: temporal kernel + weighted fingerprint + `CASE_` token prefix | v0 fuses on any shared token; over-merges on hot entities (shared NAT/host) |
| **P1** | I-20 | T06 cloud-audit fixture so the Cloud/Data shield has an adversary | One of four shields is untested against red team |
| **P1** | I-25 | Attack timeline replay + ₹ counter + DRY-RUN banner | `ROADMAP.md` Day-2 items; stage-critical |
| **P1** | I-04 | Real NetFlow / cloud-audit / auth-log **fixture ingestors** (file-based, honest labels) | Planners on synthetic weights will not survive contact with a pilot |
| **P2** | I-05 | Graph scale: NetX→sparse CSR + heuristic min-cut seeding above N nodes | Exhaustive enumeration dies past ~20 candidates |
| **P2** | I-09 | Optional OR-tools ILP path for small graphs | `ARCHITECTURE.md §5` names it |
| **P2** | I-26 | Env rename sweep `EIGENSHIELD_*`→`RAKSHA_*` (dual-read, one release, then drop) | Parked twice in `CHANGELOG.md` |
| **P2** | I-06 | Real eBPF/LSM **dry-run** probe path (`bpf()` verify-only) with explicit `CAP_BPF` gate | Only if the maintainer signs off; must stay dry-run |
| **P3** | I-27 | Ledger notarization (WORM / transparency log) behind existing `anchor_writer` seam | Anchor is same-FS today |
| **P3** | I-28 | RBAC + admin console + SBOM + dependency pinning | Pilot prerequisite (`ROADMAP.md` Phase 2) |

---

## 4. How to build each item

### I-03 — Real human step-up (do this first)

**Where:** new `spine/stepup.py`; `spine/governor.py` invariant 4; a new
`POST /api/stepup/verify` route.

**How:**

1. Operator enrolls a platform authenticator once (`navigator.credentials.create`
   on the console) → store `credential_id`, public key, sign counter in
   `config/operators.json` (**not** the ledger).
2. On a Tier-0 request, the Governor returns `decision: "STEP_UP_REQUIRED"`
   with a fresh server nonce (`stepup_id`, 120 s TTL, single-use, bound to the
   exact `tool` + canonicalized `args` hash).
3. The operator signs the nonce with WebAuthn
   (`navigator.credentials.get`). The server verifies the assertion
   **server-side** (challenge match, origin, RP ID, counter monotonicity) using
   `cryptography`/`python-fido2`.
4. Only then does `context["human_stepup"]` become `"VERIFIED"` — and the
   verification record (credential id, counter, args hash, nonce) is appended to
   the ledger as `human_stepup_verified` **before** the action is re-evaluated.

```python
# spine/governor.py — replace the string check with a capability object
verdict = context.get("stepup")            # StepUpVerifier result, not a string
human_ok = bool(verdict and verdict.valid_for(tool, args))
```

**Done when:** a fuzz test proves no path sets `human_ok=True` without a
verified assertion (extend `test_tcb_exhaustive.py`'s input domain with the
step-up class); replay of a used nonce is rejected; expired nonce is rejected;
a forged assertion fails closed; the ledger contains the verification record
before any action record.

**Safety:** fail closed on any verifier exception. Do not add a
`--disable-stepup` flag. Do not accept a shared secret as a substitute.

---

### I-11 — Wire the watchdog

**Where:** `spine/bus.py::run_pipeline` after `executor(...)` for any tool in
`_BUDGET_CATEGORY`, plus `spine/containment.py` plans.

**How:** build the watchdog once at app creation from `policy.yaml`
(`auto_rollback`). After an APPROVED disruptive action, register a probe set
(Tier-0 health probes; in the sandbox these read the topology's criticality
model — clearly labelled) and a `revert_fn` that calls the organ's revert RPC.
Run it on a thread so the HTTP response is not blocked; broadcast
`{"type": "watchdog", ...}` on the WS feed and append to the ledger.

```python
watchdog = RollbackWatchdog(policy, ledger=ledger)
def _after_approve(action, result):
    if action["tool"] in _DISRUPTIVE:
        threading.Thread(target=watchdog.watch, args=(
            action_id, probe_fn_for(action), revert_fn_for(action)), daemon=True).start()
```

**Done when:** injected latency breach for > 15 s reverts and ledgers
`rollback_executed`; a healthy run yields `WATCHDOG_CLEAR`; a test compresses
the window with the injectable `sleeper`/`clock` (already supported) and asserts
the revert callback fired exactly once; the WS frame is emitted; a watchdog
failure never blocks the ingest path.

---

### I-10 / SEC-2 — Close the sanitizer's remaining hole

`escalate_human_stepup.summary` is `type: string` (schema `maxLength: 500`) and
flows into the plan, the brief, the ledger **and** `/api/state` — i.e. to a human
operator's screen. A poisoned log could, in principle, place text there. Today
this is the only free-text field that reaches a human through the AI path, and
it is the same class of bug Plane 2 exists to kill.

**What the code actually enforces (verified by test, 2026-11-23):**

- `spine/tcb_core.py` **does** reject `summary` > 500 chars (returns
  `BLOCKED`, `fortress_tcb: tcb_override`).
- **Nothing else is checked.** No charset restriction, no markup/instruction
  scrubbing, no `maxLength` enforcement in `PolicyEngine.evaluate` itself
  (only the TCB twin), and `Orchestrator.validate_action` ignores `maxLength`
  entirely — a 2 000-char summary returns `None` (valid) there.
- So 500 characters of *arbitrary attacker-shapeable text* can still reach an
  operator's screen. Length is bounded; content is not.

**Fix (choose one, document which):**

- **(a) Whitelist-enum the field** (preferred): replace `summary` with
  `summary_code: {enum: [PARITY_COLLAPSE, THERMAL_RESIDUAL, TORBULENT_REPLAY,
  INJECTION_BLOCKED, MISMATCH_SPLICE, CROWN_ASSET_IMPLICATED, OTHER]}` and render
  the human sentence in the UI from i18n templates. Zero attacker-controlled
  bytes.
- **(b) Bounded, sanitized template**: `summary = f"{code}: {n_events} events,
  max {sev:.2f}, entities {','.join(tokens[:5])}"` — composed by the bus from
  validated fields, never echoed from the model.

**Done when:** a fuzz test posts 1 000 hostile `summary` payloads (all ≤ 500
chars, so the length check cannot save you) and asserts the rendered operator
string contains no characters outside the allowed charset and no
canary/instruction patterns; `validate_action` and `PolicyEngine.evaluate` both
enforce the same bounds as the TCB twin; the contract change is versioned
(additive → `contract v2.2`), and `telemetry_mac` + sanitizer still pass.

---

### I-01 — SOC console (and the missing brief)

**Where:** `sentinel/console/` (static, no build step) + `docs/UI_UX_BRIEF.md`
(the file the bus already references — create it, do not delete the reference).

**Contract to consume** (`spine/bus.py`, already live): WS `/ws/telemetry`
frames `event`, `action_plan`, `governor_decision`, `tool_result` (+ the new
`watchdog` and `containment` frames). REST: `/api/state` (campaigns,
last_containment, orchestrator/executor mode), `/api/health`,
`POST /api/containment`, `POST /api/orchestrate`.

**Screens (minimum viable, in this order):**

1. **Live graph** — VLAN/host topology from `company_topology.json`; Tier-0
   always rendered in a locked, distinctly-coloured class; campaign paths
   animate on new edges.
2. **Campaign panel** — `cmp_*` id, size, `severity_max`, contributing organs,
   first/last seen, and the fused kill-chain stage.
3. **Governor panel** — every decision with `decision`, `reasons[]`,
   `fortress_tcb` (`ok|tcb_override|tcb_mismatch|frozen`), budget usage,
   `config_integrity`, tripwire state.
4. **Containment panel** — proposed cut edges, `preserved_fixture_flow_pct`,
   `preserved_critical_weight_pct`, `icu_status`, and a permanent
   **"DRY-RUN"** banner (`BUILD_GUIDE.md §5.6`).
5. **Ledger drawer** — tail of the hash chain with `seq`, `prev_hash`, `hash`;
   a "verify" button that runs the same logic as `ledger_cli verify` and shows
   pass/fail.
6. **Commander strip** — `commander_mode: slm|fallback_rules` in **large type**.
   Never let a fallback-rules run look like an AI run.

**How:** vanilla HTML/CSS/JS, `EventSource`→`WebSocket`, `requestAnimationFrame`
for graph updates, no frameworks — matches the "zero-dependency console" line in
the root `README.md` §6 and keeps the district-hospital auditability promise.
Serve it as `StaticFiles` from the bus at `/console` (one process, one port,
no CORS puzzle) while keeping the existing `allow_origins` for dev.

**Done when:** a headless test opens the console against a booted bus, replays
the RAAVAN kill chain, and asserts the campaign id, the BLOCKED deep-implant
decision, and the DRY-RUN banner all appear; keyboard navigable; readable at
1280×720 and 1366×768.

---

### I-23 — Deployment profiles

**Where:** `deploy/` with `base` compose + three overlays.

```text
deploy/
  docker-compose.yml            # base: spine bus + citizen api + optional console
  profiles/
    hospital.yml                # Tier-0 = ICU/coldchain/core-auth; D weighted highest
    payments.yml                # switch isolated from office LAN; egress rules strict
    campus.yml                  # seed/demo profile (current topology)
  sentinel/Dockerfile           # python:3.11-slim, non-root uid, no model baked in
  citizen/Dockerfile
  ollama/docker-compose.ollama.yml   # optional model sidecar, manual pull
  env.example                   # ALL RAKSHA_* keys, no secrets
```

**How:** multi-stage build, `USER 10001`, read-only root FS where possible,
healthchecks hitting `/api/health`, ledger volume mounted **outside** the
container, `RAKSHA_EXECUTOR=dry-run` set in every shipped profile (organ mode is
opt-in for the demo box only). Profiles differ only by mounted
`policy.yaml` + `company_topology.json` — one code path, three policies. Add a
`make`-less `README` with the exact three commands per profile.

**Done when:** `docker compose --profile hospital up` on a clean machine
produces `/api/health` → `config_integrity: ok`, `executor_mode: organ`,
`autonomous_execution: dry-run`; the container writes no ledger inside the image
layer; image < 400 MB without the model; no secrets in any file (`grep` gate).

---

### I-24 — CI gates

**Where:** `.github/workflows/ci.yml`.

```yaml
jobs:
  test:      # pytest -q (67+), plus evals reproducibility (deterministic asserts)
  ledger:    # golden-vector hashes, tamper test, anchor cross-check
  secrets:   # gitleaks / trufflehog on the diff + full history
  manifest:  # python -m spine.boot_manifest --check must pass
  docs:      # no stale [VERIFY] left open; Last updated bumped when docs change
```

**Done when:** a red test blocks merge; a tampered ledger fixture fails the
`ledger` job; a planted fake key fails `secrets`; the manifest job catches an
unpinned config edit (this is the one that saves you on stage).

---

### I-02 — Correlator v1 (the actual research core)

**Where:** `spine/entity_graph.py` → new `spine/correlator.py`.

Replace "share any token ⇒ same campaign" with a scored union:

```text
score(i, j) = w_e · entity_overlap_jaccard(i,j)
            + w_t · exp(−Δt / τ)                     # temporal kernel, τ ≈ 300 s
            + w_s · stage_progression(i,j)           # recon→impact ordering bonus
            + w_k · case_token_match(i,j)            # exact, high weight (CASE_)
merge if score ≥ θ  (θ ~ 0.55, single constant, documented)
```

- **Temporal kernel** kills the "everything in the 10-min window is one
  campaign" over-merge.
- **Weighted fingerprint** down-weights hot entities: a `vlan_id` shared by 400
  events carries little evidence; a rare `doc_hash` shared by 2 events carries a
  lot (inverse document frequency over the window).
- **`CASE_` prefix** as an additive contract-v2.2 token so citizen reports can
  carry a high-entropy case token that the sanitizer digests to a stable
  `CASE_…` entity (parked in `CHANGELOG.md` v0.5.0).

**Done when:** an adversarial fixture set — 3 genuinely separate campaigns plus
2 decoys sharing a noisy VLAN — yields exactly 3 campaigns with the right
members; a regression test pins determinism (same input ⇒ same `cmp_*` id);
`/api/state` shows the score components so the demo can explain *why*.

---

### I-20 — T06 cloud fixture (close the fourth shield)

`playbook.yaml` T06 says "lab cloud audit log generator (pending — M6)". Build
`raavan/fixtures/cloud_audit.jsonl` — a synthetic CloudTrail-shaped log
(off-hours `GetObject` bursts, `CreateAccessKey` drift, signed-URL fan-out) with
zero real account ids — and an ingestor in `sentinel/shields/` that maps it to
the Cloud/Data heuristics named in `ARCHITECTURE.md §4` (bulk reads, off-hours
exports, new egress paths, signed-URL abuse, API-key drift). Wire it into
`killchain.py` as T06 and add the expected defense to the playbook.

**Done when:** T06 fires on the fixture, stays silent on a clean-day fixture,
and appears in the eval table as a 6/6 coverage row (update `raksha/EVALS.md` —
and re-label the coverage metric honestly).

---

### I-25 — Timeline replay, ₹ counter, DRY-RUN banner

**Replay:** the ledger already holds every `event`, `orchestration`,
`governor_decision`, `tool_result`, `rollback_executed` in order with timestamps.
Build `GET /api/replay?campaign_id=…` that returns the ordered slice, and a
console scrubber that re-renders graph + decisions at time *t*. This is
read-only; it cannot execute anything.

**₹ counter:** `EVALS.md` already gives the defensible form
`₹saved = threats_stopped × ₹avg_loss[VERIFY] − false_positives × ₹cost[VERIFY]`.
Implement it as a **pure function over ledger counts** with the ₹ inputs loaded
from `config/economics.yaml`, every value tagged `[VERIFY]` with a source field.
If a value is `null`, the counter must render **"—"**, never a guessed number.

**Done when:** replay of a recorded run reproduces the same campaign ids and
decisions; the ₹ counter shows "—" with exit criteria unmet and a number once
filled; the DRY-RUN banner is unremovable in any shipped profile and is asserted
by test.

---

### I-04 / I-05 / I-09 — Make the planners survive a pilot

- **I-04:** add file-based, clearly-labelled ingestors for auth logs, cloud
  audit and flow records (CSV/JSONL fixtures first). Keep the
  `FIXTURE-MEASURED` label until a pilot supplies real (minimised) data.
- **I-05:** above ~20 candidate edges, stop enumerating: seed with min-cut /
  Gomory-Hu on the capacity-weighted graph, then local search with the hard
  `Reach→Tier-0 = ∅` check. Keep the exhaustive path as the oracle in tests —
  any heuristic result must match it on the small graphs (that is your
  correctness proof).
- **I-09:** optional `ortools` ILP for ≤ 200 nodes behind a flag, skipped
  cleanly when the dependency is absent (district hospitals will not install it).

**Done when:** exhaustive-vs-heuristic equality holds on all small fixture
graphs; a 200-node synthetic graph plans in < 2 s; the objective terms are still
reported individually so the demo can show *why* the cut was chosen.

---

### I-26 — Env var sweep (one release, then drop)

Read `RAKSHA_X` first, fall back to `EIGENSHIELD_X`, and **log a deprecation
warning** when only the old name is set. Files:
`spine/{telemetry_mac,canaries,ledger_anchor,sanitizer,slm_client,bus}.py`.
Ship with `deploy/env.example` listing only `RAKSHA_*`. Remove the fallback one
release later — do not leave it forever (`CHANGELOG.md` v0.2.0 says exactly this).

---

## 5. Security issues to fix regardless of milestones

| ID | Issue | Reality today | Required action |
|---|---|---|---|
| SEC-1 | **Unauthenticated control plane** | `/api/orchestrate` (forces a pass), `/api/containment` (drives planner), `/api/ingest` are all open, CORS `*` | Add a bearer/HMAC gate for the control endpoints; leave `/api/ingest` open **but inert** (unsigned ⇒ unverified ⇒ `HELD_UNVERIFIED_EVIDENCE`, which already works) and bind to loopback by default |
| SEC-2 | **Free-text `summary`** reaching the operator | `escalate_human_stepup.summary` is unbounded string | See I-10 |
| SEC-3 | **Dev keys as defaults** | `EIGENSHIELD_BUS_KEY`, `_SALT`, `_CANARY_KEY`, `_ANCHOR_KEY` all have working dev fallbacks | Refuse to boot when `RAKSHA_ENV=prod` and a dev key is in use — fail closed, loudly |
| SEC-4 | **Same-FS anchor** | Anchor protects against truncation, not against a root-level attacker | Documented; keep the `anchor_writer` seam and plan WORM (I-27) |
| SEC-5 | **Watchdog not armed** | Invariant 5 exists only in tests | I-11 |
| SEC-6 | **Step-up is a string** | `human_stepup == "VERIFIED"` | I-03 |
| SEC-7 | **A real `os.kill` path exists** | `PageCurveTrap(allow_real_kill=False)` is safe by default and the bus constructs it with the default, but the flag exists and a single `PageCurveTrap(allow_real_kill=True)` anywhere would turn a simulated organ into a process-killer | Remove the flag entirely, or gate it behind an env var that is refused when `RAKSHA_ENV=prod`, and print a one-line banner on every boot: `PAGE_CURVE: dry-run (no process is ever signalled)`. Add a test that greps the repo for `allow_real_kill=True` and fails |
| SEC-8 | **Dead `note` parameter** | `POST /api/citizen/report` accepts `note` (≤ 200 chars) and silently discards it — the UI never sends it | Remove it from the API contract, or store it locally only with explicit consent. A field a user might pour a scam message into, that vanishes, is a trap |
| SEC-9 | **No TLS anywhere** | Both services are plain HTTP on `0.0.0.0` | Terminate TLS at the deploy layer (`INFRA_BUILD.md` I-23); refuse non-loopback bind without TLS when `RAKSHA_ENV=prod` |

---

## 6. Test gates

```bash
cd raksha-code
pytest -q                                     # 67 baseline — never regress
python evals/run_evals.py                     # table must reproduce
python -m spine.boot_manifest --check spine/config/manifest.json
python -m spine.ledger_cli verify             # after any run with a ledger
```

| Suite | Gate |
|---|---|
| Containment correctness | Cut disconnects every seeded attacker, preserves ≥ 90 % mission-critical weight, never cuts a crown edge |
| Governor torture | 10 000 fuzzed actions: zero Tier-0 approvals without a **verified** step-up; zero TCB disagreements escape |
| Ledger integrity | Golden hashes, anchor cross-check, tamper test, truncation test |
| Replay determinism | Same recorded input ⇒ identical `cmp_*` ids and identical decisions |
| Evals | Baseline × metric table regenerates; no number in `EVALS.md` differs from a fresh run |

---

## 7. Definition of done (Sentinel milestone)

- [ ] Real FIDO2 step-up; ledger records verification before action
- [ ] Watchdog armed on every disruptive action; rollback tested
- [ ] SEC-1 → SEC-9 closed or explicitly accepted in writing by the maintainer
- [ ] Correlator v1 with temporal kernel + weighted fingerprint + `CASE_` token
- [ ] T06 cloud fixture; 6/6 red-team coverage
- [ ] SOC console served at `/console`, DRY-RUN banner, replay scrubber
- [ ] `deploy/` three profiles, one command each, dry-run default
- [ ] CI green on all five gates
- [ ] `raksha/EVALS.md` refreshed from a real run; `CHANGELOG.md` entry appended
- [ ] No safety rail relaxed anywhere in the diff
