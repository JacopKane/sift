"""HTTP surface.

The scanner reports every file; this layer forwards only directories. Deciding
what is worth sending over a wire is an interface concern and has no business in
a filesystem library.
"""

from __future__ import annotations

import json
from collections.abc import Iterator, Sequence
from pathlib import Path
from typing import Any, cast

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from sift.ask import ask
from sift.basket import Basket, item_for
from sift.catalog import load_catalog
from sift.classify import classify
from sift.duplicates import find_duplicates
from sift.models import Classification, Plan, ScanNode, Verdict
from sift.plan import build_plan
from sift.quarantine import Quarantine
from sift.scanner import boot_volume_exclusions
from sift.survey import candidates_for_model, survey

STATIC = Path(__file__).parent / "static"
PAGE = STATIC / "index.html"
"""The built SvelteKit app.

Committed rather than built on demand, so `uv run uvicorn` works in a fresh clone
with no npm step. Rebuild with `npm run build` in web/ after changing the
frontend."""

MAX_DEPTH = 4
"""How deep the chart is drawn. Past this, arcs are thinner than a pixel."""

MIN_SHARE = 0.004
"""Children smaller than this fraction of the whole are folded into their parent
rather than drawn as slivers nobody can click."""


class Question(BaseModel):
    root: str
    prompt: str


class Basketed(BaseModel):
    root: str
    path: str


class Dropped(BaseModel):
    """A folder the browser walked itself.

    Names and sizes only — the bytes never leave the machine, and the server never
    touches its own disk to answer.
    """

    name: str
    files: list[DroppedFile]


class DroppedFile(BaseModel):
    path: str
    size_bytes: int


def create_app(home: Path | None = None, quarantine: Path | None = None) -> FastAPI:
    app = FastAPI(title="Sift")
    held = Quarantine(quarantine) if quarantine else Quarantine.native()

    # The last survey per root, so a question can be answered without walking the
    # disk again. A local single-user tool; nothing here needs a session store.
    surveyed: dict[str, ScanNode] = {}
    # Kept beside the tree so the plan can be rebuilt after something is
    # reclaimed without asking the model the same question twice.
    judged: dict[str, list[Classification]] = {}
    basket = Basket()

    @app.get("/", response_class=HTMLResponse)
    async def index() -> HTMLResponse:
        return HTMLResponse(PAGE.read_text(encoding="utf-8"))

    # Mounted last in create_app so the API routes above always win.
    app.mount("/_app", StaticFiles(directory=STATIC / "_app"), name="assets")

    # Everything below is `def`, not `async def`, and deliberately so. These
    # handlers walk disks, hash gigabytes and wait on a model; a coroutine doing
    # that holds the event loop, and one duplicate scan is enough to freeze the
    # page, the survey stream and every other request until it finishes. Declared
    # synchronous, Starlette runs them in its worker pool and the interface stays
    # answerable while they work.
    @app.get("/api/survey")
    async def survey_endpoint(root: str, judge: bool = False) -> EventSourceResponse:
        return EventSourceResponse(_stream(Path(root).expanduser(), home, judge, surveyed, judged))

    @app.post("/api/ask")
    def ask_endpoint(question: Question) -> dict[str, Any]:
        tree = surveyed.get(str(Path(question.root).expanduser()))
        if tree is None:
            raise HTTPException(409, "Survey that folder first, then ask about it.")

        try:
            selection = ask(tree, question.prompt)
        except Exception as failure:
            detail = str(failure)
            if "RESOURCE_EXHAUSTED" in detail or "429" in detail:
                raise HTTPException(
                    429,
                    "The model is rate limited right now. Wait a minute and ask again.",
                ) from failure
            raise HTTPException(502, f"The model could not answer: {detail[:200]}") from failure
        sizes = _sizes(tree)
        chosen = [
            {"path": str(path), "name": path.name, "size_bytes": sizes.get(path, 0)}
            for path in selection.paths
        ]
        chosen.sort(key=lambda item: cast(int, item["size_bytes"]), reverse=True)

        return {
            "reason": selection.reason,
            "selected": chosen,
            "irreplaceable": [str(path) for path in selection.irreplaceable],
            "total_bytes": sum(cast(int, item["size_bytes"]) for item in chosen),
        }

    @app.post("/api/basket")
    def basket_add(request: Basketed) -> dict[str, Any]:
        tree = _surveyed_or_409(surveyed, request.root)
        # Nothing is refused. The verdict comes back with the item so the browser
        # can say what it is; deciding is the person's, and emptying is a separate
        # act with a countdown behind it.
        basket.add(item_for(tree, Path(request.path)))
        return _basket_state(basket)

    @app.delete("/api/basket")
    def basket_clear() -> dict[str, Any]:
        basket.clear()
        return _basket_state(basket)

    @app.post("/api/basket/empty")
    def basket_empty(root: str) -> dict[str, Any]:
        tree = _surveyed_or_409(surveyed, root)
        receipt = basket.empty_into(held)

        # The bytes moved, so the picture has to move with them. Leaving the plan
        # as it was is how a delete that worked perfectly reads as one that did
        # nothing: the row is still listed, the map still draws it, the total
        # still counts it. Rebuilt from the tree we already have and the answers
        # the model already gave, so nothing is asked twice.
        _forget(tree, [entry.original for entry in receipt.moved])
        settled = judged.get(str(Path(root).expanduser()), [])
        plan = build_plan(tree, settled)
        _apply(tree, settled)

        return {
            "freed_bytes": receipt.freed_bytes,
            "moved": [str(entry.original) for entry in receipt.moved],
            "irreplaceable": [
                str(e.original) for e in receipt.moved if e.verdict is Verdict.IRREPLACEABLE
            ],
            "refused": receipt.refused,
            "plan": plan.model_dump(mode="json"),
            "chart": _chart(tree, tree.size_bytes),
        }

    @app.post("/api/undo")
    def undo() -> dict[str, Any]:
        receipt = held.undo()
        return {"restored": [str(entry.original) for entry in receipt.moved]}

    @app.get("/api/duplicates")
    def duplicates(root: str) -> dict[str, Any]:
        tree = _surveyed_or_409(surveyed, root)
        report = find_duplicates(tree)
        return {
            "reclaimable_bytes": report.reclaimable_bytes,
            "files_read": report.files_read,
            "sets": [
                {
                    "keep": str(found.keep),
                    "copies": [str(copy) for copy in found.copies],
                    "size_bytes": found.size_bytes,
                    "reclaimable_bytes": found.reclaimable_bytes,
                }
                for found in report.duplicates
            ],
        }

    @app.post("/api/dropped")
    def dropped(folder: Dropped) -> dict[str, Any]:
        """Plan a folder the browser walked itself, without touching this disk."""
        tree = _tree_from(folder)
        _name_what_we_can(tree)
        plan = build_plan(tree)
        return {
            "plan": plan.model_dump(mode="json"),
            "chart": _chart(tree, tree.size_bytes),
        }

    return app


def _basket_state(basket: Basket) -> dict[str, Any]:
    return {
        "items": [
            {
                "path": str(item.path),
                "size_bytes": item.size_bytes,
                "verdict": item.verdict.value if item.verdict else None,
            }
            for item in basket.items
        ],
        "total_bytes": basket.total_bytes,
    }


def _surveyed_or_409(surveyed: dict[str, ScanNode], root: str) -> ScanNode:
    tree = surveyed.get(str(Path(root).expanduser()))
    if tree is None:
        raise HTTPException(409, "Survey that folder first.")
    return tree


def _name_what_we_can(tree: ScanNode) -> None:
    """Apply the catalog to a tree with no filesystem behind it.

    The rules work on names, so they work here — but `requires_sibling` normally
    asks the disk, and a dropped folder is not on this disk. The neighbours come
    from the tree instead.
    """
    catalog = load_catalog(Path("/"))
    stack = [tree]
    while stack:
        node = stack.pop()
        siblings = {child.name for child in node.children}
        for child in node.children:
            rule = catalog.recognise(
                child.path, is_dir=child.is_dir, siblings=siblings - {child.name}
            )
            if rule is not None:
                child.rule_id, child.label = rule.id, rule.label
                child.verdict, child.restore = rule.verdict, rule.restore
                child.restore_time = rule.restore_time
            stack.append(child)


def _tree_from(folder: Dropped) -> ScanNode:
    """Rebuild a tree from what the browser reported, with no filesystem access."""
    root = ScanNode(
        path=Path(folder.name), name=folder.name, is_dir=True, size_bytes=0, allocated_bytes=0
    )
    directories: dict[Path, ScanNode] = {root.path: root}

    def directory(path: Path) -> ScanNode:
        if path not in directories:
            parent = directory(path.parent)
            node = ScanNode(path=path, name=path.name, is_dir=True, size_bytes=0, allocated_bytes=0)
            parent.children.append(node)
            directories[path] = node
        return directories[path]

    for entry in folder.files:
        path = Path(folder.name) / entry.path
        node = ScanNode(
            path=path,
            name=path.name,
            is_dir=False,
            size_bytes=entry.size_bytes,
            allocated_bytes=entry.size_bytes,
        )
        directory(path.parent).children.append(node)
        for ancestor in [path.parent, *path.parent.parents]:
            if ancestor in directories:
                directories[ancestor].size_bytes += entry.size_bytes
                directories[ancestor].allocated_bytes += entry.size_bytes

    return root


def _sizes(tree: ScanNode) -> dict[Path, int]:
    found: dict[Path, int] = {}
    stack = [tree]
    while stack:
        node = stack.pop()
        found[node.path] = node.size_bytes
        stack.extend(node.children)
    return found


def _stream(
    root: Path,
    home: Path | None,
    judge: bool = False,
    surveyed: dict[str, ScanNode] | None = None,
    judged: dict[str, list[Classification]] | None = None,
) -> Iterator[dict[str, str]]:
    # A whole-volume survey needs the exclusions; a project folder needs none, and
    # applying them anyway costs nothing.
    exclude = boot_volume_exclusions() if root == Path("/") else ()

    try:
        yield from _walk_and_judge(root, home, judge, surveyed, judged, exclude)
    except Exception as failure:
        # Said out loud, in the stream, rather than letting the connection drop.
        # A dead stream leaves the browser to guess why, and the guess it had was
        # "macOS is blocking this folder" — which sent people to System Settings
        # over a model that had timed out.
        yield {"event": "failed", "data": json.dumps({"reason": _why(root, failure)})}


def _short(failure: Exception) -> str:
    detail = str(failure).strip().splitlines()
    return (detail[0] if detail else failure.__class__.__name__)[:120]


def _why(root: Path, failure: Exception) -> str:
    """What to tell someone, in their words, about why the survey stopped."""
    if isinstance(failure, PermissionError):
        return (
            f"macOS would not let Sift read {root}. Grant Full Disk Access to the "
            "terminal you started it from, in System Settings > Privacy & Security."
        )
    if isinstance(failure, FileNotFoundError):
        return f"There is no folder at {root}."
    detail = str(failure).strip() or failure.__class__.__name__
    if "connection" in detail.lower() or "timeout" in detail.lower():
        return (
            f"The survey finished, but the model could not be reached to judge it: "
            f"{detail[:160]}. Check the network and your key in .env, then try again."
        )
    return f"The survey stopped: {detail[:200]}"


def _walk_and_judge(
    root: Path,
    home: Path | None,
    judge: bool,
    surveyed: dict[str, ScanNode] | None,
    judged: dict[str, list[Classification]] | None,
    exclude: tuple[Path, ...] | Sequence[Path],
) -> Iterator[dict[str, str]]:
    tree: ScanNode | None = None
    for node in survey(root, exclude=exclude, home=home):
        tree = node
        if node.is_dir:
            yield {"event": "directory", "data": json.dumps(_report(node))}

    assert tree is not None  # survey always reports the root last
    if surveyed is not None:
        surveyed[str(root)] = tree

    judgements: list[Classification] = []
    note = ""
    if judge:
        candidates = candidates_for_model(tree)
        if candidates:
            yield {
                "event": "judging",
                "data": json.dumps({"count": len(candidates)}),
            }
            try:
                judgements = classify(candidates)
            except Exception as failure:
                # The disk has already been read. Throwing that away because a key
                # expired or the wifi dropped loses everything the rules knew —
                # which is most of a disk — for a reason that has nothing to do
                # with the disk. The model is the part that is optional here.
                note = (
                    f"{len(candidates)} folders went unjudged: the model could not "
                    f"be reached ({_short(failure)}). Everything the rules recognise "
                    "is below; check your key in .env and survey again for the rest."
                )

    # Built before the verdicts are written back, and the order is load-bearing.
    # _apply makes a model verdict indistinguishable from a catalog one, so a tree
    # coloured first would have every judged item counted twice: once by
    # _from_catalog walking settled nodes, once by _from_model.
    plan = build_plan(tree, judgements)

    # Now colour the tree, so the map shows what the model decided. Without this
    # a folder the catalog knows nothing about — a Downloads folder — draws
    # entirely grey.
    _apply(tree, judgements)
    if judged is not None:
        judged[str(root)] = judgements
    yield {
        "event": "done",
        "data": json.dumps(
            {
                "plan": plan.model_dump(mode="json"),
                "chart": _chart(tree, tree.size_bytes),
                "note": note,
            }
        ),
    }


def _forget(tree: ScanNode, moved: list[Path]) -> None:
    """Take what is no longer on disk out of the tree, sizes and all.

    A path can survive its own reclaim: a proposal that excluded a child leaves
    the directory behind holding it. So reality decides — gone means dropped,
    still there means re-measured — and every ancestor is corrected afterwards.
    """
    if not moved:
        return

    # What each directory holds in loose files of its own, taken before anything
    # is removed. Derived afterwards instead, a pruned child's bytes reappear as
    # its parent's loose weight and the total never moves.
    loose: dict[Path, int] = {}
    stack = [tree]
    while stack:
        node = stack.pop()
        loose[node.path] = node.size_bytes - sum(child.size_bytes for child in node.children)
        stack.extend(node.children)

    touched = set(moved)
    stack = [tree]
    while stack:
        node = stack.pop()
        node.children = [
            child
            for child in node.children
            if not (child.path in touched and not child.path.exists())
        ]
        stack.extend(node.children)

    for path in touched:
        if path.exists():
            _remeasure(tree, path, loose)
    _resize(tree, loose)


def _remeasure(tree: ScanNode, path: Path, loose: dict[Path, int]) -> None:
    """Re-read one directory that survived because something was kept inside it."""
    stack = [tree]
    while stack:
        node = stack.pop()
        if node.path == path:
            node.children = []
            node.size_bytes = sum(f.stat().st_size for f in path.rglob("*") if f.is_file())
            loose[path] = node.size_bytes
            return
        stack.extend(node.children)


def _resize(node: ScanNode, loose: dict[Path, int]) -> int:
    """Sum the tree bottom-up, keeping each directory's own loose files."""
    node.size_bytes = max(loose.get(node.path, node.size_bytes), 0) + sum(
        _resize(child, loose) for child in node.children
    )
    return node.size_bytes


def _apply(tree: ScanNode, judgements: list[Classification]) -> None:
    by_path = {judgement.path: judgement for judgement in judgements}
    stack = [tree]
    while stack:
        node = stack.pop()
        judgement = by_path.get(node.path)
        if judgement is not None and node.verdict is None:
            node.verdict = judgement.verdict
            node.label = judgement.label or node.name
            node.restore = judgement.restore
        stack.extend(node.children)


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
        "last_used": node.last_used,
        "unreadable": node.unreadable,
        "children": children,
    }


__all__ = ["Plan", "create_app"]
