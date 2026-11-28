#!/usr/bin/env bash
# Start the whole RAKSHA stack with one action: preflight, both app processes,
# both Phosphor console origins, and a readiness wait before it returns.
#
#   ./start.sh                  start (or report the stack that is already up)
#   ./start.sh --status         show what is running and where
#   ./start.sh --check          preflight only, start nothing
#   ./start.sh --timeout 180    more patience for a cold venv or a slow disk
#   ./start.sh --restart        stop, then start again
#
# All real logic lives in tools/launch_apps.py so this script and start.bat can
# never drift apart.  Nothing here starts a database or a broker (the audit
# ledger is in-process), and no model run, eval or Commander call is executed.
#
# Stop with ./stop.sh.  Logs land in .raksha/logs/, the pid record in
# .raksha/launcher.json; both are git-ignored scratch.
# Re-exec under bash when invoked as `sh start.sh`: the argument handling below
# uses bash arrays, and launcher flags must behave the same either way.
if [ -z "${BASH_VERSION:-}" ]; then exec bash "$0" "$@"; fi

set -euo pipefail
cd "$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

if [ -n "${RAKSHA_PYTHON:-}" ]; then
  PY="$RAKSHA_PYTHON"
elif [ -x ".venv/bin/python" ]; then
  PY=".venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
  PY="$(command -v python3)"
elif command -v python >/dev/null 2>&1; then
  PY="$(command -v python)"
else
  echo "FAIL: no Python interpreter found — create the venv first:" >&2
  echo "      python3 -m venv .venv && .venv/bin/python -m pip install -r requirements.txt" >&2
  exit 1
fi

if [ ! -f "tools/launch_apps.py" ]; then
  echo "FAIL: tools/launch_apps.py is missing — run this script from the repository root." >&2
  exit 1
fi

MODE="--detach"
EXTRA=()
for arg in "$@"; do
  case "$arg" in
    --status | --check | --stop | --restart) MODE="$arg" ;;
    *) EXTRA+=("$arg") ;;
  esac
done

exec "$PY" tools/launch_apps.py "$MODE" ${EXTRA[@]+"${EXTRA[@]}"}
