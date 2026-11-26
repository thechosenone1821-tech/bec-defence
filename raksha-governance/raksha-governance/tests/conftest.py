"""Fixtures: a deterministic fake clock and a fresh Governor per test."""
from __future__ import annotations

import pytest

from raksha import BudgetConfig, Governor
from raksha.fido2 import generate_signer


class FakeClock:
    def __init__(self, start: float = 1_700_000_000.0) -> None:
        self.t = float(start)

    def __call__(self) -> float:
        return self.t

    def advance(self, seconds: float) -> None:
        self.t += seconds


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock()


@pytest.fixture
def gov(clock) -> Governor:
    return Governor(clock=clock, budget_config=BudgetConfig())


@pytest.fixture
def signer_priv(gov):
    priv, pub = generate_signer()
    gov.fido.register("on-call", pub)
    return priv


@pytest.fixture
def now(clock) -> float:
    return clock()
