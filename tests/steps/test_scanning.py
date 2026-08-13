"""Steps for tests/features/scanning.feature."""

from __future__ import annotations

from pathlib import Path

from pytest_bdd import parsers, scenarios, then, when

from sift.models import ScanNode
from sift.scanner import scan
from tests.steps.conftest import KB, find

scenarios("scanning.feature")


@when("I scan the root", target_fixture="tree")
def i_scan_the_root(root: Path) -> ScanNode:
    return scan(root)


@then("the scan completes")
def the_scan_completes(tree: ScanNode) -> None:
    assert tree is not None


@then(parsers.parse('"{relpath}" reports {size:d} KB'))
def reports_size(tree: ScanNode, root: Path, relpath: str, size: int) -> None:
    node = find(tree, relpath, root)
    assert node.size_bytes == size * KB


@then(parsers.parse('"{relpath}" occupies at least {size:d} KB on disk'))
def occupies_at_least(tree: ScanNode, root: Path, relpath: str, size: int) -> None:
    node = find(tree, relpath, root)
    assert node.allocated_bytes >= size * KB


@then(parsers.parse('"{relpath}" has children "{names}"'))
def has_children(tree: ScanNode, root: Path, relpath: str, names: str) -> None:
    node = find(tree, relpath, root)
    expected = sorted(name.strip() for name in names.split(","))
    assert sorted(child.name for child in node.children) == expected


@then(parsers.parse('"{relpath}" is marked unreadable'))
def is_marked_unreadable(tree: ScanNode, root: Path, relpath: str) -> None:
    node = find(tree, relpath, root)
    assert node.unreadable is True
