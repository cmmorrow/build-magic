"""This module hosts unit tests for the build-magic exceptions."""

import pytest

from build_magic.exc import BuildMagicException, ExecutionError, NoJobs, SetupError, TeardownError


def test_base_exception():
    """Verify the BuildMagicException works correctly."""
    with pytest.raises(BuildMagicException, match='build-magic error'):
        raise BuildMagicException

    with pytest.raises(BuildMagicException, match='build-magic error: test error'):
        raise BuildMagicException(message='test error')

    with pytest.raises(BuildMagicException, match='build-magic error: An error'):
        error = TypeError('An error')
        raise BuildMagicException(exception=error)

    with pytest.raises(BuildMagicException, match='build-magic error: An error'):
        error = TypeError('An error')
        raise BuildMagicException(message='test error', exception=error)


def test_execution_error():
    """Verify the ExecutionError works correctly."""
    with pytest.raises(ExecutionError, match='Command execution error'):
        raise ExecutionError

    with pytest.raises(ExecutionError, match='Command execution error: test error'):
        raise ExecutionError(message='test error')

    with pytest.raises(ExecutionError, match='Command execution error: An error'):
        error = TypeError('An error')
        raise ExecutionError(exception=error)

    with pytest.raises(ExecutionError, match='Command execution error: An error'):
        error = TypeError('An error')
        raise ExecutionError(message='test error', exception=error)


def test_setup_error():
    """Verify the SetupError works correctly."""
    with pytest.raises(SetupError, match='Setup failed'):
        raise SetupError

    with pytest.raises(SetupError, match='Setup failed: test error'):
        raise SetupError(message='test error')

    with pytest.raises(SetupError, match='Setup failed: An error'):
        error = TypeError('An error')
        raise SetupError(exception=error)

    with pytest.raises(SetupError, match='Setup failed: An error'):
        error = TypeError('An error')
        raise SetupError(message='test error', exception=error)


def test_teardown_error():
    """Verify the TeardownError works correctly."""
    with pytest.raises(TeardownError, match='Teardown failed'):
        raise TeardownError

    with pytest.raises(TeardownError, match='Teardown failed: test error'):
        raise TeardownError(message='test error')

    with pytest.raises(TeardownError, match='Teardown failed: An error'):
        error = TypeError('An error')
        raise TeardownError(exception=error)

    with pytest.raises(TeardownError, match='Teardown failed: An error'):
        error = TypeError('An error')
        raise TeardownError(message='test error', exception=error)


def test_no_jobs_error():
    """Verify the NoJobs error works correctly."""
    with pytest.raises(NoJobs, match='No jobs to execute'):
        raise NoJobs

    with pytest.raises(NoJobs, match='No jobs to execute: test error'):
        raise NoJobs(message='test error')

    with pytest.raises(NoJobs, match='No jobs to execute: An error'):
        error = TypeError('An error')
        raise NoJobs(exception=error)

    with pytest.raises(NoJobs, match='No jobs to execute: An error'):
        error = TypeError('An error')
        raise NoJobs(message='test error', exception=error)
