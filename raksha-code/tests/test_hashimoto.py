import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sentinel.shields.ring4_network_healing import HashimotoPercolation
from sentinel.shields.ring4_network_healing.hashimoto_percolation import spectral_radius, PROTECTED_WEIGHT

_TOPO = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                     "spine", "config", "company_topology.json")


def _load_edges(topo):
    vlan_ids = [v["id"] for v in topo["vlans"]]
    idx = {v: i for i, v in enumerate(vlan_ids)}
    crit_w = topo["criticality_weights"]
    edges = []
    for e in topo["edges"]:
        weight = e["weight"] if e["weight"] is not None else crit_w.get(e["criticality"], 1.0)
        protected = e["criticality"] == "crown_jewel"
        mission = e["criticality"] == "mission_critical"
        edges.append((idx[e["a"]], idx[e["b"]],
                      PROTECTED_WEIGHT if protected else float(weight),
                      protected, protected or mission))
    return vlan_ids, edges


def test_spectral_radius_positive_on_cyclic_graph():
    with open(_TOPO) as f:
        topo = json.load(f)
    vlan_ids, edges = _load_edges(topo)
    rho = spectral_radius(len(vlan_ids), [(a, b) for a, b, *_ in edges])
    assert rho > 0.5


def test_containment_cut_never_touches_crown_jewels():
    with open(_TOPO) as f:
        topo = json.load(f)
    vlan_ids, edges = _load_edges(topo)
    percol = HashimotoPercolation(target_radius=1.0)
    plan = percol.containment_plan(vlan_ids, edges, target=1.0)
    assert plan["tier0_edges_cut"] == 0
    assert plan["rho_after"] <= plan["rho_before"]
    assert plan["contained"] is True
    assert plan["preserved_critical_weight_pct"] >= 90.0
    # every removed edge is crown-jewel-free by construction
    assert all(cut["weight"] != float("inf") for cut in plan["removed_edges"])


def test_no_edges_to_cut_returns_intact_graph():
    percol = HashimotoPercolation(target_radius=1.0)
    ids = ["A", "B", "C"]
    edges = [(0, 1, PROTECTED_WEIGHT, True, True), (1, 2, PROTECTED_WEIGHT, True, True)]
    plan = percol.containment_plan(ids, edges, target=1.0)
    assert plan["removed_edges"] == []
    assert plan["tier0_edges_cut"] == 0


def test_forest_has_rho_below_one():
    # unit-transmissibility cascades cannot persist on a tree
    assert spectral_radius(3, [(0, 1), (1, 2)]) < 1.0
