"""Reclaiming space, reversibly.

Nothing here deletes. Reclaiming *moves* a path into a quarantine directory and
records where it came from; :func:`undo` reads that record and puts it back.
Emptying quarantine is a separate act the person performs.

The reason is the verdicts. A plan built partly from a model's judgement will
sometimes be wrong — two frontier models disagreed about whether a source
directory was disposable — so the operation the plan drives has to be one that
can be taken back.
"""

from __future__ import annotations

import json
import shutil
from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel, Field

from sift.models import Verdict

MANIFEST = "manifest.json"


class Reclaimed(BaseModel):
    """One thing moved, and where it came from."""

    original: Path
    held_at: Path
    size_bytes: int
    at: str

    overridden: bool = False
    """True when this was protected and reclaimed anyway. Recorded because the
    person deserves to see, on the receipt, which of these they forced."""


class Receipt(BaseModel):
    moved: list[Reclaimed] = Field(default_factory=list)
    freed_bytes: int = 0
    refused: list[str] = Field(default_factory=list)


class Protected(Exception):
    """Raised when something protected is reclaimed without insisting.

    A refusal, not a prohibition. Pass ``override=True`` and it goes: it is the
    user's disk, and a tool that simply says no is a tool they route around —
    usually with rm, which has no undo.
    """


class Quarantine:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)
        self._entries: list[Reclaimed] | None = None

    @property
    def manifest_path(self) -> Path:
        return self.root / MANIFEST

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
        override: bool = False,
    ) -> Receipt:
        """Move *path* aside, leaving anything in *excluding* where it is.

        Something marked irreplaceable is refused unless *override* is set. The
        refusal is the warning; the override is the person overruling it, which
        they are entitled to do.
        """
        forced = verdict is Verdict.IRREPLACEABLE
        if forced and not override:
            raise Protected(f"{path} cannot be replaced if you delete it")
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
            overridden=forced,
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
        """Put everything back where it came from, newest first."""
        restored: list[Reclaimed] = []
        for entry in reversed(self.held()):
            if not entry.held_at.exists():
                continue
            entry.original.parent.mkdir(parents=True, exist_ok=True)
            if entry.original.exists() and not any(entry.original.iterdir()):
                entry.original.rmdir()  # the empty shell left by an excluding move
            shutil.move(str(entry.held_at), str(entry.original))
            restored.append(entry)

        self._record([])
        self._entries = []
        return Receipt(moved=restored, freed_bytes=0)

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
