"""Fake-organisation Infra demos backed by the deterministic runtime."""
from __future__ import annotations

from .hospital import (
    HOSPITAL_CAMPAIGN_ID, HOSPITAL_CASE_ID, HOSPITAL_CONTRACT,
    HOSPITAL_ORGANIZATION, HOSPITAL_SENSOR_KEY, HOSPITAL_TOPOLOGY_PATH,
    SCENARIO_STEPS, AttackStep, HospitalScenario,
)

__all__ = [
    "HOSPITAL_CAMPAIGN_ID", "HOSPITAL_CASE_ID", "HOSPITAL_CONTRACT",
    "HOSPITAL_ORGANIZATION", "HOSPITAL_SENSOR_KEY", "HOSPITAL_TOPOLOGY_PATH",
    "SCENARIO_STEPS", "AttackStep", "HospitalScenario",
]
