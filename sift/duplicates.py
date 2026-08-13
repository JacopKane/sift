"""Finding the same file twice.

A second lens over a survey that has already been walked. Two files with
identical contents are one file and one copy, whatever they are named, and the
copy costs exactly as much as the original.

Hashing a whole disk would cost more than the survey did. Size is the filter:
files of different sizes cannot be identical, and on a real disk almost nothing
shares a size. Only the handful that do are ever opened.
"""

from __future__ import annotations

import hashlib
from collections import defaultdict
from pathlib import Path

from pydantic import BaseModel, Field

from sift.models import ScanNode

CHUNK = 1024 * 1024
MIN_BYTES = 4096
"""Below this, a duplicate is not worth the read. A thousand identical empty
files still add up to nothing."""


class Duplicate(BaseModel):
    """One set of identical files: the one to keep, and the copies."""

    keep: Path
    copies: list[Path] = Field(default_factory=list)
    size_bytes: int = 0

    @property
    def reclaimable_bytes(self) -> int:
        """What deleting the copies frees — one file's worth per copy, never the
        original's."""
        return self.size_bytes * len(self.copies)


class Report(BaseModel):
    duplicates: list[Duplicate] = Field(default_factory=list)
    files_read: int = 0
    files_surveyed: int = 0

    @property
    def reclaimable_bytes(self) -> int:
        return sum(found.reclaimable_bytes for found in self.duplicates)


def find_duplicates(tree: ScanNode, minimum: int = MIN_BYTES) -> Report:
    """Identical files under *tree*, largest sets first."""
    files = [node for node in _walk(tree) if not node.is_dir and node.size_bytes >= minimum]

    by_size: dict[int, list[ScanNode]] = defaultdict(list)
    for node in files:
        by_size[node.size_bytes].append(node)

    # Only sizes shared by more than one file are worth opening. This is the whole
    # optimisation: on a real disk it leaves single digits out of a million.
    contested = [group for group in by_size.values() if len(group) > 1]

    found: list[Duplicate] = []
    read = 0
    for group in contested:
        by_digest: dict[str, list[ScanNode]] = defaultdict(list)
        for node in group:
            digest = _digest(node.path)
            read += 1
            if digest is not None:
                by_digest[digest].append(node)

        for identical in by_digest.values():
            if len(identical) < 2:
                continue
            # The oldest is kept: whichever came first is likelier to be the one
            # something else refers to.
            oldest, *copies = sorted(identical, key=_created)
            found.append(
                Duplicate(
                    keep=oldest.path,
                    copies=[copy.path for copy in copies],
                    size_bytes=oldest.size_bytes,
                )
            )

    found.sort(key=lambda entry: entry.reclaimable_bytes, reverse=True)
    return Report(duplicates=found, files_read=read, files_surveyed=len(files))


def _created(node: ScanNode) -> float:
    try:
        return node.path.stat().st_mtime
    except OSError:
        return 0.0


def _digest(path: Path) -> str | None:
    digest = hashlib.blake2b(digest_size=16)
    try:
        with path.open("rb") as handle:
            while chunk := handle.read(CHUNK):
                digest.update(chunk)
    except OSError:
        return None
    return digest.hexdigest()


def _walk(tree: ScanNode) -> list[ScanNode]:
    found, stack = [], [tree]
    while stack:
        node = stack.pop()
        found.append(node)
        stack.extend(node.children)
    return found
