> Historical provenance: the retired voice-scorer code was removed from executable paths. Active status lives in [docs/STATUS.md](../docs/STATUS.md); see the [retired code note](../archive/provenance/RETIRED.md). Real-world privacy efficacy remains UNMEASURED.

# Phases 6–8 — Unified Infra Integration

**Status:** implemented and deterministically checked on 2026-11-26.
**Scope:** Phases 6, 7 and 8 only. Phase 9/10 are not started. VoiceGuard/MAYA
remain frozen and unintegrated; no AI/LLM/Commander/SLM/Ollama model endpoint or
inference was run. No real containment was performed.

This document is the current report for the active branch. The roadmap phase
definitions remain in [`COMBINED_SYSTEM_ROADMAP.md`](COMBINED_SYSTEM_ROADMAP.md);
source-controlled verification is in
[`../tools/check_phase678_integration.py`](../tools/check_phase678_integration.py)
and [`../tests/test_phase678_integration.py`](../tests/test_phase678_integration.py).
The decision record is
[ADR-014](adr/ADR-014-phase6-8-unified-integration.md).

---

## 1. What was actually integrated

The previous facade imported the legacy `spine.bus` and had only `/app/health`
and `/app/contract`. It has been replaced by one active runtime:

```
apps/infra/backend/app.py
    -> apps/infra/detectors.detect              (one signed-event contract)
    -> packages/spine/runtime.SafetyRuntime    (one ingest/decision/broadcast path)
       -> packages/governance.safety           (one planner + Governor + dry-run executor)
       -> packages/ledger.runtime_ledger       (one append-only hash chain)
       -> apps/infra/console                   (read-only SOC view)
```

The compatibility module [`../packages/spine/bus.py`](../packages/spine/bus.py)
no longer imports `spine.bus`; it delegates to the unified runtime and requires
the one detector contract. [`../apps/infra/backend/app.py`](../apps/infra/backend/app.py)
is a thin facade: it injects the detector, publishes `/app/health`,
`/app/contract`, `/app/console` and `/app/console.js`, and creates no second
FastAPI app or second WebSocket stream.

---

## 2. Phase 6 — one 8-organ detection ring

[`../apps/infra/detectors/registry.py`](../apps/infra/detectors/registry.py) owns
one `ORGANS` registry with exactly eight Sentinel shield organ records across
four rings. The legacy eight class names are lazy compatibility attributes in
[`../apps/infra/detectors/__init__.py`](../apps/infra/detectors/__init__.py);
they are not a second registry and are not imported by the active runtime.

The one contract is:

```text
detect(event, *, key) -> DetectionResult{status, state, reason, envelope, finding, quarantine}
```

Order is fail-closed:

1. The shared [`../packages/contracts/envelope.py`](../packages/contracts/envelope.py)
   validates the I1 signed envelope using the shared canonical JSON rule.
2. `unsigned`, `tampered`/forged, malformed and unknown-organ events are
   quarantined before any detector executes.
3. A rule fires only when **all** its required features are present and numeric.
   Missing features return `no_detection`, never a fabricated finding.
4. Every organ has `firing`, `silent` and `missing` fixtures in
   `ORGAN_FIXTURES`, exercised by checker and pytest.

The `voiceguard` string in the alias table is only an Infra feature-organ alias
to `cookie_fluid_turbulence`; it is not the frozen Citizen VoiceGuard/MAYA path.

---

## 3. Phase 7 — one deterministic safety brain

[`../packages/governance/safety.py`](../packages/governance/safety.py) contains
one `ExhaustivePlanner`, one `Governor`, one `DryRunExecutor` and one `Proposal`
type. The planner reads the pinned topology at
`raksha-code/spine/config/company_topology.json` through
[`../packages/contracts/config.py`](../packages/contracts/config.py), enumerates
every legal non-crown edge cut, host quarantine and egress-only fallback, and
computes blast radius by graph traversal.

Crown-jewel/Tier-0 cuts are impossible by construction:

- `Proposal.__post_init__` raises `UnsafeProposal` if a crown asset is the
  entity, an asset to sever, or in the blast radius, or if a crown gateway edge
  is cut.
- The planner never emits crown assets or gateway edges.
- The Governor repeats G0–G4 checks and has no `override` method.
- `POST /v1/decisions/{id}/override` returns `403` even with an admin token.

Refusals are first-class `refusal` ledger records. The order in
[`../packages/spine/runtime.py`](../packages/spine/runtime.py) is
**plan → Governor decide → ledger seal → dry-run simulation → WebSocket/API
decision broadcast**. The runtime has one `self.ledger.append(` write path,
`SafetyRuntime._seal`; `/v1/ledger/entries` also routes through that seal. The
hash chain is implemented by
[`../packages/ledger/runtime_ledger.py`](../packages/ledger/runtime_ledger.py)
and verified by `/v1/ledger/verify`.

The optional Commander is a status card in
[`../packages/governance/commander.py`](../packages/governance/commander.py):
`enabled=false`, `fallback_only=true`, `model_invoked=false`. The runtime never
calls it. No model module is imported.

---

## 4. Phase 8 — one operable app surface

The unified app exposes both the canonical `/v1` routes and the Phase 3
compatibility aliases required by `validate_routes`:

| Surface | Purpose |
|---|---|
| `POST /v1/telemetry` | signed ingest; `telemetry:write` scope, dedupe and rate limit |
| `GET /v1/state` | campaigns, topology, detections, timeline, ledger height |
| `GET /v1/decisions` | sealed allowances **and refusals** |
| `GET /v1/ledger/verify` | whole-chain canonical hash verification |
| `GET /v1/metrics` | counters, store counts and zero AI invocations |
| `GET /v1/quarantine` | unsigned/tampered/forged/unknown events, never actionable |
| `WS /v1/telemetry/stream` | one read-scoped stream; `/ws/telemetry` is the same function |
| `GET /` | preview root redirects to the read-only SOC console |
| `GET /app/console` | read-only SOC console |
| `GET /app/console.js` | same-origin JS with one injected `read` token |

The console in [`../apps/infra/console/README.md`](../apps/infra/console/README.md)
shows the full **detection → proposal → decision → ledger** sequence, with
refusals highlighted, plus ledger verification, quarantine, metrics and live WS
status. It uses only GET reads and one read-scoped WS connection. It has no
write route, override route, admin token, model endpoint or mutation control.

At startup a deterministic, synthetic fixture campaign is seeded in memory so a
judge can watch the sequence without `curl`. It is explicitly a fixture, not a
field/capture/real-network claim. The runtime remains dry-run.

---

## 5. Tests and exit gates

`tools/check_phase678_integration.py` and `tests/test_phase678_integration.py`
cover:

- eight organs, one registry, firing/silent/missing fixtures, no false
  accusation on missing features;
- unsigned, tampered, forged and unknown-organ quarantine before detection;
- crown cut construction failure, exhaustive planner coverage, allowed/refused
  decisions, dry-run-only receipts, append-only ledger and disabled Commander;
- one ledger write path and sealed-before-broadcast decision ordering;
- route profiles, scoped auth, rate limits, dedupe, quarantine, metrics,
  decisions/refusals, admin override `403`, console read-only checks and WS
  stream history;
- clean import with zero AI/VoiceGuard/MAYA/SLM/legacy-bus modules loaded;
- Phase 3, Phase 4, Phase 5 and frozen-asset gates still green.

Current consolidated counts and commands are recorded in
[`../BUILD_STATE.md`](../docs/STATUS.md) and
[`CHANGELOG.md`](CHANGELOG.md). Validation was deterministic/no-AI only; full
model-dependent suites remain deliberately out of scope.

---

## 6. Non-goals preserved

- No app-root merge and no third app.
- No VoiceGuard/MAYA integration or edit to frozen assets.
- No live Commander/AI model, no LLM/SLM/Ollama endpoint, no model inference.
- No real containment, no live host/VLAN/process/network mutation.
- No clone/field/real-network/real-world accuracy claim.
- No weakened signature, Governor, ledger, blast-radius or append-only rail.
- No commit or push was performed as part of this phase.

---

## 7. Final validation snapshot

- Root no-AI pytest: **196 passed / 0 failed / 4 warnings**.
- Legacy-cwd no-AI pytest: **171 passed / 0 failed / 4 warnings**.
- Deterministic Node tests: **60 passed**.
- Total: **256 passing checks** (196 root Python + 60 Node; legacy cwd is a
  subset and is not double-counted).
- `tools/check_phase678_integration.py`, Phase 5/4/3 checkers, MessageGuard
  eval `--check`, 5 config pins, 28 frozen assets, `compileall`,
  `git diff --check`, `git diff --cached --check` and **336/336** local Markdown
  links are green.
- Source under test: **28,005** Python lines; `git status` has **164** files and
  **0** generated `__pycache__`/`.pyc`/`.venv` artifacts.
- HEAD remains `78d928f`; no commit or push was performed.
