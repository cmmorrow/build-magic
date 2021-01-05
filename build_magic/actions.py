"""This module hosts Actions and functions to dynamically bind to CommandRunner classes."""

import os
import pathlib
import subprocess

import docker
from docker.errors import APIError, ImageLoadError
import paramiko
import vagrant


LOCAL = 'local'
REMOTE = 'remote'
VAGRANT = 'vagrant'
DOCKER = 'docker'

SETUP_METHOD = 'provision'
TEARDOWN_METHOD = 'teardown'

DEFAULT_METHOD = 'null'


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
        }
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
            DOCKER: 'capture_dir',
            VAGRANT: 'vm_up',
        },
        TEARDOWN_METHOD: {
            LOCAL: 'delete_new_files',
            REMOTE: 'remote_delete_files',
            DOCKER: 'delete_new_files',
            VAGRANT: 'vm_destroy',
        }
    }

    add_prefix = {
        VAGRANT: 'cd /vagrant;',
    }


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
        }
    }

    add_prefix = {
        VAGRANT: 'cd /vagrant;',
    }


def null(self):
    """Basic No-op."""
    return True


def vm_up(self):
    """Starts up a VM according to the corresponding Vagrantfile."""
    if self.environment == 'Vagrantfile':
        self.environment = '.'
    if self.environment != '.':
        os.environ['VAGRANT_CWD'] = self.environment
    self._vm = vagrant.Vagrant()
    try:
        self._vm.up()
        # if self.working_directory != '/vagrant':
        #     self._vm.ssh(command='cp /vagrant/* .')
    except subprocess.CalledProcessError as err:
        print(str(err))
        return False
    return True


def vm_destroy(self):
    """Destroys the VM used for executing commands."""
    if self._vm:
        try:
            self._vm.destroy()
        except subprocess.CalledProcessError:
            return False
    return True


def capture_dir(self):
    """Capture a list of all the files in a directory."""
    pwd = pathlib.Path.cwd()
    self.existing_files = [file for file in pwd.iterdir()]
    return True


def delete_new_files(self):
    """Deletes all files not previously captured."""
    if hasattr(self, 'existing_files'):
        pwd = pathlib.Path.cwd()
        current_files = pwd.iterdir()
        for file in current_files:
            if file not in self.existing_files:
                os.remove(file)
        return True
    else:
        return False


def remote_capture_dir(self):
    """Capture a list of all the files in a directory on a remote system."""
    client = paramiko.SSHClient()
    client.load_system_host_keys()
    client.connect(self.host, self.port, self.user)
    if self.working_directory:
        cmd = f'ls {self.working_directory}'
    else:
        cmd = 'ls'
    stdin, stdout, stderr = client.exec_command(cmd)
    self.existing_files = [file for file in str(stdout).split(' ')]
    client.close()
    return True


def remote_delete_files(self):
    """Deletes all files not previously captured on a remote system."""
    if hasattr(self, 'existing_files'):
        client = paramiko.SSHClient()
        client.load_system_host_keys()
        client.connect(self.host, self.port, self.user)
        if self.working_directory:
            cmd = f'ls {self.working_directory}'
        else:
            cmd = 'ls'
        stdin, stdout, stderr = client.exec_command(cmd)
        current_files = [file for file in str(stdout).split(' ')]
        for file in current_files:
            if file not in self.existing_files:
                if self.working_directory:
                    file = str(self.working_directory) + '/' + file
                client.exec_command(f'rm {file}')
        client.close()
        return True
    else:
        return False


def container_up(self):
    """Starts up a new container based on the image set in self.environment."""
    client = docker.from_env()
    try:
        self.container = client.containers.run(
            self.environment,
            detach=True,
            tty=True,
            entrypoint='sh',
            working_dir='/build_magic',
            volumes=self.binding,
            name='build-magic',
        )
    except (APIError, ImageLoadError):
        return False
    return True


def container_destroy(self):
    """Destroys the container used for executing commands."""
    try:
        self.container.kill()
        self.container.remove()
        return True
    except APIError:
        return False
