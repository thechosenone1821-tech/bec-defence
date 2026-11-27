"""Governor policy rules G1–G4 and planner blast-radius math on the real topology."""

from __future__ import annotations

import pytest

from raksha.pipeline import Governor
from raksha.pipeline.fusion import CampaignState
from raksha.pipeline.planner import Planner, Proposal
from raksha.pipeline.topology import Topology

CROWNS = ("N-TIER0-CORE", "N-IDENTITY-VAULT")


def proposal(**overrides) -> Proposal:
    base = dict(
        proposal_id="PROP-C-1-TEST", campaign_id="C-1", kind="EDGE-CUT", target="E1",
        edges_cut=("E1",), assets_severed=2, crown_path_risk="low", est_recovery_hours=4,
        targets_crown_gateway=False, target_node_is_crown=False, detail="test proposal",
        fallback_id=None, payload={},
    )
    base.update(overrides)
    return Proposal(**base)


@pytest.fixture
def governor() -> Governor:
    return Governor(blast_cap=8, precision_max_blast=2)


def test_g1_crown_gateway_refusal_offers_fallback(governor: Governor) -> None:
    decision = governor.decide(proposal(
        proposal_id="PROP-C-2247-ICU-CUT", assets_severed=14, crown_path_risk="high",
        targets_crown_gateway=True, fallback_id="PROP-C-2247-N-BUILD-SRV-EGRESS",
        detail="sever the crown segment uplink"))
    assert decision.verdict == "REFUSED" and decision.rule_id == "G1-CROWN-GATEWAY"
    assert decision.fallback_proposal_id == "PROP-C-2247-N-BUILD-SRV-EGRESS"


def test_g2_crown_target_refusal(governor: Governor) -> None:
    decision = governor.decide(proposal(
        kind="NODE-QUARANTINE", target="N-TIER0-CORE", target_node_is_crown=True))
    assert decision.verdict == "REFUSED" and decision.rule_id == "G2-CROWN-TARGET"


def test_g3_blast_cap_refusal(governor: Governor) -> None:
    decision = governor.decide(proposal(assets_severed=9, detail="over the cap"))
    assert decision.verdict == "REFUSED" and decision.rule_id == "G3-BLAST-CAP"


def test_g4_precision_allowance(governor: Governor) -> None:
    decision = governor.decide(proposal(assets_severed=2))
    assert decision.verdict == "ALLOWED" and decision.rule_id == "G4-PRECISION"


def test_g1_wins_over_g3(governor: Governor) -> None:
    decision = governor.decide(proposal(assets_severed=14, targets_crown_gateway=True))
    assert decision.rule_id == "G1-CROWN-GATEWAY"


# -- planner math on the real topology -----------------------------------------
@pytest.fixture
def topo() -> Topology:
    return Topology.load(None, CROWNS)


def test_icu_cut_severs_14_assets(topo: Topology) -> None:
    gateway = topo.crown_gateway_edge()
    severed = topo.severed_by_edge_cut(gateway["id"])
    assert len(severed) == 14
    assert "N-TIER0-CORE" not in severed and "N-IDENTITY-VAULT" not in severed
    assert "N-BUILD-SRV" in severed and "N-BACKUP-TARGET" in severed


def test_crown_never_severed_by_node_quarantine(topo: Topology) -> None:
    assert topo.severed_by_node_quarantine("N-TIER0-CORE") == set()


def test_egress_quarantine_blows_six_assets(topo: Topology) -> None:
    severed = topo.severed_by_node_quarantine("N-BUILD-SRV", outbound_only=True)
    assert severed == {"N-BUILD-SRV", "N-BACKUP-TARGET", "N-STAGING",
                       "N-ARTIFACT-REPO", "N-LOG-AGG", "N-MONITOR"}


def test_planner_proposals_for_fused_campaign(topo: Topology) -> None:
    planner = Planner(topo)
    campaign = CampaignState(campaign_id="C-2247", case_id="case-7f3a9c")
    campaign.legs = {"citizen", "infra"}
    from raksha.organs import Detection
    for organ, entity in (("docguard", "N-INVOICE-DOC"),
                          ("sessionguard", "N-BANK-SESSION"),
                          ("fileguard", "N-BUILD-SRV")):
        campaign.detections.append(Detection(organ, f"{organ}-R", "EV", "C-2247",
                                             "case-7f3a9c", "infra", entity, 4, "s"))
    proposals = {p.proposal_id: p for p in planner.proposals_for(campaign)}
    icu = proposals["PROP-C-2247-ICU-CUT"]
    assert icu.assets_severed == 14 and icu.crown_path_risk == "high"
    assert icu.targets_crown_gateway
    assert icu.fallback_id in proposals
    assert proposals[icu.fallback_id].assets_severed == 6
    assert proposals["PROP-C-2247-N-INVOICE-DOC"].assets_severed == 2
    assert proposals["PROP-C-2247-N-BANK-SESSION"].assets_severed == 2


def test_crown_entity_never_escalates(topo: Topology) -> None:
    """quorumguard fires on N-TIER0-CORE; the planner must not quarantine the crown."""
    planner = Planner(topo)
    campaign = CampaignState(campaign_id="C-2247", case_id="case-7f3a9c")
    from raksha.organs import Detection
    campaign.detections.append(Detection("quorumguard", "QG", "EV", "C-2247",
                                         "case-7f3a9c", "infra", "N-TIER0-CORE", 5, "s"))
    assert planner.proposals_for(campaign) == []
