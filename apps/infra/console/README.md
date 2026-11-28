# Completed read-only SOC console

This is the operable Infra console, not a placeholder. Open `/app/console` on
the unified Infra app. The page is same-origin and uses a `read`-scoped token
for state, decisions, ledger, quarantine, metrics, campaigns and the read
WebSocket stream. It has no control that can mutate safety state. The header links to the separate `/demo/hospital` fake-hospital exercise.

The completed console adds:

- tab navigation for overview, campaign, ledger, organs and API explorer;
- a row filter for timeline, decisions and quarantine;
- a downloadable JSON snapshot and copyable status card;
- an API explorer that renders same-origin GET responses in the page;
- a detector-card view with per-organ rule metadata;
- WebSocket status with polling fallback;
- read-token fallbacks via `Authorization`, `X-API-Token`, a same-origin read
  cookie and a read-only `access_token` query parameter.

The runtime remains deterministic, read-only and dry-run. Commander is
disabled and no real containment is performed. Query tokens are accepted only
on read-only GET routes; ingest, ledger append and override paths still require
scoped headers or cookies.

The fake-hospital exercise is a separate page with its own isolated scenario.
Its start, step, play and reset controls do not mutate the canonical live
runtime. It shows signed and deliberately invalid synthetic events traversing
detector, quarantine, campaign fusion, Governor, ledger and dry-run executor.
