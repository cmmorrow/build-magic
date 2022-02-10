"""Module for defining build-magic core classes and exceptions."""


from pathlib import Path
import re
import types

import json
from jsonschema import ValidationError, validate as jsvalidator

from yaspin import yaspin

from build_magic import actions, output, runner
from build_magic.exc import ExecutionError, NoJobs, OSEnvironmentMismatch, SetupError, TeardownError
from build_magic.macro import MacroFactory
from build_magic.reference import VARIABLE_PATTERN
from build_magic.reference import Actions, Directive, ExitCode, OutputMethod, OutputTypes, Runners
from build_magic.reference import BindDirectory, HostWorkingDirectory, KeyPassword, KeyPath, KeyType

# Add valid Parameter classes here.
PARAMETERS = (
    BindDirectory,
    HostWorkingDirectory,
    KeyPath,
    KeyType,
    KeyPassword,
)


mode = OutputMethod
_output = output.Tty()


def build_stage(*args, **kwargs):
    """Helper function for building stage objects."""
    return StageFactory.build(*args, **kwargs)


def iterate_sequence():
    """Increments the output sequence by one each time it's called.

    :rtype: Iterator[int]
    :return: The iterative sequence value.
    """
    seq = 1
    while True:
        yield seq
        seq += 1


def generate_config_template():
    """Reads the static config file template and writes the contents to a template in the current directory.

    :rtype: Path
    :return: The newly created config file.
    """
    filename = 'build-magic_template.yaml'
    current = Path().cwd().resolve()
    file = current / filename
    if file.exists():
        raise FileExistsError

    template = Path(__file__).parent / 'static' / filename
    content = template.read_text()
    file.write_text(content)
    return file


def config_parser(config):
    """Parse the parameters from a build-magic config file.

    :param dict config: The content of the config file to parse.
    :rtype: list[dict]
    :return: A list of stage parameters.
    """
    # Read the config schema.
    schema = Path(__file__).parent / 'static' / 'config_schema.json'
    with open(schema, 'r') as file:
        schema = json.load(file)

    # Validate the config file.
    try:
        jsvalidator(config, schema=schema)
    except ValidationError as err:
        raise ValueError('Config validation failed: {}'.format(err))

    # Build the stages.
    stages = []
    for data in config.get('build-magic', []):
        data = data.get('stage', {})
        stage = dict()
        stage['name'] = data.get('name', '')
        stage['description'] = data.get('description', '')
        stage['runner_type'] = data.get('runner', Runners.LOCAL.value)
        stage['environment'] = data.get('environment', '')
        stage['continue'] = data.get('continue on fail', False)
        stage['wd'] = data.get('working directory', '.')
        stage['copy'] = data.get('copy from directory', '')
        stage['artifacts'] = data.get('artifacts', [])
        stage['dotenv'] = data.get('dotenv', '')

        # Set the action.
        stage['action'] = data.get('action', Actions.DEFAULT.value)

        # Set the command, directives, and labels.
        macros = data.get('commands', [])
        commands = []
        directives = []
        labels = []
        for macro in macros:
            if 'label' in macro.keys() and len(macro.keys()) > 1:
                labels.append(macro['label'])
            else:
                labels.append('')
            directives.append(list(macro.keys())[0])
            commands.append(list(macro.values())[0])
        stage['commands'] = commands
        stage['directives'] = directives
        stage['labels'] = labels

        # Set the parameters.
        parameters = data.get('parameters', {})
        stage['parameters'] = list(parameters.items())
        stages.append(stage)

        # Set the environment variables.
        envs_raw = data.get('environment variables', {})
        envs = {}
        for key, value in envs_raw.items():
            envs.update({key: value})
        stage['environment variables'] = envs

    return stages


def parse_variables(config, variables):
    """Parses a config file for variables and substitutes the variable placeholders in the config for the given values.

    :param dict config: The content of the config file to parse.
    :param dict variables: The variables to substitute where the key matches a placeholder in the config.
    :rtype: dict
    :return: The resulting config after variable substitution.
    """
    matched = False
    config_string = json.dumps(config)
    if variables:
        if re.search(VARIABLE_PATTERN, json.dumps(config)):
            matches = re.findall(VARIABLE_PATTERN, json.dumps(config))
            if matches:
                for key, value in variables.items():
                    for match in matches:
                        if key in match:
                            # Convert value that might be Windows path.
                            if '\\' in value:
                                value = value.encode('unicode-escape').decode('utf-8')
                                value = value.replace('\\', '/')
                            pattern = re.compile(r'{{\s?' + key + r'\s?}}')
                            config_string = re.sub(pattern, value, config_string)
                            matched = True
                            break
            if not matched:
                raise ValueError('No variable matches found.')
    return json.loads(config_string)


class Engine:
    """The primary driver in build-magic. The engine executes stages and reports on the results.

    :param bool continue_on_fail: If True, all jobs will attempt to run, even if the previous job failed.
        Otherwise, execution will end after a failed job.
    :param list[Stage]|None stages: The stage or stages to execute.
    """

    __slots__ = ('_continue_on_fail', '_stages', '_verbose')

    def __init__(self, stages=None, continue_on_fail=False, output_format=OutputTypes.TTY, verbose=False):
        """Executes stages and reports the results.

        :param list[Stage]|None stages: The stage or stages to execute.
        :param bool continue_on_fail: If True, continue command execution even if a command fails or errors.
        :param OutputTypes output_format: The output interface to use for displaying messages.
        :param bool verbose: If True, print the stdout from each Macro status.
        :return: The highest status code reported by a stage.
        """
        self._continue_on_fail = continue_on_fail
        self._verbose = verbose
        self._stages = stages or []

        if not isinstance(stages, list):
            raise TypeError("Stages must be a list.")

        # Sort stages by sequence.
        if len(stages) > 1:
            self._stages = sorted(stages, key=lambda s: s.sequence)

        global _output
        _output = getattr(output, output_format.value)()

    def run(self):
        """Executes stages and reports the results.

        :return: The highest status code reported by a stage.
        """
        # Initialize the status code to 0.
        status_code = ExitCode.PASSED.value

        # Start
        _output.log(mode.JOB_START)

        for stage in self._stages:
            spinner = yaspin()
            # Run the stage.
            _output.log(mode.STAGE_START, stage.sequence, stage.name, stage.description)
            # Launch the process spinner
            _output.log(mode.PROCESS_SPINNER, spinner, process_active=True)
            stage.setup()
            try:
                exit_code = stage.run(self._continue_on_fail, self._verbose, spinner)
            except (SetupError, ExecutionError, TeardownError) as err:
                exit_code = ExitCode.INTERNAL_ERROR
                _output.log(mode.ERROR, err)
                _output.log(mode.STAGE_END, stage.sequence, exit_code)
                _output.log(mode.JOB_END)
                raise err

            if exit_code > status_code:
                if not (exit_code == ExitCode.SKIPPED and stage.sequence < len(self._stages)):
                    status_code = exit_code
            _output.log(mode.STAGE_END, stage.sequence, exit_code, stage.name)

        _output.log(mode.JOB_END)
        return status_code


class StageFactory:
    """Validates and generates Stage objects."""

    @classmethod
    def _build_macros(cls, commands, labels):
        """Build Macro objects from provided commands.

        :param list[str] commands: The commands to use for building the Macro objects.
        :param list[str] labels: The command descriptions to display.
        :rtype: list[Macro]
        :return: A list of Macro objects.
        """
        factory = MacroFactory(commands, labels=labels)
        return factory.generate()

    @classmethod
    def _build_command_runner(cls, runner_type, environment, parameters, copy, wd, artifacts, envs):
        """Build a CommandRunner object.

        :param str runner_type: The command runner to use for executing commands.
        :param str environment: The Stage environment to use.
        :param str copy: The directory to copy artifacts from, to the working directory.
        :param str wd: The working directory to use for executing commands.
        :param list[str] artifacts: The Stage artifacts to work on.
        :param dict parameters: The user-supplied parameters to pass to the command runner.
        :param dict envs: The environment variables to set.
        :rtype: CommandRunner
        :return: The CommandRunner object to use for executing the Stage's commands.
        """
        if runner_type not in Runners.available():
            raise ValueError('Runner must be one of {}.'.format(', '.join(Runners.available())))

        if runner_type == Runners.VAGRANT.value and not environment:
            raise ValueError('Environment must be a path to a Vagrant file if using the Vagrant runner.')

        if runner_type == Runners.DOCKER.value and not environment:
            raise ValueError('Environment must be a Docker image if using the Docker runner.')

        if copy and not Path(copy).exists():
            raise NotADirectoryError(f'Path {copy} does not exist.')

        command_runner = getattr(runner, runner_type.capitalize())
        return command_runner(
            environment,
            working_dir=wd,
            copy_dir=copy,
            artifacts=artifacts,
            parameters=parameters,
            envs=envs,
        )

    @classmethod
    def _build_parameters(cls, parameters):
        """Build the Parameter objects for the CommandRunner to use.

        :param list[tuple] parameters: The parameter keys and their corresponding classes.
        :rtype: dict[str, build_magic.reference.Parameter]
        :return: A dictionary of Parameter objects instantiated with the passed in values.
        """
        if not parameters:
            return {}
        parameter_map = dict([(p.ALIAS, p) if p.ALIAS else (p.KEY, p) for p in PARAMETERS])
        params = {}
        for param_key, param_value in parameters:
            if param_key not in parameter_map.keys():
                raise ValueError(f'Parameter {param_key} is not a valid parameter.')
            param = parameter_map[param_key]
            # Instantiating param can fail with a reference.ValidationError.
            params[param_key] = param(param_value)
        return params

    @classmethod
    def build(
            cls,
            sequence,
            runner_type,
            directives,
            artifacts,
            commands,
            environment,
            action,
            copy,
            wd,
            name=None,
            parameters=None,
            envs=None,
            labels=None,
            description=None,
    ):
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
        :param str|None name: The stage name if provided.
        :param list[tuple]|None parameters: The optional parameters passed by the user.
        :param dict|None envs: A dictionary of environment variables to use.
        :param dict|None labels: Command descriptions.
        :param str|None description: A description of the stage.
        :rtype: Stage
        :return: The generated Stage object.
        """
        if not commands:
            _output.log(mode.NO_JOB)
            raise NoJobs

        for directive in directives:
            directive = directive.lower()
            if directive not in Directive.available():
                raise ValueError(
                    'Directive must be one of {}'.format(', '.join(Directive.available()))
                )

        if labels is None:
            labels = [''] * len(commands)

        if len(commands) != (len(directives)):
            raise ValueError('Length of commands unequal to length of directives.')

        if len(labels) != len(commands):
            raise ValueError('Length of commands unequal to length of labels.')

        if action not in Actions.available():
            raise ValueError('Action must be one of {}.'.format(', '.join(Actions.available())))

        # Build the parameters.
        params = cls._build_parameters(parameters)

        if not artifacts:
            artifacts = []

        if not envs:
            envs = {}

        # Build the macros.
        macros = cls._build_macros(commands=commands, labels=labels)
        if not macros:
            raise ValueError('There are no commands to execute.')

        # Create the CommandRunner.
        cmd_runner = cls._build_command_runner(
            runner_type,
            environment,
            copy=copy,
            wd=wd,
            artifacts=artifacts,
            parameters=params,
            envs=envs,
        )

        return Stage(cmd_runner, macros, directives, sequence, action, name, description)


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
        '_name',
        '_description',
    ]

    def __init__(self, cmd_runner, macros, directives, sequence, action, name='', description=''):
        """Instantiates a new Stage object.

        Note: Stage objects should not be constructed directly and should instead be created by a StageFactory.

        :param CommandRunner cmd_runner: The CommandRunner to use.
        :param list[Macro] macros: The commands to execute.
        :param list[str] directives: The command directives.
        :param int|str sequence: The execution order of the macros.
        :param str action: The Action to use.
        :param str name: The stage name if provided.
        :param str description: The description of the stage if provided.
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
        self._name = name
        self._description = description

    @property
    def sequence(self):
        """The stage execution order."""
        return self._sequence

    @property
    def is_setup(self):
        """True if the setup method was already run, else False."""
        return self._is_setup

    @property
    def name(self):
        """The stage name."""
        return self._name or ''

    @property
    def description(self):
        """The stage description."""
        return self._description or ''

    def _get_action_function(self, method):
        """Fetches the mapped action function for the provided command runner method.

        :param str method: The command runner method, i.e. provision or teardown.
        :rtype: Callable
        :return: The mapped function.
        """
        method_name = self._action.mapping[method].get(self._command_runner.name, actions.DEFAULT_METHOD)
        method = getattr(actions, method_name)
        return types.MethodType(method, self._command_runner)

    def setup(self):
        """Dynamically set the provision() and teardown() methods for the Command Runner and call it's prepare() method.

        :return: None
        """
        # Dynamically bind the action's provision function to the command runner object.
        self._command_runner.provision = self._get_action_function(actions.SETUP_METHOD)

        # Dynamically bind the action's teardown function to the command runner object.
        self._command_runner.teardown = self._get_action_function(actions.TEARDOWN_METHOD)

        self._is_setup = True

    def run(self, continue_on_fail=False, verbose=False, spinner=None):
        """Executes the commands in the Stage.

        :param bool continue_on_fail: If True, keep running commands even if the last command failed. Default is False.
        :param bool verbose: If True, print the stdout from each Macro status.
        :param yaspin spinner: The yaspin spinner object to use.
        :return: The highest Stage result.
        """
        def stop_spinner():
            if spinner is not None:
                _output.log(mode.PROCESS_SPINNER, spinner, process_active=False)

        # Setup if not already setup.
        if not self.is_setup:
            self.setup()

        # Call the provision method.
        try:
            result = self._command_runner.provision()
        except KeyboardInterrupt:
            stop_spinner()
            raise KeyboardInterrupt
        except Exception as err:
            stop_spinner()
            raise SetupError(exception=err)
        if not result:
            stop_spinner()
            raise SetupError

        # Call the command runner's prepare function.
        try:
            self._command_runner.prepare()
        except OSEnvironmentMismatch:
            stop_spinner()
            msg = (
                f'Skipping Stage {self.sequence}{": " + self.name if self.name else ""} '
                f'because OS is not {self._command_runner.environment.lower()}.'
            )
            _output.log(mode.SKIP, msg)
            return ExitCode.SKIPPED

        for mac in self._macros:
            directive = self._directives[mac.sequence - 1]

            # Add the prefix to the macro.
            if self._action.add_prefix.get(self._command_runner.name):
                mac.prefix = self._action.add_prefix[self._command_runner.name]

            # Add the suffix to the macro.
            if self._action.add_suffix.get(self._command_runner.name):
                mac.suffix = self._action.add_suffix[self._command_runner.name]

            # Run the macro.
            try:
                stop_spinner()
                _output.log(
                    mode.MACRO_START,
                    directive=directive,
                    command=mac.label if mac.label else mac.command,
                    sequence=mac.sequence,
                    total=len(self._macros),
                )
                status = self._command_runner.execute(mac)
            except Exception as err:
                stop_spinner()
                raise ExecutionError(exception=err)

            # Handle the result.
            _output.log(
                mode.MACRO_STATUS,
                directive=directive,
                command=mac.label if mac.label else mac.command,
                status_code=status.exit_code,
                sequence=mac.sequence,
                total=len(self._macros),
            )
            self._results.append(status)

            if verbose:
                if status.stdout:
                    _output.print_output(status.stdout)
            if status.exit_code > 0 and not continue_on_fail:
                _output.print_output(status.stderr, is_error=True)
                break

        # Call the teardown method.
        result = self._command_runner.teardown()
        if not result:
            raise TeardownError

        # Set the exit code.
        fails = map(lambda r: True if r.exit_code > 0 else False, self._results)
        if any(fails):
            self._result = ExitCode.FAILED

        return self._result
