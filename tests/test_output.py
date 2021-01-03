"""This module hosts unit tests for the Output classes."""

from freezegun import freeze_time
import pytest

from build_magic.output import Basic, Output, OutputMethod


def test_basic_log_method(capsys):
    """Verify the basic log() method works as expected."""
    output = Output()
    with pytest.raises(NotImplementedError):
        output.log(OutputMethod.JOB_START)

    output = Basic()
    output.log(OutputMethod.JOB_START)
    captured = capsys.readouterr()
    assert 'build-magic' in captured.out
    assert 'started at' in captured.out

    log_output = captured.out
    output.start_job()
    captured = capsys.readouterr()
    assert log_output == captured.out


@freeze_time('2021-01-02 01:06:34')
def test_basic_end_job(capsys):
    """Verify the basic end_job() method works as expected."""
    output = Output()
    with pytest.raises(NotImplementedError):
        output.log(OutputMethod.JOB_END)

    output = Basic()
    output.log(OutputMethod.JOB_END)
    captured = capsys.readouterr()
    assert captured.out == 'build-magic finished at 2021-01-02T01:06:34\n'


def test_basic_start_stage(capsys):
    """Verify the basic start_stage() method works as expected."""
    output = Output()
    with pytest.raises(NotImplementedError):
        output.log(OutputMethod.STAGE_START)

    output = Basic()
    # Default stage number.
    output.log(OutputMethod.STAGE_START)
    captured = capsys.readouterr()
    assert captured.out == 'Starting Stage 1\n'

    # Assigned stage number.
    output.log(OutputMethod.STAGE_START, 7)
    captured = capsys.readouterr()
    assert captured.out == 'Starting Stage 7\n'


def test_basic_end_stage(capsys):
    """Verify the end_stage() method works as expected."""
    output = Output()
    with pytest.raises(NotImplementedError):
        output.log(OutputMethod.STAGE_END)

    output = Basic()
    # Default stage number and status.
    output.log(OutputMethod.STAGE_END)
    captured = capsys.readouterr()
    assert captured.out == 'Stage 1 complete with result DONE\n'

    # Stage number but default status.
    output.log(OutputMethod.STAGE_END, 7)
    captured = capsys.readouterr()
    assert captured.out == 'Stage 7 complete with result DONE\n'

    # Assigned stague number and status.
    output.log(OutputMethod.STAGE_END, 7, 1)
    captured = capsys.readouterr()
    assert captured.out == 'Stage 7 complete with result FAIL\n'


def test_basic_no_job(capsys):
    """Verify the basic no_job() method works as expected."""
    output = Output()
    with pytest.raises(NotImplementedError):
        output.log(OutputMethod.NO_JOB)

    output = Basic()
    output.log(OutputMethod.NO_JOB)
    captured = capsys.readouterr()
    assert captured.out == 'No commands to run. Use --help for usage. Exiting...\n'


def test_basic_macro_start(capsys):
    """Verify the basic macro_start() method doesn't print anything."""
    output = Output()
    with pytest.raises(NotImplementedError):
        output.log(OutputMethod.MACRO_START)

    output = Basic()
    output.log(OutputMethod.MACRO_START)
    captured = capsys.readouterr()
    assert not captured.out
    assert not captured.err


@freeze_time('2021-01-02 01:06:34')
def test_basic_macro_status(capsys):
    """Verify the basic macro_status() method works as expected."""
    output = Output()
    with pytest.raises(NotImplementedError):
        output.log(OutputMethod.MACRO_STATUS)

    output = Basic()
    # Only the directive.
    output.log(OutputMethod.MACRO_STATUS, 'BUILD')
    captured = capsys.readouterr()
    assert captured.out == '2021-01-02T01:06:34 [ DONE  ] BUILD   \n'

    # Default status code.
    output.log(OutputMethod.MACRO_STATUS, 'BUILD', 'tar -czf hello.tar.gz')
    captured = capsys.readouterr()
    assert captured.out == '2021-01-02T01:06:34 [ DONE  ] BUILD    : tar -czf hello.tar.gz\n'

    # No command but failing status code.
    output.log(OutputMethod.MACRO_STATUS, 'BUILD', status_code=1)
    captured = capsys.readouterr()
    assert captured.out == '2021-01-02T01:06:34 [ FAIL  ] BUILD   \n'

    # Command with failing status code.
    output.log(OutputMethod.MACRO_STATUS, 'BUILD', 'tar -czf hello.tar.gz', 1)
    captured = capsys.readouterr()
    assert captured.out == '2021-01-02T01:06:34 [ FAIL  ] BUILD    : tar -czf hello.tar.gz\n'


@freeze_time('2021-01-02 01:06:34')
def test_basic_error(capsys):
    """Verify the basic error() method works as expected."""
    output = Output()
    with pytest.raises(NotImplementedError):
        output.log(OutputMethod.MACRO_STATUS)

    output = Basic()
    output.log(OutputMethod.ERROR, 'An error occurred.')
    captured = capsys.readouterr()
    assert captured.out == '2021-01-02T01:06:34 [ ERROR ] An error occurred.\n'


@freeze_time('2021-01-02 01:06:34')
def test_basic_info(capsys):
    """Verify the basic info() method works as expected."""
    output = Output()
    with pytest.raises(NotImplementedError):
        output.log(OutputMethod.INFO)

    output = Basic()
    output.log(OutputMethod.INFO, 'This is a test.\n\n\n')
    captured = capsys.readouterr()
    assert captured.out == '2021-01-02T01:06:34 [ INFO  ] OUTPUT   : This is a test.\n\n\n\n'


# TODO: Add tests for Tty and Silent.
