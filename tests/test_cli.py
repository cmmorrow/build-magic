"""This module hosts unit tests for the cli."""

import os
from pathlib import Path
import platform
import sys
from unittest.mock import MagicMock

from click.testing import CliRunner
from docker.errors import ImageNotFound
import paramiko
import pytest
from yaml.composer import ComposerError

from build_magic import __version__ as version
from build_magic.cli import build_magic
from build_magic.exc import DockerDaemonError
from build_magic.reference import ExitCode


USAGE = """Usage: build-magic [OPTIONS] [ARGS]...

build-magic is an un-opinionated build automation tool. Some potential uses include:
    * Building applications across multiple platforms.
    * Conducting installation dry runs.
    * Automating repeated tasks.
    * Deploying and installing artifacts to remote machines.

Examples:
* Archive two files on the local machine.
    build-magic tar -czf myfiles.tar.gz file1.txt file2.txt

* Archive two files on the local machine and delete the original files.
    build-magic -c build "tar -czf myfiles.tar.gz file1.txt file2.txt" -c execute "rm file1.txt file2.txt"

* Copy two files to a remote machine and archive them.
    build-magic -r remote -e user@myhost --copy . -c build "tar -czf myfiles.tar.gz f1.txt f2.txt" f1.txt f2.txt

* Build a project in a Linux container.
    build-magic -r docker -e ubuntu:latest -c execute "configure" -c build "make all"

* Execute multiple commands in a config file.
    build-magic -C myconfig.yaml

* Execute a particular stage in a config file.
    build-magic -C myconfig.yaml -t build

* Execute a particular stage in a config file in the current directory named build-magic.yaml.
    build-magic build

* Execute all stages in a config file in the current directory named build-magic.yaml.
    build-magic all

Use --help for detailed usage of each option.

Visit https://cmmorrow.github.io/build-magic/user_guide/cli_usage/ for a detailed usage description.

"""


@pytest.fixture
def cli():
    """Provides a CliRunner object for invoking cli calls."""
    return CliRunner()


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
def targets_config(magic_dir):
    """Provides a config file for testing multiple targets in the temp directory."""
    filename = 'targets.yaml'
    config = magic_dir / filename
    content = Path(__file__).parent.joinpath('files').joinpath(filename).read_text()
    config.write_text(content)
    yield config
    os.remove(magic_dir / filename)


@pytest.fixture
def default_config():
    """Provides a default config file in the current directory."""
    filename = 'build-magic.yaml'
    current = Path().cwd().resolve()
    config = current / filename
    content = Path(__file__).parent.joinpath('files').joinpath(filename).read_text()
    config.write_text(content)
    yield config
    os.remove(config)


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
def invalid_config(magic_dir):
    """Provides an invalid config file."""
    filename = 'invalid.yaml'
    config = magic_dir / filename
    content = Path(__file__).parent.joinpath('files').joinpath(filename).read_text()
    config.write_text(content)
    yield config
    os.remove(magic_dir / filename)


@pytest.fixture
def variable_and_default_config(default_config, magic_dir, variables_config):
    """Provides a default and variable config file in the current directory."""
    filename = variables_config.name
    current = Path().cwd().resolve()
    config = current / filename
    content = variables_config.read_text()
    config.write_text(content)
    yield magic_dir
    os.remove(current / filename)


@pytest.fixture
def prompt_and_default_config(default_config, magic_dir, prompt_config):
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


@pytest.fixture
def prepare_config(magic_dir):
    """Provides a config file with a prepare section in the temp directory."""
    filename = 'prepare.yaml'
    config = magic_dir / filename
    content = Path(__file__).parent.joinpath('files').joinpath(filename).read_text()
    config.write_text(content)
    yield config
    os.remove(magic_dir / filename)


@pytest.fixture
def meta_config(magic_dir):
    """Provides a config file with meta data in the temp directory."""
    filename = 'meta.yaml'
    config = magic_dir / filename
    content = Path(__file__).parent.joinpath('files').joinpath(filename).read_text()
    config.write_text(content)
    yield config
    os.remove(magic_dir / filename)


@pytest.fixture
def skip1_config(magic_dir):
    """Provides a config file with one stage to skip in the temp directory."""
    filename = 'skip1.yaml'
    config = magic_dir / filename
    content = Path(__file__).parent.joinpath('files').joinpath(filename).read_text()
    config.write_text(content)
    yield config
    os.remove(magic_dir / filename)


@pytest.fixture
def skip1fail_config(magic_dir):
    """Provides a config file with one stage to skip and a second to fail in the temp directory."""
    filename = 'skip1fail.yaml'
    config = magic_dir / filename
    content = Path(__file__).parent.joinpath('files').joinpath(filename).read_text()
    config.write_text(content)
    yield config
    os.remove(magic_dir / filename)


@pytest.fixture
def env_and_dotenv_config(magic_dir):
    """Provides a config file with environment variables and dotenv file."""
    if platform.system() == 'Windows':
        config_filename = 'envs_win.yaml'
    else:
        config_filename = 'envs.yaml'
    dotenv_filename = 'test.env'

    config = magic_dir / config_filename
    dotenv = magic_dir / dotenv_filename

    content = Path(__file__).parent.joinpath('files').joinpath(config_filename).read_text()
    config.write_text(content)

    content = Path(__file__).parent.joinpath('files').joinpath(dotenv_filename).read_text()
    dotenv.write_text(content)

    yield magic_dir
    os.remove(magic_dir / config)
    os.remove(magic_dir / dotenv)


@pytest.fixture
def dotenv_config(magic_dir):
    """Provides a config file that uses a dotenv file in the temp directory."""
    if platform.system() == 'Windows':
        config_filename = 'dotenv_win.yaml'
    else:
        config_filename = 'dotenv.yaml'
    dotenv_filename = 'test.env'

    config = magic_dir / config_filename
    dotenv = magic_dir / dotenv_filename

    content = Path(__file__).parent.joinpath('files').joinpath(config_filename).read_text()
    config.write_text(content)

    content = Path(__file__).parent.joinpath('files').joinpath(dotenv_filename).read_text()
    dotenv.write_text(content)

    yield magic_dir
    os.remove(magic_dir / config)
    os.remove(magic_dir / dotenv)


def test_cli_no_options(cli):
    """Verify that the usage is printed when no options or arguments are provided."""
    res = cli.invoke(build_magic)
    assert res.exit_code == ExitCode.NO_TESTS
    assert res.output == USAGE


def test_cli_help(cli):
    """Verify the help is displayed when given the --help option."""
    ref = """Usage: build-magic [OPTIONS] [ARGS]...

  An un-opinionated build automation tool.

  ARGS - One of four possible uses based on context:

  1. If the --copy option is used, each argument in ARGS is a file name in the
  copy from directory to copy to the working directory.

  2. If there is a config file named build-magic.yaml in the working directory,
  ARGS is the name of a stage to execute.

  3. ARGS are considered a single command to execute if the --command option
  isn't used.

  4. ARGS are config file names if using the --info option.

  Visit https://cmmorrow.github.io/build-magic/user_guide/cli_usage/ for a
  detailed usage description.

Options:
  -c, --command <TEXT TEXT>...    A directive, command pair to execute.
  -C, --config FILENAME           The config file to load parameters from.
  --copy TEXT                     Copy files from the specified path.
  -e, --environment TEXT          The command runner environment to use.
  -r, --runner [local|remote|vagrant|docker]
                                  The command runner to use.
  --wd DIRECTORY                  The working directory to run commands from.
  --continue / --stop             Continue to run after failure if True.
  --name TEXT                     The stage name to use.
  --description TEXT              The stage description to use.
  -t, --target TEXT               Run a particular stage in a config file by
                                  name.
  -s, --skip TEXT                 Skip the specified stage.
  --info                          Display config file metadata, variables, and
                                  stage names.
  --export <TEXT TEXT>...         Export a Config File to GitHub Actions or
                                  GitLab CI.
  --env <TEXT TEXT>...            Provide an environment variable to set for
                                  stage execution.
  --dotenv FILENAME               Provide a dotenv file to set additional
                                  environment variables.
  --template                      Generates a config file template in the
                                  current directory.
  -p, --parameter <TEXT TEXT>...  Space separated key/value used for runner
                                  specific settings.
  -v, --variable <TEXT TEXT>...   Space separated key/value config file
                                  variables.
  --validate FILENAME             Validate a config file by name.
  --prompt TEXT                   Config file variable with prompt for value.
  --action [default|cleanup|persist]
                                  The setup and teardown action to perform.
  --plain                         Enables basic output. Ideal for logging and
                                  automation.
  --fancy                         Enables output with colors. Ideal for an
                                  interactive terminal session.
  --quiet                         Suppresses all output from build-magic.
  --verbose                       Verbose output -- stdout from executed
                                  commands will be printed when complete.
  --version                       Show the version and exit.
  --help                          Show this message and exit.
"""
    res = cli.invoke(build_magic, ['--help'])
    assert res.exit_code == ExitCode.PASSED
    assert res.output == ref


def test_cli_single_command(cli):
    """Verify passing a single single command as arguments works correctly."""
    res = cli.invoke(build_magic, ['echo hello world'])
    out = res.output
    assert res.exit_code == ExitCode.PASSED
    assert 'Starting Stage 1' in out
    assert '=> Current working directory: .' in out


def test_cli_multiple_commands(cli, ls):
    """Verify passing multiple commands with the -c and --command options works correctly."""
    res = cli.invoke(build_magic, ['-c', 'execute', 'echo hello world', '-c', 'execute', f'{ls}'])
    assert res.exit_code == ExitCode.PASSED

    res = cli.invoke(build_magic, ['--command', 'execute', 'echo hello world', '--command', 'execute', f'{ls}'])
    assert res.exit_code == ExitCode.PASSED


def test_cli_runner(cli, ls):
    """Verify the local runner is used with -r and --runner options works correctly."""
    res = cli.invoke(build_magic, ['-r', 'local', f'{ls}'])
    assert res.exit_code == ExitCode.PASSED

    res = cli.invoke(build_magic, ['--runner', 'local', f'{ls}'])
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


def test_cli_description(cli):
    """Verify providing a description works correctly."""
    res = cli.invoke(build_magic, ['--description', 'This is a test', 'echo hello world'])
    out = res.output
    assert res.exit_code == ExitCode.PASSED
    assert 'Starting Stage 1 - This is a test' in out


def test_cli_name_and_description(cli):
    """Verify providing a name and description works correctly."""
    res = cli.invoke(build_magic, ['--name', 'test', '--description', 'This is a test', 'echo hello world'])
    out = res.output
    assert res.exit_code == ExitCode.PASSED
    assert 'Starting Stage 1: test - This is a test' in out


def test_cli_invalid_runner(cli):
    """Test the case where an invalid command runner is provided."""
    ref = """Usage: build-magic [OPTIONS] [ARGS]...
Try 'build-magic --help' for help.

Error: Invalid value for '--runner' / '-r': 'dummy' is not one of 'local', 'remote', 'vagrant', 'docker'.
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


def test_cli_docker_environment_not_found(cli, mocker):
    """Test the case where the requested image is not found."""
    mocker.patch('docker.client.DockerClient.containers', new_callable=mocker.PropertyMock)
    mocker.patch('docker.client.DockerClient.containers.list', return_value=[])
    mocker.patch('docker.client.DockerClient.containers.run', side_effect=ImageNotFound('Not Found'))
    res = cli.invoke(build_magic, ['-r', 'docker', '-e', 'centos:7', 'echo', '"hello world"'])
    assert 'Setup failed: Not Found' in res.output


def test_cli_docker_container_already_running(cli, mocker):
    """Test the case where a build-magic container is already running."""
    mocker.patch('docker.client.DockerClient.containers', new_callable=mocker.PropertyMock)
    mocker.patch('docker.client.DockerClient.containers.list', return_value=[MagicMock])
    res = cli.invoke(build_magic, ['-r', 'docker', '-e', 'centos:7', 'echo', '"hello world"'])
    assert 'Setup failed: A build-magic container is already running.' in res.output


def test_cli_docker_not_found(cli, mocker):
    """Test the case where Docker isn't running or isn't installed."""
    mocker.patch('docker.from_env', side_effect=DockerDaemonError)
    res = cli.invoke(build_magic, ['-r', 'docker', '-e', 'alpine:latest', 'echo', '"hello world"'])
    assert 'Setup failed: Cannot connect to Docker daemon. Is Docker installed and running?' in res.output


def test_cli_docker_hostwd_not_found(cli, mocker):
    """Test the case where the hostwd doesn't exist."""
    mocker.patch('pathlib.Path.exists', return_value=False)
    res = cli.invoke(build_magic, ['-p', 'hostwd', 'fake', '-r', 'docker', '-e', 'alpine:latest', 'echo', 'hello'])
    assert res.output == 'The host working directory was not found.\n'
    assert res.exit_code == ExitCode.INPUT_ERROR.value


def test_cli_vagrant_not_found(cli, mocker):
    """Test the case where Vagrant isn't found or installed."""
    mocker.patch('vagrant.which', return_value=None)
    mocker.patch('pathlib.Path.exists', return_value=True)
    res = cli.invoke(build_magic, ['-r', 'vagrant', '-e', 'files/Vagrantfile', 'echo', '"hello world"'])
    assert 'The Vagrant executable cannot be found. Please check if it is in the system path.' in res.output


def test_cli_vagrant_hostwd_not_found(cli, mocker):
    """Test the case where the hostwd doesn't exist."""
    mocker.patch('pathlib.Path.exists', return_value=False)
    res = cli.invoke(build_magic, ['-r', 'vagrant', '-e', 'fake/Vagrantfile', 'echo', '"hello world"'])
    assert res.output == 'The host working directory was not found.\n'
    assert res.exit_code == ExitCode.INPUT_ERROR.value


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
    res = cli.invoke(build_magic, ['blah', 'file2.txt'])
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


def test_cli_fancy(cli):
    """Verify the --fancy option works correctly."""
    ref = """( 1/1 ) EXECUTE : echo hello world ."""
    res = cli.invoke(build_magic, ['--fancy', 'echo hello world'])
    assert res.exit_code == ExitCode.PASSED
    assert ref in res.output

    res = cli.invoke(build_magic, ['echo hello world'])
    assert res.exit_code == ExitCode.PASSED
    assert ref in res.output


def test_cli_plain_and_fancy(cli):
    """Test the case where both --plain and --fancy options are provided."""
    ref = """[ DONE  ] ( 1/1 ) EXECUTE  : echo hello world"""
    res = cli.invoke(build_magic, ['--plain', '--fancy', 'echo hello world'])
    assert res.exit_code == ExitCode.PASSED
    assert ref in res.output

    res = cli.invoke(build_magic, ['--fancy', '--plain', 'echo hello world'])
    assert res.exit_code == ExitCode.PASSED
    assert ref in res.output


def test_cli_plain_quiet(cli):
    """Test the case where both --plain and --quiet options are provided."""
    res = cli.invoke(build_magic, ['--plain', '--quiet', 'echo hello world'])
    assert res.exit_code == ExitCode.PASSED
    assert not res.output

    res = cli.invoke(build_magic, ['--quiet', '--plain', 'echo hello world'])
    assert res.exit_code == ExitCode.PASSED
    assert not res.output


def test_cli_fancy_quiet(cli):
    """Test the case where both --fancy and --quiet options are provided."""
    res = cli.invoke(build_magic, ['--fancy', '--quiet', 'echo hello world'])
    assert res.exit_code == ExitCode.PASSED
    assert not res.output

    res = cli.invoke(build_magic, ['--quiet', '--fancy', 'echo hello world'])
    assert res.exit_code == ExitCode.PASSED
    assert not res.output


def test_cli_fancy_plain_quiet(cli):
    """Test the case where --fancy, --plain, and --quiet are provided."""
    res = cli.invoke(build_magic, ['--fancy', '--plain', '--quiet', 'echo hello world'])
    assert res.exit_code == ExitCode.PASSED
    assert not res.output

    res = cli.invoke(build_magic, ['--plain', '--quiet', '--fancy', 'echo hello world'])
    assert res.exit_code == ExitCode.PASSED
    assert not res.output

    res = cli.invoke(build_magic, ['--quiet', '--fancy', '--plain', 'echo hello world'])
    assert res.exit_code == ExitCode.PASSED
    assert not res.output

    res = cli.invoke(build_magic, ['--fancy', '--quiet', '--plain', 'echo hello world'])
    assert res.exit_code == ExitCode.PASSED
    assert not res.output

    res = cli.invoke(build_magic, ['--quiet', '--plain', '--fancy', 'echo hello world'])
    assert res.exit_code == ExitCode.PASSED
    assert not res.output

    res = cli.invoke(build_magic, ['--plain', '--fancy', '--quiet', 'echo hello world'])
    assert res.exit_code == ExitCode.PASSED
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


def test_cli_copy(cat, cli, tmp_file):
    """Verify the --copy option works correctly."""
    res = cli.invoke(
        build_magic,
        ['--copy', str(tmp_file), '--verbose', '-c', 'execute', f'{cat} hello.txt', 'hello.txt'],
    )
    assert 'OUTPUT: hello world' in res.output
    assert res.exit_code == ExitCode.PASSED


def test_cli_working_directory(cat, cli, tmp_file):
    """Verify the --wd option works correctly."""
    res = cli.invoke(build_magic, ['--wd', str(tmp_file), '--verbose', '-c', 'execute', f'{cat} hello.txt'])
    assert res.exit_code == ExitCode.PASSED
    assert 'OUTPUT: hello world' in res.output


def test_cli_copy_working_directory(cat, cli, current_file):
    """Verify the --copy and --wd options work together correctly."""
    res = cli.invoke(
        build_magic,
        ['--copy', '.', '--wd', str(current_file), '--verbose', '-c', 'build', f'{cat} hello.txt', 'hello.txt'],
    )
    assert 'OUTPUT: hello world' in res.output
    assert res.exit_code == ExitCode.PASSED


def test_cli_continue_on_fail(cli):
    """Verify the --continue option works correctly."""
    res = cli.invoke(build_magic, ['--verbose', '--continue', '-c', 'execute', 'cp', '-c', 'execute', 'echo hello'])
    assert 'OUTPUT: hello' in res.output
    assert res.exit_code == ExitCode.FAILED


def test_cli_stop_on_fail(cli, cp):
    """Verify the --stop option works correctly."""
    res = cli.invoke(build_magic, ['--verbose', '--stop', '-c', 'execute', f'{cp}', '-c', 'execute', 'echo hello'])
    if sys.platform == 'linux':
        assert 'cp: missing file operand' in res.output
    elif sys.platform == 'win32':
        assert 'The syntax of the command is incorrect.' in res.output
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


def test_cli_config_template(cli):
    """Verify the --template option works correctly."""
    filename = 'build-magic_template.yaml'
    current = Path().cwd().resolve()
    res = cli.invoke(build_magic, ['--template'])
    assert current.joinpath(filename).exists()
    os.remove(filename)
    assert res.exit_code == ExitCode.PASSED


def test_cli_template_exists(cli):
    """Test the case where a template config file cannot be generated because one already exists."""
    filename = 'build-magic_template.yaml'
    current = Path.cwd().resolve()
    Path.touch(current.joinpath(filename))
    res = cli.invoke(build_magic, ['--template'])
    os.remove(filename)
    assert res.exit_code == ExitCode.INPUT_ERROR
    assert res.output == 'Cannot generate the config template because it already exists!\n'


def test_cli_template_permission_error(cli, mocker):
    """Test the case where a template config file cannot be generated because the user does not have permission."""
    mocker.patch('build_magic.core.generate_config_template', side_effect=PermissionError)
    res = cli.invoke(build_magic, ['--template'])
    assert res.exit_code == ExitCode.INPUT_ERROR
    assert res.output == "Cannot generate the config template because build-magic doesn't have permission.\n"


def test_cli_config(cli, config_file, ls):
    """Verify the --config option works correctly."""
    res = cli.invoke(build_magic, ['--config', str(config_file)])
    assert res.exit_code == ExitCode.PASSED
    assert 'Starting Stage 1: Test stage' in res.output
    assert '( 1/2 ) EXECUTE : echo hello' in res.output
    assert f'( 2/2 ) EXECUTE : {ls}' in res.output
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
    res = cli.invoke(build_magic, ['-C', str(targets_config), '--target', 'Stage D', '-t', 'Stage B'])
    assert res.exit_code == ExitCode.PASSED
    out = res.output
    assert 'Stage D - Test Stage D' in out
    out = out.split('\n', maxsplit=8)[-1]
    assert 'Stage B - Test Stage B' in out
    assert '( 1/1 ) EXECUTE : echo "B" .......................................... RUNNING' in res.output
    assert "Stage 2: Stage B - finished with result DONE" in res.output


def test_cli_invalid_target(cli, targets_config):
    """Test the case where an invalid target name is provided."""
    res = cli.invoke(build_magic, ['-C', str(targets_config), '-t', 'blarg'])
    out = res.output
    assert res.exit_code == ExitCode.INPUT_ERROR
    assert out == "Target blarg not found among ['Stage A', 'Stage B', 'Stage C', 'Stage D'].\n"


def test_cli_yaml_parsing_error(cli, config_file, mocker):
    """Test the case where there's an error when parsing a config file."""
    yaml_load = mocker.patch('yaml.safe_load', side_effect=ComposerError('YAML error'))
    res = cli.invoke(build_magic, ['-C', str(config_file)])
    out = res.output
    assert res.exit_code == ExitCode.INPUT_ERROR
    assert out == 'YAML error\n'
    assert yaml_load.call_count == 1


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
    assert ('Starting Stage 1: build' in out) is False
    assert ('Starting Stage 1: deploy' in out) is True
    assert ('Starting Stage 3: release' in out) is False


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
    """Verify running an ad hoc command works correctly with a default config file."""
    res = cli.invoke(build_magic, ['--name', 'test', 'echo "hello world"'])
    out = res.output
    assert res.exit_code == ExitCode.PASSED
    assert ('Starting Stage 1: test' in out) is True
    assert ('echo "hello world"' in out) is True


def test_cli_default_config_with_ad_hoc_command_no_quotes(cli, default_config):
    """Verify running an un-quoted ad hoc command works correctly with a default config file.

    This test covers an edge case where a default config exists, but an un-quoted ad hoc command is provided,
    causing the command to be executed n times where n is the number of args in the command."""
    res = cli.invoke(build_magic, ['echo', 'hello', 'world'])
    out = res.output
    assert res.exit_code == ExitCode.PASSED
    assert ('Starting Stage 1' in out) is True
    assert ('echo hello world' in out) is True
    assert ('Starting Stage 2' in out) is False
    assert ('Starting Stage 3' in out) is False


def test_cli_default_config_not_repeated(cli, default_config):
    """Test the case where a default config file is added explicitly with --command option."""
    res = cli.invoke(build_magic, ['-C', 'build-magic.yaml', '-t', 'deploy'])
    out = res.output
    assert res.exit_code == ExitCode.PASSED
    assert ('Starting Stage 1: deploy' in out) is True
    assert ('Starting Stage 2: deploy' in out) is False


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
    assert "EXECUTE : echo GOARCH=arm64" in out
    assert "EXECUTE : echo GOOS=linux" in out


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
    assert 'EXECUTE : echo elle:******' in out


def test_cli_variables_with_two_config_files(cli, variable_and_default_config):
    """Verify using variables still works when there is one config file with placeholders and one without."""
    # Without the default config
    res = cli.invoke(build_magic, ['-C', 'variables.yaml', '--variable', 'ARCH', 'arm64', '-v', 'OS', 'linux'])
    out = res.output
    assert res.exit_code == ExitCode.PASSED
    assert "EXECUTE : echo GOARCH=arm64" in out
    assert "EXECUTE : echo GOOS=linux" in out

    # Including the default config
    res = cli.invoke(
        build_magic,
        ['-C', 'variables.yaml', '-C', 'build-magic.yaml', '--variable', 'ARCH', 'arm64', '-v', 'OS', 'linux'],
    )
    out = res.output
    assert res.exit_code == ExitCode.PASSED
    assert "EXECUTE : echo GOARCH=arm64" in out
    assert "EXECUTE : echo GOOS=linux" in out


def test_cli_prompt_with_two_config_files(cli, prompt_and_default_config):
    """Verify using prompt still works when there is one config file with placeholders and one without."""
    # Without the default config
    res = cli.invoke(
        build_magic,
        ['-C', 'prompt.yaml', '-v', 'user', 'elle', '--prompt', 'password'],
        input='secret\n',
    )
    out = res.output
    assert res.exit_code == ExitCode.PASSED
    assert 'EXECUTE : echo elle:******' in out

    # Including the default config
    res = cli.invoke(
        build_magic,
        ['-C', 'prompt.yaml', '-C', 'build-magic.yaml', '-v', 'user', 'elle', '--prompt', 'password'],
        input='secret\n',
    )
    out = res.output
    assert res.exit_code == ExitCode.PASSED
    assert 'EXECUTE : echo elle:******' in out


def test_cli_config_with_prepare(cli, prepare_config):
    """Verify a config file with a prepare section works correctly."""
    res = cli.invoke(build_magic, ['-C', prepare_config])
    out = res.output
    assert res.exit_code == ExitCode.PASSED
    assert '( 1/3 ) EXECUTE : echo hello' in out
    assert '( 2/3 ) EXECUTE : echo spam' in out
    assert '( 3/3 ) EXECUTE : echo goodbye' in out
    assert '( 1/2 ) EXECUTE : echo goodbye' in out
    assert '( 2/2 ) EXECUTE : echo spam' in out


def test_cli_config_with_metadata(cli, meta_config):
    """Verify a config file with metadata works correctly."""
    res = cli.invoke(build_magic, ['-C', meta_config])
    out = res.output
    assert res.exit_code == ExitCode.PASSED
    assert '( 1/1 ) EXECUTE : echo "hello world"' in out


def test_cli_info_no_config(cli):
    """Test the case where the --info option is used with a config file."""
    ref = """No config files specified.\n"""
    res = cli.invoke(build_magic, ['--info'])
    out = res.output
    assert res.exit_code == ExitCode.INPUT_ERROR
    assert out == ref


def test_cli_info(cli, meta_config):
    """Verify the --info option works correctly with one config file."""
    ref = """version:      0.1.0
author:       Beckett Mariner
maintainer:   Brad Boimler
created:      04/17/2382
modified:     06/02/2382
description:  Second contact
stage:        Test
"""
    res = cli.invoke(build_magic, ['--info', str(meta_config)])
    out = res.output
    assert res.exit_code == ExitCode.PASSED
    assert out == ref


def test_cli_info_two_configs(cli):
    """Verify the --info option works correctly with more than one config file."""
    meta = str(Path(__file__).parent / 'files' / 'meta.yaml')
    variables = str(Path(__file__).parent / 'files' / 'variables.yaml')
    ref = f"""{meta}  version:      0.1.0
{meta}  author:       Beckett Mariner
{meta}  maintainer:   Brad Boimler
{meta}  created:      04/17/2382
{meta}  modified:     06/02/2382
{meta}  description:  Second contact
{meta}  stage:        Test
{variables}  variable:  ARCH
{variables}  variable:  OS
{variables}  stage:     Variable Test
"""
    res = cli.invoke(build_magic, ['--info', meta, variables])
    out = res.output
    assert res.exit_code == ExitCode.PASSED
    assert out == ref


def test_cli_info_no_meta_data(cli):
    """Test the case where --info is called on a Config File without meta data or a stage name."""
    skip1 = str(Path(__file__).parent / 'files' / 'skip1.yaml')
    res = cli.invoke(build_magic, ['--info', skip1])
    out = res.output
    assert res.exit_code == ExitCode.PASSED
    assert out == ''


def test_cli_info_two_configs_no_meta_data(cli):
    """Test the case where --info is called on two Config Files where one doesn't have meta data or a stage name."""
    meta = str(Path(__file__).parent / 'files' / 'meta.yaml')
    skip1 = str(Path(__file__).parent / 'files' / 'skip1.yaml')
    res = cli.invoke(build_magic, ['--info', skip1, meta])
    out = res.output
    assert res.exit_code == ExitCode.PASSED
    assert 'meta.yaml  author:       Beckett Mariner' in out
    assert 'meta.yaml  maintainer:   Brad Boimler' in out
    assert 'meta.yaml  created:      04/17/2382' in out
    assert 'meta.yaml  modified:     06/02/2382' in out
    assert 'meta.yaml  description:  Second contact' in out
    assert 'meta.yaml  stage:        Test' in out


def test_cli_info_extra_options_and_args(cli):
    """Test the case where extra args are given to the --info option."""
    meta = str(Path(__file__).parent / 'files' / 'meta.yaml')
    targets = str(Path(__file__).parent / 'files' / 'targets.yaml')
    ref = "[Errno 2] No such file or directory: 'echo hello world'\n"
    res = cli.invoke(build_magic, ['--info', meta, targets, '--verbose', 'echo hello world'])
    out = res.output
    assert res.exit_code == ExitCode.INPUT_ERROR
    assert out == ref


def test_cli_dotenv(cli, env):
    """Verify the --dotenv option works correctly."""
    env_file = Path(__file__).parent / 'files' / 'test.env'
    res = cli.invoke(build_magic, ['--dotenv', env_file, '--verbose', env])
    out = res.output
    assert res.exit_code == ExitCode.PASSED
    assert 'FOO=bar' in out
    assert 'HELLO=world' in out
    assert 'dummy' not in out


def test_cli_dotenv_warn(cli):
    """Test the case where a dotenv file without a .env extension is provided."""
    cmd = 'env'
    env_file = Path(__file__).parent / 'files' / 'meta.yaml'
    res = cli.invoke(build_magic, ['--dotenv', env_file, '--verbose', cmd], input='N')
    out = res.output
    assert res.exit_code == ExitCode.INPUT_ERROR
    assert 'The provided dotenv file does not have a .env extension. Continue anyway?' in out


def test_cli_dotenv_config_file(cli, dotenv_config):
    """Verify the dotenv config file property works correctly."""
    if platform.system() == 'Windows':
        config = dotenv_config / 'dotenv_win.yaml'
    else:
        config = dotenv_config / 'dotenv.yaml'
    res = cli.invoke(build_magic, ['-C', config, '--verbose'])
    out = res.output
    assert res.exit_code == ExitCode.PASSED
    assert 'FOO=bar' in out
    assert 'HELLO=world' in out
    assert 'dummy' not in out


def test_cli_environment_variables(cli):
    """Verify setting environment variables works correctly."""
    if platform.system() == 'Windows':
        cmd = '%HELLO% %WORLD%'
    else:
        cmd = '$HELLO $WORLD'
    res = cli.invoke(
        build_magic, [
            '--env',
            'HELLO',
            'hello',
            '--env',
            'WORLD',
            'world',
            '--verbose',
            'echo',
            cmd,
        ]
    )
    out = res.output
    assert res.exit_code == ExitCode.PASSED
    assert 'OUTPUT: hello world' in out


def test_combine_envs_and_dotenv(cli):
    """Verify that using a dotenv and individual environment variables are merged correctly."""
    env_file = Path(__file__).parent / 'files' / 'test.env'
    if platform.system() == 'Windows':
        cmd = '%HELLO% %WORLD% %FOO%'
    else:
        cmd = '$HELLO $WORLD $FOO'
    res = cli.invoke(
        build_magic, [
            '--env',
            'HELLO',
            'hello',
            '--env',
            'WORLD',
            'world',
            '--dotenv',
            env_file,
            '--verbose',
            'echo',
            cmd,
        ]
    )
    out = res.output
    assert res.exit_code == ExitCode.PASSED
    assert 'OUTPUT: hello world bar' in out


def test_envs_config_file(cli, env_and_dotenv_config):
    """Verify that using environment variables with a dotenv file in a config file work correctly."""
    if platform.system() == 'Windows':
        config = env_and_dotenv_config / 'envs_win.yaml'
    else:
        config = env_and_dotenv_config / 'envs.yaml'
    res = cli.invoke(build_magic, ['-C', config, '--verbose'])
    out = res.output
    assert res.exit_code == ExitCode.PASSED
    assert 'OUTPUT: hello world bar' in out


def test_labels_config_file(cli, labels_config):
    """Verify that commands with labels in a config file are displayed properly."""
    res = cli.invoke(build_magic, ['-C', labels_config, '--verbose'])
    out = res.output
    assert res.exit_code == ExitCode.PASSED
    assert '( 1/2 ) EXECUTE : Say hello to the user.' in out
    assert '( 2/2 ) EXECUTE : Say goodbye to the user.' in out


def test_skip_single_stage(cli, mocker):
    """Verify that skipping a single stage works correctly."""
    mocker.patch('subprocess.run', return_value=MagicMock(returncode=120, stdout=b'command not found\n'))
    res = cli.invoke(build_magic, ['-r', 'local', '-e', 'windows', 'echo hello world'])
    out = res.output
    assert res.exit_code == ExitCode.SKIPPED
    assert 'Skipping Stage 1 because OS is not windows.' in out
    assert 'Stage 1 finished with result SKIPPED' in out


def test_skip_one_stage_pass(cli, mocker, skip1_config):
    """Verify that skipping a single stage followed by a passing stage works correctly."""
    mocker.patch(
        'subprocess.run',
        side_effect=(
            MagicMock(
                returncode=120,
                stdout=b'command not found\n',
            ),
            MagicMock(
                returncode=0,
                stdout=b'hello world',
            )
        )
    )
    res = cli.invoke(build_magic, ['-C', skip1_config])
    out = res.output
    assert res.exit_code == ExitCode.PASSED
    assert 'Stage 1 finished with result SKIPPED' in out
    assert 'Stage 2 finished with result DONE' in out


def test_skip_one_stage_fail(cli, mocker, skip1fail_config):
    """Verify that skipping a single stage followed by a failing stage works correctly."""
    mocker.patch(
        'subprocess.run',
        side_effect=(
            MagicMock(
                returncode=120,
                stdout=b'command not found\n',
            ),
            MagicMock(
                returncode=1,
                stdout=b'cat: blah.txt: No such file or directory',
            )
        )
    )
    res = cli.invoke(build_magic, ['-C', skip1fail_config])
    out = res.output
    assert res.exit_code == ExitCode.FAILED
    assert 'Stage 1 finished with result SKIPPED' in out
    assert 'Stage 2 finished with result FAILED' in out


def test_manual_skip_one_stage(cli, targets_config):
    """Verify manually skipping a single stage works correctly."""
    res = cli.invoke(build_magic, ['-C', targets_config, '--skip', 'Stage C'])
    out = res.output
    assert res.exit_code == ExitCode.PASSED
    assert 'Stage 1: Stage A - finished with result DONE' in out
    assert 'Stage 2: Stage B - finished with result DONE' in out
    assert 'Skipping Stage 3: Stage C per user request.' in out
    assert 'Stage 3: Stage C - finished with result SKIPPED' in out
    assert 'Stage 4: Stage D - finished with result DONE' in out


def test_manual_skip_two_stage(cli, targets_config):
    """Verify manually skipping multiple stages works correctly."""
    res = cli.invoke(build_magic, ['-C', targets_config, '--skip', 'Stage A', '-s', 'Stage C'])
    out = res.output
    assert res.exit_code == ExitCode.PASSED
    assert 'Skipping Stage 1: Stage A per user request.' in out
    assert 'Stage 1: Stage A - finished with result SKIPPED' in out
    assert 'Stage 2: Stage B - finished with result DONE' in out
    assert 'Skipping Stage 3: Stage C per user request.' in out
    assert 'Stage 3: Stage C - finished with result SKIPPED' in out
    assert 'Stage 4: Stage D - finished with result DONE' in out


def test_manual_skip_fail(cli, targets_config):
    """Test the case where a stage to skip is not in the stages to run."""
    res = cli.invoke(build_magic, ['-C', targets_config, '--skip', 'Stage Z', '-s', 'Stage C'])
    out = res.output
    assert "Cannot skip stage Stage Z because it was not found in ['Stage A', 'Stage B', 'Stage C', 'Stage D']." in out


def test_manual_skip_fail_multiple_configs(cli, meta_config, targets_config):
    """Test the case where a stage to skip is not in the stages to run from multiple config files."""
    res = cli.invoke(build_magic, ['-C', targets_config, '-C', meta_config, '--skip', 'Stage Z'])
    out = res.output
    ref = "Cannot skip stage Stage Z because it was not found in ['Stage A', 'Stage B', 'Stage C', 'Stage D', 'Test']."
    assert ref in out


def test_export_gitlab(cli, config_file):
    """Verify exporting a config file to gitlab works correctly."""
    res = cli.invoke(build_magic, ['--export', config_file, 'gitlab'])
    out = res.output
    assert res.exit_code == ExitCode.PASSED
    assert out == """Test stage:
  stage: Test stage
  scripts:
    - echo hello
    - ls

"""


def test_export_github(cli, config_file):
    """Verify exporting a config file to github works correctly."""
    res = cli.invoke(build_magic, ['--export', config_file, 'github'])
    out = res.output
    assert res.exit_code == ExitCode.PASSED
    assert out == """jobs:
  Test stage:
    steps:
      - run: echo hello
      - run: ls

"""


def test_export_wrong_path(cli):
    """Test the case where a non-existent file is passed to --export."""
    res = cli.invoke(build_magic, ['--export', '/tmp/dummy', 'gitlab'])
    out = res.output
    assert res.exit_code == ExitCode.INPUT_ERROR
    assert out == "[Errno 2] No such file or directory: '/tmp/dummy'\n"


def test_export_bad_ci_type(cli, config_file):
    """Test the case where a bad ci type is provided to --export."""
    res = cli.invoke(build_magic, ['--export', config_file, 'dummy'])
    out = res.output
    assert res.exit_code == ExitCode.INPUT_ERROR
    assert out == "Export type must be one of ('github', 'gitlab')\n"


def test_export_path_is_directory(cli, magic_dir):
    """Test the case where the path provided to --export is a directory."""
    res = cli.invoke(build_magic, ['--export', magic_dir, 'gitlab'])
    out = res.output
    assert res.exit_code == ExitCode.INPUT_ERROR
    assert '[Errno 21] Is a directory' in out


def test_export_not_a_config_file(cli, dotenv_config):
    """Test the case where a file that isn't a config file is provided to --export."""
    file = dotenv_config / 'test.env'
    res = cli.invoke(build_magic, ['--export', file, 'gitlab'])
    out = res.output
    assert res.exit_code == ExitCode.INPUT_ERROR
    assert out == 'Cannot read config.\n'


def test_validate_config_file(cli, default_config):
    """Verify the --validate switch works correctly."""
    res = cli.invoke(build_magic, ['--validate', default_config])
    out = res.output
    assert res.exit_code == ExitCode.PASSED
    assert out == ''


def test_validate_config_file_fail(cli, invalid_config):
    """Test the case where a config file fails validation using the --validate switch."""
    ref = """Config validation failed: {'execute': 'echo "hello"'} is not of type 'array'

Failed validating 'type' in schema[0]['properties']['stage']['properties']['commands']
"""
    res = cli.invoke(build_magic, ['--validate', invalid_config])
    out = res.output
    assert res.exit_code == ExitCode.INPUT_ERROR
    assert out == ref
