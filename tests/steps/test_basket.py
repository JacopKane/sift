"""Steps for tests/features/basket.feature."""

from __future__ import annotations

import pytest
from pytest_bdd import parsers, scenarios, then, when

from sift.basket import Basket, item_for
from sift.models import ScanNode
from sift.quarantine import Protected, Quarantine, Receipt
from tests.machine import Machine

scenarios("basket.feature")


@pytest.fixture
def basket() -> Basket:
    return Basket()


@when(parsers.parse('I put "{relpath}" in the basket'))
def i_put_in_the_basket(basket: Basket, machine: Machine, surveyed: ScanNode, relpath: str) -> None:
    basket.add(item_for(surveyed, machine.path(relpath)))


@when(parsers.parse('I insist on putting "{relpath}" in the basket'))
def i_insist(basket: Basket, machine: Machine, surveyed: ScanNode, relpath: str) -> None:
    basket.add(item_for(surveyed, machine.path(relpath), overridden=True))


@when(parsers.parse('I try to put "{relpath}" in the basket'), target_fixture="warning")
def i_try_to_put(
    basket: Basket, machine: Machine, surveyed: ScanNode, relpath: str
) -> Exception | None:
    try:
        basket.add(item_for(surveyed, machine.path(relpath)))
    except Protected as refused:
        return refused
    return None


@when("I empty the basket", target_fixture="receipt")
def i_empty_the_basket(basket: Basket, held: Quarantine) -> Receipt:
    return basket.empty_into(held)


@then(parsers.parse('it warns that "{relpath}" cannot be replaced'))
def it_warns(warning: Exception | None, relpath: str) -> None:
    assert isinstance(warning, Protected)
    assert "cannot be replaced" in str(warning)
    assert relpath.split("/")[-1] in str(warning)


@then("the receipt records that it was overridden")
def receipt_records_override(receipt: Receipt) -> None:
    assert any(entry.overridden for entry in receipt.moved), (
        "forcing a protected delete has to be visible on the receipt afterwards"
    )


@then("it reports freeing what the basket held")
def reports_freeing_the_basket(receipt: Receipt) -> None:
    assert receipt.freed_bytes == sum(entry.size_bytes for entry in receipt.moved)
    assert receipt.freed_bytes > 0
