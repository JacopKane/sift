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

FILE_SHARE = 0.005
MIN_FILE_BYTES = 1024 * 1024
"""When a single file is this large, it is its own decision.

A Downloads folder is usually one video and one archive plus a hundred PDFs that
together round to nothing. Judging the folder as a whole answers "it's mixed",
which is true and useless; judging the two big files answers the actual question.
The share keeps it proportional to the disk, the floor stops a small survey from
breaking every file out."""


def survey(
    root: Path,
    exclude: Collection[Path] = (),
    home: Path | None = None,
) -> Iterator[ScanNode]:
    """Report each entry under *root*, carrying a verdict where the catalog knows one.

    A directory the catalog can name is counted but not explored. Its contents are
    already accounted for by the verdict on the whole, and enumerating them would
    mean describing every file in every node_modules on the disk to learn nothing.
    """
    catalog = load_catalog(home)

    def already_named(path: Path) -> bool:
        return catalog.recognise(path, is_dir=True) is not None

    for node in walk(root, exclude, prune=already_named):
        rule = catalog.recognise(node.path, is_dir=node.is_dir)
        if rule is not None:
            node.rule_id = rule.id
            node.label = rule.label
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
    floor = max(int(tree.size_bytes * FILE_SHARE), MIN_FILE_BYTES)
    files: list[ScanNode] = []
    directories: list[tuple[ScanNode, set[Path]]] = []
    loose: list[tuple[ScanNode, list[ScanNode]]] = []

    def loose_files(node: ScanNode) -> list[ScanNode]:
        """Big files sitting directly in a directory we are descending through."""
        return [child for child in node.children if not child.is_dir and child.size_bytes >= floor]

    def loose_remainder(node: ScanNode) -> None:
        """The small files left lying directly in a directory we descended through.

        Individually beneath notice, collectively worth a verdict — a Downloads
        folder is typically a hundred PDFs nobody has looked at since.
        """
        rest = [child for child in node.children if not child.is_dir and child.size_bytes < floor]
        if rest:
            loose.append((node, rest))

    def visit(node: ScanNode) -> None:
        if not node.is_dir or node.unreadable:
            return
        if node.verdict is not None:
            return  # settled by the catalog; children are covered by it

        if _has_settled_descendant(node):
            files.extend(loose_files(node))
            loose_remainder(node)
            for child in node.children:
                visit(child)  # structural directory — keep going down
            return

        # An opaque directory. Anything big enough to decide on its own is pulled
        # out, and what remains is offered as the rest of the directory.
        big = [
            child for child in _descendants(node) if not child.is_dir and child.size_bytes >= floor
        ]
        files.extend(big)

        # Whatever is left after the big files is still offered. On a real
        # Downloads folder that remainder is a hundred PDFs — individually
        # nothing, collectively worth a verdict. Sorting and the cap keep it from
        # crowding out anything that matters.
        remainder = node.size_bytes - sum(child.size_bytes for child in big)
        if remainder > 0:
            directories.append((node, {child.path for child in big}))

    for child in tree.children:
        visit(child)
    # The root is never a candidate itself, so its own loose files would otherwise
    # go unjudged — which on a Downloads folder is most of what is there.
    files.extend(loose_files(tree))
    loose_remainder(tree)

    described = [
        *(_describe(node) for node in files),
        *(_describe(node, excluding) for node, excluding in directories),
        *(_describe_files(node, rest) for node, rest in loose),
    ]
    described.sort(key=lambda candidate: candidate.size_bytes, reverse=True)
    return described[:limit]


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


def _describe_files(parent: ScanNode, files: list[ScanNode]) -> Candidate:
    """A candidate covering exactly the given files, and nothing else in *parent*.

    It is named after the directory, because that is what the model can reason
    about — but everything in that directory it does not cover has to be listed as
    excluded. Without that, reclaiming "the loose files in client-app" would take
    src/ with it, which the same plan marks as never-delete.
    """
    covered = {file.path for file in files}
    extensions: dict[str, int] = {}
    for file in files:
        suffix = file.path.suffix.lower() or "(none)"
        extensions[suffix] = extensions.get(suffix, 0) + file.size_bytes

    largest = sorted(files, key=lambda file: file.size_bytes, reverse=True)[:SAMPLE_FILES]

    return Candidate(
        path=parent.path,
        name=parent.name,
        label=f"loose files in {parent.name}",
        size_bytes=sum(file.size_bytes for file in files),
        file_count=len(files),
        excluding=sorted(child.path for child in parent.children if child.path not in covered),
        extensions=dict(sorted(extensions.items(), key=lambda kv: kv[1], reverse=True)),
        largest_files=[FileSummary(name=f.name, size_bytes=f.size_bytes) for f in largest],
    )


def _describe(node: ScanNode, excluding: set[Path] | None = None) -> Candidate:
    """Describe a candidate well enough to judge without opening anything.

    *excluding* names files already broken out as candidates of their own, so a
    directory describes only what is left of it and no byte is counted twice.
    """
    if not node.is_dir:
        suffix = node.path.suffix.lower() or "(none)"
        return Candidate(
            path=node.path,
            name=node.name,
            label=node.name,
            size_bytes=node.size_bytes,
            file_count=1,
            extensions={suffix: node.size_bytes},
            largest_files=[FileSummary(name=node.name, size_bytes=node.size_bytes)],
        )

    skip = excluding or set()
    files = [child for child in _descendants(node) if not child.is_dir and child.path not in skip]

    extensions: dict[str, int] = {}
    for file in files:
        suffix = file.path.suffix.lower() or "(none)"
        extensions[suffix] = extensions.get(suffix, 0) + file.size_bytes

    largest = sorted(files, key=lambda file: file.size_bytes, reverse=True)[:SAMPLE_FILES]

    return Candidate(
        path=node.path,
        name=node.name,
        # Named as a remainder so nobody reads it as the whole directory — most of
        # which may be a file that is being judged separately.
        label=f"the rest of {node.name}" if skip else node.name,
        size_bytes=sum(file.size_bytes for file in files) if skip else node.size_bytes,
        file_count=len(files),
        excluding=sorted(skip),
        extensions=dict(sorted(extensions.items(), key=lambda kv: kv[1], reverse=True)),
        largest_files=[FileSummary(name=f.name, size_bytes=f.size_bytes) for f in largest],
    )
