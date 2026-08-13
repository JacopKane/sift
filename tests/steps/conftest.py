"""The realistic machine every scenario runs against, plus the steps both features share."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from langchain_core.callbacks import BaseCallbackHandler
from pytest_bdd import given, parsers, then, when

from sift.classify import classify
from sift.config import settings
from sift.models import Classification, ScanNode, Verdict
from sift.quarantine import Protected, Quarantine, Receipt
from sift.survey import candidates_for_model, survey
from tests import machine as machine_module
from tests.machine import Machine


@pytest.fixture
def machine(tmp_path: Path) -> Iterator[Machine]:
    if machine_module.running_as_root():
        pytest.skip("root bypasses directory permissions, so the locked directory wouldn't lock")
    root = tmp_path.resolve()
    built = machine_module.build(root)
    yield built
    machine_module.unlock(root)


# --------------------------------------------------------------- helpers ----


def all_nodes(tree: ScanNode) -> Iterator[ScanNode]:
    stack = [tree]
    while stack:
        node = stack.pop()
        yield node
        stack.extend(node.children)


def node_at(tree: ScanNode, path: Path) -> ScanNode | None:
    return next((node for node in all_nodes(tree) if node.path == path), None)


def tree_of(reports: list[ScanNode]) -> ScanNode:
    """The root is always reported last, and carries the assembled tree."""
    return reports[-1]


def index_of(reports: list[ScanNode], path: Path) -> int:
    for position, node in enumerate(reports):
        if node.path == path:
            return position
    raise AssertionError(f"{path} was never reported")


# ----------------------------------------------------------------- steps ----


@given("a machine that looks like a developer's Mac")
def a_developers_mac(machine: Machine) -> None:
    """Built by the `machine` fixture; this step exists to name it in Gherkin."""


@when("I survey the machine", target_fixture="reports")
def survey_the_machine(machine: Machine) -> list[ScanNode]:
    # The catalog is anchored at the machine root, so its ~/... rules resolve
    # against the fixture rather than against the real home directory.
    return list(survey(machine.root, home=machine.root))


class CallCounter(BaseCallbackHandler):
    """Counts real model invocations. Observation, not substitution."""

    def __init__(self) -> None:
        self.calls = 0

    def on_chat_model_start(self, *args: Any, **kwargs: Any) -> None:
        self.calls += 1

    def on_llm_start(self, *args: Any, **kwargs: Any) -> None:
        self.calls += 1


@pytest.fixture
def counter() -> CallCounter:
    return CallCounter()


@when("I ask the model about the candidates", target_fixture="classified")
def ask_the_model(reports: list[ScanNode], counter: CallCounter) -> list[Classification]:
    if not settings().api_key:
        pytest.skip(f"no API key configured for provider {settings().provider}")
    candidates = candidates_for_model(tree_of(reports))
    assert candidates, "the fixture should leave something for the model to judge"
    return classify(candidates, config={"callbacks": [counter]})


@then("the survey total matches every file that was written")
def total_matches(reports: list[ScanNode], machine: Machine) -> None:
    assert tree_of(reports).size_bytes == machine.readable_bytes


@then(parsers.parse('the survey includes "{relpath}"'))
def survey_includes(reports: list[ScanNode], machine: Machine, relpath: str) -> None:
    assert node_at(tree_of(reports), machine.path(relpath)) is not None


@then(parsers.parse('"{relpath}" is absent from the survey'))
def absent_from_survey(reports: list[ScanNode], machine: Machine, relpath: str) -> None:
    assert node_at(tree_of(reports), machine.path(relpath)) is None


@given("the machine has been surveyed", target_fixture="surveyed")
def the_machine_has_been_surveyed(machine: Machine) -> ScanNode:
    return list(survey(machine.root, home=machine.root))[-1]


@pytest.fixture
def held(machine: Machine) -> Quarantine:
    # Beside the machine rather than inside it, so quarantined bytes never appear
    # in a later survey of the same tree — but named after this machine, because
    # tmp_path.parent is shared across the whole run and a plain "quarantine"
    # there accumulates every scenario's moves.
    return Quarantine(machine.root.parent / f"quarantine-{machine.root.name}")


@pytest.fixture
def sizes_before(machine: Machine) -> dict[str, int]:
    return {str(path): path.stat().st_size for path in machine.root.rglob("*") if path.is_file()}


# ------------------------------------------- reclaiming and the basket ----


def _verdict_for(tree: ScanNode, path: Path) -> Verdict | None:
    stack = [tree]
    while stack:
        node = stack.pop()
        if node.path == path:
            return node.verdict
        stack.extend(node.children)
    return None


@when(parsers.parse('I reclaim "{relpath}"'), target_fixture="receipt")
def i_reclaim(
    held: Quarantine,
    machine: Machine,
    surveyed: ScanNode,
    sizes_before: dict[str, int],
    relpath: str,
) -> Receipt:
    target = machine.path(relpath)
    return held.reclaim(target, verdict=_verdict_for(surveyed, target))


@when(parsers.parse('I reclaim "{relpath}" but not "{kept}"'), target_fixture="receipt")
def i_reclaim_excluding(
    held: Quarantine, machine: Machine, sizes_before: dict[str, int], relpath: str, kept: str
) -> Receipt:
    return held.reclaim(machine.path(relpath), excluding=[machine.path(kept)])


@when(parsers.parse('I try to reclaim "{relpath}"'), target_fixture="refusal")
def i_try_to_reclaim(
    held: Quarantine, machine: Machine, surveyed: ScanNode, relpath: str
) -> Exception | None:
    target = machine.path(relpath)
    try:
        held.reclaim(target, verdict=_verdict_for(surveyed, target))
    except Protected as refused:
        return refused
    return None


@when("I undo", target_fixture="undone")
def i_undo(held: Quarantine) -> Receipt:
    return held.undo()


@then("it refuses")
def it_refuses(refusal: Exception | None) -> None:
    assert isinstance(refusal, Protected)


@then(parsers.parse('"{relpath}" is gone from where it was'))
def gone_from_where_it_was(machine: Machine, relpath: str) -> None:
    assert not machine.path(relpath).exists()


@then(parsers.parse('"{relpath}" is back where it was'))
def back_where_it_was(machine: Machine, relpath: str) -> None:
    assert machine.path(relpath).exists()


@then("it is sitting in quarantine")
def sitting_in_quarantine(held: Quarantine, receipt: Receipt) -> None:
    assert receipt.moved
    for entry in receipt.moved:
        assert entry.held_at.exists()


@then(parsers.parse('"{relpath}" is not in quarantine'))
def not_in_quarantine(held: Quarantine, machine: Machine, relpath: str) -> None:
    name = machine.path(relpath).name
    assert not any(slot.name.endswith(name) for slot in held.root.iterdir())


@then("nothing was deleted")
def nothing_was_deleted(held: Quarantine, sizes_before: dict[str, int]) -> None:
    # Every byte that was on the machine is still somewhere: either where it was,
    # or in quarantine. A move preserves them; a delete would not.
    surviving = sum(path.stat().st_size for path in held.root.rglob("*") if path.is_file())
    for original, size in sizes_before.items():
        if Path(original).exists():
            surviving += size
    assert surviving >= sum(sizes_before.values())


@then("it still holds everything it held before")
def still_holds_everything(machine: Machine, sizes_before: dict[str, int]) -> None:
    for original, size in sizes_before.items():
        path = Path(original)
        assert path.exists(), f"{original} did not come back"
        assert path.stat().st_size == size, f"{original} came back a different size"


@then("quarantine is empty")
def quarantine_is_empty(held: Quarantine) -> None:
    assert held.held() == []
    leftovers = [slot for slot in held.root.iterdir() if slot.name != "manifest.json"]
    assert not leftovers, f"quarantine still holds {leftovers}"


@then(parsers.parse("quarantine holds {count:d} items"))
def quarantine_holds(held: Quarantine, count: int) -> None:
    assert len(held.held()) == count


@then(parsers.parse('it reports freeing the size of "{relpath}"'))
def reports_freeing(receipt: Receipt, sizes_before: dict[str, int], relpath: str) -> None:
    expected = sum(size for original, size in sizes_before.items() if relpath in original)
    assert receipt.freed_bytes == expected, (
        f"reported freeing {receipt.freed_bytes} but the directory held {expected}"
    )
