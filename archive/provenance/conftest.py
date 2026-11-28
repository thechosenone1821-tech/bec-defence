"""Keep archived MessageGuard tests out of the one active pytest suite.

The two provenance trees retain their historical ``tests/`` directories, but
they import the retired ``raksha.messageguard`` scorer. Pytest must never
collect them as a second MessageGuard suite. The deterministic Phase 4/5
runner also passes these directories as explicit ``--ignore`` arguments.
"""

collect_ignore = [
    "messageguard-alternative/raksha/tests",
    "messageguard-snapshot/raksha/tests",
]
collect_ignore_glob = [
    "*/raksha/tests/test_*.py",
]
