"""This module hosts unit tests for the ci module."""

import operator

import pytest
import yaml

from build_magic.ci import CI, export, GitHub, GitLab, Stage, Step


ds = Step(':')  # Dummy Step for testing


@pytest.fixture
def single_stage_config(config_file):
    """Provides a single stage config as a dictionary."""
    with open(config_file, 'r') as cfg:
        return yaml.safe_load(cfg)


@pytest.fixture
def multi_stage_config(multi_config):
    """Provides a multi-stage config as a dictionary."""
    with open(multi_config, 'r') as cfg:
        return yaml.safe_load(cfg)


@pytest.fixture
def env_stage_config(env_config):
    """Provides a stage with environment variables as a dictionary."""
    with open(env_config, 'r') as cfg:
        return yaml.safe_load(cfg)


@pytest.fixture
def multi_stage_no_name_config(multi_no_name_config):
    """Provides a multi-stage config without stage names as a dictionary."""
    with open(multi_no_name_config, 'r') as cfg:
        return yaml.safe_load(cfg)


@pytest.fixture
def label_stage_config(labels_config):
    """Provides a config with labels as a dictionary."""
    with open(labels_config, 'r') as cfg:
        return yaml.safe_load(cfg)


@pytest.mark.parametrize(
    ('command', 'label', 'sequence', 'expected_label', 'expected_seq'),
    [
        ('echo hello world', '', 1, '', 1),
        ('echo hello world', 'test', None, 'test', 1),
        ('echo hello world', None, None, '', 1),
        ('echo hello world', 'test', 4, 'test', 4),
    ]
)
def test_step_build(command, label, sequence, expected_label, expected_seq):
    """Verify creating a Step works correctly."""
    args = {}
    if command is not None:
        args['command'] = command
    if label is not None:
        args['label'] = label
    if sequence is not None:
        args['sequence'] = sequence
    step = Step(**args)
    assert step.command == command
    assert step.label == expected_label
    assert step.sequence == expected_seq


def test_step_bad_sequence():
    """Test the case where the provided sequence is invalid."""
    with pytest.raises(ValueError, match='sequence must be greater than 0'):
        Step(':', sequence=0)

    with pytest.raises(ValueError, match='sequence must be greater than 0'):
        Step(':', sequence=-1)


@pytest.mark.parametrize(
    ('first', 'second', 'op', 'expected'),
    [
        (Step(':', sequence=1), Step(':', sequence=4), operator.eq, False),
        (Step(':'), Step(':'), operator.eq, True),
        (Step(':', label='test'), Step(':', label='test'), operator.eq, True),
        (Step(':', label='test'), Step(':'), operator.eq, False),
        (Step(':'), Step('echo hello'), operator.eq, False),
        (Step(':', sequence=1), Step(':', sequence=1), operator.ne, False),
        (Step(':', sequence=1), Step(':', sequence=1), operator.le, True),
        (Step(':', sequence=1), Step(':', sequence=1), operator.ge, True),
        (Step(':', sequence=1), Step(':', sequence=2), operator.ne, True),
        (Step(':', sequence=1), 'dummy', operator.ne, True),
        (Step(':', sequence=1), Step(':', sequence=2), operator.lt, True),
        (Step(':', sequence=1), 'dummy', operator.lt, False),
        (Step(':', sequence=1), Step(':', sequence=2), operator.le, True),
        (Step(':', sequence=1), 'dummy', operator.le, False),
        (Step(':', sequence=1), Step(':', sequence=2), operator.gt, False),
        (Step(':', sequence=1), 'dummy', operator.gt, False),
        (Step(':', sequence=1), Step(':', sequence=2), operator.ge, False),
        (Step(':', sequence=1), 'dummy', operator.ge, False),
    ]
)
def test_step_comparison(first, second, op, expected):
    """Verify comparing Step objects works correctly."""
    assert op(first, second) is expected


def test_step_repr():
    """Verify the Step __repr__ method works as expected."""
    assert str(Step('echo hello', 'say hello', 2)) == '<echo hello say hello 2>'


@pytest.mark.parametrize(
    ('steps', 'name', 'runner', 'env', 'var', 'seq', 'ex_steps', 'ex_name', 'ex_runner', 'ex_env', 'ex_var', 'ex_seq'),
    [
        ([ds], None, None, None, None, None, (ds,), '', 'local', '', {}, 1),
        ([ds], 'ok', None, None, None, None, (ds,), 'ok', 'local', '', {}, 1),
        ([ds], None, 'docker', None, None, None, (ds,), '', 'docker', '', {}, 1),
        ([ds], None, None, 'macos', None, None, (Step(':'),), '', 'local', 'macos', {}, 1),
        ([ds], None, None, None, {'$PORT': 3000}, None, (Step(':'),), '', 'local', '', {'$PORT': 3000}, 1),
        ([ds], None, None, None, None, 3, (ds,), '', 'local', '', {}, 3),
        ((ds,), None, None, None, None, None, (ds,), '', 'local', '', {}, 1),
        ([ds], None, None, None, {'$PORT': 3000}, None, (ds,), '', 'local', '', {'$PORT': 3000}, 1),
    ]
)
def test_stage_build(steps, name, runner, env, var, seq, ex_steps, ex_name, ex_runner, ex_env, ex_var, ex_seq):
    """Verify creating a Stage object works correctly."""
    args = {}
    if steps is not None:
        args['steps'] = steps
    if name is not None:
        args['name'] = name
    if runner is not None:
        args['runner'] = runner
    if env is not None:
        args['environment'] = env
    if var is not None:
        args['variables'] = var
    if seq is not None:
        args['sequence'] = seq
    stage = Stage(**args)
    assert stage.steps == ex_steps
    assert stage.name == ex_name
    assert stage.runner == ex_runner
    assert stage.environment == ex_env
    assert stage.variables == ex_var
    assert stage.sequence == ex_seq


def test_stage_steps_wrong_type():
    """Test the case where steps are not a list or tuple."""
    with pytest.raises(TypeError, match='steps must be a list or tuple'):
        Stage(1)


def test_stage_steps_wrong_step_type():
    """Test the case where the steps is not a sequence of Step objects."""
    with pytest.raises(TypeError, match='steps must be a list or tuple of Step objects.'):
        Stage(['wrong'])


def test_stage_bad_sequence():
    """Test the case where the provided sequence is invalid."""
    with pytest.raises(ValueError, match='sequence must be greater than 0'):
        Stage([Step(':')], sequence=0)

    with pytest.raises(ValueError, match='sequence must be greater than 0'):
        Stage([Step(':')], sequence=-1)


@pytest.mark.parametrize(
    ('first', 'second', 'op', 'expected'),
    [
        (Stage([ds], sequence=1), Stage([ds], sequence=1), operator.eq, True),
        (Stage([ds], 'ok'), Stage([ds], 'ok'), operator.eq, True),
        (Stage([ds]), 'dummy', operator.ne, True),
        (Stage([ds], 'ok', 'docker'), Stage([ds], 'ok', 'docker'), operator.eq, True),
        (Stage([ds], 'ok', 'docker', 'f'), Stage([ds], 'ok', 'docker', 'f'), operator.eq, True),
        (Stage([ds], 'z', 'd', 'f', {'T': 't'}), Stage([ds], 'z', 'd', 'f', {'T': 't'}), operator.eq, True),
        (Stage([ds], 'z', 'd', 'f', {'T': 't'}, 7), Stage([ds], 'z', 'd', 'f', {'T': 't'}, 7), operator.eq, True),
        (Stage([ds], 'z', 'd', 'f', {'T': 't'}, 1), Stage([ds], 'z', 'd', 'f', {'T': 't'}, 7), operator.eq, False),
        (Stage([ds], 'z', 'd', 'g', {'T': 't'}, 7), Stage([ds], 'z', 'd', 'f', {'T': 't'}, 7), operator.eq, False),
        (Stage([ds], 'z', 'd', 'f', {'T': 't'}, 1), Stage([ds], 'z', 'd', 'f', {'T': 't'}, 7), operator.ne, True),
        (Stage([ds], 'z', 'd', 'g', {'T': 't'}, 7), Stage([ds], 'z', 'd', 'f', {'T': 't'}, 7), operator.ne, True),
        (Stage([ds], sequence=1), Stage([ds], sequence=1), operator.le, True),
        (Stage([ds], sequence=1), Stage([ds], sequence=1), operator.ge, True),
        (Stage([ds], sequence=1), Stage([ds], sequence=2), operator.lt, True),
        (Stage([ds], sequence=1), 'dummy', operator.lt, False),
        (Stage([ds], sequence=1), Stage([ds], sequence=2), operator.le, True),
        (Stage([ds], sequence=1), 'dummy', operator.le, False),
        (Stage([ds], sequence=1), Stage([ds], sequence=2), operator.gt, False),
        (Stage([ds], sequence=1), 'dummy', operator.gt, False),
        (Stage([ds], sequence=1), Stage([ds], sequence=2), operator.ge, False),
        (Stage([ds], sequence=1), 'dummy', operator.ge, False),
    ]
)
def test_stage_comparisons(first, second, op, expected):
    """Verify comparing Stage objects works correctly."""
    assert op(first, second) is expected


def test_stage_repr():
    """Verify the Stage __repr__ method works correctly."""
    assert str(Stage([ds], 'test', environment='linux', variables={'HELLO': 'world'})) == \
           "<(<:  1>,) test local linux dict_keys(['HELLO']) 1>"


def test_ci_prepare_single_stage(single_stage_config):
    """Verify the CI prepare method works correctly with a single stage."""
    stages = CI(single_stage_config)._prepare()
    assert len(stages) == 1
    stage = stages[0]
    assert stage.name == 'Test stage'
    assert stage.steps == (Step('echo hello', sequence=1), Step('ls', sequence=2))
    assert stage.runner == 'local'
    assert stage.environment == ''
    assert stage.variables == {}
    assert stage.sequence == 1


def test_ci_prepare_multi_stage(multi_stage_config):
    """Verify the CI prepare method works correctly with multiple stages."""
    stages = CI(multi_stage_config)._prepare()
    assert len(stages) == 2
    assert stages[0].name == 'Stage A'
    assert stages[1].name == 'Stage B'
    assert stages[0].sequence == 1
    assert stages[1].sequence == 2


def test_ci_prepare_variables_stage(env_stage_config):
    """Verify the CI prepare method works correctly with stage variables."""
    stages = CI(env_stage_config)._prepare()
    assert len(stages) == 1
    stage = stages[0]
    assert stage.name == ''
    assert stage.runner == 'local'
    assert stage.environment == ''
    assert stage.variables == {'HELLO': 'hello', 'WORLD': 'world'}
    assert stage.sequence == 1


def test_ci_prepare_bad_config():
    """Test the case where the config dictionary doesn't start with build-magic."""
    config = {'hello': 'world'}
    with pytest.raises(KeyError, match='build-magic key not found in config'):
        CI(config)._prepare()


def test_ci_base_class_convert(single_stage_config):
    """Test the case where the CI.convert() abstract method is called."""
    with pytest.raises(NotImplementedError):
        CI(single_stage_config).to_yaml()


def test_ci_prepare_missing_commands():
    """Test the case where the config dictionary is missing the commands key."""
    config = {
        'build-magic': [
            {
                'stage': {
                    'name': 'test',
                }
            }
        ]
    }
    with pytest.raises(KeyError, match='commands not found in stage.'):
        CI(config)._prepare()


def test_ci_bad_config():
    """Test the case where a type other than a dictionary is provided as the config argument."""
    config = 'dummy'
    with pytest.raises(TypeError, match='Cannot read config.'):
        CI(config)


def test_ci_prepare_bad_command_directive():
    """Test the case where the config dictionary has a bad config directive."""
    config = {
        'build-magic': [
            {
                'stage': {
                    'commands': [
                        {
                            'execute': 'echo hello world',
                        },
                        {
                            'dummy': 'ls',
                        },
                        {
                            'hello': 'world',
                        }
                    ]
                }
            }
        ]
    }
    with pytest.raises(KeyError, match='Key dummy not found in command.'):
        CI(config)._prepare()


def test_gitlab_to_yaml_single_stage(single_stage_config):
    """Verify the GitLab to_yaml method works correctly for a single stage."""
    output = GitLab(single_stage_config).to_yaml()
    assert output == """Test stage:
  stage: Test stage
  scripts:
    - echo hello
    - ls
"""


def test_gitlab_to_yaml_multi_stage(multi_stage_config):
    """Verify the GitLab to_yaml method works correctly for multiple stages."""
    output = GitLab(multi_stage_config).to_yaml()
    assert output == """Stage A:
  stage: Stage A
  scripts:
    - ls
    - touch hello.txt
Stage B:
  stage: Stage B
  scripts:
    - ls hello.txt
"""


def test_gitlab_to_yaml_environment_variables(env_stage_config):
    """Verify the GitLab to_yaml method works correctly for environment variables."""
    output = GitLab(env_stage_config).to_yaml()
    assert output == """build-magic 1/1:
  stage: build-magic
  variables:
    $HELLO: hello
    $WORLD: world
  scripts:
    - echo $HELLO $WORLD $FOO
"""


def test_gitlab_to_yaml_auto_name_jobs(multi_stage_no_name_config):
    """Verify the GitLab to_yaml method works correctly when automatically creating job names."""
    output = GitLab(multi_stage_no_name_config).to_yaml()
    assert output == """build-magic 1/3:
  stage: build-magic
  scripts:
    - echo one
    - echo two
build-magic 2/3:
  stage: build-magic
  scripts:
    - echo three
build-magic 3/3:
  stage: build-magic
  scripts:
    - echo four
    - echo five
"""


def test_github_to_yaml_single_stage(single_stage_config):
    """Verify the GitHub to_yaml method works correctly for a single stage."""
    output = GitHub(single_stage_config).to_yaml()
    assert output == """jobs:
  Test stage:
    steps:
      - run: echo hello
      - run: ls
"""


def test_github_to_yaml_multi_stage(multi_stage_config):
    """Verify the GitHub to_yaml method works correctly for multiple stages."""
    output = GitHub(multi_stage_config).to_yaml()
    assert output == """jobs:
  Stage A:
    steps:
      - run: ls
      - run: touch hello.txt
  Stage B:
    steps:
      - run: ls hello.txt
"""


def test_github_to_yaml_environment_variables(env_stage_config):
    """Verify the GitHub to_yaml method works correctly for environment variables."""
    output = GitHub(env_stage_config).to_yaml()
    assert output == """jobs:
  build-magic1:
    env:
      HELLO: hello
      WORLD: world
    steps:
      - run: echo $HELLO $WORLD $FOO
"""


def test_github_to_yaml_labels(label_stage_config):
    """Verify the GitHub to_yaml method works correctly with labels."""
    output = GitHub(label_stage_config).to_yaml()
    assert output == """jobs:
  Test stage:
    steps:
      - name: Say hello to the user.
        run: echo hello
      - name: Say goodbye to the user.
        run: echo goodbye
"""


def test_github_to_yaml_auto_name_jobs(multi_stage_no_name_config):
    """Verify the GitHub to_yaml method works correctly when automatically creating job names."""
    output = GitHub(multi_stage_no_name_config).to_yaml()
    assert output == """jobs:
  build-magic1:
    steps:
      - run: echo one
      - run: echo two
  build-magic2:
    steps:
      - run: echo three
  build-magic3:
    steps:
      - run: echo four
      - run: echo five
"""


def test_export_gitlab(single_stage_config):
    """Verify the export() function successfully exports to gitlab."""
    output = export(single_stage_config, 'gitlab')
    assert output == """Test stage:
  stage: Test stage
  scripts:
    - echo hello
    - ls
"""


def test_export_github(single_stage_config):
    """Verify the export() function successfully exports to github."""
    output = export(single_stage_config, 'github')
    assert output == """jobs:
  Test stage:
    steps:
      - run: echo hello
      - run: ls
"""


def test_export_unknown_ci(single_stage_config):
    """Test the case where an unknown CI string is passed to the export() function."""
    with pytest.raises(ValueError, match=r"Export type must be one of \('github', 'gitlab'\)"):
        export(single_stage_config, 'dummy')
