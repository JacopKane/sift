"""Steps for tests/features/reclaim.feature.

Real moves on a real temp filesystem. Nothing here is simulated: if a scenario
passes, the bytes actually moved and actually came back.
"""

from __future__ import annotations

import platform
import shutil
from pathlib import Path

from pytest_bdd import scenarios, then, when

from sift.models import ScanNode, Verdict
from sift.quarantine import Quarantine, Receipt, native_bin

scenarios("reclaim.feature")


@when("sift picks where reclaimed things go", target_fixture="chosen_bin")
def sift_picks_a_bin() -> Path:
    return native_bin()


@when("the bin is emptied by something other than sift")
def the_bin_is_emptied(held: Quarantine) -> None:
    # Exactly what happens when someone empties the Trash from Finder while a
    # basket is still on the receipt. Ours is the record; theirs are the bytes.
    for entry in held.held():
        if entry.held_at.exists():
            shutil.rmtree(entry.held_at, ignore_errors=True)
            entry.held_at.unlink(missing_ok=True)


@then("it is a bin the desktop already empties, not one we invented")
def bin_is_the_platforms_own(chosen_bin: Path) -> None:
    if platform.system() == "Darwin":
        assert chosen_bin.exists(), (
            f"{chosen_bin} is not there, so it is not the bin this machine already has"
        )
        assert ".sift" not in chosen_bin.parts, (
            f"{chosen_bin} is a bin we invented; macOS already has one and the "
            "person already knows how to empty it"
        )
    else:
        # No catalog for this platform yet, so nothing can reach the bin anyway.
        # Falling back to our own is the honest answer, not a half-native one.
        assert ".sift" in chosen_bin.parts


@then("it says what it could not bring back")
def says_what_it_could_not(undone: Receipt) -> None:
    assert undone.refused, (
        "the bytes were emptied from under us and undo said nothing — silence here "
        "reads as 'restored' when nothing was"
    )


def _verdict_for(tree: ScanNode, path: Path) -> Verdict | None:
    stack = [tree]
    while stack:
        node = stack.pop()
        if node.path == path:
            return node.verdict
        stack.extend(node.children)
    return None
