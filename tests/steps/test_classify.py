"""Steps for tests/features/classify.feature.

These hit the real model. Assertions are about properties, never exact strings,
because real responses vary between runs.
"""

from __future__ import annotations

from pytest_bdd import parsers, scenarios, then

from sift.models import Classification, ScanNode, Verdict
from sift.survey import candidates_for_model
from tests.machine import Machine
from tests.steps.conftest import CallCounter, tree_of

scenarios("classify.feature")


def _for(classified: list[Classification], machine: Machine, relpath: str) -> Classification:
    wanted = machine.path(relpath)
    found = next((c for c in classified if c.path == wanted), None)
    assert found is not None, f"the model returned nothing for {relpath}"
    return found


@then("every candidate is classified")
def every_candidate_classified(classified: list[Classification], reports: list[ScanNode]) -> None:
    offered = {c.path for c in candidates_for_model(tree_of(reports))}
    assert {c.path for c in classified} == offered


@then("every classification gives a reason")
def every_classification_gives_a_reason(classified: list[Classification]) -> None:
    for item in classified:
        assert item.reason.strip(), f"{item.path} came back with an empty reason"


@then("no classification invents a directory that was never offered")
def no_invented_directories(classified: list[Classification], reports: list[ScanNode]) -> None:
    offered = {c.path for c in candidates_for_model(tree_of(reports))}
    for item in classified:
        assert item.path in offered, f"{item.path} was never offered to the model"


@then(parsers.parse('"{relpath}" is not regenerable'))
def not_regenerable(classified: list[Classification], machine: Machine, relpath: str) -> None:
    item = _for(classified, machine, relpath)
    assert item.verdict is not Verdict.REGENERABLE, (
        f"{relpath} was called disposable: {item.reason}"
    )


@then(parsers.parse('"{relpath}" needs review'))
def needs_review(classified: list[Classification], machine: Machine, relpath: str) -> None:
    item = _for(classified, machine, relpath)
    assert item.verdict is Verdict.REVIEW, (
        f"{relpath} holds both disposable and irreplaceable things, so a blanket "
        f"{item.verdict.value} either risks the only copy or hides reclaimable space: {item.reason}"
    )


@then(parsers.parse('"{relpath}" is irreplaceable'))
def is_irreplaceable(classified: list[Classification], machine: Machine, relpath: str) -> None:
    assert _for(classified, machine, relpath).verdict is Verdict.IRREPLACEABLE


@then("anything called regenerable says how to restore it")
def regenerable_says_how(classified: list[Classification]) -> None:
    for item in classified:
        if item.verdict is Verdict.REGENERABLE:
            assert item.restore and item.restore.strip(), (
                f"{item.path} is called regenerable with no way to get it back"
            )


@then("the model was called once")
def model_called_once(counter: CallCounter) -> None:
    assert counter.calls == 1, f"expected one batched call, made {counter.calls}"


@then(parsers.parse('the reason given for "{relpath}" refers to what is inside it'))
def reason_refers_to_contents(
    classified: list[Classification], machine: Machine, relpath: str
) -> None:
    reason = _for(classified, machine, relpath).reason.lower()
    # The payload names .mp4, .zip, .dmg and .pdf; a reason drawn from the actual
    # contents should mention at least one of them rather than the folder's name.
    signals = ["mp4", "video", "recording", "zip", "archive", "dmg", "installer", "pdf"]
    assert any(signal in reason for signal in signals), reason
