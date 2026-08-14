"""Steps for tests/features/endpoints.feature.

Real HTTP against the real app, over a real temp filesystem, with quarantine
pointed somewhere disposable. Nothing here calls a model.
"""

from __future__ import annotations

import os
import time
from collections.abc import Iterator
from concurrent.futures import Future, ThreadPoolExecutor
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from pytest_bdd import given, parsers, scenarios, then, when

from sift.api import create_app
from tests.machine import Machine

scenarios("endpoints.feature")


@pytest.fixture
def client(machine: Machine) -> Iterator[TestClient]:
    # Entered as a context manager so every request in a scenario shares one
    # event loop, exactly as they would in the running app. A TestClient used
    # without this gives each request a loop of its own, which would hide the
    # very thing the responsiveness scenario is looking for.
    with TestClient(
        create_app(
            home=machine.root,
            quarantine=machine.root.parent / f"quarantine-{machine.root.name}",
        )
    ) as client:
        yield client


@when("the browser surveys the machine")
def browser_surveys_for_endpoints(client: TestClient, machine: Machine) -> None:
    response = client.get("/api/survey", params={"root": str(machine.root)})
    assert response.status_code == 200


@when(parsers.parse('the browser baskets "{relpath}"'), target_fixture="reply")
def browser_baskets(client: TestClient, machine: Machine, relpath: str) -> Any:
    return client.post(
        "/api/basket", json={"root": str(machine.root), "path": str(machine.path(relpath))}
    )


@when("the browser empties the basket", target_fixture="emptied")
def browser_empties(client: TestClient, machine: Machine) -> dict[str, Any]:
    response = client.post("/api/basket/empty", params={"root": str(machine.root)})
    assert response.status_code == 200, response.text
    return dict(response.json())


@when("the browser asks for duplicates", target_fixture="duplicates")
def browser_asks_duplicates(client: TestClient, machine: Machine) -> dict[str, Any]:
    response = client.get("/api/duplicates", params={"root": str(machine.root)})
    assert response.status_code == 200, response.text
    return dict(response.json())


@when("the browser sends a dropped folder", target_fixture="dropped")
def browser_sends_dropped(client: TestClient) -> dict[str, Any]:
    response = client.post(
        "/api/dropped",
        json={
            "name": "dropped-project",
            "files": [
                {"path": "package.json", "size_bytes": 2048},
                {"path": "node_modules/react/index.js", "size_bytes": 900_000},
                {"path": "src/main.ts", "size_bytes": 6000},
            ],
        },
    )
    assert response.status_code == 200, response.text
    return dict(response.json())


@then("the response says what was freed")
def response_says_freed(emptied: dict[str, Any]) -> None:
    assert emptied["freed_bytes"] > 0
    assert emptied["moved"]


@then("the browser can undo it")
def browser_can_undo(client: TestClient, machine: Machine) -> None:
    response = client.post("/api/undo")
    assert response.status_code == 200
    assert response.json()["restored"]
    assert machine.path("Sites/client-app/node_modules").exists()


@then("the basket says it cannot be replaced")
def basket_says_cannot_be_replaced(reply: Any) -> None:
    assert reply.status_code == 200, reply.text
    verdicts = [item["verdict"] for item in reply.json()["items"]]
    assert "irreplaceable" in verdicts, (
        f"it went in unlabelled: {verdicts} — the browser has nothing to colour it with"
    )


@then(parsers.parse("it is told about a set of {count:d} identical files"))
def told_about_a_set(duplicates: dict[str, Any], count: int) -> None:
    sets = duplicates["sets"]
    assert sets, "no duplicate sets were reported"
    assert any(1 + len(entry["copies"]) == count for entry in sets)


@then("it is told how much deleting the copies would free")
def told_how_much(duplicates: dict[str, Any]) -> None:
    assert duplicates["reclaimable_bytes"] > 0


@then("it gets back a plan for what was dropped")
def gets_a_plan_for_dropped(dropped: dict[str, Any]) -> None:
    labels = [item["label"] for item in dropped["plan"]["proposals"]]
    assert "node_modules" in labels, labels
    assert dropped["chart"]["name"] == "dropped-project"


@then("nothing on the server's disk was read")
def nothing_on_server_read(dropped: dict[str, Any]) -> None:
    # Every path in the answer is under the dropped folder's own name, so none of
    # it came from a real filesystem the server walked.
    def paths(node: dict[str, Any]) -> list[str]:
        found = [node["path"]]
        for child in node["children"]:
            found.extend(paths(child))
        return found

    for path in paths(dropped["chart"]):
        assert not Path(path).is_absolute(), f"{path} looks like a real filesystem path"


@then(parsers.parse('"{relpath}" is gone from where it was'))
def endpoint_gone(machine: Machine, relpath: str) -> None:
    assert not machine.path(relpath).exists()


@then(parsers.parse('"{relpath}" is back where it was'))
def endpoint_back(machine: Machine, relpath: str) -> None:
    assert machine.path(relpath).exists()


@given(parsers.parse("{count:d} large files, half of them copies of the other half"))
def large_duplicate_files(machine: Machine, count: int) -> None:
    """Enough bytes that hashing them takes long enough to notice.

    Real files with real random contents — the point is the time the hashing
    actually costs, which a stub could not spend.
    """
    folder = machine.root / "Footage"
    folder.mkdir(parents=True, exist_ok=True)
    for index in range(count // 2):
        blob = os.urandom(6 * 1024 * 1024)
        (folder / f"clip-{index}.mov").write_bytes(blob)
        (folder / f"clip-{index} copy.mov").write_bytes(blob)


@when("the browser starts looking for duplicates", target_fixture="scan")
def browser_starts_duplicates(client: TestClient, machine: Machine) -> Future[float]:
    pool = ThreadPoolExecutor(max_workers=2)

    def run() -> float:
        response = client.get("/api/duplicates", params={"root": str(machine.root)})
        assert response.status_code == 200, response.text
        return time.monotonic()

    return pool.submit(run)


@when("the browser asks for the page while that is still running", target_fixture="page")
def browser_asks_for_page(client: TestClient, scan: Future[float]) -> float:
    # Give the scan a head start so "finished first" cannot be a coincidence of
    # scheduling. If the request were being served on the event loop, this whole
    # call would queue behind it and arrive after.
    time.sleep(0.05)
    assert not scan.done(), "the duplicate scan finished too fast to prove anything"
    response = client.get("/")
    assert response.status_code == 200
    return time.monotonic()


@then("the page comes back before the duplicate scan does")
def page_comes_back_first(page: float, scan: Future[float]) -> None:
    assert page < scan.result(timeout=60), (
        "the page waited for the duplicate scan — a long job is holding the event loop, "
        "so the whole interface freezes while it runs"
    )
