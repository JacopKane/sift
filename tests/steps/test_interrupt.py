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
from sift.review import Question, build_review
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

    @property
    def questions(self) -> list[Question]:
        raw = self.state.get("__interrupt__")
        if not raw:
            return []
        return [Question.model_validate(entry) for entry in raw[0].value]

    def start(self, candidates: list) -> None:
        self.state = self.graph.invoke({"tree": self.tree, "candidates": candidates}, config=THREAD)

    def answer(self, replies: dict[str, str]) -> None:
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


@when(parsers.parse('I answer that "{relpath}" is old client work I no longer need'))
def answer_no_longer_needed(run: Run, machine: Machine, relpath: str) -> None:
    run.answer({str(machine.path(relpath)): "discard"})


@when(parsers.parse('I answer that "{relpath}" is work I still need'))
def answer_still_needed(run: Run, machine: Machine, relpath: str) -> None:
    run.answer({str(machine.path(relpath)): "keep"})


@then("it finishes without asking anything")
def finishes_without_asking(run: Run) -> None:
    assert not run.questions
    assert run.state.get("plan") is not None


@then(parsers.parse('it stops and asks about "{relpath}"'))
def stops_and_asks(run: Run, machine: Machine, relpath: str) -> None:
    asked = {question.path for question in run.questions}
    assert str(machine.path(relpath)) in asked, f"expected a question about {relpath}, got {asked}"


@then("the question says what is inside it")
def question_says_what_is_inside(run: Run) -> None:
    assert run.questions
    for question in run.questions:
        assert question.contains, "a question with no contents is unanswerable"
        assert question.asking.strip()


@then("no plan is produced while it is waiting")
def no_plan_while_waiting(run: Run) -> None:
    assert run.state.get("plan") is None, "the graph planned before the answer arrived"


@then("the run finishes")
def the_run_finishes(run: Run) -> None:
    assert run.state.get("plan") is not None
    assert not run.questions


@then(parsers.parse('"{relpath}" ends up {verdict}'))
def ends_up(run: Run, machine: Machine, relpath: str, verdict: str) -> None:
    wanted = machine.path(relpath)
    judged = next(j for j in run.state["judgements"] if j.path == wanted)
    assert judged.verdict is Verdict(verdict)


@then(parsers.parse('"{relpath}" is not proposed for deletion'))
def not_proposed_for_deletion(run: Run, machine: Machine, relpath: str) -> None:
    proposed = {path for item in run.state["plan"].proposals for path in item.paths}
    assert machine.path(relpath) not in proposed


@then("the survey was not walked a second time")
def survey_walked_once(run: Run) -> None:
    assert run.surveys == 1, "resuming should continue the run, not restart it"
