"""This module hosts unit tests for the Output classes."""
import os
from unittest.mock import MagicMock

from freezegun import freeze_time
import pytest

from build_magic import __version__ as version
from build_magic.output import Basic, Output, Silent, Tty
from build_magic.reference import OutputMethod


@freeze_time('2021-01-02 01:06:34')
def test_basic_log_method(capsys):
    """Verify the basic log() method works as expected."""
    output = Output()
    with pytest.raises(NotImplementedError):
        output.log(OutputMethod.JOB_START)

    output = Basic()
    output.log(OutputMethod.JOB_START)
    captured = capsys.readouterr()
    assert captured.out == f'2021-01-02T01:06:34 build-magic [ INFO  ] version {version}\n'

    log_output = captured.out
    output.start_job()
    captured = capsys.readouterr()
    assert log_output == captured.out


@freeze_time('2021-01-02 01:06:34')
def test_basic_print_output(capsys):
    """Verify the print_output() method works as expected."""
    output = Basic()
    output.print_output('This is a test', is_error=False)
    captured = capsys.readouterr()
    assert captured.out == "2021-01-02T01:06:34 build-magic [ INFO  ] OUTPUT: This is a test\n"

    output.print_output(b'This is a test', is_error=False)
    captured = capsys.readouterr()
    assert captured.out == "2021-01-02T01:06:34 build-magic [ INFO  ] OUTPUT: This is a test\n"

    output.print_output('This is a test', is_error=True)
    captured = capsys.readouterr()
    assert captured.out == "2021-01-02T01:06:34 build-magic [ ERROR ] This is a test\n"

    output.print_output(b'This is a test', is_error=True)
    captured = capsys.readouterr()
    assert captured.out == "2021-01-02T01:06:34 build-magic [ ERROR ] This is a test\n"


@freeze_time('2021-01-02 01:06:34')
def test_basic_end_job(capsys):
    """Verify the basic end_job() method works as expected."""
    output = Output()
    with pytest.raises(NotImplementedError):
        output.log(OutputMethod.JOB_END)

    output = Basic()
    output.log(OutputMethod.JOB_END)
    captured = capsys.readouterr()
    assert captured.out == '2021-01-02T01:06:34 build-magic [ INFO  ] Finished\n'


@freeze_time('2021-01-02 01:06:34')
def test_basic_start_stage(capsys):
    """Verify the basic start_stage() method works as expected."""
    output = Output()
    with pytest.raises(NotImplementedError):
        output.log(OutputMethod.STAGE_START)

    output = Basic()
    # Default stage number.
    output.log(OutputMethod.STAGE_START)
    captured = capsys.readouterr()
    assert captured.out == '2021-01-02T01:06:34 build-magic [ INFO  ] Starting Stage 1\n'

    # Assigned stage number.
    output.log(OutputMethod.STAGE_START, 7)
    captured = capsys.readouterr()
    assert captured.out == '2021-01-02T01:06:34 build-magic [ INFO  ] Starting Stage 7\n'

    # Assign stage name.
    output.log(OutputMethod.STAGE_START, 7, 'test stage')
    captured = capsys.readouterr()
    assert captured.out == '2021-01-02T01:06:34 build-magic [ INFO  ] Starting Stage 7: test stage\n'


@freeze_time('2021-01-02 01:06:34')
def test_basic_end_stage(capsys):
    """Verify the end_stage() method works as expected."""
    output = Output()
    with pytest.raises(NotImplementedError):
        output.log(OutputMethod.STAGE_END)

    output = Basic()
    # Default stage number and status.
    output.log(OutputMethod.STAGE_END)
    captured = capsys.readouterr()
    assert captured.out == '2021-01-02T01:06:34 build-magic [ INFO  ] Stage 1 complete with result DONE\n'

    # Stage number but default status.
    output.log(OutputMethod.STAGE_END, 7)
    captured = capsys.readouterr()
    assert captured.out == '2021-01-02T01:06:34 build-magic [ INFO  ] Stage 7 complete with result DONE\n'

    # Assigned stage number and status.
    output.log(OutputMethod.STAGE_END, 7, 1)
    captured = capsys.readouterr()
    assert captured.out == '2021-01-02T01:06:34 build-magic [ INFO  ] Stage 7 complete with result FAIL\n'

    # Assigned stage number, status, and name.
    output.log(OutputMethod.STAGE_END, 7, 1, 'test-stage')
    captured = capsys.readouterr()
    assert captured.out == '2021-01-02T01:06:34 build-magic [ INFO  ] Stage 7: test-stage - complete with result FAIL\n'


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
    assert captured.out == '2021-01-02T01:06:34 build-magic [ DONE  ] ( 1/1 ) BUILD   \n'

    # Default status code.
    output.log(OutputMethod.MACRO_STATUS, 'BUILD', 'tar -czf hello.tar.gz')
    captured = capsys.readouterr()
    assert captured.out == '2021-01-02T01:06:34 build-magic [ DONE  ] ( 1/1 ) BUILD    : tar -czf hello.tar.gz\n'

    # No command but failing status code.
    output.log(OutputMethod.MACRO_STATUS, 'BUILD', status_code=1)
    captured = capsys.readouterr()
    assert captured.out == '2021-01-02T01:06:34 build-magic [ FAIL  ] ( 1/1 ) BUILD   \n'

    # Command with failing status code.
    output.log(OutputMethod.MACRO_STATUS, 'BUILD', 'tar -czf hello.tar.gz', 1)
    captured = capsys.readouterr()
    assert captured.out == '2021-01-02T01:06:34 build-magic [ FAIL  ] ( 1/1 ) BUILD    : tar -czf hello.tar.gz\n'


@freeze_time('2021-01-02 01:06:34')
def test_basic_macro_status(capsys):
    """Verify the basic macro_status() method works as expected."""
    output = Basic()
    # Sequence of 12.
    output.log(OutputMethod.MACRO_STATUS, directive='BUILD', command='tar -czf hello.tar.gz', sequence=12)
    captured = capsys.readouterr()
    assert captured.out == '2021-01-02T01:06:34 build-magic [ DONE  ] ( 12/1 ) BUILD    : tar -czf hello.tar.gz\n'

    # Total of 42.
    output.log(OutputMethod.MACRO_STATUS, directive='BUILD', command='tar -czf hello.tar.gz', total=42)
    captured = capsys.readouterr()
    assert captured.out == '2021-01-02T01:06:34 build-magic [ DONE  ] (  1/42 ) BUILD    : tar -czf hello.tar.gz\n'

    # Sequence 12 of 42.
    output.log(OutputMethod.MACRO_STATUS, directive='BUILD', command='tar -czf hello.tar.gz', sequence=12, total=42)
    captured = capsys.readouterr()
    assert captured.out == '2021-01-02T01:06:34 build-magic [ DONE  ] ( 12/42 ) BUILD    : tar -czf hello.tar.gz\n'

    # Sequence 64 of 112.
    output.log(OutputMethod.MACRO_STATUS, directive='BUILD', command='tar -czf hello.tar.gz', sequence=64, total=112)
    captured = capsys.readouterr()
    assert captured.out == '2021-01-02T01:06:34 build-magic [ DONE  ] (  64/112 ) BUILD    : tar -czf hello.tar.gz\n'

    # Sequence 3 of 112.
    output.log(OutputMethod.MACRO_STATUS, directive='BUILD', command='tar -czf hello.tar.gz', sequence=3, total=112)
    captured = capsys.readouterr()
    assert captured.out == '2021-01-02T01:06:34 build-magic [ DONE  ] (   3/112 ) BUILD    : tar -czf hello.tar.gz\n'


@freeze_time('2021-01-02 01:06:34')
def test_basic_error(capsys):
    """Verify the basic error() method works as expected."""
    output = Output()
    with pytest.raises(NotImplementedError):
        output.log(OutputMethod.MACRO_STATUS)

    output = Basic()
    output.log(OutputMethod.ERROR, 'An error occurred.')
    captured = capsys.readouterr()
    assert captured.out == '2021-01-02T01:06:34 build-magic [ ERROR ] An error occurred.\n'


@freeze_time('2021-01-02 01:06:34')
def test_basic_info(capsys):
    """Verify the basic info() method works as expected."""
    output = Output()
    with pytest.raises(NotImplementedError):
        output.log(OutputMethod.INFO)

    output = Basic()
    output.log(OutputMethod.INFO, 'This is a test.\n\n\n')
    captured = capsys.readouterr()
    assert captured.out == '2021-01-02T01:06:34 build-magic [ INFO  ] OUTPUT: This is a test.\n'


def test_tty_get_width_and_height(mocker):
    """Verify the TTY get_width and get_height methods work correctly."""
    output = Tty()
    # Try the default case when not using a TTY.
    assert output.get_width() == 80
    assert output.get_height() == 20
    # Fake a TTY to verify the size.
    mocker.patch('os.get_terminal_size', return_value=MagicMock(columns=185, lines=35, spec=os.terminal_size))
    assert output.get_width() == 185
    assert output.get_height() == 35


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

    output.log(OutputMethod.STAGE_START, name='test-stage')
    captured = capsys.readouterr()
    assert captured.out == 'Starting Stage 1: test-stage\n'


def test_tty_end_stage(capsys):
    """Verify the end_stage() method works correctly."""
    output = Tty()
    output.log(OutputMethod.STAGE_END)
    captured = capsys.readouterr()
    assert captured.out == 'Stage 1 finished with result DONE\n\n'

    output.log(OutputMethod.STAGE_END, 1, 1)
    captured = capsys.readouterr()
    assert captured.out == 'Stage 1 finished with result FAILED\n\n'

    output.log(OutputMethod.STAGE_END, 1, 1, 'test-stage')
    captured = capsys.readouterr()
    assert captured.out == 'Stage 1: test-stage - finished with result FAILED\n\n'


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
    assert captured.out == '( 1/1 ) EXECUTE : ls ................................................ RUNNING\n'

    output.log(OutputMethod.MACRO_START, 'execute')
    captured = capsys.readouterr()
    assert captured.out == 'EXECUTE ..................................................\n'


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
    output.log(OutputMethod.INFO, 'test message.\n\n\n')
    captured = capsys.readouterr()
    assert captured.out == 'OUTPUT: test message.\n'


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
