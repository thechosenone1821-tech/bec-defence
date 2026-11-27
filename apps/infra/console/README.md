# Read-only SOC console (Phase 8)

This is the operable Phase 8 console, not a placeholder. Open `/app/console` on
the unified Infra app. The page is same-origin and uses only a `read`-scoped
token supplied by the backend to `console.js`.

It shows the deterministic fixture campaign end to end: **verified detection →
proposal → Governor decision → ledger sequence**, with refusals highlighted as
first-class decisions. It also shows ledger verification, quarantine, metrics
and a read-scoped WebSocket stream. There is no button, route or script that
can override the Governor, append telemetry, alter a decision or mutate safety
state. The runtime remains dry-run; no real containment is performed.

Files:

- `index.html` — read-only layout and sequence table.
- `console.js` — same-origin GET reads plus one read-scoped WS stream.
- `__init__.py` — asset loader and read-only capability card.
