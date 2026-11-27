#!/usr/bin/env python3
"""Deterministic Phase 5 single-source checker.

Proves one MessageGuard scorer/interface, one reason catalogue, one corpus,
one generated eval document, archived provenance trees and every local Markdown
link. No AI model, VoiceGuard/MAYA inference, Commander endpoint, network call
or pytest run is performed by this checker.
"""
from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import os
import pathlib
import re
import subprocess
import sys
import tempfile
from typing import Any, Dict, List

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import tools.check_local_links as link_checker  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]
LEGACY_ROOT = ROOT / "raksha-code"
ACTIVE_PKG = ROOT / "apps" / "citizen" / "messageguard"
ACTIVE_CORPUS = LEGACY_ROOT / "citizen" / "fixtures" / "messageguard"
RUNNER = ROOT / "evals" / "messageguard.py"
GENERATOR = ROOT / "evals" / "gen_evals_md.py"
FULL_RESULTS = ROOT / "evals" / "results.json"
LEGACY_RUNNER = LEGACY_ROOT / "evals" / "messageguard" / "run_evals.py"
RESULTS = LEGACY_ROOT / "evals" / "messageguard" / "results.json"
GENERATED = ROOT / "EVALS.md"
POINTER = ROOT / "raksha" / "MESSAGEGUARD_EVALS.md"
ARCHIVE = ROOT / "archive" / "provenance"
ALT_ROOT = ARCHIVE / "messageguard-alternative" / "raksha"
SNAP_ROOT = ARCHIVE / "messageguard-snapshot" / "raksha"
PROVENANCE_DIRS = (
    "archive/provenance/messageguard-alternative/raksha/tests",
    "archive/provenance/messageguard-snapshot/raksha/tests",
)
FORBIDDEN_MODEL_PREFIXES = (
    "citizen.voiceguard", "voiceguard", "maya", "run_maya",
    "spine.slm_client", "spine.orchestrator", "spine.bus",
)

sys.path[:0] = [str(ROOT), str(LEGACY_ROOT)]


def check(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def loaded_forbidden_modules():
    """Match tools/phase4_no_ai_plugin.py exactly (prefix or prefix + dot)."""
    return sorted(
        name for name in sys.modules
        if any(name == prefix or name.startswith(prefix + ".")
               for prefix in FORBIDDEN_MODEL_PREFIXES)
    )


def env() -> Dict[str, str]:
    out = dict(os.environ)
    out.update({
        "OLLAMA_HOST": "http://127.0.0.1:9",
        "EIGENSHIELD_MODEL": "disabled",
        "RAKSHA_PHASE4_NO_AI_MODELS": "1",
    })
    out["PYTHONPATH"] = os.pathsep.join([
        str(ROOT), str(LEGACY_ROOT), out.get("PYTHONPATH", ""),
    ]).rstrip(os.pathsep)
    return out


def load_module(name: str, path: pathlib.Path):
    spec = importlib.util.spec_from_file_location(name, path)
    check(spec is not None and spec.loader is not None, f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_python(code: str, cwd: pathlib.Path, use_env: Dict[str, str],
               *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-c", code, *args],
        cwd=cwd, env=use_env, capture_output=True, text=True,
    )


SPEC_PROBE = r'''
import importlib.util, pathlib, sys
root = pathlib.Path(sys.argv[1])
canonical = (root / "apps/citizen/messageguard/__init__.py").resolve()
assert importlib.util.find_spec("raksha.messageguard") is None
assert importlib.util.find_spec("messageguard") is None
s1 = importlib.util.find_spec("apps.citizen.messageguard")
s2 = importlib.util.find_spec("citizen.messageguard")
assert s1 and s2
assert pathlib.Path(s1.origin).resolve() == canonical
assert pathlib.Path(s2.origin).resolve() == canonical
import apps.citizen.messageguard as mg
bad = ("citizen.voiceguard", "voiceguard", "maya", "run_maya",
       "spine.slm_client", "spine.orchestrator", "spine.bus")
assert not any(m == p or m.startswith(p + ".") for m in sys.modules for p in bad)
print("NO_SECOND_SCORER")
'''

ARCHIVE_SPEC_PROBE = r'''
import importlib.util
try:
    spec = importlib.util.find_spec("raksha.messageguard")
except ModuleNotFoundError:
    spec = None
assert spec is None
print("ARCHIVE_NO_SCORER")
'''


def check_import_boundary() -> None:
    for cwd in (ROOT, LEGACY_ROOT):
        proc = run_python(SPEC_PROBE, cwd, env(), str(ROOT))
        check(proc.returncode == 0 and "NO_SECOND_SCORER" in proc.stdout,
              f"second scorer importable from {cwd}: {proc.stdout}{proc.stderr}")
    for cwd in (ALT_ROOT, SNAP_ROOT):
        isolated = dict(os.environ)
        isolated["PYTHONPATH"] = str(cwd)
        proc = run_python(ARCHIVE_SPEC_PROBE, cwd, isolated)
        check(proc.returncode == 0 and "ARCHIVE_NO_SCORER" in proc.stdout,
              f"archived raksha.messageguard importable from {cwd}: {proc.stdout}{proc.stderr}")
    check(not (ROOT / "raksha-messageguard").exists(), "old alternative top-level tree remains")
    check(not (ROOT / "random project that ew need to integrate").exists(),
          "old standalone top-level tree remains")
    for tree in (ALT_ROOT, SNAP_ROOT):
        check(tree.is_dir(), f"missing archived tree: {tree}")
        check(not any(p.is_dir() and p.name == "messageguard" for p in tree.rglob("messageguard")),
              f"archived package directory not renamed in {tree}")
    scorers = [
        p for p in ROOT.rglob("scorer.py")
        if p.parent.name == "messageguard" and ".git" not in p.parts
        and "__pycache__" not in p.parts
    ]
    check([p.resolve() for p in scorers] == [(ACTIVE_PKG / "scorer.py").resolve()],
          f"expected exactly one active messageguard/scorer.py, found {scorers}")


def check_public_interface_and_catalogue() -> None:
    import apps.citizen.messageguard as mg
    import apps.citizen.copy as citizen_copy
    import packages.contracts.i18n as i18n
    import packages.contracts.reasons as reasons
    from apps.citizen.messageguard import tokens_hinglish, normalize

    check(mg.SUPPORTED_LANGS == ("auto", "en", "hi", "te", "hinglish"),
          "canonical supported languages changed")
    check(mg.SUPPORTED_DETECTOR_LANGS == mg.SUPPORTED_LANGS,
          "scorer and package language lists disagree")
    for name in ("analyze", "score_message", "evaluate_fixtures", "detect_language",
                 "to_legacy_organ_payload", "legacy_confidence", "reason_for"):
        check(hasattr(mg, name), f"missing canonical interface: {name}")
    check(not hasattr(mg, "assess"), "second-scorer assess() leaked into canonical package")
    check(not hasattr(mg, "SignalFamilyScorer"),
          "second-scorer SignalFamilyScorer leaked into canonical package")
    check(reasons.REASON_CATALOGUE == mg.REASON_CATALOGUE,
          "reason catalogue is not re-exported from packages/contracts")
    check(set(citizen_copy.MSG_REASON_FAMILY) == set(reasons.REASON_CATALOGUE),
          "citizen copy reason-family keys diverge from the catalogue")
    check(i18n.message_reason_codes() == sorted(reasons.REASON_CATALOGUE),
          "shared i18n reason codes diverge from the catalogue")
    for family, code, row_lang, regexes in tokens_hinglish.PATTERNS:
        check(row_lang == "hinglish", f"Hinglish row has wrong lang: {row_lang}")
        check(code in reasons.REASON_CATALOGUE, f"unknown Hinglish reason code: {code}")
        check(reasons.REASON_CATALOGUE[code][0] == family,
              f"Hinglish family mismatch for {code}")
        check(bool(regexes), f"empty Hinglish regex row for {code}")
    active_sources = list((ACTIVE_PKG).glob("*.py")) + [
        ROOT / "packages" / "contracts" / "reasons.py",
        ROOT / "apps" / "citizen" / "copy.py",
    ]
    for path in active_sources:
        text = path.read_text(encoding="utf-8")
        check(not re.search(r"\bdef\s+assess\s*\(", text),
              f"second scorer assess() found in active source: {path}")
        check("class SignalFamilyScorer" not in text,
              f"second scorer class found in active source: {path}")
        check(not re.search(r"\bmsg\.[a-z_]+", text, re.IGNORECASE),
              f"second msg.* reason-code style found in active source: {path}")
    check(not loaded_forbidden_modules(),
          f"AI/voice model modules loaded by Phase 5 checker imports: {loaded_forbidden_modules()}")
    return normalize


def check_one_corpus(normalize) -> None:
    records: List[Dict[str, Any]] = []
    for path in sorted(ACTIVE_CORPUS.glob("*.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                records.append(json.loads(line))
    check(len(list(ACTIVE_CORPUS.glob("*.jsonl"))) == 18,
          "canonical corpus no longer has 18 JSONL files")
    check(len(records) == 538, f"canonical corpus has {len(records)} rows, expected 538")
    check(len({r["id"] for r in records}) == 538, "duplicate corpus ids")
    check(len({normalize.normalize(r["text"]) for r in records}) == 538,
          "duplicate normalized corpus texts")
    check({r["lang"] for r in records} == {"en", "hi", "te", "hinglish"},
          "unexpected corpus language set")
    check(sum(r["label"] == "scam" for r in records) == 402, "scam count is not 402")
    check(sum(r["label"] == "benign" for r in records) == 136, "benign count is not 136")
    hinglish = [r for r in records if r["lang"] == "hinglish"]
    check(len(hinglish) == 46, f"Hinglish port has {len(hinglish)} rows, expected 46")
    check(all(str(r.get("source", "")).startswith("phase5-port:") for r in hinglish),
          "Hinglish rows missing Phase 5 provenance")
    from apps.citizen.messageguard import FAMILY_WEIGHTS
    for record in records:
        check(record["label"] in ("scam", "benign"), f"bad label: {record['id']}")
        check(set(record.get("families", [])) <= set(FAMILY_WEIGHTS),
              f"unknown family label: {record['id']}")
    for path in ROOT.rglob("*.jsonl"):
        parts = path.relative_to(ROOT).parts
        if ".git" in parts or "archive" in parts:
            continue
        is_messageguard_corpus = (
            path.parent.name in ("messageguard", "corpus")
            or path.name.startswith(("scam_", "benign_"))
        )
        if not is_messageguard_corpus:
            continue
        check(path.resolve().parent == ACTIVE_CORPUS.resolve(),
              f"second active MessageGuard corpus file: {path}")


def check_eval_single_source() -> None:
    runner = load_module("phase9_messageguard", RUNNER)
    generator = load_module("phase9_gen_evals_md", GENERATOR)
    committed = json.loads(RESULTS.read_text(encoding="utf-8"))
    full = json.loads(FULL_RESULTS.read_text(encoding="utf-8"))
    check(runner.compute_results() == committed,
          "MessageGuard results.json is stale relative to the one scorer and one corpus")
    check(committed.get("condition", "").startswith("hand-authored / in-distribution"),
          "results.json lacks explicit hand-authored / in-distribution scope")
    check("UNMEASURED" in committed.get("condition", ""),
          "results.json lacks real-world UNMEASURED statement")
    current = GENERATED.read_text(encoding="utf-8")
    pointer = POINTER.read_text(encoding="utf-8")
    check(generator.render(full) == current,
          "generated EVALS.md is stale; rerun make eval-generate")
    check(generator.render_pointer(full) == pointer,
          "generated MessageGuard pointer is stale; rerun make eval-generate")
    for needle in ("hand-authored / in-distribution", "UNMEASURED", "Hinglish",
                   "one corpus", "one generated eval document", "538"):
        check(needle in current, f"generated EVALS.md misses: {needle}")
        check(needle in pointer, f"generated MessageGuard pointer misses: {needle}")
    check("96.5%" not in current and "11.7%" not in current,
          "generated document contains stale pre-Phase-5 headline numbers")
    active_evals = [p for p in ROOT.rglob("EVALS.md")
                    if "archive" not in p.relative_to(ROOT).parts]
    check(active_evals == [GENERATED], "more than one active EVALS.md")
    active_pointers = [p for p in ROOT.rglob("MESSAGEGUARD_EVALS.md")
                       if "archive" not in p.relative_to(ROOT).parts]
    check(active_pointers == [POINTER],
          "more than one active generated MessageGuard pointer")
    proc = subprocess.run(
        [sys.executable, str(LEGACY_RUNNER), "--check"], cwd=LEGACY_ROOT, env=env(),
        capture_output=True, text=True,
    )
    check(proc.returncode == 0 and "OK" in proc.stdout,
          f"MessageGuard compatibility --check failed: {proc.stdout}{proc.stderr}")
    import apps.citizen.messageguard as mg
    report = mg.evaluate_fixtures(ACTIVE_CORPUS)
    check(report["total"] == 538, "evaluate_fixtures total is not 538")
    expected_pass = committed["overall"]["tp_moderate"] + committed["overall"]["tn_moderate"]
    check(report["passed"] == expected_pass,
          f"evaluate_fixtures passed {report['passed']}, expected {expected_pass}")


def check_cli_and_adapter() -> None:
    import apps.citizen.messageguard as mg
    result = mg.score_message("Aapka OTP batao warna account band ho jayega", lang="hinglish")
    check(result["detector_lang"] == "hinglish", "explicit Hinglish mode not accepted")
    check(result["verdict"] in ("HIGH", "CRITICAL"), "Hinglish scam not detected")
    for mode in ("band", "clamp"):
        value = mg.legacy_confidence(result, mode=mode)
        check(0.25 <= value <= 0.99, f"legacy confidence out of band in {mode} mode")
    payload = mg.to_legacy_organ_payload(result).to_dict()
    check(payload["organ"] == "messageguard", "legacy organ name wrong")
    check(payload["band"] == result["verdict"], "legacy organ band is not authoritative verdict")
    check(payload["reason_codes"], "legacy organ payload has no reason codes")
    check("score" not in payload and "matched" not in payload,
          "legacy organ payload leaks raw score or matched phrases")

    text = "Aapka OTP batao warna account band ho jayega"
    proc = subprocess.run(
        [sys.executable, "-m", "apps.citizen.messageguard", "--lang", "hinglish",
         "--json", "--legacy", "--citizen-lang", "hi", text],
        cwd=ROOT, env=env(), capture_output=True, text=True,
    )
    check(proc.returncode == 0, f"CLI failed: {proc.stdout}{proc.stderr}")
    data = json.loads(proc.stdout)
    blob = json.dumps(data, ensure_ascii=False).lower()
    check("score" not in blob, "CLI JSON leaks a raw score")
    check("hits" not in data and "reason_details" not in data,
          "CLI JSON leaks diagnostic hits/reason details")
    check("matched" not in blob, "CLI JSON leaks matched scam phrases")
    check("SAFE" not in json.dumps(data), "CLI emits a SAFE verdict")
    check(data["detector_lang"] == "hinglish", "CLI detector language wrong")
    check(data["citizen"]["lang"] == "hi", "CLI citizen copy language wrong")
    check(data["citizen"]["helpline"] == "1930", "CLI helpline missing")
    check(0.25 <= data["legacy_organ"]["confidence"] <= 0.99,
          "CLI legacy confidence out of band")
    plain = subprocess.run(
        [sys.executable, "-m", "apps.citizen.messageguard", text],
        cwd=ROOT, env=env(), capture_output=True, text=True,
    )
    check(plain.returncode == 0, f"default CLI failed: {plain.stdout}{plain.stderr}")
    check("score" not in plain.stdout.lower(), "default CLI prints a raw score")
    check("1930" in plain.stdout, "default CLI omits 1930 helpline")
    check("SAFE" not in plain.stdout, "default CLI emits a SAFE verdict")
    check(text not in plain.stdout, "default CLI echoes the full message text")
    auto = subprocess.run(
        [sys.executable, "-m", "apps.citizen.messageguard", "--json", text],
        cwd=ROOT, env=env(), capture_output=True, text=True,
    )
    check(auto.returncode == 0, f"auto CLI failed: {auto.stdout}{auto.stderr}")
    check(json.loads(auto.stdout)["detector_lang"] == "hinglish",
          "auto CLI did not detect Hinglish")


def check_provenance_and_runner() -> None:
    for rel in (
        "archive/provenance/README.md",
        "archive/provenance/conftest.py",
        "archive/provenance/messageguard-alternative/PROVENANCE.md",
        "archive/provenance/messageguard-snapshot/PROVENANCE.md",
        "raksha/PHASE5_MESSAGEGUARD_SINGLE_SOURCE.md",
        "raksha/adr/ADR-013-messageguard-single-source.md",
        "tests/test_phase5_messageguard.py",
        "raksha-code/tests/test_phase5_messageguard_compat.py",
        "tools/check_local_links.py",
    ):
        check((ROOT / rel).is_file(), f"missing Phase 5 deliverable: {rel}")
    conftest = (ARCHIVE / "conftest.py").read_text(encoding="utf-8")
    for rel in PROVENANCE_DIRS:
        archive_rel = rel.replace("archive/provenance/", "")
        check(archive_rel in conftest,
              f"provenance conftest does not mention {archive_rel}")
    runner = load_module("phase5_no_ai_runner", ROOT / "tools" / "run_phase4_pytest.py")
    check(tuple(runner.PROVENANCE_IGNORE_DIRS) == PROVENANCE_DIRS,
          "no-AI runner does not ignore both provenance test directories")
    check(len(runner.NO_AI_TEST_FILES) == 22,
          "Phase 4 no-AI skip list changed unexpectedly")
    check(len(runner.NO_AI_NODE_TESTS) == 3,
          "Phase 4 Node test list changed unexpectedly")
    with contextlib.redirect_stdout(io.StringIO()):
        link_status = link_checker.main(["--root", str(ROOT)])
    check(link_status == 0, "tools/check_local_links.py found a broken local link")


def run() -> int:
    check_import_boundary()
    normalize = check_public_interface_and_catalogue()
    check_one_corpus(normalize)
    check_eval_single_source()
    check_cli_and_adapter()
    check_provenance_and_runner()
    check(not loaded_forbidden_modules(),
          f"AI/voice model modules loaded during Phase 5 checker: {loaded_forbidden_modules()}")
    print("OK: Phase 5 MessageGuard is single-source; no AI model invoked.")
    return 0


def main() -> int:
    try:
        return run()
    except Exception as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
