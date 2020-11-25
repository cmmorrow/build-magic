"""
Local:
    default: provision
    copy: copy files, provision
    working: cd, provision
    both: copy, cd, provision
Remote:
    default: Use home directory, provision
    copy: copy files to home directory, provision
    working: add cd prefix, provision
    both: add cd prefix, copy to wd, provision
Vagrant:
    default: Use /vagrant, add cd prefix (/vagrant), provision
    copy: copy files to /vagrant, add cd prefix (/vagrant), provision
    working: add cd prefix (wd), provision
    both: copy files to /vagrant, copy files to wd, add cd prefix (wd), provision
Docker:
    default: Set wd to /build_magic, provision
    copy: copy files to cwd, set wd to /build_magic, provision
    working: set wd to wd, provision
    both: copy files to cwd, set wd, provision

"""

import os
import pathlib
import subprocess

import paramiko
import vagrant


SETUP_METHOD = 'provision'
TEARDOWN_METHOD = 'teardown'

DEFAULT_METHOD = 'null'


class Action:
    """An Action is used to dynamically define the setup and teardown process for a CommandRunner.

    In most cases, a Default action is called to specify and dynamically bind the setup and teardown methods.

    New functions can be added to Action classes to modify the setup and teardown behavior of a CommandRunner."""

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
            'local': 'null',
            'remote': 'null',
            'docker': 'null',
            'vagrant': 'vm_up',
        },
        TEARDOWN_METHOD: {
            'local': 'null',
            'remote': 'null',
            'docker': 'null',
            'vagrant': 'vm_destroy',
        }
    }

    add_prefix = {
        'vagrant': 'cd /vagrant;',
    }


class Cleanup(Action):
    """Action for deleting any files created while executing a Stage."""

    mapping = {
        SETUP_METHOD: {
            'local': 'capture_dir',
            'remote': 'remote_capture_dir',
            'docker': 'capture_dir',
            'vagrant': 'vm_up',
        },
        TEARDOWN_METHOD: {
            'local': 'delete_new_files',
            'remote': 'remote_delete_files',
            'docker': 'delete_new_files',
            'vagrant': 'vm_destroy',
        }
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
        if self.working_directory != '/vagrant':
            self._vm.ssh(command='cp /vagrant/* .')
    except subprocess.CalledProcessError as err:
        print(err)
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
