"""Module for defining build-magic output functionality."""

from datetime import datetime
import enum
import sys

from blessings import Terminal
from colorama import init

from build_magic import __version__ as version


class ExitCode(enum.IntEnum):
    """Valid build-magic exit codes."""
    # These exit codes are based on pytest.

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


class Output:
    """Interface for defining output methods."""

    def __init__(self):
        """Instantiates a new Output class."""
        self.timer = None

    def start_job(self, *args, **kwargs):
        """Indicates the beginning of a sequence of stages."""
        raise NotImplementedError

    def end_job(self, *args, **kwargs):
        """Indicates the end of a build-magic session."""
        raise NotImplementedError

    def start_stage(self, *args, **kwargs):
        """Indicates the beginning of a stage."""
        raise NotImplementedError

    def end_stage(self, *args, **kwargs):
        """Indicates the end of a stage."""
        raise NotImplementedError

    def no_job(self, *args, **kwargs):
        """Indicates there are no commands to execute."""
        raise NotImplementedError

    def macro_start(self, *args, **kwargs):
        """Indicates the beginning of a command."""
        raise NotImplementedError

    def macro_status(self, *args, **kwargs):
        """Indicates the success status of a command."""
        raise NotImplementedError

    def error(self, *args, **kwargs):
        """Communicates an error message."""
        raise NotImplementedError

    def info(self, *args, **kwargs):
        """Communicates a general information message."""
        raise NotImplementedError

    @staticmethod
    def _display(line, err=False):
        """Prints a message to stdout.

        :param str line: The message to print.
        :param bool err: If True, output will be written to sys.stderr.
        :return: None
        """
        if err:
            print(line, file=sys.stderr)
        else:
            print(line)

    def log(self, method, *args, **kwargs):
        """Generic method for calling valid output methods.

        :param str|OutputMethod method: The output method to use.
        :param args: Optional arguments to pass to the output method.
        :param kwargs: Optional kwargs to pass to the output method.
        :return: None
        """
        if isinstance(method, OutputMethod):
            method = method.value
        func = getattr(self, method)
        func(*args, **kwargs)


class Basic(Output):
    """Prototype output to the commandline used for testing."""

    def start_job(self):
        """Indicates the beginning of a sequence of stages."""
        message = 'build-magic {} started at {}\n'.format(version, datetime.now().strftime('%c'))
        self._display(message)
        self.timer = datetime.now()

    def end_job(self):
        """Indicates the end of a build-magic session.

        :return: None
        """
        if self.timer:
            delta = datetime.now() - self.timer
            message = 'build-magic finished in {:.3f} seconds'.format(delta.total_seconds())
        else:
            message = 'build-magic finished at {}'.format(datetime.now().isoformat())
        self._display(message)

    def start_stage(self, stage_number=1):
        """Indicates the beginning of a stage.

        :param int stage_number: The stage sequence number.
        :return: None
        """
        message = 'Starting Stage {}'.format(stage_number)
        self._display(message)

    def end_stage(self, stage_number=1, status_code=0):
        """Indicates the end of a stage.

        :param int stage_number: The stage sequence number.
        :param int status_code: The highest exit code for the stage.
        :return: None
        """
        result = 'DONE'
        if status_code > 0:
            result = 'FAIL'
        message = 'Stage {} complete with result {}'.format(stage_number, result)
        self._display(message)

    def no_job(self):
        """Indicates there are no commands to execute."""
        self._display('No commands to run. Use --help for usage. Exiting...')

    def macro_start(self, *args, **kwargs):
        """Not used by the Basic Output class."""
        return

    def macro_status(self, directive, command='', status_code=0):
        """Indicates the success status of a command.

        :param str directive: The executed macro's directive.
        :param str command: The executed command.
        :param status_code: The macro's exit code.
        :return: None
        """
        result = 'DONE'
        if status_code > 0:
            result = 'FAIL'
        if not command:
            message = '{} [ {:<6}] {:<8}'.format(datetime.now().isoformat(), result, directive.upper())
        else:
            message = '{} [ {:<6}] {:<8} : {}'.format(datetime.now().isoformat(), result, directive.upper(), command)
        self._display(message)

    def error(self, err):
        """Communicates an error message.

        :param str err: The error message to display.
        :return: None
        """
        message = '{} [ ERROR ] {}'.format(datetime.now().isoformat(), err)
        self._display(message)

    def info(self, msg):
        """Communicates a general information message.

        :param str msg: The message to print.
        :return: None
        """
        message = '{} [ INFO  ] OUTPUT   : {}'.format(datetime.now().isoformat(), msg)
        self._display(message)


class Tty(Output):
    """Fancy output when using a Terminal."""

    def __init__(self):
        """Instantiates a new Tty class."""
        super().__init__()
        init()
        self._term = Terminal()

    def get_width(self):
        """If using a terminal, get the width, otherwise set it manually."""
        if self._term.does_styling:
            return self._term.width
        else:
            return 80

    def get_height(self):
        """If using a terminal, get the height, otherwise set it manually."""
        if self._term.does_styling:
            return self._term.height
        else:
            return 20

    def start_job(self):
        """Indicates the beginning of a sequence of stages."""
        message = self._term.cyan + self._term.bold + 'build-magic {}\n'.format(version) + self._term.normal
        message += self._term.cyan + 'Start time {}\n'.format(datetime.now().strftime('%c')) + self._term.normal
        self._display(message)
        self.timer = datetime.now()

    def end_job(self):
        """Indicates the end of a build-magic session.

        :return: None
        """
        if self.timer:
            delta = datetime.now() - self.timer
            message = 'build-magic finished in {:.3f} seconds'.format(delta.total_seconds())
        else:
            message = 'build-magic finished at {}'.format(datetime.now().strftime('%c'))
        self._display(message)

    def start_stage(self, stage_number=1):
        """Indicates the beginning of a stage.

        :param int stage_number: The stage sequence number.
        :return: None
        """
        message = self._term.underline + 'Starting Stage {}'.format(stage_number) + self._term.normal
        self._display(message)

    def end_stage(self, stage_name=1, status_code=0):
        """Indicates the end of a stage.

        :param int stage_name: The stage sequence number.
        :param int status_code: The highest exit code for the stage.
        :return: None
        """
        color = self._term.bold_green
        result = 'COMPLETE'
        if status_code > 0:
            color = self._term.bold_red
            result = 'FAILED'
        message = 'Stage {} finished with result {}{}{}\n'.format(stage_name, color, result, self._term.normal)
        self._display(message)

    def no_job(self):
        """Indicates there are no commands to execute."""
        self._display(self._term.yellow + 'No commands to run. Use --help for usage. Exiting...')

    def macro_start(self, directive, command=''):
        """Indicates the start of a command.

        :param str directive: The directive of the executing command.
        :param str command: The current executing command.
        :return: None
        """
        width = self.get_width()
        status = self._term.bold_yellow + 'RUNNING' + self._term.normal
        spacing = width - 22 - len(command)
        if len(command) + 11 > width - 11:
            command = command[:width - 23] + '....'
        if not command:
            message = '{} {} {}'.format(directive.upper(), command, '.' * spacing, status)
        else:
            message = '{:<8}: {} {} {}'.format(directive.upper(), command, '.' * spacing, status)
        self._display(message)

    def macro_status(self, directive='', command='', status_code=0):
        """Indicates the success status of a command.

        :param str directive: The executed macro's directive.
        :param str command: The executed command.
        :param status_code: The macro's exit code.
        :return: None
        """
        width = self.get_width()
        position = width - 10
        height = self.get_height() - 2
        if status_code > 0:
            result = self._term.bold_red + '{:<8}'.format('FAILED') + self._term.normal
        else:
            result = self._term.bold_green + '{:<8}'.format('COMPLETE') + self._term.normal
        with self._term.location(position, height):
            self._display(result)

    def error(self, err):
        """Communicates an error message.

        :param str err: The error message to display.
        :return: None
        """
        width = self.get_width()
        position = width - 10
        height = self.get_height() - 2
        result = self._term.bold_red + '{:<8}'.format('ERROR') + self._term.normal
        with self._term.location(position, height):
            self._display(result)
        self._display(self._term.red + str(err) + self._term.normal, err=True)

    def info(self, msg):
        """Communicates a general information message.

        :param str msg: The message to print.
        :return: None
        """
        message = 'OUTPUT  : {}'.format(msg)
        self._display(message)


class Silent(Output):
    """Silent output that suppresses output."""

    def start_job(self, *args, **kwargs):
        """Indicates the beginning of a sequence of stages."""
        return

    def end_job(self, *args, **kwargs):
        """Indicates the end of a build-magic session."""
        return

    def start_stage(self, *args, **kwargs):
        """Indicates the beginning of a stage."""
        return

    def end_stage(self, *args, **kwargs):
        """Indicates the end of a stage."""
        return

    def no_job(self, *args, **kwargs):
        """Indicates there are no commands to execute."""
        return

    def macro_start(self, *args, **kwargs):
        """Indicates the beginning of a command."""
        return

    def macro_status(self, *args, **kwargs):
        """Indicates the success status of a command."""
        return

    def error(self, *args, **kwargs):
        """Communicates an error message."""
        return

    def info(self, *args, **kwargs):
        """Communicates a general information message."""
        return
