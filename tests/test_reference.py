"""This module hosts unit tests for the reference module."""

import math

import pytest

from build_magic.exc import ValidationError
from build_magic.reference import EnumExt, Parameter


def test_parameter():
    """Verify the Parameter class works correctly."""
    class Test(Parameter):
        KEY = 'test'
        DEFAULT = 3.
        OTHER = 'bogus'
    param = Test(math.pi)
    assert param.KEY == 'test'
    assert param.key == 'test'
    assert param.value == math.pi
    assert str(param) == '<Test: test, 3.141592653589793>'
    assert param.as_dict() == {'test': math.pi}
    assert param.as_tuple() == ('test', math.pi)
    assert not param.alias
    assert not param.ALIAS
    assert not param.ENUM
    assert not param.enum
    assert not param.pattern
    assert not param.PATTERN
    assert param.default == 3.
    assert param.DEFAULT == 3.

    # Make sure that changing KEY doesn't affect the internal key of a Parameter object.
    with pytest.raises(AttributeError):
        param.KEY = 'other'


def test_parameter_alias():
    """Verify the Parameter class with an alias works correctly."""
    class Test(Parameter):
        KEY = 'test'
        ALIAS = 'pi'
    param = Test(math.pi)
    assert param.KEY == 'test'
    assert param.key == 'test'
    assert param.value == math.pi
    assert str(param) == '<Test: test, pi, 3.141592653589793>'
    assert param.as_dict() == {'test': math.pi}
    assert param.as_tuple() == ('test', math.pi)
    assert param.alias == 'pi'
    assert param.ALIAS == 'pi'
    assert not param.default
    assert not param.DEFAULT
    assert not param.ENUM
    assert not param.enum
    assert not param.pattern
    assert not param.PATTERN

    with pytest.raises(AttributeError):
        param.ALIAS = 'other'


def test_parameter_default():
    """Verify the Parameter class with a default works correctly."""
    class Test(Parameter):
        KEY = 'test'
        DEFAULT = 3.
    param = Test()
    assert param.KEY == 'test'
    assert param.key == 'test'
    assert param.value == 3.
    assert str(param) == '<Test: test, 3.0>'
    assert param.as_dict() == {'test': 3.}
    assert param.as_tuple() == ('test', 3.)
    assert not param.ALIAS
    assert not param.alias
    assert not param.ENUM
    assert not param.enum
    assert not param.pattern
    assert not param.PATTERN
    assert param.default == 3.
    assert param.DEFAULT == 3.

    with pytest.raises(AttributeError):
        param.DEFAULT = 'other'


def test_parameter_enum_value():
    """Verify the Parameter class with an enum value works correctly."""
    class TestEnum(EnumExt):
        ONE = 1
        TWO = 2
        THREE = 3
        FOUR = 4

    class Test(Parameter):
        KEY = 'test'
        ENUM = TestEnum

    param = Test(3)
    assert param.key == 'test'
    assert param.KEY == 'test'
    assert param.ENUM == TestEnum
    assert param.enum == TestEnum
    assert param.value == 3
    assert param.as_dict() == {'test': 3}
    assert param.as_tuple() == ('test', 3)
    assert not param.ALIAS
    assert not param.alias
    assert not param.pattern
    assert not param.PATTERN


def test_parameter_enum_key():
    """Verify the Parameter class with an enum key works correctly."""
    class TestEnum(EnumExt):
        ONE = 1
        TWO = 2
        THREE = 3
        FOUR = 4

    class Test(Parameter):
        KEY = 'test'
        ENUM = TestEnum

    param = Test('THREE')
    assert param.key == 'test'
    assert param.KEY == 'test'
    assert param.ENUM == TestEnum
    assert param.enum == TestEnum
    assert param.value == 3
    assert param.as_dict() == {'test': 3}
    assert param.as_tuple() == ('test', 3)
    assert not param.ALIAS
    assert not param.alias
    assert not param.pattern
    assert not param.PATTERN


def test_parameter_enum_validation_fail():
    """Test the case where the Parameter enum validation fails."""
    class TestEnum(EnumExt):
        ONE = 1
        TWO = 2
        THREE = 3
        FOUR = 4

    class Test(Parameter):
        KEY = 'test'
        ENUM = TestEnum

    with pytest.raises(ValidationError, match='Validation failed: Value 7 is not one of'):
        Test(7)


def test_parameter_enum_invalid_type():
    """Test the case where the enum attribute is not an Enum."""
    class Test(Parameter):
        ENUM = 'dummy'

    with pytest.raises(TypeError):
        Test(3)


def test_parameter_pattern():
    """Verify the Parameter class with a pattern works correctly."""
    class Test(Parameter):
        KEY = 'Test'
        PATTERN = r'solid|liquid|gas'

    param = Test('liquid')
    assert param.value == 'liquid'
    assert not param.default
    assert not param.DEFAULT
    assert not param.ENUM
    assert not param.enum
    assert not param.alias
    assert not param.ALIAS
    assert param.pattern == r'solid|liquid|gas'
    assert param.PATTERN == r'solid|liquid|gas'


def test_parameter_pattern_fail():
    """Test the case where value doesn't match PATTERN."""
    class Test(Parameter):
        KEY = 'Test'
        PATTERN = r'solid|liquid|gas'

    with pytest.raises(ValidationError, match='Validation failed: Value plasma does not match solid|liquid|gas.'):
        Test('plasma')


def test_parameter_pattern_invalid_type():
    """Test the case where PATTERN isn't a string."""
    class Test(Parameter):
        KEY = 'Test'
        PATTERN = 42

    with pytest.raises(TypeError):
        Test('plasma')


def test_enum_ext():
    """Verify the EnumExt class works correctly."""
    class Test(EnumExt):
        ONE = 1
        TWO = 2
        THREE = 3
        FOUR = 4

    assert Test.names() == ('ONE', 'TWO', 'THREE', 'FOUR')
    assert Test.values() == (1, 2, 3, 4)
    assert Test.available() == (1, 2, 3, 4)
    assert Test['THREE'] == Test.THREE
    assert Test.THREE.name == 'THREE'
    assert Test.THREE.value == 3
