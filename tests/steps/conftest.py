"""The realistic machine every scenario runs against, plus the steps both features share."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from pytest_bdd import given, parsers, then, when

from sift.models import ScanNode
from sift.scanner import walk
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
    return list(walk(machine.root))


@then("the survey total matches every file that was written")
def total_matches(reports: list[ScanNode], machine: Machine) -> None:
    assert tree_of(reports).size_bytes == machine.readable_bytes


@then(parsers.parse('the survey includes "{relpath}"'))
def survey_includes(reports: list[ScanNode], machine: Machine, relpath: str) -> None:
    assert node_at(tree_of(reports), machine.path(relpath)) is not None


@then(parsers.parse('"{relpath}" is absent from the survey'))
def absent_from_survey(reports: list[ScanNode], machine: Machine, relpath: str) -> None:
    assert node_at(tree_of(reports), machine.path(relpath)) is None
