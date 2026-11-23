# dashboard/ — SOC Command Dashboard (UI/UX team owns this folder)

This folder is intentionally empty except this file. The UI/UX team builds
the entire dashboard here, against the frozen backend contract.

**Start here → [`docs/UI_UX_BRIEF.md`](../docs/UI_UX_BRIEF.md)**

Hard rules:

- You own 100% of this folder. You may not edit anything outside it
  (Python backend, configs, demos). File a `ui-contract` issue instead.
- Stack: zero-framework HTML5/CSS3/JS + Canvas. No CDN, no build step,
  must run offline at the demo venue.
- Consume the backend exactly as specified in
  [`docs/INTERFACE_CONTRACT.md`](../docs/INTERFACE_CONTRACT.md)
  (`GET /api/state`, `POST /api/ingest`, `POST /api/orchestrate`,
  `WS /ws/telemetry`). Base URL via `config.js` (default `http://localhost:8080`);
  CORS is enabled, no credentials.
- Demo mode (`?demo=1`) unlocks the ACT 1–5 trigger panel; fixtures land in
  `dashboard/demo-fixtures/` from backend at handoff.

Backend devs: please don't add files here — the UI/UX team's review is the
gate for everything inside `dashboard/`.
