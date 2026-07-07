import os
import re
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
# keyed by the model *family* id (no date suffix, no context-window tag). Used
# only for the operability read-out and always shown as an estimate. Verify
# current numbers against the claude-api reference before a deploy; unknown ids
# use a mid-tier fallback.
_PRICES: dict[str, tuple[float, float]] = {
    "claude-opus-4-8": (15.0, 75.0),
    "claude-sonnet-5": (3.0, 15.0),
    "claude-haiku-4-5": (1.0, 5.0),
}
_FALLBACK_PRICE: tuple[float, float] = (3.0, 15.0)


def _price_key(model: str) -> str:
    """Reduce a deploy model id to its pricing family: drop a context-window tag
    like `[1m]` and a trailing `-YYYYMMDD` snapshot date so dated/bare forms of
    the same model resolve to one price."""
    base = model.split("[", 1)[0]
    return re.sub(r"-\d{8}$", "", base)


def estimate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    price_in, price_out = _PRICES.get(_price_key(model), _FALLBACK_PRICE)
    return input_tokens / 1_000_000 * price_in + output_tokens / 1_000_000 * price_out
