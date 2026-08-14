"""Steps for tests/features/basket.feature."""

from __future__ import annotations

import pytest
from pytest_bdd import parsers, scenarios, then, when

from sift.basket import Basket, item_for
from sift.models import ScanNode, Verdict
from sift.quarantine import Quarantine, Receipt
from tests.machine import Machine

scenarios("basket.feature")


@pytest.fixture
def basket() -> Basket:
    return Basket()


@when(parsers.parse('I put "{relpath}" in the basket'))
def i_put_in_the_basket(basket: Basket, machine: Machine, surveyed: ScanNode, relpath: str) -> None:
    basket.add(item_for(surveyed, machine.path(relpath)))


@when("I empty the basket", target_fixture="receipt")
def i_empty_the_basket(basket: Basket, held: Quarantine) -> Receipt:
    return basket.empty_into(held)


@when("something in the basket disappears before it is emptied")
def something_disappears(basket: Basket, machine: Machine) -> None:
    # A file moved or deleted by something else between choosing it and acting on
    # it. Rare, and exactly when a half-finished job hurts most.
    import shutil

    shutil.rmtree(machine.path("Library/Caches"))


@then("everything that could move did")
def everything_that_could_moved(receipt: Receipt, machine: Machine) -> None:
    assert receipt.moved, "one failure stopped the whole basket"
    assert not machine.path("Sites/client-app/node_modules").exists()


@then("the receipt says what could not")
def receipt_says_what_could_not(receipt: Receipt) -> None:
    assert receipt.refused, "a silent partial success is worse than a reported failure"


@then(parsers.parse('the basket says "{name}" cannot be replaced'))
def basket_says_cannot_be_replaced(basket: Basket, name: str) -> None:
    chosen = [item for item in basket.items if item.path.name == name]
    assert chosen, f"{name} never made it into the basket"
    assert all(item.verdict is Verdict.IRREPLACEABLE for item in chosen), (
        f"{name} went in unlabelled — the verdict is the only thing telling you what you picked"
    )


@then(parsers.parse('the receipt records "{name}" as irreplaceable'))
def receipt_records_verdict(receipt: Receipt, name: str) -> None:
    entries = [entry for entry in receipt.moved if entry.original.name == name]
    assert entries, f"{name} is not on the receipt"
    assert all(entry.verdict is Verdict.IRREPLACEABLE for entry in entries), (
        "what a thing was judged to be has to survive onto the receipt, or an undo "
        "later is a list of paths with no way to tell which mattered"
    )


@then("it reports freeing what the basket held")
def reports_freeing_the_basket(receipt: Receipt) -> None:
    assert receipt.freed_bytes == sum(entry.size_bytes for entry in receipt.moved)
    assert receipt.freed_bytes > 0
