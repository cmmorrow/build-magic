"""Click CLI for running build-magic."""

import sys

import click

from build_magic import core

# Get a list of command runners.
RUNNERS = click.Choice(core.Runners.available(), case_sensitive=False)


# Defines the type for the working directory parameter.
WORKINGDIR = click.Path(exists=False, file_okay=False, dir_okay=True, resolve_path=True, allow_dash=False)


# Defines the type for the config file.
CONFIG = click.File(mode='r', encoding='utf-8', errors='strict', lazy=False)


# Get a list of available actions.
Actions = core.Actions


USAGE = """Usage: build-magic [OPTIONS] [ARGS]...

build-magic is an un-opinionated build automation tool. Some potential uses include:
* Building applications across multiple platforms.
* Conducting installation dry runs.
* Testing application installs across multiple platforms.
* Deploying and installing artifacts to remote machines.

Examples:
* Archive two files on the local machine.
    build-magic -- tar -czf myfiles.tar.gz file1.txt file2.txt

* Archive two files on the local machine and delete the original files.
    build-magic -c build "tar -czf myfiles.tar.gz file1.txt file2.txt" -c execute "rm file1.txt file2.txt"
    
* Copy two files to a remote machine and archive them.
    build-magic -r remote -e user@myhost --copy . -c build "tar -czf myfiles.tar.gz f1.txt f2.txt" f1.txt f2.txt

* Build a project in a Linux container.
    build-magic -r docker -e Ubuntu:latest -c build "make all"

Use --help for detailed usage of each option.
"""


@click.command()
@click.option('--command', '-c', help='A directive, command pair to execute.', multiple=True, type=(str, str))
# @click.option('--config', '-C', help='The YAML formatted config file to load parameters from.', type=CONFIG)
@click.option('--copy', help='Copy from the specified path.', default='.', type=str)
@click.option('--environment', '-e', default='', help='The command runner environment to use.', type=str)
@click.option('--runner', '-r', default='local', help='The command runner to use.', type=RUNNERS)
@click.option('--wd', help='The working directory to run commands from.', default='.', type=WORKINGDIR)
@click.option('--continue/--stop', help='Continue to run after failure if True.', default=False)
@click.option('--isolate', help='Execute commands in an isolated directory.', default=False)
@click.option('--cleanup', help='Run commands and delete any created files if True.', default=False)
@click.option('--plain/--fancy', help='Enable basic output. Ideal for automation.', default=False)
@click.option('--quiet', help='Suppress all output from build-magic.', type=bool)
@click.option('--verbose/--standard', '-v', help='Verbose output.', default=False)
@click.option('--version', help='Display the build-magic version.', type=bool)
@click.argument('args', nargs=-1)
def build_magic(
        cleanup,
        command,
        copy,
        continue_,
        environment,
        args,
        isolate,
        runner,
        wd,
        plain,
        quiet,
        verbose,
        version,
):
    """An un-opinionated build automation tool.

    ARGS - Files as arguments to copy from the copy path to the working directory.
    Alternatively, ARGS can be a single command to execute if the --command option isn't used.
    In this case, type -- followed by the command.
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

    if not commands or commands == ['']:
        click.echo(USAGE)
        sys.exit(1)

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
        wd=wd,
    )

    # Run the stage.
    code = core.Engine.run([stage], continue_on_fail=continue_)

    sys.exit(code)
