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
        """Move everything in the basket aside, and forget it.

        One item failing must not strand the rest. A basket of sixty screenshots
        that stops at the eleventh because one had already been moved leaves the
        person with a half-done job and no idea which half — so each is attempted
        on its own and whatever refused is reported.
        """
        moved, freed, refused = [], 0, []
        for item in self.items:
            try:
                outcome = quarantine.reclaim(
                    item.path,
                    verdict=item.verdict,
                    excluding=item.excluding,
                    override=item.overridden,
                )
            except (Protected, OSError) as failure:
                refused.append(f"{item.path}: {failure}")
                continue
            moved.extend(outcome.moved)
            freed += outcome.freed_bytes
            refused.extend(outcome.refused)

        self.clear()
        return Receipt(moved=moved, freed_bytes=freed, refused=refused)


def item_for(tree: ScanNode, path: Path, *, overridden: bool = False) -> Item:
    """Build a basket item from what the survey already knows about *path*.

    Protection is inherited. A screenshot inside ~/Desktop carries no verdict of
    its own — the catalog names directories, not files — so reading only the
    node's own verdict let every file inside a protected folder be basketed and
    reclaimed with no warning at all. The nearest verdict above it is the answer.
    """
    inherited: Verdict | None = None
    stack: list[tuple[ScanNode, Verdict | None]] = [(tree, tree.verdict)]

    while stack:
        node, above = stack.pop()
        if node.path == path:
            return Item(
                path=path,
                size_bytes=node.size_bytes,
                verdict=node.verdict or above,
                overridden=overridden,
            )
        # Only irreplaceable is inherited: "this cache rebuilds itself" says
        # nothing about a particular file inside it, but "never delete this" does.
        carried = node.verdict if node.verdict is Verdict.IRREPLACEABLE else above
        stack.extend((child, carried) for child in node.children)

    _ = inherited
    raise KeyError(f"{path} was not in the survey")
