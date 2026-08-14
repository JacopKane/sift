"""Steps for tests/features/places.feature.

The real endpoint against the real fixture: what comes back is checked against
what is on disk, not against a list written twice.
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from pytest_bdd import given, parsers, scenarios, then, when

from sift.api import create_app
from tests.machine import Machine

scenarios("places.feature")


@pytest.fixture
def client(machine: Machine) -> TestClient:
    return TestClient(create_app(home=machine.root))


@given(parsers.parse('"{relpath}" has been taken away'))
def taken_away(machine: Machine, relpath: str) -> None:
    shutil.rmtree(machine.path(relpath))


@when("the browser asks where it can look", target_fixture="places")
def browser_asks_where(client: TestClient) -> list[dict[str, Any]]:
    response = client.get("/api/places")
    assert response.status_code == 200, response.text
    return list(response.json()["places"])


@then("every place it is offered is really there")
def every_place_is_really_there(places: list[dict[str, Any]]) -> None:
    missing = [place["label"] for place in places if not Path(place["path"]).is_dir()]
    assert not missing, f"offered {missing}, which this machine does not have — dead buttons"


@then("it is offered somewhere to start")
def offered_somewhere(places: list[dict[str, Any]]) -> None:
    assert places, "the first screen asks a question with no answers on it"


@then("none of them is the whole disk")
def none_is_the_whole_disk(places: list[dict[str, Any]]) -> None:
    assert not [p for p in places if Path(p["path"]) == Path("/")], (
        "the whole disk is a forty-second scan behind a permission dialog; asking "
        "for it on purpose is fine, offering it first is a trap"
    )


@then(parsers.parse('"{label}" is not among them'))
def not_among_them(places: list[dict[str, Any]], label: str) -> None:
    assert label not in [place["label"] for place in places]
