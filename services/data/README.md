# otm-data

Deterministic, Postgres-backed source of truth for On The Money. Pure SQL, no inference.

## Slice (v1)

2024 cycle, U.S. House, individual itemized receipts.

## Dev setup

The connection string defaults to `postgresql+psycopg://otm:otm@localhost:5433/otm`
(override with `OTM_DATABASE_URL` / `OTM_TEST_DATABASE_URL`).

### Option A: Docker

```bash
docker compose up -d          # Postgres 16 on :5433
uv sync --extra dev
uv run pytest -v              # hermetic; uses tiny fixtures
```

### Option B: native Postgres 16 (no Docker)

An isolated cluster on :5433, kept out of git under `.pgdata/`:

```bash
PG=$(brew --prefix postgresql@16)/bin
"$PG/initdb" -D .pgdata -U otm -A trust
"$PG/pg_ctl" -D .pgdata -o "-p 5433" -l .pgdata/server.log start
"$PG/createdb" -p 5433 -U otm -h localhost otm
"$PG/createdb" -p 5433 -U otm -h localhost otm_test   # tests use a separate db
uv sync --extra dev
uv run pytest -v
```

Tests connect to `otm_test` (override with `OTM_TEST_DATABASE_URL`) so running
them never touches the `otm` database you load real data into.

Stop it later with `"$PG/pg_ctl" -D .pgdata stop`.

## Small slice via the FEC API (recommended for a demo)

Pull just a few competitive districts through the FEC API instead of downloading
the multi-gigabyte bulk file. Get a free key at https://api.data.gov/signup/.

```bash
FEC_API_KEY=your-key uv run python -m otm_data.fetch_slice --out-dir ./_fec
uv run python -m otm_data.ingest --cycle 2024 --data-dir ./_fec
```

The districts it pulls (`AZ-06`, `CA-22`, `PA-08`, `TX-34`) each have a centroid
in the front end, so the map can fly to them.

## Real bulk ingest

1. Download from https://www.fec.gov/data/browse-data/?tab=bulk-data (2024):
   Candidate master (`cn`), Committee master (`cm`), Candidate-committee
   linkage (`ccl`), Contributions by individuals (`itcont`).
2. Unzip each into `./_fec/` and rename to `cn.txt`, `cm.txt`, `ccl.txt`, `itcont.txt`.
3. Run:
   ```bash
   uv run python -m otm_data.ingest --cycle 2024 --data-dir ./_fec
   ```

## Query oracle

`otm_data.oracle` exposes `resolve_candidate`, `committees_for_candidate`,
`total_raised`, and `top_donors`. Aggregates exclude memo transactions (`memo_cd='X'`).
These functions are the ground truth for both the agent tools and the eval graders.
