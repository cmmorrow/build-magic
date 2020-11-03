""""""

from datetime import datetime
import enum

from build_magic import __version__ as version


class ExitCode(enum.IntEnum):
    """"""
    # These exit codes are taken from pytest.

    PASSED = 0
    FAILED = 1
    INTERRUPTED = 2
    INTERNAL_ERROR = 3
    NO_TESTS = 5


class OutputMethod(enum.Enum):
    """"""

    TEST_START = 'start_test'
    TEST_END = 'end_test'
    STAGE_START = 'start_stage'
    STAGE_END = 'end_stage'
    NO_TESTS = 'no_tests'
    MACRO_STATUS = 'macro_status'
    ERROR = 'error'


class Output:
    """"""

    def start_test(self, *args, **kwargs):
        """"""
        raise NotImplementedError

    def end_test(self, *args, **kwargs):
        """"""
        raise NotImplementedError

    def start_stage(self, *args, **kwargs):
        """"""
        raise NotImplementedError

    def end_stage(self, *args, **kwargs):
        """"""
        raise NotImplementedError

    def no_tests(self, *args, **kwargs):
        """"""
        raise NotImplementedError

    def macro_status(self, *args, **kwargs):
        """"""
        raise NotImplementedError

    def error(self, *args, **kwargs):
        """"""
        raise NotImplementedError

    def _display(self, *args, **kwargs):
        """"""
        raise NotImplementedError

    def log(self, method, *args, **kwargs):
        """

        :param str|OutputMethod method:
        :param args:
        :param kwargs:
        :return:
        """
        if isinstance(method, OutputMethod):
            method = method.value
        func = getattr(self, method)
        func(*args, **kwargs)


class Basic(Output):
    """"""

    def _display(self, line):
        """"""
        print(line)

    def start_test(self):
        """"""
        message = 'build-magic {} started at {}\n'.format(version, datetime.now().strftime('%c'))
        self._display(message)

    def end_test(self, status_code):
        """"""
        message = 'build-magic finished with status code {}'.format(status_code)
        self._display(message)

    def start_stage(self, stage_number):
        """"""
        message = 'Starting Stage {}'.format(stage_number)
        self._display(message)

    def end_stage(self, stage_number, status_code):
        """"""
        result = 'DONE'
        if status_code > 0:
            result = 'FAIL'
        message = 'Stage {} complete with result {}'.format(stage_number, result)
        self._display(message)

    def no_tests(self):
        """"""
        self._display('No commands to run. Use --help for usage. Exiting...')

    def macro_status(self, command_type, command, status_code):
        """"""
        result = 'DONE'
        if status_code > 0:
            result = 'FAIL'
        if not command:
            message = '[ {} ] {}'.format(result, command_type)
        else:
            message = '[ {} ] {} : {}'.format(result, command_type, command)
        self._display(message)

    def error(self, err):
        """"""
        message = '[ERROR ] {}'.format(err)
        self._display(message)
