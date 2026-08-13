"""Steps for tests/features/catalog.feature."""

from __future__ import annotations

from pytest_bdd import given, parsers, scenarios, then

from sift.models import Candidate, ScanNode, Verdict
from sift.survey import candidates_for_model
from tests.machine import KB, Machine
from tests.steps.conftest import node_at, tree_of

scenarios("catalog.feature")


@given(parsers.parse('a folder "{relpath}" holding {size:d} KB'))
def a_folder_holding(machine: Machine, relpath: str, size: int) -> None:
    target = machine.path(relpath) / "contents.bin"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(b"\0" * (size * KB))


@given(parsers.parse('a file "{relpath}" of {size:d} KB'))
def a_file_of(machine: Machine, relpath: str, size: int) -> None:
    target = machine.path(relpath)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(b"\0" * (size * KB))


def _node(reports: list[ScanNode], machine: Machine, relpath: str) -> ScanNode:
    node = node_at(tree_of(reports), machine.path(relpath))
    assert node is not None, f"{relpath} was not surveyed"
    return node


def _candidates(reports: list[ScanNode]) -> list[Candidate]:
    return candidates_for_model(tree_of(reports))


def _candidate(reports: list[ScanNode], machine: Machine, relpath: str) -> Candidate:
    wanted = machine.path(relpath)
    found = next((c for c in _candidates(reports) if c.path == wanted), None)
    assert found is not None, f"{relpath} was not offered to the model"
    return found


# ------------------------------------------------------- catalog verdicts ----


@then(parsers.parse('"{relpath}" is regenerable'))
def is_regenerable(reports: list[ScanNode], machine: Machine, relpath: str) -> None:
    assert _node(reports, machine, relpath).verdict is Verdict.REGENERABLE


@then(parsers.parse('"{relpath}" is irreplaceable'))
def is_irreplaceable(reports: list[ScanNode], machine: Machine, relpath: str) -> None:
    assert _node(reports, machine, relpath).verdict is Verdict.IRREPLACEABLE


@then(parsers.parse('"{relpath}" can be restored with "{command}"'))
def can_be_restored_with(
    reports: list[ScanNode], machine: Machine, relpath: str, command: str
) -> None:
    assert _node(reports, machine, relpath).restore == command


@then(parsers.parse('"{relpath}" is not recognised'))
def is_not_recognised(reports: list[ScanNode], machine: Machine, relpath: str) -> None:
    assert _node(reports, machine, relpath).verdict is None


@then(parsers.parse('"{relpath}" is never proposed for deletion'))
def never_proposed(reports: list[ScanNode], machine: Machine, relpath: str) -> None:
    assert _node(reports, machine, relpath).verdict is Verdict.IRREPLACEABLE
    assert machine.path(relpath) not in {c.path for c in _candidates(reports)}


@then(parsers.parse('"{relpath}" reports its full size'))
def reports_full_size(reports: list[ScanNode], machine: Machine, relpath: str) -> None:
    node = _node(reports, machine, relpath)
    on_disk = sum(
        path.stat().st_size for path in machine.path(relpath).rglob("*") if path.is_file()
    )
    assert on_disk > 0, "the fixture directory should contain something"
    assert node.size_bytes == on_disk


@then(parsers.parse('nothing inside "{relpath}" was explored'))
def nothing_inside_explored(reports: list[ScanNode], machine: Machine, relpath: str) -> None:
    settled = machine.path(relpath)
    assert not _node(reports, machine, relpath).children, (
        "a directory the catalog already named needs its total, not its contents"
    )
    inside = [node for node in reports if settled in node.path.parents]
    assert not inside, f"{len(inside)} nodes were built inside an already-settled directory"


# ------------------------------------------------ what reaches the model ----


@then(parsers.parse('"{relpath}" is a candidate'))
def is_a_candidate(reports: list[ScanNode], machine: Machine, relpath: str) -> None:
    _candidate(reports, machine, relpath)


@then(parsers.parse('"{relpath}" is not a candidate'))
def is_not_a_candidate(reports: list[ScanNode], machine: Machine, relpath: str) -> None:
    assert machine.path(relpath) not in {c.path for c in _candidates(reports)}


@then("no candidate was recognised by the catalog")
def no_candidate_was_recognised(reports: list[ScanNode], machine: Machine) -> None:
    tree = tree_of(reports)
    for candidate in _candidates(reports):
        node = node_at(tree, candidate.path)
        assert node is not None
        assert node.verdict is None, f"{candidate.path} was already settled by the catalog"


@then("candidates are offered largest first")
def candidates_largest_first(reports: list[ScanNode]) -> None:
    sizes = [c.size_bytes for c in _candidates(reports)]
    assert sizes == sorted(sizes, reverse=True)


@then("no candidate counts bytes another candidate already counted")
def candidates_are_disjoint(reports: list[ScanNode]) -> None:
    # A big file and the directory it sits in can both be candidates — that is the
    # point — but between them they must add up to no more than what is there.
    candidates = _candidates(reports)
    assert sum(c.size_bytes for c in candidates) <= tree_of(reports).size_bytes


@then(parsers.parse('the candidate "{relpath}" leaves out "{name}"'))
def candidate_leaves_out(
    reports: list[ScanNode], machine: Machine, relpath: str, name: str
) -> None:
    candidate = _candidate(reports, machine, relpath)
    assert name not in {file.name for file in candidate.largest_files}
    broken_out = _node(reports, machine, f"{relpath}/{name}")
    assert candidate.size_bytes < broken_out.size_bytes, (
        "the remainder should be what is left after the big file, not the whole directory"
    )


@then(parsers.parse("the model is asked about fewer than {limit:d} directories"))
def asked_about_fewer_than(reports: list[ScanNode], limit: int) -> None:
    assert len(_candidates(reports)) < limit


@then(parsers.parse('the candidate "{relpath}" reports its largest files'))
def candidate_reports_largest_files(
    reports: list[ScanNode], machine: Machine, relpath: str
) -> None:
    candidate = _candidate(reports, machine, relpath)
    assert candidate.largest_files, "a candidate with files should name some of them"
    sizes = [f.size_bytes for f in candidate.largest_files]
    assert sizes == sorted(sizes, reverse=True)


@then(parsers.parse('the candidate "{relpath}" reports which extensions fill it'))
def candidate_reports_extensions(reports: list[ScanNode], machine: Machine, relpath: str) -> None:
    candidate = _candidate(reports, machine, relpath)
    assert ".dmg" in candidate.extensions
    assert ".pdf" in candidate.extensions
