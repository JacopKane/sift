"""One command: start the server and open the window.

    uvx --from git+https://github.com/JacopKane/sift sift

Name a folder and it is being surveyed before you have finished reading the
window. Name nothing and it asks which one — the only question it opens with.
"""

from __future__ import annotations

import argparse
import socket
import threading
import webbrowser
from pathlib import Path
from urllib.parse import quote

import uvicorn

DEFAULT_PORT = 8765
SEARCH = 20
"""How many ports past the default to try before giving up."""


def main() -> None:
    options = parse_arguments()

    # Settled before anything is printed or opened. Announcing an address we
    # then fail to bind is how a window ends up pointed at whatever else happens
    # to answer there — a stale copy of this same app, most likely, since it is
    # the thing most likely to still be holding our port.
    options.port = free_port(options.port or DEFAULT_PORT, insisted=options.port is not None)

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


def free_port(preferred: int, *, insisted: bool) -> int:
    """A port nothing else is already answering on.

    Asked for by name, the answer is that port or nothing: swapping it silently
    would send someone who typed ``--port 3000`` to a window on 3001. Left to us,
    the next free one is better than refusing to start over a number nobody chose.
    """
    if insisted:
        if _in_use(preferred):
            raise SystemExit(
                f"Port {preferred} is already in use. Something else is answering "
                f"there — quite possibly an older copy of Sift. Stop it with "
                f"`lsof -ti :{preferred} | xargs kill`, or pick another port."
            )
        return preferred

    for candidate in range(preferred, preferred + SEARCH):
        if not _in_use(candidate):
            return candidate

    raise SystemExit(
        f"Ports {preferred} to {preferred + SEARCH - 1} are all in use. "
        "Pass --port with one that is free."
    )


def _in_use(port: int) -> bool:
    """Whether anything is already bound here.

    Binding is the question, not connecting: a wedged server holds its port
    without answering, and that is exactly the case worth catching.
    """
    probe = socket.socket()
    probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        probe.bind(("127.0.0.1", port))
    except OSError:
        return True
    else:
        return False
    finally:
        probe.close()


def launch_url(options: argparse.Namespace) -> str:
    """Where to point the window.

    The root travels in the query string only when one was asked for. Defaulting
    it here would mean every plain `sift` walked somebody's Downloads folder
    uninvited, and the drop screen would never be seen.
    """
    url = f"http://127.0.0.1:{options.port or DEFAULT_PORT}/"
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
    # No default, so "they asked for this one" and "we chose it" stay tellable
    # apart — the two cases want opposite behaviour when the port is busy.
    parser.add_argument(
        "--port", type=int, default=None, help=f"port to serve on (default: {DEFAULT_PORT})"
    )
    parser.add_argument(
        "--no-browser", action="store_true", help="start the server without opening a window"
    )
    return parser.parse_args(argv)
