# Provenance archive

Read-only historical evidence for the combined-system integration. Start with
[`INTEGRATED.md`](INTEGRATED.md), which maps every retired standalone project to
its active home. These trees are not runtime packages, not active pytest suites
and not sources of published numbers.

The active repository has exactly two apps (`apps/citizen/` and `apps/infra/`),
one shared spine under `packages/`, one root `evals/` package and canonical docs
at the repository root and in `docs/`. Frozen VoiceGuard/MAYA assets remain
unchanged and VoiceGuard evals are excluded from `make eval`.

Archived MessageGuard test directories are ignored by `conftest.py` and
`tools/run_phase4_pytest.py`; other archived trees are outside the configured
pytest `testpaths`. Internal docstrings and imports in provenance trees are
historical text and must not be repaired into active runtime imports.

See the [retired code note](RETIRED.md) for the executable-code purge boundary.
