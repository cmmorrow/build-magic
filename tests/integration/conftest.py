from click.testing import CliRunner
import pytest


@pytest.fixture
def cli():
    """Provides a CliRunner object for invoking cli calls."""
    return CliRunner()
