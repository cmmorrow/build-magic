"""This module hosts Actions and functions to dynamically bind to CommandRunner classes."""

import hashlib
import os
import pathlib
import re
import shutil
import subprocess

import docker
from docker.errors import APIError, ImageLoadError
import vagrant


LOCAL = 'local'
REMOTE = 'remote'
VAGRANT = 'vagrant'
DOCKER = 'docker'

SETUP_METHOD = 'provision'
TEARDOWN_METHOD = 'teardown'

BACKUP_PATH = '.build_magic'
TEMP_PATH = '.temp_backup'

DEFAULT_METHOD = 'null'

DARWIN = 'Darwin'
LINUX = 'Linux'
WINDOWS = 'Windows'


def _execute_command(client, cmd):
    """Helper function for executing remote commands.

    :param paramiko.SSHClient client: The SSHClient object to use for executing the command.
    :param str cmd: The shell command to execute.
    :rtype: tuple
    :return: A tuple of paramiko.channel.ChannelFile object representing stdin, stdout, and stderr.
    """
    return client.exec_command(cmd)


def _get_remote_os(client):
    """Attempt to get the operating system of a remote machine.

    :param paramiko.SSHClient client: The SSHClient object to use for executing the command.
    :rtype: str|None
    :return: The operating system of the remote machine or None if detection fails.
    """
    system = None
    stdin, stdout, stderr = _execute_command(client, 'uname')
    if stdout.channel.recv_exit_status() == 0:
        os_ = stdout.readlines()[0].strip()
        if os_ in (LINUX, DARWIN):
            system = os_
        elif os_.startswith(WINDOWS):
            system = WINDOWS
    else:
        # Check if we're connecting to Windows.
        stdin, stdout, stderr = _execute_command(client, '%OS%')
        os_ = stdout.readlines()[0].strip()
        if os_ == 'Windows_NT':
            system = WINDOWS
    return system


def _get_files_and_hashes(client, directory=''):
    """Helper function for getting file names and their corresponding SHA1 hashes from a unix-like file system.

    :param paramiko.SSHClient client: The SSHClient object to use for executing the command.
    :param str directory: The directory to recursively fetch file names and hashes from.
    :rtype: paramiko.channel.ChannelFile
    :return: The resulting stdout object from the executed command.
    """
    path = directory or '$PWD'
    cmd = f'find {path} -type f | xargs shasum {path}/*'
    stdin, stdout, stderr = _execute_command(client, cmd)
    return stdout


def _get_files_unix(client, working_directory=''):
    """Helper function for getting a list of files on a remote unix-like file system.

    :param paramiko.SSHClient client: The SSHClient object to use for executing the command.
    :param str working_directory: The directory to recursively fetch file names from.
    :rtype: tuple[paramiko.channel, list[str]]
    :return: A tuple of the SSH channel and each line of the stdout object from the executed command as a list.
    """
    path = working_directory or '$PWD'
    cmd = f'find {path} -type f'
    stdin, stdout, stderr = _execute_command(client, cmd)
    return stdout.channel, [f for f in stdout.readlines()]


def _get_files_windows(client, working_directory=''):
    """Helper function for getting a list of files on a remote Windows system.

    :param paramiko.SSHClient client: The SSHClient object to use for executing the command.
    :param str working_directory: The directory to recursively fetch file names from.
    :rtype: tuple[paramiko.channel, list[str]]
    :return: A tuple of the SSH channel and each line of the stdout object from the executed command as a list.
    """
    path = working_directory + ' ' if working_directory else working_directory
    cmd = f'dir {path}/a-D /S /B'
    stdin, stdout, stderr = _execute_command(client, cmd)
    return stdout.channel, [f for f in stdout.readlines()]


def _get_directories_unix(client, working_directory=''):
    """Helper function for getting a list of directories on a remote unix-like file system.

    :param paramiko.SSHClient client: The SSHClient object to use for executing the command.
    :param str working_directory: The directory to recursively fetch directory names from.
    :rtype: tuple[paramiko.channel, list[str]]
    :return: A tuple of the SSH channel and each line of the stdout object from the executed command as a list.
    """
    path = working_directory or '$PWD'
    cmd = f'find {path} -type d'
    stdin, stdout, stderr = _execute_command(client, cmd)
    return stdout.channel, [d for d in stdout.readlines() if d != path]


def _get_directories_windows(client, working_directory=''):
    """Helper function for getting a list of directories on a remote Windows file system.

    :param paramiko.SSHClient client: The SSHClient object to use for executing the command.
    :param str working_directory: The directory to recursively fetch directory names from.
    :rtype: tuple[paramiko.channel, list[str]]
    :return: A tuple of the SSH channel and each line of the stdout object from the executed command as a list.
    """
    path = working_directory + ' ' if working_directory else working_directory
    cmd = f'dir {path}/AD /B /ON /S'
    stdin, stdout, stderr = _execute_command(client, cmd)
    return stdout.channel, [d for d in stdout.readlines()]


def _parse_files(file_list):
    """Helper function to parse a list of files into a tuple for storage.

    :param list[str] file_list: A list of file names to parse and format.
    :rtype: list[str]
    :return: A list of tuples where the first value is the file name and the second value is None.
    """
    return [(file.strip(), None) for file in file_list if file]


def _parse_directories(dir_list):
    """Helper function for parsing and cleaning a list of directories for analysis.

    :param list[str] dir_list: A list of directories to parse.
    :rtype: list[str]
    :return: The cleaned up list of directories.
    """
    return [line for line in dir_list if line is not None]


def _get_local_files_and_directories(files):
    """Helper function for getting hashes of local files, as well as subdirectories.

    :param files: Every "file" under a directory.
    :rtype: tuple[tuple[str, str], str]
    :return: A tuple of the file hashes and subdirectories.
    """
    file_hashes, dirs = [], []
    for file in sorted(files):
        try:
            file_hashes.append((str(file), hashlib.sha1(pathlib.Path(file).read_bytes()).hexdigest()))
        except IsADirectoryError:
            dirs.append(str(file))
    return file_hashes, dirs


# def _clear_directory(directory):
#     """
#
#     :param pathlib.Path directory:
#     :return:
#     """
#     for file in directory.iterdir():
#         if file.is_dir():
#             if len(list(file.iterdir())) > 0:
#                 _clear_directory(directory)
#             else:
#                 file.rmdir()
#         else:
#             file.unlink()


class Action:
    """An Action is used to dynamically define the setup and teardown process for a CommandRunner.
    At a minimum, a Default action is called to specify and dynamically bind the setup and teardown methods.
    New functions can be added to Action classes to modify the setup and teardown behavior of a CommandRunner.
    Additionally, commands can be added as macro prefixes and suffixes for each CommandRunner.

    The mapping class attribute is a dictionary with keys for the setup and teardown methods.
    Each key then has a dictionary of key/value pairs, where the key the CommandRunner name,
    and the value is the function name to dynamically bind to the setup or teardown method. For example,

        mapping = {
            'provision': {
                'local': 'copy_from',
                'remote': 'copy_to',
            }
        }

    will map the function "copy_from()" to the "provision()" method of the Local CommandRunner class
    and the function "copy_from()" to the "provision()" method of the Remote CommandRunner class.

    The add_prefix and add_suffix class attributes are dictionaries where the key is the CommandRunner name
    and the value is the function name to dynamically add as a prefix or suffix to each macro being executed
    by the corresponding CommandRunner class. For example,

        add_prefix = {
            'vagrant': 'cd /',
        }

    will add the command "cd /" as a prefix to each command executed by the Vagrant CommandRunner class.
    """

    # Class attribute that maps a command runner to a command that will be added before each executed command.
    add_prefix = {}

    # Class attribute that maps a command runner to a command that will be added after each executed command.
    add_suffix = {}

    # Class attribute that defines a mapping between command runners and the functions to run for setup and teardown.
    mapping = {
        SETUP_METHOD: {},
        TEARDOWN_METHOD: {},
    }


class Default(Action):
    """The default action which executes commands in an environment individually."""

    mapping = {
        SETUP_METHOD: {
            LOCAL: DEFAULT_METHOD,
            REMOTE: DEFAULT_METHOD,
            DOCKER: 'container_up',
            VAGRANT: 'vm_up',
        },
        TEARDOWN_METHOD: {
            LOCAL: DEFAULT_METHOD,
            REMOTE: DEFAULT_METHOD,
            DOCKER: 'container_destroy',
            VAGRANT: 'vm_destroy',
        },
    }

    add_prefix = {
        VAGRANT: 'cd /vagrant;',
    }


class Cleanup(Action):
    """Action for deleting any files created while executing a Stage."""

    mapping = {
        SETUP_METHOD: {
            LOCAL: 'capture_dir',
            REMOTE: 'remote_capture_dir',
            DOCKER: 'docker_capture_dir',
            VAGRANT: 'vm_up',
        },
        TEARDOWN_METHOD: {
            LOCAL: 'delete_new_files',
            REMOTE: 'remote_delete_files',
            DOCKER: 'docker_delete_new_files',
            VAGRANT: 'vm_destroy',
        },
    }

    add_prefix = {
        VAGRANT: 'cd /vagrant;',
    }


# class Restore(Action):
#     """Action for restoring the working directory after executing a Stage."""
#
#     mapping = {
#         SETUP_METHOD: {
#             LOCAL: 'backup_dir',
#             DOCKER: 'backup_dir',
#             VAGRANT: 'vm_up',
#         },
#         TEARDOWN_METHOD: {
#             LOCAL: 'restore_from_backup',
#             DOCKER: 'restore_from_backup',
#             VAGRANT: 'vm_destroy',
#         },
#     }
#
#     add_prefix = {
#         VAGRANT: 'cd /vagrant;',
#     }


class Persist(Action):
    """Action for starting an environment but doesn't teardown."""

    mapping = {
        SETUP_METHOD: {
            LOCAL: DEFAULT_METHOD,
            REMOTE: DEFAULT_METHOD,
            DOCKER: 'container_up',
            VAGRANT: 'vm_up',
        },
        TEARDOWN_METHOD: {
            LOCAL: DEFAULT_METHOD,
            REMOTE: DEFAULT_METHOD,
            DOCKER: DEFAULT_METHOD,
            VAGRANT: DEFAULT_METHOD,
        },
    }

    add_prefix = {
        VAGRANT: 'cd /vagrant;',
    }


def null(self):
    """Basic No-op."""
    return True


def vm_up(self):
    """Starts up a VM according to the corresponding Vagrantfile."""
    self._vm = vagrant.Vagrant()
    try:
        self._vm.up()
    except subprocess.CalledProcessError as err:
        print(str(err))
        self.teardown()
        return False
    return True


def vm_destroy(self):
    """Destroys the VM used for executing commands."""
    if hasattr(self, '_vm') and isinstance(self._vm, vagrant.Vagrant):
        try:
            self._vm.destroy()
        except subprocess.CalledProcessError as err:
            print(str(err))
            return False
    return True


def capture_dir(self):
    """Capture a list of all the files and their MD5 hashes in a directory."""
    try:
        pwd = pathlib.Path(self.working_directory).resolve()
        matches = pwd.rglob('*')
        self._existing_files, self._existing_dirs = _get_local_files_and_directories(matches)
    except:
        return False
    return True


def delete_new_files(self):
    """Deletes all files not previously captured."""
    result = False
    if hasattr(self, '_existing_files') and isinstance(self._existing_files, list):
        if len(self._existing_files) > 0:
            files, hashes = zip(*self._existing_files)
            pwd = pathlib.Path(self.working_directory).resolve()
            current = []
            for file in sorted(pwd.rglob('*')):
                try:
                    current.append((file, hashlib.sha1(pathlib.Path(file).read_bytes()).hexdigest()))
                except IsADirectoryError:
                    continue
                # Handle a Windows specific case where a PermissionError is raised instead of IsADirectoryError.
                except PermissionError as error:
                    if os.sys.platform == 'win32' and file.is_dir():
                        continue
                    else:
                        raise error
            _, new_hashes = zip(*current)
            for file, hash_ in current:
                # Don't delete anything in the .git directory.
                if re.search(r'\.git', str(file)):
                    continue
                # Remove any new files.
                if str(file) not in files and hash_ not in hashes:
                    os.remove(file)
                    continue
                # Remove any files copied from existing files.
                elif hash_ in hashes and (str(file), hash_) not in self._existing_files and new_hashes.count(hash_) > 1:
                    os.remove(file)
                    continue
            result = True
    if hasattr(self, '_existing_dirs') and isinstance(self._existing_dirs, list):
        pwd = pathlib.Path(self.working_directory).resolve()
        for file in sorted(pwd.rglob('*'), reverse=True):
            # Don't delete anything in the .git directory.
            if re.search(r'\.git', str(file)):
                continue
            if file.is_dir() and file not in self._existing_dirs:
                try:
                    os.rmdir(file)
                except OSError:
                    continue
        result = True
    return result


def docker_capture_dir(self):
    """Capture a list of all the files and their MD5 hashes in the host directory."""
    try:
        pwd = pathlib.Path(self.host_wd).resolve()
        matches = pwd.rglob('*')
        self._existing_files, self._existing_dirs = _get_local_files_and_directories(matches)
    except:
        return False
    return container_up(self)


def docker_delete_new_files(self):
    """Deletes all files not previously captured in the host directory."""
    result = False
    if hasattr(self, '_existing_files') and isinstance(self._existing_files, list):
        if len(self._existing_files) > 0:
            files, hashes = zip(*self._existing_files)
            pwd = pathlib.Path(self.host_wd).resolve()
            current = []
            for file in sorted(pwd.rglob('*')):
                try:
                    current.append((file, hashlib.sha1(pathlib.Path(file).read_bytes()).hexdigest()))
                except IsADirectoryError:
                    continue
                # Handle a Windows specific case where a PermissionError is raised instead of IsADirectoryError.
                except PermissionError as error:
                    if os.sys.platform == 'win32' and file.is_dir():
                        continue
                    else:
                        raise error
            _, new_hashes = zip(*current)
            for file, hash_ in current:
                # Don't delete anything in the .git directory.
                if re.search(r'\.git', str(file)):
                    continue
                # Remove any new files.
                if str(file) not in files and hash_ not in hashes:
                    os.remove(file)
                    continue
                # Remove any files copied from existing files.
                elif hash_ in hashes and (str(file), hash_) not in self._existing_files and new_hashes.count(hash_) > 1:
                    os.remove(file)
                    continue
            result = True
    if hasattr(self, '_existing_dirs') and isinstance(self._existing_dirs, list):
        pwd = pathlib.Path(self.host_wd).resolve()
        for file in sorted(pwd.rglob('*'), reverse=True):
            # Don't delete anything in the .git directory.
            if re.search(r'\.git', str(file)):
                continue
            if file.is_dir() and file not in self._existing_dirs:
                try:
                    os.rmdir(file)
                except OSError:
                    continue
        result = True
    container_res = container_destroy(self)
    return all([result, container_res])


def backup_dir(self):
    """Creates a backup of the working directory."""
    wd = pathlib.Path(self.working_directory).resolve()
    backup = wd / BACKUP_PATH
    try:
        if backup.exists():
            shutil.rmtree(backup)
        shutil.copytree(wd, backup)
    except (PermissionError, Exception):
        return False
    return True


def restore_from_backup(self):
    """Restore from the backup directory and delete it."""
    wd = pathlib.Path(self.working_directory).resolve()
    backup = wd / BACKUP_PATH
    if backup.exists():
        try:
            temp = wd.parent / TEMP_PATH
            shutil.move(wd, temp)
            shutil.copytree(temp / BACKUP_PATH, wd)
            shutil.rmtree(temp)
            return True
        except (PermissionError, Exception):
            return False
    else:
        return False


# def remote_backup_dir(self):
#     """Create a backup directory on a remote file system."""
#     wd = pathlib.Path(self.working_directory).resolve()
#     backup = wd / BACKUP_PATH
#     client = self.connect()
#     cmd = 'uname'
#     # Try to get the OS of the remote system.
#     stdin, stdout, stderr = client.exec_command(cmd)
#     if stdout.channel.recv_exit_status() == 0:
#         stdin, stdout, stderr = client.exec_command(f'cd {str(wd)}')
#         if stdout.readlines()[0] in ('Linux', 'Darwin'):
#             stdin, stdout, stderr = client.exec_command(f'ls {str(backup)}')
#             if stdout.channel.recv_exit_status() != 0:
#                 stdin, stdout, stderr = client.exec_command(f'rm -R -f {str(backup)}')
#             stdin, stdout, stderr = client.exec_command(f'mkdir {str(backup)}')
#             stdin, stdout, stderr = client.exec_command(f'cp -R * {str(backup)}')
#         elif stdout.readlines()[0].startswith('Windows'):
#             stdin, stdout, stderr = client.exec_command(f'ls {str(backup)}')
#             if stdout.channel.recv_exit_status() != 0:
#                 stdin, stdout, stderr = client.exec_command(f'del /q {str(backup)}')
#             stdin, stdout, stderr = client.exec_command(f'mkdir {str(backup)}')
#             stdin, stdout, stderr = client.exec_command(f'xcopy /y * {str(backup)}')
#         else:
#             return False
#     else:
#         # Check if we're connecting to Windows.
#         cmd = '%OS%'
#         stdin, stdout, stderr = client.exec_command(cmd)
#         if stdout.readlines()[0] == 'Windows_NT':
#             stdin, stdout, stderr = client.exec_command(f'cd {str(wd)}')
#             stdin, stdout, stderr = client.exec_command(f'ls {str(backup)}')
#             if stdout.channel.recv_exit_status() != 0:
#                 stdin, stdout, stderr = client.exec_command(f'del /q {str(backup)}')
#             stdin, stdout, stderr = client.exec_command(f'mkdir {str(backup)}')
#             stdin, stdout, stderr = client.exec_command(f'xcopy /y * {str(backup)}')
#         else:
#             return False
#     return True


def remote_restore_from_backup(self):
    """Restore from a backup directory on a remote file system."""


def remote_capture_dir(self):
    """Capture a list of all the files in a directory on a remote system."""
    client = self.connect()

    # Try to get the OS of the remote system.
    system = _get_remote_os(client)
    if not system:
        # OS type isn't supported yet.
        return False

    if system != WINDOWS:
        # Try to get the filename and SHA1 hashes of the remote working directory.
        stdout = _get_files_and_hashes(client, self.working_directory)

        if stdout.channel.recv_exit_status() == 0:
            existing = []
            for line in stdout.readlines():
                if line:
                    hash_, file = tuple(line.split('  '))
                    existing.append((file, hash_))
                else:
                    continue
            self._existing_files = existing
        # If trying to get the hashes fails, just use the filenames.
        else:
            _, files = _get_files_unix(client, self.working_directory)
            self._existing_files = _parse_files(files)

        # Try to get the sub-directories of the remote working directory.
        _, dirs = _get_directories_unix(client, self.working_directory)
        self._existing_dirs = _parse_directories(dirs)
    elif system == WINDOWS:
        channel, files = _get_files_windows(client, self.working_directory)

        if channel.recv_exit_status() == 0:
            self._existing_files = _parse_files(files)
        else:
            return False
        _, dirs = _get_directories_windows(client, self.working_directory)
        self._existing_dirs = _parse_directories(dirs)
    return True


def remote_delete_files(self):
    """Deletes all files not previously captured on a remote system."""
    current_files = []
    current_dirs = []
    client = self.connect()
    # Try to get the OS of the remote system.
    system = _get_remote_os(client)
    if not system:
        # OS type isn't supported yet.
        return False

    if system != WINDOWS:
        # Try to get the filename and SHA1 hashes of the remote working directory.
        stdout = _get_files_and_hashes(client, self.working_directory)
        if stdout.channel.recv_exit_status() == 0:
            for line in stdout.readlines():
                if line:
                    hash_, file = tuple(line.split('  '))
                    current_files.append((file, hash_))
                else:
                    continue
        # If trying to get the hashes fails, just use the filenames.
        else:
            channel, files = _get_files_unix(client, self.working_directory)
            if channel.recv_exit_status() == 0:
                current_files = _parse_files(files)
            else:
                # Cannot get the filenames.
                return False
        # Try to get the sub-directories of the remote working directory.
        _, dirs = _get_directories_unix(client, self.working_directory)
        current_dirs = _parse_directories(dirs)
    elif system == WINDOWS:
        channel, files = _get_files_windows(client, self.working_directory)
        if channel.recv_exit_status() == 0:
            current_files = _parse_files(files)
        else:
            # Cannot get the filenames.
            return False
        _, dirs = _get_directories_windows(client, self.working_directory)
        current_dirs = _parse_directories(dirs)

    to_delete = []
    if current_files:
        _, new_hashes = zip(*set(current_files))
        if hasattr(self, '_existing_files') and len(self._existing_files) > 0:
            files, hashes = zip(*self._existing_files)
        else:
            files, hashes = [], []
        for file, hash_ in current_files:
            # Don't delete anything in the .git directory.
            if re.search(r'\.git', str(file)):
                continue
            if str(file) not in files and hash_ not in hashes:
                if self.working_directory:
                    file = pathlib.Path(self.working_directory) / file
                to_delete.append(str(file).strip('\n'))
                continue
            elif hash_ in hashes and (str(file), hash_) not in self._existing_files and new_hashes.count(hash_) > 1:
                if self.working_directory:
                    file = pathlib.Path(self.working_directory) / file
                to_delete.append(str(file).strip('\n'))
                continue
        if to_delete:
            _execute_command(client, f'rm {" ".join(to_delete)}')
    if system != WINDOWS:
        to_delete = []
        if current_dirs:
            if hasattr(self, '_existing_dirs') and len(self._existing_dirs) > 0:
                for directory in sorted(current_dirs, reverse=True):
                    # Don't delete anything in the .git directory.
                    if re.search(r'\.git', str(directory)):
                        continue
                    if directory not in self._existing_dirs:
                        to_delete.append(directory.strip('\n'))
            if to_delete:
                _execute_command(client, f'rm -rf {" ".join(to_delete)}')
    result = True
    return result


def container_up(self):
    """Starts up a new container based on the image set in self.environment."""
    self.client = docker.from_env()
    try:
        self.container = self.client.containers.run(
            self.environment,
            detach=True,
            tty=True,
            entrypoint='sh',
            working_dir=self.working_directory,
            mounts=[self.binding],
            name='build-magic',
        )
    except (APIError, AttributeError, ImageLoadError):
        return False
    return True


def container_destroy(self):
    """Destroys the container used for executing commands."""
    try:
        self.container.kill()
        self.container.remove()
        return True
    except (APIError, Exception):
        return False
