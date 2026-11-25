"""
Pins the isolation the suite keeps from the machine running it, covering:

- The shell variables each test starts without
- The home directory each test reads
- The terminal type and width every console a test builds reads
- The block that stops a test without the `network` mark from opening a
  network connection, and the Unix socket that block leaves open
- The mark that lets a `network` test open a connection
- The group each test reading a played run joins under `--dist=loadgroup`
- The filter that raises every warning as an error
"""

from common.processes import starts_processes
from os               import environ
from pathlib          import Path
from pytest           import FixtureRequest, Function, MonkeyPatch, mark, param, raises, warns
from pytest_socket    import SocketBlockedError
from socket           import AF_UNIX, create_connection, socketpair
from warnings         import warn


def regrouped(monkeypatch: MonkeyPatch, request: FixtureRequest) -> Function:
    """
    Collects the test `request` runs afresh and passes it through the
    collection hook in `tests/conftest.py` under `--dist=loadgroup`.

    Returns:
        The fresh test, as the hook leaves it.
    """
    conftest = request.config.pluginmanager.get_plugin(
        str(request.config.rootpath / "tests/conftest.py")
    )
    fresh = Function.from_parent(request.node.parent, name=request.node.originalname)

    monkeypatch.setattr(request.config.option, "loadgroup", True, raising=False)
    conftest.pytest_collection_modifyitems(request.config, [fresh])

    return fresh


def test_a_network_test_gets_the_mark_that_opens_the_socket(request: FixtureRequest):
    """
    Asserts that the collection hook in `tests/conftest.py` gives a test
    carrying the `network` mark pytest-socket's `enable_socket` mark, which
    lets that test open a connection.
    """
    conftest = request.config.pluginmanager.get_plugin(
        str(request.config.rootpath / "tests/conftest.py")
    )

    request.node.add_marker(mark.network)
    conftest.pytest_collection_modifyitems(request.config, [request.node])

    assert request.node.get_closest_marker("enable_socket")


@mark.usefixtures("played")
def test_a_test_reading_a_played_run_joins_the_played_group(
    monkeypatch : MonkeyPatch,
    request     : FixtureRequest
):
    """
    Asserts that under `--dist=loadgroup` the collection hook gives a test
    requesting `played` the `played` group and appends it to its node id, so
    every such test runs on one worker, which plays each run once.
    """
    fresh = regrouped(monkeypatch, request)

    assert (fresh.get_closest_marker("xdist_group").args, fresh.nodeid) == (
        ("played",),
        f"{request.node.nodeid.removesuffix('@played')}@played"
    )


@starts_processes
@mark.usefixtures("played")
def test_a_grouped_test_reading_a_played_run_keeps_its_own_group(
    monkeypatch : MonkeyPatch,
    request     : FixtureRequest
):
    """
    Asserts that the collection hook leaves a test requesting `played` in
    the group its own `xdist_group` mark names, appending that one alone.
    """
    fresh = regrouped(monkeypatch, request)

    assert (
        [marked.args for marked in fresh.iter_markers("xdist_group")],
        fresh.nodeid
    ) == (
        [("processes",)],
        f"{request.node.nodeid.removesuffix('@processes')}@processes"
    )


def test_a_socket_stays_closed_outside_the_network_mark():
    """
    Asserts that a test without the `network` mark cannot open a connection,
    pytest-socket issuing a warning and then raising `SocketBlockedError` on
    the attempt.

    `create_connection` looks `getaddrinfo` up on the socket module each
    time it runs rather than binding it once at import, and that name is the
    one pytest-socket replaces when a test starts.
    """
    with warns(UserWarning), raises(SocketBlockedError):
        create_connection(("blocked.invalid", 80))


def test_a_unix_socket_stays_open():
    """
    Asserts that a test without the `network` mark can still open a Unix
    socket, which `--allow-unix-socket` in `[tool.pytest]` leaves open.

    `socketpair` looks `socket` up on the socket module each time it runs,
    so the pair it opens passes through the class pytest-socket swaps in
    when a test starts.
    """
    first, second = socketpair()

    with first, second:
        assert first.family == AF_UNIX


def test_a_warning_raises_inside_a_test():
    """
    Asserts that a warning a test triggers raises as an exception rather
    than printing in the summary, which `filterwarnings = ["error"]` in
    `[tool.pytest]` sets for the whole suite.
    """
    with raises(UserWarning):
        warn("a warning the suite reads as an error", UserWarning)


def test_home_is_an_empty_directory():
    """
    Asserts that `~` resolves to an empty directory, so no test reads a
    dotfile from the developer's home.
    """
    assert list(Path.home().iterdir()) == []


def test_the_shell_carries_no_variable_that_changes_a_result(cleared: str):
    """
    Asserts that no variable `CLEARED` names reaches a test, whatever
    the shell running the suite sets, which the `environment` fixture's
    docstring sets out group by group.
    """
    assert cleared not in environ


@mark.parametrize(
    ("variable", "value"),
    [param("COLUMNS", "80", id="eighty-columns"), param("TERM", "dumb", id="dumb")]
)
def test_the_terminal_reports_a_fixed_type_and_width(value: str, variable: str):
    """
    Asserts that `TERM` reads as `dumb`, which stops a console writing to a
    real terminal from choosing a color system, and that `COLUMNS` reads as
    `80`, which every console a test builds takes as its width before the
    size of any terminal the suite runs in.
    """
    assert environ[variable] == value
