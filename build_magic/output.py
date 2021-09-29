"""Module for defining build-magic output functionality."""

from datetime import datetime
import os
import sys

from colorama import Cursor, Fore, init, Style

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
        message = f'{datetime.now().isoformat()} build-magic [ INFO  ] Finished'
        if self.timer:
            delta = datetime.now() - self.timer
            message = f'{message} in {delta.total_seconds():.3f}'
        self._display(message)

    def start_stage(self, stage_number=1, name=None):
        """Indicates the beginning of a stage.

        :param int stage_number: The stage sequence number.
        :param str|None name: The stage name if given.
        :return: None
        """
        message = f'{datetime.now().isoformat()} build-magic [ INFO  ] Starting Stage {stage_number}'
        if name:
            message = f'{message}: {name}'
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

    def macro_status(self, directive, command='', status_code=0, sequence=1, total=1):
        """Indicates the success status of a command.

        :param str directive: The executed macro's directive.
        :param str command: The executed command.
        :param int status_code: The macro's exit code.
        :param int sequence: The macro sequence.
        :param int total: The total number of macros per stage.
        :return: None
        """
        result = 'DONE'
        length = len(str(total))
        seq = f'( {sequence:>{length}}/{total:>{length}} )'
        if status_code > 0:
            result = 'FAIL'
        message = f'{datetime.now().isoformat()} build-magic [ {result:<6}] {seq} {directive.upper():<8}'
        if command:
            message = f'{message} : {command}'
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
        msg = msg.rstrip()
        message = f'{datetime.now().isoformat()} build-magic [ INFO  ] OUTPUT: {msg}'
        self._display(message)

    def process_spinner(self, *args, **kwargs):
        """Not used by the Basic Output class."""
        return


class Tty(Output):
    """Fancy output when using a Terminal."""

    def __init__(self):
        """Instantiates a new Tty class."""
        super().__init__()
        init()

    @staticmethod
    def get_width():
        """If using a terminal, get the width, otherwise set it manually."""
        try:
            term = os.get_terminal_size()
            return term.columns
        except OSError:
            return 80

    @staticmethod
    def get_height():
        """If using a terminal, get the height, otherwise set it manually."""
        try:
            term = os.get_terminal_size()
            return term.lines
        except OSError:
            return 20

    def start_job(self):
        """Indicates the beginning of a sequence of stages."""
        # Create the hammer glyph only if using a TTY and on Mac or Linux.
        emoji = '\U0001f528' if sys.stdout.isatty() and sys.platform != 'win32' else ''
        message = Fore.CYAN + Style.BRIGHT + f'build-magic{emoji} {version}\n' + Style.RESET_ALL
        message += Fore.CYAN + f'Start time {datetime.now().strftime("%c")}\n' + Style.RESET_ALL
        self._display(message)
        self.timer = datetime.now()

    def end_job(self):
        """Indicates the end of a build-magic session.

        :return: None
        """
        # Create the sparkle glyph only if using a TTY and on Mac or Linux.
        emoji = '\u2728' if sys.stdout.isatty() and sys.platform != 'win32' else ''
        if self.timer:
            delta = datetime.now() - self.timer
            message = f'build-magic{emoji} finished in {delta.total_seconds():.3f} seconds'
        else:
            message = f'build-magic{emoji} finished at {datetime.now().strftime("%c")}'
        self._display(message)

    def start_stage(self, stage_number=1, name=None):
        """Indicates the beginning of a stage.

        :param int stage_number: The stage sequence number.
        :param str|None name: The stage name if given.
        :return: None
        """
        message = f'Starting Stage {stage_number}'
        if name:
            message += f': {name}'
        self._display(message)

    def end_stage(self, stage_name=1, status_code=0, name=None):
        """Indicates the end of a stage.

        :param int stage_name: The stage sequence number.
        :param int status_code: The highest exit code for the stage.
        :param str|None name: The stage name if given.
        :return: None
        """
        color = Fore.GREEN + Style.BRIGHT
        result = 'DONE'
        if status_code > 0:
            color = Fore.RED + Style.BRIGHT
            result = 'FAILED'
        if name:
            message = f'Stage {stage_name}: {name} - finished with result {color}{result}{Style.RESET_ALL}\n'
        else:
            message = f'Stage {stage_name} finished with result {color}{result}{Style.RESET_ALL}\n'
        self._display(message)

    def no_job(self):
        """Indicates there are no commands to execute."""
        self._display(Fore.YELLOW + 'No commands to run. Use --help for usage. Exiting...')

    def macro_start(self, directive, command='', sequence=1, total=1):
        """Indicates the start of a command.

        :param str directive: The directive of the executing command.
        :param str command: The current executing command.
        :param int sequence: The macro sequence.
        :param int total: The total number of macros per stage.
        :return: None
        """
        width = self.get_width()
        command = command.strip()
        status = Fore.YELLOW + Style.BRIGHT + 'RUNNING' + Style.RESET_ALL
        seq_length = len(str(total))
        seq = f'( {sequence:>{seq_length}}/{total:>{seq_length}} )'
        spacing = width - 23 - len(command) - len(seq)
        if not command:
            message = f'{directive.upper()} {"." * spacing}'
        elif len(command) + 12 + len(seq) > width - 11:
            command = command[:width - 27 - len(seq)] + ' ....'
            message = f'{seq} {directive.upper():<8}: {command} {status:<8}'
        else:
            message = f'{seq} {directive.upper():<8}: {command} {"." * spacing} {status:<8}'
        self._display(message)

    def macro_status(self, directive='', command='', status_code=0, sequence=1, total=1):
        """Indicates the success status of a command.

        :param str directive: The executed macro's directive.
        :param str command: The executed command.
        :param status_code: The macro's exit code.
        :param int sequence: The macro sequence.
        :param int total: The total number of macros per stage.
        :return: None
        """
        def format_(color, status):
            return color + Style.BRIGHT + f'{status:<8}' + Style.RESET_ALL

        width = self.get_width()
        position = width - 10
        if status_code > 0:
            result = format_(Fore.RED, 'FAILED')
        else:
            result = format_(Fore.GREEN, 'COMPLETE')
        self._display(Cursor.UP(1) + Cursor.FORWARD(position) + result)

    def error(self, err):
        """Communicates an error message.

        :param str err: The error message to display.
        :return: None
        """
        width = self.get_width()
        position = width - 10
        result = Fore.RED + Style.BRIGHT + '{:<8}'.format('ERROR') + Style.RESET_ALL
        self._display(Cursor.UP(1) + Cursor.FORWARD(position) + result)
        self._display(Fore.RED + str(err) + Style.RESET_ALL, err=True)

    def info(self, msg):
        """Communicates a general information message.

        :param str msg: The message to print.
        :return: None
        """
        msg = msg.rstrip()
        message = 'OUTPUT: {}'.format(msg)
        self._display(message)

    @staticmethod
    def process_spinner(spinner, process_active=False):
        """Indicates whether a process is underway.

        :param yaspin  spinner: Yaspin spinner object.
        :param boolean process_active: Process activity status.
        :return: None
        """
        if process_active:
            spinner.start()
        else:
            spinner.stop()


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

    def process_spinner(self, *args, **kwargs):
        """Indicates whether a process is underway."""
        return
