"""The contract between scanner, catalog, classifier, and UI.

Everything else in Sift agrees on these shapes. Change them here first.
"""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, Field


class Verdict(StrEnum):
    """What it costs you to get this back — the only question that matters.

    Deliberately three values, not a richer taxonomy. Whether something is a cache
    or a build artifact is interesting; whether you can get it back is decisive.
    """

    REGENERABLE = "regenerable"
    REVIEW = "review"
    IRREPLACEABLE = "irreplaceable"


class ScanNode(BaseModel):
    """One entry in a surveyed tree — a file, or a directory and everything under it.

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

    rule_id: str | None = None
    """Which catalog rule settled this, if any. Doubles as the grouping key: every
    node sharing a rule id becomes one line in the plan."""

    verdict: Verdict | None = None
    """None means the catalog had nothing to say, and a model may be asked."""

    restore: str | None = None
    restore_time: str | None = None


class FileSummary(BaseModel):
    name: str
    size_bytes: int


class Candidate(BaseModel):
    """An opaque directory the catalog couldn't name.

    Described well enough for a model to reason about it without a single file
    being opened: what it's called, how big it is, what fills it, and what the
    largest things inside are named.
    """

    path: Path
    name: str
    size_bytes: int
    file_count: int
    extensions: dict[str, int] = Field(default_factory=dict)
    """Extension to total bytes, largest first. A directory that is 95% .o files
    needs no further explanation."""

    largest_files: list[FileSummary] = Field(default_factory=list)


class Classification(BaseModel):
    """What a model concluded about one candidate."""

    path: Path
    verdict: Verdict
    reason: str

    restore: str
    """Never optional. A verdict without a way back is exactly the information the
    user needed, so "cannot be restored" has to be said rather than left blank."""
