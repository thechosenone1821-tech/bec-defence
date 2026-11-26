"""Part 6 pipeline: ingest -> detect -> fuse -> plan -> decide -> seal."""

from .fusion import CampaignFusion, CampaignState
from .governor import Decision, Governor, VERDICT_ALLOWED, VERDICT_REFUSED
from .ingest import IngestResult, IngestService
from .planner import Planner, Proposal
from .runner import Pipeline
from .topology import Topology

__all__ = [
    "CampaignFusion", "CampaignState", "Decision", "Governor", "IngestResult",
    "IngestService", "Pipeline", "Planner", "Proposal", "Topology",
    "VERDICT_ALLOWED", "VERDICT_REFUSED",
]
