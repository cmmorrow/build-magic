"""This module hosts unit tests for the core classes."""

import pytest

from build_magic.actions import Default
from build_magic.core import (
    config_parser, Engine, ExecutionError, NoJobs, SetupError, Stage, StageFactory, TeardownError
)
from build_magic.macro import Macro
from build_magic.runner import Local


def test_stage_constructor():
    """Verify the Stage constructor works correctly."""
    args = (Local(), [Macro('ls')], ['execute'], 1, 'default')
    stage = Stage(*args)
    assert isinstance(stage._command_runner, Local)
    assert stage._action is Default
    assert stage._directives == ['execute']
    assert isinstance(stage._macros[0], Macro)
    assert stage._macros[0].command == 'ls'
    assert stage._result == 0
    assert stage._results == []
    assert stage.sequence == 1
    assert not stage.is_setup


def test_stage_constructor_invalid_action():
    """Test the case where an invalid action is passed to the Stage constructor."""
    args = (Local(), [Macro('ls')], ['execute'], 1, 'dummy')
    with pytest.raises(ValueError, match='Action must be one of'):
        Stage(*args)


def test_stage_setup(mocker):
    """Verify the Stage setup() method works correctly."""
    mocker.patch('build_magic.runner.Local.prepare', return_value=True)
    args = (Local(), [Macro('ls')], ['execute'], 1, 'default')
    stage = Stage(*args)
    assert hasattr(stage._command_runner, 'provision')
    assert hasattr(stage._command_runner, 'teardown')
    assert stage._command_runner.provision() is False
    assert stage._command_runner.teardown() is False
    stage.setup()
    assert stage._is_setup
    assert stage._command_runner.provision() is True
    assert stage._command_runner.teardown() is True


def test_stage_run():
    """Verify the Stage run() method works correctly."""
    args = (Local(), [Macro('ls')], ['execute'], 1, 'default')
    stage = Stage(*args)
    assert stage.is_setup is False
    exit_code = stage.run()
    assert exit_code == 0
    assert len(stage._results) == 1
    assert stage.is_setup is True


def test_stage_run_multiple():
    """Verify the stage run() method works correctly with multiple commands."""
    macros = [Macro('ls'), Macro(prefix='echo', command='hello'), Macro('ls')]
    args = (Local(), macros, ['execute'], 1, 'default')
    stage = Stage(*args)
    assert stage.is_setup is False
    exit_code = stage.run()
    assert exit_code == 0
    assert len(stage._results) == 3
    assert stage.is_setup is True


def test_stage_run_setup_fail(mocker):
    """Test the case where the Stage run() method raises a SetupError."""
    mocker.patch('build_magic.actions.null', return_value=False)
    args = (Local(), [Macro('ls')], ['execute'], 1, 'default')
    stage = Stage(*args)
    with pytest.raises(SetupError):
        stage.run()


def test_stage_run_teardown_fail(mocker):
    """Test the case where the Stage run() method raises a TeardownError."""
    mocker.patch('build_magic.actions.null', side_effect=(True, False))
    args = (Local(), [Macro('ls')], ['execute'], 1, 'default')
    stage = Stage(*args)
    with pytest.raises(TeardownError):
        stage.run()


def test_stage_run_fail():
    """Test the case where the command executed by the run() method returns a non-zero exit code."""
    args = (Local(), [Macro('cp')], ['execute'], 1, 'default')
    stage = Stage(*args)
    exit_code = stage.run()
    assert exit_code > 0


def test_stage_run_exception(mocker):
    """Test the case where the command raises an Exception."""
    mocker.patch('build_magic.runner.Local.execute', side_effect=RuntimeError)
    args = (Local(), [Macro('ls')], ['execute'], 1, 'default')
    stage = Stage(*args)
    with pytest.raises(ExecutionError):
        stage.run()


def test_stage_run_multiple_fail():
    """Test the case where multiple commands are run and the last one returns a non-zero exit code."""
    macros = [Macro('ls'), Macro(prefix='echo', command='hello'), Macro('cp')]
    args = (Local(), macros, ['execute'], 1, 'default')
    stage = Stage(*args)
    assert stage.is_setup is False
    exit_code = stage.run()
    assert exit_code == 1
    assert len(stage._results) == 3


def test_stage_run_multiple_fail_2():
    """Test the case where multiple commands are run and execution halts with a command in the middle."""
    macros = [Macro('ls'), Macro('cp'), Macro(prefix='echo', command='hello')]
    args = (Local(), macros, ['execute'], 1, 'default')
    stage = Stage(*args)
    assert stage.is_setup is False
    exit_code = stage.run()
    assert exit_code == 1
    assert len(stage._results) == 2


def test_stage_run_multiple_continue_on_fail():
    """Test the case where multiple commands are run, one fails, but execution continues."""
    macros = [Macro('ls'), Macro('cp'), Macro(prefix='echo', command='hello')]
    args = (Local(), macros, ['execute'], 1, 'default')
    stage = Stage(*args)
    assert stage.is_setup is False
    exit_code = stage.run(continue_on_fail=True)
    assert exit_code == 1
    assert len(stage._results) == 3


def test_stage_run_verbose(capsys):
    """Verify the Stage run() method handles verbose mode correctly."""
    args = (Local(), [Macro('echo hello')], ['execute'], 1, 'default')
    stage = Stage(*args)
    assert stage.is_setup is False
    exit_code = stage.run(verbose=True)
    assert exit_code == 0
    assert len(stage._results) == 1
    assert stage.is_setup is True
    captured = capsys.readouterr()
    assert '\nOUTPUT  : hello\n' in captured.out


def test_stagefactory_build():
    """Verify the StageFactory build() method works correctly."""
    args = (0, 'local', ['execute'], None, ['ls'], '', 'default', '.', '.')
    stage = StageFactory.build(*args)
    assert isinstance(stage._command_runner, Local)
    assert stage._action is Default
    assert stage._directives == ['execute']
    assert isinstance(stage._macros[0], Macro)
    assert stage._macros[0].command == 'ls'
    assert stage._result == 0
    assert stage._results == []
    assert stage.sequence == 0
    assert not stage.is_setup


def test_stagefactory_build_invalid_runner():
    """Test the case where an invalid runner is passed to the StageFactory build() method."""
    args = (0, 'dummy', ['execute'], None, ['ls'], '', 'default', '.', '.')
    with pytest.raises(ValueError, match='Runner must be one of'):
        StageFactory.build(*args)


def test_stagefactory_build_invalid_directive():
    """Test the case where an invalid directive is passed to the StageFactory build() method."""
    args = (0, 'local', ['dummy'], None, ['ls'], '', 'default', '.', '.')
    with pytest.raises(ValueError, match='Directive must be one of'):
        StageFactory.build(*args)


def test_stagefactory_build_no_jobs():
    """Test the case where no jobs a passed to the StageFactory build() method."""
    args = (0, 'local', ['execute'], None, [], '', 'default', '.', '.')
    with pytest.raises(NoJobs):
        StageFactory.build(*args)


def test_stagefactory_build_invalid_environment():
    """Test the case where an invalid environment is passed to the StageFactory build() method."""
    args = (0, 'docker', ['execute'], None, ['ls'], '', 'default', '.', '.')
    with pytest.raises(ValueError, match='Environment must be a Docker image'):
        StageFactory.build(*args)

    args = (0, 'vagrant', ['execute'], None, ['ls'], '', 'default', '.', '.')
    with pytest.raises(ValueError, match='Environment must be a path to a Vagrant file'):
        StageFactory.build(*args)


def test_stagefactory_build_invalid_copy_directory():
    """Test the case where a non-existent copy directory is passed to the StageFactory build() method."""
    args = (0, 'local', ['execute'], None, ['ls'], '', 'default', 'dummy', '.')
    with pytest.raises(NotADirectoryError, match='Path dummy does not exist'):
        StageFactory.build(*args)


def test_stagefactory_build_unequal_directives_and_commands():
    """Test the case where the number of commands is unequal to the number of directives."""
    args = (0, 'local', ['execute', 'build'], None, ['ls'], '', 'default', '.', '.')
    with pytest.raises(ValueError, match='Length of commands unequal'):
        StageFactory.build(*args)


def test_stagefactory_build_invalid_action():
    """Test the case where an invalid action is passed to the StageFactory build() method."""
    args = (0, 'local', ['execute'], None, ['ls'], '', 'dummy', '.', '.')
    with pytest.raises(ValueError, match='Action must be one of'):
        StageFactory.build(*args)


def test_engine_constructor():
    """Verify the Engine constructor works correctly."""
    stage0 = Stage(Local(), [Macro('ls'), Macro('cat')], ['execute'], 0, 'default')
    stage1 = Stage(Local(), [Macro('echo hello')], ['execute'], 1, 'default')
    stage2 = Stage(Local(), [], [], 2, 'default')

    engine = Engine([stage1, stage0, stage2])
    assert engine._stages[0].sequence == 0
    assert engine._stages[1].sequence == 1
    assert engine._stages[2].sequence == 2
    assert not engine._continue_on_fail


def test_config_parser():
    """Verify the config parser works correctly."""
    config = {
        'stages': [
            {
                'stage': {
                    'name': 'stage 1',
                    'persist': True,
                    'continue on fail': True,
                    'runner': 'docker',
                    'environment': 'alpine:latest',
                    'copy from directory': '/src',
                    'artifacts': [
                        'file1.txt',
                        'file2.txt',
                    ],
                    'commands': [
                        {'build': 'tar -czf myfiles.tar.gz file1.txt file2.txt'},
                        {'execute': 'rm file1.txt file2.txt'}
                    ]
                }
            },
            {
                'stage': {
                    'name': 'stage 2',
                    'cleanup': True,
                    'working directory': '/src',
                    'commands': [
                        {'install': 'tar -xzf myfiles.tar.gz'},
                        {'execute': 'rm myfiles.tar.gz'},
                        {'deploy': 'cat file1.txt file2.txt'},
                    ]
                }
            }
        ]
    }
    ref = [
        {
            'name': 'stage 1',
            'runner_type': 'docker',
            'environment': 'alpine:latest',
            'continue': True,
            'wd': '.',
            'copy': '/src',
            'artifacts': ['file1.txt', 'file2.txt'],
            'action': 'persist',
            'commands': [
                'tar -czf myfiles.tar.gz file1.txt file2.txt',
                'rm file1.txt file2.txt',
            ],
            'directives': [
                'build',
                'execute',
            ]
        },
        {
            'name': 'stage 2',
            'runner_type': 'local',
            'environment': '',
            'continue': False,
            'wd': '/src',
            'copy': '.',
            'artifacts': [],
            'action': 'cleanup',
            'commands': [
                'tar -xzf myfiles.tar.gz',
                'rm myfiles.tar.gz',
                'cat file1.txt file2.txt',
            ],
            'directives': [
                'install',
                'execute',
                'deploy',
            ]
        }
    ]
    stages = config_parser(config)
    assert stages == ref


def test_config_parser_validation_fail():
    """Test the case where config file schema validation fails."""
    config = {
        'blah': []
    }
    with pytest.raises(ValueError):
        config_parser(config)
