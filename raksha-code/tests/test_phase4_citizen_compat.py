"""Legacy-cwd Phase 4 compatibility checks (deterministic, model-free)."""
from __future__ import annotations

import ast
import inspect
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / "raksha-code")]

from apps.citizen import copy as citizen_copy  # noqa: E402
from apps.citizen import features  # noqa: E402
from apps.citizen import voiceguard_interface  # noqa: E402
from packages.contracts.i18n import CitizenRenderer, normalise_language  # noqa: E402


def _lists(value):
    """Normalise frozen tuples so only sentence content, not container type, matters."""
    if isinstance(value, tuple):
        return [_lists(v) for v in value]
    if isinstance(value, list):
        return [_lists(v) for v in value]
    if isinstance(value, dict):
        return {k: _lists(v) for k, v in value.items()}
    return value


def _frozen_table(name: str):
    """Read a frozen literal table without importing VoiceGuard/model code."""
    path = ROOT / "raksha-code/citizen/voiceguard/i18n.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(t, ast.Name) and t.id == name for t in node.targets
        ):
            return _lists(ast.literal_eval(node.value))
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) \
                and node.target.id == name and node.value is not None:
            return _lists(ast.literal_eval(node.value))
    raise AssertionError(f"missing frozen table {name}")


def test_shared_i18n_contract_has_no_app_or_model_imports():
    src = (ROOT / "packages/contracts/i18n.py").read_text(encoding="utf-8")
    tree = ast.parse(src)
    names = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.extend(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom):
            names.append("." * node.level + (node.module or ""))
    assert not any(n.startswith(("apps", "citizen", "voiceguard", "maya")) for n in names)
    assert "class CitizenRenderer" in src


def test_app_copy_owns_sentences_and_matches_frozen_message_copy():
    copy = citizen_copy.CITIZEN_COPY
    assert isinstance(citizen_copy.renderer, CitizenRenderer)
    assert copy["families"] == _frozen_table("_FAMILIES")
    assert copy["message_verdict"] == _frozen_table("_MESSAGE_VERDICT")
    assert copy["message_reason_overrides"] == _frozen_table("_MESSAGE_REASON_OVERRIDES")
    assert copy["no_message_signal"] == _frozen_table("_NO_MESSAGE_SIGNAL")
    assert copy["band_copy"] == _frozen_table("_BAND_COPY")
    assert copy["advisory"] == _frozen_table("_ADVISORY")
    assert copy["report_copy"] == _frozen_table("_REPORT_COPY")
    assert copy["disclaimer"] == _frozen_table("_DISCLAIMER")
    assert normalise_language("TE_in") == "te"
    for lang in ("en", "hi", "te"):
        assert "not integrated yet" in citizen_copy.voice_tab_copy(lang)["status"]
        assert citizen_copy.voice_tab_copy(lang)["model_invoked"] is False


def test_risk_engine_uses_app_copy_not_frozen_adapter():
    from apps.citizen.risk import engine
    src = inspect.getsource(engine)
    for marker in ("i18n.render_band(", "i18n.render_advisory(",
                   "i18n.render_band_reason(", "i18n.render_reason("):
        assert marker in src, marker
    assert "legacy_voiceguard" not in src
    assert "citizen.voiceguard" not in src
    result = engine.assess(message={"verdict": "CRITICAL"}, lang="te")
    assert result["lang"] == "te"
    assert result["band"] != "SAFE"
    assert result["helpline"] == "1930"


def test_disabled_voiceguard_interface_is_documented_and_model_free():
    card = voiceguard_interface.VOICEGUARD_INTERFACE_CARD
    assert card["enabled"] is False
    assert card["status"] == "not integrated yet"
    assert card["no_ai_models"] is True
    assert "citizen.voiceguard.model" in card["forbidden_until_phase_11"]
    status = voiceguard_interface.VOICEGUARD.status()
    assert status["model_invoked"] is False
    response = voiceguard_interface.VOICEGUARD.screen([1.0], consent=True, lang="hi")
    assert response["status"] == "NOT_INTEGRATED"
    assert response["samples_echoed"] is False
    assert "AI" not in response["explanation"]["title"]


def test_feature_flags_are_hard_disabled_without_environment_override():
    assert features.NO_AI_MODELS is True
    assert features.voiceguard_enabled() is False
    assert features.no_ai_models() is True
    flags = features.FEATURE_FLAGS
    assert flags["voiceguard"] is False
    assert flags["maya_capture"] is False
    assert flags["commander_model"] is False
    assert all(flags[k] for k in ("messageguard", "risk_fusion", "report",
                                  "offline_queue", "panic_1930", "family_mode",
                                  "retention"))


def test_capability_card_states_the_four_citizen_invariants():
    cap = features.capability_card()
    assert cap["phase"] == 4
    assert cap["no_ai_models"] is True
    inv = cap["invariants"]
    assert inv["no_raw_score_to_citizen"] is True
    assert inv["no_safe_verdict"] is True
    assert inv["no_pii_leaves_phone"] is True
    assert inv["signature_required"] is True
    assert inv["governor_required"] is True
