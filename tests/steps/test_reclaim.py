"""Steps for tests/features/reclaim.feature.

Real moves on a real temp filesystem. Nothing here is simulated: if a scenario
passes, the bytes actually moved and actually came back.
"""

from __future__ import annotations

from pathlib import Path

from pytest_bdd import scenarios

from sift.models import ScanNode, Verdict

scenarios("reclaim.feature")


def _verdict_for(tree: ScanNode, path: Path) -> Verdict | None:
    stack = [tree]
    while stack:
        node = stack.pop()
        if node.path == path:
            return node.verdict
        stack.extend(node.children)
    return None
