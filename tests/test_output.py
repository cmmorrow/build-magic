"""This module hosts unit tests for the Output classes."""

from freezegun import freeze_time
import pytest

from build_magic import __version__ as version
from build_magic.output import Basic, Output, OutputMethod, Silent, Tty


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


@freeze_time('2021-01-02 01:06:34')
def test_tty_start_job(capsys):
    """Verify the start_job() method works correctly."""
    output = Tty()
    output.log(OutputMethod.JOB_START)
    captured = capsys.readouterr()
    assert f'build-magic {version}' in captured.out
    assert f'Start time Sat Jan  2 01:06:34 2021' in captured.out


@freeze_time('2021-01-02 01:06:34')
def test_tty_end_job(capsys):
    """Verify the end_job() method works correctly."""
    output = Tty()
    output.log(OutputMethod.JOB_END)
    captured = capsys.readouterr()
    assert captured.out == 'build-magic finished at Sat Jan  2 01:06:34 2021\n'


def test_tty_start_stage(capsys):
    """Verify the start_stage() method works correctly."""
    output = Tty()
    output.log(OutputMethod.STAGE_START)
    captured = capsys.readouterr()
    assert captured.out == 'Starting Stage 1\n'


def test_tty_end_stage(capsys):
    """Verify the end_stage() method works correctly."""
    output = Tty()
    output.log(OutputMethod.STAGE_END)
    captured = capsys.readouterr()
    assert captured.out == 'Stage 1 finished with result COMPLETE\n\n'

    output.log(OutputMethod.STAGE_END, 1, 1)
    captured = capsys.readouterr()
    assert captured.out == 'Stage 1 finished with result FAILED\n\n'


def test_tty_no_job(capsys):
    """Verify the no_job() method works correctly."""
    output = Tty()
    output.log(OutputMethod.NO_JOB)
    captured = capsys.readouterr()
    assert captured.out == 'No commands to run. Use --help for usage. Exiting...\n'


def test_tty_macro_start(capsys):
    """Verify the macro_start() method works correctly."""
    output = Tty()
    output.log(OutputMethod.MACRO_START, 'execute', 'ls')
    captured = capsys.readouterr()
    assert captured.out == 'EXECUTE : ls ........................................................ RUNNING\n'

    output.log(OutputMethod.MACRO_START, 'execute')
    captured = capsys.readouterr()
    assert  captured.out == 'EXECUTE  ..........................................................\n'


def test_tty_macro_status(capsys):
    """Verify the macro_status() method works correctly."""
    output = Tty()
    output.log(OutputMethod.MACRO_STATUS)
    captured = capsys.readouterr()
    assert captured.out == 'COMPLETE\n'

    output.log(OutputMethod.MACRO_STATUS, '', '', 1)
    captured = capsys.readouterr()
    assert captured.out == 'FAILED  \n'


def test_tty_error(capsys):
    """Verify the error() method works correctly."""
    output = Tty()
    output.log(OutputMethod.ERROR, 'An error occurred.')
    captured = capsys.readouterr()
    assert captured.out == 'ERROR   \n'
    assert captured.err == 'An error occurred.\n'


def test_tty_info(capsys):
    """Verify the info() method works correctly."""
    output = Tty()
    output.log(OutputMethod.INFO, 'test message.')
    captured = capsys.readouterr()
    assert captured.out == 'OUTPUT  : test message.\n'


def test_silent_start_job(capsys):
    """Verify the silent start_job() method works correctly."""
    output = Silent()
    output.log(OutputMethod.JOB_START)
    captured = capsys.readouterr()
    assert not captured.out


def test_silent_end_job(capsys):
    """Verify the silent end_job() method works correctly."""
    output = Silent()
    output.log(OutputMethod.JOB_END)
    captured = capsys.readouterr()
    assert not captured.out


def test_silent_start_stage(capsys):
    """Verify the silent start_stage() method works correctly."""
    output = Silent()
    output.log(OutputMethod.STAGE_START)
    captured = capsys.readouterr()
    assert not captured.out


def test_silent_end_stage(capsys):
    """Verify the silent end_stage() method works correctly."""
    output = Silent()
    output.log(OutputMethod.STAGE_END)
    captured = capsys.readouterr()
    assert not captured.out


def test_silent_no_job(capsys):
    """Verify the silent no_job() method works correctly."""
    output = Silent()
    output.log(OutputMethod.NO_JOB)
    captured = capsys.readouterr()
    assert not captured.out


def test_silent_macro_start(capsys):
    """Verify the silent macro_start() method works correctly."""
    output = Silent()
    output.log(OutputMethod.MACRO_START)
    captured = capsys.readouterr()
    assert not captured.out


def test_silent_macro_status(capsys):
    """Verify the silent macro_status() method works correctly."""
    output = Silent()
    output.log(OutputMethod.MACRO_STATUS)
    captured = capsys.readouterr()
    assert not captured.out


def test_silent_error(capsys):
    """Verify the silent error() method works correctly."""
    output = Silent()
    output.log(OutputMethod.ERROR)
    captured = capsys.readouterr()
    assert not captured.out


def test_silent_info(capsys):
    """Verify the silent info() method works correctly."""
    output = Silent()
    output.log(OutputMethod.INFO)
    captured = capsys.readouterr()
    assert not captured.out
