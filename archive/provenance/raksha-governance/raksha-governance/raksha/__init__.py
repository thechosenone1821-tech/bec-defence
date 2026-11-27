"""RAKSHA governance -- Response & Governance (Part 5), final consolidated build.

One package, four parts, one iron law: THE AI PROPOSES, THE GOVERNOR
DISPOSES. No component may create a path around the Governor; the
Governor was built first so nothing is ever developed against an
unguarded executor.

  Part 1  Governor safety core      governor.py, tools.py, decisions.py,
                                    policy.py, budgets.py, fido2.py,
                                    tcb.py, watchdog.py, fixtures.py
  Part 2  Evidence (reference)      ledger.py (Part 2 hardening swaps the
                                    implementation, not the interface)
  Part 3  Containment planner       planner.py (exhaustive, J = C + lD + mR + nA)
  Part 4  Commander + dry-run       commander.py, executor.py
        executor + adversarial     + the Governor-side injection suite in
        suite                      tests/

Deterministic Governor and planner. No Commander/SLM client. No
randomness anywhere. Readable by a hospital IT generalist.
"""
from .budgets import BudgetConfig, BudgetWindow
from .canonical import canonical_bytes, canonical_hash, sha256_hex
from .decisions import (
    ALLOW,
    DENY,
    Decision,
    EMPTY_METADATA,
    ESCALATE,
    decisions_agree,
    explain,
)
from .fido2 import (
    Fido2Registry,
    challenge_for,
    generate_signer,
    make_assertion,
)
from .fixtures import Edge, Topology, hospital_fixture
from .governor import Governor, GovernorOutcome
from .ledger import GENESIS_PREV, HashChainLedger, LedgerEntry
from .tools import Action, ASSERTION_FIELDS, TOOL_NAMES, TOOL_REGISTRY, parse_action
from .tcb import DEFAULT_TWINS, TwinA, TwinB
from .watchdog import RevertRegistry
from .planner import ContainmentPlanner, Plan, PLANNER_LAMBDA, PLANNER_MU, PLANNER_NU
from .commander import (
    CommanderReport,
    CommanderUnavailable,
    FallbackCommander,
    Incident,
    MODE_FALLBACK,
    MODE_OLLAMA,
    OllamaCommander,
    get_commander,
)
from .executor import DRY_RUN, DryRunExecutor

__version__ = "1.0.0"

__all__ = [
    "ALLOW", "DENY", "ESCALATE",
    "Action", "ASSERTION_FIELDS",
    "BudgetConfig", "BudgetWindow",
    "CommanderReport", "CommanderUnavailable", "ContainmentPlanner",
    "DRY_RUN", "DryRunExecutor",
    "Decision", "Edge", "EMPTY_METADATA",
    "FallbackCommander", "Fido2Registry",
    "GENESIS_PREV", "Governor", "GovernorOutcome",
    "HashChainLedger", "Incident", "LedgerEntry",
    "MODE_FALLBACK", "MODE_OLLAMA", "OllamaCommander",
    "PLANNER_LAMBDA", "PLANNER_MU", "PLANNER_NU", "Plan",
    "TOOL_NAMES", "TOOL_REGISTRY", "Topology", "TwinA", "TwinB",
    "canonical_bytes", "canonical_hash", "challenge_for",
    "decisions_agree", "explain", "generate_signer", "get_commander",
    "hospital_fixture", "make_assertion", "parse_action",
]
