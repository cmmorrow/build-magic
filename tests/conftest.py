import os
from pathlib import Path
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


@pytest.fixture
def magic_dir(tmp_path_factory):
    """Provides a temporary directory for testing copy/working directory behavior."""
    magic = tmp_path_factory.mktemp('build_magic')
    return magic


@pytest.fixture
def tmp_file(magic_dir):
    """Provides a test file in the temp directory."""
    hello = magic_dir / 'hello.txt'
    hello.write_text('hello world')
    yield magic_dir
    os.remove('hello.txt')


@pytest.fixture
def config_file(magic_dir):
    """Provides a config file in the temp directory."""
    if platform.system() == 'Windows':
        filename = 'config_win.yaml'
    else:
        filename = 'config.yaml'
    config = magic_dir / filename
    content = Path(__file__).parent.joinpath('files').joinpath(filename).read_text()
    config.write_text(content)
    yield config
    os.remove(magic_dir / filename)


@pytest.fixture
def multi_config(magic_dir):
    """Provides a config file with multiple stage in the temp directory."""
    if platform.system() == 'Windows':
        filename = 'multi_win.yaml'
    else:
        filename = 'multi.yaml'
    config = magic_dir / filename
    content = Path(__file__).parent.joinpath('files').joinpath(filename).read_text()
    config.write_text(content)
    yield config
    os.remove(magic_dir / filename)


@pytest.fixture
def env_config(magic_dir):
    """Provides a config file with environment variables."""
    if platform.system() == 'Windows':
        config_filename = 'envs_win.yaml'
    else:
        config_filename = 'envs.yaml'
    config = magic_dir / config_filename
    content = Path(__file__).parent.joinpath('files').joinpath(config_filename).read_text()
    config.write_text(content)
    yield config
    os.remove(magic_dir / config)


@pytest.fixture
def multi_no_name_config(magic_dir):
    """Provides a config file with multiple stages with no names."""
    filename = 'multi_no_name.yaml'
    config = magic_dir / filename
    content = Path(__file__).parent.joinpath('files').joinpath(filename).read_text()
    config.write_text(content)
    yield config
    os.remove(magic_dir / config)


@pytest.fixture
def labels_config(magic_dir):
    """Provides a config file with command labels in the temp directory."""
    filename = 'labels.yaml'
    config = magic_dir / filename
    content = Path(__file__).parent.joinpath('files').joinpath(filename).read_text()
    config.write_text(content)
    yield config
    os.remove(magic_dir / filename)
