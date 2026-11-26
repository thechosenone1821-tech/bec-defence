"""Raksha — citizen-safety toolkit.

This tree contains:

- ``raksha.reasons``      : the shared Part 1 contract (reason-code catalogue +
                            citizen-facing i18n in English / Hindi / Telugu).
- ``raksha.messageguard`` : Part 3, the MessageGuard scam-script detector.
- ``raksha.evals``        : the evaluation harness and published results.

Part 2 is absent from this tree by design. Per the Part 3 independence note,
Parts 2 and 3 share no code beyond Part 1's reason catalogue and can be built
in parallel with no coordination beyond the reason-code enum.
"""

__version__ = "0.3.0"
