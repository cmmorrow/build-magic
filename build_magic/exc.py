"""This module hosts the build-magic exception."""


class BuildMagicException(Exception):
    """build-magic base exception class."""

    msg = 'build-magic error'

    def __init__(self, exception=None, message=''):
        """Instantiates a BuildMagicException object.

        :param Exception exception: An exception to wrap.
        :param str message: An error message to display.
        """
        if exception:
            super().__init__(f'{self.msg}: {str(exception)}')
        elif message:
            super().__init__(f'{self.msg}: {message}')
        else:
            super().__init__(f'{self.msg}')


class ExecutionError(BuildMagicException):
    """A general build-magic execution error."""

    msg = 'Command execution error'


class SetupError(BuildMagicException):
    """An error when setting up a CommandRunner."""

    msg = 'Setup failed'


class TeardownError(BuildMagicException):
    """An error when tearing down a CommandRunner."""

    msg = 'Teardown failed'


class NoJobs(BuildMagicException):
    """There are no jobs to execute."""

    msg = 'No jobs to execute'


class ValidationError(BuildMagicException):
    """Parameter validation failed."""

    msg = 'Validation failed'


class HostWorkingDirectoryNotFound(BuildMagicException):
    """The specified host working directory doesn't exist."""

    msg = 'The host working directory was not found.'


class DockerDaemonError(BuildMagicException):
    """The Docker daemon isn't running or Docker isn't installed."""

    msg = 'Cannot connect to Docker daemon. Is Docker installed and running?'


class ContainerExistsError(BuildMagicException):
    """The build-magic container is already running."""

    msg = 'A build-magic container is already running. Please stop and remove it to continue.'


class VagrantNotFoundError(BuildMagicException):
    """The Vagrant executable was not found in the system path."""

    msg = 'Cannot find Vagrant in the system path. Is it installed?'


class OSEnvironmentMismatch(BuildMagicException):
    """The specified environment doesn't match the target operating system."""

    msg = "Target OS does not match the specified environment."
