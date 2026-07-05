#!/usr/bin/env bash
# Boots the full local stack except the web app (run that yourself so you get
# hot reload). Requires ANTHROPIC_API_KEY in the environment for live answers.
#
#   ANTHROPIC_API_KEY=sk-ant-... ./scripts/dev.sh
#   # then, in another terminal:
#   cd apps/web && npm run dev   ->  http://localhost:3000
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PG="$(brew --prefix postgresql@16)/bin"
PGDATA="$ROOT/services/data/.pgdata"

echo "[1/4] Postgres on :5433"
"$PG/pg_ctl" -D "$PGDATA" -o "-p 5433 -k /tmp" -l "$PGDATA/server.log" start \
  2>/dev/null || echo "      (already running)"
sleep 1

echo "[2/4] Ingesting a bounded FEC slice (FEC_API_KEY defaults to DEMO_KEY)"
cd "$ROOT/services/data"
if FEC_API_KEY="${FEC_API_KEY:-DEMO_KEY}" uv run python -m otm_data.fetch_slice --out-dir ./_fec; then
  uv run python -m otm_data.ingest --cycle 2024 --data-dir ./_fec
else
  echo "      (fetch failed - continuing with whatever is already loaded)"
fi

if [ -z "${ANTHROPIC_API_KEY:-}" ]; then
  echo "      WARNING: ANTHROPIC_API_KEY is not set. /ask will error until you set it."
fi

echo "[3/4] Agent service on :8000"
cd "$ROOT/services/agent"
uv run python -m otm_agent.http &
AGENT_PID=$!

echo "[4/4] BFF on :3001"
cd "$ROOT/apps/api"
npm run build >/dev/null 2>&1
node dist/main.js &
BFF_PID=$!

trap 'echo; echo "stopping..."; kill $AGENT_PID $BFF_PID 2>/dev/null || true' EXIT INT TERM

sleep 3
echo
echo "Up: agent :8000 (pid $AGENT_PID), BFF :3001 (pid $BFF_PID)."
echo "Now start the web app in another terminal:"
echo "    cd apps/web && npm run dev   ->  http://localhost:3000"
echo "Press Ctrl-C here to stop the backends."
wait
