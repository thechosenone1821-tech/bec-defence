"""EIGENSHIELD v2.1 — FORTRESS.

Hardening layer for the v2.0 immune system. Core idea: the decision path that
protects Tier-0 infrastructure must not depend on any single component,
library, or lineage of code being correct.

    fortress/tcb_core.py       primary, pure-stdlib decision procedure (TCB)
    fortress/tcb_mirror.py     independent N-version re-derivation (must agree)
    fortress/telemetry_mac.py  HMAC-signed organ events — forgeries never act
    fortress/boot_manifest.py  SHA-256 config pinning — tampered configs refuse to run
    fortress/canaries.py       canary tokens — catch a hijacked Commander
    fortress/tripwire.py       AI-crack-attempt detector — freezes the AI path
    fortress/ledger_anchor.py  anchored ledger head — detects rollback/truncation
    fortress/sandbox_runner.py subprocess + rlimits process isolation for revert paths

Everything here uses ONLY the Python standard library. No numpy, no yaml, no
third-party code is trusted on the TCB path. See docs/FORTRESS.md for the
threat model, the control matrix, and the honest limits of these guarantees.
"""

__version__ = "2.1.0"

CONTRACT = "fortress-v2.1"
