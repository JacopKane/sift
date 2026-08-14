"""Where it offers to look, on this machine.

Decided here rather than in the browser because it is a question about the
computer, not about the interface: which of these folders exist, and what the
platform calls them. A list hard-coded in the frontend is right on exactly one
operating system and quietly wrong on the rest.

The whole disk is deliberately absent. It is a scan of every file behind a
permission dialog, which is a reasonable thing to ask for on purpose — `sift /`
does it — and a bad thing to leave under the cursor on the first screen.
"""

from __future__ import annotations

import platform
from pathlib import Path

from pydantic import BaseModel


class Place(BaseModel):
    label: str
    path: Path
    icon: str
    """Which icon the interface should use. Named, not chosen here — this module
    knows about disks, not about drawing."""


# The four every desktop has under some name, in the order they are usually worth
# looking at: what you downloaded and forgot, what you dumped on the desktop,
# then the two you actually care about.
COMMON = (
    ("Downloads", "download"),
    ("Desktop", "monitor"),
    ("Documents", "file-text"),
    ("Pictures", "image"),
)


def places(home: Path | None = None) -> list[Place]:
    """The folders worth offering, filtered to the ones that are really there.

    Offering a folder this machine does not have is a button that fails after it
    is pressed, which is the worst moment to find out.
    """
    root = home or Path.home()
    found = [
        Place(label=label, path=root / label, icon=icon)
        for label, icon in COMMON
        if (root / label).is_dir()
    ]

    # Big, well understood, and the one place a size chart genuinely surprises
    # people. macOS only — the others have no single equivalent, and inventing
    # one per distribution is how a list stops being maintainable.
    if platform.system() == "Darwin" and Path("/Applications").is_dir():
        found.append(Place(label="Applications", path=Path("/Applications"), icon="layout-grid"))

    return found
