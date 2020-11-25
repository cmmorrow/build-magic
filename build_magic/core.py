"""Module for defining build-magic core classes and exceptions."""

from enum import Enum, unique
from pathlib import Path
import sys
import types

from build_magic import actions, output, runner
from build_magic.macro import MacroFactory


mode = output.OutputMethod
_output = output.Basic()


class ExecutionError(Exception):
    """A general build-magic execution error."""


class SetupError(Exception):
    """An error when setting up a CommandRunner."""


class TeardownError(Exception):
    """An error when tearing down a CommandRunner."""


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
    def available(cls):
        """Provides the enum values as a list.

        :return: A list of available enum values.
        """
        return [src.value for src in cls.__members__.values()]


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
    ISOLATE = 'isolate'


class Engine:
    """The primary driver in build-magic. The engine executes stages and reports on the results."""

    @classmethod
    def run(cls, stages, continue_on_fail=False):
        """Executes stages and reports the results.

        :param list[Stage] stages: The stage or stages to execute.
        :param bool continue_on_fail:
        :return: The highest status code reported by a stage.
        """
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
    """Validates and generates Stage objects."""

    @classmethod
    def build(cls, sequence, runner_type, directives, artifacts, commands, environment, action, copy, wd):
        """Validates inputs and generates a new Stage object.

        :param int sequence: The sequence order to run the stage in.
        :param str runner_type: The command runner to use for executing commands.
        :param list[str] directives: The Stage directives to execute.
        :param list[str] artifacts: The Stage artifacts to work on.
        :param list[str] commands: The Stage commands to execute.
        :param str environment: The Stage environment to use.
        :param str action: The Stage action to use for execution.
        :param str copy: The directory to copy artifacts from, to the working directory.
        :param str wd: The working directory to use for executing commands.
        :rtype: Stage
        :return: The generated Stage object.
        """
        if runner_type not in Runners.available():
            raise ValueError('Runner must be one of {}.'.format(', '.join(Runners.available())))

        for directive in directives:
            if directive not in Directive.available():
                raise ValueError(
                    'Directive must be one of {}'.format(', '.join(Directive.available()))
                )

        if not artifacts:
            artifacts = []

        if not commands:
            _output.log(mode.NO_TESTS)
            sys.exit(output.ExitCode.NO_TESTS)

        if runner_type == Runners.VAGRANT.value and not environment:
            raise ValueError('Environment must be a path to a Vagrant file if using the Vagrant runner.')

        if runner_type == Runners.DOCKER.value and not environment:
            raise ValueError('Environment must be a Docker image if using the Docker runner.')

        if not Path(copy).exists():
            raise NotADirectoryError(f'Path {copy} does not exist.')

        if not Path(wd).exists():
            raise NotADirectoryError(f'Path {wd} does not exist or is not a directory.')

        if len(commands) != (len(directives)):
            raise ValueError('Length of commands unequal to length of command types.')

        if action not in Actions.available():
            raise ValueError('Action must be one of {}.'.format(', '.join(Actions.available())))

        return Stage(runner_type, environment, artifacts, commands, directives, sequence, action, copy, wd)


class Stage:
    """A bundle of commands to execute in order, with a particular CommandRunner, environment, and action."""

    __slots__ = [
        '_action',
        '_command_runner',
        '_directives',
        '_macros',
        '_result',
        '_results',
        '_runner',
        '_sequence',
    ]

    def __init__(self, runner_type, environment, artifacts, commands, directives, sequence, action, copy, wd):
        """Instantiates a new Stage object.

        Note: Stage objects should not be constructed directly and should instead be created by a StageFactory.

        :param str runner_type: The CommandRunner to use.
        :param environment: The environment the CommandRunner will use.
        :param int sequence: The execution order of the macros.
        :param list[str] artifacts: The artifacts to operate on.
        :param list[str] commands: The commands to execute.
        :param list[str] directives: The command directives.
        :param str action: The Action to use.
        :param str copy: The path to copy artifacts from.
        :param str wd: The working directory to use.
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
        self._command_runner = command_runner(environment, working_dir=wd, copy_dir=copy, artifacts=artifacts)
        factory = MacroFactory(commands, suffixes=artifacts)
        self._macros = sorted(factory.generate(), key=lambda m: m.sequence)
        self._results = []
        self._result = 0
        self._runner = runner_type

    @property
    def sequence(self):
        """The stage execution order."""
        return self._sequence

    def run(self, continue_on_fail=False):
        """Executes the commands in the Stage.

        :param bool continue_on_fail: If True, keep running commands even if the last command failed. Default is False.
        :return: The highest Stage result.
        """
        # Dynamically bind the action's provision function to the command runner object.
        provision_name = self._action.mapping[actions.SETUP_METHOD].get(self._runner, actions.DEFAULT_METHOD)
        provision = getattr(actions, provision_name)
        self._command_runner.provision = types.MethodType(provision, self._command_runner)

        # Dynamically bind the action's teardown function to the command runner object.
        teardown_name = self._action.mapping[actions.TEARDOWN_METHOD].get(self._runner, actions.DEFAULT_METHOD)
        teardown = getattr(actions, teardown_name)
        self._command_runner.teardown = types.MethodType(teardown, self._command_runner)

        # Call the command runner's prepare function first.
        self._command_runner.prepare()

        # Call the provision method.
        result = self._command_runner.provision()
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
                _output.log(mode.ERROR, status.stderr.decode('utf-8'))
                break

        # Call the teardown method.
        result = self._command_runner.teardown()
        if not result:
            raise TeardownError('Teardown failed.')

        fails = map(lambda r: True if r.exit_code > 0 else False, self._results)
        if any(fails):
            self._result = 1

        return self._result
