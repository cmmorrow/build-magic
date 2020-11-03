""""""

from enum import Enum, unique
import sys
import types

from build_magic import actions, output, runner
from build_magic.macro import MacroFactory


mode = output.OutputMethod
_output = output.Basic()


class ExecutionError(Exception):
    """"""


class SetupError(Exception):
    """"""


class TeardownError(Exception):
    """"""


class EnumExt(Enum):
    """Extension for the builtin Enum class."""

    def __contains__(self, item):
        """"""
        values = self.available()
        return item in values

    @classmethod
    def available(cls):
        """"""
        return cls._member_names_


@unique
class Runners(EnumExt):
    """"""

    LOCAL = 'Local'
    REMOTE = 'Remote'
    VAGRANT = 'Vagrant'
    DOCKER = 'Docker'


@unique
class Directive(EnumExt):
    """"""

    BUILD = 'build'
    INSTALL = 'install'
    EXECUTE = 'execute'


@unique
class Actions(EnumExt):
    """"""

    DEFAULT = 'Default'
    CLEANUP = 'Cleanup'
    VERBOSE = 'Verbose'


class Engine:
    """"""

    @classmethod
    def run(cls, stages, continue_on_fail=False):
        """"""
        # Initialize the status code to 0.
        status_code = output.ExitCode.PASSED.value

        # Start
        _output.log(mode.TEST_START)

        # Sort stages by sequence.
        if len(stages) > 1:
            stages = sorted(stages, key=lambda s: s.sequence)

        for stage in stages:
            # Run the stage.
            _output.log(mode.STAGE_START, stage.sequence)
            exit_code = stage.run(continue_on_fail)
            if exit_code > status_code:
                status_code = exit_code
            _output.log(mode.STAGE_END, stage.sequence, exit_code)

        # TODO: This is the wrong status code - fix it.
        _output.log(mode.TEST_END, status_code)
        return status_code


class StageFactory:
    """"""

    @classmethod
    def build(cls, sequence, runner_type, directives, artifacts, commands, environment, action):
        """

        :param int sequence:
        :param str runner_type:
        :param list[str] directives:
        :param list[str] artifacts:
        :param list[str] commands:
        :param str environment:
        :param str action:
        :return:
        """
        if runner_type.upper() not in Runners.available():
            raise ValueError('Runner must be one of {}.'.format(', '.join(Runners.available())))

        for directive in directives:
            if directive.upper() not in Directive.available():
                raise ValueError(
                    'Directive must be one of {}'.format(', '.join(Directive.available()))
                )

        if not artifacts:
            artifacts = []

        if not commands:
            _output.log(mode.NO_TESTS)
            sys.exit(output.ExitCode.NO_TESTS)

        if runner_type == Runners.VAGRANT.name and not environment:
            raise ValueError('Environment must be a path to a Vagrant file if using the Vagrant runner.')

        if runner_type == Runners.DOCKER.name and not environment:
            raise ValueError('Environment must be a Docker image if using the Docker runner.')

        if len(commands) != (len(directives)):
            raise ValueError('Length of commands unequal to length of command types.')

        if action.upper() not in Actions.available():
            raise ValueError('Action must be one of {}.'.format(', '.join(Actions.available())))

        return Stage(runner_type, environment, artifacts, commands, directives, sequence, action)


class Stage:
    """"""

    __slots__ = ['_action', '_command_runner', '_directives', '_macros', '_result', '_results', '_runner', '_sequence']

    def __init__(self, runner_type, environment, artifacts, commands, directives, sequence, action):
        """

        :param str runner_type:
        :param environment:
        :param int sequence:
        :param list[str] artifacts:
        :param list[str] commands:
        :param list[str] directives:
        :param str action:
        """
        try:
            command_runner = getattr(runner, runner_type.capitalize())
        except AttributeError:
            raise ValueError('Runner must be one of {}.'.format(', '.join(runner.Runners.available())))

        try:
            self._action = getattr(actions, action.capitalize())
        except AttributeError:
            raise ValueError('Action must be one of {}.'.format(', '.join(Actions.available())))
        self._sequence = sequence
        self._directives = directives
        self._command_runner = command_runner(environment)
        factory = MacroFactory(commands, suffixes=artifacts)
        self._macros = sorted(factory.generate(), key=lambda m: m.sequence)
        self._results = []
        self._result = 0
        self._runner = runner

    @property
    def sequence(self):
        """"""
        return self._sequence

    def run(self, continue_on_fail=False):
        """"""
        # Dynamically bind the action's provision function to the command runner object.
        provision_name = self._action.mapping[actions.SETUP_METHOD].get(self._runner, actions.DEFAULT_METHOD)
        provision = getattr(actions, provision_name)
        self._command_runner.provision = types.MethodType(provision, self._command_runner)

        # Dynamically bind the action's teardown function to the command runner object.
        teardown_name = self._action.mapping[actions.TEARDOWN_METHOD].get(self._runner, actions.DEFAULT_METHOD)
        teardown = getattr(actions, teardown_name)
        self._command_runner.teardown = types.MethodType(teardown, self._command_runner)

        # Call the provision method.
        result = self._command_runner.provision
        if not result:
            raise SetupError('Setup failed.')

        for mac in self._macros:
            directive = self._directives[mac.sequence]

            if self._action.add_prefix.get(self._runner):
                mac.prefix = self._action.add_prefix[self._runner]

            if self._action.add_suffix.get(self._runner):
                mac.suffix = self._action.add_suffix[self._runner]

            # Run the macro.
            status = self._command_runner.execute(mac)
            _output.log(mode.MACRO_STATUS, directive, mac.command, status.exit_code)
            self._results.append(status)
            if status.exit_code > 0 and not continue_on_fail:
                _output.log(mode.ERROR, status.stdout)
                # if self._directives[-1] == runner.Directive.TEARDOWN.value.lower():
                #     func = getattr(self._command_runner, runner.Directive.TEARDOWN.value)
                #     status = func(self._macros[-1])
                #     _output.log(mode.MACRO_STATUS, self._directives[-1], '', status.exit_code)
                break

        # Call the teardown method.
        result = self._command_runner.teardown
        if not result:
            raise TeardownError('Teardown failed.')

        fails = map(lambda r: True if r.exit_code > 0 else False, self._results)
        if any(fails):
            self._result = 1

        return self._result
