""""""

import pytest

from build_magic.macro import MacroFactory, Macro


@pytest.fixture
def cmd():
    """"""
    return 'ls'


@pytest.fixture
def prefix():
    """"""
    return 'cd /tmp;'


@pytest.fixture
def suffix():
    """"""
    return '-ltr'


def test_macro_create(cmd):
    """"""
    macro = Macro(cmd)
    assert macro.sequence == 0
    assert macro._command == cmd
    assert not macro.prefix
    assert not macro.suffix
    assert macro.as_string() == 'ls'
    assert macro.as_list() == ['ls']


def test_macro_create_with_prefix(cmd, prefix):
    """"""
    macro = Macro(cmd, prefix=prefix)
    assert macro.sequence == 0
    assert macro._command == 'ls'
    assert macro.prefix == 'cd /tmp;'
    assert not macro.suffix
    assert macro.as_string() == 'cd /tmp; ls'
    assert macro.as_list() == ['cd', '/tmp;', 'ls']


def test_macro_create_suffix(cmd, suffix):
    """"""
    macro = Macro(cmd, suffix=suffix)
    assert macro.sequence == 0
    assert macro._command == 'ls'
    assert not macro.prefix
    assert macro.suffix == '-ltr'
    assert macro.as_string() == 'ls -ltr'
    assert macro.as_list() == ['ls', '-ltr']


def test_macro_create_prefix_suffix(cmd, prefix, suffix):
    """"""
    macro = Macro(cmd, prefix=prefix, suffix=suffix)
    assert macro.sequence == 0
    assert macro._command == 'ls'
    assert macro.prefix == 'cd /tmp;'
    assert macro.suffix == '-ltr'
    assert macro.as_string() == 'cd /tmp; ls -ltr'
    assert macro.as_list() == ['cd', '/tmp;', 'ls', '-ltr']


def test_macro_add_prefix(cmd, prefix):
    """"""
    macro = Macro(cmd)
    assert macro.sequence == 0
    assert macro._command == cmd
    assert not macro.prefix
    assert not macro.suffix
    assert macro.as_string() == 'ls'
    assert macro.as_list() == ['ls']

    macro.prefix = prefix
    assert macro.prefix == 'cd /tmp;'
    assert macro.as_string() == 'cd /tmp; ls'
    assert macro.as_list() == ['cd', '/tmp;', 'ls']


def test_macro_add_suffix(cmd, suffix):
    """"""
    macro = Macro(cmd)
    assert macro.sequence == 0
    assert macro._command == cmd
    assert not macro.prefix
    assert not macro.suffix
    assert macro.as_string() == 'ls'
    assert macro.as_list() == ['ls']

    macro.suffix = suffix
    assert macro.suffix == '-ltr'
    assert macro.as_string() == 'ls -ltr'
    assert macro.as_list() == ['ls', '-ltr']


def test_macro_invalid_command():
    """"""
    with pytest.raises(TypeError, match=r'command must by str'):
        Macro(['ls'])


def test_macro_invalid_sequence(cmd):
    """"""
    with pytest.raises(ValueError):
        Macro(cmd, sequence='a')


def test_macro_invalid_prefix(cmd):
    """"""
    macro = Macro(cmd)
    macro.prefix = b'1x45k'
    with pytest.raises(TypeError):
        macro.as_string()
    with pytest.raises(AttributeError):
        macro.as_list()


def test_macro_factory_single_command(cmd):
    """"""
    commands = [cmd]
    factory = MacroFactory(commands)
    assert factory._commands == (('', 'ls', ''),)
    macros = factory.generate()
    assert len(macros) == 1
    assert macros[0].as_string() == 'ls'
    assert macros[0].sequence == 0


def test_macro_factory_single_command_with_suffix(cmd):
    """"""
    suffixes = ['dummy.docx dummy.xlsx']
    commands = [cmd]
    factory = MacroFactory(commands, suffixes=suffixes)
    assert factory._commands == (('', 'ls', 'dummy.docx dummy.xlsx'),)
    macros = factory.generate()
    assert len(macros) == 1
    assert macros[0].as_string() == 'ls dummy.docx dummy.xlsx'


def test_macro_factory_multiple_commands():
    """"""
    commands = ['cd /build_magic', 'make']
    suffixes = ['', 'artifact1 artifact2 artifact3']
    factory = MacroFactory(commands, suffixes=suffixes)
    assert factory._commands == (('', 'cd /build_magic', ''), ('', 'make', 'artifact1 artifact2 artifact3'))
    macros = factory.generate()
    assert len(macros) == 2
    assert macros[0].as_string() == 'cd /build_magic'
    assert macros[1].as_string() == 'make artifact1 artifact2 artifact3'
    assert [0, 1] == [m.sequence for m in macros]


def test_macro_factory_multiple_commands_2():
    """"""
    commands = ['mkdir', 'rm dir1', 'rm dir2', 'rm dir3']
    suffixes = ['dir1 dir2 dir3']
    factory = MacroFactory(commands, suffixes=suffixes)
    assert factory._commands == (
        ('', 'mkdir', 'dir1 dir2 dir3'),
        ('', 'rm dir1', ''),
        ('', 'rm dir2', ''),
        ('', 'rm dir3', ''),
    )
    macros = factory.generate()
    assert len(macros) == 4
    assert macros[0].as_string() == 'mkdir dir1 dir2 dir3'
    assert macros[1].as_string() == 'rm dir1'
    assert macros[2].as_string() == 'rm dir2'
    assert macros[3].as_string() == 'rm dir3'
    assert [0, 1, 2, 3] == [m.sequence for m in macros]
