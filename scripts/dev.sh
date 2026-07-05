#!/usr/bin/env bash
# Boots the full local stack except the web app (run that yourself for hot
# reload). Requires ANTHROPIC_API_KEY in the environment for live answers.
#
#   ANTHROPIC_API_KEY=sk-ant-... ./scripts/dev.sh
#   # then, in another terminal:
#   cd apps/web && npm run dev   ->  http://localhost:3000
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PG="$(brew --prefix postgresql@16)/bin"
PGDATA="$ROOT/services/data/.pgdata"
LOGS="$ROOT/.devlogs"
mkdir -p "$LOGS"

echo "[1/4] Postgres on :5433"
if "$PG/pg_isready" -q -h localhost -p 5433 2>/dev/null; then
  echo "      already running"
else
  "$PG/pg_ctl" -D "$PGDATA" -o "-p 5433 -k /tmp" -l "$PGDATA/server.log" start
fi

echo "[2/4] Ingesting a bounded FEC slice (set FEC_API_KEY for reliability)"
if ( cd "$ROOT/services/data" \
     && FEC_API_KEY="${FEC_API_KEY:-DEMO_KEY}" uv run python -m otm_data.fetch_slice --out-dir ./_fec \
     && uv run python -m otm_data.ingest --cycle 2024 --data-dir ./_fec ); then
  :
else
  echo "      skipped ingest (see message above); using data already loaded"
fi

if [ -z "${ANTHROPIC_API_KEY:-}" ]; then
  echo "      WARNING: ANTHROPIC_API_KEY is not set. /ask will error until you set it."
fi

echo "[3/4] Agent service on :8000  (log: .devlogs/agent.log)"
( cd "$ROOT/services/agent" && exec uv run python -m otm_agent.http ) >"$LOGS/agent.log" 2>&1 &
AGENT_PID=$!

echo "[4/4] BFF on :3001  (log: .devlogs/bff.log)"
( cd "$ROOT/apps/api" && npm run build >/dev/null 2>&1 && exec node dist/main.js ) >"$LOGS/bff.log" 2>&1 &
BFF_PID=$!

trap 'echo; echo "stopping..."; kill $AGENT_PID $BFF_PID 2>/dev/null || true' EXIT INT TERM

sleep 4
echo
echo "Up: agent :8000 (pid $AGENT_PID), BFF :3001 (pid $BFF_PID)."
echo "Web app:  cd apps/web && npm run dev   ->  http://localhost:3000"
echo "Logs:     tail -f .devlogs/agent.log .devlogs/bff.log"
echo "Stop:     Ctrl-C here, or ./scripts/stop.sh"
wait
