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
- Some files cannot be replaced if they are deleted, and find_files marks them.
  Select them when that is what was asked for — nothing is deleted, only moved
  aside, and the person confirms before anything moves. Never refuse. Do say in
  your reason which of your selection cannot be replaced.
- Select only what was actually asked for. If someone asks for disk images, do not
  throw in their documents because they happen to be large."""


class _Answer(BaseModel):
    paths: list[str] = Field(description="Exact paths returned by a tool. Never invented.")
    reason: str = Field(description="What you selected and why, in one or two sentences.")


MAX_STEPS = 12
"""How far the agent may go before it must answer.

A ReAct loop spends roughly two steps per tool round, so this allows about five
rounds — enough to look, narrow down, and decide. Without a cap the agent keeps
searching when the honest answer is "nothing matches", and one question can cost
a hundred requests."""


class Selection(BaseModel):
    paths: list[Path]
    reason: str
    irreplaceable: list[Path] = Field(default_factory=list)
    """Of what was selected, which cannot be replaced.

    Worked out here rather than taken from the model's word for it. Asking for
    something unrecoverable is allowed; not being told that is what you asked for
    is not."""


def ask(
    tree: ScanNode,
    prompt: str,
    config: RunnableConfig | None = None,
) -> Selection:
    """Answer *prompt* against a completed survey.

    Nothing is withheld. A tool that refuses is a tool people work around, and the
    verdicts already say what each thing would cost — the answer lands in a basket
    that has to be emptied deliberately, which is where the decision belongs.
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
        e.g. path_contains='Documents'. Each file says whether it can be replaced.
        """
        return index.find(extensions, min_bytes, max_bytes, name_contains, path_contains)

    agent = create_agent(
        chat_model(),
        [what_is_here, find_files],
        system_prompt=SYSTEM,
        response_format=_Answer,
    )
    budget = cast(RunnableConfig, {"recursion_limit": MAX_STEPS, **(config or {})})
    raw = agent.invoke({"messages": [HumanMessage(content=prompt)]}, config=budget)
    result = cast(dict[str, Any], raw)
    answer = cast(_Answer, result["structured_response"])

    # Labelled here, not in the prompt. A model asked forcefully enough will say
    # whatever it is told to say about what it picked; this cannot.
    chosen = [Path(path) for path in answer.paths]
    return Selection(
        paths=chosen,
        reason=answer.reason,
        irreplaceable=[path for path in chosen if index.is_irreplaceable(path)],
    )
