"""Simulated attack scenarios for the Infrastructure console.

Everything in this module is a **script for synthetic telemetry**, not an attack
tool. Each step is one enterprise-I1 event built from the active detector
registry's own fixtures (``ORGAN_FIXTURES``), so a step that claims a rule fires
fires exactly that rule, and a step marked quiet stays quiet. No host, network,
account or file is touched: the events are posted by the browser through the same
same-origin gateway and public ingest path a real organ uses, which means the
detections, quarantines, campaign fusion, Governor decisions and ledger entries
the console shows afterwards are the real runtime's answers — not a storyboard.

Why a script instead of a fake dashboard
---------------------------------------
A presentation surface that invents its own numbers cannot be trusted for one
more second than it takes to open the ledger. So this module owns only the
*inputs* (labelled ``SIMULATED`` inside every event summary, in every campaign
id and in every case id) and the *expectations* that the acceptance test checks
against ``detect(event)``. All state stays in the shared deterministic runtime.

Nothing here executes a live containment action, imports a Commander/SLM client
or performs real counter-measures: the executor is dry-run, organ control is
refused, and efficacy against real traffic is UNMEASURED.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from apps.infra.detectors.registry import ORGAN_FIXTURES, ORGANS

SCENARIOS_CONTRACT = "raksha-simulated-attack-scenarios-v1"  # the route path is owned by apps/infra/features.py

#: every generated artefact carries this label, in the event body itself
SIMULATION_LABEL = "SIMULATED"
CAMPAIGN_TEMPLATE = f"{SIMULATION_LABEL}-{{scenario}}-{{tag}}"
CASE_TEMPLATE = f"{SIMULATION_LABEL}-CASE-{{tag}}"
EVENT_TEMPLATE = f"evt_sim_{{scenario}}_{{tag}}_{{index:02d}}"
#: the console substitutes these two tokens at trigger time, so ids stay unique
#: per run (the runtime refuses a repeated ``event_id``) and timestamps are live
TAG_TOKEN = "{tag}"
TS_TOKEN = "{ts}"

#: how each event reaches the ingest boundary — the failure modes are deliberate
ENVELOPE_SIGNED = "signed"
ENVELOPE_UNSIGNED = "unsigned"
ENVELOPE_FORGED = "forged"
ENVELOPES = (ENVELOPE_SIGNED, ENVELOPE_UNSIGNED, ENVELOPE_FORGED)

#: which registry fixture a step draws its payload from
FIXTURE_FIRING = "firing"
FIXTURE_SILENT = "silent"
FIXTURE_MISSING = "missing"
FIXTURES = (FIXTURE_FIRING, FIXTURE_SILENT, FIXTURE_MISSING)

#: what the step is expected to do to the runtime, and what the UI colours it with
EXPECT_FINDING = "finding"
EXPECT_NO_DETECTION = "no_detection"
EXPECT_QUARANTINE = "quarantine"
EXPECTATIONS = (EXPECT_FINDING, EXPECT_NO_DETECTION, EXPECT_QUARANTINE)
#: quarantine states the runtime can answer with, straight from the contract
HELD_STATES = ("unsigned", "tampered")

CLAIMS_NOT_MADE = (
    "real attack traffic",
    "real victim host, account or network",
    "real-world detection accuracy",
    "live containment action",
    "Commander inference",
    "production SLA",
)

HOW_TO_READ = (
    "Every event below is synthetic and labelled SIMULATED in its summary, its "
    "campaign id and its case id.",
    "Signed steps traverse the same HMAC verification path a real organ uses; the "
    "unsigned and forged steps exist to be refused, which is the demonstration.",
    "Detection, quarantine, fusion, decision and ledger numbers shown after a "
    "trigger are read back from the runtime, never written by this page.",
    "The ledger is append-only, so a reset clears the console view and starts a "
    "new run tag; it cannot and does not erase sealed evidence.",
)


def _payload(organ: str, fixture: str) -> dict[str, Any]:
    """One registry fixture, copied — never re-typed."""
    return dict(ORGAN_FIXTURES[organ][fixture])


@dataclass(frozen=True)
class ScenarioStep:
    """One synthetic event, with the outcome the acceptance test asserts."""

    key: str
    title: str
    narrative: str
    organ: str
    leg: str
    entity: str
    severity: int
    fixture: str = FIXTURE_FIRING
    envelope: str = ENVELOPE_SIGNED
    expects: str = EXPECT_FINDING
    expects_rule: str | None = None

    def summary(self) -> str:
        return f"{SIMULATION_LABEL} · {self.title}"

    def payload(self) -> dict[str, Any]:
        return _payload(self.organ, self.fixture)

    def rule_reason(self) -> str:
        """The registry's own reason text for the rule this step expects."""
        if not self.expects_rule:
            return ""
        spec = ORGANS.get(self.organ)
        for rule in getattr(spec, "rules", ()):
            if rule.rule_id == self.expects_rule:
                return rule.reason
        return ""

    def to_dict(self) -> dict[str, Any]:
        spec = ORGANS.get(self.organ)
        return {
            "key": self.key,
            "title": self.title,
            "narrative": self.narrative,
            "organ": self.organ,
            "ring": getattr(spec, "ring", ""),
            "leg": self.leg,
            "entity": self.entity,
            "severity": self.severity,
            "fixture": self.fixture,
            "envelope": self.envelope,
            "expects": self.expects,
            "expects_rule": self.expects_rule or "",
            "rule_reason": self.rule_reason(),
            "payload": self.payload(),
            "summary": self.summary(),
        }


@dataclass(frozen=True)
class Scenario:
    """A named demonstration with its own trigger button in the console."""

    id: str
    name: str
    tactic: str
    story: str
    watch_for: str
    steps: tuple[ScenarioStep, ...]

    @property
    def severity(self) -> int:
        return max(step.severity for step in self.steps)

    @property
    def organs(self) -> tuple[str, ...]:
        seen: list[str] = []
        for step in self.steps:
            if step.organ not in seen:
                seen.append(step.organ)
        return tuple(seen)

    @property
    def rings(self) -> tuple[str, ...]:
        seen: list[str] = []
        for step in self.steps:
            ring = str(getattr(ORGANS.get(step.organ), "ring", ""))
            if ring and ring not in seen:
                seen.append(ring)
        return tuple(seen)

    def campaign_id(self, tag: str) -> str:
        return CAMPAIGN_TEMPLATE.format(scenario=self.id, tag=tag)

    def case_id(self, tag: str) -> str:
        return CASE_TEMPLATE.format(tag=tag)

    def to_dict(self, *, tag: str = TAG_TOKEN) -> dict[str, Any]:
        steps = [step.to_dict() for step in self.steps]
        for index, step in enumerate(steps, start=1):
            step["index"] = index
            step["event"] = build_event(self, step, tag=tag, ts=TS_TOKEN, index=index)
        return {
            "id": self.id,
            "name": self.name,
            "tactic": self.tactic,
            "story": self.story,
            "watch_for": self.watch_for,
            "severity": self.severity,
            "simulated": True,
            "label": SIMULATION_LABEL,
            "organs": list(self.organs),
            "rings": list(self.rings),
            "campaign_id": self.campaign_id(tag),
            "case_id": self.case_id(tag),
            "step_count": len(steps),
            "steps": steps,
        }


def build_event(scenario: Scenario, step: dict[str, Any], *, tag: str, ts: str,
                 index: int) -> dict[str, Any]:
    """The exact wire object the console posts, with its two tokens filled in.

    The event carries only the fields the enterprise-I1 contract defines, so a
    forged step must hand-write a signature the sensor key never produced — that
    is what the quarantine proves.
    """
    event: dict[str, Any] = {
        "event_id": EVENT_TEMPLATE.format(scenario=scenario.id, tag=tag, index=index),
        "ts": ts,
        "organ": step["organ"],
        "campaign_id": scenario.campaign_id(tag),
        "case_id": scenario.case_id(tag),
        "leg": step["leg"],
        "severity": step["severity"],
        "entity": step["entity"],
        "summary": step["summary"],
        "payload": dict(step["payload"]),
    }
    if step["envelope"] == ENVELOPE_FORGED:
        # a signature that was never minted with the shared sensor key
        event["sig"] = "0" * 64
        event["sig_alg"] = "HMAC-SHA256"
    return event


def _step(key: str, title: str, narrative: str, organ: str, leg: str, entity: str,
           severity: int, *, rule: str | None = None, fixture: str = FIXTURE_FIRING,
           envelope: str = ENVELOPE_SIGNED,
           expects: str | None = None) -> ScenarioStep:
    """One call per step; the expectation follows from the fixture and envelope."""
    if expects is None:
        if envelope == ENVELOPE_SIGNED:
            expects = EXPECT_FINDING if rule else EXPECT_NO_DETECTION
        else:
            expects = EXPECT_QUARANTINE
    return ScenarioStep(
        key=key, title=title, narrative=narrative, organ=organ, leg=leg, entity=entity,
        severity=severity, fixture=fixture, envelope=envelope, expects=expects,
        expects_rule=rule,
    )


# ---------------------------------------------------------------------------
# The library. Eight scenarios, all eight registry organs, one negative control.
# ---------------------------------------------------------------------------

SCENARIOS: tuple[Scenario, ...] = (
    Scenario(
        id="suspicious-login",
        name="Suspicious login activity",
        tactic="Credential access · session replay",
        story=(
            "A burst of unusual sign-ins arrives for one account from the consumer leg: the same "
            "session cookie re-presented at a cadence the login path has never shown, then a "
            "replay that carries a signature the sensor key could not have produced."
        ),
        watch_for=(
            "The quiet baseline stays quiet, the replay burst fires the turbulence rule, and the "
            "spoofed retries are held as evidence instead of becoming findings."
        ),
        steps=(
            _step("baseline", "Quiet sign-in baseline",
                  "Two ordinary sign-ins inside the laminar band — the screen must not accuse them.",
                  "cookie_fluid_turbulence", "citizen", "HOST_CONSUMER_01", 1,
                  fixture=FIXTURE_SILENT),
            _step("replay-burst", "Replayed session cookie, turbulent cadence",
                  "The same credential is replayed above the laminar boundary three times in one window.",
                  "cookie_fluid_turbulence", "citizen", "HOST_CONSUMER_01", 4,
                  rule="COOKIE-TURBULENT-REPLAY"),
            _step("enterprise-replay", "Same cookie accepted on the enterprise path",
                  "The second leg sees the replay too, so the two legs fuse into one campaign.",
                  "cookie_fluid_turbulence", "infra", "ID_GATEWAY_03", 4,
                  rule="COOKIE-TURBULENT-REPLAY"),
            _step("spoofed-retry", "Unsigned retry of the same evidence",
                  "The attacker re-sends the event without a signature; it must be held, never trusted.",
                  "cookie_fluid_turbulence", "infra", "ID_GATEWAY_03", 5,
                  envelope=ENVELOPE_UNSIGNED, rule="COOKIE-TURBULENT-REPLAY"),
            _step("forged-retry", "Forged signature on a tampered severity",
                  "A signature the sensor key never minted — quarantine, and no say in the decision path.",
                  "cookie_fluid_turbulence", "infra", "ID_GATEWAY_03", 5,
                  envelope=ENVELOPE_FORGED, rule="COOKIE-TURBULENT-REPLAY"),
        ),
    ),
    Scenario(
        id="ransomware-sweep",
        name="Ransomware encryption sweep",
        tactic="Impact · mass file encryption",
        story=(
            "A workstation starts encrypting far faster than any backup job, and the first write to "
            "a monitored honey page breaks its XOR invariant. A second host shows the same burst "
            "count but no invariant break, so the two must not be treated alike."
        ),
        watch_for=(
            "One organ, two very different answers: a sealed finding on the host that touched the "
            "honey page, and a verified no-detection on the noisy but innocent one."
        ),
        steps=(
            _step("encrypt-burst", "Encryption event burst on the finance host",
                  "Mass encryption rate with the honey-page parity invariant broken on first write.",
                  "page_curve_trap", "infra", "HOST_FINANCE_22", 5,
                  rule="PAGECURVE-PARITY-BREAK"),
            _step("backup-job", "Nightly backup job with the same burst rate",
                  "A high encrypt rate alone is not the signal — the invariant is intact.",
                  "page_curve_trap", "infra", "HOST_BACKUP_02", 2, fixture=FIXTURE_SILENT),
            _step("shadow-delete", "Shadow-copy deletion on the file server",
                  "The sweep reaches the share; the same rule catches the second host.",
                  "page_curve_trap", "infra", "HOST_FILESRV_05", 5,
                  rule="PAGECURVE-PARITY-BREAK"),
            _step("endpoint-note", "Endpoint agent reports a locked screen, no page features",
                  "An event that carries no readable page-curve features degrades to no_detection.",
                  "page_curve_trap", "infra", "HOST_LAPTOP_77", 3, fixture=FIXTURE_MISSING),
            _step("victim-report", "User reports the ransom note on the consumer leg",
                  "The consumer-side report becomes the second leg, so the campaign can fuse.",
                  "cookie_fluid_turbulence", "citizen", "HOST_CONSUMER_44", 4,
                  rule="COOKIE-TURBULENT-REPLAY"),
        ),
    ),
    Scenario(
        id="ai-agent-flood",
        name="Coordinated AI-agent flood",
        tactic="Impact · volumetric agent flood (DDoS-style)",
        story=(
            "A fleet of scripted agents converges on one edge service. Individually each session is "
            "unremarkable; together they collapse onto a single rank-1 cluster, and the cascade "
            "metric on the network fabric climbs past the percolation threshold."
        ),
        watch_for=(
            "Many small events becoming one campaign: three agent findings on the same organ, then "
            "the ring-4 cascade rule confirming the blast is spreading."
        ),
        steps=(
            _step("agent-01", "Agent pool cluster · rank-1 session condensation",
                  "The first third of the fleet lands on one projector edge.",
                  "bec_spectral_filter", "infra", "HOST_EDGE_07", 4,
                  rule="BEC-RANK1-CONDENSATION"),
            _step("agent-02", "Agent pool cluster · second wave",
                  "A second wave from another entity, same organ, same rule.",
                  "bec_spectral_filter", "infra", "HOST_EDGE_09", 4,
                  rule="BEC-RANK1-CONDENSATION"),
            _step("agent-03", "Agent pool cluster · third wave",
                  "A third wave; the runtime keeps every sealed detection, it does not average them away.",
                  "bec_spectral_filter", "infra", "HOST_EDGE_11", 4,
                  rule="BEC-RANK1-CONDENSATION"),
            _step("human-traffic", "Ordinary traffic during the flood",
                  "Eleven sessions, no condensation — a busy service is not an attack.",
                  "bec_spectral_filter", "infra", "HOST_EDGE_03", 1, fixture=FIXTURE_SILENT),
            _step("cascade", "Fabric cascade risk while the flood holds",
                  "The non-backtracking spectral radius crosses the cascade threshold.",
                  "hashimoto_percolation", "infra", "FABRIC_CORE_01", 5,
                  rule="HASHIMOTO-CASCADE-RISK"),
            _step("citizen-noise", "Consumers report the outage on the citizen leg",
                  "The citizen leg carries a second signal, so the flood can fuse with it.",
                  "cookie_fluid_turbulence", "citizen", "HOST_CONSUMER_12", 3,
                  rule="COOKIE-TURBULENT-REPLAY"),
        ),
    ),
    Scenario(
        id="hostile-document",
        name="Hostile document through the mail gateway",
        tactic="Delivery · adversarial payload in an invoice",
        story=(
            "A vendor invoice carries a periodic adversarial suffix in its token spectrum and fractures "
            "the document graph. A second message in the same window carries no spectral features at all "
            "and must be released untouched."
        ),
        watch_for=(
            "Two documents, two outcomes: one sealed adversarial-suffix finding, one quiet pass — the "
            "screen never guesses when the features are absent."
        ),
        steps=(
            _step("invoice-suffix", "Periodic adversarial suffix in an invoice PDF",
                  "Peak energy in the token spectrum, inside a document from an unpaid vendor.",
                  "bragg_fft_firewall", "infra", "DOC_VENDOR_INVOICE", 5,
                  rule="BRAGG-FFT-PEAK"),
            _step("clean-thread", "Ordinary reply in the same thread",
                  "No spectral features supplied, so nothing is accused.",
                  "bragg_fft_firewall", "infra", "DOC_THREAD_REPLY", 1,
                  fixture=FIXTURE_MISSING),
            _step("second-document", "Second weaponised document from another sender",
                  "The same rule fires on a different entity — a pattern, not a coincidence.",
                  "bragg_fft_firewall", "infra", "DOC_PURCHASE_ORDER", 5,
                  rule="BRAGG-FFT-PEAK"),
            _step("forged-telemetry", "Gateway telemetry forged to hide the second document",
                  "The cover-up attempt is quarantined as tampered, and stays visible as evidence.",
                  "bragg_fft_firewall", "infra", "DOC_PURCHASE_ORDER", 5,
                  envelope=ENVELOPE_FORGED, rule="BRAGG-FFT-PEAK"),
        ),
    ),
    Scenario(
        id="infra-anomaly",
        name="Suspicious infrastructure activity",
        tactic="Defense evasion · monitoring anomaly",
        story=(
            "The monitoring system sees a package burning power its instruction rate cannot explain, "
            "while the behaviour trajectory on the same rack diverges instead of converging. Nothing "
            "has crossed a perimeter yet — this is the anomaly-only view an operator usually gets first."
        ),
        watch_for=(
            "Two independent organs agreeing, and the honest limit: an anomaly is a finding, not a "
            "verdict about what the process was doing."
        ),
        steps=(
            _step("power-residual", "Unexplained package-power residual",
                  "Macroscopic power draw that the instruction rate does not account for.",
                  "landauer_thermal_audit", "infra", "HOST_RACK_C12", 3,
                  rule="LANDAUER-POWER-RESIDUAL"),
            _step("idle-cluster", "Same rack, idle workload",
                  "A cool, converging rack stays quiet — the audit does not blame heat alone.",
                  "landauer_thermal_audit", "infra", "HOST_RACK_C13", 1, fixture=FIXTURE_SILENT),
            _step("divergent-agent", "Divergent control trajectory on the agent host",
                  "Sharp curvature with positive Lyapunov drift: the process is not converging.",
                  "hessian_lyapunov_guard", "infra", "HOST_AGENT_POOL_02", 4,
                  rule="HESSIAN-LYAPUNOV-CLIFF"),
            _step("meter-tampering", "Metered host refuses to report its own residual",
                  "An unsigned audit event is held rather than trusted as an all-clear.",
                  "landauer_thermal_audit", "infra", "HOST_RACK_C12", 3,
                  envelope=ENVELOPE_UNSIGNED, rule="LANDAUER-POWER-RESIDUAL"),
        ),
    ),
    Scenario(
        id="kernel-tamper",
        name="Kernel tamper and self-healing shield",
        tactic="Privilege escalation · rootkit repair",
        story=(
            "A dual-strand invariant check on an endpoint disagrees with itself — the signature of a "
            "spliced kernel module. One host has already repaired its shield and reports no mismatch, "
            "which is the answer a healthy fleet should look like."
        ),
        watch_for=(
            "Ring-4 self-healing reported as data: a real mismatch becomes a finding, a repaired host "
            "becomes a verified no-detection, and neither one triggers any live action."
        ),
        steps=(
            _step("invariant-mismatch", "Dual-strand invariant mismatch on an endpoint",
                  "The two measurement strands disagree, and the repair log stays silent.",
                  "muts_ebpf_repair", "infra", "HOST_NODE_18", 5,
                  rule="MUTS-MISMATCH-REPAIR"),
            _step("repaired-host", "Repaired endpoint after the simulated shield splice",
                  "No mismatch on the second read — the shield is holding, so nothing is claimed.",
                  "muts_ebpf_repair", "infra", "HOST_NODE_19", 1, fixture=FIXTURE_SILENT),
            _step("spread", "Second endpoint shows the same mismatch",
                  "The same invariant break on another node, one ring-4 organ, two sealed findings.",
                  "muts_ebpf_repair", "infra", "HOST_NODE_21", 5,
                  rule="MUTS-MISMATCH-REPAIR"),
        ),
    ),
    Scenario(
        id="staged-exfil",
        name="Staged data exfiltration",
        tactic="Collection and exfiltration · cross-leg campaign",
        story=(
            "A staging directory is archived, its entropy climbs, the fabric cascade metric follows, "
            "and the same case token appears on a consumer-leg session replay. Cross-leg fusion is the "
            "point: two half-stories becoming one campaign the Governor can actually rule on."
        ),
        watch_for=(
            "The full chain in one click — detection, fusion, a minimum-disruption proposal, a Governor "
            "decision and a dry-run containment action — with every ledger sequence number visible."
        ),
        steps=(
            _step("session-replay", "Replayed session used to reach the staging share",
                  "The credential that opened the door, seen on the consumer leg.",
                  "cookie_fluid_turbulence", "citizen", "HOST_CONSUMER_07", 4,
                  rule="COOKIE-TURBULENT-REPLAY"),
            _step("staging-archive", "Archive burst on the staging host",
                  "Encryption and archive features on the endpoint page curve, parity invariant broken.",
                  "page_curve_trap", "infra", "HOST_STAGING_04", 5,
                  rule="PAGECURVE-PARITY-BREAK"),
            _step("cascade-out", "Fabric cascade risk on the egress path",
                  "The spectral radius says the traffic is spreading, not stalling.",
                  "hashimoto_percolation", "infra", "FABRIC_EGRESS_02", 5,
                  rule="HASHIMOTO-CASCADE-RISK"),
            _step("cover-up", "Unsigned event claiming the transfer never happened",
                  "A quiet all-clear that was never signed is held, not believed.",
                  "hashimoto_percolation", "infra", "FABRIC_EGRESS_02", 2,
                  envelope=ENVELOPE_UNSIGNED, rule="HASHIMOTO-CASCADE-RISK"),
            _step("thermal-cover", "Power residual during the upload window",
                  "The thermal audit corroborates the transfer window independently.",
                  "landauer_thermal_audit", "infra", "HOST_STAGING_04", 3,
                  rule="LANDAUER-POWER-RESIDUAL"),
        ),
    ),
    Scenario(
        id="benign-baseline",
        name="Benign load spike (control)",
        tactic="Negative control · nothing to find",
        story=(
            "A product launch moves real traffic: busy sessions, hot racks, bursty backups, documents "
            "flying. Every event here is deliberately below the registry's thresholds or missing the "
            "features a rule needs. A demo that only shows alarms proves nothing."
        ),
        watch_for=(
            "Zero findings, zero quarantines, zero decisions — and every event still verified, still "
            "ledger-recorded, still explained. Loudly quiet is the correct answer."
        ),
        steps=(
            _step("quiet-sessions", "Busy but laminar sessions",
                  "Eleven sessions, no condensation.",
                  "bec_spectral_filter", "infra", "HOST_EDGE_02", 1, fixture=FIXTURE_SILENT),
            _step("quiet-logins", "Normal sign-in cadence on the consumer leg",
                  "Below the turbulence boundary, one replay at most.",
                  "cookie_fluid_turbulence", "citizen", "HOST_CONSUMER_01", 1,
                  fixture=FIXTURE_SILENT),
            _step("quiet-documents", "Legitimate invoices",
                  "Spectral peak well under the floor, graph intact.",
                  "bragg_fft_firewall", "infra", "DOC_VENDOR_INVOICE", 1, fixture=FIXTURE_SILENT),
            _step("quiet-endpoints", "Endpoint writes with the invariant intact",
                  "No parity break and a low encryption rate.",
                  "page_curve_trap", "infra", "HOST_FINANCE_22", 1, fixture=FIXTURE_SILENT),
            _step("quiet-cooling", "Cool racks under load",
                  "Power residual inside the explained band.",
                  "landauer_thermal_audit", "infra", "HOST_RACK_C13", 1, fixture=FIXTURE_SILENT),
            _step("quiet-fabric", "Fabric holding its shape",
                  "Spectral radius below the cascade threshold.",
                  "hashimoto_percolation", "infra", "FABRIC_CORE_01", 1, fixture=FIXTURE_SILENT),
        ),
    ),
)

SCENARIO_INDEX: dict[str, Scenario] = {scenario.id: scenario for scenario in SCENARIOS}


def scenario_for(scenario_id: str) -> Scenario | None:
    return SCENARIO_INDEX.get(str(scenario_id or ""))


def catalogue_snapshot() -> dict[str, Any]:
    """The read-only script the Infrastructure console renders and posts back."""
    organs = [{
        "name": name,
        "ring": str(spec.ring),
        "rules": [{"rule_id": rule.rule_id, "reason": rule.reason} for rule in spec.rules],
        "fixtures": {fixture: _payload(name, fixture) for fixture in FIXTURES},
    } for name, spec in ORGANS.items()]
    scenarios = [scenario.to_dict() for scenario in SCENARIOS]
    return {
        "contract": SCENARIOS_CONTRACT,
        "status": "ok",
        "simulated": True,
        "label": SIMULATION_LABEL,
        "synthetic": True,
        "attack_executed": False,
        "dry_run": True,
        "model_backed": False,
        "commander_enabled": False,
        "live_action_paths": 0,
        "notes": list(HOW_TO_READ),
        "claims_not_made": list(CLAIMS_NOT_MADE),
        "id_templates": {
            "event": EVENT_TEMPLATE,
            "campaign": CAMPAIGN_TEMPLATE,
            "case": CASE_TEMPLATE,
            "tokens": [TAG_TOKEN, TS_TOKEN],
        },
        "envelopes": list(ENVELOPES),
        "fixtures": list(FIXTURES),
        "expectations": list(EXPECTATIONS),
        "held_states": list(HELD_STATES),
        "totals": {
            "scenarios": len(scenarios),
            "steps": sum(len(scenario.steps) for scenario in SCENARIOS),
            "organs": len(organs),
            "firing_steps": sum(1 for scenario in SCENARIOS for step in scenario.steps
                                if step.expects == EXPECT_FINDING),
            "quiet_steps": sum(1 for scenario in SCENARIOS for step in scenario.steps
                               if step.expects == EXPECT_NO_DETECTION),
            "held_steps": sum(1 for scenario in SCENARIOS for step in scenario.steps
                              if step.expects == EXPECT_QUARANTINE),
        },
        "organs": organs,
        "scenarios": scenarios,
    }


__all__ = [
    "SCENARIOS_CONTRACT", "SIMULATION_LABEL",
    "CAMPAIGN_TEMPLATE", "CASE_TEMPLATE", "EVENT_TEMPLATE", "TAG_TOKEN", "TS_TOKEN",
    "ENVELOPE_SIGNED", "ENVELOPE_UNSIGNED", "ENVELOPE_FORGED", "ENVELOPES",
    "FIXTURE_FIRING", "FIXTURE_SILENT", "FIXTURE_MISSING", "FIXTURES",
    "EXPECT_FINDING", "EXPECT_NO_DETECTION", "EXPECT_QUARANTINE", "EXPECTATIONS",
    "HELD_STATES", "CLAIMS_NOT_MADE", "HOW_TO_READ",
    "ScenarioStep", "Scenario", "SCENARIOS", "SCENARIO_INDEX",
    "scenario_for", "build_event", "catalogue_snapshot",
]
