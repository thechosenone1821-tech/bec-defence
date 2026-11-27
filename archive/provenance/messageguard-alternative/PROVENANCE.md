# Alternative Part 3 MessageGuard — provenance only

- **Original path:** `raksha-messageguard/raksha/`
- **Archived here as:** `archive/provenance/messageguard-alternative/raksha/`
- **Original contents:** 431 hand-authored fixtures (324 scam, 107 benign,
  including 30/16 Hinglish), an independent `assess()` / `SignalFamilyScorer`,
  `msg.*` reason codes, CLI, legacy organ adapter, i18n, eval runner/results
  and regression tests.
- **Phase 5 disposition:** compared against the canonical v1 scorer. Only 46
  unique Hinglish rows, legacy-adapter behaviour, CLI affordances and FP
  regression value were ported. The second scorer, second catalogue, second
  corpus, second runner/results and second generated document were retired.
- **Import guard:** `raksha/messageguard/` was renamed to
  `raksha/messageguard_legacy/` so `raksha.messageguard` cannot be imported
  from a repository root. Internal historical imports are not maintained.
- **Pytest guard:** `raksha/tests/` is ignored by the top-level provenance
  `conftest.py` and by the deterministic no-AI runner.
- **Claim status:** the archived README's "990 pytest tests" and verdict
  hash are historical claims, not current measurements. No number from this
  tree is a current published number.

Do not add this tree to `PYTHONPATH`, install its `pyproject.toml`, or use it
as a runtime baseline. The active baseline is
`apps/citizen/messageguard/`.
