"""Integration tests for the Remote CommandRunner."""

import getpass
from pathlib import Path
import re
import subprocess

import pytest

from build_magic.reference import ExitCode
from . import unix


@pytest.mark.remote
def test_single_command(cli):
    """Verify passing a single command as arguments works correctly."""
    res = subprocess.run(
        'python -m build_magic --verbose --plain '
        '--runner remote '
        f'--environment {getpass.getuser()}@localhost '
        'echo hello world',
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=True,
    )
    output = res.stdout.decode('utf-8')
    assert res.returncode == ExitCode.PASSED
    assert '[ INFO  ] Starting Stage 1' in output
    assert '[ DONE  ] EXECUTE  : echo hello world' in output
    assert '[ INFO  ] OUTPUT   : hello world' in output
    assert '[ INFO  ] Stage 1 complete with result DONE' in output


@unix
@pytest.mark.remote
def test_multiple_commands(cli):
    """Verify passing multiple commands with the -c and --command options works correctly."""
    res = subprocess.run(
        'python -m build_magic --verbose --plain '
        '--runner remote '
        f'--environment {getpass.getuser()}@localhost:22 '
        '-c execute "echo hello world" '
        '-c execute "ls"',
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=True,
    )
    output = res.stdout.decode('utf-8')
    assert res.returncode == ExitCode.PASSED
    assert '[ INFO  ] Starting Stage 1' in output
    assert '[ DONE  ] EXECUTE  : echo hello world' in output
    assert '[ INFO  ] OUTPUT   : hello world' in output
    assert '[ DONE  ] EXECUTE  : ls' in output
    assert '[ INFO  ] Stage 1 complete with result DONE' in output


@unix
@pytest.mark.remote
def test_redirection(cli):
    """Verify redirecting stdout within a command works correctly."""
    res = subprocess.run(
        'python -m build_magic --verbose --plain '
        '--runner remote '
        f'--environment {getpass.getuser()}@localhost '
        '-c execute \'echo "hello world" > hello.txt\' '
        '-c execute "cat hello.txt" '
        '-c execute "rm hello.txt"',
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=True,
    )
    output = res.stdout.decode('utf-8')
    assert res.returncode == ExitCode.PASSED
    assert '[ INFO  ] Starting Stage 1' in output
    assert '[ DONE  ] EXECUTE  : echo "hello world" > hello.txt' in output
    assert '[ DONE  ] EXECUTE  : cat hello.txt' in output
    assert '[ INFO  ] OUTPUT   : hello world' in output
    assert '[ INFO  ] Stage 1 complete with result DONE' in output


@unix
@pytest.mark.remote
def test_pipe(cli):
    """Verify piping stdin within a command works correctly."""
    res = subprocess.run(
        "python -m build_magic --verbose --plain "
        "--runner remote "
        f"--environment {getpass.getuser()}@localhost "
        "'ps -ef | grep python'",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=True,
    )
    output = res.stdout.decode('utf-8')
    assert res.returncode == ExitCode.PASSED
    assert '[ INFO  ] Starting Stage 1' in output
    assert '[ DONE  ] EXECUTE  : ps -ef | grep python' in output
    assert re.search(r'(?:b?[azck]?sh|fish) -c ps -ef \| grep python', output)
    assert '[ INFO  ] Stage 1 complete with result DONE' in output


@unix
@pytest.mark.remote
def test_env(cli):
    """Verify using an environment variable within a command works correctly."""
    res = subprocess.run(
        "python -m build_magic --verbose --plain "
        "--runner remote "
        f"--environment {getpass.getuser()}@localhost "
        "'echo $SHELL'",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=True,
    )
    output = res.stdout.decode('utf-8')
    assert res.returncode == ExitCode.PASSED
    assert '[ INFO  ] Starting Stage 1' in output
    assert '[ DONE  ] EXECUTE  : echo $SHELL' in output
    assert re.search(r'\[ INFO\s\s] OUTPUT\s\s\s: /bin/(?:b?[a-z]?sh|fish)', output)
    assert '[ INFO  ] Stage 1 complete with result DONE' in output


@unix
@pytest.mark.remote
def test_wd(cli):
    """Verify setting the working directory works correctly."""
    res = subprocess.run(
        "python -m build_magic --verbose --plain "
        "--runner remote "
        f"--environment {getpass.getuser()}@localhost "
        "--wd /usr/bin pwd",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=True,
    )
    output = res.stdout.decode('utf-8')
    assert res.returncode == ExitCode.PASSED
    assert '[ INFO  ] Starting Stage 1' in output
    assert '[ DONE  ] EXECUTE  : pwd' in output
    assert '[ INFO  ] OUTPUT   : /usr/bin' in output
    assert '[ INFO  ] Stage 1 complete with result DONE' in output


@pytest.mark.remote
def test_copy_files(cli, tmp_path):
    """Verify copying files to the working directory works correctly."""
    main = tmp_path / 'main.cpp'
    plugins = tmp_path / 'plugins.cpp'
    audio = tmp_path / 'audio.cpp'
    main.touch()
    plugins.touch()
    audio.touch()
    res = subprocess.run(
        "python -m build_magic --verbose --plain "
        "--runner remote "
        f"--environment {getpass.getuser()}@localhost "
        f"--copy {tmp_path} "
        "-c execute 'ls' "
        "main.cpp plugins.cpp audio.cpp",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=True,
    )
    output = res.stdout.decode('utf-8')
    assert res.returncode == ExitCode.PASSED
    assert '[ INFO  ] Starting Stage 1' in output
    assert '[ DONE  ] EXECUTE  : ls' in output
    assert 'audio.cpp' in output
    assert 'main.cpp' in output
    assert 'plugins.cpp' in output
    assert '[ INFO  ] Stage 1 complete with result DONE' in output

    Path.home().joinpath('main.cpp').unlink()
    Path.home().joinpath('audio.cpp').unlink()
    Path.home().joinpath('plugins.cpp').unlink()


@unix
@pytest.mark.remote
def test_cleanup_all(cli, tmp_path_factory):
    """Verify the cleanup action works correctly when deleting all files."""
    target = tmp_path_factory.mktemp('target')
    source = tmp_path_factory.mktemp('source')
    file1 = source / 'file1.txt'
    file2 = source / 'file2.txt'
    file1.touch()
    file2.touch()

    res = subprocess.run(
        "python -m build_magic --verbose --plain "
        "--runner remote "
        f"--environment {getpass.getuser()}@localhost "
        "--action cleanup "
        f"--copy {source} "
        f"--wd {target} "
        "-c execute 'touch file3.txt' "
        "-c execute 'ls' "
        "file1.txt file2.txt",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=True,
    )
    output = res.stdout.decode('utf-8')
    assert res.returncode == ExitCode.PASSED
    assert '[ INFO  ] Starting Stage 1' in output
    assert '[ DONE  ] EXECUTE  : touch file3.txt' in output
    assert '[ DONE  ] EXECUTE  : ls' in output
    assert '[ INFO  ] OUTPUT   : file1.txt' in output
    assert re.search(r'\nfile2\.txt\n', output)
    assert re.search(r'\nfile3\.txt\n', output)
    assert '[ INFO  ] Stage 1 complete with result DONE' in output
    assert target.joinpath('file1.txt').exists() is False
    assert target.joinpath('file2.txt').exists() is False
    assert target.joinpath('file3.txt').exists() is False


@unix
@pytest.mark.remote
def test_cleanup_select(cli, tmp_path):
    """Verify the cleanup actions works correctly when deleting select files."""
    file1 = tmp_path / 'file1.txt'
    file2 = tmp_path / 'file2.txt'
    file1.touch()
    file2.touch()

    res = subprocess.run(
        "python -m build_magic --verbose --plain "
        "--runner remote "
        f"--environment {getpass.getuser()}@localhost "
        "--action cleanup "
        f"--wd {tmp_path} "
        "-c execute 'touch file3.txt' "
        "-c execute 'ls' ",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=True,
    )
    output = res.stdout.decode('utf-8')
    assert res.returncode == ExitCode.PASSED
    assert '[ INFO  ] Starting Stage 1' in output
    assert '[ DONE  ] EXECUTE  : touch file3.txt' in output
    assert '[ DONE  ] EXECUTE  : ls' in output
    assert '[ INFO  ] OUTPUT   : file1.txt' in output
    assert re.search(r'\nfile2\.txt\n', output)
    assert re.search(r'\nfile3\.txt\n', output)
    assert '[ INFO  ] Stage 1 complete with result DONE' in output
    assert file1.exists() is True
    assert file1.exists() is True
    assert tmp_path.joinpath('file3.txt').exists() is False


@unix
@pytest.mark.remote
def test_cleanup_directories(cli, tmp_path):
    """Verify the cleanup action works correctly when deleting directories."""
    dir1 = tmp_path / 'dir1'
    dir2 = tmp_path / 'dir2'
    dir1.mkdir()
    dir2.mkdir()
    dir3 = dir1 / 'dir3'
    dir4 = dir1 / 'dir4'
    dir5 = dir2 / 'dir5'
    dir6 = dir4 / 'dir6'
    file1 = dir1 / 'file1'
    file2 = dir1 / 'file2'
    file3 = dir2 / 'file3'
    file4 = dir3 / 'file4'
    file5 = dir3 / 'file5'
    file6 = dir3 / 'file6'
    file7 = dir5 / 'file7'
    file8 = dir6 / 'file8'
    file9 = dir6 / 'file9'

    res = subprocess.run(
        "python -m build_magic --plain "
        "--runner remote "
        f"--environment {getpass.getuser()}@localhost "
        "--action cleanup "
        f"--wd {tmp_path} "
        "-c execute 'mkdir dir1/dir3 dir1/dir4 dir2/dir5' "
        "-c execute 'mkdir dir1/dir4/dir6' "
        "-c execute 'touch dir1/file1 dir1/file2' "
        "-c execute 'touch dir2/file3' "
        "-c execute 'touch dir1/dir3/file4 dir1/dir3/file5 dir1/dir3/file6' "
        "-c execute 'touch dir2/dir5/file7' "
        "-c execute 'touch dir1/dir4/dir6/file8 dir1/dir4/dir6/file9' ",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=True,
    )
    output = res.stdout.decode('utf-8')
    assert res.returncode == ExitCode.PASSED
    assert '[ INFO  ] Starting Stage 1' in output
    assert '[ DONE  ] EXECUTE  : mkdir dir1/dir3 dir1/dir4 dir2/dir5' in output
    assert '[ DONE  ] EXECUTE  : mkdir dir1/dir4/dir6' in output
    assert '[ DONE  ] EXECUTE  : touch dir1/file1 dir1/file2' in output
    assert '[ DONE  ] EXECUTE  : touch dir2/file3' in output
    assert '[ DONE  ] EXECUTE  : touch dir1/dir3/file4 dir1/dir3/file5 dir1/dir3/file6' in output
    assert '[ DONE  ] EXECUTE  : touch dir2/dir5/file7' in output
    assert '[ DONE  ] EXECUTE  : touch dir1/dir4/dir6/file8 dir1/dir4/dir6/file9' in output
    assert '[ INFO  ] Stage 1 complete with result DONE' in output
    assert dir1.exists() is True
    assert dir2.exists() is True
    assert dir3.exists() is False
    assert dir4.exists() is False
    assert dir5.exists() is False
    assert dir6.exists() is False
    assert file1.exists() is False
    assert file2.exists() is False
    assert file3.exists() is False
    assert file4.exists() is False
    assert file5.exists() is False
    assert file6.exists() is False
    assert file7.exists() is False
    assert file8.exists() is False
    assert file9.exists() is False
