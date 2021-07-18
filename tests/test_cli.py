"""This module hosts unit tests for the cli."""

import os
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


USAGE = """Usage: build-magic [OPTIONS] [ARGS]...

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


@pytest.fixture
def config_file(magic_dir):
    """Provides a config file in the temp directory."""
    filename = 'config.yaml'
    config = magic_dir / filename
    content = Path(__file__).parent.joinpath('files').joinpath(filename).read_text()
    config.write_text(content)
    yield config
    os.remove(magic_dir / filename)


@pytest.fixture
def multi_config(magic_dir):
    """Provides a config file with multiple stage in the temp directory."""
    filename = 'multi.yaml'
    config = magic_dir / filename
    content = Path(__file__).parent.joinpath('files').joinpath(filename).read_text()
    config.write_text(content)
    yield config
    os.remove(magic_dir / filename)


@pytest.fixture
def targets_config(magic_dir):
    """Provides a config file for testing multiple targets in the temp directory."""
    filename = 'targets.yaml'
    config = magic_dir / filename
    content = Path(__file__).parent.joinpath('files').joinpath(filename).read_text()
    config.write_text(content)
    yield config
    os.remove(magic_dir / filename)


@pytest.fixture
def default_config(magic_dir):
    """Provides a default config file in the current directory."""
    filename = 'build-magic.yaml'
    current = Path().cwd().resolve()
    config = current / filename
    content = Path(__file__).parent.joinpath('files').joinpath(filename).read_text()
    config.write_text(content)
    yield magic_dir
    os.chdir(str(current))
    os.remove(filename)


@pytest.fixture
def second_default(magic_dir):
    """Provides an additional default config as an alternative."""
    filename = 'build-magic.yml'
    current = Path().cwd().resolve()
    config = current / filename
    content = Path(__file__).parent.joinpath('files').joinpath('build-magic.yaml').read_text()
    config.write_text(content)
    yield magic_dir
    os.chdir(str(current))
    os.remove(filename)


@pytest.fixture
def variable_and_default_config(default_config, variables_config):
    """Provides a default and variable config file in the current directory."""
    filename = variables_config.name
    current = Path().cwd().resolve()
    config = current / filename
    content = variables_config.read_text()
    config.write_text(content)
    yield magic_dir
    os.chdir(str(current))
    os.remove(filename)


@pytest.fixture
def prompt_and_default_config(default_config, prompt_config):
    """Provides a default and prompt config file in the current directory."""
    filename = prompt_config.name
    current = Path().cwd().resolve()
    config = current / filename
    content = prompt_config.read_text()
    config.write_text(content)
    yield magic_dir
    os.chdir(str(current))
    os.remove(filename)


@pytest.fixture
def parameters_config(magic_dir):
    """Provides a config file with parameters in the temp directory."""
    filename = 'parameters.yaml'
    config = magic_dir / filename
    content = Path(__file__).parent.joinpath('files').joinpath(filename).read_text()
    config.write_text(content)
    yield config
    os.remove(magic_dir / filename)


@pytest.fixture
def variables_config(magic_dir):
    """Provides a config file for testing variable substitution in the temp directory."""
    filename = 'variables.yaml'
    config = magic_dir / filename
    content = Path(__file__).parent.joinpath('files').joinpath(filename).read_text()
    config.write_text(content)
    yield config
    os.remove(magic_dir / filename)


@pytest.fixture
def prompt_config(magic_dir):
    """Provides a config file with a prompt for variable input in the temp directory."""
    filename = 'prompt.yaml'
    config = magic_dir / filename
    content = Path(__file__).parent.joinpath('files').joinpath(filename).read_text()
    config.write_text(content)
    yield config
    os.remove(magic_dir / filename)


def test_cli_no_options(cli):
    """Verify that the usage is printed when no options or arguments are provided."""
    res = cli.invoke(build_magic)
    assert res.exit_code == ExitCode.NO_TESTS
    assert res.output == USAGE


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
  -t, --target TEXT               Run a particular stage by name.
  --wd DIRECTORY                  The working directory to run commands from.
  --continue / --stop             Continue to run after failure if True.
  -p, --parameter <TEXT TEXT>...  Key/value used for runner specific settings.
  -v, --variable <TEXT TEXT>...   Key/value config file variables.
  --prompt TEXT                   Config file variable with prompt for value.
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

    res = cli.invoke(build_magic, ['--name', 'test stage', '-c', 'execute', 'echo hello'])
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
    ref = """[ INFO  ] OUTPUT: hello world"""
    res = cli.invoke(build_magic, ['--verbose', '--plain', 'echo hello world'])
    assert res.exit_code == ExitCode.PASSED
    assert ref in res.output

    ref = """OUTPUT: hello world"""
    res = cli.invoke(build_magic, ['--verbose', 'echo hello world'])
    assert res.exit_code == ExitCode.PASSED
    assert ref in res.output

    ref = """OUTPUT: hello world"""
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
    assert 'OUTPUT: hello world' in res.output
    assert res.exit_code == ExitCode.PASSED


def test_cli_working_directory(cli, tmp_file):
    """Verify the --wd option works correctly."""
    res = cli.invoke(build_magic, ['--wd', str(tmp_file), '--verbose', '-c', 'execute', 'cat hello.txt'])
    assert 'OUTPUT: hello world' in res.output
    assert res.exit_code == ExitCode.PASSED


def test_cli_copy_working_directory(cli, current_file):
    """Verify the --copy and --wd options work together correctly."""
    res = cli.invoke(
        build_magic,
        ['--copy', '.', '--wd', str(current_file), '--verbose', '-c', 'build', 'cat hello.txt', 'hello.txt'],
    )
    assert 'OUTPUT: hello world' in res.output
    assert res.exit_code == ExitCode.PASSED


def test_cli_continue_on_fail(cli):
    """Verify the --continue option works correctly."""
    res = cli.invoke(build_magic, ['--verbose', '--continue', '-c', 'execute', 'cp', '-c', 'execute', 'echo hello'])
    assert 'OUTPUT: hello' in res.output
    assert res.exit_code == ExitCode.FAILED


def test_cli_stop_on_fail(cli):
    """Verify the --stop option works correctly."""
    res = cli.invoke(build_magic, ['--verbose', '--stop', '-c', 'execute', 'cp', '-c', 'execute', 'echo hello'])
    if sys.platform == 'linux':
        assert 'cp: missing file operand' in res.output
    else:
        assert 'usage: cp' in res.output or 'cp: missing file operand' in res.output
    assert 'OUTPUT: hello' not in res.output
    assert res.exit_code == ExitCode.FAILED


def test_cli_parameters(cli):
    """Verify the --parameter option works correctly."""
    res = cli.invoke(build_magic, ['-p', 'keytype', 'rsa', '--parameter', 'keypass', '1234', 'echo hello'])
    assert res.exit_code == ExitCode.PASSED
    assert '( 1/1 ) EXECUTE : echo hello ........................................ RUNNING' in res.output
    assert 'Stage 1 finished with result DONE' in res.output


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


def test_cli_config(cli, config_file):
    """Verify the --config option works correctly."""
    res = cli.invoke(build_magic, ['--config', str(config_file)])
    assert res.exit_code == ExitCode.PASSED
    assert 'Starting Stage 1: Test stage' in res.output
    assert '( 1/2 ) EXECUTE : echo hello' in res.output
    assert '( 2/2 ) EXECUTE : ls' in res.output
    assert 'Stage 1: Test stage - finished with result DONE' in res.output
    assert 'build-magic finished in' in res.output


def test_cli_config_multi(cli, config_file, multi_config):
    """Verify assigning multiple config files works correctly."""
    file1 = config_file
    file2 = multi_config
    res = cli.invoke(build_magic, ['--config', str(file1), '--config', str(file2)])
    assert res.exit_code == ExitCode.PASSED
    assert 'Starting Stage 1: Test stage' in res.output
    assert 'Starting Stage 2: Stage A' in res.output
    assert 'Starting Stage 3: Stage B' in res.output
    assert 'Stage 1: Test stage - finished with result DONE' in res.output
    assert 'Stage 2: Stage A - finished with result DONE' in res.output
    assert 'Stage 3: Stage B - finished with result DONE' in res.output


def test_cli_config_parameters(cli, mocker, parameters_config):
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
    res = cli.invoke(build_magic, ['--config', str(parameters_config)])
    assert res.exit_code == ExitCode.PASSED
    assert "Starting Stage 1" in res.output
    assert "( 1/1 ) EXECUTE : echo hello ........................................ RUNNING" in res.output
    assert "Stage 1 finished with result DONE" in res.output


def test_cli_target(cli, targets_config):
    """Verify the --target option works correctly."""
    # file = Path(resource_filename('tests', 'test_cli.py')).parent / 'files' / 'targets.yaml'
    res = cli.invoke(build_magic, ['-C', str(targets_config), '--target', 'Stage D', '-t', 'Stage B'])
    assert res.exit_code == ExitCode.PASSED
    out = res.output
    assert 'Stage D' in out
    out = out.split('\n', maxsplit=8)[-1]
    assert 'Stage B' in out
    assert '( 1/1 ) EXECUTE : echo "B" .......................................... RUNNING' in res.output
    assert "Stage 2: Stage B - finished with result DONE" in res.output


def test_cli_invalid_target(cli, targets_config):
    """Test the case where an invalid target name is provided."""
    res = cli.invoke(build_magic, ['-C', str(targets_config), '-t', 'blarg'])
    out = res.output
    assert res.exit_code == ExitCode.INPUT_ERROR
    assert out == "Target blarg not found among ['Stage A', 'Stage B', 'Stage C', 'Stage D'].\n"


def test_cli_default_config_all_stages(cli, default_config):
    """Verify the "all" argument works with a default config file."""
    res = cli.invoke(build_magic, ['all'])
    out = res.output
    assert res.exit_code == ExitCode.PASSED
    assert 'Starting Stage 1: build' in out
    assert 'Starting Stage 2: deploy' in out
    assert 'Starting Stage 3: release' in out


def test_cli_default_config_single_stage(cli, default_config):
    """Verify running a single stage by name as an argument works with a default config file."""
    res = cli.invoke(build_magic, ['deploy'])
    out = res.output
    assert res.exit_code == ExitCode.PASSED
    assert 'Starting Stage 1: build' not in out
    assert 'Starting Stage 1: deploy' in out
    assert 'Starting Stage 3: release' not in out


def test_cli_default_config_reorder_stages(cli, default_config):
    """Verify running stages in a custom order by arguments works with a default config file."""
    res = cli.invoke(build_magic, ['release', 'deploy', 'build'])
    out = res.output
    assert res.exit_code == ExitCode.PASSED
    assert 'Starting Stage 3: build' in out
    assert 'Starting Stage 2: deploy' in out
    assert 'Starting Stage 1: release' in out


def test_cli_default_config_repeat_stages(cli, default_config):
    """Verify running stages more than once by arguments works with a default config file."""
    res = cli.invoke(build_magic, ['release', 'release'])
    out = res.output
    assert res.exit_code == ExitCode.PASSED
    assert 'Starting Stage 1: release' in out
    assert 'Starting Stage 2: release' in out


def test_cli_default_config_with_targets(cli, default_config):
    """Verify running stages using the --target option works with a default config file."""
    res = cli.invoke(build_magic, ['-t', 'release', '-t', 'deploy', '-t', 'build'])
    out = res.output
    assert res.exit_code == ExitCode.PASSED
    assert 'Starting Stage 3: build' in out
    assert 'Starting Stage 2: deploy' in out
    assert 'Starting Stage 1: release' in out


def test_cli_default_config_repeat_stages_all(cli, default_config):
    """Verify running stages more than once by using all works with a default config file."""
    res = cli.invoke(build_magic, ['all', 'build'])
    out = res.output
    assert res.exit_code == ExitCode.PASSED
    assert 'Starting Stage 1: build' in out
    assert 'Starting Stage 2: deploy' in out
    assert 'Starting Stage 3: release' in out
    assert 'Starting Stage 4: build' in out


def test_cli_default_config_with_ad_hoc_command(cli, default_config):
    """Verify running running an ad hoc command works correctly with a default config file."""
    res = cli.invoke(build_magic, ['--name', 'test', 'echo "hello world"'])
    out = res.output
    assert res.exit_code == ExitCode.PASSED
    assert 'Starting Stage 1: test' in out
    assert 'echo "hello world"' in out


def test_cli_default_config_not_repeated(cli, default_config):
    """Test the case where a default config file is added explicitly with --command option."""
    res = cli.invoke(build_magic, ['-C', 'build-magic.yaml', '-t', 'deploy'])
    out = res.output
    assert res.exit_code == ExitCode.PASSED
    assert 'Starting Stage 1: deploy' in out
    assert 'Starting Stage 2: deploy' not in out


def test_cli_default_config_args_with_ad_hoc_command(cli, default_config):
    """Verify running stages from arguments with a command as an argument works with a default config file."""
    # This is an edge case that works, but can lead to weird behavior.
    res = cli.invoke(build_magic, ['echo "hello world"', 'all'])
    out = res.output
    assert res.exit_code == ExitCode.PASSED
    assert 'Starting Stage 1' in out
    assert 'echo "hello world" all' in out
    assert 'Starting Stage 2: build' in out
    assert 'Starting Stage 3: deploy' in out
    assert 'Starting Stage 4: release' in out


def test_cli_default_config_usage(cli, default_config):
    """Verify the usage is printed when a default config file is present."""
    res = cli.invoke(build_magic)
    assert res.exit_code == ExitCode.NO_TESTS
    assert res.output == USAGE


def test_cli_default_config_multiple_commands(cli, default_config):
    """Verify running multiple commands works when a default config file is present."""
    res = cli.invoke(build_magic, ['-c', 'execute', 'echo hello', '-c', 'execute', 'echo world'])
    out = res.output
    assert res.exit_code == ExitCode.PASSED
    assert "EXECUTE : echo hello" in out
    assert "EXECUTE : echo world" in out


def test_cli_default_config_multiple_defaults_error(cli, default_config, second_default):
    """Test the case where an error is raised if there's more than one default config file."""
    res = cli.invoke(build_magic, ['all'])
    out = res.output
    assert res.exit_code == ExitCode.INPUT_ERROR
    assert 'More than one config file found:' in out


def test_cli_variable(cli, variables_config):
    """Verify adding variables from the CLI properly replaces placeholders in a config file."""
    res = cli.invoke(build_magic, ['-C', variables_config, '--variable', 'ARCH', 'arm64', '-v', 'OS', 'linux'])
    out = res.output
    assert res.exit_code == ExitCode.PASSED
    assert "EXECUTE : export GOARCH=arm64" in out
    assert "EXECUTE : export GOOS=linux" in out


def test_cli_variable_not_found(cli, variables_config):
    """Test the case where variables aren't substituted because they aren't found in the config file."""
    res = cli.invoke(build_magic, ['-C', variables_config, '--variable', 'user', 'elle', '-v', 'host', 'server'])
    out = res.output
    assert res.exit_code == ExitCode.INPUT_ERROR
    assert out == 'No variable matches found.\n'


def test_cli_prompt(cli, prompt_config):
    """Verify the prompt option works correctly."""
    res = cli.invoke(build_magic, ['-C', prompt_config, '-v', 'user', 'elle', '--prompt', 'password'], input='secret\n')
    out = res.output
    assert res.exit_code == ExitCode.PASSED
    assert 'EXECUTE : echo elle:secret' in out


def test_cli_variables_with_two_config_files(cli, variable_and_default_config):
    """Verify using variables still works when there is one config file with placeholders and one without."""
    # Without the default config
    res = cli.invoke(build_magic, ['-C', 'variables.yaml', '--variable', 'ARCH', 'arm64', '-v', 'OS', 'linux'])
    out = res.output
    assert res.exit_code == ExitCode.PASSED
    assert "EXECUTE : export GOARCH=arm64" in out
    assert "EXECUTE : export GOOS=linux" in out

    # Including the default config
    res = cli.invoke(
        build_magic,
        ['-C', 'variables.yaml', '-C', 'build-magic.yaml', '--variable', 'ARCH', 'arm64', '-v', 'OS', 'linux'],
    )
    out = res.output
    assert res.exit_code == ExitCode.PASSED
    assert "EXECUTE : export GOARCH=arm64" in out
    assert "EXECUTE : export GOOS=linux" in out


def test_cli_prompt_with_two_config_files(cli, prompt_and_default_config):
    """Verify using prompt still works when there is one config file with placeholders and one without."""
    # Without the default config
    res = cli.invoke(build_magic, ['-C', 'prompt.yaml', '-v', 'user', 'elle', '--prompt', 'password'], input='secret\n')
    out = res.output
    assert res.exit_code == ExitCode.PASSED
    assert 'EXECUTE : echo elle:secret' in out

    # Including the default config
    res = cli.invoke(
        build_magic,
        ['-C', 'prompt.yaml', '-C', 'build-magic.yaml', '-v', 'user', 'elle', '--prompt', 'password'], input='secret\n',
    )
    out = res.output
    assert res.exit_code == ExitCode.PASSED
    assert 'EXECUTE : echo elle:secret' in out
