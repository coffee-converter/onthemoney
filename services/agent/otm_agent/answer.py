from dataclasses import dataclass
from enum import Enum
from sqlalchemy import Engine
from otm_agent.tools import resolve_entity, funding_summary
from otm_agent.geo import district_centroid
from otm_agent.scene import build_scene


class Confidence(str, Enum):
    HIGH = "high"
    PARTIAL = "partial"
    INSUFFICIENT = "insufficient"


@dataclass
class Citation:
    label: str
    url: str


@dataclass
class Answer:
    narration: str
    confidence: Confidence
    citations: list["Citation"]
    scene: dict | None


def fec_committee_url(cmte_id: str) -> str:
    return f"https://www.fec.gov/data/committee/{cmte_id}/"


def compose_answer(engine: Engine, *, state: str, district: str,
                   cycle: int = 2024, top_n: int = 10) -> Answer:
    res = resolve_entity(engine, state=state, district=district, cycle=cycle)
    if res is None:
        return Answer(
            narration=(f"No U.S. House candidate for {state}-{district} is on file "
                       f"for the {cycle} cycle in this dataset."),
            confidence=Confidence.INSUFFICIENT,
            citations=[],
            scene=None,
        )

    fs = funding_summary(engine, res.candidate.cand_id, cycle=cycle, top_n=top_n)
    centroid = district_centroid(state, district)
    scene = (build_scene(state=state, district=district, centroid=centroid,
                         donors=fs.donors) if centroid else None)
    citations = [Citation(label=cid, url=fec_committee_url(cid))
                 for cid in res.committees]

    if fs.total == "0.00":
        confidence = Confidence.PARTIAL
        narration = (f"{res.candidate.name} ({state}-{district}) has no itemized "
                     f"individual receipts recorded for {cycle} in this dataset.")
    else:
        confidence = Confidence.HIGH
        top = fs.donors[0].name if fs.donors else "not available"
        narration = (f"{res.candidate.name} ({state}-{district}) reported "
                     f"{fs.total} in itemized individual receipts for {cycle}. "
                     f"Largest itemized donor: {top}.")

    return Answer(narration=narration, confidence=confidence,
                  citations=citations, scene=scene)
