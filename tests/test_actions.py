"""This module hosts unit tests for the actions module."""

import hashlib
import os
import pathlib
from pathlib import Path
import subprocess
import types
from unittest.mock import MagicMock

import docker
from docker.errors import APIError, ImageLoadError, ImageNotFound
import paramiko
import pytest
import vagrant

from build_magic import actions
from build_magic.exc import ContainerExistsError
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
def backup_path(build_path):
    """Provides a build-magic backup path for a working directory."""
    backup = build_path / actions.BACKUP_PATH
    backup.mkdir()
    file1 = backup / 'file1.txt'
    file2 = backup / 'file2.txt'
    file1.write_text('hello')
    file2.write_text('world')


@pytest.fixture
def git_path(build_path):
    """Provides a working directory with a .git directory."""
    git = build_path / '.git'
    git.mkdir()
    head = git / 'HEAD'
    config = git / 'config'
    refs = git / 'refs'
    refs.mkdir()
    head.touch()
    config.touch()
    test1 = refs / 'test1'
    test2 = refs / 'test2'
    test1.write_text(hashlib.sha1(b'1234').hexdigest())
    test2.write_text(hashlib.sha1(b'abcd').hexdigest())


@pytest.fixture
def nested_path(tmp_path_factory):
    """Provides a temp directory with nested directories in it."""
    magic = tmp_path_factory.mktemp('build_magic')
    dir1level1 = magic / 'dir1level1'
    dir2level1 = magic / 'dir2level1'
    dir1level1.mkdir()
    dir2level1.mkdir()
    dir1level2 = dir1level1 / 'dir1level2'
    dir2level2 = dir1level1 / 'dir2level2'
    dir3level2 = dir2level1 / 'dir3level2'
    dir4level2 = dir2level1 / 'dir4level2'
    dir1level2.mkdir()
    dir2level2.mkdir()
    dir3level2.mkdir()
    dir4level2.mkdir()
    dir1level3 = dir1level2 / 'dir1level3'
    dir2level3 = dir1level2 / 'dir2level3'
    dir3level3 = dir2level2 / 'dir3level3'
    dir4level3 = dir2level2 / 'dir4level3'
    dir5level3 = dir3level2 / 'dir5level3'
    dir6level3 = dir3level2 / 'dir6level3'
    dir7level3 = dir4level2 / 'dir7level3'
    dir8level3 = dir4level2 / 'dir8level3'
    dir1level3.mkdir()
    dir2level3.mkdir()
    dir3level3.mkdir()
    dir4level3.mkdir()
    dir5level3.mkdir()
    dir6level3.mkdir()
    dir7level3.mkdir()
    dir8level3.mkdir()
    return magic


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
            command = macro.as_string()
            result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
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
            'docker': 'docker_capture_dir',
            'vagrant': 'vm_up',
        },
        'teardown': {
            'local': 'delete_new_files',
            'remote': 'remote_delete_files',
            'docker': 'docker_delete_new_files',
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


def test_action_vm_up_error(capsys, generic_runner, mocker):
    """Test the case where vm_up() encounters a subprocess error."""
    mocker.patch('vagrant.Vagrant.up', side_effect=subprocess.CalledProcessError(1, 'error'))
    generic_runner.provision = types.MethodType(actions.vm_up, generic_runner)
    generic_runner.teardown = types.MethodType(actions.null, generic_runner)
    assert not generic_runner.provision()
    captured = capsys.readouterr()
    assert captured.out == "Command 'error' returned non-zero exit status 1.\n"


def test_action_vm_destroy(generic_runner, mocker):
    """Verify the vm_destroy() function works correctly."""
    destroy = mocker.patch('vagrant.Vagrant.destroy')
    generic_runner.teardown = types.MethodType(actions.vm_destroy, generic_runner)
    assert generic_runner.teardown()
    assert destroy.call_count == 0

    # Assign _vm to None.
    generic_runner._vm = None
    assert generic_runner.teardown()
    assert destroy.call_count == 0

    # Assign _vm to a string.
    generic_runner._vm = 'blah'
    assert generic_runner.teardown()
    assert destroy.call_count == 0

    # Assign _vm to a Vagrant object.
    generic_runner._vm = vagrant.Vagrant()
    generic_runner.alt_vagrantfile_name = 'Vagrantfile_build_magic'
    assert generic_runner.teardown()
    assert destroy.call_count == 1


def test_action_vm_destroy_delete_vagrantfile(generic_runner, mocker, tmp_path):
    """Verify the vm_destroy() function properly deletes a build-magic generated Vagrantfile."""
    mocker.patch('vagrant.Vagrant.destroy')

    ref_vagrantfile = Path(__file__).parent / 'files' / 'Vagrantfile'
    vagrantfile_path = tmp_path / 'vagrant_build_magic'
    vagrantfile_path.mkdir()
    vagrantfile = ref_vagrantfile.read_text()
    vagrantfile_path.joinpath('Vagrantfile_build_magic').write_text(vagrantfile)

    assert vagrantfile_path.joinpath('Vagrantfile_build_magic').exists()

    generic_runner.teardown = types.MethodType(actions.vm_destroy, generic_runner)
    generic_runner.environment = vagrantfile_path
    generic_runner._vm = vagrant.Vagrant()
    generic_runner.alt_vagrantfile_name = 'Vagrantfile_build_magic'
    generic_runner.teardown()
    assert not vagrantfile_path.joinpath('Vagrantfile_build_magic').exists()


def test_action_vm_destroy_error(generic_runner, mocker):
    """Test the case where vm_destroy() encounters a subprocess error."""
    mocker.patch('vagrant.Vagrant.destroy', side_effect=subprocess.CalledProcessError(1, 'error'))
    generic_runner.teardown = types.MethodType(actions.vm_destroy, generic_runner)
    generic_runner._vm = vagrant.Vagrant()
    assert not generic_runner.teardown()


def test_action_container_up(generic_runner, mocker):
    """Verify the container_up() function works correctly."""
    mocker.patch('docker.client.DockerClient.containers', new_callable=mocker.PropertyMock)
    mocker.patch('docker.client.DockerClient.containers.list', return_value=[])
    run = mocker.patch('docker.client.DockerClient.containers.run')
    ref = {
        'detach': True,
        'tty': True,
        'entrypoint': 'sh',
        'working_dir': '/build_magic',
        'mounts': [
            {
                'dir': {
                    'bind': '/build_magic',
                    'mode': 'rw',
                },
            },
        ],
        'name': 'build-magic',
    }
    generic_runner.binding = {
        'dir': {
            'bind': '/build_magic',
            'mode': 'rw',
        }
    }
    generic_runner.working_directory = '/build_magic'
    generic_runner.provision = types.MethodType(actions.container_up, generic_runner)
    assert generic_runner.provision()
    assert run.call_count == 1
    assert run.call_args[0] == ('dummy',)
    assert run.call_args[1] == ref
    assert not hasattr(generic_runner, 'guest_wd')


def test_action_container_up_error(generic_runner, mocker):
    """Test the case where an error is raised when starting the container."""
    mocker.patch('docker.client.DockerClient.containers', new_callable=mocker.PropertyMock)
    mocker.patch('docker.client.DockerClient.containers.list', return_value=[])
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


def test_action_container_up_container_exists(generic_runner, mocker):
    """Test the case where a build-magic container is already running."""
    mocker.patch('docker.client.DockerClient.containers', new_callable=mocker.PropertyMock)
    mocker.patch('docker.client.DockerClient.containers.list', return_value=[MagicMock])
    generic_runner.binding = {
        'dir': {
            'bind': '/build_magic',
            'mode': 'rw',
        }
    }
    generic_runner.working_directory = '/build_magic'
    generic_runner.provision = types.MethodType(actions.container_up, generic_runner)
    with pytest.raises(ContainerExistsError):
        generic_runner.provision()


def test_action_container_up_image_not_found(generic_runner, mocker):
    """Test the case where an image/environment cannot be found."""
    mocker.patch('docker.client.DockerClient.containers', new_callable=mocker.PropertyMock)
    mocker.patch('docker.client.DockerClient.containers.list', return_value=[])
    mocker.patch('docker.client.DockerClient.containers.run', side_effect=ImageNotFound('Not found'))
    generic_runner.binding = {
        'dir': {
            'bind': '/build_magic',
            'mode': 'rw',
        }
    }
    generic_runner.working_directory = '/build_magic'
    generic_runner.provision = types.MethodType(actions.container_up, generic_runner)
    with pytest.raises(ImageNotFound):
        generic_runner.provision()


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


def test_action_capture_dir(build_hashes, build_path, generic_runner, mocker):
    """Verify the capture_dir() function works correctly."""
    os.chdir(str(build_path))
    mocker.patch('build_magic.actions.container_up', return_value=True)
    # Local capture
    generic_runner.provision = types.MethodType(actions.capture_dir, generic_runner)
    files = [str(file) for file in Path.cwd().resolve().iterdir()]
    ref = []
    for file in files:
        ref.append((file, hashlib.sha1(Path(file).read_bytes()).hexdigest()))
    assert generic_runner.provision()
    assert sorted(generic_runner._existing_files) == sorted(ref)

    # Docker capture
    generic_runner.host_wd = '.'
    generic_runner.provision = types.MethodType(actions.docker_capture_dir, generic_runner)
    files = [str(file) for file in Path.cwd().resolve().iterdir()]
    ref = []
    for file in files:
        ref.append((file, hashlib.sha1(Path(file).read_bytes()).hexdigest()))
    assert generic_runner.provision()
    assert sorted(generic_runner._existing_files) == sorted(ref)


def test_action_capture_dir_empty(empty_path, generic_runner, mocker):
    """Verify the capture_dir() function works with an empty directory."""
    os.chdir(str(empty_path))
    mocker.patch('build_magic.actions.container_up', return_value=True)
    # Local capture
    generic_runner.provision = types.MethodType(actions.capture_dir, generic_runner)
    assert generic_runner.provision()
    assert hasattr(generic_runner, '_existing_files')
    assert len(generic_runner._existing_files) == 0

    # Docker capture
    generic_runner.host_wd = '.'
    generic_runner.provision = types.MethodType(actions.docker_capture_dir, generic_runner)
    assert generic_runner.provision()
    assert hasattr(generic_runner, '_existing_files')
    assert len(generic_runner._existing_files) == 0


def test_action_capture_dir_error(build_path, generic_runner, mocker):
    """Test the case where capture_dir() raises an error."""
    os.chdir(str(build_path))
    mocker.patch('build_magic.actions.container_up', return_value=True)
    # Local capture
    mocker.patch('pathlib.Path.resolve', side_effect=IsADirectoryError)
    generic_runner.provision = types.MethodType(actions.capture_dir, generic_runner)
    assert not generic_runner.provision()

    # Docker capture
    generic_runner.host_wd = '.'
    generic_runner.provision = types.MethodType(actions.docker_capture_dir, generic_runner)
    assert not generic_runner.provision()


def test_action_capture_dir_permission_error(build_path, generic_runner, mocker):
    """Test the case where a PermissionError is raised when trying to get the hash for a file."""
    os.chdir(str(build_path))
    mocker.patch('build_magic.actions.container_up', return_value=True)
    mocker.patch('pathlib.Path.read_bytes', side_effect=PermissionError)
    # Local capture
    generic_runner.provision = types.MethodType(actions.capture_dir, generic_runner)
    assert generic_runner.provision()
    assert hasattr(generic_runner, '_existing_files')
    assert len(generic_runner._existing_files) == 0

    # Docker capture
    generic_runner.host_wd = '.'
    generic_runner.provision = types.MethodType(actions.capture_dir, generic_runner)
    assert generic_runner.provision()
    assert hasattr(generic_runner, '_existing_files')
    assert len(generic_runner._existing_files) == 0


def test_action_delete_new_files(build_hashes, build_path, generic_runner, mocker):
    """Verify the delete_new_files() function works correctly."""
    os.chdir(str(build_path))
    mocker.patch('build_magic.actions.container_destroy', return_value=True)
    # Local capture
    generic_runner.teardown = types.MethodType(actions.delete_new_files, generic_runner)
    files = [str(file) for file in Path.cwd().resolve().rglob('*')]
    generic_runner._existing_files = list(zip(files, build_hashes))
    generic_runner.execute(Macro('tar -czf myfiles.tar.gz file1.txt file2.txt'))
    assert generic_runner.teardown()
    assert sorted([str(file) for file in Path.cwd().resolve().rglob('*')]) == sorted(files)

    # Docker capture
    generic_runner.host_wd = '.'
    generic_runner.teardown = types.MethodType(actions.docker_delete_new_files, generic_runner)
    files = [str(file) for file in Path.cwd().resolve().rglob('*')]
    generic_runner._existing_files = list(zip(files, build_hashes))
    generic_runner.execute(Macro('tar -czf myfiles.tar.gz file1.txt file2.txt'))
    assert generic_runner.teardown()
    assert sorted([str(file) for file in Path.cwd().resolve().rglob('*')]) == sorted(files)


def test_action_delete_new_files_copy(build_hashes, build_path, cp, generic_runner, mocker):
    """Verify the delete_new_files() function works correctly with copies of existing files."""
    os.chdir(str(build_path))
    mocker.patch('build_magic.actions.container_destroy', return_value=True)

    # Local capture
    generic_runner.teardown = types.MethodType(actions.delete_new_files, generic_runner)
    files = [str(file) for file in Path.cwd().resolve().rglob('*')]
    existing = []
    for file in files:
        existing.append((file, hashlib.sha1(Path(file).read_bytes()).hexdigest()))
    generic_runner._existing_files = existing
    generic_runner.execute(Macro(f'{cp} file2.txt temp.txt'))
    assert build_path.joinpath('temp.txt').exists()
    assert generic_runner.teardown()
    assert not build_path.joinpath('temp.txt').exists()
    assert sorted([str(file) for file in Path.cwd().resolve().rglob('*')]) == sorted(files)

    # Docker capture
    generic_runner.host_wd = '.'
    generic_runner.teardown = types.MethodType(actions.docker_delete_new_files, generic_runner)
    files = [str(file) for file in Path.cwd().resolve().rglob('*')]
    existing = []
    for file in files:
        existing.append((file, hashlib.sha1(Path(file).read_bytes()).hexdigest()))
    generic_runner._existing_files = existing
    generic_runner.execute(Macro(f'{cp} file2.txt temp.txt'))
    assert build_path.joinpath('temp.txt').exists()
    assert generic_runner.teardown()
    assert not build_path.joinpath('temp.txt').exists()
    assert sorted([str(file) for file in Path.cwd().resolve().rglob('*')]) == sorted(files)


def test_action_delete_new_files_preserve_renamed_file(build_hashes, build_path, generic_runner, mocker, mv):
    """Verify that a renamed file isn't deleted by delete_new_files()."""
    os.chdir(str(build_path))
    mocker.patch('build_magic.actions.container_destroy', return_value=True)

    # Local capture
    generic_runner.teardown = types.MethodType(actions.delete_new_files, generic_runner)
    files = [str(file) for file in Path.cwd().resolve().rglob('*')]
    generic_runner._existing_files = list(zip(files, build_hashes))
    generic_runner.execute(Macro(f'{mv} file2.txt temp.txt'))
    assert build_path.joinpath('temp.txt').exists()
    assert not build_path.joinpath('file2.txt').exists()
    ref_files = [str(file) for file in Path.cwd().resolve().iterdir()]
    assert generic_runner.teardown()
    assert sorted([str(file) for file in Path.cwd().resolve().rglob('*')]) == sorted(ref_files)

    # Docker capture
    generic_runner.host_wd = '.'
    generic_runner.teardown = types.MethodType(actions.docker_delete_new_files, generic_runner)
    files = [str(file) for file in Path.cwd().resolve().rglob('*')]
    generic_runner._existing_files = list(zip(files, build_hashes))
    generic_runner.execute(Macro(f'{mv} file2.txt temp.txt'))
    assert build_path.joinpath('temp.txt').exists()
    assert not build_path.joinpath('file2.txt').exists()
    ref_files = [str(file) for file in Path.cwd().resolve().iterdir()]
    assert generic_runner.teardown()
    assert sorted([str(file) for file in Path.cwd().resolve().rglob('*')]) == sorted(ref_files)


def test_action_delete_new_files_preserve_modified_file(build_hashes, build_path, generic_runner, mocker, mv):
    """Verify that a modified file isn't deleted by delete_new_files()."""
    os.chdir(str(build_path))
    mocker.patch('build_magic.actions.container_destroy', return_value=True)

    # Local capture
    generic_runner.teardown = types.MethodType(actions.delete_new_files, generic_runner)
    files = [str(file) for file in Path.cwd().resolve().rglob('*')]
    generic_runner._existing_files = list(zip(files, build_hashes))
    generic_runner.execute(Macro(f'{mv} file1.txt file2.txt'))
    assert build_path.joinpath('file2.txt').exists()
    assert not build_path.joinpath('file1.txt').exists()
    ref_files = [str(file) for file in Path.cwd().resolve().rglob('*')]
    assert generic_runner.teardown()
    assert sorted([str(file) for file in Path.cwd().resolve().iterdir()]) == sorted(ref_files)

    # Docker capture
    generic_runner.host_wd = '.'
    generic_runner.teardown = types.MethodType(actions.docker_delete_new_files, generic_runner)
    files = [str(file) for file in Path.cwd().resolve().rglob('*')]
    generic_runner._existing_files = list(zip(files, build_hashes))
    generic_runner.execute(Macro(f'{mv} file1.txt file2.txt'))
    assert build_path.joinpath('file2.txt').exists()
    assert not build_path.joinpath('file1.txt').exists()
    ref_files = [str(file) for file in Path.cwd().resolve().rglob('*')]
    assert generic_runner.teardown()
    assert sorted([str(file) for file in Path.cwd().resolve().iterdir()]) == sorted(ref_files)


def test_action_delete_new_files_empty_directory(empty_path, generic_runner, mocker):
    """Verify the delete_new_files() function works correctly starting with an empty directory."""
    os.chdir(str(empty_path))
    mocker.patch('build_magic.actions.container_destroy', return_value=True)
    # Local capture
    generic_runner.teardown = types.MethodType(actions.delete_new_files, generic_runner)
    generic_runner._existing_files = [str(file) for file in Path.cwd().resolve().rglob('*')]
    generic_runner._existing_dirs = generic_runner._existing_files
    assert len(generic_runner._existing_files) == 0
    generic_runner.execute(Macro('touch hello.txt'))
    assert generic_runner.teardown() is True
    assert len([str(file) for file in Path.cwd().resolve().rglob('*')]) == 0

    # Docker capture
    generic_runner.host_wd = '.'
    generic_runner.teardown = types.MethodType(actions.docker_delete_new_files, generic_runner)
    generic_runner._existing_files = [str(file) for file in Path.cwd().resolve().rglob('*')]
    assert len(generic_runner._existing_files) == 0
    generic_runner.execute(Macro('touch hello.txt'))
    assert generic_runner.teardown() is True
    assert len([str(file) for file in Path.cwd().resolve().rglob('*')]) == 0


def test_action_delete_new_files_empty_directory_permission_error(empty_path, generic_runner, mocker, touch):
    """Test the case where delete_new_files() raises a PermissionError attempting to delete a file."""
    os.chdir(str(empty_path))
    mocker.patch('build_magic.actions.container_destroy', return_value=True)
    mocker.patch('os.remove', side_effect=PermissionError)
    # Local capture
    generic_runner.teardown = types.MethodType(actions.delete_new_files, generic_runner)
    generic_runner._existing_files = [str(file) for file in Path.cwd().resolve().rglob('*')]
    generic_runner._existing_dirs = generic_runner._existing_files
    assert len(generic_runner._existing_files) == 0
    generic_runner.execute(Macro(f'{touch} hello.txt'))
    assert generic_runner.teardown() is True
    assert len([str(file) for file in Path.cwd().resolve().rglob('*')]) == 1

    pathlib.Path('hello.txt').unlink()

    # Docker capture
    generic_runner.host_wd = '.'
    generic_runner.teardown = types.MethodType(actions.docker_delete_new_files, generic_runner)
    generic_runner._existing_files = [str(file) for file in Path.cwd().resolve().rglob('*')]
    generic_runner._existing_dirs = generic_runner._existing_files
    assert len(generic_runner._existing_files) == 0
    generic_runner.execute(Macro(f'{touch} hello.txt'))
    assert generic_runner.teardown() is True
    assert len([str(file) for file in Path.cwd().resolve().rglob('*')]) == 1


def test_action_delete_new_files_empty_directory_new_directory(empty_path, generic_runner, mocker, touch):
    """Verify the delete_new_files() function works correctly deleting a directory starting with an empty directory."""
    os.chdir(str(empty_path))
    mocker.patch('build_magic.actions.container_destroy', return_value=True)
    # Local capture
    generic_runner.teardown = types.MethodType(actions.delete_new_files, generic_runner)
    generic_runner._existing_files = [str(file) for file in Path.cwd().resolve().rglob('*')]
    generic_runner._existing_dirs = generic_runner._existing_files
    assert len(generic_runner._existing_files) == 0
    generic_runner.execute(Macro('mkdir test1'))
    generic_runner.execute(Macro(f'{touch} test1/hello.txt'))
    assert generic_runner.teardown() is True
    assert len([str(file) for file in Path.cwd().resolve().rglob('*')]) == 0

    # Docker capture
    generic_runner.host_wd = '.'
    generic_runner.teardown = types.MethodType(actions.docker_delete_new_files, generic_runner)
    generic_runner._existing_files = [str(file) for file in Path.cwd().resolve().rglob('*')]
    generic_runner._existing_dirs = generic_runner._existing_files
    assert len(generic_runner._existing_files) == 0
    generic_runner.execute(Macro('mkdir test1'))
    generic_runner.execute(Macro(f'{touch} test1/hello.txt'))
    assert generic_runner.teardown() is True
    assert len([str(file) for file in Path.cwd().resolve().rglob('*')]) == 0


def test_action_delete_new_files_no_existing(generic_runner, mocker):
    """Test the case where the _existing_files attribute isn't set."""
    mocker.patch('build_magic.actions.container_destroy', return_value=True)
    # Local capture
    generic_runner.teardown = types.MethodType(actions.delete_new_files, generic_runner)
    assert not generic_runner.teardown()

    generic_runner._existing_files = None
    assert generic_runner.teardown() is False

    # Docker capture
    generic_runner.host_wd = '.'
    generic_runner.teardown = types.MethodType(actions.docker_delete_new_files, generic_runner)
    assert not generic_runner.teardown()

    generic_runner._existing_files = None
    assert generic_runner.teardown() is False


def test_action_delete_nested_directories(build_hashes, build_path, generic_runner, mocker, touch):
    """Test the case where there are several new nested directories added that need to be removed."""
    os.chdir(str(build_path))
    mocker.patch('build_magic.actions.container_destroy', return_value=True)

    # Local capture
    generic_runner.teardown = types.MethodType(actions.delete_new_files, generic_runner)
    files = [str(file) for file in Path.cwd().resolve().rglob('*')]
    generic_runner._existing_files = list(zip(files, build_hashes))
    dirs = []
    generic_runner._existing_dirs = dirs
    generic_runner.execute(Macro('mkdir dir1'))
    generic_runner.execute(Macro('mkdir dir2'))
    generic_runner.execute(Macro(f'mkdir dir1{os.sep}dir3'))
    generic_runner.execute(Macro(f'mkdir dir1{os.sep}dir4'))
    generic_runner.execute(Macro(f'mkdir dir1{os.sep}dir3{os.sep}dir5'))
    generic_runner.execute(Macro(f'{touch} dir1{os.sep}dir3{os.sep}dir5{os.sep}file1'))
    generic_runner.execute(Macro(f'{touch} dir1{os.sep}dir3{os.sep}dir5{os.sep}file2'))
    generic_runner.execute(Macro(f'{touch} dir1{os.sep}dir3{os.sep}file3'))
    generic_runner.execute(Macro(f'{touch} dir1{os.sep}dir4{os.sep}file4'))
    generic_runner.execute(Macro(f'{touch} dir2{os.sep}file5'))
    generic_runner.execute(Macro(f'{touch} dir2{os.sep}file6'))
    generic_runner.execute(Macro(f'{touch} dir1{os.sep}file7'))
    assert generic_runner.teardown()
    assert len([str(file) for file in Path.cwd().resolve().rglob('*')]) == 2

    # Docker capture
    generic_runner.host_wd = '.'
    generic_runner.teardown = types.MethodType(actions.docker_delete_new_files, generic_runner)
    files = [str(file) for file in Path.cwd().resolve().rglob('*')]
    generic_runner._existing_files = list(zip(files, build_hashes))
    dirs = []
    generic_runner._existing_dirs = dirs
    generic_runner.execute(Macro('mkdir dir1'))
    generic_runner.execute(Macro('mkdir dir2'))
    generic_runner.execute(Macro(f'mkdir dir1{os.sep}dir3'))
    generic_runner.execute(Macro(f'mkdir dir1{os.sep}dir4'))
    generic_runner.execute(Macro(f'mkdir dir1{os.sep}dir3{os.sep}dir5'))
    generic_runner.execute(Macro(f'{touch} dir1{os.sep}dir3{os.sep}dir5{os.sep}file1'))
    generic_runner.execute(Macro(f'{touch} dir1{os.sep}dir3{os.sep}dir5{os.sep}file2'))
    generic_runner.execute(Macro(f'{touch} dir1{os.sep}dir3{os.sep}file3'))
    generic_runner.execute(Macro(f'{touch} dir1{os.sep}dir4{os.sep}file4'))
    generic_runner.execute(Macro(f'{touch} dir2{os.sep}file5'))
    generic_runner.execute(Macro(f'{touch} dir2{os.sep}file6'))
    generic_runner.execute(Macro(f'{touch} dir1{os.sep}file7'))
    assert generic_runner.teardown()
    assert len([str(file) for file in Path.cwd().resolve().rglob('*')]) == 2


def test_action_delete_existing_nested_directories(generic_runner, mocker, nested_path, touch):
    """Test the case where a single file needs to be cleaned up in a directory hierarchy."""
    os.chdir(str(nested_path))
    mocker.patch('build_magic.actions.container_destroy', return_value=True)

    # Local capture
    generic_runner.teardown = types.MethodType(actions.delete_new_files, generic_runner)
    files = []
    generic_runner._existing_files = files
    dirs = [str(directory) for directory in Path.cwd().resolve().rglob('*')]
    generic_runner._existing_dirs = dirs
    generic_runner.execute(Macro(f'{touch} dir1level1/dir2level2/dir4level3/file'))
    assert generic_runner.teardown()
    for file in Path.cwd().resolve().glob('*'):
        assert str(file) in dirs

    # Docker capture
    generic_runner.host_wd = '.'
    generic_runner.teardown = types.MethodType(actions.docker_delete_new_files, generic_runner)
    files = []
    generic_runner._existing_files = files
    dirs = [str(directory) for directory in Path.cwd().resolve().rglob('*')]
    generic_runner._existing_dirs = dirs
    generic_runner.execute(Macro(f'{touch} dir1level1/dir2level2/dir4level3/file'))
    assert generic_runner.teardown()
    for file in Path.cwd().resolve().glob('*'):
        assert str(file) in dirs


def test_action_delete_dir_ignore_git(build_path, git_path, generic_runner, mocker, touch):
    """Test the case where the a new file added to a .git directory isn't deleted."""
    os.chdir(str(build_path))
    mocker.patch('build_magic.actions.container_destroy', return_value=True)

    # Local capture
    generic_runner.teardown = types.MethodType(actions.delete_new_files, generic_runner)
    files = [str(file) for file in Path.cwd().resolve().rglob('*')]
    generic_runner._existing_files = list(zip(files, [None] * len(files)))
    generic_runner.execute(Macro(f'{touch} .git/refs/file3'))
    generic_runner.execute(Macro(f'{touch} file3.txt'))
    assert generic_runner.teardown()
    assert Path().cwd().joinpath('.git/refs/file3').exists() is True
    assert Path().cwd().joinpath('file3.txt').exists() is False

    # Docker capture
    generic_runner.host_wd = '.'
    generic_runner.teardown = types.MethodType(actions.docker_delete_new_files, generic_runner)
    files = [str(file) for file in Path.cwd().resolve().rglob('*')]
    generic_runner._existing_files = list(zip(files, [None] * len(files)))
    generic_runner.execute(Macro(f'{touch} .git/refs/file3'))
    generic_runner.execute(Macro(f'{touch} file3.txt'))
    assert generic_runner.teardown()
    assert Path().cwd().joinpath('.git/refs/file3').exists() is True
    assert Path().cwd().joinpath('file3.txt').exists() is False


def test_action_backup_dir(build_path, generic_runner):
    """Verify the backup_dir() function works correctly."""
    os.chdir(str(build_path))
    generic_runner.provision = types.MethodType(actions.backup_dir, generic_runner)
    assert generic_runner.provision()
    assert build_path.joinpath(actions.BACKUP_PATH).exists()
    assert build_path.joinpath(actions.BACKUP_PATH).is_dir()
    assert len(list(build_path.joinpath(actions.BACKUP_PATH).iterdir())) == 2


def test_action_backup_dir_empty_directory(empty_path, generic_runner):
    """Test the case where backup_dir() is called on an empty directory."""
    os.chdir(str(empty_path))
    generic_runner.provision = types.MethodType(actions.backup_dir, generic_runner)
    assert generic_runner.provision()
    assert empty_path.joinpath(actions.BACKUP_PATH).exists()
    assert empty_path.joinpath(actions.BACKUP_PATH).is_dir()
    assert len(list(empty_path.joinpath(actions.BACKUP_PATH).iterdir())) == 0


def test_action_backup_dir_error(build_path, generic_runner, mocker):
    """Test the case where backup_dir() raises an error."""
    mocker.patch('shutil.copytree', side_effect=PermissionError)
    os.chdir(str(build_path))
    generic_runner.provision = types.MethodType(actions.backup_dir, generic_runner)
    assert not generic_runner.provision()


def test_action_backup_dir_backup_exists(build_path, generic_runner):
    """Test the case where a backup directory already exists when backup_dir() is called."""
    os.chdir(str(build_path))
    generic_runner.provision = types.MethodType(actions.backup_dir, generic_runner)
    backup = build_path.joinpath(actions.BACKUP_PATH)
    backup.mkdir()
    file = backup / 'file1.txt'
    file.write_text('test')

    assert generic_runner.provision()
    assert build_path.joinpath(actions.BACKUP_PATH).exists()
    assert build_path.joinpath(actions.BACKUP_PATH).is_dir()
    assert len(list(build_path.joinpath(actions.BACKUP_PATH).iterdir())) == 2


# def test_action_restore_from_backup(backup_path, build_path, generic_runner):
#     """Verify the restore_from_backup() function works correctly."""
#     os.chdir(str(build_path))
#     generic_runner.teardown = types.MethodType(actions.restore_from_backup, generic_runner)

#     # Modify a file and make sure the modified file isn't kept.
#     build_path.joinpath('file1.txt').write_text('temp')

#     assert generic_runner.teardown()
#     for file in build_path.iterdir():
#         assert file.read_text() in ('hello', 'world')
#     assert not build_path.parent.joinpath(actions.TEMP_PATH).exists()


# def test_action_restore_from_backup_no_backup(build_path, generic_runner):
#     """Test the case where restore_from_backup() does nothing because the backup path doesn't exist."""
#     os.chdir(str(build_path))
#     generic_runner.teardown = types.MethodType(actions.restore_from_backup, generic_runner)
#     assert not generic_runner.teardown()


# def test_action_restore_from_backup_from_empty_directory(build_path, generic_runner):
#     """Test the case where the backup of the working directory is clean."""
#     os.chdir(str(build_path))
#     generic_runner.teardown = types.MethodType(actions.restore_from_backup, generic_runner)
#     backup = build_path.joinpath(actions.BACKUP_PATH)
#     backup.mkdir()

#     assert len([file for file in build_path.iterdir() if file.is_file()]) == 2
#     assert generic_runner.teardown()
#     assert len(list(build_path.iterdir())) == 0


# def test_action_restore_from_backup_to_empty_directory(backup_path, build_path, generic_runner):
#     """Test the case where the backup restores to a clean working directory."""
#     os.chdir(str(build_path))
#     generic_runner.teardown = types.MethodType(actions.restore_from_backup, generic_runner)
#     build_path.joinpath('file1.txt').unlink()
#     build_path.joinpath('file2.txt').unlink()

#     assert len([file for file in build_path.iterdir() if file.is_file()]) == 0
#     assert generic_runner.teardown()
#     assert len(list(build_path.iterdir())) == 2


# def test_action_restore_from_backup_error(backup_path, build_path, generic_runner, mocker):
#     """Test the case where an error occurs when restoring from a backup."""
#     os.chdir(str(build_path))
#     mocker.patch('shutil.move', side_effect=PermissionError)
#     generic_runner.teardown = types.MethodType(actions.restore_from_backup, generic_runner)
#     assert not generic_runner.teardown()


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
    assert exek.call_count == 3
    assert exek.call_args[0] == ('find $PWD -type d',)
    assert generic_runner._existing_files == [
        ('/build-magic/file1.txt', '7c211433f02071597741e6ff5a8ea34789abbf43'),
        ('/build-magic/file2.txt', 'aaf4c61ddcc5e8a2dabede0f3b482cd9aea9434d'),
    ]
    assert generic_runner._existing_dirs == ['']


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
    generic_runner.working_directory = '/my/working/directory'
    assert generic_runner.provision()
    assert exek.call_count == 3
    assert exek.call_args[0] == ('find /my/working/directory -type d',)
    assert generic_runner._existing_files == [
        ('/my/working/directory/file1.txt', '7c211433f02071597741e6ff5a8ea34789abbf43'),
        ('/my/working/directory/file2.txt', 'aaf4c61ddcc5e8a2dabede0f3b482cd9aea9434d'),
    ]
    assert generic_runner._existing_dirs == ['']


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
    assert exek.call_count == 4
    assert exek.call_args[0] == ('find $PWD -type d',)
    assert generic_runner._existing_files == [
        ('/build-magic/file1.txt', None),
        ('/build-magic/file2.txt', None),
    ]
    assert generic_runner._existing_dirs == ['']


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
    assert exek.call_count == 3
    assert exek.call_args[0] == ('dir /AD /B /ON /S',)
    assert generic_runner._existing_files == [
        ('C:\\Users\\user\\build-magic\\file1.txt', None),
        ('C:\\Users\\user\\build-magic\\file2.txt', None),
    ]
    assert generic_runner._existing_dirs == ['']


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
    generic_runner.working_directory = 'C:\\Users\\user\\my\\project'
    assert generic_runner.provision()
    assert exek.call_count == 3
    assert exek.call_args[0] == ('dir C:\\Users\\user\\my\\project /AD /B /ON /S',)
    assert generic_runner._existing_files == [
        ('C:\\Users\\user\\my\\project\\file1.txt', None),
        ('C:\\Users\\user\\my\\project\\file2.txt', None),
    ]
    assert generic_runner._existing_dirs == ['']


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
    assert not hasattr(generic_runner, '_existing_dirs')


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
    assert exek.call_count == 4
    assert exek.call_args[0] == ('dir /AD /B /ON /S',)
    assert generic_runner._existing_files == [
        ('C:\\Users\\user\\build-magic\\file1.txt', None),
        ('C:\\Users\\user\\build-magic\\file2.txt', None),
    ]
    assert generic_runner._existing_dirs == ['']


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
    generic_runner.working_directory = 'C:\\Users\\user\\my\\project'
    assert generic_runner.provision()
    assert exek.call_count == 4
    assert exek.call_args[0] == ('dir C:\\Users\\user\\my\\project /AD /B /ON /S',)
    assert generic_runner._existing_files == [
        ('C:\\Users\\user\\my\\project\\file1.txt', None),
        ('C:\\Users\\user\\my\\project\\file2.txt', None),
    ]
    assert generic_runner._existing_dirs == ['']


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
    assert not hasattr(generic_runner, '_existing_dirs')


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
    assert exek.call_count == 3
    assert exek.call_args[0] == ('find $PWD -type d',)
    assert generic_runner._existing_files == []
    assert generic_runner._existing_dirs == ['']


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
    assert exek.call_count == 3
    assert exek.call_args[0] == ('dir /AD /B /ON /S',)
    assert generic_runner._existing_files == []
    assert generic_runner._existing_dirs == ['']


def test_action_remote_capture_dir_nested_directories(generic_runner, mocker):
    """Verify the remote_capture_dir() function works correctly with new nested directories."""
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
                        '03de6c570bfe24bfc328ccd7ca46b76eadaf4334  /build-magic/test/file3.txt',
                    ],
                    channel=MagicMock(recv_exit_status=lambda: 0),
                ),
                MagicMock(readlines=lambda: ['']),
            ),
            (
                None,
                MagicMock(
                    readlines=lambda: [
                        '/build-magic/test',

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
    assert exek.call_args[0] == ('find $PWD -type d',)
    assert generic_runner._existing_files == [
        ('/build-magic/file1.txt', '7c211433f02071597741e6ff5a8ea34789abbf43'),
        ('/build-magic/file2.txt', 'aaf4c61ddcc5e8a2dabede0f3b482cd9aea9434d'),
        ('/build-magic/test/file3.txt', '03de6c570bfe24bfc328ccd7ca46b76eadaf4334'),
    ]
    assert generic_runner._existing_dirs == ['/build-magic/test']


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
            # Get directories.
            (
                None,
                MagicMock(readlines=lambda: ['']),
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
    assert exek.call_count == 4
    assert exek.call_args[0] == ('rm /home/user/build-magic/myfiles.tar.gz /home/user/build-magic/other_file.txt',)


def test_action_remote_delete_files_ignore_git(generic_runner, mocker):
    """Verify the remote_delete_files() function works correctly and doesn't touch the .git directory."""
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
                        '3a19a60069b50fc489030d9e8c872f03d63c9278  /home/user/build-magic/.git/HEAD',
                        'aaf4c61ddcc5e8a2dabede0f3b482cd9aea9434d  /home/user/build-magic/file2.txt',
                        'da39a3ee5e6b4b0d3255bfef95601890afd80709  /home/user/build-magic/.git/refs/test1',
                    ],
                    channel=MagicMock(recv_exit_status=lambda: 0),
                ),
                MagicMock(readlines=lambda: ['']),
            ),
            # Get directories.
            (
                None,
                MagicMock(
                    readlines=lambda: [
                        '/home/user/build-magic/.git',
                        '/home/user/build-magic/.git/refs',
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
    ]
    assert generic_runner.teardown()
    assert exek.call_count == 4
    assert exek.call_args[0] == ('rm /home/user/build-magic/file2.txt',)


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
            # Get directories.
            (
                None,
                MagicMock(readlines=lambda: ['']),
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
    assert exek.call_count == 5
    assert exek.call_args[0] == ('rm /home/user/build-magic/myfiles.tar.gz /home/user/build-magic/other_file.txt',)


def test_action_remote_delete_files_not_shasum_ignore_git(generic_runner, mocker):
    """Verify files are deleted correctly when there's no shasum command and the .git directory is untouched."""
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
                        '/home/user/build-magic/.git/HEAD',
                        '/home/user/build-magic/file2.txt',
                        '/home/user/build-magic/.git/refs/test1',
                    ],
                    channel=MagicMock(recv_exit_status=lambda: 0),
                ),
                MagicMock(readlines=lambda: ['']),
            ),
            # Get directories.
            (
                None,
                MagicMock(
                    readlines=lambda: [
                        '/home/user/build-magic/.git',
                        '/home/user/build-magic/.git/refs',
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
    ]
    assert generic_runner.teardown()
    assert exek.call_count == 5
    assert exek.call_args[0] == ('rm /home/user/build-magic/file2.txt',)


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
            # Get directories.
            (
                None,
                MagicMock(readlines=lambda: ['']),
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
    assert exek.call_args[0] == ('del /f /s /q C:\\build-magic\\myfiles.tar.gz C:\\build-magic\\other_file.txt',)


def test_action_remote_delete_files_windows_uname_ignore_git(generic_runner, mocker):
    """Verify Windows files via uname are deleted correctly and the .git directory is untouched."""
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
                        'C:\\build-magic\\.git\\HEAD',
                        'C:\\build-magic\\file2.txt',
                        'C:\\build-magic\\.git\\refs\\test1',
                    ],
                    channel=MagicMock(recv_exit_status=lambda: 0),
                ),
                MagicMock(readlines=lambda: ['']),
            ),
            # Get directories.
            (
                None,
                MagicMock(
                    readlines=lambda: [
                        'C:\\build-magic\\.git',
                        'C:\\build-magic\\.git\\refs',
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
    ]
    assert generic_runner.teardown()
    assert exek.call_count == 4
    assert exek.call_args[0] == ('del /f /s /q C:\\build-magic\\file2.txt',)


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
            # Get directories.
            (
                None,
                MagicMock(readlines=lambda: ['']),
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
    assert exek.call_count == 5
    assert exek.call_args[0] == ('del /f /s /q C:\\build-magic\\myfiles.tar.gz C:\\build-magic\\other_file.txt',)


def test_action_remote_delete_files_windows_os_ignore_git(generic_runner, mocker):
    """Verify Windows files via OS call are deleted correctly and the .git directory is untouched."""
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
                        'C:\\build-magic\\.git\\HEAD',
                        'C:\\build-magic\\file2.txt',
                        'C:\\build-magic\\.git\\refs\\test1',
                    ],
                    channel=MagicMock(recv_exit_status=lambda: 0),
                ),
                MagicMock(readlines=lambda: ['']),
            ),
            # Get directories.
            (
                None,
                MagicMock(
                    readlines=lambda: [
                        'C:\\build-magic\\.git',
                        'C:\\build-magic\\.git\\refs',
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
    ]
    assert generic_runner.teardown()
    assert exek.call_count == 5
    assert exek.call_args[0] == ('del /f /s /q C:\\build-magic\\file2.txt',)


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


def test_action_remote_delete_files_no_existing_files(generic_runner, mocker):
    """Test the case where _existing_files isn't set."""
    mocker.patch(
        'paramiko.SSHClient.exec_command',
        side_effect=(
            # uname call.
            (
                None,
                MagicMock(
                    readlines=lambda: ['Darwin'],
                    channel=MagicMock(recv_exit_status=lambda: 1),
                ),
                MagicMock(readlines=lambda: ['Command not found.']),
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
            # Get directories.
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
    assert exek.call_args[0] == ('find $PWD -type d',)


def test_action_remote_delete_files_empty_directory(generic_runner, mocker):
    """Test the case where no files are in the working directory."""
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
                    readlines=lambda: [],
                    channel=MagicMock(recv_exit_status=lambda: 0),
                ),
                MagicMock(readlines=lambda: ['']),
            ),
            # Get directories.
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
    generic_runner._existing_files = []
    assert generic_runner.teardown()
    assert exek.call_count == 3


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
            # Get directories.
            (
                None,
                MagicMock(readlines=lambda: ['']),
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
    assert exek.call_count == 4
    assert exek.call_args[0] == ('rm /home/user/build-magic/myfiles.tar.gz /home/user/build-magic/other_file.txt',)


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
            # Get directories.
            (
                None,
                MagicMock(readlines=lambda: ['']),
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
    assert exek.call_args[0] == ('del /f /s /q C:\\build-magic\\myfiles.tar.gz C:\\build-magic\\other_file.txt',)


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
            # Get directories.
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
    assert exek.call_args[0] == ('find $PWD -type d',)


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
            # Get directories.
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
    assert exek.call_args[0] == ('find $PWD -type d',)


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
            # Get directories.
            (
                None,
                MagicMock(readlines=lambda: ['']),
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
    assert exek.call_args[0] == ('del /f /s /q C:\\build-magic\\copy1.txt',)


def test_action_remote_delete_files_remove_directories(generic_runner, mocker):
    """Verify remote directories are correctly identified for removal."""
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
                        'da39a3ee5e6b4b0d3255bfef95601890afd80709  /home/user/build-magic/dir1/dir3/dir5/file1',
                        'aaf4c61ddcc5e8a2dabede0f3b482cd9aea9434d  /home/user/build-magic/dir1/dir3/dir5/file2',
                        '7c4a8d09ca3762af61e59520943dc26494f8941b  /home/user/build-magic/dir1/dir3/file3',
                        'c7839accb3e7c2ccffa0174006bd0b446f3336fc  /home/user/build-magic/dir1/dir4/file4',
                        '25a32bfc3309d1fea5cc59a1a0c42f2ab0ea05b6  /home/user/build-magic/dir2/file5',
                        'cac55f635b3717f481eb15db3e85f5d2c770c90a  /home/user/build-magic/dir2/file6',
                        'd9507fb92bced1be0813817769628091573e5e75  /home/user/build-magic/dir1/file7',
                    ],
                    channel=MagicMock(recv_exit_status=lambda: 0),
                ),
                MagicMock(readlines=lambda: ['']),
            ),
            # Get directories.
            (
                None,
                MagicMock(
                    readlines=lambda: [
                        '/home/user/build-magic/dir1',
                        '/home/user/build-magic/dir2',
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
            # rm directories.
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
    generic_runner._existing_files = []
    generic_runner._existing_dirs = ['/home/user/build-magic']
    assert generic_runner.teardown()
    assert exek.call_count == 5
    assert exek.call_args[0] == ('rm -rf /home/user/build-magic/dir2 /home/user/build-magic/dir1',)
