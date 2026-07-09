"""Demo abuse-protection: per-IP rate limiting, a soft daily budget breaker, and
query-answer caching. Active only when OTM_DEMO_ENABLED=1; otherwise every
function short-circuits so dev and tests are unaffected. All state lives in the
demo_* Postgres tables (see schema.sql)."""
import hashlib
import json
import os
import re
from dataclasses import dataclass
from datetime import datetime
from sqlalchemy import Engine, text

SCHEMA_VERSION = 5  # bump to invalidate all cached traces on a shape change


@dataclass(frozen=True)
class DemoConfig:
    enabled: bool
    daily_usd: float
    max_query_chars: int
    rate_per_min: int
    rate_per_day: int
    max_tokens: int
    admin_secret: str | None


def load_demo_config() -> DemoConfig:
    return DemoConfig(
        enabled=os.environ.get("OTM_DEMO_ENABLED") == "1",
        daily_usd=float(os.environ.get("OTM_DEMO_DAILY_USD", "5.00")),
        max_query_chars=int(os.environ.get("OTM_DEMO_MAX_QUERY_CHARS", "500")),
        rate_per_min=int(os.environ.get("OTM_DEMO_RATE_PER_MIN", "5")),
        rate_per_day=int(os.environ.get("OTM_DEMO_RATE_PER_DAY", "40")),
        max_tokens=int(os.environ.get("OTM_DEMO_AGENT_MAX_TOKENS", "1024")),
        admin_secret=os.environ.get("OTM_ADMIN_SECRET"),
    )


def query_hash(query: str) -> str:
    norm = re.sub(r"\s+", " ", query.strip().lower()).rstrip("?.!").strip()
    return hashlib.sha256(norm.encode("utf-8")).hexdigest()


_BUMP = text(
    "INSERT INTO demo_rate_limit (ip, window_key, count) VALUES (:ip, :wk, 1) "
    "ON CONFLICT (ip, window_key) DO UPDATE SET count = demo_rate_limit.count + 1 "
    "RETURNING count"
)


def _bump(conn, ip: str, window_key: str) -> int:
    return conn.execute(_BUMP, {"ip": ip, "wk": window_key}).scalar_one()


def rate_limited(engine: Engine, cfg: DemoConfig, ip: str, now: datetime) -> bool:
    minute_key = "m:" + now.strftime("%Y-%m-%dT%H:%M")
    day_key = "d:" + now.strftime("%Y-%m-%d")
    with engine.begin() as conn:
        per_min = _bump(conn, ip, minute_key)
        per_day = _bump(conn, ip, day_key)
    return per_min > cfg.rate_per_min or per_day > cfg.rate_per_day


from datetime import date

_SPENT = text("SELECT spent_usd FROM demo_budget_ledger WHERE day = :day")
_BILL = text(
    "INSERT INTO demo_budget_ledger (day, spent_usd) VALUES (:day, :cost) "
    "ON CONFLICT (day) DO UPDATE SET spent_usd = demo_budget_ledger.spent_usd + :cost"
)


def budget_exceeded(engine: Engine, cfg: DemoConfig, day: date) -> bool:
    with engine.connect() as conn:
        spent = conn.execute(_SPENT, {"day": day}).scalar()
    return float(spent or 0) >= cfg.daily_usd


def bill(engine: Engine, day: date, cost_usd: float) -> None:
    with engine.begin() as conn:
        conn.execute(_BILL, {"day": day, "cost": cost_usd})


_CGET = text(
    "SELECT trace_json FROM demo_answer_cache "
    "WHERE query_hash = :h AND schema_version = :v"
)
_CPUT = text(
    "INSERT INTO demo_answer_cache (query_hash, trace_json, schema_version) "
    "VALUES (:h, :t, :v) "
    "ON CONFLICT (query_hash) DO UPDATE SET "
    "trace_json = :t, schema_version = :v, created_at = now()"
)


def cache_get(engine: Engine, qhash: str) -> list[dict] | None:
    with engine.connect() as conn:
        row = conn.execute(_CGET, {"h": qhash, "v": SCHEMA_VERSION}).scalar()
    return list(row) if row is not None else None


def cache_put(engine: Engine, qhash: str, messages: list[dict]) -> None:
    with engine.begin() as conn:
        conn.execute(_CPUT, {"h": qhash, "t": json.dumps(messages),
                             "v": SCHEMA_VERSION})


_REQS = text("SELECT COALESCE(SUM(count),0) FROM demo_rate_limit WHERE window_key = :dk")
_CACHED = text("SELECT COUNT(*) FROM demo_answer_cache")


def usage_summary(engine: Engine, day: date) -> dict:
    day_key = "d:" + day.strftime("%Y-%m-%d")
    with engine.connect() as conn:
        spent = conn.execute(_SPENT, {"day": day}).scalar()
        requests = conn.execute(_REQS, {"dk": day_key}).scalar_one()
        cached = conn.execute(_CACHED).scalar_one()
    return {"spent_usd": float(spent or 0), "requests_today": int(requests),
            "cached_answers": int(cached)}


RATE_MSG = ("You're asking faster than this public demo allows. Give it a minute "
            "and try again — the map and scoreboard still work in the meantime.")
BUDGET_MSG = ("On The Money's public demo has reached today's usage limit. It "
              "resets at midnight UTC — thanks for trying it! The map, scoreboard, "
              "and district lookups still work.")


def client_ip(headers) -> str:
    # Prefer x-otm-client-ip: the BFF resolves this from the true connecting peer
    # (Fly-Client-IP) and forwards it on the secret-gated proxy hop, so it is not
    # client-forgeable. Raw x-forwarded-for is client-settable — keying the rate
    # limiter on it would let a direct caller rotate the header to mint unlimited
    # buckets — so it is only a dev/local fallback.
    trusted = headers.get("x-otm-client-ip")
    if trusted:
        return trusted.strip()
    fwd = headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    return "unknown"


def limit_answer(text: str) -> dict:
    """The answer body returned when a request is refused by the guard (length,
    rate, or budget). Shaped like a normal answer so clients render it uniformly."""
    return {"text": text, "confidence": "insufficient", "total": None,
            "receipts": None, "individual_total": None, "citations": [], "scene": None}


def limit_answer_event(text: str) -> dict:
    return {"event": "answer", "data": json.dumps(limit_answer(text))}
