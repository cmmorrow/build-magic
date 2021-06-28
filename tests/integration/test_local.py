"""Integration tests for the Local CommandRunner."""

import re
import subprocess

import pytest

from build_magic.reference import ExitCode
from . import unix


@pytest.mark.local
def test_single_command(cli):
    """Verify passing a single command as arguments works correctly."""
    res = subprocess.run(
        'python -m build_magic --verbose --plain echo hello world',
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=True,
    )
    output = res.stdout.decode('utf-8')
    assert res.returncode == ExitCode.PASSED
    assert '[ INFO  ] Starting Stage 1' in output
    assert '[ DONE  ] ( 1/1 ) EXECUTE  : echo hello world' in output
    assert '[ INFO  ] OUTPUT: hello world' in output
    assert '[ INFO  ] Stage 1 complete with result DONE' in output


@pytest.mark.local
def test_named_stage(cli):
    """Verify passing a name for the stage works correctly."""
    res = subprocess.run(
        'python -m build_magic --verbose --plain --name Test echo hello world',
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=True,
    )
    output = res.stdout.decode('utf-8')
    assert res.returncode == ExitCode.PASSED
    assert '[ INFO  ] Starting Stage 1' in output
    assert '[ DONE  ] ( 1/1 ) EXECUTE  : echo hello world' in output
    assert '[ INFO  ] OUTPUT: hello world' in output
    assert '[ INFO  ] Stage 1: Test - complete with result DONE' in output


@unix
@pytest.mark.local
def test_multiple_commands(cli):
    """Verify passing multiple commands with the -c and --command options works correctly."""
    res = subprocess.run(
        'python -m build_magic --verbose --plain -c execute "echo hello world" -c execute "ls"',
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=True,
    )
    output = res.stdout.decode('utf-8')
    assert res.returncode == ExitCode.PASSED
    assert '[ INFO  ] Starting Stage 1' in output
    assert '[ DONE  ] ( 1/2 ) EXECUTE  : echo hello world' in output
    assert '[ INFO  ] OUTPUT: hello world' in output
    assert '[ DONE  ] ( 2/2 ) EXECUTE  : ls' in output
    assert '[ INFO  ] Stage 1 complete with result DONE' in output

    res = subprocess.run(
        'python -m build_magic --verbose --plain --command execute "echo hello world" --command execute "ls"',
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=True,
    )
    output = res.stdout.decode('utf-8')
    assert res.returncode == ExitCode.PASSED
    assert '[ INFO  ] Starting Stage 1' in output
    assert '[ DONE  ] ( 1/2 ) EXECUTE  : echo hello world' in output
    assert '[ INFO  ] OUTPUT: hello world' in output
    assert '[ DONE  ] ( 2/2 ) EXECUTE  : ls' in output
    assert '[ INFO  ] Stage 1 complete with result DONE' in output


@unix
@pytest.mark.local
def test_redirection(cli, tmp_path):
    """Verify redirecting stdout within a command works correctly."""
    res = subprocess.run(
        f'python -m build_magic --verbose --plain --wd {tmp_path} '
        '-c execute \'echo "hello world" > hello.txt\' -c execute "cat hello.txt"',
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=True,
    )
    output = res.stdout.decode('utf-8')
    assert res.returncode == ExitCode.PASSED
    assert '[ INFO  ] Starting Stage 1' in output
    assert '[ DONE  ] ( 1/2 ) EXECUTE  : echo "hello world" > hello.txt' in output
    assert '[ DONE  ] ( 2/2 ) EXECUTE  : cat hello.txt' in output
    assert '[ INFO  ] OUTPUT: hello world' in output
    assert '[ INFO  ] Stage 1 complete with result DONE' in output


@unix
@pytest.mark.local
def test_pipe(cli):
    """Verify piping stdin within a command works correctly."""
    res = subprocess.run(
        "python -m build_magic --verbose --plain 'ps -ef | grep python'",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=True,
    )
    output = res.stdout.decode('utf-8')
    assert res.returncode == ExitCode.PASSED
    assert '[ INFO  ] Starting Stage 1' in output
    assert '[ DONE  ] ( 1/1 ) EXECUTE  : ps -ef | grep python' in output
    assert '/bin/sh -c ps -ef | grep python' in output
    assert '[ INFO  ] Stage 1 complete with result DONE' in output


@unix
@pytest.mark.local
def test_env(cli):
    """Verify using an environment variable within a command works correctly."""
    res = subprocess.run(
        "python -m build_magic --verbose --plain 'echo $SHELL'",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=True,
    )
    output = res.stdout.decode('utf-8')
    assert res.returncode == ExitCode.PASSED
    assert '[ INFO  ] Starting Stage 1' in output
    assert '[ DONE  ] ( 1/1 ) EXECUTE  : echo $SHELL' in output
    assert re.search(r'\[ INFO\s\s] OUTPUT: /bin/(?:b?[a-z]?sh|fish)', output)
    assert '[ INFO  ] Stage 1 complete with result DONE' in output


@unix
@pytest.mark.local
def test_wd(cli):
    """Verify setting the working directory works correctly."""
    res = subprocess.run(
        "python -m build_magic --verbose --plain --wd /usr/bin pwd",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=True,
    )
    output = res.stdout.decode('utf-8')
    assert res.returncode == ExitCode.PASSED
    assert '[ INFO  ] Starting Stage 1' in output
    assert '[ DONE  ] ( 1/1 ) EXECUTE  : pwd' in output
    assert '[ INFO  ] OUTPUT: /usr/bin' in output
    assert '[ INFO  ] Stage 1 complete with result DONE' in output


@pytest.mark.local
def test_cleanup(cli, tmp_path):
    """Verify the cleanup action works correctly."""
    file1 = tmp_path / 'file1.txt'
    file2 = tmp_path / 'file2.txt'
    file1.touch()
    file2.touch()
    res = subprocess.run(
        f"python -m build_magic --verbose --plain --wd {tmp_path} --action cleanup "
        f"-c execute 'mkdir new' -c execute 'touch new/file3.txt'",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=True,
    )
    output = res.stdout.decode('utf-8')
    assert res.returncode == ExitCode.PASSED
    assert '[ INFO  ] Starting Stage 1' in output
    assert '[ DONE  ] ( 1/2 ) EXECUTE  : mkdir new' in output
    assert '[ DONE  ] ( 2/2 ) EXECUTE  : touch new/file3.txt' in output
    assert '[ INFO  ] Stage 1 complete with result DONE' in output
    assert file1.exists()
    assert file2.exists()
    assert not tmp_path.joinpath('new').exists()
