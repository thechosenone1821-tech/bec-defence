#!/usr/bin/env bash
# Stop exactly the RAKSHA processes that ./start.sh started — and nothing else.
#
#   ./stop.sh                   stop the recorded stack
#   ./stop.sh --state-dir DIR   stack recorded in another run directory
#
# Each recorded pid is verified to still run the expected app module on the
# expected port before it is signalled, so a recycled pid belonging to another
# program is reported and left alone.  A stack that is not running at all exits
# successfully: stop is idempotent.
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
  echo "FAIL: no Python interpreter found to read .raksha/launcher.json." >&2
  echo "      If the apps were started another way, find them with:" >&2
  echo "      ps -o pid,args -C python3 | grep 'apps\\.'" >&2
  exit 1
fi

exec "$PY" tools/launch_apps.py --stop "$@"
