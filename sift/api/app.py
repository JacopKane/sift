"""HTTP surface.

The scanner reports every file; this layer forwards only directories. Deciding
what is worth sending over a wire is an interface concern and has no business in
a filesystem library.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from sse_starlette.sse import EventSourceResponse

from sift.classify import classify
from sift.models import Classification, Plan, ScanNode
from sift.plan import build_plan
from sift.scanner import boot_volume_exclusions
from sift.survey import candidates_for_model, survey

PAGE = Path(__file__).parent / "index.html"

MAX_DEPTH = 4
"""How deep the chart is drawn. Past this, arcs are thinner than a pixel."""

MIN_SHARE = 0.004
"""Children smaller than this fraction of the whole are folded into their parent
rather than drawn as slivers nobody can click."""


def create_app(home: Path | None = None) -> FastAPI:
    app = FastAPI(title="Sift")

    @app.get("/", response_class=HTMLResponse)
    async def index() -> HTMLResponse:
        return HTMLResponse(PAGE.read_text(encoding="utf-8"))

    @app.get("/api/survey")
    async def survey_endpoint(root: str, judge: bool = False) -> EventSourceResponse:
        return EventSourceResponse(_stream(Path(root).expanduser(), home, judge))

    return app


def _stream(root: Path, home: Path | None, judge: bool = False) -> Iterator[dict[str, str]]:
    # A whole-volume survey needs the exclusions; a project folder needs none, and
    # applying them anyway costs nothing.
    exclude = boot_volume_exclusions() if root == Path("/") else ()

    tree: ScanNode | None = None
    for node in survey(root, exclude=exclude, home=home):
        tree = node
        if node.is_dir:
            yield {"event": "directory", "data": json.dumps(_report(node))}

    assert tree is not None  # survey always reports the root last

    judgements: list[Classification] = []
    if judge:
        candidates = candidates_for_model(tree)
        if candidates:
            yield {
                "event": "judging",
                "data": json.dumps({"count": len(candidates)}),
            }
            judgements = classify(candidates)

    plan = build_plan(tree, judgements)
    yield {
        "event": "done",
        "data": json.dumps(
            {"plan": plan.model_dump(mode="json"), "chart": _chart(tree, tree.size_bytes)}
        ),
    }


def _report(node: ScanNode) -> dict[str, Any]:
    return {
        "path": str(node.path),
        "name": node.name,
        "size_bytes": node.size_bytes,
        "label": node.label,
        "verdict": node.verdict.value if node.verdict else None,
        "restore": node.restore,
        "unreadable": node.unreadable,
    }


def _chart(node: ScanNode, total: int, depth: int = 0) -> dict[str, Any]:
    """The tree, pruned to what can actually be drawn.

    Files are included, not just directories. The largest single thing on a real
    Downloads folder is usually one video, and a map that omitted it would show
    nine gigabytes as empty space.
    """
    children: list[dict[str, Any]] = []
    if depth < MAX_DEPTH and total > 0:
        children = [
            _chart(child, total, depth + 1)
            for child in sorted(node.children, key=lambda c: c.size_bytes, reverse=True)
            if child.size_bytes / total >= MIN_SHARE
        ]

    return {
        "name": node.name,
        "path": str(node.path),
        "size_bytes": node.size_bytes,
        "verdict": node.verdict.value if node.verdict else None,
        "label": node.label,
        "unreadable": node.unreadable,
        "children": children,
    }


__all__ = ["Plan", "create_app"]
