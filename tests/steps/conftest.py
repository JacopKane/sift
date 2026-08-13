"""Shared fixtures, helpers, and Given steps for the scanner features."""

from __future__ import annotations

import os
from collections.abc import Iterator
from pathlib import Path

import pytest
from pytest_bdd import given, parsers

from sift.models import ScanNode

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


def index_of(reports: list[ScanNode], relpath: str, root: Path) -> int:
    target = root / relpath
    for position, node in enumerate(reports):
        if node.path == target:
            return position
    raise AssertionError(f"{relpath!r} was never reported")


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
