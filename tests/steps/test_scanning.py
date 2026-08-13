"""Steps for tests/features/scanning.feature."""

from __future__ import annotations

import os
from collections.abc import Iterator
from pathlib import Path

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from sift.models import ScanNode
from sift.scanner import scan

scenarios("scanning.feature")

KB = 1024


@pytest.fixture
def root(tmp_path: Path) -> Iterator[Path]:
    """A scan root that is always left readable, so tmp cleanup can't fail."""
    resolved = tmp_path.resolve()
    yield resolved
    for path in sorted(resolved.rglob("*"), reverse=True):
        if path.is_dir() and not path.is_symlink():
            path.chmod(0o755)


def find(tree: ScanNode, relpath: str, root: Path) -> ScanNode:
    target = root / relpath
    stack = [tree]
    while stack:
        node = stack.pop()
        if node.path == target:
            return node
        stack.extend(node.children)
    raise AssertionError(f"{relpath!r} was not present in the scan")


# ----------------------------------------------------------------- given ----


@given(parsers.parse('a file "{relpath}" of {size:d} KB'))
def a_file(root: Path, relpath: str, size: int) -> None:
    path = root / relpath
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"\0" * (size * KB))


@given(parsers.parse('a directory "{relpath}"'))
def a_directory(root: Path, relpath: str) -> None:
    (root / relpath).mkdir(parents=True, exist_ok=True)


@given(parsers.parse('an unreadable directory "{relpath}"'))
def an_unreadable_directory(root: Path, relpath: str) -> None:
    if os.geteuid() == 0:
        pytest.skip("running as root bypasses directory permissions")
    path = root / relpath
    path.mkdir(parents=True, exist_ok=True)
    (path / "hidden.bin").write_bytes(b"\0" * KB)
    path.chmod(0o000)


@given(parsers.parse('a symlink "{link}" pointing at "{target}"'))
def a_symlink(root: Path, link: str, target: str) -> None:
    source = root / link
    source.parent.mkdir(parents=True, exist_ok=True)
    source.symlink_to(root / target)


# ------------------------------------------------------------------ when ----


@when("I scan the root", target_fixture="tree")
def i_scan_the_root(root: Path) -> ScanNode:
    return scan(root)


# ------------------------------------------------------------------ then ----


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
