#!/usr/bin/env python3
"""HTTP smoke for the Phosphor console served by both active apps.

Boots the two real uvicorn processes (Citizen and Infra/Sentinel) on free
ports, points each app's gateway at the other, and then plays the traffic the
console itself generates: static serving from both roots, the gateway status
probe, the transcript alias, risk fusion, the Red Team three-act replay, the
fleet/containment/orchestration views, the Citizen report forward, the auth
boundaries and the legacy surfaces that stay mounted.

The tokens and the sensor key are deliberately *not* the repository defaults,
so a pass proves the gateway resolves its credentials from the environment and
signs with the key the runtime verifies — and that no credential ever reaches
the browser. No Commander inference, no live containment, no real traffic.
"""
from __future__ import annotations

import json
import os
import pathlib
import signal
import socket
import subprocess
import sys
import time
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parents[1]
STATIC = ROOT / "packages" / "frontend" / "static"

READ_TOKEN = "smoke-observer-token"
SENSOR_TOKEN = "smoke-sensor-token"
SENSOR_KEY = "smoke-sensor-key-not-the-default"
#: a fixed wall clock for the scripted events — the runtime keeps stamps verbatim,
#: so a deterministic `ts` keeps the campaign window arithmetic reproducible
SMOKE_TS = "2026-11-27T04:00:00Z"
CONSOLE_ROUTES = (
    "attack-lab", "call-screen", "citizen-spine", "governance", "message-guard",
    "red-team", "rings", "vigil",
)

CAMPAIGN_ID = "CAMP_PHOSPHOR_REPLAY"
CASE_ID = "CASE_PHOSPHOR_SANDBOX"
#: mirrors frontend/src/components/features/red-team.tsx, which
#: tools/check_frontend_integration.py verifies against the detector registry
STEPS = (
    ("cookie_fluid_turbulence", "citizen", "HOST_CONSUMER_01", 4,
     {"reynolds_number": 3100, "cookie_replay_count": 3}),
    ("bragg_fft_firewall", "infra", "DOC_VENDOR_INVOICE", 5,
     {"fft_peak_ratio": 0.88, "fiedler_value": 0.04}),
    ("bec_spectral_filter", "infra", "HOST_EDGE_07", 4,
     {"condensation_ratio": 0.91, "session_count": 12}),
    ("page_curve_trap", "infra", "HOST_FINANCE_22", 5,
     {"parity_break": 1, "encrypt_events_per_min": 512}),
    ("landauer_thermal_audit", "infra", "HOST_EDGE_07", 3,
     {"power_residual_w": 18.5}),
)


class Smoke:
    def __init__(self) -> None:
        self.checks = 0

    def check(self, condition: bool, message: str) -> None:
        self.checks += 1
        if not condition:
            raise RuntimeError(f"{message} (after {self.checks} checks)")

    def ok(self, response: Any, message: str) -> Any:
        self.check(200 <= response.status_code < 300,
                   f"{message} returned {response.status_code}: {response.text[:200]}")
        return response


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def spawn(name: str, module: str, port: int, env: dict[str, str],
          extra_args: tuple[str, ...] = ()) -> subprocess.Popen[Any]:
    log = open(f"/tmp/phosphor-{name}-smoke.log", "w", encoding="utf-8")
    return subprocess.Popen(
        [sys.executable, "-m", module, "--port", str(port), *extra_args],
        cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT, start_new_session=True,
    )


def wait_ready(port: int, timeout: float = 120.0) -> None:
    import httpx

    deadline = time.time() + timeout
    last = "no attempt"
    while time.time() < deadline:
        try:
            res = httpx.get(f"http://127.0.0.1:{port}/api/frontend/health", timeout=3.0)
            if res.status_code == 200:
                return
            last = f"status {res.status_code}"
        except Exception as exc:
            last = f"{type(exc).__name__}"
        time.sleep(0.5)
    raise RuntimeError(f"app on port {port} never became ready ({last})")


def campaign_events(salt: str, *, forged: bool = False) -> list[dict[str, Any]]:
    ts = f"{time.strftime('%Y-%m-%dT%H:%M:%S', time.gmtime())}Z"
    events: list[dict[str, Any]] = []
    for index, (organ, leg, entity, severity, payload) in enumerate(STEPS, start=1):
        event: dict[str, Any] = {
            "event_id": f"evt_{salt}_{index:02d}",
            "ts": ts,
            "organ": organ,
            "campaign_id": CAMPAIGN_ID,
            "case_id": CASE_ID,
            "leg": leg,
            "severity": severity,
            "entity": entity,
            "summary": f"{organ} replay fixture",
            "payload": payload,
        }
        if forged:
            event["sig"] = "0" * 64
            event["sig_alg"] = "HMAC-SHA256"
        events.append(event)
    return events


def run(smoke: Smoke, infra: Any, citizen: Any) -> None:
    check = smoke.check

    # ---- one static bundle, served by both apps -------------------------
    for client, redirect, service in (
        (citizen, "/console/call-screen", "citizen"),
        (infra, "/console/rings", "infra"),
    ):
        root = client.get("/", follow_redirects=False)
        check(root.status_code == 307, f"{service} root must redirect with 307, got {root.status_code}")
        check(root.headers.get("location") == redirect,
              f"{service} root must land on {redirect}, got {root.headers.get('location')}")
        health = smoke.ok(client.get("/api/frontend/health"), f"{service} frontend health").json()
        check(health["service"] == service, f"{service} frontend health names the wrong service")
        check(health["contract"] == "raksha-phosphor-frontend-v1", f"{service} frontend contract changed")
        check(health["static_build"] is True and health["gateway"] is True,
              f"{service} frontend health reports no static build or no gateway")
        for route in CONSOLE_ROUTES:
            page = smoke.ok(client.get(f"/console/{route}/"), f"{service} page /console/{route}")
            check("ARK OMNITEK" in page.text, f"/console/{route} is not the Phosphor shell")
            check(page.headers.get("cache-control") == "no-store",
                  f"{service} must not let the browser cache a console page")
            for secret in (READ_TOKEN, SENSOR_TOKEN, SENSOR_KEY):
                check(secret not in page.text,
                      f"{service} console HTML must never embed the credential {secret}")
            check("X-API-Token:" not in page.text,
                  f"{service} console HTML must not carry an auth header")
    rings = smoke.ok(infra.get("/console/rings/"), "infra rings page").content
    citizen_rings = smoke.ok(citizen.get("/console/rings/"), "citizen rings page").content
    built = (STATIC / "console" / "rings" / "index.html").read_bytes()
    check(rings == citizen_rings == built,
          "the two apps are not serving the identical static bundle")

    # ---- error handling: JSON 404s, no invented routes -------------------
    missing_api = citizen.get("/api/definitely-not-a-route")
    check(missing_api.status_code == 404, "an unknown api path must 404")
    check(missing_api.headers.get("content-type", "").startswith("application/json"),
          "an unknown api path must answer JSON, not the SPA shell")
    unknown_gateway = citizen.get("/api/gateway/nope")
    check(unknown_gateway.status_code == 404, "an unknown gateway path must 404")
    check("unknown gateway path" in unknown_gateway.text, "an unknown gateway path is unhelpful")
    fallback = citizen.get("/console/not-a-real-app")
    check(fallback.status_code == 200 and "ARK OMNITEK" in fallback.text,
          "an unknown client route must fall back to the console shell")

    # ---- the gateway status probe reaches both services ------------------
    status = smoke.ok(citizen.get("/api/gateway/status"), "gateway status").json()
    check(status["citizen"]["ok"] is True, "the gateway cannot reach the Citizen service")
    check(status["spine"]["ok"] is True, "the gateway cannot reach the Infra service")

    # ---- Citizen surfaces through the gateway ---------------------------
    health = smoke.ok(citizen.get("/api/gateway/citizen/api/citizen/health"),
                      "proxied citizen health").json()
    check(health.get("app") == "citizen" or "status" in health,
          "the citizen health card lost its identity")
    vigil = smoke.ok(citizen.get("/api/gateway/citizen/api/citizen/vigil/status"),
                     "proxied VIGIL status").json()
    check("model_status" in vigil, "VIGIL status is not exposed to the console")
    check(vigil["privacy_efficacy"] == "UNMEASURED", "VIGIL status lost its UNMEASURED claim")
    scam = smoke.ok(citizen.post("/api/gateway/citizen/api/citizen/screen_transcript",
                                 json={"text": "Your account will be blocked. Share the OTP and "
                                               "pay the verification fee by UPI now.", "lang": "en"}),
                    "transcript screen").json()
    check(scam["verdict"] in {"MODERATE", "HIGH", "CRITICAL"},
          f"the scam transcript did not raise a verdict: {scam['verdict']}")
    check(scam["engine"], "the transcript screen lost the MessageGuard engine name")
    check("recording" in scam["disclaimer"].lower(),
          "the transcript screen lost its no-recording disclaimer")
    check(scam["features"]["transcript_characters"] > 0, "transcript features are missing")
    benign = smoke.ok(citizen.post("/api/gateway/citizen/api/citizen/screen_transcript",
                                   json={"text": "The water tanker will arrive at eight this evening.",
                                         "lang": "en"}), "benign transcript").json()
    check(benign["verdict"] in {"LOW", "MODERATE"},
          f"a benign transcript over-flagged as {benign['verdict']}")
    assessed = smoke.ok(citizen.post("/api/gateway/citizen/api/citizen/assess",
                                     json={"message": {"verdict": "HIGH"},
                                           "campaign_linked": True, "repeat_contacts": 3,
                                           "lang": "te"}), "risk fusion").json()
    check(assessed["band"] in {"HIGH", "CRITICAL"}, f"fusion produced band {assessed['band']}")
    check(assessed["advisory"] and assessed["helpline"], "risk fusion lost its advisory/helpline")
    check(assessed["lang"] == "te", "risk fusion ignored the requested language")
    malformed = citizen.post("/api/gateway/citizen/api/citizen/screen_transcript",
                             content=b"not json")
    check(malformed.status_code == 400, f"a malformed body must be a 400, got {malformed.status_code}")
    bad_category = citizen.post("/api/gateway/citizen/api/citizen/report", json={"category": "yacht"})
    check(bad_category.status_code == 422, "the citizen app must refuse an unknown category")

    # ---- Infra surfaces through the gateway -----------------------------
    spine_health = smoke.ok(infra.get("/api/gateway/spine/api/health"), "spine health").json()
    check(spine_health["dry_run"] is True and spine_health["model_backed"] is False,
          "spine health lost its dry-run / no-model declaration")
    check(spine_health["commander_mode"] == "disabled", "the Commander is not reported as disabled")
    check("planes_3_4" not in spine_health, "spine health still invents a planes_3_4 claim")
    state = smoke.ok(infra.get("/api/gateway/spine/api/state"), "state view").json()
    check(state["contract"] == "raksha-phosphor-state-compat-v1", "the state view contract changed")
    check("compatibility view" in state["view"], "the state view must label itself a view")
    check(isinstance(state["recent_events"], list), "the state view lost its feed")
    check(state["governor"]["live_action_paths"] == 0, "the state view reports a live action path")
    check("GUARDED_AUTO" not in json.dumps(state), "the state view invented an autonomy mode")
    fleet = smoke.ok(infra.get("/api/gateway/spine/api/fleet"), "fleet view").json()
    check(fleet["total"] == 8, f"the fleet view should list the 8 registry organs, got {fleet['total']}")
    check(fleet["live_control"] is False, "the fleet view must report live control as unwired")
    check(all(organ["state"] in {"OBSERVED", "QUIET", "HELD_ONLY"}
              for organ in fleet["organs"].values()), "the fleet view invented an organ state")
    check("HEALTHY" not in json.dumps(fleet), "the fleet view still claims unmeasured organ health")
    canary = smoke.ok(infra.get("/api/gateway/spine/api/fleet/canary"), "canary view").json()
    check(canary["canary"]["ran"] is False, "the canary view must not claim it ran a sweep")
    halt = smoke.ok(infra.post("/api/gateway/spine/api/fleet/bragg_fft_firewall/halt",
                               json={"reason": "smoke"}), "fleet halt").json()
    check(halt["status"] == "DRY_RUN_ONLY" and halt["real_action_count"] == 0,
          "organ control is not dry-run only")

    # ---- the three-act replay, exactly as the console page drives it -----
    unsigned = smoke.ok(infra.post("/api/gateway/spine/api/ingest",
                                   json=campaign_events("smoke_u")), "unsigned ingest").json()
    check(unsigned["received"] == 5 and unsigned["unverified"] == 5,
          f"unsigned probes were not all held: {unsigned}")
    check(all(item["body"]["quarantined"] and item["body"]["verified"] == "unsigned"
              for item in unsigned["results"]),
          "unsigned probes did not quarantine as `unsigned`")
    forged = smoke.ok(infra.post("/api/gateway/spine/api/ingest",
                                 json=campaign_events("smoke_f", forged=True)), "forged ingest").json()
    check(forged["unverified"] == 5, "forged signatures were not all held")
    check(all(item["body"]["verified"] == "tampered" for item in forged["results"]),
          "forged signatures did not quarantine as `tampered`")
    held = smoke.ok(infra.post("/api/gateway/spine/api/orchestrate", json={}),
                    "held orchestrate").json()
    check(held["status"] == "HELD_UNVERIFIED_EVIDENCE",
          f"held evidence must not steer the decision path, got {held['status']}")
    check("no live containment" in held["brief"] or "no model inference" in held["brief"],
          "the orchestration brief lost its no-inference / no-live-action wording")
    signed = smoke.ok(infra.post("/api/gateway/spine-signed",
                                 json=campaign_events("smoke_s")), "signed ingest").json()
    check(signed["accepted"] == 5 and signed["unverified"] == 0,
          f"the signed campaign did not verify: accepted={signed['accepted']}")
    fired = {detection["rule_id"]
             for item in signed["results"]
             for detection in item["body"].get("detections") or []}
    check(len(fired) == 5, f"expected five registry rules to fire, got {sorted(fired)}")
    campaigns = [item["body"].get("campaign") for item in signed["results"] if item["body"].get("campaign")]
    check(any(c.get("fused") and set(c.get("legs") or []) == {"citizen", "infra"} for c in campaigns),
          f"the campaign did not fuse across both legs: {campaigns}")
    decisions = [len(item["body"].get("decisions") or []) for item in signed["results"]]
    check(sum(decisions) >= 1, "the fused campaign produced no Governor decision")
    after = smoke.ok(infra.post("/api/gateway/spine/api/orchestrate", json={}),
                     "post-replay orchestrate").json()
    # ten held probes stay in the window next to the signed findings, so the
    # honest answer is PARTIAL_HOLD; DETERMINISTIC_SNAPSHOT is only correct on a
    # runtime that has never seen an unverified event
    check(after["status"] in {"PARTIAL_HOLD", "DETERMINISTIC_SNAPSHOT"},
          f"expected the deterministic view of signed evidence, got {after['status']}")
    check(after["unverified_events"] == 10,
          f"the held probes left the orchestration view: {after['unverified_events']}")
    check(after["commander_mode"] == "disabled", "the Commander engaged during the replay")
    check(len(after["actions"]) >= 1 and len(after["decisions"]) >= 1,
          "the Governor decisions and proposals did not reach the console view")
    check(after["results"] and all(item["result"]["status"] == "dry_run_only"
                                   for item in after["results"]),
          "an execution result was not dry-run")
    containment = smoke.ok(infra.get("/api/gateway/spine/api/containment"), "containment view").json()
    check(containment["status"] == "DRY_RUN_SNAPSHOT",
          f"the containment view lost its dry-run snapshot status: {containment['status']}")
    check(containment["executor_result"]["real_action_count"] == 0
          and containment["executor_result"]["commander_model_invoked"] is False,
          "the containment view claimed a real action or a Commander call")
    check(containment["plan_source"] == "ExhaustivePlanner-v1"
          and containment["governor_id"] == "Phase7Governor-v1",
          "the containment view lost the planner/Governor identity")
    state_after = smoke.ok(infra.get("/api/gateway/spine/api/state"), "state after replay").json()
    campaign = next((c for c in state_after["campaigns"] if c["campaign_id"] == CAMPAIGN_ID), None)
    check(campaign and campaign["fused"] and campaign["size"] >= 2,
          f"the fused campaign is missing from the state view: {state_after['campaigns']}")
    check(state_after["fortress"]["unverified_held"] >= 10,
          "the held probes disappeared from the state view")
    check(state_after["fortress"]["quarantine_states"].get("unsigned") == 5
          and state_after["fortress"]["quarantine_states"].get("tampered") == 5,
          f"quarantine states are not itemised: {state_after['fortress']}")
    fleet_after = smoke.ok(infra.get("/api/gateway/spine/api/fleet"), "fleet after replay").json()
    organs = fleet_after["organs"]
    check(organs["cookie_fluid_turbulence"]["state"] == "OBSERVED"
          and organs["cookie_fluid_turbulence"]["detections"] >= 1,
          "the replaying organ is not reported as observed")
    check(organs["hashimoto_percolation"]["state"] == "QUIET",
          "an organ with no fixture in the replay was reported as more than quiet")

    # ---- the Attack Lab: every scripted scenario, on the console's own path -
    # The library is served by the Infra app and read by the console through the
    # same gateway proxy the browser uses; the payloads come from the detector
    # registry, so the assertions below are the script's own declared
    # expectations rather than numbers this file repeats.
    lab = smoke.ok(infra.get("/api/gateway/spine/api/infra/scenarios"),
                   "attack lab catalogue").json()
    check(lab["contract"] == "raksha-simulated-attack-scenarios-v1",
          f"the scenario catalogue changed contract: {lab['contract']}")
    check(lab["simulated"] is True and lab["attack_executed"] is False,
          "the scenario catalogue does not declare itself simulated and non-attacking")
    check(lab["dry_run"] is True and lab["live_action_paths"] == 0
          and lab["model_backed"] is False and lab["commander_enabled"] is False,
          "the scenario catalogue promised more than the runtime can do")
    lab_ids = {str(sc["id"]) for sc in lab["scenarios"]}
    check(len(lab_ids) >= 8, f"the Attack Lab needs at least 8 scenarios, got {len(lab_ids)}")
    check({"suspicious-login", "infra-anomaly", "ai-agent-flood", "ransomware-sweep"} <= lab_ids,
          f"the demo library lost a requested scenario: {sorted(lab_ids)}")
    check("benign-baseline" in lab_ids,
          "the demo library needs a benign control so a quiet run is demonstrable")
    check(lab["label"] == "SIMULATED"
          and {"real attack traffic", "real-world detection accuracy"} <= set(lab["claims_not_made"]),
          f"the scenario catalogue lost its claims-not-made list: {lab['claims_not_made']}")
    totals = lab["totals"]
    check(totals["scenarios"] == len(lab["scenarios"])
          and totals["organs"] == len(lab["organs"]) == 8
          and totals["steps"] == sum(len(sc["steps"]) for sc in lab["scenarios"])
          and totals["firing_steps"] + totals["quiet_steps"] + totals["held_steps"]
          == totals["steps"],
          f"the scenario catalogue does not add up: {totals}")
    seen_organs: set[str] = set()
    lab_fired = lab_held = lab_quiet = 0
    for lab_index, scenario in enumerate(lab["scenarios"], start=1):
        tag = f"smoke{lab_index}"
        seen_organs.update(scenario["organs"])
        check(scenario["simulated"] is True, f"{scenario['id']} is not labelled simulated")
        # the served script leaves the run tag as a token and the console fills it
        # in, so both halves of the id contract are checked here
        check(scenario["campaign_id"] == f"SIMULATED-{scenario['id']}-{{tag}}"
              and scenario["case_id"] == "SIMULATED-CASE-{tag}",
              f"{scenario['id']} does not carry the SIMULATED campaign/case templates")
        signed: list[dict[str, Any]] = []
        held: list[dict[str, Any]] = []
        order: list[str] = []
        for step in scenario["steps"]:
            event = json.loads(json.dumps(step["event"])
                               .replace("{tag}", tag).replace("{ts}", SMOKE_TS))
            check(str(event["summary"]).startswith("SIMULATED · "),
                  f"{scenario['id']}/{step['key']} is not labelled SIMULATED in its own summary")
            check(event["campaign_id"] == f"SIMULATED-{scenario['id']}-{tag}"
                  and event["case_id"] == f"SIMULATED-CASE-{tag}"
                  and event["event_id"] == f"evt_sim_{scenario['id']}_{tag}_{step['index']:02d}",
                  f"{scenario['id']}/{step['key']} lost its SIMULATED ids after tagging")
            order.append(str(event["event_id"]))
            (signed if step["envelope"] == "signed" else held).append(event)
        answers: dict[str, dict[str, Any]] = {}
        if signed:
            ack = smoke.ok(infra.post("/api/gateway/spine-signed", json=signed),
                           f"{scenario['id']} signed batch").json()
            check(ack["received"] == len(signed),
                  f"{scenario['id']} signed batch lost events: {ack['received']}/{len(signed)}")
            for item in ack["results"]:
                body = item.get("body") or {}
                answers[str(body.get("event_id"))] = body
        if held:
            ack = smoke.ok(infra.post("/api/gateway/spine/api/ingest", json=held),
                           f"{scenario['id']} held batch").json()
            check(ack["received"] == len(held) and ack["unverified"] == len(held),
                  f"untrusted steps were not all held in {scenario['id']}: {ack['unverified']}/{len(held)}")
            for item in ack["results"]:
                body = item.get("body") or {}
                answers[str(body.get("event_id"))] = body
        for step, event_id in zip(scenario["steps"], order):
            body = answers.get(event_id) or {}
            expects = step["expects"]
            detections = body.get("detections") or []
            if expects == "finding":
                check(body.get("accepted") and not body.get("quarantined") and detections
                      and body.get("verified") == "valid",
                      f"{scenario['id']}/{step['key']} expected a sealed finding, got {body}")
                rules = {str(d.get("rule_id")) for d in detections}
                check(step["expects_rule"] in rules,
                      f"{scenario['id']}/{step['key']} fired {rules}, script says {step['expects_rule']}")
                lab_fired += 1
            elif expects == "no_detection":
                check(body.get("accepted") and not body.get("quarantined") and not detections
                      and not body.get("proposals"),
                      f"{scenario['id']}/{step['key']} expected a verified no-detection, got {body}")
                check(body.get("verified") == "valid",
                      f"{scenario['id']}/{step['key']} was not verified: {body.get('verified')}")
                lab_quiet += 1
            else:
                # an unverified event is still ingested — as evidence — but it must
                # never reach a detection, a proposal or a decision
                check(body.get("quarantined") and not detections,
                      f"{scenario['id']}/{step['key']} expected quarantine, got {body}")
                check(not body.get("proposals") and not body.get("decisions")
                      and not body.get("executions"),
                      f"{scenario['id']}/{step['key']} steered the decision path: {body}")
                check(body.get("verified") in {"unsigned", "tampered"},
                      f"{scenario['id']}/{step['key']} held as {body.get('verified')}")
                lab_held += 1
    check(seen_organs == {organ["name"] for organ in lab["organs"]},
          "the scenario library does not cover every registry organ")
    check(lab_fired == totals["firing_steps"] and lab_quiet == totals["quiet_steps"]
          and lab_held == totals["held_steps"],
          f"the Attack Lab drifted from its script: fired={lab_fired}/{totals['firing_steps']} "
          f"quiet={lab_quiet}/{totals['quiet_steps']} held={lab_held}/{totals['held_steps']}")
    lab_state = smoke.ok(infra.get("/api/gateway/spine/api/state"), "state after the Attack Lab").json()
    lab_campaigns = {str(c["campaign_id"]): c for c in lab_state["campaigns"]}
    fused = [cid for cid, card in lab_campaigns.items() if card.get("fused")]
    check(lab_campaigns, "the Attack Lab left no campaign in the state view")
    check(fused, "no scripted scenario fused into a cross-leg campaign")
    smoke_campaigns = [cid for cid in lab_campaigns if cid.endswith(tuple(f"smoke{i}" for i in range(1, 10)))]
    check(smoke_campaigns, "none of the Attack Lab runs reached the state view's campaign list")
    check(all(cid.startswith("SIMULATED-") for cid in smoke_campaigns),
          f"an Attack Lab campaign lost its SIMULATED id: {sorted(smoke_campaigns)[:3]}")
    benign_id = "SIMULATED-benign-baseline-smoke" + str(len(lab["scenarios"]))
    check(benign_id not in lab_campaigns,
          "the benign control produced a campaign row — a quiet run must stay quiet")
    check(lab_state["governor"]["live_action_paths"] == 0
          and lab_state["governor"]["commander_model_invoked"] is False,
          "the Attack Lab produced a live action path or a Commander call")
    sim_events = [str(event.get("event_id") or "") for event in lab_state["recent_events"]
                  if "_sim_" in str(event.get("event_id") or "")]
    check(len(sim_events) >= 1, "the state view echoed no Attack Lab event at all")
    check(all(event.startswith("evt_sim_") for event in sim_events),
          f"an event in the scripted feed lost its evt_sim prefix: {sim_events[:3]}")
    # ---- ledger, auth boundaries, citizen forward ------------------------
    verify = smoke.ok(infra.get("/api/gateway/spine/v1/ledger/verify"), "ledger verify").json()
    check(verify.get("ok") is True, f"the append-only ledger did not verify: {verify}")
    override = infra.post("/api/gateway/spine/v1/decisions/PROP-SMOKE/override", json={})
    check(override.status_code == 403, "the ledger accepted an override attempt")
    import httpx

    bare = httpx.post(f"{infra.base_url}/api/ingest", json=campaign_events("smoke_bare")[0])
    check(bare.status_code == 401,
          f"the raw backend answered {bare.status_code} to an unauthenticated ingest")
    raw_read = httpx.get(f"{infra.base_url}/v1/state")
    check(raw_read.status_code == 401,
          f"the raw backend served state without a token ({raw_read.status_code})")
    raw_list = httpx.post(f"{infra.base_url}/api/ingest", json=campaign_events("smoke_list"))
    check(raw_list.status_code == 422,
          f"a batch posted to the single-event ingest route must be refused, got {raw_list.status_code}")
    leaked = [secret for secret in (READ_TOKEN, SENSOR_TOKEN, SENSOR_KEY, "X-API-Token")
              if secret in json.dumps(state_after) or secret in rings.decode("utf-8", "replace")]
    check(not leaked, "a credential reached a browser-visible response")
    report = smoke.ok(citizen.post("/api/gateway/citizen/api/citizen/report",
                                   json={"category": "call", "severity": 0.9,
                                         "case_id": CASE_ID}), "citizen report").json()
    check(report["status"] == "REPORTED", "the citizen report did not report")
    forward = report.get("forwarded") or {}
    check(forward.get("forwarded") is True,
          f"the citizen report was not forwarded to the shared runtime: {forward}")
    bus_reply = forward.get("bus_reply") or {}
    check(bus_reply.get("accepted") is True and bus_reply.get("quarantined") is True
          and bus_reply.get("verified") == "unknown_organ",
          f"a consumer report should seal as unknown_organ context, got {bus_reply}")
    check(not bus_reply.get("detections"), "a consumer report must not become a detection")

    # ---- legacy surfaces stay mounted ------------------------------------
    smoke.ok(citizen.get("/app/manifest.json"), "the legacy Citizen PWA manifest")
    check(citizen.get("/vigil/").status_code in {200, 307}, "the legacy VIGIL surface stopped responding")
    smoke.ok(infra.get("/app/console"), "the legacy Infra console")
    smoke.ok(infra.get("/demo/hospital"), "the fake-hospital demo")


def main() -> int:
    smoke = Smoke()
    processes: list[subprocess.Popen[Any]] = []
    clients: list[Any] = []
    infra_port, citizen_port = free_port(), free_port()
    specs = (("infra", "apps.infra", infra_port, ("--no-seed-demo",)),
             ("citizen", "apps.citizen", citizen_port, ()))
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join(
        [str(ROOT), str(ROOT / "raksha-code"), env.get("PYTHONPATH", "")])
    env["PYTHONUNBUFFERED"] = "1"
    env.update({
        "RAKSHA_INFRA_INTERNAL_URL": f"http://127.0.0.1:{infra_port}",
        "RAKSHA_CITIZEN_INTERNAL_URL": f"http://127.0.0.1:{citizen_port}",
        "RAKSHA_BUS_URL": f"http://127.0.0.1:{infra_port}",
        "RAKSHA_FRONTEND_READ_TOKEN": READ_TOKEN,
        "RAKSHA_FRONTEND_SENSOR_TOKEN": SENSOR_TOKEN,
        "RAKSHA_OBSERVER_TOKEN": READ_TOKEN,
        "RAKSHA_SENSOR_TOKEN": SENSOR_TOKEN,
        "RAKSHA_SENSOR_KEY": SENSOR_KEY,
    })
    try:
        import httpx

        if not (STATIC / "index.html").is_file():
            raise RuntimeError("static frontend build is missing — run `make frontend-build` first")
        for name, module, port, extra in specs:
            processes.append(spawn(name, module, port, env, extra))
        for _name, _module, port, _extra in specs:
            wait_ready(port)
        infra = httpx.Client(base_url=f"http://127.0.0.1:{infra_port}", timeout=30.0)
        citizen = httpx.Client(base_url=f"http://127.0.0.1:{citizen_port}", timeout=30.0)
        clients = [infra, citizen]
        run(smoke, infra, citizen)

        # A run that only passes --port must still let the console reach its own
        # backend: the gateway has to follow the bound port, not the default.
        bare_port = free_port()
        bare_env = {key: value for key, value in env.items()
                    if not key.startswith(("RAKSHA_INFRA_INTERNAL_URL", "RAKSHA_CITIZEN_INTERNAL_URL",
                                           "RAKSHA_BUS_URL", "RAKSHA_FRONTEND_"))}
        processes.append(spawn("infra-bare", "apps.infra", bare_port, bare_env, ("--no-seed-demo",)))
        wait_ready(bare_port)
        bare_client = httpx.Client(base_url=f"http://127.0.0.1:{bare_port}", timeout=30.0)
        clients.append(bare_client)
        bare_state = smoke.ok(bare_client.get("/api/gateway/spine/api/state"),
                              "console gateway on a --port-only Infra run")
        smoke.check(bare_state.json().get("contract") == "raksha-phosphor-state-compat-v1",
                    "a --port-only run did not reach its own state view")
        bare_page = smoke.ok(bare_client.get("/console/rings/"), "console page on a --port-only run")
        smoke.check("ARK OMNITEK" in bare_page.text,
                    "a --port-only run served the wrong console document")

        for process in processes:
            smoke.check(process.poll() is None, "an app process died during the smoke")
        print(f"OK: Phosphor console served by both apps — {smoke.checks} checks across the static "
              "export, gateway proxy, transcript screen, risk fusion, three-act replay, "
              "fleet/containment views, ledger, auth boundaries, --port self-addressing and legacy "
              "surfaces; "
              "dry-run only, no Commander inference")
        return 0
    except Exception as exc:
        for (name, _module, _port, _extra), process in zip(specs, processes):
            log = pathlib.Path(f"/tmp/phosphor-{name}-smoke.log")
            if log.is_file():
                print(f"--- {name} exit={process.poll()} log tail ---", file=sys.stderr)
                print("\n".join(log.read_text(encoding="utf-8", errors="replace").splitlines()[-30:]),
                      file=sys.stderr)
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    finally:
        for client in clients:
            try:
                client.close()
            except Exception:
                pass
        for process in processes:
            if process.poll() is None:
                try:
                    os.killpg(os.getpgid(process.pid), signal.SIGTERM)
                except (ProcessLookupError, PermissionError):
                    process.terminate()


if __name__ == "__main__":
    raise SystemExit(main())
