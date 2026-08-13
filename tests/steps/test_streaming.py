"""Steps for tests/features/streaming.feature."""

from __future__ import annotations

from pathlib import Path

from pytest_bdd import parsers, scenarios, then, when

from sift.models import ScanNode
from sift.scanner import walk
from tests.steps.conftest import KB, index_of

scenarios("streaming.feature")


@when("I walk the root", target_fixture="reports")
def i_walk_the_root(root: Path) -> list[ScanNode]:
    return list(walk(root))


@then(parsers.parse('"{relpath}" is reported'))
def is_reported(reports: list[ScanNode], root: Path, relpath: str) -> None:
    index_of(reports, relpath, root)


@then(parsers.parse('"{earlier}" is reported before "{later}"'))
def reported_before(reports: list[ScanNode], root: Path, earlier: str, later: str) -> None:
    assert index_of(reports, earlier, root) < index_of(reports, later, root)


@then(parsers.parse('"{relpath}" is reported before the root'))
def reported_before_the_root(reports: list[ScanNode], root: Path, relpath: str) -> None:
    assert index_of(reports, relpath, root) < len(reports) - 1


@then("the last report is the root")
def last_report_is_the_root(reports: list[ScanNode], root: Path) -> None:
    assert reports[-1].path == root


@then(parsers.parse("the last report totals {size:d} KB"))
def last_report_totals(reports: list[ScanNode], size: int) -> None:
    assert reports[-1].size_bytes == size * KB
