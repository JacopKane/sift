"""Steps for tests/features/safety.feature.

Every assertion is a regression guard for a bug that happened. The pipeline runs
once and all of them are checked against that one result.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytest
from pytest_bdd import scenarios, then, when

from sift.classify import classify
from sift.config import settings
from sift.models import Candidate, Classification, Plan, ScanNode, Verdict
from sift.plan import build_plan
from sift.survey import candidates_for_model, survey
from tests.machine import Machine

scenarios("safety.feature")


@dataclass
class Pipeline:
    tree: ScanNode
    candidates: list[Candidate]
    judgements: list[Classification]
    plan: Plan
    chart: ScanNode


@when("the whole pipeline runs", target_fixture="run")
def the_whole_pipeline_runs(machine: Machine) -> Pipeline:
    if not settings().api_key:
        pytest.skip(f"no API key configured for provider {settings().provider}")

    from sift.api.app import _apply

    tree = list(survey(machine.root, home=machine.root))[-1]
    candidates = candidates_for_model(tree)
    judgements = classify(candidates)
    plan = build_plan(tree, judgements)
    # Ordering matters and is asserted below: the plan is built before verdicts
    # are written back, or every judged item counts twice.
    _apply(tree, judgements)
    return Pipeline(tree, candidates, judgements, plan, tree)


def _nodes(tree: ScanNode) -> list[ScanNode]:
    found, stack = [], [tree]
    while stack:
        node = stack.pop()
        found.append(node)
        stack.extend(node.children)
    return found


def _source_dirs(machine: Machine) -> list[Path]:
    return [machine.path("Sites/client-app/src"), machine.path("Sites/old-project/src")]


@then("source code is never proposed for deletion")
def source_never_proposed(run: Pipeline, machine: Machine) -> None:
    proposed = {path for item in run.plan.proposals for path in item.paths}
    for source in _source_dirs(machine):
        assert source not in proposed, f"{source} was proposed for deletion"
        swept = {
            path
            for item in run.plan.proposals
            for path in item.paths
            if path in source.parents and source not in item.excluding
        }
        assert not swept, f"reclaiming {swept} would take {source} with it"


@then("source code is settled without asking a model")
def source_settled_by_rule(run: Pipeline, machine: Machine) -> None:
    offered = {candidate.path for candidate in run.candidates}
    for source in _source_dirs(machine):
        node = next(n for n in _nodes(run.tree) if n.path == source)
        assert node.verdict is Verdict.IRREPLACEABLE, (
            "source must be settled by rule, so the answer cannot change with the model"
        )
        assert source not in offered, f"{source} was put to a model"


@then("nothing holding irreplaceable things is called disposable")
def mixed_never_disposable(run: Pipeline) -> None:
    for item in run.plan.proposals:
        if item.verdict is not Verdict.REGENERABLE:
            continue
        for path in item.paths:
            inside = [
                node
                for node in _nodes(run.tree)
                if node.verdict is Verdict.IRREPLACEABLE
                and path in node.path.parents
                and node.path not in item.excluding
            ]
            assert not inside, f"{path} is called disposable but holds {inside[0].path}"


@then("the plan never accounts for more bytes than the disk holds")
def plan_adds_up(run: Pipeline) -> None:
    claimed = sum(item.size_bytes for item in [*run.plan.proposals, *run.plan.irreplaceable])
    assert claimed <= run.plan.surveyed_bytes, (
        f"the plan claims {claimed} bytes of a {run.plan.surveyed_bytes} byte survey"
    )


@then("nothing proposed would delete something kept back")
def nothing_proposed_sweeps_protected(run: Pipeline) -> None:
    kept = {path for item in run.plan.irreplaceable for path in item.paths}
    for item in run.plan.proposals:
        for path in item.paths:
            swept = {
                other
                for other in kept
                if (path in other.parents or path == other) and other not in item.excluding
            }
            assert not swept, f"reclaiming {path} would delete {swept}"


@then("everything called regenerable says how to get it back")
def regenerable_says_how(run: Pipeline) -> None:
    for item in run.plan.proposals:
        if item.verdict is Verdict.REGENERABLE:
            assert item.restore.strip(), f"{item.label} is disposable with no way back"


@then("the map is coloured by what was actually decided")
def map_is_coloured(run: Pipeline) -> None:
    verdicts = {node.verdict for node in _nodes(run.chart) if node.verdict}
    assert len(verdicts) > 1, f"the whole map draws in one colour: {verdicts}"

    judged = {judgement.path for judgement in run.judgements}
    coloured = {node.path for node in _nodes(run.chart) if node.verdict}
    assert judged & coloured, "nothing the model decided reached the map"


@then("no verdict was invented for something never offered")
def no_invented_verdicts(run: Pipeline) -> None:
    offered = {candidate.path for candidate in run.candidates}
    for judgement in run.judgements:
        assert judgement.path in offered, f"{judgement.path} was never offered to the model"


@then("the reclaimable total promises only what can be rebuilt")
def reclaimable_is_only_regenerable(run: Pipeline) -> None:
    expected = sum(
        item.size_bytes for item in run.plan.proposals if item.verdict is Verdict.REGENERABLE
    )
    assert run.plan.reclaimable_bytes == expected, (
        "reclaimable must count only what can be rebuilt; anything else promises "
        "space that may be somebody's only copy"
    )
