"""This module hosts unit tests for the cli."""

import os
import re
from pathlib import Path
from pkg_resources import resource_filename
import sys
from unittest.mock import MagicMock

from click.testing import CliRunner
import paramiko
import pytest

from build_magic import __version__ as version
from build_magic.cli import build_magic
from build_magic.reference import ExitCode


@pytest.fixture
def cli():
    """Provides a CliRunner object for invoking cli calls."""
    return CliRunner()


@pytest.fixture
def magic_dir(tmp_path_factory):
    """Provides a temporary directory for testing copy/working directory behavior."""
    magic = tmp_path_factory.mktemp('build_magic')
    return magic


@pytest.fixture
def tmp_file(magic_dir):
    """Provides a test file in the temp directory."""
    hello = magic_dir / 'hello.txt'
    hello.write_text('hello world')
    yield magic_dir
    os.remove('hello.txt')


@pytest.fixture
def current_file(magic_dir):
    """Provides a test file in the current directory."""
    current = Path().cwd().resolve()
    hello = current / 'hello.txt'
    hello.write_text('hello world')
    yield magic_dir
    os.chdir(str(current))
    os.remove('hello.txt')


def test_cli_no_options(cli):
    """Verify that the usage is printed when no options or arguments are provided."""
    ref = """Usage: build-magic [OPTIONS] [ARGS]...

build-magic is an un-opinionated build automation tool. Some potential uses include:
    * Building applications across multiple platforms.
    * Conducting installation dry runs.
    * Testing application installs across multiple platforms.
    * Deploying and installing artifacts to remote machines.

Examples:
* Archive two files on the local machine.
    build-magic tar -czf myfiles.tar.gz file1.txt file2.txt

* Archive two files on the local machine and delete the original files.
    build-magic -c build "tar -czf myfiles.tar.gz file1.txt file2.txt" -c execute "rm file1.txt file2.txt"
    
* Copy two files to a remote machine and archive them.
    build-magic -r remote -e user@myhost --copy . -c build "tar -czf myfiles.tar.gz f1.txt f2.txt" f1.txt f2.txt

* Build a project in a Linux container.
    build-magic -r docker -e Ubuntu:latest -c build "make all"

Use --help for detailed usage of each option.

Visit https://cmmorrow.github.io/build-magic/user_guide/cli_usage/ for a detailed usage description.

"""
    res = cli.invoke(build_magic)
    assert res.exit_code == ExitCode.NO_TESTS
    assert res.output == ref


def test_cli_help(cli):
    """Verify the help is displayed when given the --help option."""
    ref = """Usage: build-magic [OPTIONS] [ARGS]...

  An un-opinionated build automation tool.

  ARGS - Files as arguments to copy from the copy path to the working
  directory. Alternatively, ARGS can be a single command to execute if the
  --command option isn't used.

  Visit https://cmmorrow.github.io/build-magic/user_guide/cli_usage/ for a
  detailed usage description.

Options:
  -c, --command <TEXT TEXT>...    A directive, command pair to execute.
  -C, --config FILENAME           The config file to load parameters from.
  --copy TEXT                     Copy from the specified path.
  -e, --environment TEXT          The command runner environment to use.
  -r, --runner [local|remote|vagrant|docker]
                                  The command runner to use.
  --name TEXT                     The stage name to use.
  --wd DIRECTORY                  The working directory to run commands from.
  --continue / --stop             Continue to run after failure if True.
  -p, --parameter <TEXT TEXT>...  Key/value used for runner specific settings.
  --action [default|cleanup|persist]
                                  Setup and teardown action to perform.
  --plain / --fancy               Enable basic output. Ideal for automation.
  --quiet                         Suppress all output from build-magic.
  --verbose                       Verbose output -- stdout from executed
                                  commands will be printed.

  --version                       Show the version and exit.
  --help                          Show this message and exit.
"""
    res = cli.invoke(build_magic, ['--help'])
    assert res.exit_code == ExitCode.PASSED
    assert res.output == ref


def test_cli_single_command(cli):
    """Verify passing a single single command as arguments works correctly."""
    res = cli.invoke(build_magic, ['echo hello world'])
    assert res.exit_code == ExitCode.PASSED


def test_cli_multiple_commands(cli):
    """Verify passing multiple commands with the -c and --command options works correctly."""
    res = cli.invoke(build_magic, ['-c', 'execute', 'echo hello world', '-c', 'execute', 'ls'])
    assert res.exit_code == ExitCode.PASSED

    res = cli.invoke(build_magic, ['--command', 'execute', 'echo hello world', '--command', 'execute', 'ls'])
    assert res.exit_code == ExitCode.PASSED


def test_cli_runner(cli):
    """Verify the local runner is used with -r and --runner options works correctly."""
    res = cli.invoke(build_magic, ['-r', 'local', 'ls'])
    assert res.exit_code == ExitCode.PASSED

    res = cli.invoke(build_magic, ['--runner', 'local', 'ls'])
    assert res.exit_code == ExitCode.PASSED


def test_cli_stage_name(cli):
    """Verify the stage --name option works as expected."""
    res = cli.invoke(build_magic, ['--name', 'test stage', 'echo hello'])
    assert res.exit_code == ExitCode.PASSED
    assert 'Starting Stage 1: test stage' in res.output
    assert 'Stage 1: test stage - finished with result COMPLETE'


def test_cli_invalid_runner(cli):
    """Test the case where an invalid command runner is provided."""
    ref = """Usage: build-magic [OPTIONS] [ARGS]...
Try 'build-magic --help' for help.

Error: Invalid value for '--runner' / '-r': invalid choice: dummy. (choose from local, remote, vagrant, docker)
"""
    res = cli.invoke(build_magic, ['-r', 'dummy', 'ls'])
    assert res.exit_code == ExitCode.INPUT_ERROR
    assert res.output == ref


def test_cli_docker_missing_environment(cli):
    """Test the case where the docker runner is called without the environment option."""
    ref = """Environment must be a Docker image if using the Docker runner.
"""
    res = cli.invoke(build_magic, ['-r', 'docker', 'ls'])
    assert res.exit_code == ExitCode.INPUT_ERROR
    assert res.output == ref


def test_cli_vagrant_missing_environment(cli):
    """Test the case where the vagrant runner is called without the environment option."""
    ref = """Environment must be a path to a Vagrant file if using the Vagrant runner.
"""
    res = cli.invoke(build_magic, ['-r', 'vagrant', 'ls'])
    assert res.exit_code == ExitCode.INPUT_ERROR
    assert res.output == ref


def test_cli_empty_string_command(cli):
    """Test the case where the command provided is an empty string."""
    ref = """There are no commands to execute.
"""
    res = cli.invoke(build_magic, ['-c', 'execute', ''])
    assert res.exit_code == ExitCode.INPUT_ERROR
    assert res.output == ref


def test_cli_artifacts_but_empty_string_command(cli):
    """Test the case where artifacts are provided as arguments but with no command."""
    res = cli.invoke(build_magic, ['file1.txt', 'file2.txt'])
    assert res.exit_code == ExitCode.FAILED


def test_cli_options_no_command(cli):
    """Test the case where options are provided without a command."""
    res = cli.invoke(build_magic, ['--verbose', '--plain'])
    assert res.exit_code == ExitCode.NO_TESTS


def test_cli_verbose_output(cli):
    """Verify the --verbose option works correctly."""
    ref = """[ INFO  ] OUTPUT   : hello world"""
    res = cli.invoke(build_magic, ['--verbose', '--plain', 'echo hello world'])
    assert res.exit_code == ExitCode.PASSED
    assert ref in res.output

    ref = """OUTPUT  : hello world"""
    res = cli.invoke(build_magic, ['--verbose', 'echo hello world'])
    assert res.exit_code == ExitCode.PASSED
    assert ref in res.output

    ref = """OUTPUT  : hello world"""
    res = cli.invoke(build_magic, ['--verbose', '--fancy', 'echo hello world'])
    assert res.exit_code == ExitCode.PASSED
    assert ref in res.output


def test_cli_quiet(cli):
    """Verify the --quiet option supresses output correctly."""
    res = cli.invoke(build_magic, ['--quiet', '--verbose', 'echo hello world'])
    assert res.exit_code == ExitCode.PASSED
    assert not res.output

    res = cli.invoke(build_magic, ['--quiet', 'cp'])
    assert res.exit_code == ExitCode.FAILED
    assert not res.output


def test_cli_version(cli):
    """Verify the --version option works correctly."""
    res = cli.invoke(build_magic, ['--version'])
    assert res.exit_code == ExitCode.PASSED
    assert res.output == f'{version}\n'


def test_keyboard_interrupt(cli, mocker):
    """Test the case where build-magic is interrupted with SIGINT."""
    mocker.patch('build_magic.core.Engine.run', side_effect=KeyboardInterrupt)
    ref = """
build-magic interrupted and exiting....
"""
    res = cli.invoke(build_magic, ['sleep 5'])
    assert res.exit_code == ExitCode.INTERRUPTED
    assert res.output == ref


def test_cli_copy(cli, tmp_file):
    """Verify the --copy option works correctly."""
    res = cli.invoke(build_magic, ['--copy', str(tmp_file), '--verbose', '-c', 'execute', 'cat hello.txt', 'hello.txt'])
    assert 'OUTPUT  : hello world' in res.output
    assert res.exit_code == ExitCode.PASSED


def test_cli_working_directory(cli, tmp_file):
    """Verify the --wd option works correctly."""
    res = cli.invoke(build_magic, ['--wd', str(tmp_file), '--verbose', '-c', 'execute', 'cat hello.txt'])
    assert 'OUTPUT  : hello world' in res.output
    assert res.exit_code == ExitCode.PASSED


def test_cli_copy_working_directory(cli, current_file):
    """Verify the --copy and --wd options work together correctly."""
    res = cli.invoke(
        build_magic,
        ['--copy', '.', '--wd', str(current_file), '--verbose', '-c', 'build', 'cat hello.txt', 'hello.txt'],
    )
    assert 'OUTPUT  : hello world' in res.output
    assert res.exit_code == ExitCode.PASSED


def test_cli_continue_on_fail(cli):
    """Verify the --continue option works correctly."""
    res = cli.invoke(build_magic, ['--verbose', '--continue', '-c', 'execute', 'cp', '-c', 'execute', 'echo hello'])
    assert 'OUTPUT  : hello' in res.output
    assert res.exit_code == ExitCode.FAILED


def test_cli_stop_on_fail(cli):
    """Verify the --stop option works correctly."""
    res = cli.invoke(build_magic, ['--verbose', '--stop', '-c', 'execute', 'cp', '-c', 'execute', 'echo hello'])
    if sys.platform == 'linux':
        assert 'cp: missing file operand' in res.output
    else:
        assert 'usage: cp' in res.output
    assert 'OUTPUT  : hello' not in res.output
    assert res.exit_code == ExitCode.FAILED


def test_cli_parameters(cli):
    """Verify the --parameter option works correctly."""
    res = cli.invoke(build_magic, ['-p', 'keytype', 'rsa', '--parameter', 'keypass', '1234', 'echo hello'])
    assert res.exit_code == ExitCode.PASSED
    assert 'EXECUTE : echo hello ................................................ RUNNING' in res.output
    assert 'Stage 1 finished with result COMPLETE' in res.output


def test_cli_parameters_invalid_parameter(cli):
    """Test the case where an invalid parameter is provided."""
    res = cli.invoke(build_magic, ['-p', 'dummy', '1234', 'echo hello'])
    assert res.exit_code == ExitCode.INPUT_ERROR
    assert res.output == 'Parameter dummy is not a valid parameter.\n'


def test_cli_parameters_invalid_parameter_value(cli):
    """Test the case where an invalid parameter value is provided."""
    res = cli.invoke(build_magic, ['-p', 'keytype', 'dummy', 'echo hello'])
    assert res.exit_code == ExitCode.INPUT_ERROR
    assert "Validation failed: Value dummy is not one of " in res.output


def test_cli_config(cli):
    """Verify the --config option works correctly."""
    file = Path(resource_filename('tests', 'test_cli.py')).parent / 'files' / 'config.yaml'
    res = cli.invoke(build_magic, ['--config', str(file)])
    assert res.exit_code == ExitCode.PASSED
    assert 'Starting Stage 1: Test stage' in res.output
    assert 'EXECUTE : echo hello' in res.output
    assert 'EXECUTE : ls' in res.output
    assert 'Stage 1: Test stage - finished with result COMPLETE' in res.output
    assert 'build-magic finished in' in res.output


def test_cli_config_multi(cli):
    """Verify assigning multiple config files works correctly."""
    file1 = Path(resource_filename('tests', 'test_cli.py')).parent / 'files' / 'config.yaml'
    file2 = Path(resource_filename('tests', 'test_cli.py')).parent / 'files' / 'multi.yaml'
    res = cli.invoke(build_magic, ['--config', str(file1), '--config', str(file2)])
    assert res.exit_code == ExitCode.PASSED
    assert 'Starting Stage 1: Test stage' in res.output
    assert 'Starting Stage 2: Stage A' in res.output
    assert 'Starting Stage 3: Stage B' in res.output
    assert 'Stage 1: Test stage - finished with result COMPLETE' in res.output
    assert 'Stage 2: Stage A - finished with result COMPLETE' in res.output
    assert 'Stage 3: Stage B - finished with result COMPLETE' in res.output


def test_cli_config_parameters(cli, mocker):
    """Verify assigning parameters from a config file works correctly."""
    mocker.patch('paramiko.ECDSAKey.from_private_key_file')
    mocker.patch('build_magic.runner.Remote.connect', return_value=paramiko.SSHClient)
    mocker.patch(
        'paramiko.SSHClient.exec_command',
        return_value=(
            None,
            MagicMock(readlines=lambda: 'hello', channel=MagicMock(recv_exit_status=lambda: 0)),
            MagicMock(readlines=lambda: '')
        )
    )
    mocker.patch('paramiko.SSHClient.close')
    config = Path(resource_filename('tests', 'test_cli.py')).parent / 'files' / 'parameters.yaml'
    res = cli.invoke(build_magic, ['--config', str(config)])
    assert res.exit_code == ExitCode.PASSED
    assert "Starting Stage 1" in res.output
    assert "EXECUTE : echo hello ................................................ RUNNING" in res.output
    assert "Stage 1 finished with result COMPLETE" in res.output


def test_cli_target(cli):
    """Verify the --target option works correctly."""
    file = Path(resource_filename('tests', 'test_cli.py')).parent / 'files' / 'targets.yaml'
    res = cli.invoke(build_magic, ['-C', str(file), '--target', 'Stage D', '-t', 'Stage B'])
    assert res.exit_code == ExitCode.PASSED
    out = res.output
    assert 'Stage D' in out
    out = out.split('\n', maxsplit=8)[-1]
    assert 'Stage B' in out
