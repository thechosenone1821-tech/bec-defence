"""The hospital topology fixture.

All flow numbers in Raksha governance are fixture-measured: they come from
the edge weights defined here. There is no live NetFlow in the sandbox, and
any figure derived from this file must be labelled "fixture" wherever it is
quoted (binding rule 2: no unverified number).

Terms used throughout the package:

  crown asset   the ICU VLAN and everything in it. Raksha NEVER disrupts it.
                This is absolute, stronger than any human sign-off.
  Tier-0 asset  crown assets plus the other life-critical systems (EHR
                primary, Active Directory and their service identities).
                Disrupting a *non-crown* Tier-0 asset is possible, but only
                with valid FIDO2 human sign-off.

  critical edge an edge carrying a critical service flow. Its weight is the
                flow weight used by the uptime watchdog.

HONESTY (binding rule 2): every weight in this file is a FIXTURE
measurement standing in for real NetFlow telemetry. Any figure derived
from it must be labelled "fixture" wherever quoted.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass(frozen=True)
class Edge:
    id: str
    a: str
    b: str
    weight: float
    critical: bool


@dataclass(frozen=True)
class Topology:
    vlans: Dict[str, bool]           # vlan name -> is the crown VLAN?
    hosts: Dict[str, str]            # host name -> vlan name
    edges: Dict[str, Edge]           # edge id -> Edge
    identities: Dict[str, bool]      # identity -> is Tier-0?
    crown_vlan: str
    tier0_hosts: frozenset           # non-crown Tier-0 hosts
    tier0_identities: frozenset
    critical_floor: float = 0.999

    # --- existence checks (used by the schema gate) ---
    def host_exists(self, name: str) -> bool:
        return name in self.hosts

    def vlan_exists(self, name: str) -> bool:
        return name in self.vlans

    def edge_exists(self, name: str) -> bool:
        return name in self.edges

    def identity_exists(self, name: str) -> bool:
        return name in self.identities

    # --- crown / tier-0 classification ---
    def is_crown_host(self, name: str) -> bool:
        return self.hosts.get(name) == self.crown_vlan

    def is_tier0_host(self, name: str) -> bool:
        return self.is_crown_host(name) or name in self.tier0_hosts

    # --- topology arithmetic ---
    def edges_of_host(self, name: str) -> List[Edge]:
        return [e for e in self.edges.values() if e.a == name or e.b == name]

    def total_critical_weight(self) -> float:
        return sum(e.weight for e in self.edges.values() if e.critical)

    def edge(self, edge_id: str) -> Optional[Edge]:
        return self.edges.get(edge_id)


def hospital_fixture() -> Topology:
    """The demo/test hospital: one crown VLAN (ICU), one core switch.

    Consolidated-build changes (documented, deliberate):

    - EAST-WEST LATERAL LINKS x1..x4 (non-critical) give the containment
      planner (Part 3) real multi-hop paths, so lateral movement cannot be
      contained by one uplink cut. x4 lands on the Tier-0 EHR host, which
      is exactly the trade-off the planner's nu*A term and the FIDO2
      step-up gate exist for.
    - e_ncs (nurse call station) is reclassified non-critical: its flow is
      a ward convenience flow, not a life-critical one. The critical set
      is {e_pump, e_vent, e_ehr, e_ad, e_ad2}, total critical weight
      92.05 (fixture).
    """
    edges = [
        # uplinks to the core switch (fixture-measured weights)
        Edge("e_pump", "pump-01", "core-sw", 15.0, True),      # crown host
        Edge("e_vent", "vent-02", "core-sw", 12.0, True),      # crown host
        Edge("e_ehr", "ehr-primary", "core-sw", 40.0, True),   # Tier-0 host
        Edge("e_ad", "ad-dc-01", "core-sw", 25.0, True),      # Tier-0 host
        Edge("e_ad2", "ad-dc-01", "core-sw", 0.05, True),     # Tier-0 host
        Edge("e_ncs", "ncs-12", "core-sw", 8.0, False),
        Edge("e_ws", "ws-11", "core-sw", 10.0, False),
        Edge("e_hvac", "hvac-01", "core-sw", 5.0, False),
        Edge("e_prn1", "prn-01", "core-sw", 2.0, False),
        Edge("e_prn2", "prn-02", "core-sw", 1.0, False),
        # east-west lateral links (the paths attackers actually travel)
        Edge("x1", "ws-11", "prn-01", 3.0, False),             # ward-3 <-> guest-5
        Edge("x2", "prn-01", "hvac-01", 2.0, False),           # guest-5 <-> bms-2
        Edge("x3", "ws-11", "ncs-12", 1.0, False),             # ward-3 lateral
        Edge("x4", "ncs-12", "ehr-primary", 4.0, False),       # ward-3 -> Tier-0 EHR
    ]
    return Topology(
        vlans={
            "icu-7": True,          # the crown VLAN
            "ward-3": False,
            "admin-1": False,
            "bms-2": False,
            "guest-5": False,
            "remediation-9": False,
        },
        hosts={
            "pump-01": "icu-7",
            "vent-02": "icu-7",
            "ncs-12": "ward-3",
            "ws-11": "ward-3",
            "ehr-primary": "admin-1",
            "ad-dc-01": "admin-1",
            "core-sw": "admin-1",
            "hvac-01": "bms-2",
            "prn-01": "guest-5",
            "prn-02": "guest-5",
        },
        edges={e.id: e for e in edges},
        identities={
            "svc-ehr-backup": True,
            "svc-print": False,
        },
        crown_vlan="icu-7",
        tier0_hosts=frozenset({"ehr-primary", "ad-dc-01"}),
        tier0_identities=frozenset({"svc-ehr-backup"}),
        critical_floor=0.999,
    )
