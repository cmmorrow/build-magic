"""This module hosts classes for representing Config Files in other CI/CD formats."""

from abc import abstractmethod
import yaml

from build_magic.reference import Directive, ExportType


class Step:
    """This class represents a single build-magic command for converting to a CI command."""

    __slots__ = ('_label', '_command', '_sequence')

    def __init__(self, command, label='', sequence=1):
        """Instantiate a new Step object."""
        self._command = command
        self._label = label
        if sequence < 1:
            raise ValueError('sequence must be greater than 0.')
        self._sequence = sequence

    def __eq__(self, other):
        """Magic method for comparing if two Step objects are equal.

        :param Any other: The object to compare against.
        :rtype: bool
        :return: True if other is a Step object and the relevant attributes in other are equal to self.
        """
        if isinstance(other, Step):
            return self._command == other.command and self._label == other.label and self._sequence == other.sequence
        return False

    def __lt__(self, other):
        """Magic method for comparing if self is less than other.

        :param Any other: The object to compare against.
        :rtype: bool
        :return: True if the sequence of self is less than the sequence of other.
        """
        if isinstance(other, Step):
            return self._sequence < other.sequence
        return False

    def __le__(self, other):
        """Magic method for comparing if self is less than or equal to other.

        :param Any other: The object to compare against.
        :rtype: bool
        :return: True if the sequence of self is less than or equal to the sequence of other.
        """
        if isinstance(other, Step):
            return self._sequence <= other.sequence
        return False

    def __gt__(self, other):
        """Magic method for comparing if self is greater than other.

        :param Any other: The object to compare against.
        :rtype: bool
        :return: True if the sequence of self is greater than the sequence of other.
        """
        if isinstance(other, Step):
            return self._sequence > other.sequence
        return False

    def __ge__(self, other):
        """Magic method for comparing if self is greater than or equal to other.

        :param Any other: The object to compare against.
        :rtype: bool
        :return: True if the sequence of self is greater than or equal to the sequence of other.
        """
        if isinstance(other, Step):
            return self._sequence >= other.sequence
        return False

    def __repr__(self):
        """The representation of a Step object when printed.

        :rtype: str
        :return: The representation of the Step object.
        """
        return f'<{self.command} {self.label} {self.sequence}>'

    @property
    def command(self):
        """Getter method for the command attribute.

        :return: The Step object command attribute.
        """
        return self._command

    @property
    def sequence(self):
        """Getter method for the sequence attribute.

        :return: The Step object sequence attribute.
        """
        return self._sequence

    @property
    def label(self):
        """Getter method for the label attribute.

        :return: The Step object label attribute.
        """
        return self._label


class Stage:
    """This class represents a build-magic stage for converting to a CI job."""

    __slots__ = ('_name', '_variables', '_steps', '_runner', '_environment', '_sequence')

    def __init__(self, steps, name='', runner='local', environment='', variables=None, sequence=1):
        """Instantiate a new Stage object."""
        self._name = name
        self._runner = runner
        self._environment = environment
        if sequence < 1:
            raise ValueError('sequence must be greater than 0.')
        self._sequence = sequence
        self._variables = variables if variables is not None else {}
        if not isinstance(steps, (list, tuple)):
            raise TypeError('steps must be a list or tuple.')
        for step in steps:
            if not isinstance(step, Step):
                raise TypeError('steps must be a list or tuple of Step objects.')
        self._steps = tuple(steps)

    def __eq__(self, other):
        """Magic method for comparing if two Stage objects are equal.

        :param Any other: The object to compare against.
        :rtype: bool
        :return: True if other is a Stage object and the relevant attributes in other are equal to self.
        """
        if isinstance(other, Stage):
            return all(
                (
                    self._steps == other.steps,
                    self._name == other.name,
                    self._runner == other.runner,
                    self._environment == other.environment,
                    self._variables == other.variables,
                    self._sequence == other.sequence,
                )
            )
        return False

    def __lt__(self, other):
        """Magic method for comparing if self is less than other.

        :param Any other: The object to compare against.
        :rtype: bool
        :return: True if the sequence of self is less than the sequence of other.
        """
        if isinstance(other, Stage):
            return self._sequence < other.sequence
        return False

    def __le__(self, other):
        """Magic method for comparing if self is less than or equal to other.

        :param Any other: The object to compare against.
        :rtype: bool
        :return: True if the sequence of self is less than or equal to the sequence of other.
        """
        if isinstance(other, Stage):
            return self._sequence <= other.sequence
        return False

    def __gt__(self, other):
        """Magic method for comparing if self is greater than other.

        :param Any other: The object to compare against.
        :rtype: bool
        :return: True if the sequence of self is greater than the sequence of other.
        """
        if isinstance(other, Stage):
            return self._sequence > other.sequence
        return False

    def __ge__(self, other):
        """Magic method for comparing if self is greater than or equal to other.

        :param Any other: The object to compare against.
        :rtype: bool
        :return: True if the sequence of self is greater than or equal to the sequence of other.
        """
        if isinstance(other, Stage):
            return self._sequence >= other.sequence
        return False

    def __repr__(self):
        """The representation of a Stage object when printed.

        :rtype: str
        :return: The representation of the Stage object.
        """
        return f'<{self.steps} {self.name} {self.runner} {self.environment} {self.variables.keys()} {self.sequence}>'

    @property
    def name(self):
        """Getter method for the name attribute.

        :return: The Stage object name attribute.
        """
        return self._name

    @property
    def variables(self):
        """Getter method for the variables attribute.

        :return: The Stage object variables attribute.
        """
        return dict(self._variables)

    @property
    def steps(self):
        """Getter method for the steps attribute.

        :return: The Stage object steps attribute.
        """
        return self._steps

    @property
    def runner(self):
        """Getter method for the runner attribute.

        :return: The Stage object runner attribute.
        """
        return self._runner

    @property
    def environment(self):
        """Getter method for the environment attribute.

        :return: The Stage object environment attribute.
        """
        return self._environment

    @property
    def sequence(self):
        """Getter method for the sequence attribute.

        :return: The Stage object sequence attribute.
        """
        return self._sequence


class CI:
    """Base class for representing CI file adapter."""

    __slots__ = ('_config', '_output')

    class CIDumper(yaml.SafeDumper):
        """pyYAML formater object."""

        def increase_indent(self, flow=False, indentless=False):
            return super().increase_indent(flow, False)

    def __init__(self, config):
        """Instantiate a new CI object."""
        if not isinstance(config, dict):
            raise TypeError('Cannot read config.')
        self._config = config
        self._output = None

    def _prepare(self):
        """Converts a config to intermediary Stage and Step objects.

        :rtype: list[Stage]
        :return: A list of Stage objects that represent the provided config.
        """
        if 'build-magic' not in self._config.keys():
            raise KeyError('build-magic key not found in config.')
        stages_ = self._config['build-magic']
        stages = []
        for seq, stage_ in enumerate(stages_):
            if 'commands' not in stage_['stage'].keys():
                raise KeyError('commands not found in stage.')
            steps = []
            for i, command in enumerate(stage_['stage']['commands']):
                label = command.get('label', '')
                commands = set(command.keys())
                directives = set(Directive.values())
                try:
                    directive = (commands & directives).pop()
                except KeyError:
                    raise KeyError(
                        f'Key {(commands.symmetric_difference(directives) & commands).pop()} not found in command.'
                    )
                cmd = command.get(directive)
                steps.append(Step(cmd, label, i + 1))
            name = stage_['stage'].get('name', '')
            runner = stage_['stage'].get('runner', 'local')
            environment = stage_['stage'].get('environment', '')
            variables = stage_['stage'].get('environment variables', {}).items()
            stages.append(
                Stage(
                    steps,
                    name=name,
                    runner=runner,
                    environment=environment,
                    variables=variables,
                    sequence=(seq + 1),
                )
            )
        return stages

    @abstractmethod
    def _convert(self, stages):
        """Abstract method for converting a list of Stage objects to the concrete CI representation.

        :param list[Stage] stages: The Stage objects to convert.
        :rtype: dict
        :return: A dictionary representation of the concrete CI format.
        """
        raise NotImplementedError

    def _export(self):
        """Internal method for preparing and converting a config to a concrete CI representation.

        :return: None
        """
        stages = self._prepare()
        self._output = self._convert(stages)

    def to_yaml(self, filename=None):
        """Attempts to formats the concrete CI representation as YAML.

        :param str|None filename: Optional filename to write the YAML output to.
        :rtype: str
        :return: If filename is provided, writes the YAML output to a file, otherwise, returns the YAML output.
        """
        if not self._output:
            self._export()
        if filename:
            with open(filename, 'w') as path:
                out = yaml.dump(self._output, path, sort_keys=False, Dumper=self.CIDumper)
                return out
        return yaml.dump(self._output, sort_keys=False, Dumper=self.CIDumper)


class GitLab(CI):
    """Concrete representation of a GitLab CI pipeline."""

    def _convert(self, stages):
        """Converts a list of Stage objects to a GitLab CI representation.

        :param list[Stage] stages: The Stage objects to convert to GitLab.
        :rtype: dict
        :return: A dictionary representation of the resulting GitLab CI pipeline.
        """
        jobs = {}
        for stage in sorted(stages):
            job = {}
            name = stage.name if stage.name else f'build-magic {stage.sequence}/{len(stages)}'
            job['stage'] = name if stage.name else 'build-magic'
            if stage.variables:
                job['variables'] = {f'${key}': value for key, value in stage.variables.items()}
            job['scripts'] = [step.command for step in sorted(stage.steps)]
            jobs[name] = job
        return jobs


class GitHub(CI):
    """Concrete representation of a GitHub Actions workflow."""

    def _convert(self, stages):
        """Converts a list of Stage object to a GitHub Actions representation.

        :param list[Stage] stages: The Stage objects to convert to GitHub.
        :rtype: dict
        :return: A dictionary representation of the resulting GitHub Actions workflow.
        """
        jobs = {}
        for stage in sorted(stages):
            job = {}
            name = stage.name if stage.name else f'build-magic{stage.sequence}'
            if stage.variables:
                job['env'] = stage.variables
            steps = []
            for step in sorted(stage.steps):
                step_ = {}
                if step.label:
                    step_['name'] = step.label
                step_['run'] = step.command
                steps.append(step_)
            job['steps'] = steps
            jobs[name] = job
        return {'jobs': jobs}


def export(config, export_type):
    """Factory function for exporting a build-magic config as other CI YAML files.

    :param dict config:
    :param str export_type:
    :return:
    """
    args = {'config': config}
    if export_type == ExportType.GITHUB.value:
        ci = GitHub(**args)
    elif export_type == ExportType.GITLAB.value:
        ci = GitLab(**args)
    else:
        raise ValueError(f'Export type must be one of {ExportType.available()}')

    return ci.to_yaml()
