"""Module for defining build-magic core classes and exceptions."""

from enum import Enum, unique
from pathlib import Path
import types

from build_magic import actions, output, runner
from build_magic.macro import MacroFactory


mode = output.OutputMethod
_output = output.Tty()


OUTPUT_TYPES = {
    'plain': 'Basic',
    'fancy': 'Tty',
}


class ExecutionError(Exception):
    """A general build-magic execution error."""


class SetupError(Exception):
    """An error when setting up a CommandRunner."""


class TeardownError(Exception):
    """An error when tearing down a CommandRunner."""


class NoJobs(Exception):
    """There are no jobs to execute."""


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
    """The primary driver in build-magic. The engine executes stages and reports on the results.

    :param bool continue_on_fail: If True, all jobs will attempt to run, even if the previous job failed.
        Otherwise, execution will end after a failed job.
    :param list[Stage]|None stages: The stage or stages to execute.
    """

    __slots__ = ['_continue_on_fail', '_stages']

    def __init__(self, stages=None, continue_on_fail=False, output_format='fancy'):
        """Executes stages and reports the results.

        :param list[Stage]|None stages: The stage or stages to execute.
        :param bool continue_on_fail:
        :param str output_format:
        :return: The highest status code reported by a stage.
        """
        self._continue_on_fail = continue_on_fail
        self._stages = stages or []

        # Sort stages by sequence.
        if len(stages) > 1:
            self._stages = sorted(stages, key=lambda s: s.sequence)

        if output_format not in OUTPUT_TYPES:
            raise ValueError('Output must be one of {}'.format(', '.join(OUTPUT_TYPES.keys())))
        global _output
        _output = getattr(output, OUTPUT_TYPES[output_format])()

    def run(self):
        """Executes stages and reports the results.

        :return: The highest status code reported by a stage.
        """
        # Initialize the status code to 0.
        status_code = output.ExitCode.PASSED.value

        # Start
        _output.log(mode.JOB_START)

        for stage in self._stages:
            # Run the stage.
            _output.log(mode.STAGE_START, stage.sequence)
            stage.setup()
            exit_code = stage.run(self._continue_on_fail)
            if exit_code > status_code:
                status_code = exit_code
            _output.log(mode.STAGE_END, stage.sequence, exit_code)

        # TODO: This is the wrong status code - fix it.
        _output.log(mode.JOB_END)
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
            _output.log(mode.NO_JOB)
            raise NoJobs

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

        # Build the macros.
        factory = MacroFactory(commands, suffixes=artifacts)
        macros = factory.generate()

        # Create the CommandRunner.
        command_runner = getattr(runner, runner_type.capitalize())
        cmd_runner = command_runner(environment, working_dir=wd, copy_dir=copy, artifacts=artifacts)

        return Stage(cmd_runner, macros, directives, sequence, action)


class Stage:
    """A bundle of commands to execute in order, with a particular CommandRunner, environment, and action."""

    __slots__ = [
        '_action',
        '_command_runner',
        '_directives',
        '_is_setup',
        '_macros',
        '_result',
        '_results',
        '_sequence',
    ]

    def __init__(self, cmd_runner, macros, directives, sequence, action):
        """Instantiates a new Stage object.

        Note: Stage objects should not be constructed directly and should instead be created by a StageFactory.

        :param CommandRunner cmd_runner: The CommandRunner to use.
        :param list[Macro] macros: The commands to execute.
        :param list[str] directives: The command directives.
        :param int sequence: The execution order of the macros.
        :param str action: The Action to use.
        """
        try:
            self._action = getattr(actions, action.capitalize())
        except AttributeError:
            raise ValueError('Action must be one of {}.'.format(', '.join(Actions.available())))

        self._command_runner = cmd_runner
        self._macros = macros
        self._directives = directives
        self._sequence = sequence
        self._results = []
        self._result = 0
        self._is_setup = False

    @property
    def sequence(self):
        """The stage execution order."""
        return self._sequence

    @property
    def is_setup(self):
        """True if the setup method was already run, else False."""
        return self._is_setup

    def setup(self):
        """Dynamically set the provision() and teardown() methods for the Command Runner and call it's prepare() method.

        :return: None
        """
        # Dynamically bind the action's provision function to the command runner object.
        provision_name = (
            self._action
                .mapping[actions.SETUP_METHOD]
                .get(self._command_runner.name, actions.DEFAULT_METHOD)
        )
        provision = getattr(actions, provision_name)
        self._command_runner.provision = types.MethodType(provision, self._command_runner)

        # Dynamically bind the action's teardown function to the command runner object.
        teardown_name = (
            self._action
                .mapping[actions.TEARDOWN_METHOD]
                .get(self._command_runner.name, actions.DEFAULT_METHOD)
        )
        teardown = getattr(actions, teardown_name)
        self._command_runner.teardown = types.MethodType(teardown, self._command_runner)

        # Call the command runner's prepare function first.
        self._command_runner.prepare()
        self._is_setup = True

    def run(self, continue_on_fail=False):
        """Executes the commands in the Stage.

        :param bool continue_on_fail: If True, keep running commands even if the last command failed. Default is False.
        :return: The highest Stage result.
        """
        # Setup if not already setup.
        if not self.is_setup:
            self.setup()

        # Call the provision method.
        result = self._command_runner.provision()
        if not result:
            raise SetupError('Setup failed.')

        for mac in self._macros:
            directive = self._directives[mac.sequence]

            # Add the prefix to the macro.
            if self._action.add_prefix.get(self._command_runner.name):
                mac.prefix = self._action.add_prefix[self._command_runner.name]

            # Add the suffix to the macro.
            if self._action.add_suffix.get(self._command_runner.name):
                mac.suffix = self._action.add_suffix[self._command_runner.name]

            # Run the macro.
            try:
                _output.log(mode.MACRO_START, directive, mac.command)
                status = self._command_runner.execute(mac)
            except Exception as err:
                raise ExecutionError(str(err))

            # Handle the result.
            _output.log(mode.MACRO_STATUS, directive, mac.command, status.exit_code)
            self._results.append(status)
            if status.exit_code > 0 and not continue_on_fail:
                _output.log(mode.ERROR, status.stderr.decode('utf-8'))
                break

        # Call the teardown method.
        result = self._command_runner.teardown()
        if not result:
            raise TeardownError('Teardown failed.')

        # Set the exit code.
        fails = map(lambda r: True if r.exit_code > 0 else False, self._results)
        if any(fails):
            self._result = 1

        return self._result
