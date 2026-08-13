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

    label: str | None = None
    """What to call this in the plan — the rule's name rather than the directory's,
    so forty-seven paths read as one decision about node_modules."""

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
    label: str
    size_bytes: int
    file_count: int

    excluding: list[Path] = Field(default_factory=list)
    """Files inside this directory that are being judged separately, because they
    are large enough to decide on their own. Their bytes are not in
    ``size_bytes``, and reclaiming this candidate must leave them alone."""

    extensions: dict[str, int] = Field(default_factory=dict)
    """Extension to total bytes, largest first. A directory that is 95% .o files
    needs no further explanation."""

    largest_files: list[FileSummary] = Field(default_factory=list)


class Classification(BaseModel):
    """What a model concluded about one candidate."""

    path: Path
    verdict: Verdict
    reason: str

    label: str = ""
    size_bytes: int = 0
    excluding: list[Path] = Field(default_factory=list)
    """Carried over from the candidate rather than re-read from the tree. A
    remainder candidate is smaller than the directory it names, and looking the
    size up again would silently count the broken-out files twice."""

    restore: str
    """Never optional. A verdict without a way back is exactly the information the
    user needed, so "cannot be restored" has to be said rather than left blank."""


class PlanItem(BaseModel):
    """One decision, however many directories it covers."""

    label: str
    verdict: Verdict
    size_bytes: int
    paths: list[Path]
    restore: str
    restore_time: str | None = None
    rule_id: str | None = None
    reason: str | None = None

    excluding: list[Path] = Field(default_factory=list)
    """Paths inside this item that it does not cover, because they are their own
    decision. Reclaiming this item must leave them where they are."""
    """Why, when a model decided it. Catalog rules carry their reason in the label."""


class Plan(BaseModel):
    proposals: list[PlanItem]
    """What could be reclaimed, largest first. Never includes anything irreplaceable."""

    protected: list[PlanItem]
    """Shown so you can see Sift understood your disk, never offered for deletion."""

    reclaimable_bytes: int
    """Only what is regenerable. Counting `review` here would promise space that
    might turn out to be somebody's only copy."""

    needs_review_bytes: int
    """Held back pending a human decision — and the reason there's a conversation."""

    surveyed_bytes: int
