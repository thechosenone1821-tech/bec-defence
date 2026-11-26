# Captured traffic

Empty by design. Phase 5 requires real traffic, and none exists in this
repository — see `specs/04_infra_detection_rings.md` §5.

Drop JSONL files here in the format documented in `corpora/capture.py`:

    {"organ": "COOKIE_FLUID_TURBULENCE", "label": "benign",
     "captured_at": "2026-11-23T10:00:00Z", "source": "prod-gw-01",
     "features": {"rho_cadence": 4.1, "v_cursor": 118.0, "l_nav": 402.0}}

Then run:

    python3 corpora/calibrate_organs.py corpora/captures/<file>.jsonl

Until a file is here, every organ reports `INSUFFICIENT_DATA` and the default
threshold stays in use with `default_in_use` set. That is the honest state.
