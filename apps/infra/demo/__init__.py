"""Fake-organisation Infra demos backed by the deterministic runtime.

``hospital`` runs an isolated multi-stage exercise with its own runtime; ``scenarios``
is a read-only script library that posts synthetic events into the shared runtime so
the real console surfaces move. Both are simulated and dry-run only.
"""
from __future__ import annotations

from .hospital import (
    HOSPITAL_CAMPAIGN_ID, HOSPITAL_CASE_ID, HOSPITAL_CONTRACT,
    HOSPITAL_ORGANIZATION, HOSPITAL_SENSOR_KEY, HOSPITAL_TOPOLOGY_PATH,
    SCENARIO_STEPS, AttackStep, HospitalScenario,
)

from .scenarios import (
    SCENARIOS, SCENARIOS_CONTRACT, SIMULATION_LABEL, Scenario, ScenarioStep,
    build_event, catalogue_snapshot, scenario_for,
)

__all__ = [
    "HOSPITAL_CAMPAIGN_ID", "HOSPITAL_CASE_ID", "HOSPITAL_CONTRACT",
    "HOSPITAL_ORGANIZATION", "HOSPITAL_SENSOR_KEY", "HOSPITAL_TOPOLOGY_PATH",
    "SCENARIO_STEPS", "AttackStep", "HospitalScenario",
    "SCENARIOS", "SCENARIOS_CONTRACT", "SIMULATION_LABEL", "Scenario", "ScenarioStep",
    "build_event", "catalogue_snapshot", "scenario_for",
]
