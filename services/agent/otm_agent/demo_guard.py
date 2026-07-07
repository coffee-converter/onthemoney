"""Demo abuse-protection: per-IP rate limiting, a soft daily budget breaker, and
query-answer caching. Active only when OTM_DEMO_ENABLED=1; otherwise every
function short-circuits so dev and tests are unaffected. All state lives in the
demo_* Postgres tables (see schema.sql)."""
import hashlib
import os
import re
from dataclasses import dataclass

SCHEMA_VERSION = 1  # bump to invalidate all cached traces on a shape change


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
