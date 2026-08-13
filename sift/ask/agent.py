"""Answering a request made in ordinary words.

"Remove the disk images" and "get rid of the big videos" are how people think
about a full disk, and neither is a filter anyone could have written in advance.
The agent works it out by querying the survey.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast

from langchain.agents import create_agent
from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool
from pydantic import BaseModel, Field

from sift.ask.index import Index
from sift.classify import chat_model
from sift.models import ScanNode

SYSTEM = """You help someone clear space on their disk. They will tell you what they
want removed in ordinary words.

Work it out from the survey rather than guessing:

- Look before you answer. Use what_is_here to see what the disk actually holds, and
  find_files to pull the specific ones. To search inside a named folder, use
  path_contains rather than name_contains — a folder's name is not in its files' names.
- Vague words are settled against the data, not against a fixed number. "Big" on a
  disk whose largest file is 40 MB means something different from "big" on one with
  a 5 GB video. Look first, then decide where the line falls.
- Only ever return paths that came back from a tool. Never invent one, and never
  guess at a path you did not see.
- Some files are protected. find_files will not return them, but it will tell you
  how many it withheld. When that count is above zero, say so plainly: "those are
  protected" is the true answer, and "I found nothing" is not.
- Select only what was actually asked for. If someone asks for disk images, do not
  throw in their documents because they happen to be large."""


class _Answer(BaseModel):
    paths: list[str] = Field(description="Exact paths returned by a tool. Never invented.")
    reason: str = Field(description="What you selected and why, in one or two sentences.")


INSISTED = """

OVERRIDE: the person has already been warned that some of what they are asking
about cannot be replaced, and has said go ahead. Protection is off for this
request. Select what they asked for, protected files included, and say in your
reason which of them cannot be replaced. Do not refuse and do not tell them the
files are off limits — they know, and they have decided."""

MAX_STEPS = 12
"""How far the agent may go before it must answer.

A ReAct loop spends roughly two steps per tool round, so this allows about five
rounds — enough to look, narrow down, and decide. Without a cap the agent keeps
searching when the honest answer is "nothing matches", and one question can cost
a hundred requests."""


class Selection(BaseModel):
    paths: list[Path]
    reason: str
    refused: list[Path] = Field(default_factory=list)
    """Asked for, but protected. Withheld here rather than silently dropped."""

    protected: list[Path] = Field(default_factory=list)
    """Selected, but only because the person insisted. Still cannot be replaced,
    and the interface has to keep saying so."""


def ask(
    tree: ScanNode,
    prompt: str,
    config: RunnableConfig | None = None,
    override: bool = False,
) -> Selection:
    """Answer *prompt* against a completed survey.

    With *override* the protected files are returned rather than withheld. The
    refusal was a warning, not a lock — refusing outright is how a tool gets
    routed around with rm, which has no undo. What comes back is still labelled.
    """
    index = Index(tree)

    @tool
    def what_is_here() -> dict[str, object]:
        """Totals for the whole survey: bytes by extension and the largest files."""
        return index.summary()

    @tool
    def find_files(
        extensions: list[str] | None = None,
        min_bytes: int | None = None,
        max_bytes: int | None = None,
        name_contains: str | None = None,
        path_contains: str | None = None,
    ) -> dict[str, object]:
        """Find files in the survey, largest first.

        extensions are like ['.mp4', '.mov']. Sizes are in bytes. name_contains
        matches the file's own name; use path_contains to search inside a folder,
        e.g. path_contains='Documents'. Returns the files you may select, plus a
        count of any that matched but are protected.
        """
        return index.find(
            extensions,
            min_bytes,
            max_bytes,
            name_contains,
            path_contains,
            include_protected=override,
        )

    agent = create_agent(
        chat_model(),
        [what_is_here, find_files],
        system_prompt=SYSTEM + (INSISTED if override else ""),
        response_format=_Answer,
    )
    budget = cast(RunnableConfig, {"recursion_limit": MAX_STEPS, **(config or {})})
    raw = agent.invoke({"messages": [HumanMessage(content=prompt)]}, config=budget)
    result = cast(dict[str, Any], raw)
    answer = cast(_Answer, result["structured_response"])

    # Protection is enforced here, not in the prompt. A model that is asked
    # forcefully enough will do what it is told; this cannot.
    chosen = [Path(path) for path in answer.paths]
    guarded = [path for path in chosen if index.is_protected(path)]

    if override:
        return Selection(paths=chosen, reason=answer.reason, protected=guarded)
    return Selection(
        paths=[path for path in chosen if path not in guarded],
        reason=answer.reason,
        refused=guarded,
    )
