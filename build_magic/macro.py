"""Module for defining Macro classes."""

import re
import shlex

from build_magic.reference import PromptSequence


class MacroFactory:
    """Generates Macro objects based on the provided commands.

    :param list[str] commands: The commands to use for building Macros.
    :param list[str] prefixes: The command prefixes to use for building Macros.
    :param list[str] suffixes: The command suffixes to use for building Macros.
    """

    __slots__ = ['_commands']

    def __init__(self, commands, prefixes=None, suffixes=None):
        """Instantiates a new MacroFactory object."""
        if not prefixes:
            prefixes = []
        if not suffixes:
            suffixes = []
        if commands is None:
            self._commands = []
        else:
            while len(prefixes) < len(commands):
                prefixes.append('')
            while len(suffixes) < len(commands):
                suffixes.append('')
            self._commands = tuple(zip(prefixes, commands, suffixes))

    def generate(self):
        """Generates Macro objects based on the commands supplied to the MacroFactory.

        :rtype: list[Macro]
        :return: A list of generated Macro objects.
        """
        macros = []
        i = 1
        for prefix, cmd, suffix, in self._commands:
            if not cmd:
                continue
            macros.append(
                Macro(cmd, sequence=i, prefix=prefix, suffix=suffix)
            )
            i += 1
        return macros


class Macro:
    """A command to be executed by a CommandRunner.

    Macros are the primary object for doing work in build-magic. A Macro is composed of a command
    to be executed at the command-line by a CommandRunner.

    :param str command: The base command to be executed as supplied by the user.
    :param int sequence: The run order of the command.
    :param str prefix: A command or portion of a command to append to the beginning of the base command.
    :param str suffix: A command or portion of a command to append to the end of the base command.
    """

    __slots__ = ['_command', 'prefix', 'sequence', 'suffix']

    def __init__(self, command='', sequence=0, prefix='', suffix=''):
        """Instantiates a new Macro object."""
        if not isinstance(command, str):
            raise TypeError('command must by str not {}'.format(type(command)))
        self._command = command
        self.sequence = int(sequence)
        self.prefix = str(prefix)
        self.suffix = str(suffix)

    @property
    def command(self):
        """Provides the command to execute for display purposes.

        Any command that contains a prompt sequence will be converted to hidden characters to mask the prompted string.

        :rtype: str
        :return: The Macro command.
        """
        if PromptSequence.START in self._command:
            return self._hide_prompted_command()
        else:
            return self._command

    def _hide_prompted_command(self):
        """Find the prompt start and end tags and replace the whole sequence with the hidden sequence.

        :return: The command with prompted sequences hidden.
        """
        cmd = self._command
        # Find prompt sequences and replace them with the hidden character sequence.
        pattern = re.compile(str(re.escape(PromptSequence.START)) + r'.*?' + str(re.escape(PromptSequence.END)))
        prompted = re.findall(pattern, cmd)
        for seq in prompted:
            cmd = cmd.replace(seq, PromptSequence.HIDDEN)
        return cmd

    def _strip_prompt_from_command(self):
        """Remove the prompt start and end tags from the command.

        :return: The command without the prompt tags.
        """
        cmd = self._command
        if PromptSequence.START in cmd:
            cmd = cmd.replace(PromptSequence.START, '').replace(PromptSequence.END, '')
        return cmd

    def as_list(self):
        """Breaks up a command into a list.

        :rtype: list[str]
        :return: The command as a list.
        """
        def prep(cmd):
            return shlex.split(cmd) if cmd else []

        command = self._strip_prompt_from_command()
        command = prep(self.prefix) + prep(command) + prep(self.suffix)
        return command

    def as_string(self):
        """Provides a command as a string.

        :rtype: str
        :return: The command as a string.
        """
        cmd = self._strip_prompt_from_command()
        if self.prefix:
            cmd = self.prefix + ' ' + cmd
        if self.suffix:
            cmd += ' ' + self.suffix
        return cmd
