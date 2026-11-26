"""Governor policy engine: the component that decides, including refusing.

Policy rules (frozen, evaluated in order — first match wins):
  G1 CROWN-GATEWAY   any proposal that cuts the crown segment uplink is refused;
                     a fallback containment is offered instead
  G2 CROWN-TARGET    containment that severs a crown asset itself is refused
  G3 BLAST-CAP       proposals severing more than `blast_cap` assets are refused
  G4 PRECISION       everything else (low blast, no crown involvement) is allowed

Every decision is append-only: the runner writes it to the ledger before it is
returned, and there is no override path anywhere in the service (contract R6).
"""

from __future__ import annotations

import time
from dataclasses import dataclass

VERDICT_ALLOWED = "ALLOWED"
VERDICT_REFUSED = "REFUSED"


@dataclass(frozen=True, slots=True)
class Decision:
    proposal_id: str
    campaign_id: str
    verdict: str
    rule_id: str
    reason: str
    fallback_proposal_id: str | None
    ts: str
    assets_severed: int

    def to_dict(self) -> dict[str, object]:
        return {
            "proposal_id": self.proposal_id, "campaign_id": self.campaign_id,
            "verdict": self.verdict, "rule_id": self.rule_id, "reason": self.reason,
            "fallback_proposal_id": self.fallback_proposal_id, "ts": self.ts,
            "assets_severed": self.assets_severed,
        }


class Governor:
    def __init__(self, blast_cap: int = 8, precision_max_blast: int = 2) -> None:
        self._blast_cap = blast_cap
        self._precision_max = precision_max_blast

    def decide(self, proposal) -> Decision:  # noqa: ANN001 — Proposal avoids a cycle
        base = {
            "proposal_id": proposal.proposal_id,
            "campaign_id": proposal.campaign_id,
            "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "assets_severed": proposal.assets_severed,
        }
        if proposal.targets_crown_gateway:
            return Decision(
                **base, verdict=VERDICT_REFUSED, rule_id="G1-CROWN-GATEWAY",
                reason=(f"cut would sever the crown segment uplink: {proposal.assets_severed} assets "
                        f"lose connectivity ({proposal.detail}); a lesser containment is offered instead"),
                fallback_proposal_id=proposal.fallback_id,
            )
        if proposal.target_node_is_crown:
            return Decision(
                **base, verdict=VERDICT_REFUSED, rule_id="G2-CROWN-TARGET",
                reason="proposal targets a Tier-0 crown asset directly; crown assets are never contained",
                fallback_proposal_id=None,
            )
        if proposal.assets_severed > self._blast_cap:
            return Decision(
                **base, verdict=VERDICT_REFUSED, rule_id="G3-BLAST-CAP",
                reason=(f"blast radius {proposal.assets_severed} exceeds the cap of {self._blast_cap}; "
                        "a narrower containment is required"),
                fallback_proposal_id=proposal.fallback_id,
            )
        return Decision(
            **base, verdict=VERDICT_ALLOWED, rule_id="G4-PRECISION",
            reason=(f"blast radius {proposal.assets_severed} within cap, no crown involvement: "
                    f"{proposal.detail}"),
            fallback_proposal_id=None,
        )
