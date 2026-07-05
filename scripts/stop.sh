#!/usr/bin/env bash
# Stops the local backends started by dev.sh. Pass --db to also stop Postgres.
#
#   ./scripts/stop.sh        # agent + BFF (+ any web dev server)
#   ./scripts/stop.sh --db   # also stop the Postgres cluster
pkill -f "otm_agent.http" 2>/dev/null && echo "stopped agent (:8000)" || echo "agent not running"
pkill -f "dist/main.js" 2>/dev/null && echo "stopped BFF (:3001)" || echo "BFF not running"
pkill -f "scripts/dev.sh" 2>/dev/null || true
pkill -f "next dev" 2>/dev/null && echo "stopped web (:3000)" || true

if [ "${1:-}" = "--db" ]; then
  PG="$(brew --prefix postgresql@16)/bin"
  ROOT="$(cd "$(dirname "$0")/.." && pwd)"
  "$PG/pg_ctl" -D "$ROOT/services/data/.pgdata" stop 2>/dev/null \
    && echo "stopped Postgres (:5433)" || echo "Postgres not running"
fi
