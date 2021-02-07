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
            super().__init__(f'{self.msg}.')


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
