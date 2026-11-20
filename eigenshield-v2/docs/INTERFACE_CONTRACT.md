# INTERFACE CONTRACT v1.0.0 — Sense & Sanitize ⇄ Decide & Contain ⇄ Dashboard

Frozen seams for EIGENSHIELD v2.0. Changes require a PR **and** sign-off from
both backend developers (+ UI/UX for the dashboard-facing parts). Changelog
at the bottom.

---

## 1. Plane 1 → Plane 2 (raw organ events) — internal only

Organs (A) call `BaseOrgan.emit(...)`. Event dicts may contain near-raw
identifiers and are useless to B. The sanitizer is the trust boundary.

```json
{
  "event_id": "evt_9f3a2c1b77aa",
  "timestamp_utc": "2026-11-20T09:18:04.215Z",
  "ring": "RING_3_ENDPOINT_SILICON",
  "organ": "ENDPOINT_PAGE_CURVE",
  "signal_type": "PARITY_ENTROPY_COLLAPSE",
  "severity": 0.96,
  "entities": {"host_id": "HOST_042", "vlan_id": "VLAN_MAINT_03", "user_id": "USER_019", "process_hash": "pid:4242"},
  "metrics": {"bytes_written": 4096, "parity_delta": 0.994, "local_reflex_action": "PID_TERMINATED_0.9MS"}
}
```

## 2. Plane 2 → Plane 3 (sanitized events) — the seam

`bus.sanitizer.sanitize_event(raw) -> SanitizedEvent`. Guarantees:

* **Zero raw strings.** Filenames, URLs, usernames, prompts, payloads are
  replaced by opaque HMAC-SHA256 tokens (`HOST_AB12CD` style) or
  `sha256:<32-hex>` digests. Stability: same input + same salt ⇒ same token.
* `severity ∈ [0.00, 1.00]` (clamped). `metrics` values: bool, bounded int
  (0…10¹²), bounded float, or digest. Lists/dicts/raw strings are dropped.
* `ring` matches `^RING_[1-4]_[A-Z_]{3,48}$` else `RING_UNKNOWN`.
* `signal_type` matches `^[A-Z0-9_]{3,64}$` else `UNPARSED_SIGNAL_<hash>`.
* `timestamp_utc` forced to ISO-8601 Z; `event_id` charset-locked.

### Sanitized event schema (normative)

| Field | Type | Notes |
| --- | --- | --- |
| `event_id` | string | `evt_[a-z0-9]{12}` |
| `timestamp_utc` | string | `YYYY-MM-DDTHH:MM:SS(.sss)Z` |
| `ring` | string enum | `RING_1_PERIMETER_IDENTITY` · `RING_2_AI_DEFENSE` · `RING_3_ENDPOINT_SILICON` · `RING_4_NETWORK_HEALING` |
| `organ` | string | uppercase enum-ish, free-form `^[A-Z0-9_]{3,64}$` |
| `signal_type` | string | e.g. `RANK1_CONDENSATION_DETECTED`, `TURBULENT_SESSION_REPLAY`, `PARITY_ENTROPY_COLLAPSE`, `UNACCOUNTED_POWER_RESIDUAL`, `INDIRECT_INJECTION_BLOCKED`, `JAILBREAK_TRAJECTORY_DEFLECTED`, `MISMATCH_SHIELD_SPLICED`, `PERCOLATION_CUT_EXECUTED` |
| `severity` | number | 0..1 |
| `entities` | object | keys ∈ `host_id, user_id, vlan_id, session_id, process_hash, agent_id, doc_hash, service_id, cluster_id` (+ unknown keys → digest); values: `*_<6HEX>` tokens, `sha256:…`, `pid:…` |
| `metrics` | object | bounded numerics / bools / digests only |

Entity-token grammar: `^(HOST|USER|VLAN|SESS|PROC|AGENT|DOC|SVC|CLUS)_[0-9A-F]{6}$`.
Legacy values already matching `^(HOST|USER|VLAN|SESS|PROC|AGENT|DOC|SVC|CLUS)_[A-Za-z0-9].*`
or `pid:`/`sha256:` pass through unchanged (the mock feeds use this).

## 3. Plane 3 action contract — the 10 tools

The Commander outputs ONLY this fixed allowlist (`commander/tool_schemas.json`).
Every action: `{"tool": <name>, "args": {…}, "rationale": "≤ 20 words"}`.

| # | tool | args (required) | Governor behavior |
| --- | --- | --- | --- |
| 1 | `drop_bec_cluster` | `cluster_id:str`, `ttl_seconds:int 60..86400` | budget-free; drops bot cluster at edge |
| 2 | `revoke_turbulent_session` | `session_id:str`, `user_id:str`, `require_fido2:bool` | budget-free |
| 3 | `quarantine_ai_document` | `doc_hash:str`, `agent_id:str` | budget-free |
| 4 | `clamp_lyapunov_steering` | `model_id:str`, `stiffness_gain:number 0.05..1.0` | budget-free |
| 5 | `arm_page_curve_traps` | `host_id:str`, `density_level:enum(low,standard,high)` | budget-free (arms; never destroys) |
| 6 | `isolate_thermal_anomaly_host` | `host_id:str`, `dump_hardware_trace:bool` | **host-quarantine budget** (5 / 5 min); Tier-0 host ⇒ BLOCKED |
| 7 | `execute_percolation_cut` | `target_spectral_radius:number 0.5..0.99`, `preserve_tier0_vlans:bool` | **VLAN-cut budget** (3 / 5 min); `preserve_tier0_vlans` must be `true`; Tier-0 VLAN in args ⇒ BLOCKED |
| 8 | `deploy_muts_ebpf_shield` | `service_id:str`, `patch_profile_id:enum(bounds_check_v1,cfi_v1,syscall_filter_v1)` | **eBPF-splice budget** (4 / 5 min) |
| 9 | `set_service_readonly` | `service_id:str`, `ttl_seconds:int 60..86400` | **host-quarantine budget** |
| 10 | `escalate_human_stepup` | `incident_id:str`, `severity:number 0..1`, `summary:str ≤500` | always APPROVED (it only asks a human) |

Orchestrator validation (B) *and* Governor validation (B, defense-in-depth)
both enforce this. A organ RPCs accept the same ten tools and nothing else.

### Governor decision object (normative)

```json
{
  "decision": "APPROVED | BLOCKED | ESCALATE",
  "tool": "isolate_thermal_anomaly_host",
  "args": { "…" : "…" },
  "reasons": ["tier-0 protected asset(s) referenced: ['HOST_ER_DB_PRIMARY']; …"],
  "autonomy_mode": "GUARDED_AUTO",
  "ts": 1795130400.215,
  "ledger_seq": 41,
  "ledger_hash": "…"
}
```

Semantics: `APPROVED` → executor runs the organ RPC. `BLOCKED` → never run;
ledger entry written; dashboard shows a red banner. `ESCALATE` → autonomy
frozen for that budget category for 5 min; human required.

## 4. Plane 2 service API (FastAPI) — dashboard + B consume this

Base URL: `http://<host>:8080` (config: `--port`). CORS: permissive, no credentials.

| Method | Path | Body → Response |
| --- | --- | --- |
| GET | `/` | → service card JSON (`{"service","status","dashboard","endpoints"}`) |
| GET | `/api/health` | → `{"status":"ok","planes_3_4":true,"commander_mode":"slm\|fallback_rules\|unavailable","uptime_sec":…}` |
| GET | `/api/state` | → `{"buffered_events":n,"entity_graph":{…},"last_plan":{…}\|null,"orchestration_count":n,"recent_events":[SanitizedEvent…(≤20)]}` |
| POST | `/api/ingest` | SanitizedEvent **or array** of them → `{"accepted":k,"received":n}` — never 4xxs a single bad event (it is dropped, not bounced) |
| POST | `/api/orchestrate` | no body → full pipeline bundle `{"status","trigger","plan_id","commander_mode","actions","decisions","results","brief"}` |
| WS | `/ws/telemetry` | server→client messages below; client may send any text (keepalive) |

### WebSocket message envelope (dashboard contract)

All frames: `{"type": string, "data": object}`.

| `type` | `data` payload | When |
| --- | --- | --- |
| `hello` | `{"buffered_events": n}` | on connect |
| `event` | `SanitizedEvent` (§2) | every accepted ingest |
| `action_plan` | bundle (same shape as `/api/orchestrate` response) | after each orchestration (auto on sev ≥ 0.8, or manual) |

The UI **must** tolerate unknown message types (forward-compat) and must not
assume ordering between `event` and `action_plan` frames.

### Entity graph payload (`/api/state.entity_graph` and inside pipeline context)

```json
{
  "window_sec": 600,
  "node_count": 42,
  "edge_count": 87,
  "nodes": ["HOST_AB12CD", "USER_99AA..", "…"],
  "edges": [{"src": "SESS_…", "dst": "USER_…", "kind": "linked"}, "…"],
  "chain": "SESSION -> USER -> HOST -> VLAN -> SERVICE"
}
```
Node/edge lists are truncated to 200/500 entries.

## 5. Audit ledger record shape

Append-only JSONL, one record per line. Each record:

```json
{"seq": 41, "ts": 1795130400.215, "record_type": "governor_decision|orchestration|rollback_executed|watchdog_event",
 "prev_hash": "<sha256 of previous record or GENESIS>", "payload": {…}, "hash": "<sha256 of this record sans hash>"}
```

`AuditLedger.verify()` → `{"valid": true|false, "entries": n, "head": <hash>}`.
The stage demo shows `valid: true` live; tampering any byte breaks
verification at that `seq` (test: `tests/test_audit_ledger.py`).

## 6. Planner output (Commander → Governor)

```json
{
  "plan_id": "plan_…",
  "kill_chain_stage": "recon|initial_access|execution|persistence|lateral_movement|impact",
  "correlated_entities": ["HOST_…", "USER_…"],
  "actions": [ {"tool": "…", "args": {…}, "rationale": "…"} ],
  "brief": "≤ 120 words, plain English, for the CISO",
  "commander_mode": "slm | fallback_rules | mock",
  "generated_at": 1795130400.215
}
```

## 7. Error & degradation semantics

| Failure | Behavior |
| --- | --- |
| SLM unreachable / invalid JSON | Orchestrator falls back to deterministic rules; `commander_mode: "fallback_rules"` |
| Sanitizer receives garbage | Event dropped silently; counters in `/api/state` reflect the drop |
| Budget exhausted | Governor returns `ESCALATE`, freezes category for 5 min, writes ledger entry |
| Ledger write fails | Exceptions propagate — the Governor never approves silently |
| WS client disconnects | Server drops the client; no backpressure on the reflex path |
| Orchestration itself crashes | Logged; telemetry keeps flowing; `/api/health` shows `commander_mode` |

## 8. Versioning & changelog

`CONTRACT_VERSION = "1.0.0"`. Bump minor for additive, major for breaking.

| Version | Date | Change |
| --- | --- | --- |
| 1.0.0 | 2026-11-20 | Initial freeze. SanitizedEvent schema, 10-tool allowlist, WS envelope (`hello/event/action_plan`), REST surface, degrade semantics. |
| 2.1.0 | 2026-11-20 | FORTRESS appendix: signed telemetry, verified gate, replay defense, tripwire freeze, TCB N-version cross-check, ledger anchor, manifest boot check, additive REST/WS fields. |

---

## Appendix v2.1 (FORTRESS) — additive deltas, same freeze rules

`CONTRACT_VERSION` semantics: these are **additive** to v1.0.0. UIs that
ignore the new fields keep working. Nothing in v1.0.0 was removed or
narrowed except where marked **BREAKING-for-unsigned-producers**.

### A. Organ → bus authentication (**BREAKING-for-unsigned-producers**)

Internal organs MUST emit events carrying
`mac = HMAC-SHA256(EIGENSHIELD_BUS_KEY, canonical_json(event without mac))`.
The bus verifies on ingest:

* Events that verify are marked `"verified": true`, enter the entity graph,
  and are eligible to trigger orchestration.
* Events that do NOT verify are marked `"verified": false`, stay visible in
  `/api/state.recent_events` (they are attack evidence), are **never**
  processed by the Commander or the Governor, and never trigger the
  entity graph or auto-orchestration.
* Verified duplicates are replay-dropped for 600 s (`SeenEventCache`).

`SanitizedEvent` therefore gains an out-of-band field set by the bus only:
`"verified": bool`. Producers MUST NOT set it.

### B. `/api/ingest` response

```json
{"accepted": 7, "received": 7, "unverified": 0}
```

`unverified` is additive. `accepted` counts events admitted to the buffer
(both verified and unverified-but-visible); `replay_dropped`/`unverified_held`
counters are in `/api/state.fortress`.

### C. `/api/orchestrate` — new outcome

```json
{"status": "HELD_UNVERIFIED_EVIDENCE",
 "reason": "no organ-signed telemetry in window; AI path held closed",
 "unverified_events": 7}
```

The Commander now consumes **verified events only**. If none exist, no plan
is produced and no action reaches the Governor.

### D. `/api/state` — new fields

```json
{ "governor": {"config_integrity": "ok | TAMPERED | UNVERIFIED | unknown", …},
  "fortress": {"telemetry_mac": true, "unverified_held": n, "replay_dropped": n,
               "tripwire": {"frozen": false, "frozen_until_in_sec": 0.0,
                            "frozen_reason": "", "trip_count": 0}} }
```

### E. Governor decision object — new fields

`"fortress_tcb"`: `"ok | tcb_override | tcb_mismatch | tcb_error_failclosed | frozen | fortress_absent"`.
Any non-`ok`/`fortress_absent` value means the independent TCB rejected or
froze the action; the decision is `BLOCKED` and the tripwire may have fired.

### F. Audit ledger

Each append re-pins an HMAC-sealed side anchor (`<ledger>.anchor`).
`AuditLedger.verify()` now also cross-checks the anchor and reports
`{"valid": false, "reason": "ledger anchor mismatch: …"}` on truncation
re-forgery that passes the hash chain alone.

### G. Boot-time integrity

Deployments SHOULD run
`python -m fortress.boot_manifest --check config/manifest.json` before
starting the bus (exit 2 ⇒ refuse to boot). Absent a manifest, the bus boots
with `config_integrity: "UNVERIFIED"` — visible, never silent.

