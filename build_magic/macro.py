"""Module for defining Macro classes."""

import shlex


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
        i = 0
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
        """Provides the command to execute.

        :rtype: str
        :return: The Macro command.
        """
        return self._command

    def as_list(self):
        """Breaks up a command into a list.

        :rtype: list[str]
        :return: The command as a list.
        """
        def prep(cmd):
            if cmd:
                cmd = shlex.split(cmd)
            else:
                cmd = []
            return cmd

        command = prep(self.prefix) + prep(self._command) + prep(self.suffix)
        return command

    def as_string(self):
        """Provides a command as a string.

        :rtype: str
        :return: The command as a string.
        """
        cmd = self._command
        if self.prefix:
            cmd = self.prefix + ' ' + cmd
        if self.suffix:
            cmd += ' ' + self.suffix
        return cmd
