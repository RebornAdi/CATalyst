#!/bin/bash
set -e
ROOT="$(cd "$(dirname "$0")" && pwd)"

cleanup() {
  trap - EXIT INT TERM
  kill 0 2>/dev/null || true
}
trap cleanup EXIT INT TERM

if [ ! -d "$ROOT/.venv" ]; then
  python3 -m venv "$ROOT/.venv"
fi

"$ROOT/.venv/bin/python" -m pip install -q --upgrade pip
"$ROOT/.venv/bin/pip" install -q -r "$ROOT/requirements-dev.txt"

if [ ! -d "$ROOT/frontend/node_modules" ]; then
  (cd "$ROOT/frontend" && npm install)
fi

(cd "$ROOT/backend/module1_data_simulation" && "$ROOT/.venv/bin/uvicorn" app:app --port 8001) &
(cd "$ROOT/backend/module2_intelligence" && "$ROOT/.venv/bin/uvicorn" app.main:app --port 8002) &
(cd "$ROOT/backend/module3_orchestrator" && "$ROOT/.venv/bin/uvicorn" app:app --port 8003) &

sleep 2
(cd "$ROOT/frontend" && npm run dev -- --host 127.0.0.1) &

echo ""
echo "CATalyst is starting..."
echo "Module 1: http://127.0.0.1:8001/docs"
echo "Module 2: http://127.0.0.1:8002/docs"
echo "Module 3: http://127.0.0.1:8003/docs"
echo "Frontend: http://127.0.0.1:5173"
echo ""
echo "Press Ctrl+C to stop everything."
wait
