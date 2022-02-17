import platform

import pytest


@pytest.fixture
def ls():
    """Provides the correct list command for the executing operating system."""
    if platform.system() == 'Windows':
        return 'dir'
    else:
        return 'ls'


@pytest.fixture
def cat():
    """Provides the correct cat command for the executing operating system."""
    if platform.system() == 'Windows':
        return 'type'
    else:
        return 'cat'


@pytest.fixture
def cp():
    """Provides the correct file copy command for the executing operating system."""
    if platform.system() == 'Windows':
        return 'copy'
    else:
        return 'cp'


@pytest.fixture
def mv():
    """Provides the correct file move command for the executing operating system."""
    if platform.system() == 'Windows':
        return 'move'
    else:
        return 'mv'


@pytest.fixture
def touch():
    """Provides the correct touch command for the executing operating system."""
    if platform.system() == 'Windows':
        return 'type nul >>'
    else:
        return 'touch'


@pytest.fixture
def env():
    """Provides the correct env command for the executing operating system."""
    if platform.system() == 'Windows':
        return 'set'
    else:
        return 'env'
