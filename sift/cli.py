"""One command: start the server and open the window.

    uvx --from git+https://github.com/JacopKane/sift sift

Name a folder and it is being surveyed before you have finished reading the
window. Name nothing and it asks which one — the only question it opens with.
"""

from __future__ import annotations

import argparse
import threading
import webbrowser
from pathlib import Path
from urllib.parse import quote

import uvicorn


def main() -> None:
    options = parse_arguments()

    if not options.no_browser:
        # After a delay, because opening the browser before uvicorn is listening
        # shows a connection error the person then has to reload past.
        threading.Timer(1.0, webbrowser.open, args=(launch_url(options),)).start()

    print(f"Sift is at http://127.0.0.1:{options.port}/")
    uvicorn.run(
        "sift.api:create_app",
        factory=True,
        host="127.0.0.1",
        port=options.port,
        log_level="warning",
    )


def launch_url(options: argparse.Namespace) -> str:
    """Where to point the window.

    The root travels in the query string only when one was asked for. Defaulting
    it here would mean every plain `sift` walked somebody's Downloads folder
    uninvited, and the drop screen would never be seen.
    """
    url = f"http://127.0.0.1:{options.port}/"
    if options.root is None:
        return url
    return f"{url}?root={quote(str(Path(options.root).expanduser()))}"


def parse_arguments(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="sift", description="Disk cleanup that asks instead of guessing."
    )
    parser.add_argument(
        "root",
        nargs="?",
        default=None,
        help="folder to survey on launch (default: ask)",
    )
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument(
        "--no-browser", action="store_true", help="start the server without opening a window"
    )
    return parser.parse_args(argv)
