"""Module for defining CommandRunner classes."""

from collections import namedtuple
from pathlib import Path
import re
import subprocess
import time

import docker
from docker.errors import ContainerError, APIError, ImageLoadError
import paramiko

"""The captured output of a command executed by a CommandRunner."""
Status = namedtuple('Status', ['stdout', 'stderr', 'exit_code'])


class CommandRunner:
    """An abstract class for defining methods for executing commands."""

    def __init__(self, environment, timeout=30):
        """"""
        self.environment = environment
        self.timeout = timeout

    def provision(self, func):
        """"""
        func()

    def execute(self, macro):
        """"""
        raise NotImplementedError

    def teardown(self, func):
        """"""
        func()


class Local(CommandRunner):
    """"""

    def __init__(self, environment='', timeout=30):
        """

        :param environment:
        """
        super().__init__(environment, timeout)

    def execute(self, macro):
        """"""
        command = macro.as_list()
        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            # capture_output=True,
            timeout=self.timeout,
        )
        return Status(result.stdout, result.stderr, result.returncode)


class Remote(CommandRunner):
    """"""

    def __init__(self, environment, timeout=30):
        """

        :param environment:
        """
        super().__init__(environment, timeout)
        self.user = None
        self.host = None
        self.port = None
        match = re.match(r'([\w\-.]+)@([\w\-.]+)(?::([0-9]{2,5}))?$', environment)
        if match:
            self.user = match.group(1)
            self.host = match.group(2)
            self.port = int(match.group(3))

    def execute(self, macro):
        """"""
        command = macro.as_string()
        stdout = []
        stderr = []
        exit_code = -1
        buff_size = 4096
        host = self.host
        user = self.user
        port = self.port
        # noinspection PyTypeChecker
        client = paramiko.Transport((host, port))
        client.connect(username=user)
        session = client.open_channel(kind='session')
        session.exec_command(command)

        start = time.time()
        current = start
        while current - start < self.timeout:
            if session.exit_status_ready():
                exit_code = session.recv_exit_status()
                buffer = session.recv(buff_size)
                stdout.append(buffer)
                if len(buffer) != 0:
                    while len(buffer) != 0:
                        buffer = session.recv(buff_size)
                        stdout.append(buffer)
                buffer = session.recv_stderr(buff_size)
                stderr.append(buffer)
                if len(buffer) != 0:
                    while len(buffer) != 0:
                        buffer = session.recv_stderr(buff_size)
                        stdout.append(buffer)
        session.close()
        client.close()
        if exit_code < 0:
            raise TimeoutError('Connection to remote host {} timed out after {} seconds.'.format(host, self.timeout))
        return Status(stdout=stdout, stderr=stderr, exit_code=exit_code)


class Vagrant(CommandRunner):
    """"""

    __slots__ = ['_vm']

    def __init__(self, environment='.', timeout=30):
        """"""
        super().__init__(environment, timeout)
        self._vm = None

    # def provision(self, macro):
    #     """"""
    #     if self.environment != '.':
    #         os.environ['VAGRANT_CWD'] = self.environment
    #     self._vm = vagrant.Vagrant()
    #     try:
    #         self._vm.up()
    #     except subprocess.CalledProcessError as err:
    #         return Status('', err, 1)
    #     return Status('', '', 0)

    def execute(self, macro):
        """"""
        cmd = 'cd /vagrant; ' + macro.as_string()
        if not self._vm:
            self.provision(macro)
        try:
            self._vm.ssh(command=cmd)
        except subprocess.CalledProcessError as err:
            return Status('', err, 1)
        return Status('', '', 0)

    # def teardown(self, macro):
    #     """"""
    #     if self._vm:
    #         try:
    #             self._vm.destroy()
    #         except subprocess.CalledProcessError as err:
    #             return Status('', err, 1)
    #     return Status('', '', 0)


class Docker(CommandRunner):
    """"""

    def __init__(self, environment='alpine:latest', timeout=30, working_directory='.'):
        """

        :param environment:
        :param timeout:
        :param working_directory:
        """
        super().__init__(environment, timeout)
        if working_directory == '.':
            self.working_directory = Path(working_directory).cwd()
        else:
            self.working_directory = Path(working_directory)
        self.container = None

    def provision(self, macro=None):
        """"""
        return self.execute(macro)

    def execute(self, macro):
        """

        :param macro:
        :return:
        """
        if macro:
            command = macro.as_list()
        else:
            command = macro
        client = docker.from_env()
        try:
            container = client.containers.run(
                self.environment,
                command=command,
                detach=False,
                remove=True,
                working_dir='/build_magic',
                volumes={self.working_directory: {'bind': '/build_magic', 'mode': 'rw'}}
            )
            self.container = container
            status = Status('', '', exit_code=0)
        except (ContainerError, APIError, ImageLoadError) as err:
            status = Status('', stderr=err, exit_code=1)
        return status
        # command = macro.as_list()
        # if not self.container:
        #     status = self.provision(macro)
        # else:
        #     exit_status, output = self.container.exec_run(command, workdir='/build_magic', demux=True)
        #     status = Status(stdout=output[0], stderr=output[1], exit_code=exit_status)
        # return status

    def teardown(self, macro):
        """"""
        return self.execute(macro)
        # if self.container:
        #     try:
        #         self.container.stop(timeout=self.timeout)
        #         status = Status(stdout='', stderr='', exit_code=0)
        #     except APIError as err:
        #         status = Status(stdout='', stderr=err, exit_code=1)
        #     return status
        # else:
        #     return self.execute(macro)
