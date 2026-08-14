"""Steps for tests/features/api.feature.

Real HTTP against the real app over a real temp filesystem. The only thing not
exercised here is the model, because these run on every commit.
"""

from __future__ import annotations

import json
from typing import Any, cast

from fastapi.testclient import TestClient
from pytest_bdd import parsers, scenarios, then, when

from sift.api import create_app
from tests.machine import Machine

scenarios("api.feature")


def _events(raw: str) -> list[dict[str, Any]]:
    """Parse an SSE body into ordered (event, data) records."""
    parsed: list[dict[str, Any]] = []
    # SSE frames are separated by a blank line, which on the wire is \r\n\r\n.
    for block in raw.replace("\r\n", "\n").strip().split("\n\n"):
        name, payload = None, None
        for line in block.splitlines():
            if line.startswith("event:"):
                name = line[len("event:") :].strip()
            elif line.startswith("data:"):
                payload = line[len("data:") :].strip()
        if name and payload:
            parsed.append({"event": name, "data": json.loads(payload)})
    return parsed


@when("the browser surveys the machine", target_fixture="events")
def browser_surveys(machine: Machine) -> list[dict[str, Any]]:
    client = TestClient(create_app(home=machine.root))
    response = client.get("/api/survey", params={"root": str(machine.root)})
    assert response.status_code == 200
    return _events(response.text)


@when("the browser surveys the machine and asks the model", target_fixture="events")
def browser_surveys_and_judges(machine: Machine) -> list[dict[str, Any]]:
    client = TestClient(create_app(home=machine.root))
    response = client.get("/api/survey", params={"root": str(machine.root), "judge": True})
    assert response.status_code == 200
    return _events(response.text)


def _chart_nodes(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    done = next(e["data"] for e in events if e["event"] == "done")
    found: list[dict[str, Any]] = []
    stack = [done["chart"]]
    while stack:
        node = stack.pop()
        found.append(node)
        stack.extend(node["children"])
    return found


@then(parsers.parse('the map shows a verdict for "{relpath}"'))
def map_shows_verdict(events: list[dict[str, Any]], machine: Machine, relpath: str) -> None:
    wanted = str(machine.path(relpath))
    node = next((n for n in _chart_nodes(events) if n["path"] == wanted), None)
    assert node is not None, f"{relpath} is not on the map"
    assert node["verdict"] is not None, (
        f"{relpath} was judged but the map shows it as unknown, so it draws in grey"
    )


@then("the map is not a single colour")
def map_is_not_one_colour(events: list[dict[str, Any]]) -> None:
    verdicts = {node["verdict"] for node in _chart_nodes(events)}
    assert len(verdicts - {None}) > 1, (
        f"the whole map draws in one colour; verdicts present: {verdicts}"
    )


@then("the plan the browser receives accounts for no more than was surveyed")
def served_plan_adds_up(events: list[dict[str, Any]]) -> None:
    plan = _plan(events)
    claimed = sum(item["size_bytes"] for item in [*plan["proposals"], *plan["protected"]])
    assert claimed <= plan["surveyed_bytes"], (
        f"the served plan claims {claimed} bytes of a {plan['surveyed_bytes']} byte "
        "survey, so colouring the tree made something count twice"
    )


@when("the browser opens the app", target_fixture="page")
def browser_opens_app(machine: Machine) -> str:
    client = TestClient(create_app(home=machine.root))
    response = client.get("/")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    return response.text


def _reports(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [e["data"] for e in events if e["event"] == "directory"]


def _plan(events: list[dict[str, Any]]) -> dict[str, Any]:
    done = [e["data"] for e in events if e["event"] == "done"]
    assert len(done) == 1, f"expected exactly one completion event, got {len(done)}"
    return cast(dict[str, Any], done[0]["plan"])


def _report_for(events: list[dict[str, Any]], machine: Machine, relpath: str) -> dict[str, Any]:
    wanted = str(machine.path(relpath))
    found = next((r for r in _reports(events) if r["path"] == wanted), None)
    assert found is not None, f"the browser was never told about {relpath}"
    return found


@then(parsers.parse('it is told about "{relpath}"'))
def told_about(events: list[dict[str, Any]], machine: Machine, relpath: str) -> None:
    _report_for(events, machine, relpath)


@then("it is never told about individual files")
def never_told_about_files(events: list[dict[str, Any]], machine: Machine) -> None:
    reported = {r["path"] for r in _reports(events)}
    assert str(machine.path("Downloads/installer.dmg")) not in reported
    assert str(machine.path("Sites/client-app/package.json")) not in reported


@then(parsers.parse('the report for "{relpath}" says regenerable'))
def report_says_regenerable(events: list[dict[str, Any]], machine: Machine, relpath: str) -> None:
    assert _report_for(events, machine, relpath)["verdict"] == "regenerable"


@then(parsers.parse('the report for "{relpath}" says how to restore it'))
def report_says_how(events: list[dict[str, Any]], machine: Machine, relpath: str) -> None:
    assert _report_for(events, machine, relpath)["restore"]


def _chart_paths(events: list[dict[str, Any]]) -> set[str]:
    done = next(e["data"] for e in events if e["event"] == "done")
    paths: set[str] = set()

    def walk(node: dict[str, Any]) -> None:
        paths.add(node["path"])
        for child in node["children"]:
            walk(child)

    walk(done["chart"])
    return paths


@then(parsers.parse('the map includes "{relpath}"'))
def map_includes(events: list[dict[str, Any]], machine: Machine, relpath: str) -> None:
    assert str(machine.path(relpath)) in _chart_paths(events)


@then("the map leaves out files too small to see")
def map_leaves_out_slivers(events: list[dict[str, Any]], machine: Machine) -> None:
    # 3 KB against a 14 MB survey is far thinner than a pixel; drawing it would add
    # an unclickable sliver and nothing else.
    assert str(machine.path("Downloads/invoice-2024-01.pdf")) not in _chart_paths(events)


@then("the survey finishes with a plan")
def finishes_with_a_plan(events: list[dict[str, Any]]) -> None:
    assert events[-1]["event"] == "done"
    _plan(events)


@then(parsers.parse('the plan proposes reclaiming "{label}"'))
def plan_proposes(events: list[dict[str, Any]], label: str) -> None:
    labels = [item["label"] for item in _plan(events)["proposals"]]
    assert label in labels, labels


@then("the plan totals what is safe to reclaim")
def plan_totals(events: list[dict[str, Any]]) -> None:
    plan = _plan(events)
    assert plan["reclaimable_bytes"] > 0
    assert plan["reclaimable_bytes"] < plan["surveyed_bytes"]


@then("directories are reported before the plan")
def directories_before_plan(events: list[dict[str, Any]]) -> None:
    names = [event["event"] for event in events]
    assert names.index("directory") < names.index("done")


@then("it receives an HTML page")
def receives_html(page: str) -> None:
    assert "<!doctype html" in page.lower() or "<html" in page.lower()


@then("the page names the product")
def page_names_product(page: str) -> None:
    assert "Sift" in page
