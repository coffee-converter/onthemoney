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
