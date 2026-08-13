"""Filesystem walk.

Pure library: imports nothing from the web, AI, or config layers, so it stays
portable to a CLI or a native shell.
"""

from __future__ import annotations

import os
from collections import deque
from collections.abc import Callable, Collection, Generator, Iterator
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from sift.models import ScanNode

_BLOCK_SIZE = 512
"""``st_blocks`` is reported in 512-byte units regardless of the filesystem's own
block size — a POSIX quirk, not a value to derive from the filesystem."""


Prune = Callable[[Path], bool]


def walk(
    root: Path,
    exclude: Collection[Path] = (),
    prune: Prune | None = None,
) -> Iterator[ScanNode]:
    """Report each entry under *root* the moment its size is known.

    Children are always reported before their parent, because a directory's size
    isn't known until everything beneath it has been counted. The root is
    therefore reported last, and carries the assembled tree.

    Anything in *exclude* is skipped without being opened, and never appears in
    the tree. See :func:`sift.scanner.roots.boot_volume_exclusions` for the set a
    whole-volume scan needs.

    *prune* is asked about each directory before it is entered. When it says yes,
    the directory's total is still counted exactly, but nothing inside it is
    reported or retained: the caller has already decided the contents don't
    matter. Measured on one real projects folder, that is the difference between
    building 1.7 million nodes and building a few thousand.
    """
    yield from _walk_dir(Path(root), frozenset(Path(path) for path in exclude), prune, depth=0)


def scan(
    root: Path,
    exclude: Collection[Path] = (),
    prune: Prune | None = None,
) -> ScanNode:
    """Drain :func:`walk` and return the finished tree.

    For callers with no use for progress — tests, and anything that needs the
    whole picture before it can start.
    """
    return deque(walk(root, exclude, prune), maxlen=1)[0]


def _walk_dir(
    path: Path,
    exclude: frozenset[Path],
    prune: Prune | None,
    depth: int,
) -> Generator[ScanNode, None, ScanNode]:
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

    # The root is never pruned: the caller asked to look at it by name, so
    # answering with a single total would be answering a different question.
    if prune is not None and depth > 0 and prune(path):
        node.size_bytes, node.allocated_bytes = _measure(path)
        yield node
        return node

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
            child = yield from _walk_dir(entry_path, exclude, prune, depth + 1)
        else:
            child = _scan_file(entry)
            yield child

        node.children.append(child)
        node.size_bytes += child.size_bytes
        node.allocated_bytes += child.allocated_bytes

    yield node
    return node


WORKERS = min(16, (os.cpu_count() or 4) * 2)
"""Threads used to total a pruned subtree.

More than cores because this is I/O bound, not CPU bound: every worker spends its
time blocked in stat, and the GIL is released for the duration of the syscall. On
a 1.5M-file projects folder the walk was 95s single-threaded, and syscalls rather
than object construction were the cost.
"""

_PARALLEL_FROM = 64
"""Below this many subdirectories a thread pool costs more than it saves."""


def _measure(path: Path) -> tuple[int, int]:
    """Total a subtree without building anything.

    Strings rather than Path objects, and no model construction: this runs over
    the parts of a disk nobody needs described, only counted.
    """
    roots = _immediate_dirs(str(path))
    size, allocated = _measure_files(str(path))

    if len(roots) < _PARALLEL_FROM:
        for root in roots:
            counted, occupied = _measure_serial(root)
            size += counted
            allocated += occupied
        return size, allocated

    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        for counted, occupied in pool.map(_measure_serial, roots):
            size += counted
            allocated += occupied

    return size, allocated


def _immediate_dirs(path: str) -> list[str]:
    try:
        return [
            entry.path for entry in os.scandir(path) if entry.is_dir() and not entry.is_symlink()
        ]
    except PermissionError:
        return []


def _measure_files(path: str) -> tuple[int, int]:
    """Files directly in *path*, ignoring its subdirectories."""
    size = allocated = 0
    try:
        entries = list(os.scandir(path))
    except PermissionError:
        return 0, 0
    for entry in entries:
        if entry.is_symlink() or entry.is_dir():
            continue
        stat = entry.stat(follow_symlinks=False)
        size += stat.st_size
        allocated += stat.st_blocks * _BLOCK_SIZE
    return size, allocated


def _measure_serial(path: str) -> tuple[int, int]:
    size = allocated = 0
    stack = [path]

    while stack:
        try:
            entries = list(os.scandir(stack.pop()))
        except PermissionError:
            continue

        for entry in entries:
            if entry.is_symlink():
                continue
            if entry.is_dir():
                stack.append(entry.path)
            else:
                stat = entry.stat(follow_symlinks=False)
                size += stat.st_size
                allocated += stat.st_blocks * _BLOCK_SIZE

    return size, allocated


def _scan_file(entry: os.DirEntry[str]) -> ScanNode:
    stat = entry.stat(follow_symlinks=False)
    return ScanNode(
        path=Path(entry.path),
        name=entry.name,
        is_dir=False,
        size_bytes=stat.st_size,
        allocated_bytes=stat.st_blocks * _BLOCK_SIZE,
    )
