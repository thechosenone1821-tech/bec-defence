# Infra backend

`app.py` is a thin facade over `packages/spine/bus.py`. It adds an app-owned
`/app/health` boundary marker and keeps the service entry point inside
`apps/infra`, not inside the Citizen app.

Run from repo root: `python -m apps.infra.backend --port 8090`.
