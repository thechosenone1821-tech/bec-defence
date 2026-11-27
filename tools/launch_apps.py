#!/usr/bin/env python3
"""One deterministic process launcher for exactly two RAKSHA apps.

The Infra/SOC console and the Citizen PWA are started as separate uvicorn
processes. Both app entrypoints bind all interfaces for the Arena preview.
This launcher adds no third app, no AI model/Commander endpoint, no live
executor and no real containment action.
"""
from __future__ import annotations

import json
import os
import pathlib
import signal
import subprocess
import sys
import time
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parents[1]
INFRA_MANIFEST = ROOT / "apps" / "infra" / "BOOT_MANIFEST.json"
CITIZEN_MANIFEST = ROOT / "apps" / "citizen" / "BOOT_MANIFEST.json"


def _port(path: pathlib.Path) -> int:
    return int(json.loads(path.read_text(encoding="utf-8"))["default_port"])


def _apps() -> tuple[tuple[str, str, int], ...]:
    return (
        ("infra", "apps.infra", _port(INFRA_MANIFEST)),
        ("citizen", "apps.citizen", _port(CITIZEN_MANIFEST)),
    )


def main(argv: list[str] | None = None) -> int:
    apps = _apps()
    env = dict(os.environ)
    env["PYTHONUNBUFFERED"] = "1"
    env["PYTHONPATH"] = os.pathsep.join(
        [str(ROOT), str(ROOT / "raksha-code"), env.get("PYTHONPATH", "")]
    ).rstrip(os.pathsep)
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
            command = [sys.executable, "-m", module, "--port", str(port)]
            print(f"starting {name}: {' '.join(command)}", flush=True)
            processes.append(subprocess.Popen(
                command, cwd=ROOT, env=env, start_new_session=True,
            ))
        print(f"Infra console: /app/console on port {apps[0][2]}", flush=True)
        print(f"Citizen PWA: /app/ on port {apps[1][2]}", flush=True)
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
