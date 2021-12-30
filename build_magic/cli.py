"""Click CLI for running build-magic."""
import os
from io import TextIOWrapper
import json
import logging
import pathlib
import re
import shlex

import click
import yaml

# Need this to disable logging in the vagrant package when Vagrant isn't installed.
logging.disable(logging.WARNING)

from build_magic import __version__ as ver
from build_magic import core
from build_magic.exc import ExecutionError, HostWorkingDirectoryNotFound, NoJobs, SetupError, TeardownError
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
    build-magic -r docker -e ubuntu:latest -c execute "configure" -c build "make all"

* Execute multiple commands in a config file.
    build-magic -C myconfig.yaml

* Execute a particular stage in a config file.
    build-magic -C myconfig.yaml -t build

* Execute a particular stage in a config file in the current directory named build-magic.yaml.
    build-magic build

* Execute all stages in a config file in the current directory named build-magic.yaml.
    build-magic all

Use --help for detailed usage of each option.

Visit https://cmmorrow.github.io/build-magic/user_guide/cli_usage/ for a detailed usage description.
"""


ACTION_HELP = 'The setup and teardown action to perform.'
COMMAND_HELP = 'A directive, command pair to execute.'
CONFIG_HELP = 'The config file to load parameters from.'
CONTINUE_HELP = 'Continue to run after failure if True.'
COPY_HELP = 'Copy files from the specified path.'
DESCRIPTION_HELP = 'The stage description to use.'
DOTENV_HELP = 'Provide a dotenv file to set additional environment variables.'
ENV_HELP = 'Provide an environment variable to set for stage execution.'
ENVIRONMENT_HELP = 'The command runner environment to use.'
FANCY_HELP = 'Enables output with colors. Ideal for an interactive terminal session.'
INFO_HELP = 'Display config file metadata, variables, and stage names.'
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


def error(ctx, msg, code):
    """High-level function for printing an error message and providing an error code.

    :param click.Context ctx: The click Context to use.
    :param str msg: The error message to print.
    :param int code: The exit code to return.
    """
    click.secho(str(msg), fg='red', err=True)
    ctx.exit(code)


def get_template(ctx, _, value):
    """Callback that generates a build-magic config file template and exits.

    :param click.Context ctx: The context of the click command.
    :param click.Parameter _: The template parameter object.
    :param bool value: True if the --template flag is set.
    :return: None
    """
    if not value:
        return
    try:
        core.generate_config_template()
        ctx.exit()
    except FileExistsError:
        error(
            ctx=ctx,
            msg='Cannot generate the config template because it already exists!',
            code=reference.ExitCode.INPUT_ERROR,
        )
    except PermissionError:
        error(
            ctx=ctx,
            msg="Cannot generate the config template because build-magic doesn't have permission.",
            code=reference.ExitCode.INPUT_ERROR,
        )


def set_silent(_, param, value):
    """Callback that sets the quiet output type.

    :param click.Context _: The context of the click command.
    :param click.Parameter param: The quiet parameter object.
    :param bool value: True if the --quiet flag is set.
    :rtype: str
    :return: The build-magic Silent output type.
    """
    if value or param.default is True:
        return reference.OutputTypes.SILENT


def set_basic(_, param, value):
    """Callback that sets the plain output type.

    :param click.Context _: The context of the click command.
    :param click.Parameter param: The plain parameter object.
    :param bool value: True if the --plain flag is set.
    :rtype: str
    :return: The build-magic Basic output type.
    """
    if value or param.default is True:
        return reference.OutputTypes.BASIC


def set_tty(_, param, value):
    """Callback that sets the fancy output type.

    :param click.Context _: The context of the click command.
    :param click.Parameter param: The fancy parameter object.
    :param bool value: True if the --fancy flag is set.
    :rtype: str
    :return: The build-magic TTY output type.
    """
    if value or param.default is True:
        return reference.OutputTypes.TTY


@click.command()
@click.option('--command', '-c', help=COMMAND_HELP, multiple=True, type=(str, str))
@click.option('--config', '-C', help=CONFIG_HELP, multiple=True, type=CONFIG)
@click.option('--copy', help=COPY_HELP, default='', type=str)
@click.option('--environment', '-e', help=ENVIRONMENT_HELP, default='', type=str)
@click.option('--runner', '-r', help=RUNNER_HELP, type=RUNNERS)
@click.option('--wd', help=WD_HELP, default='.', type=WORKINGDIR)
@click.option('--continue/--stop', 'continue_', help=CONTINUE_HELP, default=False)
@click.option('--name', help=NAME_HELP, type=str, default='')
@click.option('--description', help=DESCRIPTION_HELP, type=str, default='')
@click.option('--target', '-t', help=TARGET_HELP, multiple=True, type=str)
@click.option('--info', help=INFO_HELP, is_flag=True)
@click.option('--env', help=ENV_HELP, multiple=True, type=(str, str))
@click.option('--dotenv', help=DOTENV_HELP, type=CONFIG, default=None)
@click.option('--template', help=TEMPLATE_HELP, is_flag=True, is_eager=True, expose_value=False, callback=get_template)
@click.option('--parameter', '-p', help=PARAMETER_HELP, multiple=True, type=(str, str))
@click.option('--variable', '-v', help=VARIABLE_HELP, multiple=True, type=(str, str))
@click.option('--prompt', help=PROMPT_HELP, multiple=True, type=str)
@click.option('--action', help=ACTION_HELP, type=ACTIONS)
@click.option('--plain', help=PLAIN_HELP, is_flag=True, default=False, callback=set_basic)
@click.option('--fancy', help=FANCY_HELP, is_flag=True, default=True, callback=set_tty)
@click.option('--quiet', help=QUIET_HELP, is_flag=True, default=False, callback=set_silent)
@click.option('--verbose', help=VERBOSE_HELP, is_flag=True)
@click.version_option(version=ver, message='%(version)s')
@click.argument('args', nargs=-1)
def build_magic(
        command,
        config,
        info,
        env,
        dotenv,
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
        description,
        wd,
        plain,
        quiet,
        fancy,
        verbose,
):
    """An un-opinionated build automation tool.

    ARGS - One of four possible uses based on context:

    1. If the --copy option is used, each argument in ARGS is a file name in the copy from directory to copy to
    the working directory.

    2. If there is a config file named build-magic.yaml in the working directory, ARGS is the name of a stage to
    execute.

    3. ARGS are considered a single command to execute if the --command option isn't used.

    4. ARGS are config file names if using the --info option.

    Visit https://cmmorrow.github.io/build-magic/user_guide/cli_usage/ for a detailed usage description.
    """

    ctx = click.get_current_context()

    if info:
        execute_info_subcommand(ctx=ctx, config_files=args)

    # Get the output type.
    out = quiet or plain or fancy

    stages_ = []
    all_stage_names = []
    seq = core.iterate_sequence()

    config = configs_with_default_config(ctx=ctx, configs=config, command=command)

    # Set the commands from the command line.
    if command:
        directives, commands = list(zip(*command))
        artifacts = args

        stages_.append(
            dict(
                sequence=next(seq),
                runner_type=reference.Runners.LOCAL.value,
                directives=directives,
                name=name,
                description=description,
                artifacts=artifacts,
                action=reference.Actions.DEFAULT.value,
                commands=commands,
                environment=environment,
                copy=copy,
                wd=wd,
                parameters=parameter,
                envs={**parse_dotenv_file(dotenv), **dict(env)},
            )
        )
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

            if target:
                # Only execute stages that match a target name.
                for trgt in target:
                    if trgt in stage_names:
                        stage_ = stages[stage_names.index(trgt)]
                        stages_.append(get_config_params(stage_, cfg.name, next(seq)))
            elif args and cfg.name in DEFAULT_CONFIG_NAMES:
                for trgt in [shlex.split(t)[0] for t in args]:

                    if trgt == 'all':
                        # Execute all stages in the default config file.
                        for stage_ in stages:
                            stages_.append(get_config_params(stage_, cfg.name, next(seq)))

                    elif trgt in stage_names:
                        # Execute only the stage in the default config file that matches the given arg.
                        stage_ = stages[stage_names.index(trgt)]
                        stages_.append(get_config_params(stage_, cfg.name, next(seq)))

                    else:
                        # Otherwise, assume the args are a command.
                        directives, commands = ['execute'], [' '.join(args)]
                        stages_.append(
                            dict(
                                sequence=next(seq),
                                runner_type=reference.Runners.LOCAL.value,
                                directives=directives,
                                name=name,
                                description=description,
                                artifacts=[],
                                action=reference.Actions.DEFAULT.value,
                                commands=commands,
                                environment=environment,
                                copy=copy,
                                wd=wd,
                                parameters=parameter,
                                envs={**parse_dotenv_file(dotenv), **dict(env)},
                            )
                        )
                        break

            elif not args and cfg.name in DEFAULT_CONFIG_NAMES:
                # If a default config file exists but there are no args, skip it.
                continue

            else:
                # The typical case where each stage is executed in the specified config file.
                for stage_ in stages:
                    stages_.append(get_config_params(stage_, cfg.name, next(seq)))

    # Assume the args are an ad-hoc command to execute.
    elif args and not command:
        directives, commands = ['execute'], [' '.join(args)]
        stages_.append(
            dict(
                sequence=1,
                runner_type=reference.Runners.LOCAL.value,
                directives=directives,
                name=name,
                description=description,
                artifacts=[],
                action=reference.Actions.DEFAULT.value,
                commands=commands,
                environment=environment,
                copy=copy,
                wd=wd,
                parameters=parameter,
                envs={**parse_dotenv_file(dotenv), **dict(env)},
            )
        )
    # If all else fails, display the usage text.
    if not stages_:
        if target:
            error(
                ctx=ctx,
                msg=f'Target {target[0]} not found among {all_stage_names}.',
                code=reference.ExitCode.INPUT_ERROR,
            )

        click.echo(USAGE)
        ctx.exit(reference.ExitCode.NO_TESTS)

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

    ctx.exit(code)


def read_config_file(cfg):
    """Loads a config yaml file.

    :param TextIOWrapper cfg: The config file to read.
    :rtype: dict
    :return: A dictionary representing the the loaded config.
    """
    try:
        obj = yaml.safe_load(cfg)
        if isinstance(cfg, TextIOWrapper):
            cfg.close()
        return obj
    except yaml.YAMLError as err:
        error(
            ctx=click.get_current_context(),
            msg=str(err),
            code=reference.ExitCode.INPUT_ERROR,
        )


def get_config_info(cfg, show_filename=False):
    """Writes relevant info in a config file to stdout.

    :param TextIO cfg: The config file to read and display info of.
    :param bool show_filename: If True, display the filename of the config file.
    :return: None
    """
    def add_output(label_, val):
        spacing.append(len(label_))
        output.append((label_, val))

    obj = read_config_file(cfg)
    filename = f'{cfg.name}  ' if show_filename else ''

    version = obj.get('version')
    author = obj.get('author')
    maintainer = obj.get('maintainer')
    created = obj.get('created')
    modified = obj.get('modified')
    description = obj.get('description')

    variables = []
    if re.search(reference.VARIABLE_PATTERN, json.dumps(obj)):
        variables = re.findall(reference.VARIABLE_PATTERN, json.dumps(obj))
        variables = set(variables)
        variables = sorted([var.strip('{{').strip('}}').strip() for var in variables])

    stages = [stg.get('stage') for stg in obj['build-magic']]
    stage_names = [stage.get('name') for stage in stages if stage.get('name')]

    spacing = []
    output = []

    if version:
        add_output('version', version)
    if author:
        add_output('author', author)
    if maintainer:
        add_output('maintainer', maintainer)
    if created:
        add_output('created', created)
    if modified:
        add_output('modified', modified)
    if description:
        add_output('description', description)

    for variable in variables:
        add_output('variable', variable)

    for name in stage_names:
        add_output('stage', name)

    space = max(spacing) + 1 if spacing else 1
    for label, value in output:
        click.echo(f'{filename}{label + ":":<{space}}  {value}')


def execute_info_subcommand(ctx, config_files):
    """Opens config files and fetches the info for each.

    :param click.Context ctx: The context of the click command.
    :param tuple[str] config_files: The config files to get the info of.
    """
    if not config_files:
        error(
            ctx=ctx,
            msg='No config files specified.',
            code=reference.ExitCode.INPUT_ERROR,
        )
    show_filenames = True if len(config_files) > 1 else False
    try:
        for cfg in [open(arg, 'r') for arg in config_files]:
            get_config_info(cfg, show_filename=show_filenames)
    except FileNotFoundError as e:
        error(
            ctx=ctx,
            msg=str(e),
            code=reference.ExitCode.INPUT_ERROR,
        )
    ctx.exit()


def configs_with_default_config(ctx, configs, command=None):
    """Check to see if there is a default config and add it to the list of configs.

    :param click.Context ctx: The context of the click command.
    :param tuple[TextIOWrapper] configs: The config filenames to use.
    :param tuple[str]|None command: The commands to use if set.
    :rtype: list[TextIOWrapper]
    :return: A list of the configs that include the default config file if one exists.
    """
    new_configs = list(configs)

    # Check to see if a default-named config file exists in the current directory.
    default_configs = DEFAULT_CONFIG_NAMES & set([path.name for path in pathlib.Path.cwd().iterdir()])
    if len(default_configs) > 1:
        error(
            ctx=ctx,
            msg=f'More than one config file found: {default_configs}',
            code=reference.ExitCode.INPUT_ERROR,
        )

    # Add the default config to the list of configs.
    if len(default_configs) == 1:
        default_config_file_name = tuple(default_configs)[0]
        config_file = pathlib.Path(default_config_file_name).open()
        if config_file.name not in [conf.name for conf in configs]:
            new_configs.insert(0, config_file)
        else:
            config_file.close()
        if command and not config_file.closed:
            config_file.close()

    return new_configs


def execute_stages(engine):
    """Helper function for executing each stage in order.

    :param engine: The build-magic Engine object to execute.
    :rtype: int
    :return: The highest exit code from the executed stages.
    """
    ctx = click.get_current_context()
    try:
        return engine.run()
    except NoJobs:
        ctx.exit(reference.ExitCode.NO_TESTS)
    except (ExecutionError, SetupError, TeardownError):
        ctx.exit(reference.ExitCode.INTERNAL_ERROR)
    except KeyboardInterrupt:
        error(
            ctx=ctx,
            msg='\nbuild-magic interrupted and exiting....',
            code=reference.ExitCode.INTERRUPTED,
        )


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
        except (NotADirectoryError, ValueError, reference.ValidationError, HostWorkingDirectoryNotFound) as err:
            error(
                ctx=click.get_current_context(),
                msg=str(err),
                code=reference.ExitCode.INPUT_ERROR,
            )
    return stages


def get_config_params(stage, path, seq=1):
    """Maps config keys to stage arguments as a dictionary.

    :param dict stage: The stage to map.
    :param str path: The config file path.
    :param int seq: The stage sequence.
    :rtype: dict
    :return: The mapped keyword arguments.
    """
    dotenv = stage.get('dotenv')
    if dotenv:
        # Make the path to the dotenv file relative to the config file.
        rel_path = os.path.dirname(path)
        dotenv_path = os.path.join(rel_path, dotenv)
        envs = parse_dotenv_file(open(dotenv_path, 'r'))
    else:
        envs = {}
    envs = {**envs, **stage.get('environment variables')}

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
        description=stage.get('description'),
        parameters=stage.get('parameters'),
        labels=stage.get('labels'),
        envs=envs,
    )


def get_stages_from_config(cfg, variables):
    """Read a config YAML file and extract the stages.

    :param bytes|IO[bytes]|Text|IO[Text] cfg: The config file object.
    :param dict variables: Variables to substitute into the config file.
    :rtype: list[dict]
    :return: The extracted stages.
    """
    # Read the config YAML file.
    obj = read_config_file(cfg)

    # Parse the YAML file and set the options.
    try:
        obj = core.parse_variables(obj, variables)
        return core.config_parser(obj)
    except ValueError as err:
        error(
            ctx=click.get_current_context(),
            msg=str(err),
            code=reference.ExitCode.INPUT_ERROR,
        )


def parse_dotenv_file(dotenv):
    """Read a dotenv file and parse each line of environment variables into a dictionary.

    Line starting with "#" are ignored by the parser.

    Only the first "=" in a line is used to split a variable from it's value.

    Uncommented lines without a "=" are ignored.

    :param io.TextIOWrapper|io.TextIO dotenv: The dotenv file to read and parse.
    :rtype: dict
    :return: A dictionary of the parsed variables.
    """
    ctx = click.get_current_context()

    if not dotenv:
        return {}

    if '.env' not in dotenv.name:
        resume = click.confirm('The provided dotenv file does not have a .env extension. Continue anyway?')
        if not resume:
            dotenv.close()
            ctx.exit(reference.ExitCode.INPUT_ERROR)

    envs = {}
    for line in dotenv.readlines():
        if line.startswith('#'):
            continue
        if '=' not in line:
            continue
        env, val = line.split('=', maxsplit=1)
        envs.update({env.strip(): val.strip()})

    dotenv.close()
    return envs
