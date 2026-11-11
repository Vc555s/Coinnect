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
need "$PYTHON"; need npm; need curl

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
  while (ss -ltnH "sport = :$API_PORT" 2>/dev/null | grep -q .); do API_PORT=$((API_PORT + 1)); done
  echo "→ Building the web app"
  (cd "$ROOT/frontend" && npm run build)
  echo "→ Coinnect on http://localhost:$API_PORT  (API docs: /docs)"
  cd "$ROOT/backend" && exec "$UVICORN" app.main:app --host 0.0.0.0 --port "$API_PORT"
fi

port_busy() {
  if command -v ss >/dev/null 2>&1; then ss -ltnH "sport = :$1" 2>/dev/null | grep -q .
  else (exec 3<>"/dev/tcp/127.0.0.1/$1") 2>/dev/null; fi
}
free_port() {  # first free port at or above $1
  local p=$1
  while port_busy "$p"; do p=$((p + 1)); done
  echo "$p"
}

cleanup() { trap - EXIT INT TERM; kill 0 2>/dev/null || true; }
trap cleanup EXIT INT TERM

# Another program may already own the default ports; never share them by accident.
want_api=$API_PORT; want_web=$WEB_PORT
API_PORT=$(free_port "$API_PORT")
WEB_PORT=$(free_port "$WEB_PORT")
[ "$API_PORT" = "$want_api" ] || echo "→ Port $want_api is in use, the API will use $API_PORT"
[ "$WEB_PORT" = "$want_web" ] || echo "→ Port $want_web is in use, the web app will use $WEB_PORT"

LOG="$ROOT/backend/data/api.log"
mkdir -p "$ROOT/backend/data"
(cd "$ROOT/backend" && CORS_ORIGINS="http://localhost:$WEB_PORT" "$UVICORN" app.main:app --reload --port "$API_PORT") >"$LOG" 2>&1 &
API_PID=$!

# Start the web app only once *our* API answers, so its proxy can't point at something else.
for _ in $(seq 1 60); do
  if curl -fs "http://127.0.0.1:$API_PORT/api/health" 2>/dev/null | grep -q '"status":"ok"'; then break; fi
  if ! kill -0 "$API_PID" 2>/dev/null; then
    echo "Error: the API failed to start. Last lines of $LOG:" >&2; tail -n 20 "$LOG" >&2; exit 1
  fi
  sleep 1
done
curl -fs "http://127.0.0.1:$API_PORT/api/health" >/dev/null || { echo "Error: API not responding on :$API_PORT (see $LOG)" >&2; exit 1; }

(cd "$ROOT/frontend" && COINNECT_API="http://127.0.0.1:$API_PORT" PORT="$WEB_PORT" npx vite --host --strictPort) &

echo ""
echo "  Web app   http://localhost:$WEB_PORT"
echo "  API docs  http://localhost:$API_PORT/docs   (log: backend/data/api.log)"
echo "  Demo login: asha@coinnect.dev / demo1234   (Ctrl+C to stop)"
echo ""
wait
