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
  find_files to pull the specific ones.
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


class Selection(BaseModel):
    paths: list[Path]
    reason: str
    refused: list[Path] = Field(default_factory=list)
    """Asked for, but protected. Withheld here rather than silently dropped."""


def ask(tree: ScanNode, prompt: str, config: RunnableConfig | None = None) -> Selection:
    """Answer *prompt* against a completed survey."""
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
    ) -> dict[str, object]:
        """Find files in the survey, largest first.

        extensions are like ['.mp4', '.mov']. Sizes are in bytes. Returns the files
        you may select, plus a count of any that matched but are protected.
        """
        return index.find(extensions, min_bytes, max_bytes, name_contains)

    agent = create_agent(
        chat_model(),
        [what_is_here, find_files],
        system_prompt=SYSTEM,
        response_format=_Answer,
    )
    raw = agent.invoke({"messages": [HumanMessage(content=prompt)]}, config=config)
    result = cast(dict[str, Any], raw)
    answer = cast(_Answer, result["structured_response"])

    # Protection is enforced here, not in the prompt. A model that is asked
    # forcefully enough will do what it is told; this cannot.
    chosen = [Path(path) for path in answer.paths]
    refused = [path for path in chosen if index.is_protected(path)]

    return Selection(
        paths=[path for path in chosen if path not in refused],
        reason=answer.reason,
        refused=refused,
    )
