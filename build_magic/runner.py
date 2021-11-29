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

from build_magic.exc import HostWorkingDirectoryNotFound, OSEnvironmentMismatch
from build_magic.reference import BindDirectory, HostWorkingDirectory, OSVersionCommands


HOST_WD = 'hostwd'
BIND_DIR = 'bind'
ENVS = 'envs'
CWD = '.'


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

    def __init__(
            self,
            environment,
            working_dir='',
            copy_dir='',
            timeout=30,
            artifacts=None,
            parameters=None,
            envs=None,
    ):
        """Instantiate a new CommandRunner object."""
        self.environment = environment
        self.working_directory = working_dir
        self.copy_from_directory = copy_dir
        self.timeout = timeout
        self.artifacts = [] if not artifacts else artifacts
        self.parameters = {} if not parameters else parameters
        self.envs = {} if not envs else envs

    def _merge_envs(self):
        """Merge environment variables with self.envs."""
        envs = os.environ
        envs.update(self.envs)
        self.envs = envs

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
                if src == CWD:
                    src = Path.cwd().resolve()
                source = Path(src) / artifact
                try:
                    shutil.copy(source, dst)
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

    def __init__(
            self,
            environment='',
            working_dir='',
            copy_dir='',
            timeout=30,
            artifacts=None,
            parameters=None,
            envs=None,
    ):
        """Instantiates a new Local command runner object."""
        super().__init__(environment, working_dir, copy_dir, timeout, artifacts, parameters, envs)

    def os_matches_environment(self):
        """Tests if self.environment matches the locally running operating system or distro.

        :return: True if the environment matches the OS, else False.
        """
        if self.environment.lower() in ('macos', 'darwin'):
            cmd = OSVersionCommands.DARWIN.value
        elif self.environment.lower() in ('win', 'windows'):
            cmd = OSVersionCommands.WINDOWS.value
        else:
            cmd = OSVersionCommands.LINUX.value

        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=True,
        )

        if result.returncode > 0:
            return False

        if self.environment.lower() in ('macos', 'darwin'):
            return True if b'Mac OS X' or b'MacOS' in result.stdout else False
        elif self.environment.lower() in ('win', 'windows'):
            return True if b'Microsoft Windows' in result.stdout else False
        else:
            return True if bytes(self.environment.lower(), encoding='utf-8') in result.stdout else False

    def prepare(self):
        """Changes to the specified working directory and copies artifacts if necessary.

        :rtype: bool
        :return: Returns True.
        """
        if self.copy_from_directory:
            self.copy(self.copy_from_directory, self.working_directory)

        if self.working_directory:
            self.cd(self.working_directory)

        if self.environment:
            if self.os_matches_environment() is False:
                raise OSEnvironmentMismatch

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
            env=self._merge_envs(),
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
            envs=None,
    ):
        """Instantiates a new Remote command runner object."""
        if working_dir == CWD:
            working_dir = ''

        super().__init__(environment, working_dir, copy_dir, timeout, artifacts, parameters, envs)

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
            stdin_, stdout_, stderr_ = ssh.exec_command(
                command,
                timeout=self.timeout,
                get_pty=True,
                environment=self.envs,
            )
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

    vagrantfile_name = 'Vagrantfile'
    alt_vagrantfile_name = 'Vagrantfile_build_magic'
    vagrant_cwd_env = 'VAGRANT_CWD'
    vagrantfile_name_env = 'VAGRANT_VAGRANTFILE'
    default_home_dir = '/home/vagrant'
    default_bind_dir = '/vagrant'

    def __init__(
            self,
            environment=CWD,
            working_dir='',
            copy_dir='',
            timeout=30,
            artifacts=None,
            parameters=None,
            envs=None,
    ):
        """Instantiates a new Vagrant command runner object."""
        if not working_dir:
            working_dir = self.default_home_dir

        super().__init__(environment, working_dir, copy_dir, timeout, artifacts, parameters, envs)

        self._vm = None
        self._vagrantfile_config = {
            BIND_DIR: False,
            ENVS: False,
        }

        if self.environment == self.vagrantfile_name:
            self.environment = CWD

        if self.environment != CWD:
            if self.vagrantfile_name in self.environment:
                self.environment = self.environment.split(self.vagrantfile_name)[0]
            os.environ.pop(self.vagrant_cwd_env, '')
            os.environ[self.vagrant_cwd_env] = str(Path(self.environment).resolve())

        self.bind_path = self.parameters.get(BIND_DIR, BindDirectory(self.default_bind_dir)).value
        if self.bind_path != self.default_bind_dir:
            self._vagrantfile_config[BIND_DIR] = True

        if self.envs:
            self._vagrantfile_config[ENVS] = True

        self.host_wd = self.parameters.get(HOST_WD, HostWorkingDirectory(self.environment)).value
        if not Path(self.host_wd).exists():
            raise HostWorkingDirectoryNotFound

        # Create a new Vagrantfile if needed.
        if any(self._vagrantfile_config.values()):
            config = self.build_config()
            self.create_vagrantfile_config(config)

    def build_config(self):
        """Assemble the Vagrantfile config based on the command runner settings.

        :rtype: str
        :return: The Vagrantfile config.
        """
        wd = self.default_home_dir if self.working_directory == CWD else self.working_directory

        bind_dir = ''
        if self._vagrantfile_config.get(BIND_DIR, False):
            bind_dir = f'  config.vm.synced_folder "{CWD}", "{self.bind_path}"'

        envs = []
        exports = ''
        if self.envs:
            for env, value in self.envs.items():
                envs.append(f'echo "export {env}={value}" >> {wd}/.profile')
            exports = '\n'.join(envs)

        provision = ''
        if exports:
            provision = f"""  config.vm.provision "build-magic", type: "shell" do |s|
    s.inline = <<-SCRIPT
{exports}
SCRIPT
  end"""

        config = f"""# Config added by build-magic
Vagrant.configure("2") do |config|
{bind_dir}
{provision}
end"""
        return config

    def create_vagrantfile_config(self, config):
        """Concatenate a new Vagrantfile config to an existing Vagrantfile.

        The steps are:

            1. Read the Vagrantfile from self.environment.
            2. Append config to the end of the Vagrantfile.
            3. Write the new Vagrantfile to the same directory as the existing Vagrantfile.
            4. Set the VAGRANT_VAGRANTFILE environment variable to point to the new Vagrantfile.

        :param config: A Vagrant.config section to add to an existing Vagrantfile.
        :return: None
        """
        vagrantfile_path = Path(self.environment).resolve()
        vagrantfile = vagrantfile_path.joinpath(self.vagrantfile_name).read_text()
        new_vagrantfile = vagrantfile + config
        vagrantfile_path.joinpath(self.alt_vagrantfile_name).write_text(new_vagrantfile)
        os.environ.pop(self.vagrantfile_name_env, '')
        os.environ[self.vagrantfile_name_env] = self.alt_vagrantfile_name

    def prepare(self):
        """Handles copying artifacts to the working directory if necessary."""
        if self._vm and self.working_directory != self.bind_path:
            try:
                self._vm.ssh(command=f'sudo mkdir {self.working_directory}')
            except subprocess.CalledProcessError:
                return False

        if self.copy_from_directory and len(self.artifacts) > 0:
            self.copy(Path(self.copy_from_directory).resolve(), Path(self.host_wd).resolve())
            try:
                self._vm.ssh(command=f'sudo cp -R {self.bind_path}/* {self.working_directory}')
            except subprocess.CalledProcessError:
                return False
            return True
        return False

    def execute(self, macro):
        """Executes the Macro in the VM.

        :param Macro macro: The Macro object to execute.
        :return: The Status of the executed Macro.
        """
        if self.working_directory != self.default_home_dir:
            macro.prefix = f'cd {self.working_directory};'

        cmd = macro.as_string()

        try:
            out = self._vm.ssh(command=cmd)
        except subprocess.CalledProcessError as err:
            return Status('', str(err), 1)
        return Status(out, '', 0)


class Docker(CommandRunner):
    """Manages macros executed in a Docker container."""

    default_working_dir = '/build_magic'

    def __init__(
            self,
            environment='alpine',
            working_dir='',
            copy_dir='',
            timeout=30,
            artifacts=None,
            parameters=None,
            envs=None,
    ):
        """Instantiates a new Docker command runner object."""
        if not working_dir or working_dir == CWD:
            working_dir = self.default_working_dir

        super().__init__(environment, working_dir, copy_dir, timeout, artifacts, parameters, envs)

        self.host_wd = self.parameters.get(HOST_WD, HostWorkingDirectory(CWD)).value
        if not Path(self.host_wd).exists():
            raise HostWorkingDirectoryNotFound

        self.bind_path = self.parameters.get(BIND_DIR, BindDirectory()).value
        self.binding = Mount(
            target=self.bind_path,
            source=str(Path(self.host_wd).resolve()),
            type=BIND_DIR,
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
                    self.container.exec_run(cmd=f'mkdir {self.working_directory}')
                    self.container.exec_run(cmd=f'/bin/sh -c "cp -R {self.bind_path}/* {self.working_directory}"')
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
            code, out = self.container.exec_run(
                cmd=command,
                stdout=True,
                stderr=True,
                tty=True,
                environment=self.envs,
            )
            if out:
                out = out.decode('utf-8')
            if code > 0:
                status = Status(stdout='', stderr=out, exit_code=code)
            else:
                status = Status(stdout=out, stderr='', exit_code=code)
        except ContainerError as err:
            status = Status('', stderr=str(err), exit_code=1)
        return status
