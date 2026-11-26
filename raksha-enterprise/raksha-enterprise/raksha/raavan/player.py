"""RAAVAN — the red-team player.

RAAVAN emits detections of its own attacks through the normal verification
path: it signs its attack corpus with the sensor key and submits it exactly
like a real sensor would (HTTP POST to the bus, or direct pipeline submission
in embedded mode). It then checks the outcomes it expected — detections per
step, quarantines for unsigned/tampered probes, the Governor's refusal of the
ICU cut and the allowance of the lesser containment.

RAAVAN replays a signed corpus; it is not a live adversary, and its report
never claims one was stopped.
"""

from __future__ import annotations

import argparse
import json
import time
from dataclasses import dataclass, field
from importlib import resources
from pathlib import Path

from ..config import Settings, ensure_dirs, load_or_create_sensor_key
from ..events import Event, EventValidationError, sign_event, tamper_event
from ..ledger import LedgerStore
from ..logging_setup import setup_logging
from ..metrics import Metrics
from ..pipeline import Pipeline
from ..storage import EventStore

DEFAULT_SCENARIO = "scenarios/c2247.json"


def load_scenario(path: Path | None = None) -> dict:
    if path is not None:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    return json.loads(
        resources.files("raksha").joinpath(f"raavan/{DEFAULT_SCENARIO}").read_text(encoding="utf-8")
    )


@dataclass
class StepResult:
    step_id: str
    label: str
    events_sent: int = 0
    detections: list[dict] = field(default_factory=list)
    quarantined: list[str] = field(default_factory=list)
    decisions: list[dict] = field(default_factory=list)
    failures: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.failures


class RaavanPlayer:
    def __init__(self, transport, sensor_key: bytes, scenario: dict,
                 ledger: LedgerStore | None = None) -> None:
        """transport: callable(Event) -> result dict (pipeline.process output or bus response)."""
        self._transport = transport
        self._key = sensor_key
        self._scenario = scenario
        self._ledger = ledger
        self._fused_seen = False

    # -- corpus --------------------------------------------------------------
    def _build_event(self, spec: dict) -> Event:
        event = Event(
            event_id=spec["event_id"], ts=spec["ts"], organ=spec["organ"],
            campaign_id=spec.get("campaign_id", ""), case_id=spec.get("case_id", ""),
            leg=spec["leg"], severity=spec["severity"], entity=spec["entity"],
            summary=spec["summary"], payload=spec["payload"],
        )
        if not spec.get("unsigned"):
            sign_event(event, self._key)
        if spec.get("tamper"):
            tamper_event(event)
        return event

    @staticmethod
    def _match_detections(expect: list[dict], detections: list[dict]) -> list[str]:
        got = {(d["organ"], d["entity"]) for d in detections}
        return [f"expected detection {pair} did not fire"
                for pair in ((e["organ"], e["entity"]) for e in expect) if pair not in got]

    # -- run -----------------------------------------------------------------
    def run(self) -> dict:
        started = time.perf_counter()
        height_before = self._ledger.height() if self._ledger else None
        step_results: list[StepResult] = []
        all_detections: list[dict] = []
        all_decisions: list[dict] = []

        for step in self._scenario["steps"]:
            result = StepResult(step_id=step["id"], label=step["label"])
            for spec in step["events"]:
                try:
                    event = self._build_event(spec)
                except EventValidationError as exc:
                    result.failures.append(f"{spec.get('event_id')}: invalid scenario event: {exc}")
                    continue
                result.events_sent += 1
                outcome = self._transport(event)
                campaign = outcome.get("campaign") or {}
                if campaign.get("fused"):
                    self._fused_seen = True
                if outcome.get("verified") != "valid":
                    result.quarantined.append(outcome["event_id"])
                result.detections.extend(outcome.get("detections") or [])
                result.decisions.extend(outcome.get("decisions") or [])

            expect = step.get("expect", {})
            result.failures.extend(
                self._match_detections(expect.get("detections", []), result.detections))
            n_quarantined = expect.get("quarantined")
            if n_quarantined is not None and len(result.quarantined) != n_quarantined:
                result.failures.append(
                    f"expected {n_quarantined} quarantined events, got {len(result.quarantined)}")
            for expected in expect.get("decisions", []):
                suffix, verdict = expected["proposal_suffix"], expected["verdict"]
                if not any(suffix in d["proposal_id"] and d["verdict"] == verdict
                           for d in result.decisions):
                    result.failures.append(f"expected a {verdict} decision on proposal matching {suffix!r}")
            all_detections.extend(result.detections)
            all_decisions.extend(result.decisions)
            step_results.append(result)

        report = self._final_expectations(all_detections, all_decisions, sum(len(r.quarantined) for r in step_results))
        report["steps"] = [vars(r) for r in step_results]
        report["wall_clock_ms"] = round((time.perf_counter() - started) * 1000, 1)
        if self._ledger is not None:
            report["ledger_height_before"] = height_before
            report["ledger_height_after"] = self._ledger.height()
        report["ok"] = report["ok"] and all(r.ok for r in step_results)
        return report

    def _final_expectations(self, detections: list[dict], decisions: list[dict],
                            total_quarantined: int) -> dict:
        expect = self._scenario.get("expect", {})
        failures: list[str] = []
        refusals = [d for d in decisions if d["verdict"] == "REFUSED"]
        allowances = [d for d in decisions if d["verdict"] == "ALLOWED"]

        if expect.get("total_detections") is not None and len(detections) != expect["total_detections"]:
            failures.append(f"expected {expect['total_detections']} detections, got {len(detections)}")
        if expect.get("quarantined") is not None and total_quarantined != expect["quarantined"]:
            failures.append(f"expected {expect['quarantined']} quarantines, got {total_quarantined}")
        if expect.get("campaign_fused") and not self._fused_seen:
            failures.append("campaign never fused across both legs")
        if expect.get("refusals") is not None and len(refusals) != expect["refusals"]:
            failures.append(f"expected {expect['refusals']} refusals, got {len(refusals)}")
        if expect.get("allowances") is not None and len(allowances) != expect["allowances"]:
            failures.append(f"expected {expect['allowances']} allowances, got {len(allowances)}")
        if expect.get("refused_proposal_suffix") and \
                not any(expect["refused_proposal_suffix"] in d["proposal_id"] for d in refusals):
            failures.append(f"no refusal on proposal matching {expect['refused_proposal_suffix']!r}")
        if expect.get("fallback_allowed_suffix") and \
                not any(expect["fallback_allowed_suffix"] in d["proposal_id"] for d in allowances):
            failures.append(f"no allowance on fallback proposal matching {expect['fallback_allowed_suffix']!r}")
        return {
            "scenario_id": self._scenario["scenario_id"],
            "scenario_name": self._scenario["name"],
            "framing": self._scenario["framing"],
            "total_detections": len(detections),
            "refusals": [d["proposal_id"] for d in refusals],
            "allowances": [d["proposal_id"] for d in allowances],
            "failures": failures,
            "ok": not failures,
        }


# -- transports ----------------------------------------------------------------
def embedded_transport(pipeline: Pipeline):
    def _send(event: Event) -> dict:
        return pipeline.process(event, source="raavan")
    return _send


def http_transport(base_url: str, token: str):
    """Submit to a running bus. The player signs with the deployment's sensor
    key — pass it via --sensor-key-hex / RAKSHA_SENSOR_KEY."""
    import httpx  # optional dependency, bus mode only

    client = httpx.Client(base_url=base_url.rstrip("/"), timeout=30.0)

    def _send(event: Event) -> dict:
        response = client.post("/v1/telemetry", json=event.to_dict(),
                               headers={"Authorization": f"Bearer {token}"})
        response.raise_for_status()
        return response.json()
    return _send


# -- entrypoints ---------------------------------------------------------------
def run_embedded(data_dir: Path, scenario_path: Path | None = None) -> dict:
    settings = Settings(data_dir=data_dir.resolve(), log_level="WARNING", rate_limit_epm=600)
    ensure_dirs(settings)
    sensor_key = load_or_create_sensor_key(settings)
    store = EventStore(settings.events_db_path)
    ledger = LedgerStore(settings.ledger_db_path)
    pipeline = Pipeline(settings, sensor_key, ledger, store, Metrics())
    player = RaavanPlayer(embedded_transport(pipeline), sensor_key,
                          load_scenario(scenario_path), ledger=ledger)
    return player.run()


def run_against_bus(base_url: str, token: str, sensor_key_hex: str,
                    scenario_path: Path | None = None) -> dict:
    sensor_key = bytes.fromhex(sensor_key_hex)
    scenario = load_scenario(scenario_path)
    player = RaavanPlayer(http_transport(base_url, token), sensor_key, scenario)
    return player.run()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="raksha-raavan",
        description="RAAVAN red-team replay: signed attack corpus through the normal verification path",
    )
    parser.add_argument("--bus-url", default=None, help="run against a live bus, e.g. http://127.0.0.1:8000")
    parser.add_argument("--token", default=os_environ_token(), help="API token with telemetry:write scope")
    parser.add_argument("--sensor-key-hex", default=None, help="sensor HMAC key (bus mode; or RAKSHA_SENSOR_KEY)")
    parser.add_argument("--data-dir", default="./data", help="data dir for embedded mode")
    parser.add_argument("--scenario", default=None, help="scenario JSON path (default: packaged c2247)")
    args = parser.parse_args(argv)
    setup_logging("WARNING")

    scenario_path = Path(args.scenario) if args.scenario else None
    if args.bus_url:
        key_hex = args.sensor_key_hex or os_environ_sensor_key()
        report = run_against_bus(args.bus_url, args.token, key_hex, scenario_path)
    else:
        report = run_embedded(Path(args.data_dir), scenario_path)
    print(json.dumps(report, indent=2, sort_keys=True, default=str))
    return 0 if report["ok"] else 1


def os_environ_token() -> str:
    import os
    return os.environ.get("RAAVAN_TOKEN", "")


def os_environ_sensor_key() -> str:
    import os
    value = os.environ.get("RAKSHA_SENSOR_KEY", "")
    if not value:
        raise SystemExit("bus mode needs the sensor key: --sensor-key-hex or RAKSHA_SENSOR_KEY")
    return value


if __name__ == "__main__":
    raise SystemExit(main())
