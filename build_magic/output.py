"""Module for defining build-magic output functionality."""

from datetime import datetime
import sys

from blessings import Terminal
from colorama import init

from build_magic import __version__ as version
from build_magic.reference import OutputMethod


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

        :param str|build_magic.reference.OutputMethod method: The output method to use.
        :param args: Optional arguments to pass to the output method.
        :param kwargs: Optional kwargs to pass to the output method.
        :return: None
        """
        if isinstance(method, OutputMethod):
            method = method.value
        func = getattr(self, method)
        func(*args, **kwargs)

    def print_output(self, message, is_error=False):
        """High level method for printing a message to stdout.

        :param str|bytes message: The message to print to stdout.
        :param bool is_error: Prints using the error format if True, otherwise prints using the info format.
        :return: None
        """
        level = OutputMethod.ERROR if is_error else OutputMethod.INFO
        if isinstance(message, bytes):
            out = message.decode('utf-8')
        else:
            out = str(message)
        self.log(level, out)


class Basic(Output):
    """Prototype output to the commandline used for testing."""

    def start_job(self):
        """Indicates the beginning of a sequence of stages."""
        message = f'{datetime.now().isoformat()} build-magic [ INFO  ] version {version}'
        self._display(message)
        self.timer = datetime.now()

    def end_job(self):
        """Indicates the end of a build-magic session.

        :return: None
        """
        if self.timer:
            delta = datetime.now() - self.timer
            message = f'{datetime.now().isoformat()} build-magic [ INFO  ] finished in {delta.total_seconds():.3f}'
        else:
            message = f'{datetime.now().isoformat()} build-magic [ INFO  ] finished'
        self._display(message)

    def start_stage(self, stage_number=1, name=None):
        """Indicates the beginning of a stage.

        :param int stage_number: The stage sequence number.
        :param str|None name: The stage name if given.
        :return: None
        """
        if name:
            message = f'{datetime.now().isoformat()} build-magic [ INFO  ] Starting Stage {stage_number}: {name}'
        else:
            message = f'{datetime.now().isoformat()} build-magic [ INFO  ] Starting Stage {stage_number}'
        self._display(message)

    def end_stage(self, stage_number=1, status_code=0, name=None):
        """Indicates the end of a stage.

        :param int stage_number: The stage sequence number.
        :param int status_code: The highest exit code for the stage.
        :param str|None name: The stage name if given.
        :return: None
        """
        result = 'DONE'
        if status_code > 0:
            result = 'FAIL'
        if name:
            message = f'{datetime.now().isoformat()} build-magic [ INFO  ] Stage {stage_number}: {name} - ' \
                      f'complete with result {result}'
        else:
            message = f'{datetime.now().isoformat()} build-magic [ INFO  ] Stage {stage_number} ' \
                      f'complete with result {result}'
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
            message = f'{datetime.now().isoformat()} build-magic [ {result:<6}] {directive.upper():<8}'
        else:
            message = f'{datetime.now().isoformat()} build-magic [ {result:<6}] {directive.upper():<8} : {command}'
        self._display(message)

    def error(self, err):
        """Communicates an error message.

        :param str err: The error message to display.
        :return: None
        """
        message = f'{datetime.now().isoformat()} build-magic [ ERROR ] {err}'
        self._display(message)

    def info(self, msg):
        """Communicates a general information message.

        :param str msg: The message to print.
        :return: None
        """
        message = f'{datetime.now().isoformat()} build-magic [ INFO  ] OUTPUT   : {msg}'
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

    def start_stage(self, stage_number=1, name=None):
        """Indicates the beginning of a stage.

        :param int stage_number: The stage sequence number.
        :param str|None name: The stage name if given.
        :return: None
        """
        if name:
            message = self._term.underline + f'Starting Stage {stage_number}: {name}' + self._term.normal
        else:
            message = self._term.underline + f'Starting Stage {stage_number}' + self._term.normal
        self._display(message)

    def end_stage(self, stage_name=1, status_code=0, name=None):
        """Indicates the end of a stage.

        :param int stage_name: The stage sequence number.
        :param int status_code: The highest exit code for the stage.
        :param str|None name: The stage name if given.
        :return: None
        """
        color = self._term.bold_green
        result = 'COMPLETE'
        if status_code > 0:
            color = self._term.bold_red
            result = 'FAILED'
        if name:
            message = f'Stage {stage_name}: {name} - finished with result {color}{result}{self._term.normal}\n'
        else:
            message = f'Stage {stage_name} finished with result {color}{result}{self._term.normal}\n'
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
