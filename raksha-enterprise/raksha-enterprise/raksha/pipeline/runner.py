"""Pipeline orchestrator: ingest -> detect -> fuse -> plan -> decide -> seal.

Stage latencies are observed into the metrics registry. Governor decisions are
written to the ledger (sealed) BEFORE they are returned or broadcast — the
ledger is the source of truth, and refusals are recorded exactly like
allowances.
"""

from __future__ import annotations

import threading

from ..config import Settings
from ..events import Event, VerifyState
from ..metrics import Metrics
from ..organs import Detection, get_organ
from .fusion import CampaignFusion
from .governor import Governor, VERDICT_ALLOWED, VERDICT_REFUSED
from .ingest import IngestService, IngestResult  # noqa: F401 — re-exported
from .planner import Planner, Proposal  # noqa: F401 — re-exported
from .topology import Topology


class Pipeline:
    def __init__(self, settings: Settings, sensor_key: bytes, ledger, store,
                 metrics: Metrics, notifier=None) -> None:  # noqa: ANN001
        self.settings = settings
        self.metrics = metrics
        self.ledger = ledger
        self.store = store
        self.topology = Topology.load(settings.data_dir / "topology.json", settings.crown_assets)
        self.fusion = CampaignFusion()
        self.planner = Planner(self.topology)
        self.governor = Governor(blast_cap=settings.blast_cap,
                                 precision_max_blast=settings.precision_max_blast)
        self.ingest = IngestService(sensor_key, store, metrics,
                                    rate_limit_epm=settings.rate_limit_epm)
        self.notifier = notifier
        self._lock = threading.Lock()
        self._decided: set[str] = set()
        self._sealed_campaigns: set[str] = set()

    # ------------------------------------------------------------------
    def process(self, event: Event, source: str = "sensor") -> dict[str, object]:
        out: dict[str, object] = {
            "event_id": event.event_id, "accepted": False, "verified": None,
            "reason": "", "detections": [], "proposals": [], "decisions": [],
        }
        ingest: IngestResult = self.ingest.submit(event, source=source)
        out["accepted"] = ingest.accepted
        out["verified"] = ingest.verified.value
        out["reason"] = ingest.reason
        if not ingest.accepted:
            return out
        if ingest.verified is not VerifyState.VALID:
            # Quarantine path: stored, counted, never actionable (contract R3).
            return out

        organ = get_organ(event.organ)
        if organ is None:
            self.metrics.inc("detect.unknown_organ")
            out["reason"] = f"unknown organ {event.organ!r} — event is not actionable"
            return out

        with self.metrics.timer("detect"):
            rule_id = organ.detect(event.payload)
        if rule_id is None:
            self.metrics.inc("detect.benign")
            out["reason"] = "verified, no rule fired"
            return out

        detection = Detection(
            organ=organ.name, rule_id=rule_id, event_id=event.event_id,
            campaign_id=event.campaign_id, case_id=event.case_id, leg=event.leg,
            entity=event.entity, severity=event.severity, summary=event.summary,
        )
        self.store.save_detection(detection.to_dict())
        self.metrics.inc("detect.flagged")
        out["detections"].append(detection.to_dict())

        with self.metrics.timer("fuse"):
            state = self.fusion.add(detection)
        out["campaign"] = state.to_dict()

        # Seal the fused campaign once, when it spans both legs.
        with self._lock:
            newly_fused = state.fused and state.campaign_id not in self._sealed_campaigns
            if newly_fused:
                self._sealed_campaigns.add(state.campaign_id)
        if newly_fused:
            with self.metrics.timer("seal"):
                self.ledger.append(
                    kind="detection", ref=f"FUSE-{state.campaign_id}",
                    text=(f"campaign {state.campaign_id} fused across legs "
                          f"{sorted(state.legs)} via opaque case token"),
                    payload={"case_id": state.case_id, "legs": sorted(state.legs),
                             "organs": sorted(state.organs)},
                )
            self.metrics.inc("seal.campaign_fused")
            out["sealed_campaign"] = True
        if self.notifier:
            self.notifier("detection", detection.to_dict())

        # Plan (idempotent by proposal id) and rule on every new proposal.
        with self.metrics.timer("plan"):
            proposals = self.planner.proposals_for(state)
        for proposal in proposals:
            with self._lock:
                fresh = proposal.proposal_id not in self._decided
                if fresh:
                    self._decided.add(proposal.proposal_id)
            if not fresh:
                continue
            out["proposals"].append(proposal.to_dict())
            if self.notifier:
                self.notifier("proposal", proposal.to_dict())
            with self.metrics.timer("seal"):
                self.ledger.append(
                    kind="proposal", ref=proposal.proposal_id, text=proposal.detail,
                    payload={"campaign_id": proposal.campaign_id,
                             "assets_severed": proposal.assets_severed,
                             "edges_cut": list(proposal.edges_cut)},
                )
            with self.metrics.timer("decide"):
                decision = self.governor.decide(proposal)
            with self.metrics.timer("seal"):
                if decision.verdict == VERDICT_ALLOWED:
                    text = f"containment ALLOWED: {proposal.detail}"
                else:
                    text = f"Governor REFUSED {proposal.proposal_id}: {decision.reason}"
                block = self.ledger.append(
                    kind="containment" if decision.verdict == VERDICT_ALLOWED else "refusal",
                    ref=proposal.proposal_id, text=text,
                    payload=decision.to_dict(),
                )
            self.metrics.inc(f"decide.{decision.verdict.lower()}")
            decision_dict = decision.to_dict()
            decision_dict["ledger_seq"] = block["seq"]
            out["decisions"].append(decision_dict)
            if self.notifier:
                self.notifier("decision", decision_dict)
        return out

    # ------------------------------------------------------------------
    def state_snapshot(self) -> dict[str, object]:
        campaigns = [c.to_dict() for c in self.fusion.all()]
        detected_entities = {e for c in self.fusion.all() for e in c.entities}
        graph = self.topology.to_dict()
        for node in graph["nodes"]:
            node["detected"] = node["id"] in detected_entities
        return {"campaigns": campaigns, "topology": graph,
                "ledger_height": self.ledger.height()}
