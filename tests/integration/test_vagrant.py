"""Integration tests for the Vagrant CommandRunner."""

from pathlib import Path
import shutil
import subprocess

import pytest

from build_magic.reference import ExitCode


@pytest.mark.vagrant
def test_wd(cli):
    """Verify setting the working directory works correctly."""
    path = Path(__file__).parent
    res = subprocess.run(
        "python -m build_magic --verbose --plain "
        "--runner vagrant "
        f"--environment {path.parent}/files/Vagrantfile "
        "--wd /app "
        "-c execute 'pwd'",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=True,
    )
    output = res.stdout.decode('utf-8')
    assert res.returncode == ExitCode.PASSED
    assert '[ INFO  ] Starting Stage 1' in output
    assert '[ DONE  ] ( 1/1 ) EXECUTE  : pwd' in output
    assert '[ INFO  ] OUTPUT: /app' in output
    assert '[ INFO  ] Stage 1 complete with result DONE' in output


@pytest.mark.vagrant
def test_isolation(cli, tmp_path_factory):
    """Verify copying files to a working directory in the vm works correctly."""
    source = tmp_path_factory.mktemp('source')
    target = tmp_path_factory.mktemp('target')
    main = source / 'main.cpp'
    plugins = source / 'plugins.cpp'
    audio = source / 'audio.cpp'
    main.touch()
    plugins.touch()
    audio.touch()
    vagrantfile = Path(__file__).parent.parent / 'files' / 'Vagrantfile'
    shutil.copy2(vagrantfile, target)
    res = subprocess.run(
        "python -m build_magic --verbose --plain "
        "--runner vagrant "
        f"--environment {target.resolve()}/Vagrantfile "
        f"--copy {source} "
        "--wd /app "
        "-c execute 'pwd' "
        "-c execute 'ls /app' "
        "-c execute 'cat Vagrantfile' "
        "audio.cpp main.cpp plugins.cpp",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=True,
    )
    output = res.stdout.decode('utf-8')
    assert res.returncode == ExitCode.PASSED
    assert '[ INFO  ] Starting Stage 1' in output
    assert '[ DONE  ] ( 1/3 ) EXECUTE  : pwd' in output
    assert '[ INFO  ] OUTPUT: /app' in output
    assert '[ INFO  ] OUTPUT: audio.cpp' in output
    assert 'main.cpp' in output
    assert 'plugins.cpp' in output
    assert '[ INFO  ] Stage 1 complete with result DONE' in output


@pytest.mark.skip
def test_cleanup(cli, tmp_path):
    """Verify cleanup is working correctly."""
    # TODO: As of 0.1, cleanup isn't implemented for the Vagrant runner.
    path = Path(__file__).parent
    res = subprocess.run(
        "python -m build_magic --verbose --plain "
        "--runner vagrant "
        f"--environment {path.parent}/files/Vagrantfile "
        "--action cleanup "
        "--wd /vagrant "
        "-c execute 'touch file1.txt file2.txt' "
        "-c execute 'ls'",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=True,
    )
    output = res.stdout.decode('utf-8')
    print(output)
    assert False
