import os
from dataclasses import dataclass

DEFAULT_MODEL = "claude-sonnet-5"


@dataclass(frozen=True)
class Settings:
    model: str
    database_url: str | None
    top_n: int


def get_settings() -> Settings:
    return Settings(
        model=os.environ.get("OTM_AGENT_MODEL", DEFAULT_MODEL),
        database_url=os.environ.get("OTM_DATABASE_URL"),
        top_n=int(os.environ.get("OTM_AGENT_TOP_N", "10")),
    )


# Approximate public list prices in USD per million tokens (input, output),
# keyed by model id. Used only for the operability read-out and always shown as
# an estimate. Verify current numbers against the claude-api reference before a
# deploy; unknown ids use a mid-tier fallback.
_PRICES: dict[str, tuple[float, float]] = {
    "claude-opus-4-8": (15.0, 75.0),
    "claude-sonnet-5": (3.0, 15.0),
    "claude-haiku-4-5-20251001": (1.0, 5.0),
}
_FALLBACK_PRICE: tuple[float, float] = (3.0, 15.0)


def estimate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    price_in, price_out = _PRICES.get(model, _FALLBACK_PRICE)
    return input_tokens / 1_000_000 * price_in + output_tokens / 1_000_000 * price_out
