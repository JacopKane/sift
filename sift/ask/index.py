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
        self._protected = frozenset(
            node.path for node in _walk(tree) if node.verdict is Verdict.IRREPLACEABLE
        )
        self.total_bytes = tree.size_bytes

    def is_protected(self, path: Path) -> bool:
        """True when the catalog has declared this off limits, at any depth above."""
        return path in self._protected or any(parent in self._protected for parent in path.parents)

    def find(
        self,
        extensions: list[str] | None = None,
        min_bytes: int | None = None,
        max_bytes: int | None = None,
        name_contains: str | None = None,
        path_contains: str | None = None,
        limit: int = 60,
        include_protected: bool = False,
    ) -> dict[str, object]:
        """Matching files, with protected ones counted rather than silently dropped.

        Dropping them quietly makes the agent report "I found nothing", which reads
        as "that isn't there" when the truth is "that is off limits" — a different
        answer, and the one the person asking actually needs.
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
        # When the person has insisted, protection stops being a filter and becomes
        # a label. They still see which of these cannot be replaced.
        allowed = (
            list(matched)
            if include_protected
            else [node for node in matched if not self.is_protected(node.path)]
        )
        withheld = len(matched) - len(allowed)
        allowed.sort(key=lambda node: node.size_bytes, reverse=True)

        # A protected directory is counted but never explored, so none of its files
        # are in the index. Without this a query aimed at one comes back empty and
        # the honest-sounding answer is "there is nothing there" — when the truth
        # is "that is off limits". Naming the directory closes that gap.
        aimed_at = sorted(
            str(path)
            for path in self._protected
            if path_contains and path_contains.lower() in str(path).lower()
        )

        return {
            "files": [
                {"path": str(node.path), "name": node.name, "size_bytes": node.size_bytes}
                for node in allowed[:limit]
            ],
            "withheld_because_protected": withheld,
            "protected_directories_matched": aimed_at,
            "note": _note(aimed_at, withheld),
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


def _note(directories: list[str], files: int) -> str:
    """What to tell the model about anything it matched but may not have."""
    off_limits = [*directories]
    if files:
        off_limits.append(f"{files} file(s)")
    if not off_limits:
        return ""
    return (
        f"Protected and off limits: {', '.join(off_limits)}. Say they are protected. "
        "Do not say nothing was found — that is a different answer, and it is not true."
    )


def _walk(node: ScanNode) -> list[ScanNode]:
    found: list[ScanNode] = []
    stack = [node]
    while stack:
        current = stack.pop()
        found.append(current)
        stack.extend(current.children)
    return found
