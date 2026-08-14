"""A queryable view of a survey.

The agent is given tools over this rather than the tree itself. A whole-disk
survey is far too large to hand to a model, and handing it over would tie the
design to whichever provider has the biggest context window this month —
which is the opposite of being able to swap providers by environment variable.
"""

from __future__ import annotations

from pathlib import Path

from sift.models import ScanNode, Verdict


class Index:
    def __init__(self, tree: ScanNode) -> None:
        self._files = [node for node in _walk(tree) if not node.is_dir]
        self._irreplaceable = frozenset(
            node.path for node in _walk(tree) if node.verdict is Verdict.IRREPLACEABLE
        )
        self.total_bytes = tree.size_bytes

    def is_irreplaceable(self, path: Path) -> bool:
        """True when the survey judged this unrecoverable, at any depth above.

        A label, not a lock. Nothing consults this to decide whether a file may be
        returned — only to say what it is.
        """
        return path in self._irreplaceable or any(
            parent in self._irreplaceable for parent in path.parents
        )

    def find(
        self,
        extensions: list[str] | None = None,
        min_bytes: int | None = None,
        max_bytes: int | None = None,
        name_contains: str | None = None,
        path_contains: str | None = None,
        limit: int = 60,
    ) -> dict[str, object]:
        """Matching files, largest first, each labelled with what it would cost.

        Everything that matches comes back. Withholding files made the agent report
        "I found nothing", which reads as "that isn't there" when the truth was
        "that is off limits" — and it is not the tool's place to decide either way.
        Saying which files cannot be replaced is.
        """
        wanted = {e.lower() if e.startswith(".") else f".{e.lower()}" for e in extensions or []}

        matched = [
            node
            for node in self._files
            if (not wanted or node.path.suffix.lower() in wanted)
            and (min_bytes is None or node.size_bytes >= min_bytes)
            and (max_bytes is None or node.size_bytes <= max_bytes)
            and (name_contains is None or name_contains.lower() in node.name.lower())
            # Searching by folder needs the whole path: "Documents" never appears in
            # a filename, so without this the agent asks about a protected directory,
            # matches nothing, and reports "there is no such folder" — which is false.
            and (path_contains is None or path_contains.lower() in str(node.path).lower())
        ]
        matched.sort(key=lambda node: node.size_bytes, reverse=True)
        shown = matched[:limit]
        unrecoverable = sum(1 for node in shown if self.is_irreplaceable(node.path))

        return {
            "files": [
                {
                    "path": str(node.path),
                    "name": node.name,
                    "size_bytes": node.size_bytes,
                    "irreplaceable": self.is_irreplaceable(node.path),
                }
                for node in shown
            ],
            "irreplaceable_count": unrecoverable,
            "note": _note(unrecoverable),
        }

    def summary(self) -> dict[str, object]:
        by_extension: dict[str, int] = {}
        for node in self._files:
            suffix = node.path.suffix.lower() or "(none)"
            by_extension[suffix] = by_extension.get(suffix, 0) + node.size_bytes

        ranked = sorted(by_extension.items(), key=lambda kv: kv[1], reverse=True)
        biggest = sorted(self._files, key=lambda n: n.size_bytes, reverse=True)[:10]

        return {
            "total_bytes": self.total_bytes,
            "file_count": len(self._files),
            "bytes_by_extension": dict(ranked[:20]),
            "largest_files": [
                {"name": n.name, "size_bytes": n.size_bytes, "path": str(n.path)} for n in biggest
            ],
        }


def _note(unrecoverable: int) -> str:
    """What to tell the model about what it just matched."""
    if not unrecoverable:
        return ""
    return (
        f"{unrecoverable} of these cannot be replaced if deleted. You may still select "
        "them if that is what was asked for — it is the person's disk and nothing is "
        "deleted, only moved aside. Say in your reason which ones they are."
    )


def _walk(node: ScanNode) -> list[ScanNode]:
    found: list[ScanNode] = []
    stack = [node]
    while stack:
        current = stack.pop()
        found.append(current)
        stack.extend(current.children)
    return found
