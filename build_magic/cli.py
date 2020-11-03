""""""

import click
import sys

from build_magic import core


RUNNERS = click.Choice(core.Runners.available(), case_sensitive=False)


@click.command()
@click.option('--runner', '-r', default='local', help='The command runner to use', type=RUNNERS)
@click.option('--environment', '-e', default='', help='The runner environment to use', type=str)
@click.option('--command', '-c', help='A command to execute.', multiple=True, type=(str, str))
@click.option('--test/--no-test', '-t', help='Run commands and delete any created files when complete.', default=False)
@click.option('--continue-on-fail/--stop-on-fail', help='Continue to run after failure if True', default=False)
def build_magic(runner, environment, command, test, continue_on_fail):
    """"""
    action = 'default'
    if test:
        action = 'cleanup'
    if command:
        types, commands = list(zip(*command))
    else:
        types, commands = [], []
    stage = core.StageFactory.build(
        sequence=1,
        runner_type=runner,
        directives=list(types),
        artifacts=[],
        action=action,
        commands=list(commands),
        environment=environment,
    )
    code = core.Engine.run([stage], continue_on_fail=continue_on_fail)
    sys.exit(code)
