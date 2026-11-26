"""Commander (Part 4 of the governance build) -- the proposer.

The commander is the only place a model may enter the pipeline, and its
output is still just raw action envelopes: every one of them passes
Governor.decide() like anything else. Every response carries a
``commander_mode`` field so nothing can pose as something it is not.

Modes:
  fallback_rules  deterministic rules engine, always available. By
                  construction it can only emit tools from fixed
                  templates: incident fields flow into justification
                  text (inert audit strings), never into ``tool``.
  ollama_local    adapter for a local Ollama model proposing
                  grammar-constrained JSON against the same 10-tool
                  allowlist. NOT exercised in this build -- no model
                  runs in the sandbox, so every demo honestly runs in
                  fallback mode. A jailbroken model output is still
                  dropped by the Governor's schema lock.

Nothing here needs training -- only running (spec: "three things that
need model training" table; this is the zero-training path).
"""
from __future__ import annotations

import json
import os
import urllib.request
from dataclasses import dataclass
from typing import Optional, Tuple

MODE_FALLBACK = "fallback_rules"
MODE_OLLAMA = "ollama_local"


class CommanderUnavailable(Exception):
    pass


@dataclass(frozen=True)
class Incident:
    incident_id: str
    seeds: Tuple[str, ...]      # compromised host ids (must exist in the topology)
    alerts: Tuple[dict, ...] = ()


@dataclass(frozen=True)
class CommanderReport:
    commander_mode: str
    proposals: Tuple[dict, ...]  # raw action envelopes; re-validated by the Governor
    notes: Tuple[str, ...]


class FallbackCommander:
    """Deterministic rules engine. Template emission only."""

    mode = MODE_FALLBACK

    def propose(self, incident: Incident) -> CommanderReport:
        proposals = []
        for host in incident.seeds:
            proposals.append({
                "tool": "snapshot.capture",
                "params": {"host": host},
                "justification": (f"incident {incident.incident_id}: forensic "
                                  f"triage of seed host {host}"),
                "requested_by": "commander:fallback",
            })
            proposals.append({
                "tool": "host.quarantine",
                "params": {"host": host},
                "justification": (f"incident {incident.incident_id}: seed host "
                                  f"{host} contained pending forensics"),
                "requested_by": "commander:fallback",
            })
        return CommanderReport(
            commander_mode=self.mode,
            proposals=tuple(proposals),
            notes=(
                "deterministic fallback rules v1: whitelist tools only, by "
                "construction (incident fields reach justification text only)",
                "cut-set refinement is delegated to the containment planner",
            ),
        )


class OllamaCommander:
    """Local-model adapter (spec: e.g. qwen3.5:4b, ~1 day to wire once a
    model is pulled). Contract: the model returns JSON
    {"actions": [{"tool", "params", "justification", "requested_by"}]}
    inside the 10-tool allowlist; ANY deviation is dropped by the Governor.
    """

    mode = MODE_OLLAMA

    def __init__(self, model: str, endpoint: str = "http://127.0.0.1:11434"):
        self.model = model
        self.endpoint = endpoint

    def healthcheck(self) -> None:
        try:
            with urllib.request.urlopen(self.endpoint + "/api/tags", timeout=2) as resp:
                resp.read()
        except Exception as exc:
            raise CommanderUnavailable(
                f"no local model at {self.endpoint}: {exc}") from exc

    def propose(self, incident: Incident) -> CommanderReport:
        prompt = (
            "You are the RAKSHA commander for a hospital SOC. Propose "
            'containment actions as JSON {"actions": [{"tool": <name>, '
            '"params": <object>, "justification": <text>, '
            '"requested_by": "commander:ollama"}]}. Allowed tools: '
            "host.quarantine, host.release, vlan.move, edge.sever, "
            "edge.restore, session.terminate, creds.rotate, "
            "firewall.rule.add, firewall.rule.remove, snapshot.capture. "
            f"Incident {incident.incident_id}: seeds={list(incident.seeds)}; "
            f"alerts={json.dumps(list(incident.alerts))}."
        )
        body = json.dumps({"model": self.model, "prompt": prompt,
                           "format": "json", "stream": False}).encode()
        try:
            req = urllib.request.Request(
                self.endpoint + "/api/generate", data=body,
                headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read())
            parsed = json.loads(data.get("response", "{}"))
            actions = parsed.get("actions", [])
            if not isinstance(actions, list):
                raise CommanderUnavailable("model output malformed: actions not a list")
            clean = []
            for a in actions:
                if isinstance(a, dict):
                    clean.append({
                        "tool": a.get("tool"),
                        "params": a.get("params", {}),
                        "justification": str(a.get("justification", ""))[:512],
                        "requested_by": str(a.get("requested_by", "commander:ollama"))[:64],
                    })
            return CommanderReport(
                commander_mode=self.mode, proposals=tuple(clean),
                notes=("ollama local model output; still schema-locked, "
                       "twin-checked and budgeted by the Governor",))
        except CommanderUnavailable:
            raise
        except Exception as exc:
            raise CommanderUnavailable(f"ollama call failed: {exc}") from exc


def get_commander(prefer_model: Optional[str] = None):
    """Best available commander. Without a reachable local model this is
    ALWAYS the deterministic fallback -- the pipeline never blocks on a
    model being present, and the response declares which mode ran."""
    model = prefer_model or os.environ.get("RAKSHA_OLLAMA_MODEL")
    if model:
        candidate = OllamaCommander(model)
        try:
            candidate.healthcheck()
            return candidate
        except CommanderUnavailable:
            pass
    return FallbackCommander()
