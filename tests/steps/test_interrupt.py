"""Steps for tests/features/interrupt.feature.

The graph runs for real, interrupt and all. Answering resumes the same thread,
which is the whole point of the checkpointer.
"""

from __future__ import annotations

from typing import Any

import pytest
from langgraph.types import Command
from pytest_bdd import parsers, scenarios, then, when

from sift.config import settings
from sift.models import ScanNode, Verdict
from sift.review import ASK_ABOVE, Question, build_review
from sift.survey import candidates_for_model
from tests.machine import Machine

scenarios("interrupt.feature")

THREAD = {"configurable": {"thread_id": "test"}}


class Run:
    """A review in progress, and how many times the survey was consulted."""

    def __init__(self, tree: ScanNode) -> None:
        self.graph = build_review()
        self.tree = tree
        self.surveys = 1
        self.state: dict[str, Any] = {}
        self.asked: set[str] = set()

    @property
    def questions(self) -> list[Question]:
        raw = self.state.get("__interrupt__")
        if not raw:
            return []
        return [Question.model_validate(entry) for entry in raw[0].value]

    def start(self, candidates: list) -> None:
        self.state = self.graph.invoke({"tree": self.tree, "candidates": candidates}, config=THREAD)

    def answer(self, replies: dict[str, str]) -> None:
        self.asked |= set(replies)
        self.state = self.graph.invoke(Command(resume=replies), config=THREAD)


@when("the review runs", target_fixture="run")
def the_review_runs(machine: Machine, surveyed: ScanNode) -> Run:
    if not settings().api_key:
        pytest.skip(f"no API key configured for provider {settings().provider}")
    run = Run(surveyed)
    run.start(candidates_for_model(surveyed))
    return run


@when("the review runs over things the rules already settled", target_fixture="run")
def review_over_settled(surveyed: ScanNode) -> Run:
    # No candidates at all: everything was named by a rule, so there is nothing to
    # classify and nothing to ask about. This must not call a model.
    run = Run(surveyed)
    run.start([])
    return run


@when("I answer that everything asked about is finished with")
def answer_all_discard(run: Run) -> None:
    run.answer({question.path: "discard" for question in run.questions})


@when("I answer that everything asked about still matters")
def answer_all_keep(run: Run) -> None:
    run.answer({question.path: "keep" for question in run.questions})


@then("it finishes without asking anything")
def finishes_without_asking(run: Run) -> None:
    assert not run.questions
    assert run.state.get("plan") is not None


@then("everything unresolved and worth asking about was asked about")
def everything_unresolved_was_asked(run: Run) -> None:
    floor = int(run.tree.size_bytes * ASK_ABOVE)
    should = {
        str(j.path)
        for j in run.state["judgements"]
        if j.verdict is Verdict.REVIEW and j.size_bytes >= floor
    }
    asked = {question.path for question in run.questions}
    assert asked == should, f"asked about {asked}, should have asked about {should}"


@then("nothing already settled by a rule was asked about")
def nothing_settled_was_asked(run: Run) -> None:
    settled = {str(node.path) for node in _nodes(run.tree) if node.verdict is not None}
    for question in run.questions:
        assert question.path not in settled, f"{question.path} was already settled"


@then("every question says what is inside what it asks about")
def every_question_says_contents(run: Run) -> None:
    for question in run.questions:
        assert question.contains, "a question with no contents is unanswerable"
        assert question.asking.strip()


@then("no plan is produced while it is waiting")
def no_plan_while_waiting(run: Run) -> None:
    if not run.questions:
        return  # nothing was ambiguous this run; there is nothing to wait for
    assert run.state.get("plan") is None, "the graph planned before the answer arrived"


@then("the run finishes")
def the_run_finishes(run: Run) -> None:
    assert run.state.get("plan") is not None
    assert not run.questions


@then(parsers.parse("everything I was asked about ends up {verdict}"))
def everything_ends_up(run: Run, verdict: str) -> None:
    if not run.asked:
        pytest.skip("nothing was ambiguous this run, so there is nothing to check")
    for path in run.asked:
        judged = next(j for j in run.state["judgements"] if str(j.path) == path)
        assert judged.verdict is Verdict(verdict)


@then("none of it is proposed for deletion")
def none_proposed(run: Run) -> None:
    proposed = {str(p) for item in run.state["plan"].proposals for p in item.paths}
    assert not (run.asked & proposed)


@then("the survey was not walked a second time")
def survey_walked_once(run: Run) -> None:
    assert run.surveys == 1, "resuming should continue the run, not restart it"


def _nodes(tree: ScanNode) -> list[ScanNode]:
    found, stack = [], [tree]
    while stack:
        node = stack.pop()
        found.append(node)
        stack.extend(node.children)
    return found
