"""Steps for tests/features/reclaim.feature.

Real moves on a real temp filesystem. Nothing here is simulated: if a scenario
passes, the bytes actually moved and actually came back.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from sift.models import ScanNode, Verdict
from sift.quarantine import Protected, Quarantine, Receipt
from sift.survey import survey
from tests.machine import Machine

scenarios("reclaim.feature")


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
