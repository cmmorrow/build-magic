"""This module hosts unit tests for the actions module."""

import hashlib
import os
from pathlib import Path
import subprocess
import types
from unittest.mock import MagicMock

import docker
from docker.errors import APIError, ImageLoadError
import paramiko
import pytest
import vagrant

from build_magic import actions
from build_magic.macro import Macro
from build_magic.runner import CommandRunner


@pytest.fixture
def build_path(tmp_path_factory):
    """Provides a temp directory with various files in it."""
    magic = tmp_path_factory.mktemp('build_magic')
    file1 = magic / 'file1.txt'
    file2 = magic / 'file2.txt'
    file1.write_text('hello')
    file2.write_text('world')
    return magic


@pytest.fixture
def empty_path(tmp_path_factory):
    """Provides a temp directory with no files in it."""
    return tmp_path_factory.mktemp('empty_dir')


@pytest.fixture
def build_hashes():
    """Provides the hashes for files in build_path."""
    return (
        '7c211433f02071597741e6ff5a8ea34789abbf43',
        'aaf4c61ddcc5e8a2dabede0f3b482cd9aea9434d',
    )


@pytest.fixture
def generic_runner():
    """Provides a generic command runner class for attaching action functions."""
    class GenericRunner(CommandRunner):

        def execute(self, macro):
            command = macro.as_list()
            result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            return result.stdout, result.stderr, result.returncode

        def prepare(self):
            return

    return GenericRunner('dummy')


def test_default_action():
    """Verify there isn't any regression in the default action."""
    ref = {
        'provision': {
            'local': 'null',
            'remote': 'null',
            'docker': 'container_up',
            'vagrant': 'vm_up',
        },
        'teardown': {
            'local': 'null',
            'remote': 'null',
            'docker': 'container_destroy',
            'vagrant': 'vm_destroy',
        }
    }
    assert hasattr(actions.Default, 'mapping')
    assert actions.Default.mapping == ref


def test_cleanup_action():
    """Verify there isn't any regression in the cleanup action."""
    ref = {
        'provision': {
            'local': 'capture_dir',
            'remote': 'remote_capture_dir',
            'docker': 'capture_dir',
            'vagrant': 'vm_up',
        },
        'teardown': {
            'local': 'delete_new_files',
            'remote': 'remote_delete_files',
            'docker': 'delete_new_files',
            'vagrant': 'vm_destroy',
        }
    }
    assert hasattr(actions.Cleanup, 'mapping')
    assert actions.Cleanup.mapping == ref


def test_persist_action():
    """Verify there isn't any regression in the persist action."""
    ref = {
        'provision': {
            'local': 'null',
            'remote': 'null',
            'docker': 'container_up',
            'vagrant': 'vm_up',
        },
        'teardown': {
            'local': 'null',
            'remote': 'null',
            'docker': 'null',
            'vagrant': 'null',
        }
    }

    assert hasattr(actions.Persist, 'mapping')
    assert actions.Persist.mapping == ref


def test_action_null(generic_runner):
    """Verify the null() function works correctly."""
    generic_runner.provision = types.MethodType(actions.null, generic_runner)
    assert generic_runner.provision()

    generic_runner.teardown = types.MethodType(actions.null, generic_runner)
    assert generic_runner.teardown()


def test_action_vm_up(generic_runner, mocker):
    """Verify the vm_up() function works correctly."""
    up = mocker.patch('vagrant.Vagrant.up')
    generic_runner.provision = types.MethodType(actions.vm_up, generic_runner)
    assert generic_runner.provision()
    assert up.call_count == 1
    assert os.environ.get('VAGRANT_CWD')
    assert os.environ['VAGRANT_CWD'] == 'dummy'  # Environment set in generic_runner constructor.

    generic_runner.environment = 'Vagrantfile'
    assert generic_runner.environment == 'Vagrantfile'
    assert generic_runner.provision()
    assert generic_runner.environment == '.'


def test_action_vm_up_error(capsys, generic_runner, mocker):
    """Test the case where vm_up() encounters a subprocess error."""
    mocker.patch('vagrant.Vagrant.up', side_effect=subprocess.CalledProcessError(1, 'error'))
    generic_runner.provision = types.MethodType(actions.vm_up, generic_runner)
    assert not generic_runner.provision()
    captured = capsys.readouterr()
    assert captured.out == "Command 'error' returned non-zero exit status 1.\n"


def test_action_vm_destroy(generic_runner, mocker):
    """Verify the vm_destroy() function works correctly."""
    destroy = mocker.patch('vagrant.Vagrant.destroy')
    generic_runner.teardown = types.MethodType(actions.vm_destroy, generic_runner)
    assert generic_runner.teardown()
    assert destroy.call_count == 0

    generic_runner._vm = vagrant.Vagrant()
    assert generic_runner.teardown()
    assert destroy.call_count == 1


def test_action_vm_destroy_error(generic_runner, mocker):
    """Test the case where vm_destroy() encounters a subprocess error."""
    mocker.patch('vagrant.Vagrant.destroy', side_effect=subprocess.CalledProcessError(1, 'error'))
    generic_runner.teardown = types.MethodType(actions.vm_destroy, generic_runner)
    generic_runner._vm = vagrant.Vagrant()
    assert not generic_runner.teardown()


def test_action_container_up(generic_runner, mocker):
    """Verify the container_up() function works correctly."""
    mocker.patch('docker.client.DockerClient.containers', new_callable=mocker.PropertyMock)
    run = mocker.patch('docker.client.DockerClient.containers.run')
    ref = {
        'detach': True,
        'tty': True,
        'entrypoint': 'sh',
        'working_dir': '/build_magic',
        'volumes': {
            'dir': {
                'bind': '/app',
                'mode': 'rw',
            }
        },
        'name': 'build-magic',
    }
    generic_runner.binding = {
        'dir': {
            'bind': '/app',
            'mode': 'rw',
        }
    }
    generic_runner.provision = types.MethodType(actions.container_up, generic_runner)
    assert generic_runner.provision()
    assert run.call_count == 1
    assert run.call_args[0] == ('dummy',)
    assert run.call_args[1] == ref


def test_action_container_up_error(generic_runner, mocker):
    """Test the case where an error is raised when starting the container."""
    mocker.patch('docker.client.DockerClient.containers', new_callable=mocker.PropertyMock)
    mocker.patch(
        'docker.client.DockerClient.containers.run',
        side_effect=(APIError('error'), ImageLoadError, AttributeError),
    )
    generic_runner.binding = {
        'dir': {
            'bind': '/app',
            'mode': 'rw',
        }
    }
    generic_runner.provision = types.MethodType(actions.container_up, generic_runner)
    assert not generic_runner.provision()
    assert not generic_runner.provision()
    assert not generic_runner.provision()


def test_action_container_destroy(generic_runner):
    """Verify the container_destroy() function works correctly."""
    generic_runner.container = MagicMock(spec=docker.client.APIClient, remove=lambda: None)
    generic_runner.teardown = types.MethodType(actions.container_destroy, generic_runner)
    assert generic_runner.teardown()


def test_action_container_destroy_error(generic_runner):
    """Test the case where container_destroy() raises an error."""
    generic_runner.container = None
    generic_runner.teardown = types.MethodType(actions.container_destroy, generic_runner)
    assert not generic_runner.teardown()


def test_action_capture_dir(build_hashes, build_path, generic_runner):
    """Verify the capture_dir() function works correctly."""
    os.chdir(str(build_path))
    generic_runner.provision = types.MethodType(actions.capture_dir, generic_runner)
    files = [str(file) for file in Path.cwd().resolve().iterdir()]
    ref = []
    for file in files:
        ref.append((file, hashlib.sha1(Path(file).read_bytes()).hexdigest()))
    assert generic_runner.provision()
    print(sorted(ref))
    print(sorted(generic_runner._existing_files))
    assert sorted(generic_runner._existing_files) == sorted(ref)


def test_action_capture_dir_empty(empty_path, generic_runner):
    """Verify the capture_dir() function works with an empty directory."""
    os.chdir(str(empty_path))
    generic_runner.provision = types.MethodType(actions.capture_dir, generic_runner)
    assert generic_runner.provision()
    assert hasattr(generic_runner, '_existing_files')
    assert len(generic_runner._existing_files) == 0


def test_action_capture_dir_error(build_path, generic_runner, mocker):
    """Test the case where capture_dir() raises an error."""
    os.chdir(str(build_path))
    mocker.patch('pathlib.Path.cwd', side_effect=IsADirectoryError)
    generic_runner.provision = types.MethodType(actions.capture_dir, generic_runner)
    assert not generic_runner.provision()


def test_action_delete_new_files(build_hashes, build_path, generic_runner):
    """Verify the delete_new_files() function works correctly."""
    os.chdir(str(build_path))
    generic_runner.teardown = types.MethodType(actions.delete_new_files, generic_runner)
    files = [str(file) for file in Path.cwd().resolve().iterdir()]
    generic_runner._existing_files = list(zip(files, build_hashes))
    generic_runner.execute(Macro('tar -czf myfiles.tar.gz file1.txt file2.txt'))
    assert generic_runner.teardown()
    assert sorted([str(file) for file in Path.cwd().resolve().iterdir()]) == sorted(files)


def test_action_delete_new_files_copy(build_hashes, build_path, generic_runner):
    """Verify the delete_new_files() function works correctly with copies of existing files."""
    os.chdir(str(build_path))
    generic_runner.teardown = types.MethodType(actions.delete_new_files, generic_runner)
    files = [str(file) for file in Path.cwd().resolve().iterdir()]
    generic_runner._existing_files = list(zip(files, build_hashes))
    generic_runner.execute(Macro('cp file2.txt temp.txt'))
    assert generic_runner.teardown()
    assert sorted([str(file) for file in Path.cwd().resolve().iterdir()]) == sorted(files)


def test_action_delete_new_files_preserve_renamed_file(build_hashes, build_path, generic_runner):
    """Verify that a renamed file isn't deleted by delete_new_files()."""
    os.chdir(str(build_path))
    generic_runner.teardown = types.MethodType(actions.delete_new_files, generic_runner)
    files = [str(file) for file in Path.cwd().resolve().iterdir()]
    generic_runner._existing_files = list(zip(files, build_hashes))
    generic_runner.execute(Macro('mv file2.txt temp.txt'))
    ref_files = [str(file) for file in Path.cwd().resolve().iterdir()]
    assert generic_runner.teardown()
    assert sorted([str(file) for file in Path.cwd().resolve().iterdir()]) == sorted(ref_files)


def test_action_delete_new_files_preserve_modified_file(build_hashes, build_path, generic_runner):
    """Verify that a modified file isn't deleted by delete_new_files()."""
    os.chdir(str(build_path))
    generic_runner.teardown = types.MethodType(actions.delete_new_files, generic_runner)
    files = [str(file) for file in Path.cwd().resolve().iterdir()]
    generic_runner._existing_files = list(zip(files, build_hashes))
    generic_runner.execute(Macro('mv file1.txt file2.txt'))
    ref_files = [str(file) for file in Path.cwd().resolve().iterdir()]
    assert generic_runner.teardown()
    assert sorted([str(file) for file in Path.cwd().resolve().iterdir()]) == sorted(ref_files)


def test_action_delete_new_files_empty_directory(empty_path, generic_runner):
    """Verify the delete_new_files() function works correctly with an empty directory."""
    os.chdir(str(empty_path))
    generic_runner.teardown = types.MethodType(actions.delete_new_files, generic_runner)
    generic_runner._existing_files = [str(file) for file in Path.cwd().resolve().iterdir()]
    assert len(generic_runner._existing_files) == 0
    generic_runner.execute(Macro('echo hello'))
    assert generic_runner.teardown()
    assert len([str(file) for file in Path.cwd().resolve().iterdir()]) == 0


def test_action_delete_new_files_no_existing(generic_runner):
    """Test the case where the _existing_files attribute isn't set."""
    generic_runner.teardown = types.MethodType(actions.delete_new_files, generic_runner)
    assert not generic_runner.teardown()

    generic_runner._existing_files = None
    assert not generic_runner.teardown()


def test_action_remote_capture_dir(generic_runner, mocker):
    """Verify the remote_capture_dir() function works correctly."""
    exek = mocker.patch(
        'paramiko.SSHClient.exec_command',
        side_effect=(
            (
                None,
                MagicMock(
                    readlines=lambda: ['Linux'],
                    channel=MagicMock(recv_exit_status=lambda: 0),
                ),
                MagicMock(readlines=lambda: ['']),
            ),
            (
                None,
                MagicMock(
                    readlines=lambda: [
                        '7c211433f02071597741e6ff5a8ea34789abbf43  /build-magic/file1.txt',
                        'aaf4c61ddcc5e8a2dabede0f3b482cd9aea9434d  /build-magic/file2.txt',
                    ],
                    channel=MagicMock(recv_exit_status=lambda: 0),
                ),
                MagicMock(readlines=lambda: ['']),
            ),
        ),
    )
    mocker.patch('paramiko.SSHClient.close')
    generic_runner.connect = types.MethodType(lambda _: paramiko.SSHClient(), generic_runner)
    generic_runner.provision = types.MethodType(actions.remote_capture_dir, generic_runner)
    assert generic_runner.provision()
    assert exek.call_count == 2
    assert exek.call_args[0] == ('find $PWD -type f | xargs shasum $PWD/*',)
    assert generic_runner._existing_files == [
        ('/build-magic/file1.txt', '7c211433f02071597741e6ff5a8ea34789abbf43'),
        ('/build-magic/file2.txt', 'aaf4c61ddcc5e8a2dabede0f3b482cd9aea9434d'),
    ]


def test_action_remote_capture_dir_with_working_directory(generic_runner, mocker):
    """Verify the the remote_capture_dir() function works correctly with a working directory set."""
    exek = mocker.patch(
        'paramiko.SSHClient.exec_command',
        side_effect=(
            (
                None,
                MagicMock(
                    readlines=lambda: ['Linux'],
                    channel=MagicMock(recv_exit_status=lambda: 0),
                ),
                MagicMock(readlines=lambda: ['']),
            ),
            (
                None,
                MagicMock(
                    readlines=lambda: [
                        '7c211433f02071597741e6ff5a8ea34789abbf43  /my/working/directory/file1.txt',
                        'aaf4c61ddcc5e8a2dabede0f3b482cd9aea9434d  /my/working/directory/file2.txt',
                    ],
                    channel=MagicMock(recv_exit_status=lambda: 0),
                ),
                MagicMock(readlines=lambda: ['']),
            ),
        ),
    )
    mocker.patch('paramiko.SSHClient.close')
    generic_runner.connect = types.MethodType(lambda _: paramiko.SSHClient(), generic_runner)
    generic_runner.provision = types.MethodType(actions.remote_capture_dir, generic_runner)
    generic_runner.working_directory = '/my/working/directory'
    assert generic_runner.provision()
    assert exek.call_count == 2
    assert exek.call_args[0] == ('find /my/working/directory -type f | xargs shasum /my/working/directory/*',)
    assert generic_runner._existing_files == [
        ('/my/working/directory/file1.txt', '7c211433f02071597741e6ff5a8ea34789abbf43'),
        ('/my/working/directory/file2.txt', 'aaf4c61ddcc5e8a2dabede0f3b482cd9aea9434d'),
    ]


def test_action_remote_capture_dir_no_shasum(generic_runner, mocker):
    """Verify the remote_capture_dir() function works correctly when the shasum command fails."""
    exek = mocker.patch(
        'paramiko.SSHClient.exec_command',
        side_effect=(
            (
                None,
                MagicMock(
                    readlines=lambda: ['Linux'],
                    channel=MagicMock(recv_exit_status=lambda: 0),
                ),
                MagicMock(readlines=lambda: ['']),
            ),
            (
                None,
                MagicMock(
                    readlines=lambda: [''],
                    channel=MagicMock(recv_exit_status=lambda: 1),
                ),
                MagicMock(
                    readlines=lambda: ['Command not found'],
                )
            ),
            (
                None,
                MagicMock(
                    readlines=lambda: [
                        '/build-magic/file1.txt',
                        '/build-magic/file2.txt',
                    ],
                    channel=MagicMock(recv_exit_status=lambda: 0),
                ),
                MagicMock(readlines=lambda: ['']),
            ),
        ),
    )
    mocker.patch('paramiko.SSHClient.close')
    generic_runner.connect = types.MethodType(lambda _: paramiko.SSHClient(), generic_runner)
    generic_runner.provision = types.MethodType(actions.remote_capture_dir, generic_runner)
    assert generic_runner.provision()
    assert exek.call_count == 3
    assert exek.call_args[0] == ('find $PWD -type f',)
    assert generic_runner._existing_files == [
        ('/build-magic/file1.txt', None),
        ('/build-magic/file2.txt', None),
    ]


def test_action_remote_capture_dir_windows_uname(generic_runner, mocker):
    """Verify the remote_capture_dir() function works correctly on windows."""
    exek = mocker.patch(
        'paramiko.SSHClient.exec_command',
        side_effect=(
            (
                None,
                MagicMock(
                    readlines=lambda: ['Windows_NT'],
                    channel=MagicMock(recv_exit_status=lambda: 0),
                ),
                MagicMock(readlines=lambda: ['']),
            ),
            (
                None,
                MagicMock(
                    readlines=lambda: [
                        'C:\\Users\\user\\build-magic\\file1.txt',
                        'C:\\Users\\user\\build-magic\\file2.txt',
                    ],
                    channel=MagicMock(recv_exit_status=lambda: 0),
                ),
                MagicMock(readlines=lambda: ['']),
            ),
        ),
    )
    mocker.patch('paramiko.SSHClient.close')
    generic_runner.connect = types.MethodType(lambda _: paramiko.SSHClient(), generic_runner)
    generic_runner.provision = types.MethodType(actions.remote_capture_dir, generic_runner)
    assert generic_runner.provision()
    assert exek.call_count == 2
    assert exek.call_args[0] == ('dir /a-D /S /B',)
    assert generic_runner._existing_files == [
        ('C:\\Users\\user\\build-magic\\file1.txt', None),
        ('C:\\Users\\user\\build-magic\\file2.txt', None),
    ]


def test_action_remote_capture_dir_windows_uname_working_directory(generic_runner, mocker):
    """Verify the remote_capture_dir() function with a working directory works correctly on windows."""
    exek = mocker.patch(
        'paramiko.SSHClient.exec_command',
        side_effect=(
            (
                None,
                MagicMock(
                    readlines=lambda: ['Windows_NT'],
                    channel=MagicMock(recv_exit_status=lambda: 0),
                ),
                MagicMock(readlines=lambda: ['']),
            ),
            (
                None,
                MagicMock(
                    readlines=lambda: [
                        'C:\\Users\\user\\my\\project\\file1.txt',
                        'C:\\Users\\user\\my\\project\\file2.txt',
                    ],
                    channel=MagicMock(recv_exit_status=lambda: 0),
                ),
                MagicMock(readlines=lambda: ['']),
            ),
        ),
    )
    mocker.patch('paramiko.SSHClient.close')
    generic_runner.connect = types.MethodType(lambda _: paramiko.SSHClient(), generic_runner)
    generic_runner.provision = types.MethodType(actions.remote_capture_dir, generic_runner)
    generic_runner.working_directory = 'C:\\Users\\user\\my\\project'
    assert generic_runner.provision()
    assert exek.call_count == 2
    assert exek.call_args[0] == ('dir C:\\Users\\user\\my\\project /a-D /S /B',)
    assert generic_runner._existing_files == [
        ('C:\\Users\\user\\my\\project\\file1.txt', None),
        ('C:\\Users\\user\\my\\project\\file2.txt', None),
    ]


def test_action_remote_capture_dir_windows_uname_fail(generic_runner, mocker):
    """Test the case where remote_capture_dir() fails on windows."""
    exek = mocker.patch(
        'paramiko.SSHClient.exec_command',
        side_effect=(
            (
                None,
                MagicMock(
                    readlines=lambda: ['Windows_NT'],
                    channel=MagicMock(recv_exit_status=lambda: 0),
                ),
                MagicMock(readlines=lambda: ['']),
            ),
            (
                None,
                MagicMock(
                    readlines=lambda: [''],
                    channel=MagicMock(recv_exit_status=lambda: 1),
                ),
                MagicMock(readlines=lambda: ['Command failed.']),
            ),
        ),
    )
    mocker.patch('paramiko.SSHClient.close')
    generic_runner.connect = types.MethodType(lambda _: paramiko.SSHClient(), generic_runner)
    generic_runner.provision = types.MethodType(actions.remote_capture_dir, generic_runner)
    assert not generic_runner.provision()
    assert exek.call_count == 2
    assert exek.call_args[0] == ('dir /a-D /S /B',)
    assert not hasattr(generic_runner, '_existing_files')


def test_action_remote_capture_dir_windows_os(generic_runner, mocker):
    """Verify the remote_capture_dir() function works correctly when uname fails."""
    exek = mocker.patch(
        'paramiko.SSHClient.exec_command',
        side_effect=(
            (
                None,
                MagicMock(
                    readlines=lambda: [''],
                    channel=MagicMock(recv_exit_status=lambda: 1),
                ),
                MagicMock(readlines=lambda: ['Command not found.']),
            ),
            (
                None,
                MagicMock(
                    readlines=lambda: ['Windows_NT'],
                    channel=MagicMock(recv_exit_status=lambda: 0),
                ),
                MagicMock(readlines=lambda: ['']),
            ),
            (
                None,
                MagicMock(
                    readlines=lambda: [
                        'C:\\Users\\user\\build-magic\\file1.txt',
                        'C:\\Users\\user\\build-magic\\file2.txt',
                    ],
                    channel=MagicMock(recv_exit_status=lambda: 0),
                ),
                MagicMock(readlines=lambda: ['']),
            ),
        ),
    )
    mocker.patch('paramiko.SSHClient.close')
    generic_runner.connect = types.MethodType(lambda _: paramiko.SSHClient(), generic_runner)
    generic_runner.provision = types.MethodType(actions.remote_capture_dir, generic_runner)
    assert generic_runner.provision()
    assert exek.call_count == 3
    assert exek.call_args[0] == ('dir /a-D /S /B',)
    assert generic_runner._existing_files == [
        ('C:\\Users\\user\\build-magic\\file1.txt', None),
        ('C:\\Users\\user\\build-magic\\file2.txt', None),
    ]


def test_action_remote_capture_dir_windows_os_working_directory(generic_runner, mocker):
    """Verify the remote_capture_dir() function with a working directory works correctly on windows."""
    exek = mocker.patch(
        'paramiko.SSHClient.exec_command',
        side_effect=(
            (
                None,
                MagicMock(
                    readlines=lambda: [''],
                    channel=MagicMock(recv_exit_status=lambda: 1),
                ),
                MagicMock(readlines=lambda: ['Command not found.']),
            ),
            (
                None,
                MagicMock(
                    readlines=lambda: ['Windows_NT'],
                    channel=MagicMock(recv_exit_status=lambda: 0),
                ),
                MagicMock(readlines=lambda: ['']),
            ),
            (
                None,
                MagicMock(
                    readlines=lambda: [
                        'C:\\Users\\user\\my\\project\\file1.txt',
                        'C:\\Users\\user\\my\\project\\file2.txt',
                    ],
                    channel=MagicMock(recv_exit_status=lambda: 0),
                ),
                MagicMock(readlines=lambda: ['']),
            ),
        ),
    )
    mocker.patch('paramiko.SSHClient.close')
    generic_runner.connect = types.MethodType(lambda _: paramiko.SSHClient(), generic_runner)
    generic_runner.provision = types.MethodType(actions.remote_capture_dir, generic_runner)
    generic_runner.working_directory = 'C:\\Users\\user\\my\\project'
    assert generic_runner.provision()
    assert exek.call_count == 3
    assert exek.call_args[0] == ('dir C:\\Users\\user\\my\\project /a-D /S /B',)
    assert generic_runner._existing_files == [
        ('C:\\Users\\user\\my\\project\\file1.txt', None),
        ('C:\\Users\\user\\my\\project\\file2.txt', None),
    ]


def test_action_remote_capture_dir_windows_os_fail(generic_runner, mocker):
    """Test the case where remote_capture_dir() fails on windows."""
    exek = mocker.patch(
        'paramiko.SSHClient.exec_command',
        side_effect=(
            (
                None,
                MagicMock(
                    readlines=lambda: [''],
                    channel=MagicMock(recv_exit_status=lambda: 1),
                ),
                MagicMock(readlines=lambda: ['Command not found.']),
            ),
            (
                None,
                MagicMock(
                    readlines=lambda: ['Windows_NT'],
                    channel=MagicMock(recv_exit_status=lambda: 0),
                ),
                MagicMock(readlines=lambda: ['']),
            ),
            (
                None,
                MagicMock(
                    readlines=lambda: [''],
                    channel=MagicMock(recv_exit_status=lambda: 1),
                ),
                MagicMock(readlines=lambda: ['Command failed.']),
            ),
        ),
    )
    mocker.patch('paramiko.SSHClient.close')
    generic_runner.connect = types.MethodType(lambda _: paramiko.SSHClient(), generic_runner)
    generic_runner.provision = types.MethodType(actions.remote_capture_dir, generic_runner)
    assert not generic_runner.provision()
    assert exek.call_count == 3
    assert exek.call_args[0] == ('dir /a-D /S /B',)
    assert not hasattr(generic_runner, '_existing_files')


def test_action_remote_capture_dir_empty(generic_runner, mocker):
    """Verify the remote_capture_dir() function works correctly with an empty directory."""
    exek = mocker.patch(
        'paramiko.SSHClient.exec_command',
        side_effect=(
            (
                None,
                MagicMock(
                    readlines=lambda: ['Linux'],
                    channel=MagicMock(recv_exit_status=lambda: 0),
                ),
                MagicMock(readlines=lambda: ['']),
            ),
            (
                None,
                MagicMock(
                    readlines=lambda: [''],
                    channel=MagicMock(recv_exit_status=lambda: 0),
                ),
                MagicMock(readlines=lambda: ['']),
            ),
        ),
    )
    mocker.patch('paramiko.SSHClient.close')
    generic_runner.connect = types.MethodType(lambda _: paramiko.SSHClient(), generic_runner)
    generic_runner.provision = types.MethodType(actions.remote_capture_dir, generic_runner)
    assert generic_runner.provision()
    assert exek.call_count == 2
    assert exek.call_args[0] == ('find $PWD -type f | xargs shasum $PWD/*',)
    assert generic_runner._existing_files == []


def test_action_remote_capture_dir_empty_windows(generic_runner, mocker):
    """Verify the remote_capture_dir() function works correctly with an empty directory on Windows."""
    exek = mocker.patch(
        'paramiko.SSHClient.exec_command',
        side_effect=(
            (
                None,
                MagicMock(
                    readlines=lambda: ['Windows_NT'],
                    channel=MagicMock(recv_exit_status=lambda: 0),
                ),
                MagicMock(readlines=lambda: ['']),
            ),
            (
                None,
                MagicMock(
                    readlines=lambda: [''],
                    channel=MagicMock(recv_exit_status=lambda: 0),
                ),
                MagicMock(readlines=lambda: ['']),
            ),
        ),
    )
    mocker.patch('paramiko.SSHClient.close')
    generic_runner.connect = types.MethodType(lambda _: paramiko.SSHClient(), generic_runner)
    generic_runner.provision = types.MethodType(actions.remote_capture_dir, generic_runner)
    assert generic_runner.provision()
    assert exek.call_count == 2
    assert exek.call_args[0] == ('dir /a-D /S /B',)
    assert generic_runner._existing_files == []


def test_action_remote_delete_files(generic_runner, mocker):
    """Verify the remote_delete_files() function works correctly."""
    exek = mocker.patch(
        'paramiko.SSHClient.exec_command',
        side_effect=(
            # uname call.
            (
                None,
                MagicMock(
                    readlines=lambda: ['Linux'],
                    channel=MagicMock(recv_exit_status=lambda: 0),
                ),
                MagicMock(readlines=lambda: ['']),
            ),
            # current files call.
            (
                None,
                MagicMock(
                    readlines=lambda: [
                        '7c211433f02071597741e6ff5a8ea34789abbf43  /home/user/build-magic/file1.txt',
                        '3a19a60069b50fc489030d9e8c872f03d63c9278  /home/user/build-magic/myfiles.tar.gz',
                        'aaf4c61ddcc5e8a2dabede0f3b482cd9aea9434d  /home/user/build-magic/file2.txt',
                        'da39a3ee5e6b4b0d3255bfef95601890afd80709  /home/user/build-magic/other_file.txt',
                    ],
                    channel=MagicMock(recv_exit_status=lambda: 0),
                ),
                MagicMock(readlines=lambda: ['']),
            ),
            # rm call.
            (
                None,
                MagicMock(readlines=lambda: ['']),
                MagicMock(readlines=lambda: ['']),
            ),
        ),
    )
    mocker.patch('paramiko.SSHClient.close')
    generic_runner.connect = types.MethodType(lambda _: paramiko.SSHClient(), generic_runner)
    generic_runner.teardown = types.MethodType(actions.remote_delete_files, generic_runner)
    generic_runner._existing_files = [
        ('/home/user/build-magic/file1.txt', '7c211433f02071597741e6ff5a8ea34789abbf43'),
        ('/home/user/build-magic/file2.txt', 'aaf4c61ddcc5e8a2dabede0f3b482cd9aea9434d'),
    ]
    assert generic_runner.teardown()
    assert exek.call_count == 3
    assert exek.call_args[0] == ('rm "/home/user/build-magic/myfiles.tar.gz" "/home/user/build-magic/other_file.txt"',)


def test_action_remote_delete_files_no_shasum(generic_runner, mocker):
    """Verify the remote_delete_files() function works correctly when there's no shasum command."""
    exek = mocker.patch(
        'paramiko.SSHClient.exec_command',
        side_effect=(
            # uname call.
            (
                None,
                MagicMock(
                    readlines=lambda: ['Linux'],
                    channel=MagicMock(recv_exit_status=lambda: 0),
                ),
                MagicMock(readlines=lambda: ['']),
            ),
            # shasum call fails.
            (
                None,
                MagicMock(
                    readlines=lambda: [''],
                    channel=MagicMock(recv_exit_status=lambda: 1),
                ),
                MagicMock(readlines=lambda: ['Command failed.']),
            ),
            # current files call.
            (
                None,
                MagicMock(
                    readlines=lambda: [
                        '/home/user/build-magic/file1.txt',
                        '/home/user/build-magic/myfiles.tar.gz',
                        '/home/user/build-magic/file2.txt',
                        '/home/user/build-magic/other_file.txt',
                    ],
                    channel=MagicMock(recv_exit_status=lambda: 0),
                ),
                MagicMock(readlines=lambda: ['']),
            ),
            # rm call.
            (
                None,
                MagicMock(readlines=lambda: ['']),
                MagicMock(readlines=lambda: ['']),
            ),
        ),
    )
    mocker.patch('paramiko.SSHClient.close')
    generic_runner.connect = types.MethodType(lambda _: paramiko.SSHClient(), generic_runner)
    generic_runner.teardown = types.MethodType(actions.remote_delete_files, generic_runner)
    generic_runner._existing_files = [
        ('/home/user/build-magic/file1.txt', None),
        ('/home/user/build-magic/file2.txt', None),
    ]
    assert generic_runner.teardown()
    assert exek.call_count == 4
    assert exek.call_args[0] == ('rm "/home/user/build-magic/myfiles.tar.gz" "/home/user/build-magic/other_file.txt"',)


def test_action_remote_delete_files_windows_uname(generic_runner, mocker):
    """Verify the remote_delete_files() function works correctly for windows."""
    exek = mocker.patch(
        'paramiko.SSHClient.exec_command',
        side_effect=(
            # uname call.
            (
                None,
                MagicMock(
                    readlines=lambda: ['Windows_NT'],
                    channel=MagicMock(recv_exit_status=lambda: 0),
                ),
                MagicMock(readlines=lambda: ['']),
            ),
            # current files call.
            (
                None,
                MagicMock(
                    readlines=lambda: [
                        'C:\\build-magic\\file1.txt',
                        'C:\\build-magic\\myfiles.tar.gz',
                        'C:\\build-magic\\file2.txt',
                        'C:\\build-magic\\other_file.txt',
                    ],
                    channel=MagicMock(recv_exit_status=lambda: 0),
                ),
                MagicMock(readlines=lambda: ['']),
            ),
            # rm call.
            (
                None,
                MagicMock(readlines=lambda: ['']),
                MagicMock(readlines=lambda: ['']),
            ),
        ),
    )
    mocker.patch('paramiko.SSHClient.close')
    generic_runner.connect = types.MethodType(lambda _: paramiko.SSHClient(), generic_runner)
    generic_runner.teardown = types.MethodType(actions.remote_delete_files, generic_runner)
    generic_runner._existing_files = [
        ('C:\\build-magic\\file1.txt', None),
        ('C:\\build-magic\\file2.txt', None),
    ]
    assert generic_runner.teardown()
    assert exek.call_count == 3
    assert exek.call_args[0] == ('rm "C:\\build-magic\\myfiles.tar.gz" "C:\\build-magic\\other_file.txt"',)


def test_action_remote_delete_files_windows_os(generic_runner, mocker):
    """Verify the remote_delete_files() function works correctly for windows."""
    exek = mocker.patch(
        'paramiko.SSHClient.exec_command',
        side_effect=(
            # uname call.
            (
                None,
                MagicMock(
                    readlines=lambda: [''],
                    channel=MagicMock(recv_exit_status=lambda: 1),
                ),
                MagicMock(readlines=lambda: ['Command not found.']),
            ),
            # OS call.
            (
                None,
                MagicMock(
                    readlines=lambda: ['Windows_NT'],
                    channel=MagicMock(recv_exit_status=lambda: 0),
                ),
                MagicMock(readlines=lambda: ['']),
            ),
            # current files call.
            (
                None,
                MagicMock(
                    readlines=lambda: [
                        'C:\\build-magic\\file1.txt',
                        'C:\\build-magic\\myfiles.tar.gz',
                        'C:\\build-magic\\file2.txt',
                        'C:\\build-magic\\other_file.txt',
                    ],
                    channel=MagicMock(recv_exit_status=lambda: 0),
                ),
                MagicMock(readlines=lambda: ['']),
            ),
            # rm call.
            (
                None,
                MagicMock(readlines=lambda: ['']),
                MagicMock(readlines=lambda: ['']),
            ),
        ),
    )
    mocker.patch('paramiko.SSHClient.close')
    generic_runner.connect = types.MethodType(lambda _: paramiko.SSHClient(), generic_runner)
    generic_runner.teardown = types.MethodType(actions.remote_delete_files, generic_runner)
    generic_runner._existing_files = [
        ('C:\\build-magic\\file1.txt', None),
        ('C:\\build-magic\\file2.txt', None),
    ]
    assert generic_runner.teardown()
    assert exek.call_count == 4
    assert exek.call_args[0] == ('rm "C:\\build-magic\\myfiles.tar.gz" "C:\\build-magic\\other_file.txt"',)


def test_action_remote_delete_files_unix_fail(generic_runner, mocker):
    """Test the case where getting file hashes and filenames fails."""
    exek = mocker.patch(
        'paramiko.SSHClient.exec_command',
        side_effect=(
            # uname call.
            (
                None,
                MagicMock(
                    readlines=lambda: ['Linux'],
                    channel=MagicMock(recv_exit_status=lambda: 0),
                ),
                MagicMock(readlines=lambda: ['']),
            ),
            # shasum call.
            (
                None,
                MagicMock(
                    readlines=lambda: [''],
                    channel=MagicMock(recv_exit_status=lambda: 1),
                ),
                MagicMock(readlines=lambda: ['Command not found.']),
            ),
            # current files call.
            (
                None,
                MagicMock(
                    readlines=lambda: [''],
                    channel=MagicMock(recv_exit_status=lambda: 1),
                ),
                MagicMock(readlines=lambda: ['Command not found.']),
            ),
        ),
    )
    mocker.patch('paramiko.SSHClient.close')
    generic_runner.connect = types.MethodType(lambda _: paramiko.SSHClient(), generic_runner)
    generic_runner.teardown = types.MethodType(actions.remote_delete_files, generic_runner)
    generic_runner._existing_files = [
        ('/home/user/build-magic/file1.txt', '7c211433f02071597741e6ff5a8ea34789abbf43'),
        ('/home/user/build-magic/file2.txt', 'aaf4c61ddcc5e8a2dabede0f3b482cd9aea9434d'),
    ]
    assert not generic_runner.teardown()
    assert exek.call_count == 3
    assert exek.call_args[0] == ('find $PWD -type f',)


def test_action_remote_delete_files_windows_uname_fail(generic_runner, mocker):
    """Test the case where getting filenames in Windows fails."""
    exek = mocker.patch(
        'paramiko.SSHClient.exec_command',
        side_effect=(
            # uname call.
            (
                None,
                MagicMock(
                    readlines=lambda: ['Windows_NT'],
                    channel=MagicMock(recv_exit_status=lambda: 0),
                ),
                MagicMock(readlines=lambda: ['']),
            ),
            # current files call.
            (
                None,
                MagicMock(
                    readlines=lambda: [''],
                    channel=MagicMock(recv_exit_status=lambda: 1),
                ),
                MagicMock(readlines=lambda: ['Command not found.']),
            ),
        ),
    )
    mocker.patch('paramiko.SSHClient.close')
    generic_runner.connect = types.MethodType(lambda _: paramiko.SSHClient(), generic_runner)
    generic_runner.teardown = types.MethodType(actions.remote_delete_files, generic_runner)
    generic_runner._existing_files = [
        ('C:\\build-magic\\file1.txt', None),
        ('C:\\build-magic\\file2.txt', None),
    ]
    assert not generic_runner.teardown()
    assert exek.call_count == 2
    assert exek.call_args[0] == ('dir /a-D /S /B',)


def test_action_remote_delete_files_windows_os_fail(generic_runner, mocker):
    """Test the case where getting filenames in Windows fails."""
    exek = mocker.patch(
        'paramiko.SSHClient.exec_command',
        side_effect=(
            # uname call.
            (
                None,
                MagicMock(
                    readlines=lambda: [''],
                    channel=MagicMock(recv_exit_status=lambda: 1),
                ),
                MagicMock(readlines=lambda: ['Command not found.']),
            ),
            # OS call.
            (
                None,
                MagicMock(
                    readlines=lambda: [''],
                    channel=MagicMock(recv_exit_status=lambda: 1),
                ),
                MagicMock(readlines=lambda: ['Command not found.']),
            ),
        ),
    )
    mocker.patch('paramiko.SSHClient.close')
    generic_runner.connect = types.MethodType(lambda _: paramiko.SSHClient(), generic_runner)
    generic_runner.teardown = types.MethodType(actions.remote_delete_files, generic_runner)
    generic_runner._existing_files = [
        ('C:\\build-magic\\file1.txt', None),
        ('C:\\build-magic\\file2.txt', None),
    ]
    assert not generic_runner.teardown()
    assert exek.call_count == 2
    assert exek.call_args[0] == ('%OS%',)


def test_action_remote_delete_files_unsupported_os(generic_runner, mocker):
    """Test the case where uname is an unknown OS."""
    exek = mocker.patch(
        'paramiko.SSHClient.exec_command',
        side_effect=(
            # uname call.
            (
                None,
                MagicMock(
                    readlines=lambda: ['AIX'],
                    channel=MagicMock(recv_exit_status=lambda: 0),
                ),
                MagicMock(readlines=lambda: ['']),
            ),
        ),
    )
    mocker.patch('paramiko.SSHClient.close')
    generic_runner.connect = types.MethodType(lambda _: paramiko.SSHClient(), generic_runner)
    generic_runner.teardown = types.MethodType(actions.remote_delete_files, generic_runner)
    generic_runner._existing_files = [
        ('C:\\build-magic\\file1.txt', None),
        ('C:\\build-magic\\file2.txt', None),
    ]
    assert not generic_runner.teardown()
    assert exek.call_count == 1
    assert exek.call_args[0] == ('uname',)


def test_action_remote_delete_files_windows_os_filename_fail(generic_runner, mocker):
    """Test the case where getting filenames in Windows fails."""
    exek = mocker.patch(
        'paramiko.SSHClient.exec_command',
        side_effect=(
            # uname call.
            (
                None,
                MagicMock(
                    readlines=lambda: [''],
                    channel=MagicMock(recv_exit_status=lambda: 1),
                ),
                MagicMock(readlines=lambda: ['Command not found.']),
            ),
            # OS call.
            (
                None,
                MagicMock(
                    readlines=lambda: ['Windows_NT'],
                    channel=MagicMock(recv_exit_status=lambda: 0),
                ),
                MagicMock(readlines=lambda: ['']),
            ),
            # Current files call.
            (
                None,
                MagicMock(
                    readlines=lambda: [''],
                    channel=MagicMock(recv_exit_status=lambda: 1),
                ),
                MagicMock(readlines=lambda: ['Command not found.']),
            ),
        ),
    )
    mocker.patch('paramiko.SSHClient.close')
    generic_runner.connect = types.MethodType(lambda _: paramiko.SSHClient(), generic_runner)
    generic_runner.teardown = types.MethodType(actions.remote_delete_files, generic_runner)
    generic_runner._existing_files = [
        ('C:\\build-magic\\file1.txt', None),
        ('C:\\build-magic\\file2.txt', None),
    ]
    assert not generic_runner.teardown()
    assert exek.call_count == 3
    assert exek.call_args[0] == ('dir /a-D /S /B',)


def test_action_remote_delete_files_no_existing_files(generic_runner):
    """Test the case where _existing_files isn't set."""
    generic_runner.teardown = types.MethodType(actions.remote_delete_files, generic_runner)
    assert not generic_runner.teardown()


def test_action_remote_delete_files_no_change(generic_runner, mocker):
    """Test the case where no files are deleted because there aren't any new files."""
    exek = mocker.patch(
        'paramiko.SSHClient.exec_command',
        side_effect=(
            # uname call.
            (
                None,
                MagicMock(
                    readlines=lambda: ['Linux'],
                    channel=MagicMock(recv_exit_status=lambda: 0),
                ),
                MagicMock(readlines=lambda: ['']),
            ),
            # current files call.
            (
                None,
                MagicMock(
                    readlines=lambda: [
                        '7c211433f02071597741e6ff5a8ea34789abbf43  /home/user/build-magic/file1.txt',
                        'aaf4c61ddcc5e8a2dabede0f3b482cd9aea9434d  /home/user/build-magic/file2.txt',
                    ],
                    channel=MagicMock(recv_exit_status=lambda: 0),
                ),
                MagicMock(readlines=lambda: ['']),
            ),
        ),
    )
    mocker.patch('paramiko.SSHClient.close')
    generic_runner.connect = types.MethodType(lambda _: paramiko.SSHClient(), generic_runner)
    generic_runner.teardown = types.MethodType(actions.remote_delete_files, generic_runner)
    generic_runner._existing_files = [
        ('/home/user/build-magic/file1.txt', '7c211433f02071597741e6ff5a8ea34789abbf43'),
        ('/home/user/build-magic/file2.txt', 'aaf4c61ddcc5e8a2dabede0f3b482cd9aea9434d'),
    ]
    assert generic_runner.teardown()
    assert exek.call_count == 2
    assert exek.call_args[0] == ('find $PWD -type f | xargs shasum $PWD/*',)


def test_action_remote_delete_files_empty_directory(generic_runner, mocker):
    """Test the case where no files are in the working directory."""
    exek = mocker.patch('paramiko.SSHClient.exec_command')
    mocker.patch('paramiko.SSHClient.close')
    generic_runner.connect = types.MethodType(lambda _: paramiko.SSHClient(), generic_runner)
    generic_runner.teardown = types.MethodType(actions.remote_delete_files, generic_runner)
    generic_runner._existing_files = []
    assert generic_runner.teardown()
    assert exek.call_count == 0


def test_action_remote_delete_files_copies_by_hash(generic_runner, mocker):
    """Verify the remote_delete_files() function correctly deletes copied files by hash."""
    exek = mocker.patch(
        'paramiko.SSHClient.exec_command',
        side_effect=(
            # uname call.
            (
                None,
                MagicMock(
                    readlines=lambda: ['Linux'],
                    channel=MagicMock(recv_exit_status=lambda: 0),
                ),
                MagicMock(readlines=lambda: ['']),
            ),
            # current files call.
            (
                None,
                MagicMock(
                    readlines=lambda: [
                        '7c211433f02071597741e6ff5a8ea34789abbf43  /home/user/build-magic/file1.txt',
                        '7c211433f02071597741e6ff5a8ea34789abbf43  /home/user/build-magic/myfiles.tar.gz',
                        'aaf4c61ddcc5e8a2dabede0f3b482cd9aea9434d  /home/user/build-magic/file2.txt',
                        'aaf4c61ddcc5e8a2dabede0f3b482cd9aea9434d  /home/user/build-magic/other_file.txt',
                    ],
                    channel=MagicMock(recv_exit_status=lambda: 0),
                ),
                MagicMock(readlines=lambda: ['']),
            ),
            # rm call.
            (
                None,
                MagicMock(readlines=lambda: ['']),
                MagicMock(readlines=lambda: ['']),
            ),
        ),
    )
    mocker.patch('paramiko.SSHClient.close')
    generic_runner.connect = types.MethodType(lambda _: paramiko.SSHClient(), generic_runner)
    generic_runner.teardown = types.MethodType(actions.remote_delete_files, generic_runner)
    generic_runner._existing_files = [
        ('/home/user/build-magic/file1.txt', '7c211433f02071597741e6ff5a8ea34789abbf43'),
        ('/home/user/build-magic/file2.txt', 'aaf4c61ddcc5e8a2dabede0f3b482cd9aea9434d'),
    ]
    assert generic_runner.teardown()
    assert exek.call_count == 3
    assert exek.call_args[0] == ('rm "/home/user/build-magic/myfiles.tar.gz" "/home/user/build-magic/other_file.txt"',)


def test_action_remote_delete_files_copies_by_filename(generic_runner, mocker):
    """Verify the remote_delete_files() function correctly deletes copied files by filename."""
    exek = mocker.patch(
        'paramiko.SSHClient.exec_command',
        side_effect=(
            # uname call.
            (
                None,
                MagicMock(
                    readlines=lambda: ['Windows_NT'],
                    channel=MagicMock(recv_exit_status=lambda: 0),
                ),
                MagicMock(readlines=lambda: ['']),
            ),
            # current files call.
            (
                None,
                MagicMock(
                    readlines=lambda: [
                        'C:\\build-magic\\file1.txt',
                        'C:\\build-magic\\myfiles.tar.gz',
                        'C:\\build-magic\\file2.txt',
                        'C:\\build-magic\\other_file.txt',
                    ],
                    channel=MagicMock(recv_exit_status=lambda: 0),
                ),
                MagicMock(readlines=lambda: ['']),
            ),
            # rm call.
            (
                None,
                MagicMock(readlines=lambda: ['']),
                MagicMock(readlines=lambda: ['']),
            ),
        ),
    )
    mocker.patch('paramiko.SSHClient.close')
    generic_runner.connect = types.MethodType(lambda _: paramiko.SSHClient(), generic_runner)
    generic_runner.teardown = types.MethodType(actions.remote_delete_files, generic_runner)
    generic_runner._existing_files = [
        ('C:\\build-magic\\file1.txt', None),
        ('C:\\build-magic\\file2.txt', None),
    ]
    assert generic_runner.teardown()
    assert exek.call_count == 3
    assert exek.call_args[0] == ('rm "C:\\build-magic\\myfiles.tar.gz" "C:\\build-magic\\other_file.txt"',)


def test_action_remote_delete_files_preserve_renamed_files_by_hash(generic_runner, mocker):
    """Test the case where files in _existing_files are renamed."""
    exek = mocker.patch(
        'paramiko.SSHClient.exec_command',
        side_effect=(
            # uname call.
            (
                None,
                MagicMock(
                    readlines=lambda: ['Linux'],
                    channel=MagicMock(recv_exit_status=lambda: 0),
                ),
                MagicMock(readlines=lambda: ['']),
            ),
            # current files call.
            (
                None,
                MagicMock(
                    readlines=lambda: [
                        '7c211433f02071597741e6ff5a8ea34789abbf43  /home/user/build-magic/copy1.txt',
                        'aaf4c61ddcc5e8a2dabede0f3b482cd9aea9434d  /home/user/build-magic/file2.txt',
                    ],
                    channel=MagicMock(recv_exit_status=lambda: 0),
                ),
                MagicMock(readlines=lambda: ['']),
            ),
        ),
    )
    mocker.patch('paramiko.SSHClient.close')
    generic_runner.connect = types.MethodType(lambda _: paramiko.SSHClient(), generic_runner)
    generic_runner.teardown = types.MethodType(actions.remote_delete_files, generic_runner)
    generic_runner._existing_files = [
        ('/home/user/build-magic/file1.txt', '7c211433f02071597741e6ff5a8ea34789abbf43'),
        ('/home/user/build-magic/file2.txt', 'aaf4c61ddcc5e8a2dabede0f3b482cd9aea9434d'),
    ]
    assert generic_runner.teardown()
    assert exek.call_count == 2
    assert exek.call_args[0] == ('find $PWD -type f | xargs shasum $PWD/*',)


def test_action_remote_delete_files_preserve_modified_files_by_hash(generic_runner, mocker):
    """Test the case where files in _existing_files are modified."""
    exek = mocker.patch(
        'paramiko.SSHClient.exec_command',
        side_effect=(
            # uname call.
            (
                None,
                MagicMock(
                    readlines=lambda: ['Linux'],
                    channel=MagicMock(recv_exit_status=lambda: 0),
                ),
                MagicMock(readlines=lambda: ['']),
            ),
            # current files call.
            (
                None,
                MagicMock(
                    readlines=lambda: [
                        'da39a3ee5e6b4b0d3255bfef95601890afd80709  /home/user/build-magic/file1.txt',
                        'aaf4c61ddcc5e8a2dabede0f3b482cd9aea9434d  /home/user/build-magic/file2.txt',
                    ],
                    channel=MagicMock(recv_exit_status=lambda: 0),
                ),
                MagicMock(readlines=lambda: ['']),
            ),
        ),
    )
    mocker.patch('paramiko.SSHClient.close')
    generic_runner.connect = types.MethodType(lambda _: paramiko.SSHClient(), generic_runner)
    generic_runner.teardown = types.MethodType(actions.remote_delete_files, generic_runner)
    generic_runner._existing_files = [
        ('/home/user/build-magic/file1.txt', '7c211433f02071597741e6ff5a8ea34789abbf43'),
        ('/home/user/build-magic/file2.txt', 'aaf4c61ddcc5e8a2dabede0f3b482cd9aea9434d'),
    ]
    assert generic_runner.teardown()
    assert exek.call_count == 2
    assert exek.call_args[0] == ('find $PWD -type f | xargs shasum $PWD/*',)


def test_action_remote_delete_files_preserve_renamed_files_by_name(generic_runner, mocker):
    """Test the case where files in _existing_files are renamed on Windows."""
    exek = mocker.patch(
        'paramiko.SSHClient.exec_command',
        side_effect=(
            # uname call.
            (
                None,
                MagicMock(
                    readlines=lambda: ['Windows_NT'],
                    channel=MagicMock(recv_exit_status=lambda: 0),
                ),
                MagicMock(readlines=lambda: ['']),
            ),
            # current files call.
            (
                None,
                MagicMock(
                    readlines=lambda: [
                        'C:\\build-magic\\copy1.txt',
                        'C:\\build-magic\\file2.txt',
                    ],
                    channel=MagicMock(recv_exit_status=lambda: 0),
                ),
                MagicMock(readlines=lambda: ['']),
            ),
            # rm call.
            (
                None,
                MagicMock(readlines=lambda: ['']),
                MagicMock(readlines=lambda: ['']),
            ),
        ),
    )
    mocker.patch('paramiko.SSHClient.close')
    generic_runner.connect = types.MethodType(lambda _: paramiko.SSHClient(), generic_runner)
    generic_runner.teardown = types.MethodType(actions.remote_delete_files, generic_runner)
    generic_runner._existing_files = [
        ('C:\\build-magic\\file1.txt', None),
        ('C:\\build-magic\\file2.txt', None),
    ]
    assert generic_runner.teardown()
    assert exek.call_count == 3
    assert exek.call_args[0] == ('rm "C:\\build-magic\\copy1.txt"',)
