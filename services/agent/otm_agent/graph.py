import re
from dataclasses import dataclass
from sqlalchemy import Engine
from langgraph.graph import StateGraph, START, END
from otm_agent.answer import compose_answer, Confidence

_MONEY = re.compile(r"\$?([\d,]+\.\d{2})")


def _norm_money(raw: str) -> str:
    return raw.replace(",", "")


@dataclass
class Verdict:
    district: str
    claimed_total: str | None
    truth_total: str
    verified: bool
    confidence: Confidence


def parse_claimed_total(text: str) -> str | None:
    m = _MONEY.search(text or "")
    return _norm_money(m.group(1)) if m else None


def _resolve(state: dict) -> dict:
    ans = compose_answer(state["engine"], state=state["state"],
                         district=state["district"])
    truth = "0.00"
    for c in _MONEY.findall(ans.narration):
        truth = _norm_money(c)
        break
    state["truth_total"] = truth
    state["truth_confidence"] = ans.confidence
    return state


def _verify(state: dict) -> dict:
    state["verified"] = (state.get("claimed_total") == state["truth_total"])
    return state


def _calibrate(state: dict) -> dict:
    if state["verified"]:
        state["final_confidence"] = state["truth_confidence"]
    else:
        state["final_confidence"] = Confidence.INSUFFICIENT
    return state


def build_graph():
    g = StateGraph(dict)
    g.add_node("resolve", _resolve)
    g.add_node("verify", _verify)
    g.add_node("calibrate", _calibrate)
    g.add_edge(START, "resolve")
    g.add_edge("resolve", "verify")
    g.add_edge("verify", "calibrate")
    g.add_edge("calibrate", END)
    return g.compile()


def supervise(engine: Engine, *, state: str, district: str,
              claimed_total: str | None) -> Verdict:
    graph = build_graph()
    result = graph.invoke({
        "engine": engine, "state": state, "district": district,
        "claimed_total": claimed_total,
    })
    return Verdict(
        district=f"{state}-{district}",
        claimed_total=claimed_total,
        truth_total=result["truth_total"],
        verified=result["verified"],
        confidence=result["final_confidence"],
    )
