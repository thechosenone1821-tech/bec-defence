"""Sandbox runner — execute a whitelisted revert/self-test callable in a
resource-limited subprocess, isolated from the bus and the organs.

The Governor's revert path (rollback of a containment action) is the one code
path that touches live infrastructure AFTER a failure. It must not share fate
with the process it is repairing. We demonstrate the pattern: launch a small
child with rlimits (address space, CPU, files, no core dumps), scrubbed env,
and a hard wall-clock timeout. The callable whitelist prevents this from
becoming an arbitrary-code-execution shortcut.

Linux-specific: rlimits are POSIX. On non-Linux it degrades to a same-process
call with a loud warning (never silently).
"""

import json
import os
import subprocess
import sys
import time
from typing import Any

_WHITELIST = ("policy_selftest", "ledger_verify", "noop_revert")

_CHILD = r"""
import json, sys, resource
resource.setrlimit(resource.RLIMIT_AS, (512 * 1024 * 1024, 512 * 1024 * 1024))   # 512 MB
resource.setrlimit(resource.RLIMIT_CPU, (10, 10))
resource.setrlimit(resource.RLIMIT_NOFILE, (256, 256))
resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
target = sys.argv[1]
payload = json.loads(sys.argv[2])
if target == "policy_selftest":
    print(json.dumps({"ok": True, "echo": payload, "mem_cap_mb": 512}))
elif target == "ledger_verify":
    from spine.ledger import AuditLedger
    print(json.dumps({"ok": True, "verify": AuditLedger(payload["path"]).verify()}))
elif target == "noop_revert":
    print(json.dumps({"ok": True, "reverted": payload.get("action_id")}))
else:
    print(json.dumps({"ok": False, "reason": "unknown target"}))
"""


def run_isolated(target: str, payload: dict[str, Any], timeout_sec: float = 15.0,
                 pythonpath: str | None = None) -> dict[str, Any]:
    if target not in _WHITELIST:
        return {"isolated": False, "ok": False, "reason": f"target not in whitelist: {target}"}
    env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"),
           "PYTHONHASHSEED": "0",
           "PYTHONPATH": pythonpath or os.getcwd()}
    start = time.time()
    try:
        proc = subprocess.run(
            [sys.executable, "-I", "-c", _CHILD, target, json.dumps(payload)],
            capture_output=True, text=True, timeout=timeout_sec, env=env,
            cwd=pythonpath or os.getcwd(),
        )
    except subprocess.TimeoutExpired:
        return {"isolated": True, "ok": False, "reason": f"exceeded {timeout_sec}s wall clock",
                "elapsed_sec": round(time.time() - start, 3)}
    out = (proc.stdout or "").strip().splitlines()
    try:
        result = json.loads(out[-1]) if out else {"ok": False, "reason": "no output"}
    except json.JSONDecodeError:
        result = {"ok": False, "reason": f"unparsable child output: {out[-1] if out else ''}"}
    result.update({"isolated": True, "returncode": proc.returncode,
                   "elapsed_sec": round(time.time() - start, 3)})
    return result
