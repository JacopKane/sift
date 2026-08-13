"""Filesystem walk.

Pure library: imports nothing from the web, AI, or config layers, so it stays
portable to a CLI or a native shell.
"""

from __future__ import annotations

import os
from collections import deque
from collections.abc import Collection, Generator, Iterator
from pathlib import Path

from sift.models import ScanNode

_BLOCK_SIZE = 512
"""``st_blocks`` is reported in 512-byte units regardless of the filesystem's own
block size — a POSIX quirk, not a value to derive from the filesystem."""


def walk(root: Path, exclude: Collection[Path] = ()) -> Iterator[ScanNode]:
    """Report each entry under *root* the moment its size is known.

    Children are always reported before their parent, because a directory's size
    isn't known until everything beneath it has been counted. The root is
    therefore reported last, and carries the assembled tree.

    Anything in *exclude* is skipped without being opened, and never appears in
    the tree. See :func:`sift.scanner.roots.boot_volume_exclusions` for the set a
    whole-volume scan needs.
    """
    yield from _walk_dir(Path(root), frozenset(Path(path) for path in exclude))


def scan(root: Path, exclude: Collection[Path] = ()) -> ScanNode:
    """Drain :func:`walk` and return the finished tree.

    For callers with no use for progress — tests, and anything that needs the
    whole picture before it can start.
    """
    return deque(walk(root, exclude), maxlen=1)[0]


def _walk_dir(path: Path, exclude: frozenset[Path]) -> Generator[ScanNode, None, ScanNode]:
    """Yield everything under *path*, then *path* itself, and return it.

    The return value is what lets a parent accumulate a child's totals without
    having to guess which of the yielded nodes was the subtree root.
    """
    node = ScanNode(
        path=path,
        name=path.name,
        is_dir=True,
        size_bytes=0,
        allocated_bytes=0,
    )

    try:
        entries = list(os.scandir(path))
    except PermissionError:
        # Expected on macOS for TCC-gated directories. The node is still reported
        # so the tree keeps its shape and the UI can offer a grant button rather
        # than silently losing the branch.
        node.unreadable = True
        yield node
        return node

    for entry in entries:
        entry_path = Path(entry.path)

        # Checked before anything else so an excluded path is never opened, even
        # to ask what it is.
        if entry_path in exclude:
            continue

        # Symlinks are skipped rather than followed: following them double-counts
        # the target and can escape the scan root entirely.
        if entry.is_symlink():
            continue

        if entry.is_dir():
            child = yield from _walk_dir(entry_path, exclude)
        else:
            child = _scan_file(entry)
            yield child

        node.children.append(child)
        node.size_bytes += child.size_bytes
        node.allocated_bytes += child.allocated_bytes

    yield node
    return node


def _scan_file(entry: os.DirEntry[str]) -> ScanNode:
    stat = entry.stat(follow_symlinks=False)
    return ScanNode(
        path=Path(entry.path),
        name=entry.name,
        is_dir=False,
        size_bytes=stat.st_size,
        allocated_bytes=stat.st_blocks * _BLOCK_SIZE,
    )
