"""Module for defining CommandRunner classes."""

import os
from pathlib import Path
import re
import shutil
import socket
import subprocess

from docker.types import Mount
from docker.errors import ContainerError
import paramiko
from scp import SCPClient

from build_magic.reference import BindDirectory, HostWorkingDirectory


class Status:
    """The captured output of a command executed by a CommandRunner."""

    __slots__ = ['_stdout', '_stderr', '_exit_code']

    def __init__(self, stdout='', stderr='', exit_code=0):
        """Instantiates a new Status object.

        :param bytes|str stdout: The stdout captured by a CommandRunner.
        :param bytes|str stderr: The stderr captured by a CommandRunner.
        :param num exit_code: The exit code captured by a CommandRunner.
        """
        self._stdout = stdout
        self._stderr = stderr
        self._exit_code = exit_code

    @property
    def stdout(self):
        """Provides the captured stdout.

        :rtype: str
        :return: The captured stdout.
        """
        return self._stdout

    @property
    def stderr(self):
        """Provides the captured stderr.

        :rtype: str
        :return: The captured stderr.
        """
        return self._stderr

    @property
    def exit_code(self):
        """The captured exit code.

        :rtype: int
        :return: The captured exit code.
        """
        return self._exit_code

    @staticmethod
    def _validate(other):
        """Raise an exception if other isn't a Status object.

        :param Any other: The object to validate.
        :return: None
        """
        if not isinstance(other, Status):
            raise TypeError(f'Cannot compare object of type Status with object of type {type(other)}')

    def __repr__(self):
        """Overrides the default string representation to display stdout, stderr, and exit_code.

        :rtype: str
        :return: The Status string representation.
        """
        return f'<stdout={self.stdout}, stderr={self.stderr}, exit_code={self.exit_code}>'

    def __eq__(self, other):
        """Compare two Status object to see if they are equal.

        :param Any other: The Status object to compare against.
        :rtype: bool
        :return: True if the Status objects are equal, otherwise False.
        """
        self._validate(other)
        return self.stdout == other.stdout and self.stderr == other.stderr and self.exit_code == other.exit_code

    def __lt__(self, other):
        """Compare if the exit code of the current Status object is less than the exit code of another Status object.

        :param Any other: The Status object to compare against.
        :rtype: bool
        :return: True if the exit code is less than the exit code of other, else False.
        """
        self._validate(other)
        return self.exit_code < other.exit_code

    def __le__(self, other):
        """Compare if the exit code of the current Status object is less than or equal to the exit code of another
        Status object.

        :param Any other: The Status object to compare against.
        :rtype: bool
        :return: True if the exit code is less than or equal to the exit code of other, else False.
        """
        self._validate(other)
        return self.exit_code <= other.exit_code

    def __gt__(self, other):
        """Compare if the exit code of the current Status object is greater than the exit code of another Status object.

        :param Any other: The Status object to compare against.
        :rtype: bool
        :return: True if the exit code is greater than the exit code of other, else False.
        """
        self._validate(other)
        return self.exit_code > other.exit_code

    def __ge__(self, other):
        """Check if the exit code of the Status object is greater than or equal to the exit code of another Status
        object.

        :param Any other: The Status object to compare against.
        :rtype: bool
        :return: True if the exit code is greater than or equal to the exit code of other, else False.
        """
        self._validate(other)
        return self.exit_code >= other.exit_code


class CommandRunner:
    """An abstract class for defining methods for executing commands.

    When instantiating and calling a CommandRunner child object,
    the object's methods should be called in the following order:

        - prepare()
        - provision()
        - execute()
        - teardown()
    """

    def __init__(self, environment, working_dir='', copy_dir='', timeout=30, artifacts=None, parameters=None):
        """Instantiate a new CommandRunner object."""
        self.environment = environment
        self.working_directory = working_dir
        self.copy_from_directory = copy_dir
        self.timeout = timeout
        self.artifacts = [] if not artifacts else artifacts
        self.parameters = {} if not parameters else parameters

        # TODO: Need to validate the types for artifacts and parameters.

    @staticmethod
    def cd(directory):
        """Changes the current working directory.

        :param str|Path directory: The directory to change to.
        :rtype: bool
        :return: True if directory is not an empty string or None.
        """
        if directory:
            path = Path(directory)
            try:
                os.chdir(path)
            except (OSError, Exception):
                return False
            return True
        else:
            return False

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
                try:
                    shutil.copy(src, dst)
                except (OSError, Exception):
                    return False
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

    def __init__(self, environment='', working_dir='', copy_dir='', timeout=30, artifacts=None, parameters=None):
        """Instantiates a new Local command runner object."""
        super().__init__(environment, working_dir, copy_dir, timeout, artifacts, parameters)

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
        command = macro.as_string()
        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=self.timeout,
            shell=True,
        )
        return Status(result.stdout, result.stderr, result.returncode)


class Remote(CommandRunner):
    """Manages macros executed on a remote host machine."""

    _default_ssh_path = Path('~/.ssh').expanduser()
    _environment_pattern = r'^(?:([\w\-.]+)@)?([\w\-.]+)(?::([0-9]{2,5}))?$'

    def __init__(
            self,
            environment='localhost',
            working_dir='',
            copy_dir='',
            timeout=30,
            artifacts=None,
            parameters=None,
    ):
        """Instantiates a new Remote command runner object."""
        if working_dir == '.':
            working_dir = ''

        super().__init__(environment, working_dir, copy_dir, timeout, artifacts, parameters)

        self.user = None
        self.host = None
        self.port = None
        match = re.match(self._environment_pattern, environment)
        if match:
            self.user, self.host = match.group(1), match.group(2)
            self.port = int(match.group(3)) if match.group(3) else 22

        self.key = self._get_ssh_key()

    def _get_ssh_key(self):
        """Get the SSH private key to use for authentication.

        :rtype: paramiko.PKey
        :return: The SSH private key object.
        """
        # Get the SSH key type from parameters or default to RSA.
        key_type_param = self.parameters.get('keytype')
        if key_type_param:
            key_type = getattr(paramiko, f'{key_type_param.value}')
        else:
            key_type = paramiko.RSAKey

        # Get the SSH private key path from parameters or default to $HOME/.ssh/id_rsa.
        key_path_param = self.parameters.get('keypath')
        if key_path_param:
            key_path = key_path_param.value
        else:
            key_path = str(self._default_ssh_path / 'id_rsa')

        # Get the SSH private key password from parameters if provided.
        if 'keypass' in self.parameters:
            key_pass_param = self.parameters.get('keypass').value
        elif 'key_password' in self.parameters:
            key_pass_param = self.parameters.get('key_password').value
        else:
            key_pass_param = None
        try:
            return key_type.from_private_key_file(key_path, password=key_pass_param)
        except (
            FileNotFoundError,
            IOError,
            Exception,
            paramiko.ssh_exception.SSHException,
            paramiko.PasswordRequiredException,
        ) as err:
            raise ValueError(f'SSH failure: {err}')

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
        try:
            ssh.connect(**conn_args)
        except socket.gaierror:
            raise Exception('SSH connection failed.')
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
        try:
            stdin_, stdout_, stderr_ = ssh.exec_command(command, timeout=self.timeout)
            stdout = stdout_.readlines()
            stderr = stderr_.readlines()
            exit_code = stdout_.channel.recv_exit_status()
        except socket.timeout:
            raise TimeoutError(
                'Connection to remote host {} timed out after {} seconds.'.format(self.host, self.timeout)
            )
        finally:
            ssh.close()
        return Status(stdout=''.join(stdout), stderr=''.join(stderr), exit_code=exit_code)


class Vagrant(CommandRunner):
    """Manages macros executed executed in a guest virtual machine managed by Vagrant."""

    def __init__(
            self,
            environment='.',
            working_dir='/home/vagrant',
            copy_dir='',
            timeout=30,
            artifacts=None,
            parameters=None,
    ):
        """Instantiates a new Vagrant command runner object."""
        super().__init__(environment, working_dir, copy_dir, timeout, artifacts, parameters)
        self.host_wd = self.parameters.get('hostwd', HostWorkingDirectory('.')).value
        self.bind_path = self.parameters.get('bind', BindDirectory('/vagrant')).value
        self._vm = None

    def prepare(self):
        """Handles copying artifacts to the working directory if necessary."""
        if self.copy_from_directory:
            if self._vm and self.working_directory != self.bind_path and len(self.artifacts) > 0:
                self.copy(self.copy_from_directory, Path(self.host_wd).resolve())
                try:
                    self._vm.ssh(command=f'sudo mkdir {self.working_directory}')
                    self._vm.ssh(command=f'cp -R {self.bind_path}/* {self.working_directory}')
                except subprocess.CalledProcessError:
                    return False
                return True
        return False

    def execute(self, macro):
        """Executes the Macro in the VM.

        :param Macro macro: The Macro object to execute.
        :return: The Status of the executed Macro.
        """
        if self.working_directory != '/home/vagrant':
            macro.prefix = f'cd {self.working_directory};'
        cmd = macro.as_string()
        try:
            out = self._vm.ssh(command=cmd)
        except subprocess.CalledProcessError as err:
            return Status('', str(err), 1)
        return Status(out, '', 0)


class Docker(CommandRunner):
    """Manages macros executed in a Docker container."""

    def __init__(
            self,
            environment='alpine',
            working_dir='/build_magic',
            copy_dir='',
            timeout=30,
            artifacts=None,
            parameters=None
    ):
        """Instantiates a new Docker command runner object."""
        super().__init__(environment, working_dir, copy_dir, timeout, artifacts, parameters)
        if self.working_directory == '.':
            self.working_directory = '/build_magic'
        self.host_wd = self.parameters.get('hostwd', HostWorkingDirectory('.')).value
        self.bind_path = self.parameters.get('bind', BindDirectory()).value
        self.binding = Mount(
            target=self.bind_path,
            source=str(Path(self.host_wd).resolve()),
            type='bind',
        )
        self.client = None
        self.container = None

    def prepare(self):
        """Handles copying artifacts to the working directory if necessary."""
        if self.copy_from_directory:
            if self.working_directory != self.bind_path and len(self.artifacts) > 0:
                self.copy(self.copy_from_directory, Path(self.host_wd).resolve())
                if not self.container:
                    self.provision()
                try:
                    self.container.exec_run(cmd=f'mkdir {self.working_directory}', tty=True)
                    self.container.exec_run(cmd=f'cp -R {self.bind_path}/* {self.working_directory}', tty=True)
                except ContainerError:
                    return False
                return True
        return False

    def execute(self, macro):
        """Executes the Macro in the container.

        :param Macro macro: The Macro object to execute.
        :return: The Status of the executed Macro.
        """
        if macro:
            command = ['/bin/sh', '-c', macro.as_string()]
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
