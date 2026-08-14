"""Steps for tests/features/cli.feature.

The real argument parser and the real URL builder, over a real path.
"""

from __future__ import annotations

import socket
from collections.abc import Iterator
from urllib.parse import parse_qs, urlparse

import pytest
from pytest_bdd import given, scenarios, then, when

from sift.cli import free_port, launch_url, parse_arguments

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


@pytest.fixture
def taken() -> Iterator[int]:
    """A real socket on a real port, held open for the length of the scenario."""
    holder = socket.socket()
    holder.bind(("127.0.0.1", 0))
    holder.listen(1)
    try:
        yield int(holder.getsockname()[1])
    finally:
        holder.close()


@given("something else is already holding the usual port")
def something_else_is_holding_it(taken: int) -> None:
    assert taken


@when("sift is launched asking for that exact port", target_fixture="outcome")
def launched_asking_for_that_port(taken: int) -> BaseException | int:
    options = parse_arguments(["--port", str(taken)])
    try:
        return free_port(options.port, insisted=True)
    except SystemExit as stopped:
        return stopped


@then("it picks a port that is free")
def picks_a_free_port(taken: int) -> None:
    chosen = free_port(taken, insisted=False)
    assert chosen != taken, (
        "it announced the port something else already answers on, so the window "
        "opens onto whatever that other thing happens to serve"
    )
    probe = socket.socket()
    try:
        probe.bind(("127.0.0.1", chosen))
    finally:
        probe.close()


@then("the window it opens points at that port")
def window_points_at_the_chosen_port(taken: int) -> None:
    chosen = free_port(taken, insisted=False)
    options = parse_arguments(["--port", str(chosen)])
    assert f":{chosen}/" in launch_url(options)


@then("it stops and says the port is taken")
def stops_and_says_so(outcome: BaseException | int) -> None:
    assert isinstance(outcome, SystemExit), (
        f"it carried on and returned port {outcome} — a port asked for by name is "
        "a request, and swapping it silently sends you to the wrong window"
    )
    assert "in use" in str(outcome).lower(), str(outcome)
