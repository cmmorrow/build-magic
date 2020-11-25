"""Module for defining build-magic output functionality."""

from datetime import datetime
import enum

from build_magic import __version__ as version


class ExitCode(enum.IntEnum):
    """Valid build-magic exit codes."""
    # These exit codes are taken from pytest.

    PASSED = 0
    FAILED = 1
    INTERRUPTED = 2
    INTERNAL_ERROR = 3
    NO_TESTS = 5


class OutputMethod(enum.Enum):
    """Valid build-magic output methods."""

    TEST_START = 'start_test'
    TEST_END = 'end_test'
    STAGE_START = 'start_stage'
    STAGE_END = 'end_stage'
    NO_TESTS = 'no_tests'
    MACRO_STATUS = 'macro_status'
    ERROR = 'error'


class Output:
    """Interface for defining output methods."""

    def start_test(self, *args, **kwargs):
        """Indicates the beginning of a sequence of stages."""
        raise NotImplementedError

    def end_test(self, *args, **kwargs):
        """Indicates the end of a build-magic session."""
        raise NotImplementedError

    def start_stage(self, *args, **kwargs):
        """Indicates the beginning of a stage."""
        raise NotImplementedError

    def end_stage(self, *args, **kwargs):
        """Indicates the end of a stage."""
        raise NotImplementedError

    def no_tests(self, *args, **kwargs):
        """Indicates there are no commands to execute."""
        raise NotImplementedError

    def macro_status(self, *args, **kwargs):
        """Indicates the success status of a command."""
        raise NotImplementedError

    def error(self, *args, **kwargs):
        """Communicates an error message."""
        raise NotImplementedError

    def _display(self, *args, **kwargs):
        """Method that displays an output method."""
        raise NotImplementedError

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

    def _display(self, line):
        """Prints a message to stdout.

        :param str line: The message to print.
        :return: None
        """
        print(line)

    def start_test(self):
        """Indicates the beginning of a sequence of stages."""
        message = 'build-magic {} started at {}\n'.format(version, datetime.now().strftime('%c'))
        self._display(message)

    def end_test(self, status_code):
        """Indicates the end of a build-magic session.

        :param int status_code: The build-magic exit code.
        :return: None
        """
        message = 'build-magic finished with status code {}'.format(status_code)
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

    def no_tests(self):
        """Indicates there are no commands to execute."""
        self._display('No commands to run. Use --help for usage. Exiting...')

    def macro_status(self, directive, command, status_code):
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
            message = '[ {} ] {}'.format(result, directive)
        else:
            message = '[ {} ] {} : {}'.format(result, directive, command)
        self._display(message)

    def error(self, err):
        """Communicates an error message.

        :param str err: The error message to display.
        :return: None
        """
        message = '[ERROR ] {}'.format(err)
        self._display(message)
