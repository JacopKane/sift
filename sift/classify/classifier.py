"""Asking a model about the directories the catalog could not name.

One batched call for every candidate. The model never sees the file tree and never
sees file contents — only what each opaque directory is called, how big it is, and
what fills it.
"""

from __future__ import annotations

from collections.abc import Sequence
from functools import lru_cache
from pathlib import Path
from typing import Any, cast

from langchain.chat_models import init_chat_model
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.rate_limiters import InMemoryRateLimiter
from langchain_core.runnables import RunnableConfig
from pydantic import BaseModel

from sift.config import settings
from sift.models import Candidate, Classification, Verdict

SYSTEM = """You help someone reclaim disk space without losing anything they cannot get back.

For each directory, decide what recovering it would cost them:

  regenerable    a command or tool rebuilds it exactly; deleting it costs only time
  review         mixed contents, or you cannot tell from what you were given
  irreplaceable  holds work or records that no command reproduces

Rules:

- A directory holding BOTH regenerable and irreplaceable things is `review`. Not
  `regenerable`, which proposes deleting somebody's only copy. Not `irreplaceable`
  either, which hides space they could safely have reclaimed. `review` means: there
  is something here worth keeping and something worth reclaiming, so a human should
  look. Say which is which in the reason.
- If your reasoning contains an "if" you cannot check, the answer is `review`.
  "An archive can be recreated if the source project still exists" is a guess
  about something you were not shown, and betting on it deletes the only copy.
  You may only say `regenerable` when the thing that rebuilds it is visible in
  what you were given, or is a tool everyone has.
- `restore` is always filled in. For `regenerable`, give the actual command. For
  `irreplaceable`, say plainly that it cannot be restored.
- Judge from the contents you are shown — the extensions, the largest file names,
  the counts — not from the directory's name.
- Return exactly one entry per directory, echoing its path back exactly as given."""

_EXTENSIONS_SHOWN = 6


class _Judgement(BaseModel):
    """What comes back over the wire.

    Mirrors :class:`~sift.models.Classification` but with a plain string path, since
    models emit strings and coercion belongs on our side of the seam.
    """

    path: str
    verdict: Verdict
    reason: str
    restore: str


class _Batch(BaseModel):
    judgements: list[_Judgement]


def classify(
    candidates: Sequence[Candidate],
    config: RunnableConfig | None = None,
) -> list[Classification]:
    """Judge every candidate in a single call."""
    if not candidates:
        return []

    model = chat_model().with_structured_output(_Batch)
    reply = cast(
        _Batch,
        model.invoke(
            [SystemMessage(SYSTEM), HumanMessage(_render(candidates))],
            config=config,
        ),
    )

    # Sizes and labels come back from the candidate, never from the tree. A
    # remainder candidate is smaller than the directory it names, and looking it up
    # again would silently re-count the files broken out of it.
    offered = {str(candidate.path): candidate for candidate in candidates}

    # Deliberately not filtered against the offered set: if the model answers about
    # something nobody asked, that is a fact worth failing a test over rather than
    # quietly discarding.
    return [
        Classification(
            path=Path(judgement.path),
            verdict=judgement.verdict,
            reason=judgement.reason,
            restore=judgement.restore,
            label=_of(offered, judgement.path, "label", Path(judgement.path).name),
            size_bytes=_of(offered, judgement.path, "size_bytes", 0),
            excluding=_of(offered, judgement.path, "excluding", []),
        )
        for judgement in reply.judgements
    ]


def _of(offered: dict[str, Candidate], path: str, field: str, fallback: Any) -> Any:
    candidate = offered.get(path)
    return getattr(candidate, field) if candidate else fallback


@lru_cache(maxsize=1)
def _limiter() -> InMemoryRateLimiter:
    """One bucket for the whole process, shared by every call.

    Retrying alone does not help: the retries spend the same minute's budget as
    the requests that exhausted it. Pacing is what actually prevents the failure.
    """
    per_minute = settings().sift_requests_per_minute
    return InMemoryRateLimiter(
        requests_per_second=per_minute / 60,
        check_every_n_seconds=0.25,
        max_bucket_size=max(1, per_minute // 4),
    )


def chat_model() -> BaseChatModel:
    conf = settings()
    # Two, not six. Retries multiply against the agent's step limit: at six, one
    # question could issue seven attempts per step across a dozen steps before
    # giving up. Pacing is what prevents rate limits; retrying is only the
    # fallback when pacing was not enough.
    kwargs: dict[str, Any] = {"max_retries": 2, "rate_limiter": _limiter()}

    # Passed explicitly rather than exported to os.environ: the key comes from .env
    # via Settings, and a library reading it back out of the process environment
    # would be a second, invisible source of truth.
    if conf.api_key:
        kwargs["api_key"] = conf.api_key

    if conf.provider == "google_genai":
        # Thinking tokens bill as output. Measured on this task: gemini-3.6-flash
        # spent 1217 of them to reach the same verdicts this model reaches with none.
        kwargs["thinking_budget"] = 0
    return cast(BaseChatModel, init_chat_model(conf.model, model_provider=conf.provider, **kwargs))


def _render(candidates: Sequence[Candidate]) -> str:
    return "\n\n".join(_render_one(candidate) for candidate in candidates)


def _render_one(candidate: Candidate) -> str:
    fills = ", ".join(
        f"{extension} {_size(total)}"
        for extension, total in list(candidate.extensions.items())[:_EXTENSIONS_SHOWN]
    )
    largest = ", ".join(
        f"{file.name} ({_size(file.size_bytes)})" for file in candidate.largest_files
    )
    return (
        f"{candidate.path}\n"
        f"  size: {_size(candidate.size_bytes)} across {candidate.file_count} files\n"
        f"  fills: {fills or '(nothing)'}\n"
        f"  largest: {largest or '(no files)'}"
    )


def _size(count: int) -> str:
    size = float(count)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024:
            return f"{size:.0f} {unit}" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"
