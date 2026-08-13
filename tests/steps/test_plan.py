"""Steps for tests/features/plan.feature.

No network here: the plan is arithmetic and grouping over verdicts that already
exist, so these run on every commit.
"""

from __future__ import annotations

from pytest_bdd import given, parsers, scenarios, then, when

from sift.models import Plan, ScanNode, Verdict
from sift.plan import build_plan
from tests.machine import KB, Machine
from tests.steps.conftest import tree_of

scenarios("plan.feature")


@given(parsers.parse('a second project at "{relpath}" with its own node_modules'))
def a_second_project(machine: Machine, relpath: str) -> None:
    project = machine.path(relpath)
    (project / "node_modules" / "react").mkdir(parents=True, exist_ok=True)
    (project / "package.json").write_bytes(b"\0" * (2 * KB))
    (project / "node_modules" / "react" / "index.js").write_bytes(b"\0" * (500 * KB))


@when("I build a plan", target_fixture="plan")
def i_build_a_plan(reports: list[ScanNode]) -> Plan:
    return build_plan(tree_of(reports))


@then(parsers.parse('the plan has one proposal for "{label}"'))
def one_proposal_for(plan: Plan, label: str) -> None:
    matching = [item for item in plan.proposals if item.label == label]
    assert len(matching) == 1, f"expected one {label} proposal, got {len(matching)}"


@then(parsers.parse("that proposal covers {count:d} directories"))
def proposal_covers(plan: Plan, count: int) -> None:
    item = max(plan.proposals, key=lambda i: len(i.paths))
    assert len(item.paths) == count


@then("that proposal totals the size of both")
def proposal_totals_both(plan: Plan, reports: list[ScanNode]) -> None:
    tree = tree_of(reports)
    item = max(plan.proposals, key=lambda i: len(i.paths))
    expected = sum(_node_at(tree, path).size_bytes for path in item.paths)
    assert item.size_bytes == expected


def _node_at(tree: ScanNode, path: object) -> ScanNode:
    stack = [tree]
    while stack:
        node = stack.pop()
        if node.path == path:
            return node
        stack.extend(node.children)
    raise AssertionError(f"{path} is not in the survey")


@then("the proposals are ordered largest first")
def proposals_ordered(plan: Plan) -> None:
    sizes = [item.size_bytes for item in plan.proposals]
    assert sizes == sorted(sizes, reverse=True)


@then(parsers.parse('"{relpath}" is proposed'))
def is_proposed(plan: Plan, machine: Machine, relpath: str) -> None:
    proposed = {path for item in plan.proposals for path in item.paths}
    assert machine.path(relpath) in proposed


@then(parsers.parse('the reclaimable total counts "{relpath}" only once'))
def counted_only_once(plan: Plan, machine: Machine, reports: list[ScanNode], relpath: str) -> None:
    nested = _node_at(tree_of(reports), machine.path(relpath))
    parent_item = next(
        item for item in plan.proposals if machine.path(relpath).parent in item.paths
    )
    # The enclosing proposal already includes the nested directory's bytes; if the
    # nested one were also counted, the total would exceed the enclosing size.
    assert nested.size_bytes < parent_item.size_bytes
    assert plan.reclaimable_bytes == sum(
        item.size_bytes for item in plan.proposals if item.verdict is Verdict.REGENERABLE
    )


@then(parsers.parse('"{relpath}" is not proposed'))
def not_proposed(plan: Plan, machine: Machine, relpath: str) -> None:
    proposed = {path for item in plan.proposals for path in item.paths}
    assert machine.path(relpath) not in proposed


@then(parsers.parse('"{relpath}" is listed as protected'))
def listed_as_protected(plan: Plan, machine: Machine, relpath: str) -> None:
    protected = {path for item in plan.protected for path in item.paths}
    assert machine.path(relpath) in protected


@then("every proposal says how to restore it")
def every_proposal_says_how(plan: Plan) -> None:
    for item in plan.proposals:
        assert item.restore.strip(), f"{item.label} is proposed with no way back"


@then("the reclaimable total counts only what can be rebuilt")
def total_counts_only_regenerable(plan: Plan) -> None:
    expected = sum(
        item.size_bytes for item in plan.proposals if item.verdict is Verdict.REGENERABLE
    )
    assert plan.reclaimable_bytes == expected
    review = [item for item in plan.proposals if item.verdict is Verdict.REVIEW]
    assert review, "the fixture should leave something genuinely ambiguous"
    assert plan.reclaimable_bytes < sum(item.size_bytes for item in plan.proposals)


@then("what needs a human decision is counted separately")
def review_counted_separately(plan: Plan) -> None:
    expected = sum(item.size_bytes for item in plan.proposals if item.verdict is Verdict.REVIEW)
    assert plan.needs_review_bytes == expected
    assert plan.needs_review_bytes > 0


@then("neither total counts anything protected")
def protected_not_counted(plan: Plan) -> None:
    protected_bytes = sum(item.size_bytes for item in plan.protected)
    assert protected_bytes > 0, "the fixture should have something worth protecting"

    # The three buckets are disjoint, so together they cannot exceed the survey.
    # If protected bytes leaked into either total this overshoots.
    counted = plan.reclaimable_bytes + plan.needs_review_bytes + protected_bytes
    assert counted <= plan.surveyed_bytes

    proposed_paths = {path for item in plan.proposals for path in item.paths}
    protected_paths = {path for item in plan.protected for path in item.paths}
    assert not (proposed_paths & protected_paths)


@then("the reclaimable total is less than everything surveyed")
def total_less_than_surveyed(plan: Plan) -> None:
    assert 0 < plan.reclaimable_bytes < plan.surveyed_bytes


@then("no proposal covers a path inside another proposal")
def no_nested_proposals(plan: Plan) -> None:
    proposed = {path for item in plan.proposals for path in item.paths}
    for path in proposed:
        overlap = proposed & set(path.parents)
        assert not overlap, f"{path} sits inside {overlap}, so it would be counted twice"


@then("nothing irreplaceable is proposed")
def nothing_irreplaceable_proposed(plan: Plan) -> None:
    for item in plan.proposals:
        assert item.verdict is not Verdict.IRREPLACEABLE
