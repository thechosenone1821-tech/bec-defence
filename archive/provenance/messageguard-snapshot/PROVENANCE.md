# Standalone Part 3 MessageGuard snapshot — provenance only

- **Original path:** `random project that ew need to integrate/raksha/`
- **Archived here as:** `archive/provenance/messageguard-snapshot/raksha/`
- **Original status:** already folded into the main tree before Phase 5; its
  `INTEGRATED.md` marks it provenance-only. It contains a duplicate 492-row
  fixture snapshot, a standalone `messageguard/` directory, eval artefacts,
  tests and docs.
- **Phase 5 disposition:** moved into `archive/provenance/` to match the
  north-star layout. No code, corpus row or number was ported from here.
- **Import guard:** `raksha/messageguard/` was renamed to
  `raksha/messageguard_legacy/`. There is no `raksha/__init__.py` at this
  snapshot root, and the tree is not on any runtime `sys.path`.
- **Pytest guard:** `raksha/tests/` is ignored by the top-level provenance
  `conftest.py` and by the deterministic no-AI runner.

The original `INTEGRATED.md` and other historical text are preserved. Do not
restore this snapshot as a second runtime MessageGuard. The active baseline
is `apps/citizen/messageguard/`.
