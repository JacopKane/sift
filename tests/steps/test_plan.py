"""Steps for tests/features/plan.feature.

No network here: the plan is arithmetic and grouping over verdicts that already
exist, so these run on every commit.
"""

from __future__ import annotations

from pytest_bdd import given, parsers, scenarios, then, when

from sift.models import Classification, Plan, ScanNode, Verdict
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


@when("I build a plan from what the model said", target_fixture="plan")
def i_build_a_plan_from_judgements(
    reports: list[ScanNode], classified: list[Classification]
) -> Plan:
    return build_plan(tree_of(reports), classified)


@then("the plan accounts for no more than was surveyed")
def accounts_for_no_more_than_surveyed(plan: Plan) -> None:
    claimed = sum(item.size_bytes for item in [*plan.proposals, *plan.irreplaceable])
    assert claimed <= plan.surveyed_bytes, (
        f"the plan claims {claimed} bytes of a {plan.surveyed_bytes} byte survey, "
        "so something is counted twice"
    )


@then("nothing proposed contains something kept back")
def nothing_proposed_contains_irreplaceable(plan: Plan) -> None:
    kept_back = {path for item in plan.irreplaceable for path in item.paths}
    for item in plan.proposals:
        for path in item.paths:
            swept_up = {
                kept for kept in kept_back if path in kept.parents and kept not in item.excluding
            }
            assert not swept_up, (
                f"reclaiming {path} would delete {swept_up}, which the plan says cannot be replaced"
            )


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


@then(parsers.parse('"{relpath}" is listed as irreplaceable'))
def listed_as_irreplaceable(plan: Plan, machine: Machine, relpath: str) -> None:
    kept_back = {path for item in plan.irreplaceable for path in item.paths}
    assert machine.path(relpath) in kept_back


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


@then("neither total counts anything irreplaceable")
def irreplaceable_not_counted(plan: Plan) -> None:
    unrecoverable = sum(item.size_bytes for item in plan.irreplaceable)
    assert unrecoverable > 0, "the fixture should have something that cannot be replaced"

    # The three buckets are disjoint, so together they cannot exceed the survey.
    # If irreplaceable bytes leaked into either total this overshoots.
    counted = plan.reclaimable_bytes + plan.needs_review_bytes + unrecoverable
    assert counted <= plan.surveyed_bytes

    proposed_paths = {path for item in plan.proposals for path in item.paths}
    protected_paths = {path for item in plan.irreplaceable for path in item.paths}
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


@when(parsers.parse('"{relpath}" is judged to rebuild itself'), target_fixture="judgement")
def judged_to_rebuild(machine: Machine, reports: list[ScanNode], relpath: str) -> Classification:
    node = next(n for n in _all(reports[-1]) if n.path == machine.path(relpath))
    return Classification(
        path=node.path,
        verdict=Verdict.REGENERABLE,
        label=node.name,
        restore="download it again",
        size_bytes=node.size_bytes,
        reason="a real judgement, shaped exactly as the model returns one",
    )


@when(
    "the plan is built, the verdicts written back, and the plan built again",
    target_fixture="both",
)
def built_twice(reports: list[ScanNode], judgement: Classification) -> tuple[Plan, Plan]:
    tree = reports[-1]
    first = build_plan(tree, [judgement])
    # What the survey does next, and what any later rebuild has to survive: the
    # model's verdicts written onto the tree, where they become indistinguishable
    # from the catalog's.
    for node in _all(tree):
        if node.path == judgement.path and node.verdict is None:
            node.verdict = judgement.verdict
            node.label = judgement.label
            node.restore = judgement.restore
    return first, build_plan(tree, [judgement])


@then("both plans account for the same bytes")
def both_account_the_same(both: tuple[Plan, Plan]) -> None:
    first, again = both
    assert _claimed(first) == _claimed(again), (
        f"rebuilding after a reclaim gave {_claimed(again)} where the survey gave "
        f"{_claimed(first)} — every judged item counted once from the catalog pass "
        "and once from the model pass"
    )


@then("neither lists anything twice")
def neither_lists_twice(both: tuple[Plan, Plan]) -> None:
    for plan in both:
        paths = [p for item in [*plan.proposals, *plan.irreplaceable] for p in item.paths]
        assert len(paths) == len(set(paths)), f"listed twice: {paths}"


def _claimed(plan: Plan) -> int:
    return sum(item.size_bytes for item in [*plan.proposals, *plan.irreplaceable])


def _all(tree: ScanNode) -> list[ScanNode]:
    found, stack = [], [tree]
    while stack:
        node = stack.pop()
        found.append(node)
        stack.extend(node.children)
    return found
