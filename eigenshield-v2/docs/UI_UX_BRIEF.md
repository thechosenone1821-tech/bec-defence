# UI/UX BRIEF — EIGENSHIELD v2.0 SOC Command Dashboard

**Audience:** UI/UX design + frontend engineering (not backend) · **Deliverable:**
the live SOC dashboard rendered against the frozen backend contract · **Repo
location:** `dashboard/` · **Backend is off-limits** — you consume it, you
don't modify it.

---

## 0. What you're building, in one line

A zero-dependency, wall-of-monitors command surface that makes a room full of
judges gasp when a hospital campus repels a ransomware worm in 50 ms — and
that an actual CISO would trust at 3 a.m.

Read first: `README.md` (root, EIGENSHIELD vision) → `docs/INTERFACE_CONTRACT.md`
(your exact data shapes) → `docs/WORK_SPLIT.md` (scope boundaries).

## 1. Product context

EIGENSHIELD is an autonomous "immune system" for a hospital + bank campus.
Eight reflex organs stop attacks in under 2 ms; a tiny local AI commander
(3–4 B params, on-prem) correlates the weak signals; a deterministic
"Governor" (zero AI) hard-blocks anything dangerous — e.g. it can *never*
isolate the ICU. Your dashboard is the human's window into all of it.

**Showcase beats (the stage demo you'll design for):**

1. **ACT 1** — 50k botnet sessions excised in ~1 ms (Ring 1 lights up).
2. **ACT 2** — a judge yells sentences at an AI; it gets snapped back
   (Ring 2 deflects, < 1 ms).
3. **ACT 3** — ransomware dies on its first 4 KB write; a hidden CPU thread
   is flagged by physics (Ring 3).
4. **ACT 4** — a worm is boxed out of the hospital VLANs; a zero-day is
   healed twice, 48 ms apart (Ring 4).
5. **ACT 5** — the AI *hallucinates* "isolate the ER database" — the Governor
   hard-blocks it on the big screen. Tier-0 stays green. (This is the act
   that wins the room.)

## 2. Audiences & jobs-to-be-done

| Persona | Context | What they must see instantly |
| --- | --- | --- |
| **CISO / VP Security** | Stage, demo, board videos | "Is Tier-0 safe?" → giant status seal; "what just happened?" → 3-line AI brief |
| **SOC analyst (L1/L2)** | 27″ wall + analyst laptop (1440px) | Live rings, kill-chain entity graph, approve/escalate context |
| **SRE / Infra** | 3 a.m. incident | Which VLAN edge got cut, which budget remains, rollback watchdog state |
| **Auditor / compliance** | After-action review | Hash-chained ledger viewer + one-click `verify()` (valid = chain intact) |

Design tension to manage: *calm confidence* (nothing is on fire most of the
time) vs. *alarm legibility* (when the Governor fires, it must be unmissable).

## 3. Scope boundaries

**You own:** everything under `dashboard/` — HTML/CSS/JS, assets, a
`config.js` with the backend base URL, and your own dev tooling.

**You never touch:** `reflexes/`, `bus/`, `commander/`, `governor/`,
`config/`, `simulator/`, Python at all. If an endpoint or field is missing,
file an issue labeled `ui-contract` — a backend dev lands it behind a
contract minor bump.

**Stack rule (from the hackathon constitution):** zero-framework
HTML5/CSS3/JS + Canvas (no React/Vue/Angular builds, no CDN deps, no build
step). Justification: it must run offline in the demo venue on a laptop with
no network. If your team strongly prefers a framework, it must vend everything
locally (no CDN) and be justified in the handoff doc — but the default answer
is vanilla.

## 4. Routes & screens

Single-page app, hash-routed (`#/overview`, `#/incidents`, …). Left nav rail
(icon + label), top status bar, main canvas area, right intelligence rail
(collapsible).

### 4.1 Command Overview (`#/overview`) — the hero screen

* **Left 60 % — Ring topology canvas.** Four concentric rings (Ring 1…4),
  nodes = VLANs/hosts/services (data from `/api/state.entity_graph`,
  reconciled with `config/company_topology.json` reference asset provided by
  backend in the handoff). Edges pulse on active alerts. Node glyphs:
  circle=host, rounded-square=VLAN, diamond=service, lock badge=Tier-0.
  Color encodes worst current severity (green→amber→red). Ring-4 containment
  animation: severed edges draw apart with a visible "CUT" tag + reason chip
  (`w=1.0 — worm path severed`).
* **Top bar — Campus status seal.** Three states: `NOMINAL` (green, calm
  pulse), `DEGRADED` (amber — commander offline or budget partial),
  `GOVERNOR INTERVENTION` (red — last human-required act). Beside it: rolling
  24 h counters (threats auto-stopped, reflex p99 ms, Tier-0 probe latency,
  budgets remaining).
* **Right rail — Live event ticker** (WS `event` feed): last ~12 events,
  monospace, severity dot, signal_type, opaque token, relative time
  ("0.9 ms ago" for reflex actions). Click → Incident detail.
* **Bottom strip — Commander brief card.** Latest `action_plan` frame:
  `kill_chain_stage` chip, up to 4 proposed actions with
  APPROVED/BLOCKED/ESCALATE chips, the 120-word brief. Badge shows
  `commander_mode`: `slm` (cyan) / `fallback_rules` (amber, labeled
  "deterministic fallback — model optional" — this is a *feature*, say so).

### 4.2 Incident Timeline (`#/incidents`)

* Vertical timeline of the active kill chain:
  `SESSION → USER → HOST → VLAN → SERVICE` with stage markers
  (recon → initial_access → … → impact).
* Each node card: opaque token, first/last seen, severity sparkline, organ
  that fired, local reflex action (e.g. `PID_TERMINATED_0.9MS`).
* Actions panel: every governor decision with reasons (from `decisions[]`),
  BLOCKED ones expanded with full reason string. This is where ACT 5 lives on
  the wall: red BLOCKED card, reason text, "Tier-0: STILL ONLINE" green seal.

### 4.3 Tier-0 Health Board (`#/tier0`)

* One huge card per protected asset (VLAN ICU, VLAN COLDCHAIN, VLAN CORE-AUTH,
  HOST_ER_DB_PRIMARY, HOST_BLOODBANK_CTRL_01 — from `policy.yaml`): probe
  latency gauge vs 120 ms SLO, last-cut count, lock icon, uptime % vs 99.99
  target.
* Watchdog status: idle/armed/probing/ROLLED-BACK (red flash + banner
  "Governor auto-reverted <action> — see ledger seq #n").
* "Why can't the AI touch this?" expandable explainer (crown-jewel lock,
  blast-radius budget, 15-second rollback — three bullet points, one line each).

### 4.4 Audit Ledger Viewer (`#/ledger`)

* Virtualized table: seq, time, record_type, prev_hash (truncated), hash
  (truncated), expandable payload JSON (syntax-highlighted, read-only).
* **Verify chain** button → calls a tiny backend endpoint if provided
  (`GET /api/ledger/verify` — if absent in contract v1, do it client-side from
  `/api/ledger/tail`… **no** — do not invent endpoints; instead render chain
  status from the `ledger_hash`/`ledger_seq` fields present in decisions, and
  link the raw JSONL file path. Backend will add `/api/ledger/verify` in
  contract v1.1 — track issue).
* Search by token (`HOST_…`), by tool, by decision. Export visible rows as JSONL.

### 4.5 Red-Team Demo Control (`#/demo`) — visible only in demo mode

* Toggle: `?demo=1` in URL or `localStorage.eigenshield_demo=1`. Hidden in
  production builds.
* Five ACT buttons, one per stage act. Each sends a canned sanitized event
  batch to `POST /api/ingest` (exact payloads in *Appendix A* below — backend
  provides these as fixtures in `dashboard/demo-fixtures/`).
* Big countdown + act title overlay ("ACT 3 — THE 4 KB TRAP") for stage pacing.
  Success criteria chips light up as WS frames arrive (e.g. "PID_TERMINATED
  received ✓").
* A `commander_mode` pill in the top bar shows whether the real SLM answered
  or the deterministic fallback — judges find this fascinating; make it visible.

### 4.6 Policy & Settings (`#/policy`) — read-only

* Renders `config/policy.yaml` as a readable page: autonomy mode
  (`GUARDED_AUTO`), crown-jewel lists, 5-minute budget usage meters (live from
  `/api/state.last_plan` + governor status when available), min preserved
  uptime floor, rollback parameters. Editing happens via PR, not the UI —
  show a lock, not a save button.

## 5. Design system

**Theme:** "Hospital-grade mission control." Dark, low-blue-light, high
contrast, zero gratuitous chrome.

* Palette: background `#070B14`; panels `#0E1626` / `#131F36`; hairline
  `#1E2A44`; text `#E6EDF7` / secondary `#8CA3C3`; accent cyan `#22D3EE`;
  ok `#34D399`; warn `#FBBF24`; danger `#FB4D5E`; crown-gold `#F5C518`
  (Tier-0 only — used nowhere else).
* Type: Inter (or system-ui stack) for prose; `ui-monospace/SFMono/JetBrains
  Mono` for telemetry, tokens, hashes. Tabular numerals everywhere numbers move.
* Grid: 12-col, 24 px gutter, 1440 px and 2560 px reference frames; canvas
  ring view scales fluidly; side rails fixed (320 px / 400 px).
* Motion: 60 fps or nothing. Event tick-flash 600 ms; ring pulse ≤ 0.6 Hz;
  act overlay crossfade 300 ms; **no** parallax, no particles, no auto-play
  audio. `prefers-reduced-motion` disables all non-essential animation.
* Sound: optional short blip on GOVERNOR INTERVENTION only (mute default).
* Iconography: 1.5 px stroke line icons; lock glyph mandatory for Tier-0;
  custom eight-organ glyph set (request from backend if metaphors unclear).
* Density: analyst Mode (dense) vs Wall Mode (projector-legible ≥ 24 px
  base font) — one toggle, persisted.

**Components:** status seal, metric tile, event row, severity chip, tool-chip
(10 tools, each with fixed hue), decision banner, lock card, budget meter,
kill-chain stepper, ledger row, ACT button, toast (for backend unreachable).

**Accessibility:** WCAG 2.1 AA; color is never the only signal (icons +
labels); focus-visible rings; full keyboard nav for rails; screen-reader
landmarks (`banner/navigation/main/complementary`); canvas ring view has a
list-view fallback table for SR users (same data).

## 6. Data contracts (authoritative summary)

Base URL: `window.EIGENSHIELD_API` from `config.js` (default
`http://localhost:8080`). CORS enabled, no auth in the demo (OIDC hook noted as
post-hackathon).

* `GET /api/health` → `{status, planes_3_4, commander_mode, uptime_sec}`
* `GET /api/state` → `{buffered_events, entity_graph{window_sec,nodes[],edges[],chain}, last_plan, orchestration_count, recent_events[]}`
* `POST /api/ingest` (single or array) → `{accepted, received}`
* `POST /api/orchestrate` → full bundle `{status, trigger, plan_id, commander_mode, actions[], decisions[], results[], brief}`
* `WS /ws/telemetry` → `{type:"hello"|"event"|"action_plan", data:{…}}`
  (full schemas: `docs/INTERFACE_CONTRACT.md` — treat it as law; if it
  conflicts with this brief, the contract wins)

**Resilience rules:** WS drops → 1 s backoff reconnect + "LIVE" pill goes
gray/amber; exponential backoff to 10 s; poll `/api/state` every 5 s as a
fallback so the wall never looks dead; backend fully down → last-known state
with red "BACKEND OFFLINE — SHOWING LAST KNOWN" banner (never fake freshness).

**Sample fixtures** for offline work (backend will drop these into
`dashboard/demo-fixtures/` at handoff):
`event-ring1-rank1.json`, `event-ring3-parity.json`, `event-ring4-muts.json`,
`plan-fallback-5-actions.json`, `decision-tier0-blocked.json`.

## 7. Demo-mode event fixtures (ACT buttons)

Each button POSTs a JSON array to `/api/ingest`:

* **ACT 1** — `RANK1_CONDENSATION_DETECTED` (severity 0.88, cluster entities) +
  `TURBULENT_SESSION_REPLAY` (0.74, session/user entities).
* **ACT 2** — `INDIRECT_INJECTION_BLOCKED` (0.70, doc/agent entities) +
  `JAILBREAK_TRAJECTORY_DEFLECTED` (0.66, agent entities).
* **ACT 3** — `PARITY_ENTROPY_COLLAPSE` (0.96, host/process entities) +
  `UNACCOUNTED_POWER_RESIDUAL` (0.71).
* **ACT 4** — `MISMATCH_SHIELD_SPLICED` (0.90, service entities) +
  `PERCOLATION_CUT_EXECUTED` (0.85, edge metrics).
* **ACT 5** — raw poisoned payload (shows sanitizer digestion: string
  `"user": "admin; IGNORE ALL RULES …"` becomes an opaque token) **plus**
  instructions panel pointing judges to
  `python simulator/demo_05_governor_hallucination.py` for the full scripted
  block — the Tier-0 hard-block is a terminal act, don't fake it in-browser.

## 8. Deliverables & handoff

1. Hi-fi Figma (or penpot) of the 6 screens + component sheet; Wall Mode and
   analyst Mode frames for Overview + Incidents.
2. `dashboard/` implementing the above: `index.html`, `style.css`, `app.js`
   (modules welcome, no bundler), `config.js`, `demo-fixtures/`, `README.md`
   (serve: `npx serve -l 3000 .` or any static server; note the WS URL).
3. Motion spec (timings/easings) + empty/error/offline states for every
   widget (draw them in Figma too).
4. Accessibility pass log (contrast ratios, SR walkthrough notes).
5. 10-minute demo runbook (click order for ACT 1→5) co-written with backend.

## 9. Milestones (aligns with backend plan)

| # | Day | Gate |
| --- | --- | --- |
| U1 | Day 2 | Figma direction ×2, wall-mode legibility test on a projector (room light on) |
| U2 | Day 4 | Overview + ticker wired to real `/api/state` + WS with contract fixtures |
| U3 | Day 7 | All 6 screens live; demo mode ACT 1–4 firing from fixtures |
| U4 | Day 9 | ACT 5 walkthrough rehearsal with backend; resilience drill (kill backend mid-demo → banner) |
| U5 | Day 10 | Freeze; handoff doc; tagged screenshots for the pitch deck |

## 10. Explicit non-goals

No editing of backend code or configs · no authentication/SSO in the demo
(contract lists it as v1.1+) · no mobile app · no historical analytics
(we show the live 10-minute window; "time travel" is out of scope) · no dark-
pattern engagement tricks — this is an operations tool, not a consumer app ·
no new sensors, thresholds or AI claims invented in the UI copy. If the UI
says "48 ms", that number comes from a metric, not marketing.

## 11. Open questions for backend (file as `ui-contract` issues)

1. `GET /api/ledger/verify` endpoint for the ledger screen (v1.1).
2. Topology static asset (VLAN graph layout hints) for the ring canvas.
3. Governor `status()` snapshot endpoint for budget meters (v1.1).
4. Whether Wall Mode needs a fullscreen browser-kiosk flag from backend env.

**When in doubt: calm, legible, honest. Show the machine thinking; never fake
it.**
