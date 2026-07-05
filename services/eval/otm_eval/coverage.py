"""Dataset coverage stats for the scoreboard: how much real data backs the
eval. Not a data dump - just scale, so a viewer sees the eval runs on the full
dataset, not a toy slice.
"""
from sqlalchemy import Engine, text


def coverage_stats(engine: Engine, *, cycle: int = 2024) -> dict:
    with engine.connect() as c:
        districts = c.execute(text(
            "SELECT COUNT(DISTINCT office_state || '-' || district) "
            "FROM candidates WHERE office = 'H'"
        )).scalar()
        candidates = c.execute(text(
            "SELECT COUNT(*) FROM candidates WHERE office = 'H'"
        )).scalar()
        contributions = c.execute(text("SELECT COUNT(*) FROM contributions")).scalar()
    return {
        "cycle": cycle,
        "districts": int(districts or 0),
        "candidates": int(candidates or 0),
        "contributions": int(contributions or 0),
    }
