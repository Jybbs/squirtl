"""
Pins what each command reports through, covering the console loguru writes
to, from `DEBUG` up under `--verbose` and from `INFO` up otherwise, and the
error a command refuses, logged as one line per reason it gives before the
command exits 1.
"""

from loguru import logger
from pytest import CaptureFixture, mark, param, raises

from squirtl.cli.logs     import listen, refusing
from squirtl.runs.schemas import Run


def messages(capsys: CaptureFixture[str]) -> list[str]:
    """
    Reads the message of each line logged to standard error, past the time
    the line opens on.
    """
    return [line.partition(" ")[2] for line in capsys.readouterr().err.splitlines()]


@mark.parametrize(
    ("verbose", "logged"),
    [
        param(False, ["Episode"], id="info-up"),
        param(True, ["Step", "Episode"], id="debug-up-under-verbose")
    ]
)
def test_the_console_logs_from_the_level_verbose_sets(
    capsys  : CaptureFixture[str],
    logged  : list[str],
    verbose : bool
):
    """
    Asserts that the console writes each line to standard error, a debug
    line only under `verbose`.
    """
    listen(verbose)
    logger.debug("Step")
    logger.info("Episode")

    assert messages(capsys) == logged


@mark.parametrize(
    ("record", "logged"),
    [
        param(
            "{}",
            [f"Run.{field}: Field required" for field in (
                "digest", "revision", "settings", "started"
            )],
            id = "an-empty-object"
        ),
        param(
            "{",
            ["Run: Invalid JSON: EOF while parsing an object at line 1 column 1"],
            id = "an-object-broken-off"
        )
    ]
)
def test_a_record_holding_no_run_logs_one_line_per_error_and_exits_1(
    capsys : CaptureFixture[str],
    logged : list[str],
    record : str
):
    """
    Asserts that a refused `ValidationError` exits 1, logging one line
    per error Pydantic reports, each the path to the record or its field
    beside Pydantic's message, whether the record lacks fields or breaks
    off mid-object.
    """
    listen()

    with raises(SystemExit) as refused, refusing(ValueError):
        Run.model_validate_json(record)

    assert refused.value.code == 1
    assert messages(capsys) == logged


def test_any_other_refused_error_logs_its_message_and_exits_1(
    capsys: CaptureFixture[str]
):
    """
    Asserts that a refused error other than a `ValidationError` exits 1,
    logging its message as one line.
    """
    listen()

    with raises(SystemExit) as refused, refusing(OSError):
        raise FileNotFoundError("data/runs/a holds no run")

    assert refused.value.code == 1
    assert messages(capsys) == ["data/runs/a holds no run"]
