from typing import Annotated, Literal
from typing_extensions import TypedDict
from enum import Enum
import operator
from langgraph.graph import StateGraph, START, END

class Confidence(str, Enum):
    HIGH = "high"
    PARTIAL = "partial"
    INSUFFICIENT = "insufficient"

MAX_RETRIES = 1


# ----------- State

class State(TypedDict):
    truth_fn: object
    state: str
    district: str
    claimed_total: str | None
    truth_total: str
    truth_confidence: Confidence
    verified: bool
    retries: int
    final_confidence: Confidence
    trace: Annotated[list, operator.add]


# ----------- Nodes

def _resolve(state: State) -> dict:
    total, conf = state["truth_fn"](state["state"], state["district"])
    return {
        "truth_total": total,
        "truth_confidence": conf,
        "trace": [f"resolve: {total}"]
    }

def _verify(state: State) -> dict:
    return { 
        "verified": state.get("claimed_total") == state["truth_total"], 
        "trace": ["verify"] 
    }

def _reresolve(state: State) -> dict:
    total, conf = state["truth_fn"](state["state"], state["district"])
    return { 
        "truth_total": total, 
        "truth_confidence": conf,
        "retries": state.get("retries", 0) + 1, 
        "trace": ["reresolve"] 
    }

def _calibrate(state: State) -> dict:
    final = state["truth_confidence"] if state["verified"] else Confidence.INSUFFICIENT
    return {
        "final_confidence": final,
        "trace": [f"calibrate: {final.value}"]
    }


# ----------- Edges

def route_after_verify(state: State) -> Literal["calibrate", "reresolve"]:
    if state["verified"]:
        return "calibrate"
    if state.get("retries", 0) < MAX_RETRIES:
        return "reresolve"
    return "calibrate"


# ----------- Graph

def build_graph():
    g = StateGraph(State)
    g.add_node("resolve", _resolve)
    g.add_node("verify", _verify)
    g.add_node("reresolve", _reresolve)
    g.add_node("calibrate", _calibrate)
    g.add_edge(START, "resolve")
    g.add_edge("resolve", "verify")
    g.add_conditional_edges("verify", route_after_verify, ["calibrate", "reresolve"])
    g.add_edge("reresolve", "verify")
    g.add_edge("calibrate", END)
    return g.compile()


# ----------- Main

def _demo_oracle():
    seats = {
        ("NY", "14"): ("2841577.19", Confidence.HIGH),
        ("TX", "35"): ("0.00", Confidence.PARTIAL),
    }
    def truth_fn(state, district):
        return seats.get((state, district), ("0.00", Confidence.INSUFFICIENT))
    return truth_fn

def _run(label, *, state, district, claimed_total):
    result = build_graph().invoke({
        "truth_fn": _demo_oracle(),
        "state": state,
        "district": district,
        "claimed_total": claimed_total,
        "retries": 0,
        "trace": []
    })
    print(f"\n{label}: {state}-{district} claimed={claimed_total}")
    for line in result["trace"]:
        print(f"  {line}")
    print(f"  => {result['final_confidence'].value}")

if __name__ == "__main__":
    _run("verified high", state="NY", district="14", claimed_total="2841577.19")
    _run("mismatch -> insufficient", state="NY", district="14", claimed_total="99999999.00")
    _run("partial", state="TX", district="35", claimed_total="0.00")
    print("\n" + build_graph().get_graph().draw_mermaid())
