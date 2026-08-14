"""Steps for tests/features/duplicates.feature."""

from __future__ import annotations

import os
import time
from pathlib import Path

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from sift.duplicates import Report, find_duplicates
from sift.models import ScanNode, Verdict
from sift.survey import survey
from tests.machine import Machine

scenarios("duplicates.feature")


@pytest.fixture
def judged() -> str | None:
    """Nothing has been judged, unless a scenario says so."""
    return None


@given(parsers.parse('"{relpath}" has been judged to rebuild itself'), target_fixture="judged")
def judged_regenerable(relpath: str) -> str:
    return relpath


@given(parsers.parse('"{relpath}" is the older of the two'))
def is_the_older(machine: Machine, relpath: str) -> None:
    # Which one is kept turns on mtime, so leaving them the same age makes the
    # scenario pass or fail on the order the filesystem happened to report.
    yesterday = time.time() - 86_400
    os.utime(machine.path(relpath), (yesterday, yesterday))


@when("I look for duplicates", target_fixture="report")
def i_look_for_duplicates(machine: Machine, judged: str | None) -> Report:
    tree = list(survey(machine.root, home=machine.root))[-1]
    # What the classifier writes back once the model has answered. A cache the
    # catalog names is pruned during the walk and never reaches here; a folder the
    # model judged is fully in the tree, which is where the overlap lives.
    if judged:
        _mark(tree, machine.path(judged), Verdict.REGENERABLE)
    return find_duplicates(tree)


def _mark(tree: ScanNode, path: Path, verdict: Verdict) -> None:
    stack = [tree]
    while stack:
        node = stack.pop()
        if node.path == path:
            node.verdict = verdict
            return
        stack.extend(node.children)
    raise KeyError(f"{path} was not in the survey")


def _pair(report: Report, machine: Machine, one: str, two: str) -> bool:
    first, second = machine.path(one), machine.path(two)
    return any({first, second} <= {found.keep, *found.copies} for found in report.duplicates)


@then(parsers.parse('"{one}" and "{two}" are the same file'))
def are_the_same_file(report: Report, machine: Machine, one: str, two: str) -> None:
    assert _pair(report, machine, one, two), (
        f"{one} and {two} hold the same bytes but were not paired"
    )


@then(parsers.parse('"{one}" and "{two}" are not the same file'))
def are_not_the_same_file(report: Report, machine: Machine, one: str, two: str) -> None:
    assert not _pair(report, machine, one, two)


@then(parsers.parse('"{relpath}" is not a duplicate of either'))
def not_a_duplicate_of_either(report: Report, machine: Machine, relpath: str) -> None:
    path = machine.path(relpath)
    assert not any(path in {found.keep, *found.copies} for found in report.duplicates), (
        f"{relpath} holds different bytes and should not be in any set"
    )


@then("one of them is reported as reclaimable")
def one_is_reclaimable(report: Report) -> None:
    assert report.duplicates
    assert all(found.copies for found in report.duplicates)


@then("far fewer files were read than the survey holds")
def far_fewer_read(report: Report) -> None:
    # The point of matching on size first: opening everything would cost more than
    # the survey did.
    assert report.files_read < report.files_surveyed / 2, (
        f"read {report.files_read} of {report.files_surveyed} files"
    )


@then("the reclaimable copy is not the oldest one")
def copy_is_not_the_oldest(report: Report) -> None:
    for found in report.duplicates:
        oldest = min([found.keep, *found.copies], key=lambda path: path.stat().st_mtime)
        assert found.keep == oldest, "the original should be kept, not a copy"


@then("what could be reclaimed is the size of one copy, not both")
def reclaimable_is_one_copy(report: Report) -> None:
    for found in report.duplicates:
        assert found.reclaimable_bytes == found.size_bytes * len(found.copies)
        assert found.reclaimable_bytes < found.size_bytes * (len(found.copies) + 1)


def _all(tree: ScanNode) -> list[ScanNode]:
    found, stack = [], [tree]
    while stack:
        node = stack.pop()
        found.append(node)
        stack.extend(node.children)
    return found


@then(parsers.parse('nothing inside "{relpath}" is offered as a copy'))
def nothing_inside_is_offered(report: Report, machine: Machine, relpath: str) -> None:
    inside = machine.path(relpath)
    offered = [copy for found in report.duplicates for copy in found.copies]
    assert not [c for c in offered if inside in c.parents], (
        f"a copy inside {relpath} was offered again, and {relpath} is already going "
        "whole — approving both promises the same bytes twice"
    )
