"""Filesystem walk.

Pure library: imports nothing from the web, AI, or config layers, so it stays
portable to a CLI or a native shell.
"""

from __future__ import annotations

import os
from pathlib import Path

from sift.models import ScanNode

_BLOCK_SIZE = 512
"""``st_blocks`` is reported in 512-byte units regardless of the filesystem's own
block size — a POSIX quirk, not a value to derive from the filesystem."""


def scan(root: Path) -> ScanNode:
    """Walk *root* and return it as a tree, with sizes summed bottom-up."""
    return _scan_dir(Path(root))


def _scan_dir(path: Path) -> ScanNode:
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
        # Expected on macOS for TCC-gated directories. The tree keeps its shape so
        # the UI can offer a grant button instead of losing the branch entirely.
        node.unreadable = True
        return node

    for entry in entries:
        # Symlinks are skipped rather than followed: following them double-counts
        # the target and can escape the scan root entirely.
        if entry.is_symlink():
            continue

        child = _scan_dir(Path(entry.path)) if entry.is_dir() else _scan_file(entry)
        node.children.append(child)
        node.size_bytes += child.size_bytes
        node.allocated_bytes += child.allocated_bytes

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
