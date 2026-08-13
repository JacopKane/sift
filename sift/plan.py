"""Turning verdicts into a plan.

Grouping is the whole job. Forty-seven node_modules directories scattered across
three projects are one decision, not forty-seven, and the rule that recognised
them is what says so.
"""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from pathlib import Path

from sift.models import Classification, Plan, PlanItem, ScanNode, Verdict

CANNOT_RESTORE = "cannot be restored"


def build_plan(
    tree: ScanNode,
    classifications: Sequence[Classification] = (),
) -> Plan:
    """Assemble what the catalog settled and what the model judged into one plan."""
    items = [*_from_catalog(tree), *_from_model(tree, classifications)]

    proposals = sorted(
        (item for item in items if item.verdict is not Verdict.IRREPLACEABLE),
        key=lambda item: item.size_bytes,
        reverse=True,
    )
    protected = sorted(
        (item for item in items if item.verdict is Verdict.IRREPLACEABLE),
        key=lambda item: item.size_bytes,
        reverse=True,
    )

    return Plan(
        proposals=proposals,
        protected=protected,
        reclaimable_bytes=_total(proposals, Verdict.REGENERABLE),
        needs_review_bytes=_total(proposals, Verdict.REVIEW),
        surveyed_bytes=tree.size_bytes,
    )


def _total(items: Sequence[PlanItem], verdict: Verdict) -> int:
    return sum(item.size_bytes for item in items if item.verdict is verdict)


def _from_catalog(tree: ScanNode) -> Iterator[PlanItem]:
    grouped: dict[str, list[ScanNode]] = {}
    for node in _topmost_settled(tree):
        # Falling back to the path keeps a rule-less node its own group rather than
        # silently merging every unlabelled node into one.
        grouped.setdefault(node.rule_id or str(node.path), []).append(node)

    for nodes in grouped.values():
        first = nodes[0]
        assert first.verdict is not None  # _topmost_settled only yields settled nodes
        yield PlanItem(
            label=first.label or first.name,
            verdict=first.verdict,
            size_bytes=sum(node.size_bytes for node in nodes),
            paths=[node.path for node in nodes],
            restore=first.restore or CANNOT_RESTORE,
            restore_time=first.restore_time,
            rule_id=first.rule_id,
        )


def _from_model(tree: ScanNode, classifications: Sequence[Classification]) -> Iterator[PlanItem]:
    for classification in classifications:
        if _node_at(tree, classification.path) is None:
            continue  # the model answered about something that isn't on this disk
        yield PlanItem(
            label=classification.label or classification.path.name,
            verdict=classification.verdict,
            # The candidate's size, not the node's: a remainder covers less than the
            # directory it is named after.
            size_bytes=classification.size_bytes,
            paths=[classification.path],
            excluding=classification.excluding,
            restore=classification.restore,
            reason=classification.reason,
        )


def _topmost_settled(tree: ScanNode) -> Iterator[ScanNode]:
    """Every settled node whose ancestors are all unsettled.

    Descending past a settled node would count the same bytes twice — once for the
    cache directory, once for everything inside it.
    """
    stack = list(tree.children)
    while stack:
        node = stack.pop()
        if node.verdict is not None:
            yield node
        else:
            stack.extend(node.children)


def _node_at(tree: ScanNode, path: Path) -> ScanNode | None:
    stack = [tree]
    while stack:
        node = stack.pop()
        if node.path == path:
            return node
        stack.extend(node.children)
    return None
