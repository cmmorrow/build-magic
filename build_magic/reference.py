"""This module hosts enums and other constants used by build-magic."""
import enum
from enum import Enum, unique
from pathlib import Path
import re

from build_magic.exc import ValidationError


class EnumExt(Enum):
    """Extension for the builtin Enum class."""

    @classmethod
    def names(cls):
        """Provides a tuple of the enum names.

        :rtype: tuple[str]
        :return: A tuple of Enum names.
        """
        return tuple(cls.__members__)

    @classmethod
    def available(cls):
        """Provides the Enum values as a tuple.

        :rtype: tuple[Any]
        :return: A list of available Enum values.
        """
        return tuple([src.value for src in cls])

    @classmethod
    def values(cls):
        """An alias for the available property.

        :rtype: tuple[Any]
        :return: A list of available Enum values.
        """
        return cls.available()


class ParameterMeta(type):
    """Parameter Metaclass for preventing the KEY attribute from being changed."""

    def __new__(mcs, name, bases, attrs):
        """Capture the class attributes and make them immutable."""
        class_ = super().__new__(mcs, name, bases, attrs)
        class_.KEY = attrs.get('KEY', None)
        class_.ENUM = attrs.get('ENUM', None)
        class_.ALIAS = attrs.get('ALIAS', None)
        class_.DEFAULT = attrs.get('DEFAULT', None)
        class_.PATTERN = attrs.get('PATTERN', None)
        return class_


class Parameter(metaclass=ParameterMeta):
    """A class for providing generic key/value pairs."""

    __slots__ = ['_key', '_value']

    def __setattr__(self, key, value):
        """Override the default __setattr__ behavior.

        :param str key: The parameter key to set.
        :param str value: The parameter value to set.
        :return: None
        """
        if key not in ('_key', '_value'):
            raise AttributeError
        super.__setattr__(self, key, value)

    def __init__(self, value=None):
        """Instantiates a new Parameter object.

        :param Any value: The value of the Parameter.
        """
        self._key = self.KEY
        self._value = value or self.default
        if self.pattern:
            if not self.validate_pattern():
                raise ValidationError(message=f'Value {self.value} does not match {self.pattern}.')
        if self.enum:
            if not self.validate_enum():
                valid = (e.value for e in self.enum.__members__.values())
                raise ValidationError(message=f'Value {self.value} is not one of {set(valid)}.')

    def __repr__(self):
        """The string representation of the Parameter object.

        :rtype: str
        :return: The Parameter representation.
        """
        if self.alias:
            return f'<{self.__class__.__name__}: {self._key}, {self.alias}, {self._value}>'
        else:
            return f'<{self.__class__.__name__}: {self._key}, {self._value}>'

    def __eq__(self, other):
        """Compare the object to other to determine if they are equivalent.

        :param Any other: The object to compare against.
        :return: True if the objects are equivalent, otherwise False.
        """
        if isinstance(other, type(self)):
            if self.value == other.value and self.key == other.key:
                return True
        return False

    @property
    def key(self):
        """Getter for the Parameter key.

        :rtype: tuple
        :return: The Parameter object key.
        """
        return self._key

    @property
    def enum(self):
        """Getter for the Parameter enum.

        :rtype: None|enum.Enum
        :return: The Parameter object enum.
        """
        return self.ENUM

    @property
    def alias(self):
        """Getter for the Parameter alias/es.

        :rtype: str|list
        :return: The Parameter object alias.
        """
        return self.ALIAS

    @property
    def default(self):
        """Getter for the Parameter default.

        :rtype: Any
        :return: The Parameter object default.
        """
        return self.DEFAULT

    @property
    def pattern(self):
        """Getter for the Parameter regex pattern.

        :rtype: str
        :return: The Parameter object pattern.
        """
        return self.PATTERN

    @property
    def value(self):
        """Getter for the Parameter value.

        :rtype: Any
        :return: The Parameter object value.
        """
        return self._value

    def as_dict(self):
        """Provides the Parameter object as a dictionary.

        :rtype: dict[Any]
        :return: The Parameter as a dictionary.
        """
        return {self._key: self._value}

    def as_tuple(self):
        """Provides the Parameter object as a tuple where the first value is the key and the second is the value.

        :rtype: tuple[str, Any]
        :return: The Parameter as a tuple.
        """
        return self._key, self._value

    def validate_enum(self):
        """Check to make sure the ENUM attribute is a subclass of enum.enum and value is in ENUM.

        :rtype: bool
        :return: True if the Parameter value is in ENUM, otherwise False.
        """
        if not issubclass(self.enum.__class__, Enum) and type(self.enum) != type(Enum):
            raise TypeError('ENUM is not of type enum.Enum.')
        in_keys = self.value in [e.name for e in self.enum.__members__.values()]
        in_values = self.value in [e.value for e in self.enum.__members__.values()]
        if in_keys:
            self._value = self.enum[self.value].value
        return any((in_keys, in_values))

    def validate_pattern(self):
        """Check to make sure the Parameter value matches the PATTERN attribute.

        :rtype: bool
        :return: True of the Parameter value matches PATTERN, otherwise False.
        """
        if not isinstance(self.pattern, str):
            raise TypeError('PATTERN must be a string.')
        match = re.match(self.pattern, self.value)
        return True if match is not None else False


@unique
class OutputTypes(EnumExt):
    """Mapping of valid output type options to the corresponding Output subclass."""

    BASIC = 'Basic'
    TTY = 'Tty'
    SILENT = 'Silent'


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

    TEST = 'test'
    BUILD = 'build'
    DEPLOY = 'deploy'
    EXECUTE = 'execute'
    INSTALL = 'install'
    RELEASE = 'release'


@unique
class Actions(EnumExt):
    """Valid action argument names."""

    DEFAULT = 'default'
    CLEANUP = 'cleanup'
    PERSIST = 'persist'


@unique
class ExitCode(enum.IntEnum):
    """Valid build-magic exit codes."""

    PASSED = 0
    FAILED = 1
    INTERRUPTED = 4
    INTERNAL_ERROR = 3
    INPUT_ERROR = 2
    NO_TESTS = 5


@unique
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


class KeyTypes(EnumExt):
    """Valid public/private key types."""

    dsa = 'DSSKey'
    dss = 'DSSKey'
    rsa = 'RSAKey'
    ecdsa = 'ECDSAKey'
    ed25519 = 'Ed25519Key'


class KeyPath(Parameter):
    """Defines a path to a SSH private key or cert file."""

    KEY = 'keypath'
    DEFAULT = str(Path('~/.ssh/id_rsa').expanduser())


class KeyType(Parameter):
    """Defines a SSH public/private key or cert algorithm."""

    KEY = 'keytype'
    DEFAULT = 'RSAKey'
    ENUM = KeyTypes


class KeyPassword(Parameter):
    """Defines the password for decrypting a private key file."""

    KEY = 'key_password'
    ALIAS = 'keypass'


class SSHUser(Parameter):
    """Defines the user for logging into a remote server."""

    KEY = 'ssh_username'
    ALIAS = 'sshuser'


class SSHPassword(Parameter):
    """Defines the password for logging into a remote server."""

    KEY = 'ssh_password'
    ALIAS = 'sshpass'


class HostWorkingDirectory(Parameter):
    """Defines the host machine working directory for Vagrant or Docker runners."""

    KEY = 'hostwd'
    DEFAULT = '.'


class BindDirectory(Parameter):
    """Defines the bind directory of a guest container or VM to the host machine."""

    KEY = 'bind'
    DEFAULT = '/build_magic'
