"""The review: classify, stop to ask, then plan.

A LangGraph graph with one interrupt. Everywhere else in Sift "asks rather than
guesses" means asking the filesystem; here it means asking the person, because
some facts were never written to the disk. Whether last year's client folder
still matters is not recoverable by any amount of scanning.

The interrupt is the reason this is a graph rather than three function calls. It
pauses mid-run with its state intact, waits, and continues — the survey is not
walked again and nothing is re-classified.
"""

from __future__ import annotations

from typing import Annotated, Any, TypedDict, cast

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt
from pydantic import BaseModel

from sift.classify import classify
from sift.models import Candidate, Classification, Plan, ScanNode, Verdict
from sift.plan import build_plan

ASK_ABOVE = 0.02
"""A question has to be worth the interruption: at least this share of the survey.

A tool that asks about everything is a tool nobody answers, and every question it
spends on something trivial makes the next one likelier to be waved through.
"""


class Question(BaseModel):
    """What Sift could not work out on its own."""

    path: str
    asking: str
    contains: list[str]
    size_bytes: int


def _merge(existing: dict[str, str] | None, incoming: dict[str, str]) -> dict[str, str]:
    return {**(existing or {}), **incoming}


class Review(TypedDict, total=False):
    tree: ScanNode
    candidates: list[Candidate]
    judgements: list[Classification]
    answers: Annotated[dict[str, str], _merge]
    plan: Plan


def _judge(state: Review) -> Review:
    return {"judgements": classify(state["candidates"])}


def _worth_asking(
    judgements: list[Classification], candidates: list[Candidate], floor: int
) -> list[Classification]:
    """Only what is genuinely unresolved and big enough to matter."""
    offered = {candidate.path: candidate for candidate in candidates}
    return [
        judgement
        for judgement in judgements
        if judgement.verdict is Verdict.REVIEW
        and judgement.size_bytes >= floor
        and judgement.path in offered
    ]


def _ask(state: Review) -> Command[Any]:
    tree = state["tree"]
    floor = int(tree.size_bytes * ASK_ABOVE)
    unresolved = _worth_asking(state["judgements"], state["candidates"], floor)
    if not unresolved:
        return Command(goto="plan")

    by_path = {candidate.path: candidate for candidate in state["candidates"]}
    questions = [
        Question(
            path=str(judgement.path),
            asking=judgement.reason,
            contains=[file.name for file in by_path[judgement.path].largest_files],
            size_bytes=judgement.size_bytes,
        )
        for judgement in unresolved
    ]

    # Everything stops here. The graph keeps its state, so answering continues the
    # same run rather than starting a new one.
    replies = cast(dict[str, str], interrupt([q.model_dump() for q in questions]))
    return Command(goto="plan", update={"answers": replies})


def _plan(state: Review) -> Review:
    answers = state.get("answers") or {}
    judged = [_settled(j, answers.get(str(j.path))) for j in state["judgements"]]
    return {"judgements": judged, "plan": build_plan(state["tree"], judged)}


def _settled(judgement: Classification, answer: str | None) -> Classification:
    """Apply what the person said. Their answer outranks the model's guess."""
    if not answer:
        return judgement
    if answer == "keep":
        return judgement.model_copy(
            update={
                "verdict": Verdict.IRREPLACEABLE,
                "reason": "You said this still matters.",
                "restore": "cannot be restored",
            }
        )
    return judgement.model_copy(
        update={
            "verdict": Verdict.REGENERABLE,
            "reason": "You said this is no longer needed.",
            "restore": "cannot be restored once quarantine is emptied",
        }
    )


def build_review() -> Any:
    graph = StateGraph(Review)
    graph.add_node("judge", _judge)
    graph.add_node("ask", _ask)
    graph.add_node("plan", _plan)
    graph.add_edge(START, "judge")
    graph.add_edge("judge", "ask")
    graph.add_edge("plan", END)
    # A checkpointer is what makes the interrupt resumable rather than fatal.
    return graph.compile(checkpointer=InMemorySaver())
