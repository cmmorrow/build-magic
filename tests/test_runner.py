"""This module hosts unit tests for the CommandRunner sub classes."""

import os
from pathlib import Path
import subprocess
from unittest.mock import MagicMock

from docker.errors import ContainerError
import paramiko
import pytest

from build_magic.macro import Macro
from build_magic.runner import Docker, Local, Remote, Vagrant


valid_ssh = (
    ('dummy', None, 'dummy', None),
    ('example.com', None, 'example.com', None),
    ('test-site', None, 'test-site', None),
    ('user@dummy', 'user', 'dummy', None),
    ('dummy:12345', None, 'dummy', 12345),
    ('user@dummy:12345', 'user', 'dummy', 12345),
    ('fake-user@dummy', 'fake-user', 'dummy', None),
    ('fake.user@dummy', 'fake.user', 'dummy', None),
    ('fake_user@dummy', 'fake_user', 'dummy', None),
    ('test_site', None, 'test_site', None),
    ('user1234@dummy', 'user1234', 'dummy', None),
    ('user1234@dummy:123', 'user1234', 'dummy', 123),
    ('a@a:12', 'a', 'a', 12),
)

bad_ssh = (
    ('$$%', None, None, None),
    ('example:1', None, None, None),
    ('example:111111', None, None, None),
    ('f@ke-user@dummy', None, None, None),
    ('fak:user@dummy', None, None, None),
    ('fak:user@dummy:1234', None, None, None),
    ('fake user@dummy', None, None, None),
    ('user@:1234', None, None, None),
    ('@dummy:1234', None, None, None),
    ('@a', None, None, None),
)


@pytest.fixture(params=valid_ssh)
def valid_ssh_conn(request):
    """Provides valid SSH connection strings."""
    yield request.param


@pytest.fixture(params=bad_ssh)
def bad_ssh_conn(request):
    """Provides bad SSH connection strings."""
    yield request.param


@pytest.fixture
def local_runner():
    """Provides a Local command runner object."""
    return Local()


@pytest.fixture
def docker_runner():
    """Provides a Docker command runner object."""
    return Docker()


@pytest.fixture
def vagrant_runner():
    """Provides a Vagrant command runner object."""
    return Vagrant()


@pytest.fixture
def remote_runner():
    """Provides a Remote command runner object."""
    return Remote()


@pytest.fixture(scope='session')
def build_path(tmp_path_factory):
    """Provides a temp directory with a single file in it."""
    magic = tmp_path_factory.mktemp('build_magic')
    hello = magic / 'hello.txt'
    hello.write_text('hello')
    return magic


def test_local_constructor():
    """Verify the Local command runner constructor works correctly."""
    runner = Local()
    assert not runner.environment
    assert not runner.working_directory
    assert not runner.copy_from_directory
    assert not runner.artifacts
    assert type(runner.artifacts) == list
    assert runner.timeout == 30
    assert runner.name == 'local'

    runner = Local(environment='dummy', working_dir='/test', copy_dir='/other', timeout=10, artifacts=['hello.txt'])
    assert runner.environment == 'dummy'
    assert runner.working_directory == '/test'
    assert runner.copy_from_directory == '/other'
    assert runner.artifacts == ['hello.txt']
    assert runner.timeout == 10


def test_local_prepare(build_path, local_runner, tmp_path):
    """Verify the Local command runner prepare() method works correctly."""
    if os.sys.platform == 'linux':
        assert str(Path.cwd().stem) == 'build-magic'
    else:
        assert str(Path.cwd().stem) == 'tests'
    local_runner.working_directory = str(tmp_path)
    local_runner.prepare()
    assert 'test_local_prepare' in str(Path.cwd().stem)

    assert len(list(Path.cwd().iterdir())) == 0
    local_runner.copy_from_directory = str(build_path)
    local_runner.prepare()
    assert len(list(Path.cwd().iterdir())) == 0

    local_runner.artifacts.append('hello.txt')
    local_runner.prepare()
    assert len(list(Path.cwd().iterdir())) == 1


def test_local_execute(build_path, local_runner, tmp_path):
    """Verify the Local command runner execute() method works correctly."""
    cmd = Macro('tar -v -czf hello.tar.gz hello.txt')
    local_runner.working_directory = str(tmp_path)
    local_runner.copy_from_directory = str(build_path)
    local_runner.artifacts.append('hello.txt')
    local_runner.prepare()
    status = local_runner.execute(cmd)
    assert status.exit_code == 0
    if os.sys.platform == 'linux':
        assert status.stdout == b'hello.txt\n'
        assert status.stderr == b''
    else:
        assert status.stdout == b''
        assert status.stderr == b'a hello.txt\n'


def test_local_execute_fail(local_runner, tmp_path):
    """Test the case where a Local execute() command fails."""
    cmd = Macro('tar -v -czf hello.tar.gz dummy.txt')
    local_runner.prepare()
    status = local_runner.execute(cmd)
    if os.sys.platform == 'linux':
        assert status.exit_code == 2
    else:
        assert status.exit_code == 1
    assert status.stdout == b''
    if os.sys.platform == 'linux':
        assert status.stderr == b'tar: dummy.txt: Cannot stat: No such file or directory\n' \
                                b'tar: Exiting with failure status due to previous errors\n'
    else:
        assert status.stderr == b'tar: dummy.txt: Cannot stat: No such file or directory\n' \
                                b'tar: Error exit delayed from previous errors.\n'


def test_docker_constructor():
    """Verify the Docker command runner constructor works correctly."""
    runner = Docker()
    assert runner.environment == 'alpine'
    assert runner.working_directory == '.'
    assert not runner.copy_from_directory
    assert not runner.artifacts
    assert type(runner.artifacts) == list
    assert runner.timeout == 30
    assert runner.binding == {'.': {'bind': '/build_magic', 'mode': 'rw'}}
    assert not runner.container
    assert runner.name == 'docker'

    runner = Docker(environment='python:3', working_dir='/test', copy_dir='/other', timeout=10, artifacts=['hello.txt'])
    assert runner.environment == 'python:3'
    assert runner.working_directory == '/test'
    assert runner.copy_from_directory == '/other'
    assert runner.timeout == 10
    assert runner.artifacts == ['hello.txt']


def test_docker_prepare(docker_runner, build_path, tmp_path):
    """Verify the Docker command runner prepare() method works correctly."""
    # assert str(Path.cwd().stem) == 'tests'
    os.chdir(str(tmp_path))
    assert not docker_runner.prepare()

    assert len(list(Path.cwd().iterdir())) == 0
    docker_runner.copy_from_directory = str(build_path)
    docker_runner.prepare()
    assert len(list(Path.cwd().iterdir())) == 0

    docker_runner.artifacts.append('hello.txt')
    docker_runner.prepare()
    assert len(list(Path.cwd().iterdir())) == 1


def test_docker_execute(docker_runner, mocker):
    """Verify the Docker command runner execute() method works correctly."""
    ref = {
        'cmd': [
            'echo',
            'hello',
        ],
        'stdout': True,
        'stderr': True,
        'tty': True,
        'demux': True,
    }
    container = mocker.patch('docker.models.containers.Container')
    run = mocker.patch('docker.models.containers.Container.exec_run', return_value=(0, ('hello', None)))
    cmd = Macro('echo hello')
    docker_runner.container = container
    status = docker_runner.execute(cmd)
    assert run.call_count == 1
    call_args = run.mock_calls[0]
    assert call_args[2] == ref
    assert status.exit_code == 0
    assert status.stdout == 'hello'
    assert not status.stderr


def test_docker_execute_fail(docker_runner, mocker):
    """Test the case where a Docker execute() method fails."""
    cmd = Macro('cat')
    errors = (
        ContainerError('test', 1, cmd.as_string(), 'alpine', ''),
    )
    container = mocker.patch('docker.models.containers.Container')
    mocker.patch('docker.models.containers.Container.exec_run', side_effect=errors)
    docker_runner.container = container
    status = docker_runner.execute(cmd)
    assert status.exit_code == 1
    assert not status.stdout
    assert status.stderr == "Command 'cat' in image 'alpine' returned non-zero exit status 1: "


def test_vagrant_constructor():
    """Verify the Vagrant command runner constructor works correctly."""
    runner = Vagrant()
    assert runner.environment == '.'
    assert runner.working_directory == '.'
    assert not runner.copy_from_directory
    assert not runner.artifacts
    assert type(runner.artifacts) == list
    assert runner.timeout == 30
    assert not runner._vm
    assert runner.name == 'vagrant'

    runner = Vagrant(environment='/opt', working_dir='/test', copy_dir='/other', timeout=10, artifacts=['hello.txt'])
    assert runner.environment == '/opt'
    assert runner.working_directory == '/test'
    assert runner.copy_from_directory == '/other'
    assert runner.timeout == 10
    assert runner.artifacts == ['hello.txt']


def test_vagrant_prepare(build_path, tmp_path, vagrant_runner):
    """Verify the Vagrant command runner prepare() method works correctly."""
    # assert str(Path.cwd().stem) == 'tests'
    os.chdir(str(tmp_path))
    assert not vagrant_runner.prepare()

    assert len(list(Path.cwd().iterdir())) == 0
    vagrant_runner.copy_from_directory = str(build_path)
    vagrant_runner.prepare()
    assert len(list(Path.cwd().iterdir())) == 0

    vagrant_runner.artifacts.append('hello.txt')
    vagrant_runner.prepare()
    assert len(list(Path.cwd().iterdir())) == 1


def test_vagrant_execute(vagrant_runner):
    """Verify the Vagrant command runner execute() method works correctly."""
    cmd = Macro('tar -v -czf hello.tar.gz hello.txt')
    vm = MagicMock()
    vagrant_runner._vm = vm
    status = vagrant_runner.execute(cmd)
    call_args = vm.mock_calls[0]
    assert call_args[2] == {'command': 'tar -v -czf hello.tar.gz hello.txt'}
    assert status.stdout
    assert not status.stderr
    assert status.exit_code == 0


def test_vagrant_execute_fail(vagrant_runner):
    """Test the case where a Vagrant execute() method fails."""
    command = 'cat'
    cmd = Macro(command)

    # The case where _vm is None.
    with pytest.raises(AttributeError):
        vagrant_runner.execute(cmd)

    # The case where a CalledProcessError is raised.
    vm = MagicMock()
    vm.ssh.side_effect = subprocess.CalledProcessError(100, command)
    vagrant_runner._vm = vm
    status = vagrant_runner.execute(cmd)
    assert status.exit_code == 1
    assert not status.stdout
    assert status.stderr == f"Command '{command}' returned non-zero exit status 100."


def test_remote_constructor():
    """Verify the Remote command runner constructor works correctly."""
    runner = Remote()
    assert runner.environment == 'localhost'
    assert not runner.working_directory
    assert not runner.copy_from_directory
    assert runner.timeout == 30
    assert not runner.artifacts
    assert not runner.user
    assert runner.host == 'localhost'
    assert not runner.port
    assert runner.name == 'remote'


def test_remote_constructor_valid_ssh(valid_ssh_conn):
    """Validate Remote command runner SSH connections strings."""
    valid = valid_ssh_conn
    runner = Remote(environment=valid[0])
    assert runner.user == valid[1]
    assert runner.host == valid[2]
    assert runner.port == valid[3]


def test_remote_constructor_bad_ssh(bad_ssh_conn):
    """Test the case where Remote command runner SSH connection strings are invalid."""
    bad = bad_ssh_conn
    runner = Remote(environment=bad[0])
    assert runner.user == bad[1]
    assert runner.host == bad[2]
    assert runner.port == bad[3]


def test_remote_prepare(build_path, mocker, tmp_path, remote_runner):
    """Verify the Remote command runner prepare() method works correctly."""
    mocker.patch('paramiko.SSHClient', spec=paramiko.SSHClient)
    put = mocker.patch('scp.SCPClient.put', return_value=None)
    os.chdir(str(tmp_path))
    assert not remote_runner.prepare()

    assert len(list(Path.cwd().iterdir())) == 0
    remote_runner.copy_from_directory = str(build_path)
    assert not remote_runner.prepare()
    assert len(list(Path.cwd().iterdir())) == 0

    remote_runner.artifacts.append('hello.txt')
    assert remote_runner.prepare()
    assert put.call_count == 1
    assert 'hello.txt' in put.call_args[0][0]


# TODO: Add test for Remote execute.
