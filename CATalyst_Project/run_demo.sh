#!/bin/bash
set -e
ROOT="$(cd "$(dirname "$0")" && pwd)"

if [ ! -d "$ROOT/backend/module1_data_simulation/.venv" ]; then
  python3 -m venv "$ROOT/backend/module1_data_simulation/.venv"
  "$ROOT/backend/module1_data_simulation/.venv/bin/pip" install -r "$ROOT/backend/module1_data_simulation/requirements.txt"
fi

if [ ! -d "$ROOT/backend/module2_intelligence/.venv" ]; then
  python3 -m venv "$ROOT/backend/module2_intelligence/.venv"
  "$ROOT/backend/module2_intelligence/.venv/bin/pip" install -r "$ROOT/backend/module2_intelligence/requirements.txt"
fi

if [ ! -d "$ROOT/backend/module3_orchestrator/.venv" ]; then
  python3 -m venv "$ROOT/backend/module3_orchestrator/.venv"
  "$ROOT/backend/module3_orchestrator/.venv/bin/pip" install -r "$ROOT/backend/module3_orchestrator/requirements.txt"
fi

(cd "$ROOT/backend/module1_data_simulation" && .venv/bin/uvicorn app:app --port 8001) &
(cd "$ROOT/backend/module2_intelligence" && .venv/bin/uvicorn app:app --port 8002) &
(cd "$ROOT/backend/module3_orchestrator" && .venv/bin/uvicorn app:app --port 8003) &

trap 'kill 0' EXIT
wait
