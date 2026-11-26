"""sentinel/shields — Ring 4, Organ 8: MutS/MutL DNA Mismatch-Repair Runtime.

Modeled on cellular MutS/MutL mismatch repair: services register lightweight
dual-strand invariants (bounds-checked control flow / memory bounds). When a
zero-day exploit triggers a mismatch, the monitor freezes the offending
thread, blocks the malformed syscall/branch, and splices in a pre-verified,
bounds-checked fallback shield.

MVP honesty note: this module SIMULATES the inline eBPF/LSM shield with the
same control surface as production (register -> mismatch -> freeze -> splice).
Loading real eBPF programs requires CAP_BPF/CAP_SYS_ADMIN and is out of scope
for the portable stage demo; the latency accounting and decision flow are
faithful, the kernel hook is mocked.
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

from sentinel.shields.base_organ import BaseOrgan

PATCH_PROFILES = {
    "bounds_check_v1": {"kind": "memory_bounds", "verified": True, "description": "bounds-checked load/store trampoline"},
    "cfi_v1": {"kind": "control_flow", "verified": True, "description": "forward-edge CFI trampoline"},
    "syscall_filter_v1": {"kind": "syscall_surface", "verified": True, "description": "syscall allowlist with execve/ptrace denial"},
}


class MutsEbpfRepair(BaseOrgan):
    ring = "RING_4_NETWORK_HEALING"
    organ = "MUTS_EBPF_REPAIR"

    def __init__(self, splice_budget_ms: float = 50.0, **kwargs: Any):
        super().__init__(**kwargs)
        self.splice_budget_ms = splice_budget_ms
        self._invariants: Dict[str, Dict[str, Any]] = {}
        self._splices: List[Dict[str, Any]] = []
        self.register_rpc("deploy_muts_ebpf_shield", self._rpc_deploy)

    # ------------------------------------------------------------------ #
    def register_invariant(self, service_id: str, profile_id: str) -> Dict[str, Any]:
        profile = PATCH_PROFILES.get(profile_id)
        if profile is None:
            raise ValueError(f"unknown patch profile: {profile_id}")
        self._invariants[service_id] = {
            "invariant_id": f"inv_{service_id}_{int(time.time()*1000)}",
            "service_id": service_id,
            "profile_id": profile_id,
            "profile": profile,
            "registered_at": time.time(),
        }
        return self._invariants[service_id]

    def report_mismatch(self, service_id: str, detail: str = "bounds_violation",
                        host_id: Optional[str] = None) -> Dict[str, Any]:
        """MutS equivalent: freeze + verify. MutL equivalent: splice shield."""
        inv = self._invariants.get(service_id)
        t0 = time.perf_counter()
        if inv is None:
            return {"status": "MISMATCH_NO_INVARIANT", "service_id": service_id}

        frozen_at = time.perf_counter()
        profile = inv["profile"]

        # Part 4 Phase 1, defect 1: "a repeated exploit is repaired so the second
        # attempt fails" is this organ's whole thesis, and the code could not
        # tell a first attempt from a second: `second_attempt_blocked` was
        # hard-coded True on *every* call, so the first mismatch and the repeat
        # were indistinguishable. A repeat now has its own status.
        repaired = bool(inv.get("repaired"))
        if repaired:
            record = {
                "status": "ALREADY_REPAIRED",
                "service_id": service_id,
                "invariant_id": inv["invariant_id"],
                "patch_profile_id": inv["profile_id"],
                "first_repaired_at": inv.get("repaired_at"),
                "detail": detail,
                "second_attempt_blocked": True,
                "within_budget": True,
            }
            self._splices.append(record)
            self.emit(
                "MISMATCH_REPEAT_BLOCKED",
                severity=0.7,
                entities={"host_id": host_id, "vlan_id": "VLAN_CORP_IT",
                          "service_id": service_id},
                metrics={"repeat": True},
                reason=(f"{service_id} matched a signature already repaired at "
                        f"{inv.get('repaired_at')}; the repeat exploit did not run"),
            )
            return record

        inv["repaired"] = True
        inv["repaired_at"] = time.time()

        # Simulated verification + splice of the pre-compiled fallback path.
        splice_ms = round((time.perf_counter() - t0) * 1e3 + 0.012, 3)  # +12us modeled work
        # Part 4 Phase 1, defect 2: this used to clamp `splice_ms` to the budget
        # *before* comparing it with the budget, so `within_budget` was True for
        # every possible input — including a zero budget. A measurement that
        # cannot fail is not a measurement. The raw value is now reported and
        # compared honestly; the clamp target is visible in the record.
        within = bool(splice_ms <= self.splice_budget_ms)

        record = {
            "status": "SHIELD_SPLICED",
            "service_id": service_id,
            "invariant_id": inv["invariant_id"],
            "patch_profile_id": inv["profile_id"],
            "freeze_ms": round((frozen_at - t0) * 1e3, 3),
            "splice_ms": splice_ms,
            "splice_budget_ms": self.splice_budget_ms,
            "within_budget": within,
            "detail": detail,
            "second_attempt_blocked": False,
        }
        self._splices.append(record)
        # Part 4 Phase 3: this organ runs *inside* a service and was stamping
        # HOST_APP_SRV_07 — a real topology id — on every splice regardless of
        # where it actually ran. The host is now an argument; when the caller
        # has none, the event says None instead of inventing one.
        #
        # Severity followed the same pattern: the constant 0.9 regardless of
        # whether the splice met its latency budget. A splice that blew the
        # budget by 40x and one that met it scored identically. It now tracks
        # the overrun.
        overrun = max(0.0, splice_ms - self.splice_budget_ms)
        # A zero budget is a legal configuration (the contract suite sets it to
        # prove ``within_budget`` can fail at all), so the scaling term is
        # guarded — an organ must never raise on a legal input.
        scale = 4 * self.splice_budget_ms
        severity = 0.9 if overrun <= 0.0 else min(1.0, 0.9 + overrun / (scale if scale > 1e-9 else 0.05))
        self.emit(
            "MISMATCH_SHIELD_SPLICED",
            severity=severity,
            entities={"host_id": host_id, "vlan_id": "VLAN_CORP_IT",
                      "service_id": service_id},
            metrics={"splice_ms": splice_ms, "within_budget": within,
                     "splice_budget_ms": self.splice_budget_ms,
                     "overrun_ms": round(overrun, 3)},
            reason=(f"{service_id} tripped invariant {inv['invariant_id']} "
                    f"({detail}); {inv['profile_id']} spliced in {splice_ms:.3f} ms "
                    f"against a {self.splice_budget_ms:.1f} ms budget "
                    f"({'within budget' if within else f'over by {overrun:.3f} ms'}), "
                    f"freeze window {(frozen_at - t0) * 1e3:.3f} ms"),
        )
        return record

    def splice_history(self) -> List[Dict[str, Any]]:
        return list(self._splices)

    # ------------------------------------------------------------------ #
    def _rpc_deploy(self, args: Dict[str, Any]) -> Dict[str, Any]:
        service_id = args.get("service_id", "APP_SRV_07")
        profile_id = args.get("patch_profile_id", "bounds_check_v1")
        if service_id not in self._invariants:
            self.register_invariant(service_id, profile_id)
        return {"status": "SHIELD_DEPLOYED", "service_id": service_id,
                "patch_profile_id": profile_id, "verified": True}
