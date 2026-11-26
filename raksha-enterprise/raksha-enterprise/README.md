# Project Raksha — Part 6 Enterprise Backend

Backend-only implementation of Part 6: it moves **signed telemetry**, runs the
**organ detectors**, fuses **cross-leg campaigns**, proposes containment, records
**Governor decisions (including refusals)** in an **append-only ledger**, exposes
observability over **HTTP + WebSocket**, lets **RAAVAN** replay attacks through the
normal verification path, and **measures itself** with a deterministic eval harness.

No frontend ships here — the API is the product. A console can sit on top of
`/v1/state`, `/v1/decisions` and the WS stream; it can never override a decision.

---

## Architecture

```
 sensors ──POST /v1/telemetry──▶ ┌────────────────────  raksha bus (FastAPI)  ─────────────────┐
                                 │  auth (scoped tokens) → ingest (HMAC verify, dedupe,        │
 RAAVAN ──signed attack corpus──▶│      rate-limit, quarantine)                                │
                                 │      → detect (8 organs, frozen rules)                      │
                                 │      → fuse  (campaign via opaque case token, both legs)    │
                                 │      → plan  (containment proposals, BFS blast radius)      │
                                 │      → decide (Governor G1–G4: refusals are first-class)    │
                                 │      → seal  (append-only SHA-256 ledger, SQLite)           │
                                 │  GET /v1/state  /v1/decisions  /v1/ledger/verify  /v1/metrics│
                                 │  WS  /v1/telemetry/stream (detections, proposals, decisions)│
                                 └──────────────────────────────────────────────────────────────┘
                                   events.db (raw+quarantine)   ledger.db (hash chain)
```

Module map:

| Path | Responsibility |
|---|---|
| `raksha/events.py` | I1 envelope: strict validation, canonical JSON, HMAC-SHA256 sign/verify |
| `raksha/organs/` | 8 detector modules + registry; missing features never flag (R3) |
| `raksha/pipeline/ingest.py` | dedupe, per-source rate limit, verify-or-quarantine |
| `raksha/pipeline/fusion.py` | campaign state machine (legs, organs, entities, risk score) |
| `raksha/pipeline/topology.py` | asset graph; BFS containment math (`carries_traffic` links only) |
| `raksha/pipeline/planner.py` | proposals: node quarantine / edge cut, computed blast radius |
| `raksha/pipeline/governor.py` | policy G1 crown-gateway, G2 crown-target, G3 blast-cap, G4 precision |
| `raksha/pipeline/runner.py` | orchestrator; stage latencies into metrics; seal-before-broadcast |
| `raksha/ledger/` | hash chain (pure), SQLite store (WAL), operator CLI |
| `raksha/storage/db.py` | events + detections store; quarantine query |
| `raksha/bus/` | FastAPI app factory, scoped token auth, WS hub, metrics endpoint |
| `raksha/raavan/` | red-team player: signs its attack corpus and replays it like a sensor |
| `tools/` | `gen_corpus.py` (deterministic corpora, seed 20261126), `run_evals.py` (EVALS.md) |

Design-honesty framing (kept from the roadmap): **RAAVAN emits detections of its own
attacks** through the same verification path a real sensor uses — the only end-to-end
path a sandbox can honestly exercise. Its reports never claim a real attack was stopped.

---

## Quickstart

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install ".[api,dev]"        # core engine is stdlib-only; api extra = fastapi+uvicorn

make seed                       # bootstrap: data dir, sensor key, tokens (printed once), topology
make api                        # uvicorn on 127.0.0.1:8000

# second terminal — attack the live bus (sensor token + key were set at seed time):
python3 -m raksha.raavan.player --bus-url http://127.0.0.1:8000 \
    --token <sensor token> --sensor-key-hex <RAKSHA_SENSOR_KEY hex>
# or run RAAVAN embedded (no server):
python3 -m raksha.raavan.player --data-dir ./data

make evals                      # regenerate data/evals/{EVALS.md,summary.json}
make ledger-verify              # recompute the whole hash chain
make test                       # 79 tests
```

Docker: `docker build -t raksha-backend . && docker run -p 8000:8000 raksha-backend`
(first boot inside the container prints the once-only tokens to the container log).

The demo deployment ships with topology `c2247` (campaign *Staged Ransom via Vendor
Invoice*): a voice-clone scam call authorizes a poisoned vendor invoice; a replayed
banking session releases payment; ransomware stages on the build server and probes the
Governor. The planner proposes the ICU cut (severing the crown segment uplink — 14
assets lose connectivity by BFS count); **the Governor refuses it** (G1) and the
fallback (egress-only isolation, 6 assets) is allowed. All of it is computed, not authored.

---

## API reference

Auth: `Authorization: Bearer <token>` or `X-API-Token`. Scopes: `telemetry:write`,
`read`, `admin` (admin still cannot override decisions).

| Method | Path | Scope | Notes |
|---|---|---|---|
| GET | `/healthz` | — | liveness, version |
| POST | `/v1/telemetry` | telemetry:write | one I1 envelope; returns verified state, detections, proposals, decisions. 422 on malformed envelope; 429 over rate limit |
| GET | `/v1/state` | read | campaigns + topology (nodes flagged `detected`) + ledger height |
| GET | `/v1/campaigns` | read | fused campaign list with legs/organs/risk |
| GET | `/v1/decisions` | read | ledger decisions incl. refusals, rule ids, fallbacks |
| POST | `/v1/decisions/{id}/override` | admin | **always 403** — append-only by design (R6) |
| GET | `/v1/ledger/head` | read | height + head hash |
| GET | `/v1/ledger/verify` | read | full chain recompute → ok/height/first_bad_seq |
| POST | `/v1/ledger/entries` | admin | operator block (ops-note); hashed like everything else |
| GET | `/v1/quarantine` | read | tampered/unsigned events — kept, never actionable |
| GET | `/v1/metrics` | read | counters + stage latency p50/p95 + store counts |
| WS | `/v1/telemetry/stream?token=` | read | `hello`, `detection`, `proposal`, `decision` frames |

Telemetry envelope (I1): `event_id, ts, organ, campaign_id, case_id, leg, severity,
entity, summary, payload, sig_alg, sig` — `sig` = HMAC-SHA256 over the canonical JSON
(sorted keys, compact separators) of the event with `sig` excluded. Canonicalization
is byte-identical across Python, the browser console and the eval harness.

Governor rules (frozen, first match wins):
`G1 CROWN-GATEWAY` refuse any cut of the crown segment uplink, offer fallback ·
`G2 CROWN-TARGET` refuse containment of a crown asset itself ·
`G3 BLAST-CAP` refuse > 8 severed assets · `G4 PRECISION` allow the rest.
Decisions are sealed to the ledger **before** they are returned or broadcast.

---

## Measured numbers

`data/evals/EVALS.md` (regenerate: `python3 tools/gen_corpus.py --out ./data/evals &&
python3 tools/run_evals.py --out ./data/evals`). Fixture corpora, seed 20261126,
frozen rules shared verbatim with the service — evals cannot drift from the code.

| Metric | Value |
|---|---|
| Detection rate (aggregate, 335 attack rows) | **91.9 %** (85.0–97.8 % per organ) |
| False-positive rate (1200 clean rows) | **0.08 %** |
| verify_event | µs-scale per event (HMAC over canonical JSON) |
| organ.detect / fusion.add | µs-scale per event |
| planner.proposals_for | ms-scale per fused campaign (BFS on real topology) |
| ledger.append | ms-scale per block (SQLite WAL) |
| End-to-end c2247 campaign (18 events, full pipeline incl. SQLite, 50 fresh runs) | **p50 2.5 ms / p95 3.7 ms** |
| Integrity self-check | 40 signed verify · 5 tampered flagged · 10 unsigned flagged |

**Scope honesty:** these are measurements of this codebase on fixture corpora in a
sandbox — not deployment claims. Governor latency under production load, detection
rates against a live adversary, and real-network containment cost remain **unmeasured**
and are listed as such in EVALS.md's claims ledger. The demo case token is low-entropy;
production must use high-entropy random case tokens.

---

## Security model (and its limits)

* **Integrity:** unsigned/tampered events are stored with `verified=0` and quarantined;
  they never reach detection. The ledger is append-only; `verify` recomputes every hash
  and reports the first bad block (unit-tested against direct SQLite tampering).
* **Auth:** static token file with sha256-hashed tokens and scopes; seeded at first
  boot; plaintext shown exactly once. Token rotation = regenerate the file.
* **Limits (documented, deliberate):** no TLS (terminate at your proxy), no mTLS
  between sensor and bus, no multi-node ledger consensus (single-writer SQLite; Part 7
  owns durability at scale), tokens are not a full IAM, `RaavanPlayer` holds the sensor
  key by definition (it *is* the adversarial sensor in this build).

## Operations

* State: `data/events.db`, `data/ledger.db`, `data/keys/`, `data/topology.json`
  (all under `RAKSHA_DATA_DIR`; mount as a volume in Docker).
* Logs: single-line JSON on stderr (`RAKSHA_LOG_LEVEL`).
* Backups: copy `ledger.db` (WAL mode; use `sqlite3 ... ".backup"` for consistency).
* Verify any time: `make ledger-verify`, or `GET /v1/ledger/verify`.
* The topology file is deployment config — edit it to your asset graph; blast-radius
  math and Governor thresholds (`RAKSHA_*` overrides on Settings) follow it.

## Tests

79 tests, ~0.4 s: envelope validation and HMAC round-trips; organ boundaries (missing
features never flag); ledger tamper detection at the exact block; planner blast-radius
math on the real topology (14-asset ICU cut, 6-asset egress cut, crown never severed);
Governor rule precedence; the full c2247 scenario end-to-end (13 detections, 2
quarantines, 3 allowances, 1 refusal, ledger height +9); bus API incl. auth scopes,
422 envelope handling, the always-403 override, and a live WebSocket broadcast test.
