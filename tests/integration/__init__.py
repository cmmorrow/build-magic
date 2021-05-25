import platform

import pytest

# Specify platform based skip conditions.
mac_os = pytest.mark.skipif(
    platform.system() != 'Darwin',
    reason='Test requires MacOS.',
)

linux = pytest.mark.skipif(
    platform.system() != 'Linux',
    reason='Test requires Linux.',
)

unix = pytest.mark.skipif(
    platform.system() not in ('Darwin', 'Linux'),
    reason='Test requires *nix OS.',
)

windows = pytest.mark.skipif(
    platform.system() != 'Windows',
    reason='Test requires Windows.',
)