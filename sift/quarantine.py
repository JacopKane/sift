"""Reclaiming space, reversibly.

Nothing here deletes. Reclaiming *moves* a path into the bin this machine already
has and records where it came from; :func:`undo` reads that record and puts it
back. Emptying the bin is a separate act the person performs — and because it is
their own Trash, they already know how, and already trust it.

The reason is the verdicts. A plan built partly from a model's judgement will
sometimes be wrong — two frontier models disagreed about whether a source
directory was disposable — so the operation the plan drives has to be one that
can be taken back.
"""

from __future__ import annotations

import json
import platform
import shutil
from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel, Field

from sift.models import Verdict

MANIFEST = "manifest.json"

OURS = Path.home() / ".sift"
"""Where the record lives when the bin is not ours to put files in."""


def native_bin() -> Path:
    """Where this machine already puts things on their way out.

    Using the desktop's own bin is what makes "we never delete, you do" true
    rather than a promise: the files land somewhere the person already knows how
    to inspect, restore from and empty, with no second bin to learn.

    Only macOS is native so far. The freedesktop spec needs a `.trashinfo`
    sidecar written per file for a Linux desktop to offer "restore", and there is
    no Linux catalog yet for anything to reach it with — a half-native bin, where
    files appear but cannot be put back, is worse than an honest one of our own.
    """
    # platform.system() rather than sys.platform: the type checker narrows the
    # latter to whatever it is running on and declares the other branch dead.
    if platform.system() == "Darwin":
        return Path.home() / ".Trash"
    return OURS / "quarantine"


class Reclaimed(BaseModel):
    """One thing moved, and where it came from."""

    original: Path
    held_at: Path
    size_bytes: int
    at: str

    verdict: Verdict | None = None
    """What it was judged to be at the moment it moved.

    Kept because the manifest is the record of what happened, and a list of paths
    with no verdicts gives you no way, weeks later, to tell which of them you
    would be sorry to lose."""


class Receipt(BaseModel):
    moved: list[Reclaimed] = Field(default_factory=list)
    freed_bytes: int = 0
    refused: list[str] = Field(default_factory=list)


class Quarantine:
    def __init__(self, root: Path, *, record: Path | None = None) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)
        # Kept out of the bin when the bin is the person's own: a manifest.json
        # sitting in their Trash is our clutter in their space, and it would be
        # emptied along with everything else exactly when undo still needs it.
        self.manifest_path = record or root / MANIFEST
        self.manifest_path.parent.mkdir(parents=True, exist_ok=True)
        self._entries: list[Reclaimed] | None = None

    @classmethod
    def native(cls) -> Quarantine:
        """The bin this machine already has, with our record kept beside it."""
        return cls(native_bin(), record=OURS / MANIFEST)

    def held(self) -> list[Reclaimed]:
        if not self.manifest_path.exists():
            return []
        raw = json.loads(self.manifest_path.read_text(encoding="utf-8"))
        return [Reclaimed.model_validate(entry) for entry in raw]

    def reclaim(
        self,
        path: Path,
        *,
        verdict: Verdict | None = None,
        excluding: list[Path] | None = None,
    ) -> Receipt:
        """Move *path* aside, leaving anything in *excluding* where it is.

        Nothing is refused. The verdict travels with the move and onto the
        manifest so the receipt can say what each thing was, but it is not a gate:
        a tool that says no is a tool people route around, usually with rm, which
        has no undo. The judgement is there to inform the choice, not to make it.
        """
        if not path.exists():
            return Receipt(refused=[f"{path} is not there"])

        keep = set(excluding or [])
        held_at = self._free_slot(path)

        if keep:
            # Move the directory, then put back what the proposal did not cover.
            # Copying instead would double the disk use of the very operation
            # meant to reduce it.
            shutil.move(str(path), str(held_at))
            path.mkdir(parents=True, exist_ok=True)
            for kept in keep:
                stowed = held_at / kept.relative_to(path)
                if stowed.exists():
                    shutil.move(str(stowed), str(kept))
        else:
            shutil.move(str(path), str(held_at))

        entry = Reclaimed(
            original=path,
            held_at=held_at,
            size_bytes=_size_of(held_at),
            at=datetime.now(UTC).isoformat(),
            verdict=verdict,
        )
        # The slot is already claimed on disk by the move itself, so the manifest
        # is the only thing that needs appending. Re-reading it per item turned a
        # basket of sixty into sixty read-and-rewrite cycles of a growing file.
        self._record([*self._cached(), entry])
        return Receipt(moved=[entry], freed_bytes=entry.size_bytes)

    def _cached(self) -> list[Reclaimed]:
        if self._entries is None:
            self._entries = self.held()
        return self._entries

    def undo(self) -> Receipt:
        """Put everything back where it came from, newest first.

        The bin belongs to the person, so it can be emptied from under us between
        reclaiming and undoing. Anything whose bytes are gone is reported rather
        than skipped: a receipt that lists nothing reads as "all restored".
        """
        restored: list[Reclaimed] = []
        gone: list[str] = []
        for entry in reversed(self.held()):
            if not entry.held_at.exists():
                gone.append(f"{entry.original}: emptied from the bin before undo")
                continue
            entry.original.parent.mkdir(parents=True, exist_ok=True)
            if entry.original.exists() and not any(entry.original.iterdir()):
                entry.original.rmdir()  # the empty shell left by an excluding move
            shutil.move(str(entry.held_at), str(entry.original))
            restored.append(entry)

        self._record([])
        self._entries = []
        return Receipt(moved=restored, freed_bytes=0, refused=gone)

    def _free_slot(self, path: Path) -> Path:
        """Somewhere in quarantine nothing already occupies.

        Two directories can share a name — every node_modules does — so the slot
        is numbered rather than named after the source.
        """
        for index in range(10_000):
            slot = self.root / f"{index:04d}-{path.name}"
            if not slot.exists():
                return slot
        raise RuntimeError("quarantine is full; empty it before reclaiming more")

    def _record(self, entries: list[Reclaimed]) -> None:
        self._entries = list(entries)
        self.manifest_path.write_text(
            json.dumps([entry.model_dump(mode="json") for entry in entries], indent=2),
            encoding="utf-8",
        )


def _size_of(path: Path) -> int:
    if path.is_file():
        return path.stat().st_size
    return sum(child.stat().st_size for child in path.rglob("*") if child.is_file())
