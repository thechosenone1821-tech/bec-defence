"""One-action start and stop: the launcher scripts and the engine they share.

These tests keep ``start.sh`` / ``start.bat`` / ``stop.sh`` / ``stop.bat`` honest
without booting servers: the files must be usable, must delegate every decision
to :mod:`tools.launch_apps`, must advertise only flags that exist, must not drag
a model run or an eval pass into start-up, and the launcher's own state handling
(idempotent start, refusal to signal a recycled pid) must behave. The real
two-process start is exercised by ``tools/run_frontend_smoke.py`` and the
``--check`` preflight runs as a CI step.
"""
from __future__ import annotations

import json
import os
import pathlib
import re
import subprocess
import sys

import pytest

from tools import launch_apps

ROOT = pathlib.Path(__file__).resolve().parents[1]
SH = ("start.sh", "stop.sh")
BAT = ("start.bat", "stop.bat")
#: anything that would turn "start the app" into "start a model or a test run"
NOT_A_STARTUP_COMMAND = ("run_vigil", "run_evals", "make eval", "pytest", "npm run",
                         "uvicorn", "-m apps.", "--reload")


def _read(name: str) -> str:
    return (ROOT / name).read_text(encoding="utf-8")


def test_all_four_scripts_exist_and_are_launchable() -> None:
    for name in SH + BAT:
        assert (ROOT / name).is_file(), name
    for name in SH:
        data = (ROOT / name).read_bytes()
        assert os.access(ROOT / name, os.X_OK), f"{name} must be executable"
        assert data.startswith(b"#!/usr/bin/env bash"), name
        assert b"\r" not in data, f"{name} must stay LF-only"
    for name in BAT:
        data = (ROOT / name).read_bytes()
        assert data.decode().splitlines()[0] == "@echo off", name
        assert data.count(b"\r\n") >= 10, f"{name} needs CRLF line endings for cmd.exe"


def test_scripts_delegate_every_rule_to_the_launcher() -> None:
    for text in (_read(name) for name in SH + BAT):
        assert "launch_apps.py" in text or "launch_apps.py" in text.replace("\\", "/"), text[:40]
        for banned in NOT_A_STARTUP_COMMAND:
            assert banned not in text, f"scripts must not run {banned!r}"
    assert "--detach" in _read("start.sh") and "--detach" in _read("start.bat")
    assert "--stop" in _read("stop.sh") and "--stop" in _read("stop.bat")
    # no second implementation of readiness or cleanup in the shell layer
    for name in SH + BAT:
        assert "curl" not in _read(name) and "taskkill" not in _read(name), name


@pytest.mark.parametrize("name", SH + BAT)
def test_scripts_never_invent_a_flag_or_a_target(name: str) -> None:
    text = _read(name)
    help_text = subprocess.run([sys.executable, "tools/launch_apps.py", "--help"],
                               capture_output=True, text=True, cwd=ROOT, check=True).stdout
    known = set(re.findall(r"--[a-z][a-z-]+", help_text))
    for flag in set(re.findall(r"(?<![\w-])(--[a-z][a-z-]+)", text)):
        assert flag in known, f"{name} advertises an unknown flag {flag}"
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    for target in set(re.findall(r"make ([a-z-]+)", text)):
        assert f"\n{target}:" in makefile, f"{name} tells the user to run an unknown target {target}"


def test_launcher_wired_into_the_make_surface() -> None:
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    for target in ("start:", "stop:", "status:", "restart:", "run:"):
        assert f"\n{target}" in makefile, target
    assert "./start.sh" in makefile and "./stop.sh" in makefile


def test_printed_urls_match_both_boot_manifests() -> None:
    apps = launch_apps._apps()
    assert [name for name, _module, _port in apps] == ["infra", "citizen"]
    for name, _module, _port in apps:
        manifest = json.loads((ROOT / "apps" / name / "BOOT_MANIFEST.json").read_text(encoding="utf-8"))
        assert launch_apps.CONSOLE_ROUTES[name] == manifest["root_redirect"], name
        assert launch_apps.FRONTEND_HEALTH_PATH == manifest["frontend_health_path"], name
    rows = launch_apps._urls(apps)
    console_rows = [row for row in rows if row[0].startswith("RAKSHA ")]
    assert len(console_rows) == 2, "one console URL per interface, no more"
    for _label, url in rows:
        assert url.startswith("http://127.0.0.1:"), url


def test_optional_env_file_fills_gaps_without_overriding_the_operator(tmp_path) -> None:
    config = tmp_path / "env"
    config.write_text(
        "# launcher config\n\nexport RAKSHA_INFRA_PORT=8199\n"
        'RAKSHA_SENSOR_KEY="from-file"\nRAKSHA_CITIZEN_PORT = 8200\n',
        encoding="utf-8",
    )
    saved = {key: os.environ.get(key) for key in
             ("RAKSHA_INFRA_PORT", "RAKSHA_SENSOR_KEY", "RAKSHA_CITIZEN_PORT")}
    os.environ["RAKSHA_INFRA_PORT"] = "8100"
    os.environ.pop("RAKSHA_SENSOR_KEY", None)
    os.environ.pop("RAKSHA_CITIZEN_PORT", None)
    try:
        assert launch_apps._load_env_file(config) == 2
        assert os.environ["RAKSHA_INFRA_PORT"] == "8100", "a real env value must win"
        assert os.environ["RAKSHA_SENSOR_KEY"] == "from-file"
        assert os.environ["RAKSHA_CITIZEN_PORT"] == "8200"
        assert launch_apps._load_env_file(tmp_path / "missing") == 0
    finally:
        for key, value in saved.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def test_stop_refuses_a_recycled_pid_and_leaves_this_process_alone(tmp_path) -> None:
    state = tmp_path / "launcher.json"
    state.write_text(json.dumps({"apps": {"infra": {"pid": os.getpid(), "port": 8090,
                                                    "module": "apps.infra"}}}),
                     encoding="utf-8")
    assert launch_apps.cmd_stop(tmp_path) == 1, "a pid that no longer runs the app must not be killed"
    assert not state.exists(), "the stale record is dropped either way"
    assert launch_apps.cmd_stop(tmp_path) == 0, "a second stop is a no-op"


def test_status_reports_an_unrecorded_stack_without_claiming_it(tmp_path) -> None:
    assert launch_apps.cmd_status(tmp_path) == 1, "no state file must not read as healthy"


def test_start_never_turns_a_model_on_by_itself() -> None:
    saved = os.environ.pop("EIGENSHIELD_MODEL", None)
    try:
        env = launch_apps._spawn_env(launch_apps._apps())
    finally:
        if saved is not None:
            os.environ["EIGENSHIELD_MODEL"] = saved
    assert env["EIGENSHIELD_MODEL"] == "disabled"
    assert env["RAKSHA_INFRA_INTERNAL_URL"].endswith(str(launch_apps._apps()[0][2]))
    assert env["RAKSHA_CITIZEN_INTERNAL_URL"].endswith(str(launch_apps._apps()[1][2]))
    assert env["RAKSHA_BUS_URL"] == env["RAKSHA_INFRA_INTERNAL_URL"]


def test_preflight_runs_cleanly_from_the_command_line() -> None:
    res = subprocess.run([sys.executable, "tools/launch_apps.py", "--check"],
                         capture_output=True, text=True, cwd=ROOT, timeout=240, check=False)
    combined = res.stdout + res.stderr
    assert "Traceback" not in combined, combined[-800:]
    assert res.returncode in (0, 1), combined[-400:]
    for expected in ("interpreter", "dependencies", "credentials", "model policy",
                     "database      none required", "services      none required"):
        assert expected in res.stdout, expected
    assert "demo default" in res.stdout or "set" in res.stdout
    for secret in (os.environ.get("RAKSHA_SENSOR_KEY", "raksha-phase678-dev-sensor-key"),
                   os.environ.get("RAKSHA_OBSERVER_TOKEN", "demo-observer-token")):
        assert secret not in combined, "preflight must report credentials by name only"
    if res.returncode != 0:
        assert "PROBLEM" in res.stderr
