"""Walking a disk and recognising what's on it.

Composes the two pure layers: :mod:`sift.scanner` reports what is there,
:mod:`sift.catalog` names what it can. The catalog is applied *during* the walk,
so verdicts stream out with the nodes rather than arriving in a second pass.
"""

from __future__ import annotations

from collections.abc import Collection, Iterator
from pathlib import Path

from sift.catalog import load_catalog
from sift.models import Candidate, FileSummary, ScanNode
from sift.scanner import walk

CANDIDATE_LIMIT = 40
"""How many opaque directories the model is asked about at most.

A cap rather than a size floor: a floor has to be picked for a disk size, and is
wrong on the next machine. Taking the largest N scales to any disk and keeps the
call one predictable size.
"""

SAMPLE_FILES = 5


def survey(
    root: Path,
    exclude: Collection[Path] = (),
    home: Path | None = None,
) -> Iterator[ScanNode]:
    """Report each entry under *root*, carrying a verdict where the catalog knows one."""
    catalog = load_catalog(home)

    for node in walk(root, exclude):
        rule = catalog.recognise(node.path, is_dir=node.is_dir)
        if rule is not None:
            node.rule_id = rule.id
            node.verdict = rule.verdict
            node.restore = rule.restore
            node.restore_time = rule.restore_time
        yield node


def candidates_for_model(tree: ScanNode, limit: int = CANDIDATE_LIMIT) -> list[Candidate]:
    """The opaque directories worth asking a model about, largest first.

    A candidate is the *topmost* directory the catalog couldn't name that has
    nothing recognised beneath it either. Descending further would ask about a
    directory and its own children; stopping higher would ask about the whole home
    folder. Neither is a useful question.
    """
    found: list[ScanNode] = []

    def visit(node: ScanNode) -> None:
        if not node.is_dir or node.unreadable:
            return
        if node.verdict is not None:
            return  # settled by the catalog; children are covered by it
        if _has_settled_descendant(node):
            for child in node.children:
                visit(child)  # structural directory — keep going down
            return
        if node.size_bytes == 0:
            return  # nothing to reclaim, so nothing to ask about
        found.append(node)

    # The root is structural by definition and is never itself a candidate.
    for child in tree.children:
        visit(child)

    found.sort(key=lambda node: node.size_bytes, reverse=True)
    return [_describe(node) for node in found[:limit]]


def _has_settled_descendant(node: ScanNode) -> bool:
    stack = list(node.children)
    while stack:
        current = stack.pop()
        if current.verdict is not None:
            return True
        stack.extend(current.children)
    return False


def _descendants(node: ScanNode) -> Iterator[ScanNode]:
    stack = list(node.children)
    while stack:
        current = stack.pop()
        yield current
        stack.extend(current.children)


def _describe(node: ScanNode) -> Candidate:
    files = [child for child in _descendants(node) if not child.is_dir]

    extensions: dict[str, int] = {}
    for file in files:
        suffix = file.path.suffix.lower() or "(none)"
        extensions[suffix] = extensions.get(suffix, 0) + file.size_bytes

    largest = sorted(files, key=lambda file: file.size_bytes, reverse=True)[:SAMPLE_FILES]

    return Candidate(
        path=node.path,
        name=node.name,
        size_bytes=node.size_bytes,
        file_count=len(files),
        extensions=dict(sorted(extensions.items(), key=lambda kv: kv[1], reverse=True)),
        largest_files=[FileSummary(name=f.name, size_bytes=f.size_bytes) for f in largest],
    )
