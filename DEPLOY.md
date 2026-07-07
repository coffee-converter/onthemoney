# Deploying On The Money (Vercel + Neon + a container host)

This is a polyglot monorepo. Vercel hosts the web app, Neon hosts Postgres, and
a container host (this guide uses **Fly.io**; Railway/Render work the same way
from the Dockerfiles) runs the two private backend services.

```
Browser ─► Vercel (Next.js web + /api/bff proxy, PUBLIC)
             │  injects OTM_PROXY_SECRET, forwards client IP
             ▼
           BFF (NestJS, container host)  ──►  Agent (FastAPI, container host, PRIVATE)
             AGENT_URL → agent                 verifies OTM_PROXY_SECRET (rejects if missing)
                                               OTM_DATABASE_URL → Neon
                                               ANTHROPIC_API_KEY, demo-guard env
                                                        │
                                                        ▼
                                                     Neon Postgres
```

The demo abuse-protection (per-IP rate limit, $5/day budget breaker, answer
cache, shared-secret gate) lives in the agent and activates when
`OTM_DEMO_ENABLED=1`.

## Prerequisites

- Accounts: [Neon](https://neon.tech), [Fly.io](https://fly.io), [Vercel](https://vercel.com).
- An **`ANTHROPIC_API_KEY`** — ideally a **dedicated key in its own workspace
  with a monthly spend cap** set in the Anthropic Console. This is the ultimate
  backstop the code can't set for you.
- CLIs: `flyctl` (`brew install flyctl`), `vercel` (installed), `psql` (installed).
- Pick strong random secrets once and reuse them across services:
  ```bash
  export OTM_PROXY_SECRET=$(openssl rand -hex 32)
  export OTM_ADMIN_SECRET=$(openssl rand -hex 32)
  ```

## Environment matrix

| Var | Agent | BFF | Vercel (web) | Value |
| --- | :-: | :-: | :-: | --- |
| `OTM_DATABASE_URL` | ✅ | | | Neon URL, `postgresql+psycopg://…?sslmode=require` |
| `ANTHROPIC_API_KEY` | ✅ | | | your dedicated key |
| `OTM_DEMO_ENABLED` | ✅ | | | `1` |
| `OTM_DEMO_DAILY_USD` | ✅ | | | `5.00` (tune freely) |
| `OTM_PROXY_SECRET` | ✅ | ✅ | ✅ | same random value everywhere |
| `OTM_ADMIN_SECRET` | ✅ | | | random value (gates `/admin/usage`) |
| `AGENT_URL` | | ✅ | | agent's private URL, e.g. `http://otm-agent.internal:8000` |
| `BFF_INTERNAL_URL` | | | ✅ | BFF's public URL, e.g. `https://otm-bff.fly.dev` |
| `NEXT_PUBLIC_API_URL` | | | leave **unset** | so the client uses the same-origin `/api/bff` proxy |

## Step 1 — Neon Postgres

1. Create a Neon project; copy the connection string. Convert it for SQLAlchemy
   + psycopg3 by inserting the driver: `postgresql+psycopg://…` and keep
   `?sslmode=require`. Save it:
   ```bash
   export NEON_URL='postgresql://USER:PASS@HOST/neondb?sslmode=require'      # raw (for psql)
   export OTM_DATABASE_URL='postgresql+psycopg://USER:PASS@HOST/neondb?sslmode=require'
   ```
2. Create the schema (includes the base FEC tables + the `demo_*` tables):
   ```bash
   psql "$NEON_URL" -f services/data/otm_data/schema.sql
   ```
3. Load a **bounded slice** (fits Neon's ~0.5 GB free tier — the full ~4M-row
   nationwide load needs a paid tier). Run the ingest locally, pointed at Neon:
   ```bash
   cd services/data
   FEC_API_KEY=your_fec_key uv run python -m otm_data.fetch_slice --out-dir ./_fec
   OTM_DATABASE_URL="$OTM_DATABASE_URL" uv run python -m otm_data.ingest --cycle 2024 --data-dir ./_fec
   ```
   (No `FEC_API_KEY`? `fetch_slice` falls back to a small demo slice via `DEMO_KEY`.)
4. Sanity check: `psql "$NEON_URL" -c 'SELECT count(*) FROM contributions;'`

## Step 2 — Backend services on Fly.io

`flyctl auth login` first. Deploy each service as its own Fly app.

**Agent** (private — no public services). `fly.toml` in `services/agent`:
```toml
app = "otm-agent"
primary_region = "iad"
[build]
  dockerfile = "Dockerfile"
[env]
  OTM_DEMO_ENABLED = "1"
  OTM_DEMO_DAILY_USD = "5.00"
# No [http_service] block → no public endpoint; reachable only at otm-agent.internal:8000
```
The agent's Dockerfile builds from the **repo root** (it bundles the `otm_data`
path dep), so deploy with an explicit context:
```bash
fly deploy --config services/agent/fly.toml --dockerfile services/agent/Dockerfile .
fly secrets set --app otm-agent \
  OTM_DATABASE_URL="$OTM_DATABASE_URL" ANTHROPIC_API_KEY="$ANTHROPIC_API_KEY" \
  OTM_PROXY_SECRET="$OTM_PROXY_SECRET" OTM_ADMIN_SECRET="$OTM_ADMIN_SECRET"
```

**BFF** (public — Vercel reaches it). `fly.toml` in `apps/api`:
```toml
app = "otm-bff"
primary_region = "iad"
[build]
  dockerfile = "Dockerfile"
[http_service]
  internal_port = 3001
  force_https = true
  auto_stop_machines = true
  min_machines_running = 0
```
```bash
fly deploy --config apps/api/fly.toml apps/api
fly secrets set --app otm-bff \
  AGENT_URL="http://otm-agent.internal:8000" OTM_PROXY_SECRET="$OTM_PROXY_SECRET"
```
The BFF being public is safe: the agent verifies `OTM_PROXY_SECRET`, so a request
reaching the BFF without the secret is rejected downstream (403).

## Step 3 — Web app on Vercel

All Vercel commands are scoped to the **`nft-coffee`** team.
```bash
cd apps/web
vercel link --scope nft-coffee                          # create/link project under NFTcoffee
vercel env add OTM_PROXY_SECRET production --scope nft-coffee    # paste the same secret
vercel env add BFF_INTERNAL_URL production --scope nft-coffee    # https://otm-bff.fly.dev
vercel --prod --scope nft-coffee
```
Leave `NEXT_PUBLIC_API_URL` unset so the browser uses the same-origin `/api/bff`
proxy (which injects the secret the browser's `EventSource` cannot send).

## Step 4 — Verify

- `curl https://<your-vercel-app>/api/bff/scoreboard` → scoreboard JSON.
- Open the app, ask a question, confirm the streamed answer + map render.
- `curl -H "x-admin-secret: $OTM_ADMIN_SECRET" http://otm-agent.internal:8000/admin/usage`
  (from a Fly machine or via `fly ssh`) → today's spend/requests/cache counts.
- Direct-hit the BFF without the secret → expect a 403 from the agent, proving
  the gate holds.

## Guardrails recap

- Set the **Anthropic workspace monthly spend cap** (Console) — the one control
  that holds even if everything else fails.
- Keep the agent **private** (no Fly `[http_service]`); only the BFF is public.
- Rotate `OTM_PROXY_SECRET`/`OTM_ADMIN_SECRET` if ever exposed.
