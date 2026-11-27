"""CLI smoke tests."""

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def _run_cli(args, expect_code=0):
    return subprocess.run(
        [sys.executable, "-m", "raksha.messageguard", *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=60,
    )


def test_cli_flags_scam():
    r = _run_cli(["Your KYC expires today, update at bit.ly/kyc9 or account will be blocked"])
    assert r.returncode == 0
    assert "HIGH" in r.stdout or "CRITICAL" in r.stdout


def test_cli_citizen_output_localized():
    r = _run_cli(["--lang", "hi", "Share the OTP, else account will be blocked"])
    assert r.returncode == 0
    assert "Citizen (hi)" in r.stdout


def test_cli_json_mode():
    r = _run_cli(["--json", "You have won the lucky draw, send the processing fee"])
    assert r.returncode == 0
    data = json.loads(r.stdout)
    assert data["band"] in ("HIGH", "CRITICAL")
    assert data["reasons"]


def test_cli_legacy_mode_in_band():
    r = _run_cli(["--legacy", "--json", "CBI officer: digital arrest, transfer bail money now"])
    assert r.returncode == 0
    # --json prints the verdict JSON only; legacy payload follows after marker
    assert "legacy organ RPC payload" in r.stdout


def test_cli_harmless_message_is_low():
    r = _run_cli(["Your EMI of Rs.14,200 is due on 01-12-26. Pay on time."])
    assert r.returncode == 0
    assert "LOW" in r.stdout
