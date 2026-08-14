"""Steps for tests/features/cli.feature.

The real argument parser and the real URL builder, over a real path.
"""

from __future__ import annotations

from urllib.parse import parse_qs, urlparse

from pytest_bdd import scenarios, then, when

from sift.cli import launch_url, parse_arguments

scenarios("cli.feature")


@when("sift is launched with a folder", target_fixture="opened")
def launched_with_folder(tmp_path: str) -> str:
    options = parse_arguments([str(tmp_path), "--port", "9999"])
    return launch_url(options)


@when("sift is launched with nothing", target_fixture="opened")
def launched_with_nothing() -> str:
    return launch_url(parse_arguments(["--port", "9999"]))


@then("the window it opens is pointed at that folder")
def window_points_at_folder(opened: str, tmp_path: str) -> None:
    asked = parse_qs(urlparse(opened).query).get("root")
    assert asked == [str(tmp_path)], f"{opened} does not carry the folder that was asked for"


@then("the window it opens names no folder")
def window_names_no_folder(opened: str) -> None:
    assert "root" not in parse_qs(urlparse(opened).query), (
        f"{opened} picks a folder nobody asked for — the drop screen never shows"
    )
