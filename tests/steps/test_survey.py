"""Steps for tests/features/survey.feature."""

from __future__ import annotations

from pytest_bdd import parsers, scenarios, then

from sift.models import ScanNode
from tests.machine import Machine
from tests.steps.conftest import all_nodes, index_of, node_at, tree_of

scenarios("survey.feature")


@then("every directory equals the sum of what is beneath it")
def directories_sum_their_children(reports: list[ScanNode]) -> None:
    for node in all_nodes(tree_of(reports)):
        if not node.is_dir:
            continue
        if node.verdict is not None:
            # Counted whole rather than explored: the catalog already named it, so
            # its total is measured directly and it has no children to sum.
            continue
        assert node.size_bytes == sum(child.size_bytes for child in node.children)
        assert node.allocated_bytes == sum(child.allocated_bytes for child in node.children)


@then(parsers.parse('"{relpath}" is marked unreadable'))
def marked_unreadable(reports: list[ScanNode], machine: Machine, relpath: str) -> None:
    node = node_at(tree_of(reports), machine.path(relpath))
    assert node is not None
    assert node.unreadable is True


@then("every file occupies at least its own size on disk")
def files_occupy_at_least_their_size(reports: list[ScanNode]) -> None:
    files = [node for node in all_nodes(tree_of(reports)) if not node.is_dir]
    assert files, "the fixture should have produced files"
    for node in files:
        assert node.allocated_bytes >= node.size_bytes


@then(parsers.parse('"{earlier}" is reported before "{later}"'))
def reported_before(reports: list[ScanNode], machine: Machine, earlier: str, later: str) -> None:
    assert index_of(reports, machine.path(earlier)) < index_of(reports, machine.path(later))


@then(parsers.parse('"{relpath}" is reported before the machine root'))
def reported_before_the_root(reports: list[ScanNode], machine: Machine, relpath: str) -> None:
    assert index_of(reports, machine.path(relpath)) < len(reports) - 1


@then("the machine root is reported last")
def root_reported_last(reports: list[ScanNode], machine: Machine) -> None:
    assert reports[-1].path == machine.root


@then("the last report carries the whole tree")
def last_report_carries_the_tree(reports: list[ScanNode], machine: Machine) -> None:
    tree = tree_of(reports)
    assert tree.size_bytes == machine.readable_bytes
    # Everything reported appears in the tree exactly once, and vice versa.
    assert len(list(all_nodes(tree))) == len(reports)


@then("every file says when it was last opened")
def files_say_when_last_opened(reports: list[ScanNode]) -> None:
    files = [node for node in _every(reports[-1]) if not node.is_dir]
    assert files, "the fixture should hold files"
    assert all(node.last_used is not None for node in files), (
        "'you have not opened this in three years' is the most persuasive thing a "
        "disk tool can say, and it is one field on a stat call we already make"
    )


@then("a directory says when anything inside it was last opened")
def directories_carry_the_newest(reports: list[ScanNode]) -> None:
    for node in _every(reports[-1]):
        if not node.is_dir or not node.children:
            continue
        newest = max(
            (child.last_used for child in node.children if child.last_used is not None),
            default=None,
        )
        if newest is None:
            continue
        assert node.last_used is not None and node.last_used >= newest, (
            f"{node.name} claims to be older than something inside it — a folder is "
            "as recently used as its most recently used file, or you archive live work"
        )


def _every(tree: ScanNode) -> list[ScanNode]:
    found, stack = [], [tree]
    while stack:
        node = stack.pop()
        found.append(node)
        stack.extend(node.children)
    return found
