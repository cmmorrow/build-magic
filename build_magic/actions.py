""""""

import os
import pathlib
import subprocess

import vagrant


SETUP_METHOD = 'provision'
TEARDOWN_METHOD = 'teardown'

DEFAULT_METHOD = 'null'


class Action:
    """"""

    add_prefix = {}
    add_suffix = {}
    mapping = {
        SETUP_METHOD: {},
        TEARDOWN_METHOD: {},
    }


class Default(Action):
    """"""

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
    """"""

    mapping = {
        SETUP_METHOD: {
            'local': 'capture_dir',
            'docker': 'capture_dir',
            'vagrant': 'copy_shared_to_vagrant_home',
        },
        TEARDOWN_METHOD: {
            'local': 'delete_new_files',
            'docker': 'delete_new_files',
            'vagrant': 'vm_destroy',
        }
    }


def null(self):
    """"""
    return


def vm_up(self):
    """"""
    if self.environment != '.':
        os.environ['VAGRANT_CWD'] = self.environment
    self._vm = vagrant.Vagrant()
    try:
        self._vm.up()
    except subprocess.CalledProcessError:
        return False
    return True


def vm_destroy(self):
    """"""
    if self._vm:
        try:
            self._vm.destroy()
        except subprocess.CalledProcessError:
            return False
    return True


def capture_dir(self):
    """"""
    pwd = pathlib.Path.cwd()
    self.existing_files = pwd.iterdir()
    return True


def delete_new_files(self):
    """"""
    if hasattr(self, 'existing_files'):
        pwd = pathlib.Path.cwd()
        current_files = pwd.iterdir()
        for file in current_files:
            if file not in self.existing_files:
                os.remove(file)
        return True
    else:
        return False


def copy_shared_to_vagrant_home(self):
    """"""
    if self._vm:
        self._vm.ssh(command='cp /vagrant/* .')
        return True
    else:
        return False
