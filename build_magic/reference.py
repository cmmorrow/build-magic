"""This module hosts enums and other constants used by build-magic."""
import enum
from enum import Enum, unique


class EnumExt(Enum):
    """Extension for the builtin Enum class."""

    def __contains__(self, item):
        """Adds dictionary-like key searching behavior to class attributes.

        :param item: The item to check for in class attributes.
        :return: The matching value.
        """
        values = self.available()
        return item in values

    @classmethod
    def names(cls):
        """Provides a tuple of the enum names.

        :rtype: tuple[str]
        :return: A tuple of Enum names.
        """
        return tuple([name for name in cls.__members__.keys()])

    @classmethod
    def available(cls):
        """Provides the Enum values as a tuple.

        :rtype: tuple[Any]
        :return: A list of available Enum values.
        """
        return tuple([src.value for src in cls.__members__.values()])

    @classmethod
    def values(cls):
        """An alias for the available property.

        :rtype: tuple[Any]
        :return: A list of available Enum values.
        """
        return cls.available()


@unique
class OutputTypes(EnumExt):
    """Mapping of valid output type options to the corresponding Output subclass."""

    plain = 'Basic'
    fancy = 'Tty'
    quiet = 'Silent'


@unique
class Runners(EnumExt):
    """Valid command runner argument names."""

    LOCAL = 'local'
    REMOTE = 'remote'
    VAGRANT = 'vagrant'
    DOCKER = 'docker'


@unique
class Directive(EnumExt):
    """Valid directive argument names."""

    BUILD = 'build'
    DEPLOY = 'deploy'
    EXECUTE = 'execute'
    INSTALL = 'install'


@unique
class Actions(EnumExt):
    """Valid action argument names."""

    DEFAULT = 'default'
    CLEANUP = 'cleanup'
    PERSIST = 'persist'


class ExitCode(enum.IntEnum):
    """Valid build-magic exit codes."""

    PASSED = 0
    FAILED = 1
    INTERRUPTED = 4
    INTERNAL_ERROR = 3
    INPUT_ERROR = 2
    NO_TESTS = 5


class OutputMethod(enum.Enum):
    """Valid build-magic output methods."""

    JOB_START = 'start_job'
    JOB_END = 'end_job'
    STAGE_START = 'start_stage'
    STAGE_END = 'end_stage'
    NO_JOB = 'no_job'
    MACRO_START = 'macro_start'
    MACRO_STATUS = 'macro_status'
    ERROR = 'error'
    INFO = 'info'
