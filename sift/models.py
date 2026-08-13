"""The contract between scanner, catalog, classifier, and UI.

Everything else in Sift agrees on these shapes. Change them here first.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field


class ScanNode(BaseModel):
    """One entry in a scanned tree — a file, or a directory and everything under it.

    Two sizes, because they answer different questions. ``size_bytes`` is what the
    file *is*; ``allocated_bytes`` is what it costs you. They diverge on sparse
    files and APFS clones, and only the second one frees up when you delete.
    """

    path: Path
    name: str
    is_dir: bool
    size_bytes: int
    allocated_bytes: int
    children: list[ScanNode] = Field(default_factory=list)
    unreadable: bool = False
    """True when the OS refused to let us look inside. Not an error — a state the
    UI renders as a card with a grant button."""
