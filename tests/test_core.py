"""This module hosts unit tests for the core classes."""

import json
import os
import pathlib

import pytest

from build_magic.actions import Default
from build_magic.core import (
    config_parser, Engine, generate_config_template, iterate_sequence, parse_variables, Stage, StageFactory
)
from build_magic.exc import ExecutionError, SetupError, TeardownError, NoJobs, ValidationError
from build_magic.macro import Macro
from build_magic.reference import KeyPath, KeyType
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
    with pytest.raises(SetupError, match='Setup failed'):
        stage.run()


def test_stage_run_teardown_fail(mocker):
    """Test the case where the Stage run() method raises a TeardownError."""
    mocker.patch('build_magic.actions.null', side_effect=(True, False))
    args = (Local(), [Macro('ls')], ['execute'], 1, 'default')
    stage = Stage(*args)
    with pytest.raises(TeardownError, match='Teardown failed'):
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
    with pytest.raises(ExecutionError, match='Command execution error'):
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
    assert '\nOUTPUT: hello\n' in captured.out


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
    with pytest.raises(NoJobs, match='No jobs to execute'):
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
    with pytest.raises(ValueError, match='Length of commands unequal to length of directives.'):
        StageFactory.build(*args)


def test_stagefactory_build_invalid_action():
    """Test the case where an invalid action is passed to the StageFactory build() method."""
    args = (0, 'local', ['execute'], None, ['ls'], '', 'dummy', '.', '.')
    with pytest.raises(ValueError, match='Action must be one of'):
        StageFactory.build(*args)


def test_stagefactory_build_parameters():
    """Verify the StageFactory _build_parameters() class method works correctly."""
    ref = {
        'keytype': KeyType('ECDSAKey'),
        'keypath': KeyPath('$HOME/.ssh/key_ecdsa'),
    }
    params = [('keypath', f'$HOME/.ssh/key_ecdsa'), ('keytype', 'ecdsa')]
    out = StageFactory._build_parameters(params)
    assert out == ref


def test_stagefactory_build_parameters_invalid():
    """Test the case where StageFactory _build_parameters() is passed an invalid parameter."""
    params = [('dummy', '1234')]
    with pytest.raises(ValueError, match='Parameter dummy is not a valid parameter.'):
        StageFactory._build_parameters(params)


def test_stagefactory_build_parameters_validation_fail():
    """Test the case where StageFactory _build_parameters() is passed an invalid parameter value."""
    params = [('keytype', 'dummy')]
    with pytest.raises(ValidationError):
        StageFactory._build_parameters(params)


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


def test_engine_stage_list_type_fail():
    """Verify the stages argument must be a list."""
    params = "dummy"
    with pytest.raises(TypeError):
        Engine(params)


def test_generate_config_template():
    """Verify the generate_config_template() function works correctly."""
    filename = 'build-magic_template.yaml'
    template = pathlib.Path(__file__).parent.parent / 'build_magic' / 'static' / filename
    ref = template.read_text()

    config = generate_config_template()
    content = config.read_text()
    os.unlink(config)
    assert content == ref


def test_config_parser():
    """Verify the config parser works correctly."""
    config = {
        'build-magic': [
            {
                'stage': {
                    'name': 'stage 1',
                    'action': 'persist',
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
                        {'execute': 'rm file1.txt file2.txt'},
                    ]
                }
            },
            {
                'stage': {
                    'name': 'stage 2',
                    'action': 'cleanup',
                    'working directory': '/src',
                    'commands': [
                        {'install': 'tar -xzf myfiles.tar.gz'},
                        {'execute': 'rm myfiles.tar.gz'},
                        {'deploy': 'cat file1.txt file2.txt'},
                        {'release': 'git push origin main'},
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
            ],
            'parameters': [],
        },
        {
            'name': 'stage 2',
            'runner_type': 'local',
            'environment': '',
            'continue': False,
            'wd': '/src',
            'copy': '',
            'artifacts': [],
            'action': 'cleanup',
            'commands': [
                'tar -xzf myfiles.tar.gz',
                'rm myfiles.tar.gz',
                'cat file1.txt file2.txt',
                'git push origin main',
            ],
            'directives': [
                'install',
                'execute',
                'deploy',
                'release',
            ],
            'parameters': [],
        }
    ]
    stages = config_parser(config)
    assert stages == ref


def test_config_parser_with_parameters():
    """Verify the config parser handles parameters correctly."""
    config = {
        'build-magic': [
            {
                'stage': {
                    'runner': 'remote',
                    'environment': 'user@myhost:2222',
                    'parameters': [
                        {'keytype': 'ecdsa'},
                        {'keypath': '$HOME/user/.ssh/key_ecdsa'},
                        {'keypass': '"1234"'},
                    ],
                    'commands': [
                        {'test': 'ls'},
                    ]
                }
            }
        ]
    }
    ref = [
        {
            'name': '',
            'runner_type': 'remote',
            'environment': 'user@myhost:2222',
            'continue': False,
            'wd': '.',
            'copy': '',
            'artifacts': [],
            'action': 'default',
            'commands': [
                'ls',
            ],
            'directives': [
                'test',
            ],
            'parameters': [
                ('keytype', 'ecdsa'),
                ('keypath', '$HOME/user/.ssh/key_ecdsa'),
                ('keypass', '"1234"'),
            ],
        }
    ]
    stages = config_parser(config)
    assert stages == ref


def test_config_parser_with_parameters_validation_fail():
    """Test the case where an invalid parameter value is provided."""
    config = {
        'build-magic': [
            {
                'stage': {
                    'runner': 'remote',
                    'environment': 'user@myhost:2222',
                    'parameters': [
                        {'keytype': 'dummy'},
                        {'keypath': '$HOME/user/.ssh/key_ecdsa'},
                        {'keypass': '"1234"'},
                    ],
                    'commands': [
                        {'execute': 'ls'},
                    ]
                }
            }
        ]
    }
    with pytest.raises(ValueError):
        config_parser(config)


def test_config_parser_validation_fail():
    """Test the case where config file schema validation fails."""
    config = {
        'blah': []
    }
    with pytest.raises(ValueError):
        config_parser(config)


def test_iterative_sequence():
    """Verify the iterate_sequence works correctly."""
    seq = iterate_sequence()
    out = []
    i = 0
    while i < 5:
        out.append(next(seq))
        i += 1
    assert out == [1, 2, 3, 4, 5]


def test_parse_variables():
    """Verify parser_variables works correctly."""
    variables = {
        'OS': 'linux',
        'ARCH': 'arm64',
    }
    config = {
        'build-magic': [
            {
                'stage': {
                    'name': 'example',
                    'runner': 'local',
                    'commands': [
                        {'execute': 'export GOARCH={{ ARCH }}'},
                        {'execute': 'export GOOS={{ OS }}'},
                    ]
                }
            }
        ]
    }
    output = parse_variables(config, variables)
    assert json.dumps(output) == (
        '{"build-magic": [{"stage": {"name": "example", "runner": "local", "commands": '
        '[{"execute": "export GOARCH=arm64"}, {"execute": "export GOOS=linux"}]}}]}'
    )


def test_parse_variables_multiple_matches():
    """Verify parser_variables works with substituting multiple instances of the same variable."""
    variables = {
        'user': 'max',
        'pass': 'dummy',
        'version': '2.2.2',
    }
    config = {
        'build-magic': [
            {
                'stage': {
                    'name': 'example',
                    'commands': [
                        {'execute': 'prep.sh --version {{ version }}'},
                        {'build': 'build.sh --u {{ user }} --pass {{ pass }} --version {{ version }}'},
                        {'install': 'docker build -t test:{{ version }} .'},
                    ]
                }
            }
        ]
    }
    output = parse_variables(config, variables)
    assert json.dumps(output) == (
        '{"build-magic": [{"stage": {"name": "example", "commands": [{"execute": "prep.sh --version 2.2.2"}, '
        '{"build": "build.sh --u max --pass dummy --version 2.2.2"}, {"install": "docker build -t test:2.2.2 ."}]}}]}'
    )


def test_parse_variables_different_spacing():
    """Verify parser_variables works with inconsistent spacing around the placeholder text."""
    variables = {
        'user': 'max',
        'pass': 'dummy',
        'version': '2.2.2',
    }
    config = {
        'build-magic': [
            {
                'stage': {
                    'name': 'example',
                    'commands': [
                        {'execute': 'prep.sh --version {{version }}'},
                        {'build': 'build.sh --u {{ user }} --pass {{pass}} --version {{ version}}'},
                        {'install': 'docker build -t test:{{version}} .'},
                    ]
                }
            }
        ]
    }
    output = parse_variables(config, variables)
    assert json.dumps(output) == (
        '{"build-magic": [{"stage": {"name": "example", "commands": [{"execute": "prep.sh --version 2.2.2"}, '
        '{"build": "build.sh --u max --pass dummy --version 2.2.2"}, {"install": "docker build -t test:2.2.2 ."}]}}]}'
    )


def test_parse_variables_no_matches():
    """Test the case where there are no matches for parse_variables to substitute."""
    variables = {
        'user': 'max',
        'pass': 'dummy',
        'version': '2.2.2',
    }
    config = {
        'build-magic': [
            {
                'stage': {
                    'name': 'example',
                    'runner': 'local',
                    'commands': [
                        {'execute': 'export GOARCH={{ ARCH }}'},
                        {'execute': 'export GOOS={{ OS }}'},
                    ]
                }
            }
        ]
    }
    with pytest.raises(ValueError, match='No variable matches found'):
        parse_variables(config, variables)


def test_parse_variables_too_much_space():
    """Test the case where a placeholder isn't substituted by parse_variables because there's too much white space."""
    variables = {
        'OS': 'linux',
        'ARCH': 'arm64',
    }
    config = {
        'build-magic': [
            {
                'stage': {
                    'name': 'example',
                    'runner': 'local',
                    'commands': [
                        {'execute': 'export GOARCH={{  ARCH }}'},
                        {'execute': 'export GOOS={{ OS     }}'},
                    ]
                }
            }
        ]
    }
    output = parse_variables(config, variables)
    assert json.dumps(output) == (
        '{"build-magic": [{"stage": {"name": "example", "runner": "local", "commands": '
        '[{"execute": "export GOARCH={{  ARCH }}"}, {"execute": "export GOOS={{ OS     }}"}]}}]}'
    )


def test_parse_variables_no_variables_no_placeholders():
    """Test the case where parse_variables isn't provided any variables or placeholders."""
    variables = {}
    config = {
        'build-magic': [
            {
                'stage': {
                    'name': 'example',
                    'runner': 'local',
                    'commands': [
                        {'execute': 'export GOARCH=arm64'},
                        {'execute': 'export GOOS=linux'},
                    ]
                }
            }
        ]
    }
    output = parse_variables(config, variables)
    assert json.dumps(output) == (
        '{"build-magic": [{"stage": {"name": "example", "runner": "local", "commands": '
        '[{"execute": "export GOARCH=arm64"}, {"execute": "export GOOS=linux"}]}}]}'
    )


def test_parse_variables_no_variables():
    """Test the case where parse_variables isn't provided any variables."""
    variables = {}
    config = {
        'build-magic': [
            {
                'stage': {
                    'name': 'example',
                    'runner': 'local',
                    'commands': [
                        {'execute': 'export GOARCH={{ ARCH }}'},
                        {'execute': 'export GOOS={{ OS }}'},
                    ]
                }
            }
        ]
    }
    output = parse_variables(config, variables)
    assert json.dumps(output) == (
        '{"build-magic": [{"stage": {"name": "example", "runner": "local", "commands": '
        '[{"execute": "export GOARCH={{ ARCH }}"}, {"execute": "export GOOS={{ OS }}"}]}}]}'
    )
