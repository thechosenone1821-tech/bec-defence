#!/usr/bin/env python3
"""One process launcher for exactly two RAKSHA apps.

The Infra/SOC console and the Citizen app are started as separate uvicorn
processes. Both app entrypoints bind all interfaces for the Arena preview.
This launcher adds no third app, no Commander endpoint, no live executor
and no real containment action. VIGIL runs inside the Citizen process.

Port overrides are read from ``RAKSHA_INFRA_PORT`` and ``RAKSHA_CITIZEN_PORT``
so a fresh preview mapping can be used without editing either boot manifest.

Modes
-----
``launch_apps.py``              attached foreground run; Ctrl+C stops both apps
``launch_apps.py --check``      preflight only: interpreter, imports, config, ports
``launch_apps.py --detach``     start in the background, wait until both apps are
                                ready, print the URLs and record the process ids
``launch_apps.py --status``     report the recorded stack and probe both origins
``launch_apps.py --stop``       stop only the processes this launcher recorded
``launch_apps.py --restart``    stop, then start detached again

``start.sh`` / ``stop.sh`` and ``start.bat`` / ``stop.bat`` are thin wrappers
around ``--detach`` and ``--stop``, so Windows and POSIX systems share one code
path instead of two implementations of the same startup rules.

What this launcher deliberately never does
-----------------------------------------
* it starts no database and no broker: the audit ledger is an in-process
  append-only chain and the console gateway is a module inside each app;
* it executes no model at all: no VIGIL batch, no eval run, no Commander call, and
  Infra's optional model stays ``EIGENSHIELD_MODEL=disabled`` unless the
  operator already set it;
* it never prints a credential: tokens are read from the environment (or the
  git-ignored ``.raksha/env`` file) and are reported by name only;
* it does not kill what it did not start: ``--stop`` verifies that a recorded
  pid still runs the expected module on the expected port, and refuses when a
  pid has clearly been recycled by another program.
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.request
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parents[1]
INFRA_MANIFEST = ROOT / "apps" / "infra" / "BOOT_MANIFEST.json"
CITIZEN_MANIFEST = ROOT / "apps" / "citizen" / "BOOT_MANIFEST.json"
STATE_NAME = "launcher.json"
DEFAULT_STATE_DIR = ROOT / ".raksha"
DEFAULT_ENV_FILE = "env"
MIN_PYTHON = (3, 11)
READY_TIMEOUT_SECONDS = 120.0
STOP_GRACE_SECONDS = 10.0

#: the console route each app redirects ``/`` to, mirrored from the boot manifests
CONSOLE_ROUTES = {"infra": "/console/rings", "citizen": "/console/call-screen"}
FRONTEND_HEALTH_PATH = "/api/frontend/health"
#: modules the two apps import at start-up, paired with the requirement shipping them
REQUIRED_MODULES = (
    ("fastapi", "fastapi"),
    ("starlette", "starlette"),
    ("uvicorn", "uvicorn"),
    ("httpx", "httpx"),
    ("pydantic", "pydantic"),
    ("multipart", "python-multipart"),
    ("yaml", "PyYAML"),
    ("numpy", "numpy"),
    ("scipy", "scipy"),
    ("networkx", "networkx"),
    ("cv2", "opencv-python-headless"),
    ("torch", "torch"),
    ("torchvision", "torchvision"),
)
#: environment the two apps and the shared console gateway read
PORT_VARS = {"infra": "RAKSHA_INFRA_PORT", "citizen": "RAKSHA_CITIZEN_PORT"}
URL_VARS = ("RAKSHA_INFRA_INTERNAL_URL", "RAKSHA_CITIZEN_INTERNAL_URL", "RAKSHA_BUS_URL")
TOKEN_VARS = ("RAKSHA_OBSERVER_TOKEN", "RAKSHA_SENSOR_TOKEN", "RAKSHA_ADMIN_TOKEN",
              "RAKSHA_SENSOR_KEY", "RAKSHA_FRONTEND_READ_TOKEN", "RAKSHA_FRONTEND_SENSOR_TOKEN")


class LaunchError(RuntimeError):
    """A startup or shutdown problem that already knows how to explain itself."""


def _psutil():
    try:
        import psutil  # declared in requirements.txt

        return psutil
    except ImportError:
        return None


def _port(path: pathlib.Path) -> int:
    return int(json.loads(path.read_text(encoding="utf-8"))["default_port"])


def _env_port(name: str, path: pathlib.Path) -> int:
    raw = os.environ.get(name, "").strip()
    return int(raw) if raw else _port(path)


def _apps() -> tuple[tuple[str, str, int], ...]:
    return (
        ("infra", "apps.infra", _env_port("RAKSHA_INFRA_PORT", INFRA_MANIFEST)),
        ("citizen", "apps.citizen", _env_port("RAKSHA_CITIZEN_PORT", CITIZEN_MANIFEST)),
    )


def _relative(path: pathlib.Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def _load_env_file(path: pathlib.Path) -> int:
    """Apply ``KEY=VALUE`` lines that are not already in the environment.

    The repository's secrets gate rejects any file named ``.env``, so the
    optional launcher config file lives in the git-ignored run directory.
    """
    if not path.is_file():
        return 0
    applied = 0
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip().removeprefix("export ").strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value
            applied += 1
    return applied


def _spawn_env(apps: tuple[tuple[str, str, int], ...]) -> dict[str, str]:
    """The environment both children start with, defaults included."""
    env = dict(os.environ)
    env["PYTHONUNBUFFERED"] = "1"
    env["RAKSHA_INFRA_PORT"] = str(apps[0][2])
    env["RAKSHA_CITIZEN_PORT"] = str(apps[1][2])
    env.setdefault("RAKSHA_INFRA_INTERNAL_URL", f"http://127.0.0.1:{apps[0][2]}")
    env.setdefault("RAKSHA_CITIZEN_INTERNAL_URL", f"http://127.0.0.1:{apps[1][2]}")
    env.setdefault("RAKSHA_FRONTEND_READ_TOKEN",
                   os.environ.get("RAKSHA_OBSERVER_TOKEN", "demo-observer-token"))
    env.setdefault("RAKSHA_FRONTEND_SENSOR_TOKEN",
                   os.environ.get("RAKSHA_SENSOR_TOKEN", "demo-sensor-token"))
    env.setdefault("RAKSHA_SENSOR_KEY", "raksha-phase678-dev-sensor-key")
    # the Citizen app forwards signed reports into the shared runtime, which
    # needs the ingest URL and the scoped token the runtime accepts
    env.setdefault("RAKSHA_BUS_URL", f"http://127.0.0.1:{apps[0][2]}")
    env.setdefault("RAKSHA_SENSOR_TOKEN", os.environ.get("RAKSHA_SENSOR_TOKEN", "demo-sensor-token"))
    # the deterministic runtime stays deterministic: the launcher never turns a
    # model on by itself, an operator has to ask for one per app
    env.setdefault("EIGENSHIELD_MODEL", "disabled")
    env["PYTHONPATH"] = os.pathsep.join(
        [str(ROOT), str(ROOT / "raksha-code"), env.get("PYTHONPATH", "")]
    ).rstrip(os.pathsep)
    return env


def _app_command(module: str, port: int) -> list[str]:
    return [sys.executable, "-m", module, "--port", str(port)]


def _spawn(module: str, port: int, env: dict[str, str],
           log: pathlib.Path) -> subprocess.Popen[Any]:
    """Start one app detached, with its own log and process group."""
    handle = log.open("ab")
    kwargs: dict[str, Any] = {"cwd": ROOT, "env": env, "stdout": handle,
                              "stderr": subprocess.STDOUT, "stdin": subprocess.DEVNULL,
                              "start_new_session": True}
    if os.name == "nt":  # survive the closing of the start window
        kwargs["creationflags"] = (getattr(subprocess, "DETACHED_PROCESS", 0)
                                   | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0))
    try:
        return subprocess.Popen(_app_command(module, port), **kwargs)
    finally:
        handle.close()


def _health(port: int, timeout: float = 2.0) -> dict[str, Any] | None:
    """The app's own frontend health document, or None when nothing answers."""
    request = urllib.request.Request(f"http://127.0.0.1:{port}{FRONTEND_HEALTH_PATH}",
                                     headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            if response.status != 200:
                return None
            body = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, OSError, ValueError):
        return None
    return body if isinstance(body, dict) else None


def _pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    psutil = _psutil()
    if psutil is not None:
        return bool(psutil.pid_exists(pid))
    if os.name == "nt":
        probe = subprocess.run(["tasklist", "/nh", "/fo", "csv", "/fi", f"PID eq {pid}"],
                               capture_output=True, text=True, check=False)
        return str(pid) in (probe.stdout or "")
    try:
        os.kill(pid, 0)
    except (ProcessLookupError, PermissionError, OSError):
        return False
    return True


def _pid_command(pid: int) -> str:
    """Best-effort command line of a pid, used to refuse killing strangers."""
    psutil = _psutil()
    if psutil is not None:
        try:
            return " ".join(psutil.Process(pid).cmdline())
        except Exception:
            return ""
    try:
        return pathlib.Path(f"/proc/{pid}/cmdline").read_bytes().decode("utf-8", "replace").replace("\0", " ")
    except OSError:
        return ""


def _is_expected_process(pid: int, module: str, port: int) -> bool:
    command = _pid_command(pid)
    if not command:
        return False
    return f"-m {module}" in command and f"--port {port}" in command


def _stop_pid(pid: int, label: str, *, force_after: float = STOP_GRACE_SECONDS) -> str:
    """Stop one recorded process (and its children), escalating once."""
    if not _pid_alive(pid):
        return "already exited"
    psutil = _psutil()
    if psutil is not None:
        try:
            target = psutil.Process(pid)
            tree = [target] + target.children(recursive=True)
        except psutil.NoSuchProcess:
            return "already exited"
        for item in tree:
            try:
                item.terminate()
            except psutil.NoSuchProcess:
                pass
        _gone, alive = psutil.wait_procs(tree, timeout=force_after)
        for item in alive:
            try:
                item.kill()
            except psutil.NoSuchProcess:
                pass
        return "terminated" if not alive else "killed after the grace period"
    if os.name == "nt":
        # no psutil: taskkill only touches the tree rooted at our own pid
        subprocess.run(["taskkill", "/PID", str(pid), "/T"], check=False,
                       capture_output=True, text=True)
        deadline = time.time() + force_after
        while time.time() < deadline and _pid_alive(pid):
            time.sleep(0.2)
        if _pid_alive(pid):
            subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], check=False,
                           capture_output=True, text=True)
        return "terminated" if not _pid_alive(pid) else f"{label} ignored the stop request"
    for sig in (signal.SIGTERM, signal.SIGKILL):
        try:
            os.killpg(pid, sig)  # start_new_session made the pid its own group leader
        except (ProcessLookupError, PermissionError):
            try:
                os.kill(pid, sig)
            except (ProcessLookupError, PermissionError):
                return "already exited"
        deadline = time.time() + force_after
        while time.time() < deadline:
            if not _pid_alive(pid):
                return "terminated" if sig == signal.SIGTERM else "killed after the grace period"
            time.sleep(0.1)
    raise LaunchError(f"{label} (pid {pid}) survived SIGKILL — investigate manually")


def _state_path(state_dir: pathlib.Path) -> pathlib.Path:
    return state_dir / STATE_NAME


def _read_state(state_dir: pathlib.Path) -> dict[str, Any] | None:
    path = _state_path(state_dir)
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def _write_state(state_dir: pathlib.Path, payload: dict[str, Any]) -> None:
    _state_path(state_dir).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n",
                                       encoding="utf-8")


def _managed_live(state: dict[str, Any] | None,
                  apps: tuple[tuple[str, str, int], ...]) -> dict[str, dict[str, Any]]:
    """Recorded apps whose process is alive and answering on its own port.

    The probe uses the *recorded* port, so an operator who moved a port between
    runs neither reuses a process on the old socket nor treats it as a conflict.
    """
    recorded = (state or {}).get("apps", {})
    live: dict[str, dict[str, Any]] = {}
    for name, module, port in apps:
        entry = recorded.get(name) or {}
        port = int(entry.get("port", port) or port)
        pid = int(entry.get("pid", 0) or 0)
        if pid and _pid_alive(pid) and (_health(port) or {}).get("service") == name:
            if _pid_command(pid) and not _is_expected_process(pid, module, port):
                continue  # pid was recycled by another program: never reuse, never kill
            live[name] = dict(entry, pid=pid, port=port, module=module)
    return live


def _urls(apps: tuple[tuple[str, str, int], ...]) -> list[tuple[str, str]]:
    """Every entry point worth printing after a successful start."""
    rows: list[tuple[str, str]] = []
    for name, _module, port in apps:
        rows.append((f"RAKSHA {name} console", f"http://127.0.0.1:{port}{CONSOLE_ROUTES[name]}"))
    for name, _module, port in apps:
        rows.append((f"{name} frontend health", f"http://127.0.0.1:{port}{FRONTEND_HEALTH_PATH}"))
    infra_port = apps[0][2]
    citizen_port = apps[1][2]
    rows += [
        ("Infra status card", f"http://127.0.0.1:{infra_port}/api/infra/status"),
        ("Infra legacy console", f"http://127.0.0.1:{infra_port}/app/console"),
        ("Fake-hospital exercise", f"http://127.0.0.1:{infra_port}/demo/hospital"),
        ("Attack Lab (simulated)", f"http://127.0.0.1:{infra_port}/console/attack-lab"),
        ("Citizen VIGIL status", f"http://127.0.0.1:{citizen_port}/api/citizen/vigil/status"),
        ("Citizen legacy PWA", f"http://127.0.0.1:{citizen_port}/app/"),
    ]
    return rows


def _print_urls(apps: tuple[tuple[str, str, int], ...]) -> None:
    for label, url in _urls(apps):
        print(f"{label:26s} {url}", flush=True)


def _log_tail(log: pathlib.Path | None, lines: int = 25) -> str:
    if log is None or not log.is_file():
        return "  (no log file)"
    tail = log.read_text(encoding="utf-8", errors="replace").splitlines()[-lines:]
    return "\n".join(f"  {line}" for line in tail) or "  (log empty)"


def _check_python(problems: list[str]) -> list[str]:
    version = sys.version_info[:3]
    ok = version >= MIN_PYTHON
    wanted = ".".join(str(part) for part in MIN_PYTHON)
    found = ".".join(str(part) for part in version)
    if not ok:
        problems.append(f"python {wanted}+ is required, found {found} — use the repository "
                        "venv (`.venv/bin/python`, `.venv\\Scripts\\python.exe`)")
    return [f"{'interpreter  OK' if ok else 'interpreter  UNSUPPORTED'}: {found} at {sys.executable} "
            f"(needs {wanted}+)"]


def _check_modules(problems: list[str]) -> list[str]:
    import importlib.util

    missing = [requirement for module, requirement in REQUIRED_MODULES
               if importlib.util.find_spec(module) is None]
    if missing:
        problems.append("missing packages: " + ", ".join(missing)
                        + " — run `make install` (or `python -m pip install -r requirements.txt`)")
    present = len(REQUIRED_MODULES) - len(missing)
    note = f", missing {', '.join(missing)}" if missing else ""
    psutil = _psutil()
    return [f"dependencies {'OK' if not missing else 'INCOMPLETE'}: {present}/"
            f"{len(REQUIRED_MODULES)} importable{note}",
            f"process control {'OK' if psutil else 'FALLBACK'}: psutil "
            + ("verifies pids before signalling them" if psutil else
               "not importable — pid checks fall back to tasklist//proc and are weaker")]


def _check_frontend(problems: list[str]) -> list[str]:
    static = ROOT / "packages" / "frontend" / "static"
    if not (static / "index.html").is_file():
        problems.append("the static console build is missing — run `make frontend-build`")
        return ["frontend bundle MISSING: packages/frontend/static/index.html"]
    count = sum(1 for path in static.rglob("*") if path.is_file())
    return [f"frontend bundle OK: {count} files under packages/frontend/static"]


def _check_config(env: dict[str, str]) -> list[str]:
    port_note = "; ".join(f"{name}={env.get(variable, 'unset')}"
                         for name, variable in PORT_VARS.items())
    url_note = "; ".join(f"{name}={env.get(name, 'unset')}" for name in URL_VARS)
    states = ", ".join(f"{name}={'set' if os.environ.get(name, '').strip() else 'demo default'}"
                       for name in TOKEN_VARS)
    demo = [name for name in TOKEN_VARS if not os.environ.get(name, "").strip()]
    lines = [f"ports          {port_note}",
             f"internal urls   {url_note}",
             f"credentials    {states} (values are never printed)",
             f"model policy   EIGENSHIELD_MODEL={env.get('EIGENSHIELD_MODEL', 'disabled')}"
             " — no model run, no eval, no Commander by the launcher"]
    if demo:
        lines.append("credentials    NOTE: " + ", ".join(demo)
                     + " fall back to the packaged demo values — set them for any non-local deployment")
    return lines


def _check_ports(apps: tuple[tuple[str, str, int], ...],
                 managed: dict[str, Any] | None = None) -> tuple[list[str], list[str]]:
    """Display lines plus hard problems for the ports the launcher needs.

    A port held by this launcher's own recorded process is fine — that is the
    already-running case. Anything else on the port is a conflict, because a
    second app would fight it for the socket.
    """
    lines: list[str] = []
    problems: list[str] = []
    managed = managed or {}
    for name, _module, port in apps:
        info = _health(port)
        if info is None:
            lines.append(f"port {name:<8} free: {port}")
            continue
        if name in managed:
            lines.append(f"port {name:<8} in use by the recorded {name} process (pid "
                         f"{managed[name].get('pid')}); re-running start changes nothing")
            continue
        service = str(info.get("service", "")) or "an unknown service"
        lines.append(f"port {name:<8} occupied by {service} on {port}")
        problems.append(
            f"port {port} already answers for {name} but is not recorded in the launcher state; "
            f"a second app would fight it for the socket — stop that process, or point this stack "
            f"elsewhere with {PORT_VARS[name]}"
        )
    return lines, problems


def check(apps: tuple[tuple[str, str, int], ...],
          managed: dict[str, Any] | None = None) -> tuple[list[str], list[str]]:
    """Preflight everything a start would depend on."""
    problems: list[str] = []
    lines = _check_python(problems) + _check_modules(problems) + _check_frontend(problems)
    lines += _check_config(_spawn_env(apps))
    port_lines, port_problems = _check_ports(apps, managed)
    lines += port_lines
    problems += port_problems
    lines.append("database      none required: the audit ledger is an in-process append-only chain")
    lines.append("services      none required: the console gateway is a module inside each app")
    return lines, problems


def _wait_ready(apps: tuple[tuple[str, str, int], ...], processes: list[Any],
                logs: dict[str, pathlib.Path], timeout: float) -> None:
    """Block until both origins answer, or fail with the log that explains why."""
    pending = {name for name, _module, _port in apps}
    deadline = time.time() + timeout
    while pending:
        for index in range(len(apps)):
            name, _module, port = apps[index]
            if name not in pending:
                continue
            code = processes[index].poll()
            if code is not None:
                raise LaunchError(f"{name} exited with code {code} before it was ready:\n"
                                  + _log_tail(logs.get(name)))
            info = _health(port)
            if info and info.get("service") == name:
                pending.discard(name)
                print(f"{name:8s} ready on port {port}", flush=True)
            elif time.time() > deadline:
                hint = ("a cold start imports the model-backed Citizen stack, so raise "
                        f"--timeout (used {timeout:g}s)" if timeout < 20 else
                        f"raise --timeout (used {timeout:g}s)")
                if info:
                    raise LaunchError(f"{name} did not report ready on port {port} within "
                                      f"{timeout:g}s; health answered {json.dumps(info)[:180]} — {hint}")
                raise LaunchError(f"{name} did not answer on port {port} within {timeout:g}s — "
                                  f"{hint}\n" + _log_tail(logs.get(name)))
        if pending:
            time.sleep(0.25)


def cmd_check(state_dir: pathlib.Path) -> int:
    apps = _apps()
    lines, problems = check(apps, _managed_live(_read_state(state_dir), apps))
    for line in lines:
        print(line)
    for problem in problems:
        print(f"PROBLEM: {problem}", file=sys.stderr)
    if problems:
        print(f"FAIL: {len(problems)} startup problem(s)", file=sys.stderr)
        return 1
    print(f"OK: startup preflight passed — {len(lines)} checks, {len(apps)} apps, "
          "no database, no model run")
    return 0


def cmd_status(state_dir: pathlib.Path) -> int:
    apps = _apps()
    state = _read_state(state_dir)
    recorded = (state or {}).get("apps", {})
    problems: list[str] = []
    for name, module, port in apps:
        entry = recorded.get(name) or {}
        port = int(entry.get("port", port) or port)
        pid = int(entry.get("pid", 0) or 0)
        info = _health(port)
        managed = bool(pid) and _pid_alive(pid)
        answering = bool(info) and info.get("service") == name
        if answering and managed:
            command = _pid_command(pid)
            if command and not _is_expected_process(pid, module, port):
                print(f"{name:8s} SUSPECT: pid {pid} is alive but no longer runs "
                      f"`-m {module} --port {port}`")
                problems.append(f"{name} pid does not match")
                continue
            print(f"{name:8s} running pid={pid} port={port} console=http://127.0.0.1:{port}"
                  f"{CONSOLE_ROUTES[name]}")
            continue
        if answering:
            print(f"{name:8s} answering on port {port} but not recorded in "
                  f"{_relative(_state_path(state_dir))} — started outside these scripts")
            problems.append(f"{name} is unmanaged")
            continue
        detail = f" (recorded pid {pid} has exited)" if pid else ""
        print(f"{name:8s} stopped{detail}")
        problems.append(f"{name} is not running")
    for name, log in ((state or {}).get("logs") or {}).items():
        print(f"{name:8s} log  {log}")
    if problems:
        print(f"FAIL: {', '.join(problems)}", file=sys.stderr)
        return 1
    print("OK: both apps recorded by this launcher are answering")
    return 0


def cmd_stop(state_dir: pathlib.Path, *, verbose: bool = True) -> int:
    apps = _apps()
    state = _read_state(state_dir)
    recorded = (state or {}).get("apps", {})
    if not recorded:
        _lines, problems = _check_ports(apps)
        for problem in problems:
            print(f"NOTE: {problem}", file=sys.stderr)
        if verbose:
            print(f"OK: nothing to stop — no stack recorded in {_relative(_state_path(state_dir))}")
        return 0
    problems: list[str] = []
    for name, module, port in apps:
        entry = recorded.get(name) or {}
        pid = int(entry.get("pid", 0) or 0)
        if not pid:
            continue
        if not _pid_alive(pid):
            print(f"{name:8s} already exited (pid {pid})", flush=True)
            continue
        command = _pid_command(pid)
        if not command:
            print(f"{name:8s} NOTE: command line of pid {pid} is unreadable; signalling the "
                  "recorded pid only", flush=True)
        elif not _is_expected_process(pid, module, port):
            problems.append(f"{name}: refusing to signal pid {pid} — it now runs {command[:70]!r}, "
                            f"not `-m {module} --port {port}` (pid recycled?)")
            continue
        print(f"{name:8s} {_stop_pid(pid, name)} pid={pid}", flush=True)
    _state_path(state_dir).unlink(missing_ok=True)
    for problem in problems:
        print(f"PROBLEM: {problem}", file=sys.stderr)
    if problems:
        print(f"FAIL: {len(problems)} process(es) left untouched on purpose", file=sys.stderr)
        return 1
    return 0


def cmd_detach(state_dir: pathlib.Path, *, timeout: float, do_check: bool) -> int:
    apps = _apps()
    state = _read_state(state_dir)
    live = _managed_live(state, apps)
    if len(live) == len(apps):
        print("OK: the stack is already running — no duplicate processes started", flush=True)
        _print_urls(apps)
        print(f"      status: python {_relative(pathlib.Path(__file__).resolve())} --status")
        print("      stop:   ./stop.sh (or stop.bat)")
        return 0
    for name, module, port in apps:
        entry = ((state or {}).get("apps") or {}).get(name) or {}
        stale_pid = int(entry.get("pid", 0) or 0)
        if stale_pid and name not in live and _pid_alive(stale_pid):
            print(f"NOTE: the recorded {name} pid {stale_pid} is alive but not answering on port "
                  f"{entry.get('port', port)} — `--stop` will signal it; a deliberate port move "
                  f"needs that stop first", file=sys.stderr)
    if do_check:
        lines, problems = check(apps, live)
        if problems:
            for problem in problems:
                print(f"PROBLEM: {problem}", file=sys.stderr)
            print(f"FAIL: startup blocked by {len(problems)} problem(s); run the script with "
                  "--check for the full preflight", file=sys.stderr)
            return 1
        print(f"preflight OK ({len(lines)} checks)", flush=True)

    state_dir.mkdir(parents=True, exist_ok=True)
    log_dir = state_dir / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    env = _spawn_env(apps)
    logs: dict[str, pathlib.Path] = {}
    entries: dict[str, dict[str, Any]] = {}
    processes: list[Any] = []
    try:
        for name, module, port in apps:
            if name in live:
                entries[name] = dict(live[name], adopted=True)
                processes.append(_AdoptedProcess(int(live[name]["pid"])))
                print(f"{name:8s} reusing pid {live[name]['pid']}", flush=True)
                continue
            logs[name] = log_dir / f"{name}.log"
            logs[name].write_bytes(b"")  # a fresh log per start keeps failure tails useful
            process = _spawn(module, port, env, logs[name])
            processes.append(process)
            entries[name] = {"pid": process.pid, "port": port, "module": module,
                             "command": _app_command(module, port), "log": str(logs[name])}
            print(f"starting {name}: {' '.join(_app_command(module, port))} "
                  f"-> {_relative(logs[name])}", flush=True)
        _write_state(state_dir, {"contract": "raksha-launcher-state-v1",
                                 "started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                                 "python": sys.executable, "apps": entries,
                                 "logs": {name: str(path) for name, path in logs.items()},
                                 "console_urls": {name: f"http://127.0.0.1:{port}{CONSOLE_ROUTES[name]}"
                                                  for name, _module, port in apps}})
        _wait_ready(apps, processes, logs, timeout)
    except (LaunchError, OSError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        for (name, _module, _port), process in zip(apps, processes):
            if not isinstance(process, _AdoptedProcess) and process.poll() is None:
                _stop_pid(process.pid, name)
            logs.setdefault(name, log_dir / f"{name}.log")
        _state_path(state_dir).unlink(missing_ok=True)
        for name, _module, _port in apps:
            print(f"--- {name} log tail ---", file=sys.stderr)
            print(_log_tail(logs[name], 15), file=sys.stderr)
        return 1

    print("", flush=True)
    _print_urls(apps)
    print("", flush=True)
    print(f"state   {_relative(_state_path(state_dir))} (pids, ports, logs)", flush=True)
    print("stop    ./stop.sh (or stop.bat) — stops only these pids", flush=True)
    print("status  ./start.sh is safe to re-run; it reports the running stack instead of "
          "starting a second one", flush=True)
    print("models  none executed at startup: VIGIL stays idle until an image is submitted to "
          "the Citizen app", flush=True)
    return 0


class _AdoptedProcess:
    """Stand-in for a process this launcher reused rather than spawned."""

    def __init__(self, pid: int) -> None:
        self.pid = pid

    def poll(self) -> int | None:
        return None if _pid_alive(self.pid) else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Start, inspect and stop the two RAKSHA apps.")
    parser.add_argument("--detach", action="store_true",
                        help="start both apps in the background and return once they are ready")
    parser.add_argument("--check", action="store_true",
                        help="run the startup preflight and exit")
    parser.add_argument("--status", action="store_true", help="report the recorded stack")
    parser.add_argument("--stop", action="store_true", help="stop only the recorded processes")
    parser.add_argument("--restart", action="store_true", help="stop, then start detached again")
    parser.add_argument("--timeout", type=float, default=READY_TIMEOUT_SECONDS,
                        help=f"readiness budget in seconds (default {READY_TIMEOUT_SECONDS:.0f})")
    parser.add_argument("--state-dir", default=os.environ.get("RAKSHA_RUN_DIR", str(DEFAULT_STATE_DIR)),
                        help="run directory holding the state file and logs (default .raksha)")
    parser.add_argument("--env-file", default=DEFAULT_ENV_FILE,
                        help="optional KEY=VALUE file inside the run directory (default: env)")
    parser.add_argument("--no-check", action="store_true", help="skip the preflight before starting")
    args = parser.parse_args(argv)

    state_dir = pathlib.Path(args.state_dir).resolve()
    env_file = state_dir / args.env_file
    applied = _load_env_file(env_file)
    if applied:
        print(f"config  {applied} value(s) applied from {_relative(env_file)}", flush=True)

    if args.check:
        return cmd_check(state_dir)
    if args.status:
        return cmd_status(state_dir)
    if args.stop:
        return cmd_stop(state_dir)
    if args.restart:
        cmd_stop(state_dir, verbose=False)
        return cmd_detach(state_dir, timeout=args.timeout, do_check=not args.no_check)
    if args.detach:
        return cmd_detach(state_dir, timeout=args.timeout, do_check=not args.no_check)
    return _run_attached()


def _run_attached() -> int:
    apps = _apps()
    env = _spawn_env(apps)
    processes: list[subprocess.Popen[Any]] = []

    def shutdown(*_args: object) -> None:
        for process in processes:
            if process.poll() is None:
                try:
                    os.killpg(process.pid, signal.SIGTERM)
                except (ProcessLookupError, PermissionError):
                    process.terminate()

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    try:
        for name, module, port in apps:
            command = _app_command(module, port)
            print(f"starting {name}: {' '.join(command)}", flush=True)
            processes.append(subprocess.Popen(command, cwd=ROOT, env=env, start_new_session=True))
        _print_urls(apps)
        while True:
            for process in processes:
                code = process.poll()
                if code is not None:
                    shutdown()
                    for other in processes:
                        other.wait(timeout=10)
                    return int(code)
            time.sleep(0.2)
    except KeyboardInterrupt:
        shutdown()
        for process in processes:
            process.wait(timeout=10)
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
