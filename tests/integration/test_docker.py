"""Integration tests for the Docker CommandRunner."""

from pathlib import Path
import subprocess

import pytest

from build_magic.reference import ExitCode


@pytest.mark.docker
def test_single_command(cli):
    """Verify passing a single command as arguments works correctly."""
    res = subprocess.run(
        'python -m build_magic --verbose --plain '
        '--runner docker '
        '--environment alpine:latest '
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


@pytest.mark.docker
def test_redirection(cli, tmp_path):
    """Verify redirecting stdout within a command works correctly."""
    ref_file = tmp_path / 'hello.txt'
    res = subprocess.run(
        'python -m build_magic --verbose --plain '
        f'--parameter hostwd {tmp_path} '
        '--runner docker '
        '--environment alpine:latest '
        '-c execute \'echo "hello world" > hello.txt\' -c execute "cat hello.txt"',
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
    assert ref_file.exists()


@pytest.mark.docker
def test_redirection_working_directory(cli):
    """Verify redirecting stdout within a command works correctly when setting the working directory."""
    res = subprocess.run(
        'python -m build_magic --verbose --plain --wd /app '
        '--runner docker '
        '--environment alpine:latest '
        '-c execute \'echo "hello world" > hello.txt\' -c execute "cat hello.txt"',
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


@pytest.mark.docker
def test_env(cli):
    """Verify using an environment variable within a command works correctly."""
    res = subprocess.run(
        "python -m build_magic --verbose --plain "
        "--runner docker "
        "--environment alpine:latest "
        "'echo $TERM'",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=True,
    )
    output = res.stdout.decode('utf-8')
    assert res.returncode == ExitCode.PASSED
    assert '[ INFO  ] Starting Stage 1' in output
    assert '[ DONE  ] EXECUTE  : echo $TERM' in output
    assert '[ INFO  ] OUTPUT   : xterm' in output
    assert '[ INFO  ] Stage 1 complete with result DONE' in output


@pytest.mark.docker
def test_bind_path(cli, tmp_path):
    """Verify setting the bind path works correctly."""
    main = tmp_path / 'main.cpp'
    plugins = tmp_path / 'plugins.cpp'
    audio = tmp_path / 'audio.cpp'
    main.touch()
    plugins.touch()
    audio.touch()
    res = subprocess.run(
        "python -m build_magic --verbose --plain "
        "--runner docker "
        "--environment alpine:latest "
        f"--parameter hostwd {tmp_path} "
        "--parameter bind /app "
        "--wd /app "
        "-c execute 'pwd' "
        "-c execute 'ls'",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=True,
    )
    output = res.stdout.decode('utf-8')
    assert res.returncode == ExitCode.PASSED
    assert '[ INFO  ] Starting Stage 1' in output
    assert '[ DONE  ] EXECUTE  : pwd' in output
    assert '[ INFO  ] OUTPUT   : /app' in output
    assert '[ DONE  ] EXECUTE  : ls' in output
    assert 'audio.cpp' in output
    assert 'main.cpp' in output
    assert 'plugins.cpp' in output
    assert '[ INFO  ] Stage 1 complete with result DONE' in output


@pytest.mark.docker
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
        "--runner docker "
        "--environment alpine:latest "
        f"--copy {tmp_path} "
        "--wd /app "
        "-c execute 'pwd' "
        "-c execute 'ls' "
        "main.cpp plugins.cpp audio.cpp",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=True,
    )
    output = res.stdout.decode('utf-8')
    assert res.returncode == ExitCode.PASSED
    assert '[ INFO  ] Starting Stage 1' in output
    assert '[ DONE  ] EXECUTE  : pwd' in output
    assert '[ INFO  ] OUTPUT   : /app' in output
    assert '[ DONE  ] EXECUTE  : ls' in output
    assert 'audio.cpp' in output
    assert 'main.cpp' in output
    assert 'plugins.cpp' in output
    assert '[ INFO  ] Stage 1 complete with result DONE' in output

    Path.cwd().resolve().joinpath('main.cpp').unlink()
    Path.cwd().resolve().joinpath('audio.cpp').unlink()
    Path.cwd().resolve().joinpath('plugins.cpp').unlink()


@pytest.mark.docker
def test_cleanup(cli, tmp_path):
    """Verify the cleanup action works correctly."""
    main = tmp_path / 'main.cpp'
    plugins = tmp_path / 'plugins.cpp'
    audio = tmp_path / 'audio.cpp'
    main.touch()
    plugins.touch()
    audio.touch()
    res = subprocess.run(
        "python -m build_magic --verbose --plain "
        "--runner docker "
        "--environment alpine:latest "
        "--action cleanup "
        f"--parameter hostwd {tmp_path} "
        "-c execute 'touch test1.txt test2.txt' "
        "-c execute 'ls'",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=True,
    )
    output = res.stdout.decode('utf-8')
    assert res.returncode == ExitCode.PASSED
    assert '[ INFO  ] Starting Stage 1' in output
    assert '[ DONE  ] EXECUTE  : touch test1.txt test2.txt' in output
    assert '[ DONE  ] EXECUTE  : ls' in output
    assert 'audio.cpp' in output
    assert 'main.cpp' in output
    assert 'plugins.cpp' in output
    assert 'test1.txt' in output
    assert 'test2.txt' in output
    assert '[ INFO  ] Stage 1 complete with result DONE' in output
    assert main.exists() is True
    assert audio.exists() is True
    assert plugins.exists() is True
    assert tmp_path.joinpath('test1.txt').exists() is False
    assert tmp_path.joinpath('test2.txt').exists() is False


@pytest.mark.docker
def test_persist(cli):
    """Verify the persist action works correctly."""
    res = subprocess.run(
        'python -m build_magic --verbose --plain '
        '--runner docker '
        '--environment alpine:latest '
        '--action persist '
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

    res = subprocess.run(
        'docker ps',
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=True,
    )
    output = res.stdout.decode('utf-8')
    assert res.returncode == ExitCode.PASSED
    assert 'build-magic' in output

    subprocess.run('docker stop build-magic', shell=True)
    subprocess.run('docker rm build-magic', shell=True)
