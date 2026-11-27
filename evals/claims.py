#!/usr/bin/env python3
"""Phase 9 — one claims ledger and one measurement-claim verifier.

Every measured number in ``EVALS.md`` resolves to a numeric leaf in
``evals/results.json`` with a fixture / synthetic / sandbox / hand-authored
condition. Every number in the outward-facing static docs must have an explicit
row in ``evals/claims_sources.json`` before it can appear in a README, status
page or changelog. Real-world accuracy, latency and uptime remain UNMEASURED.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys
from typing import Any, Iterator

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

EVALS_PATH = ROOT / "EVALS.md"
RESULTS_PATH = ROOT / "evals" / "results.json"
SOURCES_PATH = ROOT / "evals" / "claims_sources.json"
LEDGER_PATH = ROOT / "evals" / "claims_ledger.json"
RUNNER_PATH = ROOT / "evals" / "run_evals.py"
STATIC_DOCS = (
    "summary.md",
    "README.md",
    "docs/STATUS.md",
    "docs/README.md",
    "CHANGELOG.md",
    "raksha/README.md",
    "raksha/PHASE910_UNIFIED_RELEASE.md",
    "raksha/MESSAGEGUARD_EVALS.md",
)
ALLOWED_CONDITIONS = (
    "fixture", "synthetic", "sandbox", "hand-authored", "real-world UNMEASURED",
)
LINK_RE = re.compile(r"!?\[[^\]]*\]\([^)]*\)")
FENCE_RE = re.compile(r"```.*?```", re.S)
COMMENT_RE = re.compile(r"<!--.*?-->", re.S)
NUM_RE = re.compile(r"(?<![A-Za-z0-9_])(?:\d+(?:[.,:/-]\d+)*%?)(?![A-Za-z0-9_])")
FORBIDDEN_CLAIMS = (
    re.compile(r"field\s+FPR", re.I),
    re.compile(r"production\s+SLA", re.I),
    re.compile(r"guaranteed\s+uptime", re.I),
    re.compile(r"real[- ]network\s+detection", re.I),
    re.compile(r"real[- ]speech\s+accuracy", re.I),
)


def _strip_noise(text: str) -> str:
    text = COMMENT_RE.sub(" ", text)
    text = FENCE_RE.sub(" ", text)
    return LINK_RE.sub(lambda match: re.sub(r"\([^)]*\)", "()", match.group(0)), text)


def numeric_tokens(text: str) -> list[str]:
    return NUM_RE.findall(_strip_noise(text))


def _walk_numbers(obj: Any, pointer: str = "") -> Iterator[tuple[str, int | float]]:
    if isinstance(obj, dict):
        for key, value in obj.items():
            yield from _walk_numbers(value, f"{pointer}/{key}")
    elif isinstance(obj, list):
        for index, value in enumerate(obj):
            yield from _walk_numbers(value, f"{pointer}/{index}")
    elif isinstance(obj, bool):
        return
    elif isinstance(obj, (int, float)):
        yield pointer, obj


def _condition_for(pointer: str) -> str:
    if pointer.startswith("/sections/citizen"):
        return "fixture / sandbox"
    if pointer.startswith("/sections/messageguard"):
        return "hand-authored / in-distribution; real-world UNMEASURED"
    if pointer.startswith("/sections/organs"):
        return "synthetic / sandbox"
    if pointer.startswith("/sections/governance"):
        return "sandbox"
    if pointer.startswith("/sections/replay"):
        return "sandbox"
    return "hand-authored"


def _variants(value: int | float) -> list[str]:
    out = {str(value)}
    if isinstance(value, float):
        out.update({
            f"{value:.1%}", f"{value:.2%}", f"{value * 100:.1f}%",
            f"{value:.4f}", str(round(value, 4)),
        })
    return sorted(out)


def _resolve_pointer(results: dict[str, Any], pointer: str) -> Any:
    node: Any = results
    for part in pointer.lstrip("/").split("/"):
        if not part:
            continue
        if isinstance(node, dict):
            node = node[part]
        elif isinstance(node, list):
            node = node[int(part)]
        else:
            raise KeyError(pointer)
    return node


def build_ledger(results: dict[str, Any], sources: dict[str, Any]) -> dict[str, Any]:
    # Canonicalise key order before walking: generation receives an in-memory
    # dict while verification receives sort_keys JSON from disk. Both must yield
    # the same deterministic measurement-row order.
    results = json.loads(json.dumps(results, sort_keys=True))
    static_rows = [dict(row, kind="documentation") for row in sources["rows"]]
    measurement_rows: list[dict[str, Any]] = []
    for index, (pointer, value) in enumerate(_walk_numbers(results), start=1):
        condition = _condition_for(pointer)
        for variant_index, variant in enumerate(_variants(value), start=1):
            measurement_rows.append({
                "claim_id": f"MEAS-{index:04d}-{variant_index}",
                "value": variant,
                "condition": condition,
                "source": f"evals/results.json#{pointer}",
                "used_in": ["EVALS.md"],
                "kind": "measurement",
            })
    return {
        "contract": "raksha-claims-ledger-v1",
        "generated_by": "evals/claims.py",
        "allowed_conditions": list(ALLOWED_CONDITIONS),
        "real_world_claims": "UNMEASURED",
        "voiceguard_evals_included": False,
        "rows": static_rows + measurement_rows,
    }


def _check_real_world_sentences(text: str, label: str) -> None:
    for sentence in re.split(r"(?<=[.!?])\s+", text):
        lowered = sentence.lower()
        if "real-world" in lowered or "real world" in lowered:
            measured = re.search(r"accuracy|latency|uptime|fpr|recall|false-positive", lowered)
            negative_claim = (
                re.search(r"\bno real[- ]world\b", lowered)
                and re.search(r"claim|action", lowered)
            )
            if measured and "UNMEASURED" not in sentence and not negative_claim:
                raise RuntimeError(f"{label} contains a real-world measured claim without UNMEASURED")
    for pattern in FORBIDDEN_CLAIMS:
        for match in pattern.finditer(text):
            start = text.rfind(".", 0, match.start()) + 1
            end = text.find(".", match.end())
            context = text[start: end + 1 if end != -1 else len(text)]
            lowered = context.lower()
            allowed = (
                "UNMEASURED" in context
                or (re.search(r"\bno\b", lowered)
                    and re.search(r"claim|action|introduced", lowered))
            )
            if not allowed:
                raise RuntimeError(f"{label} contains a forbidden field claim: {pattern.pattern}")


def verify() -> None:
    results = json.loads(RESULTS_PATH.read_text(encoding="utf-8"))
    sources = json.loads(SOURCES_PATH.read_text(encoding="utf-8"))
    committed = json.loads(LEDGER_PATH.read_text(encoding="utf-8"))
    expected = build_ledger(results, sources)
    if committed != expected:
        raise RuntimeError("evals/claims_ledger.json is stale; rerun make eval")

    static_values: dict[str, set[str]] = {doc: set() for doc in STATIC_DOCS}
    for row in sources["rows"]:
        if not all(key in row for key in ("claim_id", "value", "condition", "source", "used_in")):
            raise RuntimeError(f"incomplete claims source row: {row}")
        if not any(label in row["condition"] for label in ALLOWED_CONDITIONS):
            raise RuntimeError(f"claims source row lacks an allowed condition: {row['claim_id']}")
        source = row["source"]
        if source.startswith("evals/results.json#"):
            _resolve_pointer(results, source.split("#", 1)[1])
        elif source != "repository structure" and not (ROOT / source).exists():
            raise RuntimeError(f"claims source path does not exist: {source}")
        for doc in row["used_in"]:
            if doc in static_values:
                static_values[doc].add(str(row["value"]))

    all_docs = list(STATIC_DOCS) + ["EVALS.md"]
    measurement_values = {
        str(row["value"]) for row in committed["rows"] if row.get("kind") == "measurement"
    }
    for rel in all_docs:
        path = ROOT / rel
        if not path.exists():
            raise RuntimeError(f"missing claims-covered document: {rel}")
        text = path.read_text(encoding="utf-8")
        _check_real_world_sentences(text, rel)
        tokens = numeric_tokens(text)
        if rel == "EVALS.md":
            missing = sorted(set(tokens) - measurement_values)
            if missing:
                raise RuntimeError(f"EVALS.md numbers without a measurement ledger row: {missing}")
        else:
            missing = sorted(set(tokens) - static_values[rel])
            if missing:
                raise RuntimeError(f"{rel} numbers without a claims source row: {missing}")

    if results["measurement_policy"]["real_world"] != "UNMEASURED":
        raise RuntimeError("measurement policy does not mark real-world claims UNMEASURED")
    if results["voiceguard"]["included_in_runner"] is not False:
        raise RuntimeError("VoiceGuard evals must stay out of the Phase 9 runner")
    if results["voiceguard"]["future_phase"] != "Eleven":
        raise RuntimeError("VoiceGuard re-entry must be future Phase Eleven")
    if "run_maya" in RUNNER_PATH.read_text(encoding="utf-8"):
        raise RuntimeError("unified runner must not import frozen MAYA evals")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help=argparse.SUPPRESS)
    parser.parse_args(argv)
    try:
        verify()
    except Exception as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    print("OK: claims ledger verifies; every outward number has a conditioned source row")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
