# Compatibility tree

This tree preserves the authored PWA assets, MessageGuard fixtures, shared spine configuration and compatibility aliases. `citizen.*` imports resolve to the active `apps.citizen` package; the PWA files are served through path extension, not a second service. The legacy eval runner is a thin compatibility wrapper around the root `evals/` package. Retired voice-scorer code was removed; see the [retired code note](../archive/provenance/RETIRED.md). Active status lives in [docs/STATUS.md](../docs/STATUS.md).
