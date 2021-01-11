"""Module for defining CommandRunner classes."""

import os
from pathlib import Path
import re
import shutil
import subprocess

from docker.errors import ContainerError
import paramiko
from scp import SCPClient


class Status:
    """The captured output of a command executed by a CommandRunner."""

    def __init__(self, stdout='', stderr='', exit_code=0):
        """Instantiates a new Status object.

        :param bytes|str stdout: The stdout captured by a CommandRunner.
        :param bytes|str stderr: The stderr captured by a CommandRunner.
        :param num exit_code: The exit code captured by a CommandRunner.
        """
        self.stdout = stdout
        self.stderr = stderr
        self.exit_code = exit_code


class CommandRunner:
    """An abstract class for defining methods for executing commands.

    When instantiating and calling a CommandRunner child object,
    the object's methods should be called in the following order:

        - prepare()
        - provision()
        - execute()
        - teardown()
    """

    def __init__(self, environment, working_dir='', copy_dir='', timeout=30, artifacts=None):
        """Instantiate a new CommandRunner object."""
        self.environment = environment
        self.working_directory = working_dir
        self.copy_from_directory = copy_dir
        self.timeout = timeout
        if not artifacts:
            self.artifacts = []
        else:
            self.artifacts = artifacts

    def copy(self, src, dst):
        """Copies the CommandRunner object's artifacts from one path to another.

        :param str|Path src: The source path to copy from.
        :param str|Path dst: The destination path to copy to.
        :rtype: bool
        :return: True if src and dst are not empty strings or None.
        """
        if not self.artifacts:
            return False
        if src and dst:
            for artifact in self.artifacts:
                if src == '.':
                    src = Path.cwd().resolve()
                src = Path(src) / artifact
                shutil.copy(src, dst)
            return True
        else:
            return False

    @staticmethod
    def cd(directory):
        """Changes the current working directory.

        :param str|Path directory: The directory to change to.
        :rtype: bool
        :return: True if directory is not an empty string or None.
        """
        if directory:
            path = Path(directory)
            os.chdir(path)
            return True
        else:
            return False

    def provision(self):
        """Base provision() method.

        This method should be overridden by dynamically assigning it to a child object.

        :rtype: Any
        :return: The result of the callable.
        """
        return False

    def execute(self, macro):
        """Base execute() method.

        :param Macro macro: The Macro object to execute.
        :return: None
        """
        raise NotImplementedError

    def prepare(self):
        """Base prepare() method.

        :return: None
        """
        raise NotImplementedError

    def teardown(self):
        """Base provision() method.

        This method should be overridden by dynamically assigning it to a child object.

        :rtype: Any
        :return: The result of the callable.
        """
        return False

    @property
    def name(self):
        """Provides the CommandRunner name."""
        return str(self.__class__.__name__).lower()


class Local(CommandRunner):
    """Manages macros executed on the local host machine."""

    def __init__(self, environment='', working_dir='', copy_dir='', timeout=30, artifacts=None):
        """Instantiates a new Local command runner object."""
        super().__init__(environment, working_dir, copy_dir, timeout, artifacts)

    def prepare(self):
        """Changes to the specified working directory and copies artifacts if necessary.

        :rtype: bool
        :return: Returns True.
        """
        if self.copy_from_directory:
            self.copy(self.copy_from_directory, self.working_directory)
        if self.working_directory:
            self.cd(self.working_directory)
        return True

    def execute(self, macro):
        """Executes the Macro object on the local host machine.

        :param Macro macro: The Macro object the execute.
        :rtype: Status
        :return: A Status object reflecting the results of the macro.
        """
        command = macro.as_list()
        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=self.timeout,
        )
        return Status(result.stdout, result.stderr, result.returncode)


class Remote(CommandRunner):
    """Manages macros executed on a remote host machine."""

    def __init__(self, environment='localhost', working_dir='', copy_dir='', timeout=30, artifacts=None):
        """Instantiates a new Remote command runner object."""
        if working_dir == '.':
            working_dir = ''
        super().__init__(environment, working_dir, copy_dir, timeout, artifacts)
        self.user = None
        self.host = None
        self.port = None
        match = re.match(r'^(?:([\w\-.]+)@)?([\w\-.]+)(?::([0-9]{2,5}))?$', environment)
        if match:
            self.user = match.group(1)
            self.host = match.group(2)
            if match.group(3):
                self.port = int(match.group(3))
            else:
                self.port = 22

        self.home = os.environ.get('HOME')
        self.key = paramiko.RSAKey.from_private_key_file(str(Path(self.home) / '.ssh' / 'id_rsa'))

    def connect(self):
        """Creates an SSH connection.

        :rtype: paramiko.SSHClient
        :return: The SSH client.
        """
        ssh = paramiko.SSHClient()
        ssh.load_system_host_keys()
        conn_args = dict(hostname=self.host, pkey=self.key)
        if self.port:
            conn_args.update(dict(port=self.port))
        if self.user:
            conn_args.update(dict(username=self.user))
        ssh.connect(**conn_args)
        return ssh

    def copy(self, src, dst=None):
        """Copies the object's artifacts from a directory on the local host to a directory on the remote host.

        :param str|Path src: The source directory to copy from.
        :param str|Path dst: The destination directory to copy to.
        :rtype: bool
        :return: True if the copy operation was successful.
        """
        # Add the absolute path to each artifact.
        src = Path(src)
        files = []
        for artifact in self.artifacts:
            files.append(str(src / artifact))

        if not files:
            return False

        # Connect to the remote host over scp.
        ssh = self.connect()

        # Copy each file to the remote host.
        with SCPClient(ssh.get_transport()) as cp:
            if dst:
                cp.put(files, remote_path=dst)
            else:
                cp.put(files)
        return True

    def prepare(self):
        """Handles copying artifacts to the remote host if necessary.

        :rtype: bool
        :return: True if copying artifacts was initiated and successful, otherwise False.
        """
        if self.copy_from_directory:
            src = self.copy_from_directory
            if self.working_directory:
                dst = self.working_directory
            else:
                dst = None
            return self.copy(src, dst)
        else:
            return False

    def execute(self, macro):
        """Executes the Macro object on the remote host machine.

        :param Macro macro: The Macro object to execute.
        :rtype: Status
        :return: A Status object that reflects the results of the macro.
        """
        if self.working_directory:
            macro.prefix = f'cd {self.working_directory};'
        command = macro.as_string()

        ssh = self.connect()
        stdin_, stdout_, stderr_ = ssh.exec_command(command, timeout=self.timeout)
        stdout = stdout_.readlines()
        stderr = stderr_.readlines()
        exit_code = stdout_.channel.recv_exit_status()

        if exit_code < 0:
            raise TimeoutError(
                'Connection to remote host {} timed out after {} seconds.'.format(self.host, self.timeout)
            )
        return Status(stdout=''.join(stdout), stderr=''.join(stderr), exit_code=exit_code)


class Vagrant(CommandRunner):
    """Manages macros executed executed in a guest virtual machine managed by Vagrant."""

    def __init__(self, environment='.', working_dir='.', copy_dir='', timeout=30, artifacts=None):
        """Instantiates a new Vagrant command runner object."""
        super().__init__(environment, working_dir, copy_dir, timeout, artifacts)
        self._vm = None

    def prepare(self):
        """Handles copying artifacts to the working directory if necessary."""
        if self.copy_from_directory:
            self.copy(self.copy_from_directory, Path.cwd().resolve())
            return True
        else:
            return False

    def execute(self, macro):
        """Executes the Macro in the VM.

        :param Macro macro: The Macro object to execute.
        :return: The Status of the executed Macro.
        """
        cmd = macro.as_string()
        try:
            out = self._vm.ssh(command=cmd)
        except subprocess.CalledProcessError as err:
            return Status('', str(err), 1)
        return Status(out, '', 0)


class Docker(CommandRunner):
    """Manages macros executed in a Docker container."""

    def __init__(self, environment='alpine', working_dir='.', copy_dir='', timeout=30, artifacts=None):
        """Instantiates a new Docker command runner object."""
        super().__init__(environment, working_dir, copy_dir, timeout, artifacts)
        self.binding = {
            str(self.working_directory): {
                'bind': '/build_magic',
                'mode': 'rw',
            }
        }
        self.container = None

    def prepare(self):
        """Handles copying artifacts to the working directory if necessary."""
        if self.copy_from_directory:
            self.copy(self.copy_from_directory, self.working_directory)
            return True
        else:
            return False

    def execute(self, macro):
        """Executes the Macro in the container.

        :param Macro macro: The Macro object to execute.
        :return: The Status of the executed Macro.
        """
        if macro:
            command = macro.as_list()
        else:
            command = None

        if not self.container:
            self.provision()
        try:
            code, (out, err) = self.container.exec_run(
                cmd=command,
                stdout=True,
                stderr=True,
                tty=True,
                demux=True,
            )
            status = Status(stdout=out, stderr=err, exit_code=code)
        except ContainerError as err:
            status = Status('', stderr=str(err), exit_code=1)
        return status
