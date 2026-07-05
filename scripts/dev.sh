#!/usr/bin/env bash
# Boots the full local stack except the web app (run that yourself for hot
# reload). Requires ANTHROPIC_API_KEY in the environment for live answers.
#
#   ANTHROPIC_API_KEY=sk-ant-... ./scripts/dev.sh
#   # then, in another terminal:
#   cd apps/web && npm run dev   ->  http://localhost:3000
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"

# Load keys from a local, gitignored .env if present (ANTHROPIC_API_KEY, FEC_API_KEY).
if [ -f "$ROOT/.env" ]; then
  set -a
  . "$ROOT/.env"
  set +a
fi

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
# tests run against a separate database so they never clobber dev data
"$PG/createdb" -p 5433 -U otm -h localhost otm_test 2>/dev/null || true

echo "[2/4] FEC data"
# Never clobber an existing load (e.g. the full nationwide import). Ingest only
# runs on an empty DB, unless OTM_FORCE_INGEST=1 is set.
EXISTING="$("$PG/psql" -tA -p 5433 -U otm -h localhost -d otm \
            -c 'SELECT COUNT(*) FROM contributions' 2>/dev/null | tr -d '[:space:]')"
case "$EXISTING" in ''|*[!0-9]*) EXISTING=0 ;; esac
if [ "${OTM_FORCE_INGEST:-}" != "1" ] && [ "$EXISTING" -gt 0 ]; then
  echo "      $EXISTING contributions already loaded; skipping ingest (OTM_FORCE_INGEST=1 to force)"
else
  echo "      Ingesting a bounded FEC slice (set FEC_API_KEY for reliability)"
  if ( cd "$ROOT/services/data" \
       && FEC_API_KEY="${FEC_API_KEY:-DEMO_KEY}" uv run python -m otm_data.fetch_slice --out-dir ./_fec \
       && uv run python -m otm_data.ingest --cycle 2024 --data-dir ./_fec ); then
    :
  else
    echo "      skipped ingest (see message above); using data already loaded"
  fi
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
