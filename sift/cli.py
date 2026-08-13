"""One command: start the server, open the browser, begin surveying.

    uvx --from git+https://github.com/JacopKane/sift sift

No configuration screen and no empty state. The point of a disk tool is to be
looking at your disk within seconds of launching it.
"""

from __future__ import annotations

import argparse
import os
import threading
import webbrowser

import uvicorn


def main() -> None:
    options = _arguments()

    url = f"http://127.0.0.1:{options.port}/"
    if not options.no_browser:
        # After a delay, because opening the browser before uvicorn is listening
        # shows a connection error the person then has to reload past.
        threading.Timer(1.0, webbrowser.open, args=(f"{url}?root={options.root}",)).start()

    print(f"Sift is at {url}")
    uvicorn.run(
        "sift.api:create_app",
        factory=True,
        host="127.0.0.1",
        port=options.port,
        log_level="warning",
    )


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="sift", description="Disk cleanup that asks instead of guessing."
    )
    parser.add_argument(
        "root",
        nargs="?",
        default=os.path.expanduser("~/Downloads"),
        help="folder to survey on launch (default: ~/Downloads)",
    )
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument(
        "--no-browser", action="store_true", help="start the server without opening a window"
    )
    return parser.parse_args()
