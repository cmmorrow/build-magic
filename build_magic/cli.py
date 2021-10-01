"""Click CLI for running build-magic."""

from io import TextIOWrapper
import logging
import pathlib
import shlex
import sys

import click
import yaml

# Need this to disable logging in the vagrant package when Vagrant isn't installed.
logging.disable(logging.WARNING)

from build_magic import __version__ as ver
from build_magic import core
from build_magic.exc import ExecutionError, NoJobs, SetupError, TeardownError
from build_magic import reference

# Get a list of command runners.
RUNNERS = click.Choice(reference.Runners.available(), case_sensitive=False)


# Get a list of available actions.
ACTIONS = click.Choice(reference.Actions.available(), case_sensitive=False)


# Defines the type for the working directory parameter.
WORKINGDIR = click.Path(exists=False, file_okay=False, dir_okay=True, resolve_path=False, allow_dash=False)


# Defines the type for the config file.
CONFIG = click.File(mode='r', encoding='utf-8', errors='strict', lazy=False)


DEFAULT_CONFIG_NAMES = {
    'build-magic.yaml',
    'build_magic.yaml',
    'build-magic.yml',
    'build_magic.yml',
}


USAGE = """Usage: build-magic [OPTIONS] [ARGS]...

build-magic is an un-opinionated build automation tool. Some potential uses include:
    * Building applications across multiple platforms.
    * Conducting installation dry runs.
    * Automating repeated tasks.
    * Deploying and installing artifacts to remote machines.

Examples:
* Archive two files on the local machine.
    build-magic tar -czf myfiles.tar.gz file1.txt file2.txt

* Archive two files on the local machine and delete the original files.
    build-magic -c build "tar -czf myfiles.tar.gz file1.txt file2.txt" -c execute "rm file1.txt file2.txt"
    
* Copy two files to a remote machine and archive them.
    build-magic -r remote -e user@myhost --copy . -c build "tar -czf myfiles.tar.gz f1.txt f2.txt" f1.txt f2.txt

* Build a project in a Linux container.
    build-magic -r docker -e Ubuntu:latest -c execute "configure" -c build "make all"
    
* Execute multiple commands in a config file.
    build-magic -C myconfig.yaml
    
* Execute a particular stage in a config file.
    build-magic -C myconfig.yaml -t build

Use --help for detailed usage of each option.

Visit https://cmmorrow.github.io/build-magic/user_guide/cli_usage/ for a detailed usage description.
"""


ACTION_HELP = 'The setup and teardown action to perform.'
COMMAND_HELP = 'A directive, command pair to execute.'
CONFIG_HELP = 'The config file to load parameters from.'
CONTINUE_HELP = 'Continue to run after failure if True.'
COPY_HELP = 'Copy files from the specified path.'
ENVIRONMENT_HELP = 'The command runner environment to use.'
NAME_HELP = 'The stage name to use.'
PARAMETER_HELP = 'Space separated key/value used for runner specific settings.'
PLAIN_HELP = 'Enables basic output. Ideal for logging and automation.'
PROMPT_HELP = 'Config file variable with prompt for value.'
QUIET_HELP = 'Suppresses all output from build-magic.'
RUNNER_HELP = 'The command runner to use.'
TARGET_HELP = 'Run a particular stage in a config file by name.'
TEMPLATE_HELP = 'Generates a config file template in the current directory.'
VARIABLE_HELP = 'Space separated key/value config file variables.'
VERBOSE_HELP = 'Verbose output -- stdout from executed commands will be printed when complete.'
WD_HELP = 'The working directory to run commands from.'


@click.command()
@click.option('--command', '-c', help=COMMAND_HELP, multiple=True, type=(str, str))
@click.option('--config', '-C', help=CONFIG_HELP, multiple=True, type=CONFIG)
@click.option('--copy', help=COPY_HELP, default='', type=str)
@click.option('--environment', '-e', help=ENVIRONMENT_HELP, default='', type=str)
@click.option('--runner', '-r', help=RUNNER_HELP, type=RUNNERS)
@click.option('--name', help=NAME_HELP, type=str)
@click.option('--target', '-t', help=TARGET_HELP, multiple=True, type=str)
@click.option('--template', help=TEMPLATE_HELP, is_flag=True)
@click.option('--wd', help=WD_HELP, default='.', type=WORKINGDIR)
@click.option('--continue/--stop', 'continue_', help=CONTINUE_HELP, default=False)
@click.option('--parameter', '-p', help=PARAMETER_HELP, multiple=True, type=(str, str))
@click.option('--variable', '-v', help=VARIABLE_HELP, multiple=True, type=(str, str))
@click.option('--prompt', help=PROMPT_HELP, multiple=True, type=str)
@click.option('--action', help=ACTION_HELP, type=ACTIONS)
@click.option('--plain/--fancy', help=PLAIN_HELP, default=False)
@click.option('--quiet', help=QUIET_HELP, is_flag=True)
@click.option('--verbose', help=VERBOSE_HELP, is_flag=True)
@click.version_option(version=ver, message='%(version)s')
@click.argument('args', nargs=-1)
def build_magic(
        command,
        config,
        copy,
        continue_,
        environment,
        args,
        parameter,
        variable,
        prompt,
        action,
        runner,
        name,
        target,
        template,
        wd,
        plain,
        quiet,
        verbose,
):
    """An un-opinionated build automation tool.

    ARGS - One of three possible uses based on context:

    1. If the --copy option is used, each argument in ARGS is a file name in the copy from directory to copy to
    the working directory.

    2. If there is a config file named build-magic.yaml in the working directory, ARGS is the name of a stage to
    execute.

    3. ARGS are considered a single command to execute if the --command option isn't used.

    Visit https://cmmorrow.github.io/build-magic/user_guide/cli_usage/ for a detailed usage description.
    """

    if template:
        try:
            core.generate_config_template()
            sys.exit(0)
        except FileExistsError:
            click.secho('Cannot generate the config template because it already exists!', fg='red', err=True)
            sys.exit(reference.ExitCode.INPUT_ERROR)
        except PermissionError:
            click.secho(
                "Cannot generate the config template because build-magic doesn't have permission.",
                fg='red',
                err=True,
            )
            sys.exit(reference.ExitCode.INPUT_ERROR)

    # Get the output type.
    if plain:
        out = reference.OutputTypes.BASIC
    elif quiet:
        out = reference.OutputTypes.SILENT
    else:
        out = reference.OutputTypes.TTY

    stages_ = []
    all_stage_names = []
    config = list(config)
    seq = core.iterate_sequence()

    # Check to see if a default-named config file exists in the current directory.
    default_configs = DEFAULT_CONFIG_NAMES & set([path.name for path in pathlib.Path.cwd().iterdir()])
    if len(default_configs) > 1:
        click.secho(f'More than one config file found: {default_configs}', fg='red', err=True)
        sys.exit(reference.ExitCode.INPUT_ERROR)

    # Add the default config to the list of configs.
    if len(default_configs) == 1:
        default_config_file_name = tuple(default_configs)[0]
        config_file = pathlib.Path(default_config_file_name).open()
        if config_file.name not in [conf.name for conf in config]:
            config.insert(0, config_file)
        else:
            config_file.close()

    # Set the commands from the command line.
    if command:
        directives, commands = list(zip(*command))
        artifacts = args

        stages_.append(
            dict(
                sequence=next(seq),
                runner_type=reference.Runners.LOCAL.value,
                directives=directives,
                artifacts=artifacts,
                action=reference.Actions.DEFAULT.value,
                commands=commands,
                environment=environment,
                copy=copy,
                wd=wd,
                parameters=parameter,
            )
        )
        if name:
            stages_[0].update(dict(name=name))
        if len(default_configs) == 1:
            if not config_file.closed:
                config_file.close()

    elif config:
        if prompt:
            variable = list(variable)
            for var in prompt:
                value = click.prompt(f'{var}', hide_input=True)
                variable.append((var, reference.PromptSequence.START + value + reference.PromptSequence.END))
        for cfg in config:
            stages = get_stages_from_config(cfg, dict(variable))
            stage_names = [stg.get('name') for stg in stages if stg.get('name')]
            all_stage_names.extend(stage_names)
            # Only execute stages that match a target name.
            if target:
                for trgt in target:
                    if trgt in stage_names:
                        stage_ = stages[stage_names.index(trgt)]
                        stages_.append(get_config_params(stage_, next(seq)))
            elif args and cfg.name in DEFAULT_CONFIG_NAMES:
                for trgt in [shlex.split(t)[0] for t in args]:
                    # Execute all stages in the default config file.
                    if trgt == 'all':
                        for stage_ in stages:
                            stages_.append(get_config_params(stage_, next(seq)))
                    # Execute only the stage in the default config file that matches the given arg.
                    elif trgt in stage_names:
                        stage_ = stages[stage_names.index(trgt)]
                        stages_.append(get_config_params(stage_, next(seq)))
                    # Otherwise, assume the args are a command.
                    else:
                        directives, commands = ['execute'], [' '.join(args)]
                        stages_.append(
                            dict(
                                sequence=next(seq),
                                runner_type=reference.Runners.LOCAL.value,
                                directives=directives,
                                artifacts=[],
                                action=reference.Actions.DEFAULT.value,
                                commands=commands,
                                environment=environment,
                                copy=copy,
                                wd=wd,
                                parameters=parameter,
                            )
                        )
                        if name:
                            stages_[0].update(dict(name=name))
                        break
            # If a default config file exists but there are no args, skip it.
            elif not args and cfg.name in DEFAULT_CONFIG_NAMES:
                continue
            # The typical case where each stage is executed in the specified config file.
            else:
                for stage_ in stages:
                    stages_.append(get_config_params(stage_, next(seq)))
    # Assume the args are an ad-hoc command to execute.
    elif args and not command:
        directives, commands = ['execute'], [' '.join(args)]
        stages_.append(
            dict(
                sequence=1,
                runner_type=reference.Runners.LOCAL.value,
                directives=directives,
                artifacts=[],
                action=reference.Actions.DEFAULT.value,
                commands=commands,
                environment=environment,
                copy=copy,
                wd=wd,
                parameters=parameter,
            )
        )
        if name:
            stages_[0].update(dict(name=name))
    # If all else fails, display the usage text.
    if not stages_:
        if target:
            click.secho(f'Target {target[0]} not found among {all_stage_names}.', fg='red', err=True)
            sys.exit(reference.ExitCode.INPUT_ERROR)
        click.echo(USAGE)
        sys.exit(reference.ExitCode.NO_TESTS)

    # Override values in the config file with options set at the command line.
    for stage in stages_:
        if action:
            stage.update(dict(action=action))
        if environment:
            stage.update(dict(environment=environment))
        if copy:
            stage.update(dict(copy=copy))
        if len(wd) > 1:
            stage.update(dict(wd=wd))
        if runner:
            stage.update(dict(runner_type=runner))

    stages = build_stages(stages_)
    engine = core.Engine(stages, continue_on_fail=continue_, output_format=out, verbose=verbose)
    code = execute_stages(engine)

    sys.exit(code)


def execute_stages(engine):
    """Helper function for executing each stage in order.

    :param engine: The build-magic Engine object to execute.
    :rtype: int
    :return: The highest exit code from the executed stages.
    """
    try:
        code = engine.run()
    except NoJobs:
        sys.exit(reference.ExitCode.NO_TESTS)
    except (ExecutionError, SetupError, TeardownError):
        sys.exit(reference.ExitCode.INTERNAL_ERROR)
    except KeyboardInterrupt:
        click.secho('\nbuild-magic interrupted and exiting....', fg='red', err=True)
        sys.exit(reference.ExitCode.INTERRUPTED)
    return code


def build_stages(args):
    """Helper function for building each Stage object.

    :param list[dict] args: A list of keyword arguments to pass to the Stage factory.
    :rtype: list[Stage]
    :return: A list of corresponding Stage objects.
    """
    stages = []
    for stage in args:
        try:
            stages.append(core.build_stage(**stage))
        except (NotADirectoryError, ValueError, reference.ValidationError) as err:
            click.secho(str(err), fg='red', err=True)
            sys.exit(reference.ExitCode.INPUT_ERROR)
    return stages


def get_config_params(stage, seq=1):
    """Maps config keys to stage arguments as a dictionary.

    :param dict stage: The stage to map.
    :param int seq: The stage sequence.
    :rtype: dict
    :return: The mapped keyword arguments.
    """
    return dict(
        sequence=seq,
        runner_type=stage.get('runner_type'),
        directives=stage.get('directives'),
        artifacts=stage.get('artifacts'),
        action=stage.get('action'),
        commands=stage.get('commands'),
        environment=stage.get('environment'),
        copy=stage.get('copy'),
        wd=stage.get('wd'),
        name=stage.get('name'),
        parameters=stage.get('parameters'),
    )


def get_stages_from_config(cfg, variables):
    """Read a config YAML file and extract the stages.

    :param bytes|IO[bytes]|Text|IO[Text]: The config file object.
    :param dict variables: Variables to substitute into the config file.
    :rtype: list[dict]
    :return: The extracted stages.
    """
    # Read the config YAML file.
    obj = yaml.safe_load(cfg)
    if isinstance(cfg, TextIOWrapper):
        cfg.close()

    # Parse the YAML file and set the options.
    try:
        obj = core.parse_variables(obj, variables)
        stages = core.config_parser(obj)
    except ValueError as err:
        click.secho(str(err), fg='red', err=True)
        sys.exit(reference.ExitCode.INPUT_ERROR)
    return stages
