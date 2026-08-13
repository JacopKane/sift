"""What the person has chosen to get rid of.

The plan proposes; the basket is where the decision is recorded. It exists as its
own thing because putting something in and emptying it are separate acts — that
gap is where the warning lives, and where a countdown can be cancelled.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field

from sift.models import ScanNode, Verdict
from sift.quarantine import Protected, Quarantine, Receipt


class Item(BaseModel):
    path: Path
    size_bytes: int
    verdict: Verdict | None = None
    excluding: list[Path] = Field(default_factory=list)
    overridden: bool = False
    """Set when the person was warned this cannot be replaced and said go ahead."""


class Basket:
    def __init__(self) -> None:
        self._items: dict[Path, Item] = {}

    @property
    def items(self) -> list[Item]:
        return sorted(self._items.values(), key=lambda item: item.size_bytes, reverse=True)

    @property
    def total_bytes(self) -> int:
        return sum(item.size_bytes for item in self._items.values())

    def add(self, item: Item) -> None:
        """Take one in, refusing anything protected that has not been insisted on."""
        if item.verdict is Verdict.IRREPLACEABLE and not item.overridden:
            raise Protected(f"{item.path} cannot be replaced if you delete it")
        self._items[item.path] = item

    def remove(self, path: Path) -> None:
        self._items.pop(path, None)

    def clear(self) -> None:
        self._items.clear()

    def empty_into(self, quarantine: Quarantine) -> Receipt:
        """Move everything in the basket aside, and forget it."""
        moved, freed, refused = [], 0, []
        for item in self.items:
            outcome = quarantine.reclaim(
                item.path,
                verdict=item.verdict,
                excluding=item.excluding,
                override=item.overridden,
            )
            moved.extend(outcome.moved)
            freed += outcome.freed_bytes
            refused.extend(outcome.refused)

        self.clear()
        return Receipt(moved=moved, freed_bytes=freed, refused=refused)


def item_for(tree: ScanNode, path: Path, *, overridden: bool = False) -> Item:
    """Build a basket item from what the survey already knows about *path*."""
    stack = [tree]
    while stack:
        node = stack.pop()
        if node.path == path:
            return Item(
                path=path,
                size_bytes=node.size_bytes,
                verdict=node.verdict,
                overridden=overridden,
            )
        stack.extend(node.children)
    raise KeyError(f"{path} was not in the survey")
