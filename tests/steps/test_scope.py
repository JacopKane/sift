"""Steps for tests/features/scope.feature."""

from __future__ import annotations

from collections.abc import Collection
from pathlib import Path

from pytest_bdd import parsers, scenarios, then, when

from sift.models import ScanNode
from sift.scanner import boot_volume_exclusions, walk
from tests.machine import Machine
from tests.steps.conftest import all_nodes, tree_of

scenarios("scope.feature")


@when(parsers.parse('I survey "{relpath}"'), target_fixture="reports")
def survey_one_folder(machine: Machine, relpath: str) -> list[ScanNode]:
    return list(walk(machine.path(relpath)))


@when(parsers.parse('I survey the machine excluding "{relpath}"'), target_fixture="reports")
def survey_excluding(machine: Machine, relpath: str) -> list[ScanNode]:
    return list(walk(machine.root, exclude=[machine.path(relpath)]))


@when("I ask what a boot volume survey excludes", target_fixture="exclusions")
def ask_boot_volume_exclusions() -> Collection[Path]:
    return boot_volume_exclusions()


@then(parsers.parse('nothing outside "{relpath}" appears in the survey'))
def nothing_outside(reports: list[ScanNode], machine: Machine, relpath: str) -> None:
    boundary = machine.path(relpath)
    for node in all_nodes(tree_of(reports)):
        assert node.path == boundary or boundary in node.path.parents


@then("the survey total is less than surveying the whole machine")
def less_than_the_whole_machine(reports: list[ScanNode], machine: Machine) -> None:
    assert tree_of(reports).size_bytes < machine.readable_bytes


@then(parsers.parse('it excludes "{path}"'))
def it_excludes(exclusions: Collection[Path], path: str) -> None:
    assert Path(path) in exclusions
