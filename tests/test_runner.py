"""This module hosts unit tests for the CommandRunner sub classes."""

import os
from pathlib import Path
import socket
import subprocess
from unittest.mock import MagicMock

from docker.errors import ContainerError
import paramiko
import pytest
import vagrant

from build_magic.exc import HostWorkingDirectoryNotFound
from build_magic.macro import Macro
from build_magic.reference import BindDirectory, HostWorkingDirectory, KeyPassword, KeyPath, KeyType
from build_magic.runner import CommandRunner, Docker, Local, Remote, Status, Vagrant


valid_ssh = (
    ('dummy', None, 'dummy', 22),
    ('example.com', None, 'example.com', 22),
    ('test-site', None, 'test-site', 22),
    ('user@dummy', 'user', 'dummy', 22),
    ('dummy:12345', None, 'dummy', 12345),
    ('user@dummy:12345', 'user', 'dummy', 12345),
    ('fake-user@dummy', 'fake-user', 'dummy', 22),
    ('fake.user@dummy', 'fake.user', 'dummy', 22),
    ('fake_user@dummy', 'fake_user', 'dummy', 22),
    ('test_site', None, 'test_site', 22),
    ('user1234@dummy', 'user1234', 'dummy', 22),
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


@pytest.fixture
def ssh_path(tmp_path_factory):
    """Provides a temp directory with a sample SSH key."""
    magic = tmp_path_factory.mktemp('build_magic')
    key = magic / 'key_ecdsa'
    paramiko.ECDSAKey.generate().write_private_key_file(str(key))
    return magic


@pytest.fixture
def ssh_key_with_password(tmp_path_factory):
    """Provides a temp directory with a sample SSH key protected with passphrase."""
    magic = tmp_path_factory.mktemp('build_magic')
    key = magic / 'id_rsa'
    paramiko.RSAKey.generate(1024).write_private_key_file(str(key), password="1234")
    return magic


@pytest.fixture
def mock_key(mocker):
    """Provides a mock RSAKey object."""
    return mocker.patch('paramiko.RSAKey.from_private_key_file', return_value=paramiko.RSAKey.generate(512))


def test_status_representation():
    """Verify the __repr__ method works correctly."""
    status = Status(stdout='test', stderr='An error', exit_code=1)
    assert str(status) == '<stdout=test, stderr=An error, exit_code=1>'


def test_status_equal():
    """Verify the Status equality comparison works correctly."""
    status1 = Status(stdout='test', stderr='An error', exit_code=1)
    status2 = Status('test', 'An error', 1)
    status3 = Status(stdout='test')
    other = 42

    # Test equality.
    assert status1 == status2

    # Test inequality.
    assert status1 != status3

    # Test identity.
    assert status1 is not status2

    # Test incomparable
    with pytest.raises(TypeError):
        assert status1 == other


def test_status_less_than():
    """Verify the Status less than comparison works correctly."""
    status1 = Status(stdout='test')
    status2 = Status(stderr='An error.', exit_code=99)
    status3 = Status(stderr='Another error.', exit_code=99)
    other = 42

    assert status1 < status2
    assert not status2 < status3
    assert status2 <= status3

    with pytest.raises(TypeError):
        # noinspection PyTypeChecker
        assert status1 < other
    with pytest.raises(TypeError):
        # noinspection PyTypeChecker
        assert status1 <= other


def test_status_greater_than():
    """Verify the Status greater than comparison works correctly."""
    status1 = Status(stdout='test')
    status2 = Status(stderr='An error.', exit_code=99)
    status3 = Status(stderr='Another error.', exit_code=99)
    other = 42

    assert status2 > status1
    assert not status2 > status3
    assert status2 >= status3

    with pytest.raises(TypeError):
        # noinspection PyTypeChecker
        assert status1 > other
    with pytest.raises(TypeError):
        # noinspection PyTypeChecker
        assert status1 >= other


def test_base_runner():
    """Verify that the base CommanRunner object works correctly."""
    runner = CommandRunner('dummy')
    assert not runner.provision()
    assert not runner.teardown()
    with pytest.raises(NotImplementedError):
        runner.execute(Macro('dummy'))
    with pytest.raises(NotImplementedError):
        runner.prepare()


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


@pytest.mark.parametrize(
    'version', (
        b'Microsoft Windows 10 Enterprise',
        b'Microsoft Windows 8.1 Pro',
        b'Microsoft Windows 7 Ultimate',
        b'Microsoft Windows 11 Home Single Language',
        b'Microsoft Windows Server 2012 R2 Enterprise',
    )
)
def test_local_os_matches_environment_windows(local_runner, mocker, version):
    """Verify the Local command runner os_matches_environment() method works correctly for Windows."""
    mocker.patch(
        'subprocess.run',
        return_value=MagicMock(
            spec=subprocess.CompletedProcess,
            returncode=0,
            stdout=version,
        )
    )
    local_runner.environment = 'windows'
    assert local_runner.os_matches_environment()

    local_runner.environment = 'win'
    assert local_runner.os_matches_environment()


@pytest.mark.parametrize(
    'version', (
        b'Mac OS X',
        b'MacOS',
        b'macOS Server',
    )
)
def test_local_os_matches_environment_macos(local_runner, mocker, version):
    """Verify the Local command runner os_matches_environment() method works correctly for MacOS."""
    mocker.patch(
        'subprocess.run',
        return_value=MagicMock(
            spec=subprocess.CompletedProcess,
            returncode=0,
            stdout=version,
        )
    )
    local_runner.environment = 'macos'
    assert local_runner.os_matches_environment()

    local_runner.environment = 'darwin'
    assert local_runner.os_matches_environment()


@pytest.mark.parametrize(
    'version', (
        (b'ID=debian', 'debian'),
        (b'ID=ubuntu', 'Ubuntu'),
        (b'ID=centos', 'centos'),
        (b'ID=rhel', 'rhel'),
        (b'ID=fedora', 'fedora'),
        (b'ID=mint', 'mint'),
        (b'ID=suse', 'suse'),
        (b'ID=arch', 'arch'),
    ),
)
def test_local_os_matches_environment_linux(local_runner, mocker, version):
    """Verify the Local command runner os_matches_environment() method works correctly for Linux distros."""
    os_ver, env = version
    mocker.patch(
        'subprocess.run',
        return_value=MagicMock(
            spec=subprocess.CompletedProcess,
            returncode=0,
            stdout=os_ver,
        )
    )
    local_runner.environment = env
    assert local_runner.os_matches_environment()


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
        assert status.stderr == b'a hello.txt' + bytes(os.linesep, encoding='utf-8')


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
        assert status.stderr == (
            b'tar: dummy.txt: Cannot stat: No such file or directory\n'
            b'tar: Exiting with failure status due to previous errors\n'
        )
    elif os.sys.platform == 'win32':
        assert status.stderr == (
            b"tar: dummy.txt: Couldn't find file: No such file or directory\r\n"
            b'tar: Error exit delayed from previous errors.\r\n'
        )
    else:
        assert status.stderr == (
            b'tar: dummy.txt: Cannot stat: No such file or directory\n'
            b'tar: Error exit delayed from previous errors.\n'
        )


def test_local_envs(local_runner):
    """Verify envs passed to the Local runner are included in execute()."""
    envs = {
        'HELLO': 'world',
        'FOO': 'bar',
    }
    cmd = 'env'
    macro = Macro(cmd)
    local_runner.envs = envs
    status = local_runner.execute(macro)
    assert status.exit_code == 0
    for key, value in envs.items():
        assert f'{key}={value}' in str(status.stdout)
    assert len(status.stdout) > 20


def test_docker_constructor(mocker):
    """Verify the Docker command runner constructor works correctly."""
    mocker.patch('pathlib.Path.exists', return_value=True)
    runner = Docker()
    assert runner.environment == 'alpine'
    assert runner.working_directory == '/build_magic'
    assert not runner.copy_from_directory
    assert not runner.artifacts
    assert type(runner.artifacts) == list
    assert runner.timeout == 30
    assert runner.binding == {
        'ReadOnly': False,
        'Source': str(Path.cwd().resolve()),
        'Target': '/build_magic',
        'Type': 'bind',
    }
    assert not runner.container
    assert runner.name == 'docker'
    assert runner.host_wd == '.'
    assert runner.bind_path == '/build_magic'
    assert runner.envs == {}

    if os.sys.platform == 'win32':
        host_wd = 'C:\\my_repo'
    else:
        host_wd = '/my_repo'

    runner = Docker(
        environment='python:3',
        working_dir='/app',
        copy_dir='/other',
        timeout=10,
        artifacts=['hello.txt'],
        parameters={
            'hostwd': HostWorkingDirectory(host_wd),
            'bind': BindDirectory('/opt'),
        },
        envs={
            'HELLO': 'world',
            'FOO': 'bar',
        }
    )
    assert runner.environment == 'python:3'
    assert runner.working_directory == '/app'
    assert runner.copy_from_directory == '/other'
    assert runner.timeout == 10
    assert runner.artifacts == ['hello.txt']
    assert runner.host_wd == host_wd
    assert runner.bind_path == '/opt'
    assert runner.binding == {
        'ReadOnly': False,
        'Source': host_wd,
        'Target': '/opt',
        'Type': 'bind',
    }
    assert runner.envs == {
        'HELLO': 'world',
        'FOO': 'bar',
    }


def test_docker_host_wd_not_found(mocker):
    """Test the case where the host working directory isn't found."""
    mocker.patch('pathlib.Path.exists', return_value=False)
    with pytest.raises(HostWorkingDirectoryNotFound):
        assert Docker()


def test_docker_prepare(docker_runner, build_path, mocker, tmp_path):
    """Verify the Docker command runner prepare() method works correctly."""
    os.chdir(str(tmp_path))
    container = mocker.patch('docker.models.containers.Container')
    run = mocker.patch('docker.models.containers.Container.exec_run')
    docker_runner.container = container

    # Nothing to do.
    assert not docker_runner.prepare()
    assert len(list(Path.cwd().iterdir())) == 0

    # Set the copy_from_directory.
    docker_runner.copy_from_directory = str(build_path)
    assert not docker_runner.prepare()
    assert len(list(Path.cwd().iterdir())) == 0

    # Set at least one artifact.
    docker_runner.artifacts.append('hello.txt')
    assert not docker_runner.prepare()
    assert len(list(Path.cwd().iterdir())) == 0

    # Change the working directory to something other than the bind path.
    docker_runner.working_directory = '/app'
    assert docker_runner.prepare()
    assert len(list(Path.cwd().iterdir())) == 1
    assert run.call_count == 2

    # Prepare to copy but fail because of a container error.
    run.reset_mock()
    run.side_effect = ContainerError('test', 1, 'test', 'dummy', 'error')
    runner = Docker()
    runner.container = container
    runner.copy_from_directory = str(build_path)
    runner.working_directory = '/app'
    runner.artifacts.append('hello.txt')
    assert not runner.prepare()


def test_docker_execute(docker_runner, mocker):
    """Verify the Docker command runner execute() method works correctly."""
    ref = {
        'cmd': [
            '/bin/sh',
            '-c',
            'echo hello',
        ],
        'environment': {},
        'stdout': True,
        'stderr': True,
        'tty': True,
    }
    container = mocker.patch('docker.models.containers.Container')
    run = mocker.patch('docker.models.containers.Container.exec_run', return_value=(0, b'hello'))
    cmd = Macro('echo hello')
    docker_runner.container = container
    status = docker_runner.execute(cmd)
    assert run.call_count == 1
    call_args = run.mock_calls[0]
    assert call_args[2] == ref
    assert status.exit_code == 0
    assert status.stdout == 'hello'
    assert not status.stderr


def test_docker_command_fail(docker_runner, mocker):
    """Test the case where executing a command with the Docker runner fails."""
    cmd = Macro('hello')
    error = b'/bin/sh: hello: not found'
    container = mocker.patch('docker.models.containers.Container')
    mocker.patch('docker.models.containers.Container.exec_run', return_value=(127, error))
    docker_runner.container = container
    status = docker_runner.execute(cmd)
    assert status.exit_code == 127
    assert not status.stdout
    assert status.stderr == '/bin/sh: hello: not found'


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


def test_docker_envs(docker_runner, mocker):
    """Verify environment variables are executed by Docker's execute() method."""
    container = mocker.patch('docker.models.containers.Container')
    execute = mocker.patch('docker.models.containers.Container.exec_run', return_value=(0, b'blah'))

    envs = {
        'HELLO': 'world',
        'FOO': 'bar',
    }
    macro = Macro('env')
    docker_runner.container = container
    docker_runner.envs = envs
    docker_runner.execute(macro)
    assert execute.call_args[1].get('environment', {}) == envs


def test_vagrant_constructor(mocker):
    """Verify the Vagrant command runner constructor works correctly."""
    mocker.patch('pathlib.Path.exists', return_value=True)
    runner = Vagrant()
    assert runner.environment == '.'
    assert runner.working_directory == '/home/vagrant'
    assert not runner.copy_from_directory
    assert not runner.artifacts
    assert type(runner.artifacts) == list
    assert runner.timeout == 30
    assert not runner._vm
    assert runner.name == 'vagrant'
    assert runner.host_wd == '.'
    assert runner.bind_path == '/vagrant'
    assert runner.envs == {}

    if os.sys.platform == 'win32':
        host_wd = 'C:\\my_repo'
        env = 'C:\\opt'
    else:
        host_wd = '/my_repo'
        env = '/opt'

    runner = Vagrant(
        environment=env,
        working_dir='/test',
        copy_dir='/other',
        timeout=10,
        artifacts=['hello.txt'],
        parameters={
            'hostwd': HostWorkingDirectory(host_wd),
            'bind': BindDirectory('/app'),
        },
        envs={
            'HELLO': 'world',
            'FOO': 'bar',
        }
    )
    assert runner.environment == env
    assert runner.working_directory == '/test'
    assert runner.copy_from_directory == '/other'
    assert runner.timeout == 10
    assert runner.artifacts == ['hello.txt']
    assert runner.host_wd == host_wd
    assert runner.bind_path == '/app'
    assert os.environ.get('VAGRANT_CWD') == env
    assert runner.envs == {
        'HELLO': 'world',
        'FOO': 'bar',
    }

    os.environ.pop('VAGRANT_CWD', '')
    runner = Vagrant(
        environment='Vagrantfile',
    )
    assert not os.environ.get('VAGRANT_CWD')
    assert runner.environment == '.'

    runner = Vagrant(
        environment='/opt/Vagrantfile'
    )
    assert os.environ.get('VAGRANT_CWD') == env
    assert runner.environment == '/opt/'


def test_vagrant_host_wd_not_found(mocker):
    """Test the case where the host working directory isn't found."""
    mocker.patch('pathlib.Path.exists', return_value=False)
    with pytest.raises(HostWorkingDirectoryNotFound):
        assert Vagrant()


def test_vagrant_prepare(build_path, mocker, tmp_path, vagrant_runner):
    """Verify the Vagrant command runner prepare() method works correctly."""
    ssh = mocker.patch('vagrant.Vagrant.ssh')
    vm = vagrant.Vagrant()
    os.chdir(str(tmp_path))

    # Nothing to do.
    assert not vagrant_runner.prepare()
    assert len(list(Path.cwd().iterdir())) == 0

    # Set vm and copy_from_directory, but do nothing because there are no artifacts.
    vagrant_runner._vm = vm
    vagrant_runner.copy_from_directory = str(build_path)
    assert not vagrant_runner.prepare()
    assert len(list(Path.cwd().iterdir())) == 0
    assert ssh.call_count == 1

    ssh.reset_mock()

    # Copy to the working directory because there's at least one artifact.
    vagrant_runner.artifacts.append('hello.txt')
    assert vagrant_runner.prepare()
    assert len(list(Path.cwd().iterdir())) == 1
    assert ssh.call_count == 2

    # Do nothing because the working directory is also the bind path.
    vagrant_runner.working_directory = vagrant_runner.bind_path
    vagrant_runner.artifacts = []
    assert not vagrant_runner.prepare()

    ssh.reset_mock()
    ssh.side_effect = subprocess.CalledProcessError(1, 'test')

    # Prepare to copy but fail because SSH failed.
    runner = Vagrant()
    runner.copy_from_directory = str(build_path)
    runner.artifacts.append('hello.txt')
    runner._vm = vm
    assert not runner.prepare()


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


def test_vagrant_execute_not_found(mocker, vagrant_runner):
    """Test the case where the Vagrant exe cannot be found."""
    mocker.patch('vagrant.Vagrant.ssh', side_effect=RuntimeError)
    cmd = Macro('ls')
    vagrant_runner._vm = vagrant.Vagrant()
    with pytest.raises(RuntimeError):
        vagrant_runner.execute(cmd)


def test_vagrant_execute_working_directory(vagrant_runner):
    """Verify the Vagrant command runner execute() method works correctly with working directory."""
    cmd = Macro('tar -v -czf hello.tar.gz hello.txt')
    vm = MagicMock()
    vagrant_runner._vm = vm
    vagrant_runner.working_directory = '/app'
    status = vagrant_runner.execute(cmd)
    call_args = vm.mock_calls[0]
    assert call_args[2] == {'command': 'cd /app; tar -v -czf hello.tar.gz hello.txt'}
    assert status.stdout
    assert not status.stderr
    assert status.exit_code == 0


def test_remote_constructor(mock_key):
    """Verify the Remote command runner constructor works correctly."""
    runner = Remote()
    assert runner.environment == 'localhost'
    assert not runner.working_directory
    assert not runner.copy_from_directory
    assert runner.timeout == 30
    assert not runner.artifacts
    assert not runner.user
    assert runner.host == 'localhost'
    assert runner.port == 22
    assert runner.name == 'remote'
    assert isinstance(runner.key, paramiko.RSAKey)
    assert runner.envs == {}


def test_remote_constructor_valid_ssh(mock_key, valid_ssh_conn):
    """Validate Remote command runner SSH connections strings."""
    valid = valid_ssh_conn
    runner = Remote(environment=valid[0])
    assert runner.user == valid[1]
    assert runner.host == valid[2]
    assert runner.port == valid[3]


def test_remote_constructor_bad_ssh(bad_ssh_conn, mock_key):
    """Test the case where Remote command runner SSH connection strings are invalid."""
    bad = bad_ssh_conn
    runner = Remote(environment=bad[0])
    assert runner.user == bad[1]
    assert runner.host == bad[2]
    assert runner.port == bad[3]


def test_remote_with_parameters(ssh_path):
    """Verify the Remote command runner handles passed in parameters correctly."""
    ref = paramiko.ECDSAKey.from_private_key_file(f'{ssh_path}/key_ecdsa')
    params = {
        'keypath': KeyPath(f'{ssh_path}/key_ecdsa'),
        'keytype': KeyType('ecdsa'),
    }
    runner = Remote('user@myhost', parameters=params)
    assert isinstance(runner.key, paramiko.ECDSAKey)
    assert runner.key == ref


def test_remote_passphrase_key(ssh_key_with_password):
    """Verify the Remote command runner handles a password protected key."""
    params = {
        'keypath': KeyPath(f'{ssh_key_with_password}/id_rsa'),
        'keypass': KeyPassword('1234'),
    }
    runner = Remote('user@myhost', parameters=params)
    assert runner.key.can_sign()


def test_remote_passphrase_key_fail(ssh_key_with_password):
    """Test the case where an invalid private key password is provided."""
    params = {
        'keypath': KeyPath(f'{ssh_key_with_password}/id_rsa'),
        'keypass': KeyPassword('11111'),
    }
    with pytest.raises(ValueError):
        Remote('user@myhost', parameters=params)


def test_remote_key_file_not_found():
    """Test the case where the private key file doesn't exist."""
    params = {
        'keypath': KeyPath('/zztle3aw399cx/id_rsa'),
    }
    with pytest.raises(ValueError):
        Remote('user@myhost', parameters=params)


def test_remote_prepare(build_path, mock_key, mocker, tmp_path, remote_runner):
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
    assert 'hello.txt' in put.call_args[0][0][0]


def test_remote_execute(mock_key, mocker, remote_runner):
    """Verify the Remote command runner execute() method works correctly."""
    conn = mocker.patch('build_magic.runner.Remote.connect', return_value=paramiko.SSHClient)
    exek = mocker.patch(
        'paramiko.SSHClient.exec_command',
        return_value=(
            None,
            MagicMock(readlines=lambda: 'hello', channel=MagicMock(recv_exit_status=lambda: 0)),
            MagicMock(readlines=lambda: '')
        )
    )
    close = mocker.patch('paramiko.SSHClient.close')
    cmd = Macro('echo hello')
    status = remote_runner.execute(cmd)
    assert exek.call_args[0][0] == 'echo hello'
    assert exek.call_args[1] == {'environment': {}, 'get_pty': True, 'timeout': 30}
    assert conn.call_count == 1
    assert exek.call_count == 1
    assert close.call_count == 1
    assert not status.stderr
    assert status.stdout == 'hello'
    assert status.exit_code == 0


def test_remote_execute_timeout(mock_key, mocker, remote_runner):
    """Test the case the Remote command runner execute() method raises a Timeout error."""
    conn = mocker.patch('build_magic.runner.Remote.connect', return_value=paramiko.SSHClient)
    close = mocker.patch('paramiko.SSHClient.close')
    mocker.patch('paramiko.SSHClient.exec_command', side_effect=socket.timeout)
    cmd = Macro('echo hello')
    with pytest.raises(TimeoutError):
        remote_runner.execute(cmd)
    assert conn.call_count == 1
    assert close.call_count == 1


def test_remote_connection_fail(mock_key, mocker, remote_runner):
    """Test the case where the Remote command runner fails to connect."""
    mocker.patch('paramiko.SSHClient.connect', side_effect=socket.gaierror)
    cmd = Macro('echo hello')
    with pytest.raises(Exception, match='SSH connection failed.'):
        remote_runner.execute(cmd)


def test_remote_execute_fail(mock_key, mocker, remote_runner):
    """Test the case where the Remote execute() method fails."""
    conn = mocker.patch('build_magic.runner.Remote.connect', return_value=paramiko.SSHClient)
    exek = mocker.patch(
        'paramiko.SSHClient.exec_command',
        return_value=(
            None,
            MagicMock(readlines=lambda: '', channel=MagicMock(recv_exit_status=lambda: 1)),
            MagicMock(readlines=lambda: 'An error message')
        )
    )
    close = mocker.patch('paramiko.SSHClient.close')
    cmd = Macro('cp')
    status = remote_runner.execute(cmd)
    assert exek.call_args[0][0] == 'cp'
    assert exek.call_args[1] == {'environment': {}, 'get_pty': True, 'timeout': 30}
    assert conn.call_count == 1
    assert exek.call_count == 1
    assert close.call_count == 1
    assert status.stderr == 'An error message'
    assert status.stdout == ''
    assert status.exit_code == 1


def test_copy_to_working_directory(tmp_path_factory, local_runner):
    """Verify the file copy behavior works correctly when calling the runner's copy() method."""
    dir1 = tmp_path_factory.mktemp('dir1')
    dir2 = tmp_path_factory.mktemp('dir2')
    main = dir1 / 'main.cpp'
    audio = dir1 / 'audio.cpp'
    plugins = dir1 / 'plugins.cpp'
    main.touch()
    audio.touch()
    plugins.touch()

    local_runner.copy_from_directory = dir1
    local_runner.working_directory = dir2
    local_runner.artifacts = ['main.cpp', 'audio.cpp', 'plugins.cpp']
    assert local_runner.prepare()
    assert dir2.joinpath('main.cpp').exists()
    assert dir2.joinpath('audio.cpp').exists()
    assert dir2.joinpath('plugins.cpp').exists()


def test_copy_to_working_directory_fail(tmp_path_factory, local_runner):
    """Test the case where not all files are copied from the copy directory because they don't exist."""
    dir1 = tmp_path_factory.mktemp('dir1')
    dir2 = tmp_path_factory.mktemp('dir2')
    main = dir1 / 'main.cpp'
    main.touch()

    local_runner.copy_from_directory = dir1
    local_runner.working_directory = dir2
    local_runner.artifacts = ['main.cpp', 'audio.cpp', 'plugins.cpp']
    assert local_runner.prepare()
    assert dir2.joinpath('main.cpp').exists()
    assert not dir2.joinpath('audio.cpp').exists()
    assert not dir2.joinpath('plugins.cpp').exists()
