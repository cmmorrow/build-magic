"""Click CLI for running build-magic."""

import click
import sys

from build_magic import core

# Get a list of command runners.
RUNNERS = click.Choice(core.Runners.available(), case_sensitive=False)


# Defines the type for the working directory parameter.
WORKINGDIR = click.Path(exists=False, file_okay=False, dir_okay=True, resolve_path=True, allow_dash=False)


# Defines the type for the config file.
CONFIG = click.File(mode='r', encoding='utf-8', errors='strict', lazy=False)


# Get a list of available actions.
Actions = core.Actions


@click.command()
@click.option('--command', '-c', help='A directive, command pair to execute.', multiple=True, type=(str, str))
# @click.option('--config', '-C', help='The JSON formatted config file to load parameters from.', type=CONFIG)
@click.option('--copy', '-p', help='Copy from the specified path.', default='', type=str)
@click.option('--environment', '-e', default='', help='The command runner environment to use.', type=str)
@click.option('--runner', '-r', default='local', help='The command runner to use.', type=RUNNERS)
@click.option('--working-dir', '-w', help='The working directory to run commands from.', default='.', type=WORKINGDIR)
@click.option('--continue-on-fail/--stop-on-fail', help='Continue to run after failure if True.', default=False)
@click.option('--isolate', '-i', help='Execute commands in an isolated directory.', default=False)
@click.option('--cleanup', help='Run commands and delete any created files if True.', default=False)
@click.argument('args', nargs=-1)
def build_magic(cleanup, command, copy, continue_on_fail, environment, args, isolate, runner, working_dir):
    """The build automation tool.

    ARGS - Files as arguments to copy from the copy path to the working directory.
           Alternatively, ARGS can be a command to execute if the --command option isn't used.
           Instead, type -- followed by the command.
    """
    # Set the action to use.
    action = Actions.DEFAULT.value
    if cleanup:
        action = Actions.CLEANUP.value

    # Set the commands to use.
    if command:
        types, commands = list(zip(*command))
        artifacts = args
    else:
        types, commands = ['build'], [' '.join(args)]
        artifacts = []

    # Build the stage.
    stage = core.StageFactory.build(
        sequence=1,
        runner_type=runner,
        directives=list(types),
        artifacts=artifacts,
        action=action,
        commands=list(commands),
        environment=environment,
        copy=copy,
        wd=working_dir,
    )

    # Run the stage.
    code = core.Engine.run([stage], continue_on_fail=continue_on_fail)

    sys.exit(code)
