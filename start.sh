#!/usr/bin/env bash
# Coinnect launcher.
#
#   ./start.sh          development: API on :8000 (auto-reload) + Vite on :5173
#   ./start.sh --prod   build the web app and serve everything from the API on :8000
#
# First run creates backend/.venv and installs npm packages. Ports: API_PORT, WEB_PORT.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
API_PORT="${API_PORT:-8000}"
WEB_PORT="${WEB_PORT:-5173}"
PYTHON="${PYTHON:-python3}"
MODE="${1:-dev}"

need() { command -v "$1" >/dev/null 2>&1 || { echo "Error: $1 is required" >&2; exit 1; }; }
need "$PYTHON"; need npm

if [ ! -x "$ROOT/backend/.venv/bin/python" ]; then
  echo "→ Creating backend/.venv"
  "$PYTHON" -m venv "$ROOT/backend/.venv"
  "$ROOT/backend/.venv/bin/pip" install -q --upgrade pip
  "$ROOT/backend/.venv/bin/pip" install -q -r "$ROOT/backend/requirements.txt"
fi
if [ ! -d "$ROOT/frontend/node_modules" ]; then
  echo "→ Installing frontend packages"
  (cd "$ROOT/frontend" && npm ci --no-audit --no-fund)
fi

UVICORN="$ROOT/backend/.venv/bin/uvicorn"

if [ "$MODE" = "--prod" ]; then
  echo "→ Building the web app"
  (cd "$ROOT/frontend" && npm run build)
  echo "→ Coinnect on http://localhost:$API_PORT  (API docs: /docs)"
  cd "$ROOT/backend" && exec "$UVICORN" app.main:app --host 0.0.0.0 --port "$API_PORT"
fi

cleanup() { trap - EXIT INT TERM; kill 0 2>/dev/null || true; }
trap cleanup EXIT INT TERM

(cd "$ROOT/backend" && CORS_ORIGINS="http://localhost:$WEB_PORT" "$UVICORN" app.main:app --reload --port "$API_PORT") &
(cd "$ROOT/frontend" && COINNECT_API="http://127.0.0.1:$API_PORT" PORT="$WEB_PORT" npx vite --host) &

echo ""
echo "  Web app   http://localhost:$WEB_PORT"
echo "  API docs  http://localhost:$API_PORT/docs"
echo "  Demo login: asha@coinnect.dev / demo1234   (Ctrl+C to stop)"
echo ""
wait
