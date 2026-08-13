"""Steps for tests/features/ask.feature. These call the real model."""

from __future__ import annotations

import pytest
from pytest_bdd import parsers, scenarios, then, when

from sift.ask import Selection, ask
from sift.config import settings
from sift.models import ScanNode
from tests.machine import Machine
from tests.steps.conftest import CallCounter, tree_of

scenarios("ask.feature")


@when(parsers.parse('I ask to "{prompt}"'), target_fixture="answer")
def i_ask_to(reports: list[ScanNode], prompt: str, counter: CallCounter) -> Selection:
    if not settings().api_key:
        pytest.skip(f"no API key configured for provider {settings().provider}")
    return ask(tree_of(reports), prompt, config={"callbacks": [counter]})


@then(parsers.parse('the answer selects "{relpath}"'))
def answer_selects(answer: Selection, machine: Machine, relpath: str) -> None:
    assert machine.path(relpath) in answer.paths, (
        f"{relpath} was not selected; got {[str(p) for p in answer.paths]}"
    )


@then(parsers.parse('the answer leaves "{relpath}" alone'))
def answer_leaves_alone(answer: Selection, machine: Machine, relpath: str) -> None:
    assert machine.path(relpath) not in answer.paths


@then(parsers.parse('the answer selects nothing inside "{relpath}"'))
def selects_nothing_inside(answer: Selection, machine: Machine, relpath: str) -> None:
    boundary = machine.path(relpath)
    inside = [p for p in answer.paths if boundary == p or boundary in p.parents]
    assert not inside, f"selected protected paths: {[str(p) for p in inside]}"


@then("the answer says what it refused")
def answer_says_what_it_refused(answer: Selection) -> None:
    assert answer.refused or "protect" in answer.reason.lower(), (
        "asking for something protected should be acknowledged, not silently dropped"
    )


@then("the answer gives a reason")
def answer_gives_a_reason(answer: Selection) -> None:
    assert answer.reason.strip()


@then("the answer selects nothing")
def answer_selects_nothing(answer: Selection) -> None:
    assert not answer.paths, f"nothing here matches, yet it chose {answer.paths}"


@then(parsers.parse("it took no more than {limit:d} model calls"))
def took_no_more_than(answer: Selection, counter: CallCounter, limit: int) -> None:
    # Cost is a property worth failing over. An uncapped agent kept searching for
    # something that was not there and spent minutes and hundreds of requests
    # doing it.
    assert counter.calls <= limit, f"one question cost {counter.calls} model calls"
