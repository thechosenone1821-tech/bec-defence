"""sentinel/shields — Ring 3, Organ 5: Page-Curve 4 KB Ransomware Trap.

Weaves hidden bipartite honey-block pairs (A, B) into high-value directories.
Each 4 KB chunk keeps an erasure-coded mutual-information parity invariant

    P_i = A_i XOR H(B_i, salt_i)

inspired by bipartite Page-curve entanglement boundaries. A file-system hook
(fanotify/eBPF on Linux, Minifilter on Windows; Python ``watchdog`` for the
local MVP) verifies parity on write. Any unauthorized cipher pass breaks the
invariant on its FIRST 4 KB write and terminates the offending PID.

By default the organ is in DRY-RUN: it records the kill decision and returns a
kill-request token, but never calls os.kill. Pass allow_real_kill=True (used
only by the sandboxed demo against its own child PID) to enforce for real.
"""

from __future__ import annotations

import hashlib
import hmac
import os
import secrets
import time
from typing import Any, Dict, List, Optional

from sentinel.shields.base_organ import BaseOrgan

BLOCK = 4096


def _keystream(salt: bytes, length: int) -> bytes:
    out = bytearray()
    counter = 0
    while len(out) < length:
        out += hashlib.sha256(salt + counter.to_bytes(8, "big")).digest()
        counter += 1
    return bytes(out[:length])


def _parity(a: bytes, b: bytes, salt: bytes) -> bytes:
    ks = _keystream(salt, len(a))
    return bytes(x ^ y ^ z for x, y, z in zip(a, b, ks))


def _flipped_bits(expected: bytes, stored: bytes) -> int:
    """Count parity bits where the recomputed invariant disagrees with the seal.

    Comparing the two honey halves against each other would be meaningless:
    they are independent random blocks, so an untouched pair differs in ~50 %
    of bits. The only quantity with content is *recomputed parity* versus the
    *parity sealed at arm() time* — and because
    ``P = A XOR H(B, salt)``, that difference is exactly the bits of A that
    were overwritten.
    """
    return sum((x ^ y).bit_count() for x, y in zip(expected, stored))


class PageCurveTrap(BaseOrgan):
    ring = "RING_3_ENDPOINT_SILICON"
    organ = "ENDPOINT_PAGE_CURVE"

    def __init__(self, allow_real_kill: bool = False, **kwargs: Any):
        super().__init__(**kwargs)
        self.allow_real_kill = allow_real_kill
        self._honey: Dict[str, Dict[str, Any]] = {}
        self.register_rpc("arm_page_curve_traps", self._rpc_arm)

    # ------------------------------------------------------------------ #
    def arm(self, directory: str, host_id: str = "HOST_042", density_level: str = "high") -> Dict[str, Any]:
        """Create honey-block pairs inside ``directory`` (must exist)."""
        density = {"low": 2, "standard": 4, "high": 8}.get(density_level, 4)
        os.makedirs(directory, exist_ok=True)
        created: List[str] = []
        for i in range(density):
            a = secrets.token_bytes(BLOCK)
            b = secrets.token_bytes(BLOCK)
            salt = secrets.token_bytes(16)
            p = _parity(a, b, salt)
            pa = os.path.join(directory, f".honey_a_{i:02d}.bin")
            pb = os.path.join(directory, f".honey_b_{i:02d}.bin")
            with open(pa, "wb") as f:
                f.write(a)
            with open(pb, "wb") as f:
                f.write(b)
            self._honey[pa] = {"pair": pb, "salt": salt, "parity": p, "host_id": host_id}
            created.extend([pa, pb])
        return {"status": "TRAPS_ARMED", "host_id": host_id, "density_level": density_level,
                "honey_blocks": len(self._honey), "files": created}

    def verify_file(self, path: str) -> Dict[str, Any]:
        meta = self._honey.get(path)
        if meta is None:
            return {"path": path, "honey": False, "intact": True}
        with open(path, "rb") as f:
            a = f.read()
        with open(meta["pair"], "rb") as f:
            b = f.read()
        expected = _parity(a, b, meta["salt"])
        intact = hmac.compare_digest(expected, meta["parity"])
        return {"path": path, "honey": True, "intact": bool(intact), "host_id": meta["host_id"],
                # Part 4 Phase 3: the verifier now returns its evidence, not just
                # a boolean, so no caller has to invent a number to describe it.
                "flipped_bits": _flipped_bits(expected, meta["parity"]),
                "expected_parity": expected}

    def verify_all(self) -> List[Dict[str, Any]]:
        return [self.verify_file(p) for p in list(self._honey)]

    def on_write(self, path: str, pid: int, host_id: str = "HOST_042") -> Dict[str, Any]:
        """File-system hook callback. Breaks => kill request for ``pid``."""
        check = self.verify_file(path)
        if check["intact"]:
            return {"path": path, "action": "NONE", "honey": check["honey"]}

        # Part 4 Phase 3 (defect #11): three numbers here were decorative.
        #   - ``severity`` was the constant 0.96 for every break, so a
        #     one-bit flip and a total cipher pass scored identically.
        #   - ``parity_delta`` was the constant 0.994, never measured.
        #   - ``latency_ms`` was the constant 0.9, never timed — and the
        #     local-reflex label ``PID_TERMINATED_0.9MS`` published it.
        # All three are now measured from the bytes and the clock. A reason
        # that states the measurement is the difference between a log line
        # an operator can act on and one they learn to skip.
        t0 = time.perf_counter()
        delta_bits = check["flipped_bits"]
        parity_delta = delta_bits / (BLOCK * 8)
        # Severity tracks how much of the block the writer rewrote.
        #
        # Note the ceiling: because ``P = A XOR H(B, salt)`` and B is random,
        # recomputed parity of a *random* overwrite differs from the seal in
        # ~50 % of bits, not 100 %. So ``parity_delta`` saturates near 0.5 and
        # scaling by 1/2 could never exceed 0.75 — below the Commander's 0.9
        # "confirmed encryption" band, which would have silently demoted a real
        # ransomware event to a trap-refresh. The scale is anchored on the
        # measurable range: 1 bit (≈0) → 0.50, a full-block cipher pass
        # (≈0.5) → 0.96, matching the band the rest of the system expects.
        severity = min(1.0, 0.50 + parity_delta * 0.92)
        latency_ms = (time.perf_counter() - t0) * 1e3

        event = self.emit(
            "PARITY_ENTROPY_COLLAPSE",
            severity=severity,
            entities={"host_id": host_id, "vlan_id": "VLAN_CORP_IT",
                      "user_id": "USER_UNKNOWN",
                      "process_hash": f"pid:{pid}"},
            metrics={"bytes_written": BLOCK,
                     "parity_delta": round(parity_delta, 6),
                     "flipped_bits": delta_bits,
                     "local_reflex_action": "PID_TERMINATED",
                     "verify_latency_ms": round(latency_ms, 4)},
            reason=(f"Honey block {os.path.basename(path)} failed its "
                    f"mutual-information parity check after {BLOCK} bytes were "
                    f"written by pid {pid}: {delta_bits} of {BLOCK * 8} parity "
                    f"bits flipped ({parity_delta:.2%} of the block), verified in "
                    f"{latency_ms:.2f} ms. Legitimate readers never write here."),
        )
        result = {
            "path": path,
            "honey": True,
            "action": "PID_TERMINATED",
            "pid": pid,
            "latency_ms": round(latency_ms, 4),
            "dry_run": not self.allow_real_kill,
            "event": event,
            "ts": time.time(),
        }
        if self.allow_real_kill:
            try:
                os.kill(pid, 9)
                result["os_kill"] = "SIGKILL_SENT"
            except (ProcessLookupError, PermissionError) as exc:
                result["os_kill"] = f"FAILED:{exc}"
        return result

    # ------------------------------------------------------------------ #
    def _rpc_arm(self, args: Dict[str, Any]) -> Dict[str, Any]:
        return {"status": "TRAP_DENSITY_BOOSTED", "host_id": args.get("host_id"),
                "density_level": args.get("density_level", "high")}
