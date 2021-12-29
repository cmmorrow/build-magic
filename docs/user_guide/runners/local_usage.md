# Using the Local Command Runner

The *local* Command Runner executes commands on the host machine where build-magic is running. This means build-magic can only run commands that work on the host machine or shell where build-magic is running.

## Running Shell Commands

The *local* Command Runner invokes the default shell to execute commands, allowing the use of redirection and piping on a Posix-like OS.

=== "Command-line"

    ```bash  
    > build-magic --verbose \
      -c execute 'echo "hello world" > hello.txt' \
      -c execute 'cat hello.txt'
    ```

=== "Config File"

    ```yaml
    build-magic:
      - stage:
          commands:
            - execute: echo "hello world" > hello.txt
            - execute: cat hello.txt
    ```

```bash
> build-magic --verbose 'ps -ef | grep python'
```

Environment variables can be included in commands by wrapping the command in single quotes:

```bash
> build-magic --verbose 'echo $SHELL'
```

## Setting the Working Directory

The Working Directory is the path that build-magic operates from. By default, the Working Directory is the current directory of the shell when build-magic is executed. On Linux and MacOS, this directory is the value of `$PWD` or `pwd` on Windows.

The Working Directory can be changed to any path the user has permission to read from with the `--wd` option.

=== "Command-line"

    ```bash
    > build-magic --wd ~/myproject make
    ```

=== "Config File"

    ```yaml
    build-magic:
      - stage:
          working directory: ~/myproject
          commands:
            - execute: make
    ```

## Cleaning Up New Files

Compiling software into executables can often produce extra files that need to be manually deleted. Build-magic can clean up these newly created files with the *cleanup* Action.

The *cleanup* Action will take a snapshot of every file and directory in the working directory before the Stage runs. At the end of the Stage, any files or directories that don't exist in the snapshot are deleted.

If there are build artifacts that shouldn't be deleted, they should be moved or deployed before the Stage ends so that they aren't deleted. These build artifacts are typically binary executables, archives, or minified code and should be pushed to an artifactory, moved, or deployed before the Stage ends.

The *cleanup* Action can be executed with the **--action** option.

=== "Command-line"

    ```bash
    > build-magic --action cleanup \
      -c build 'python setup.py sdist bdist_wheel --universal' \
      -c release 'twine upload dist/*'
    ```

=== "Config File"

    ```yaml
    build-magic:
      - stage:
          action: cleanup
          commands:
            build: python setup.py sdist bdist_wheel --universal
            release: twine upload dist/*
    ```

!!! Note
    There is a special exclusion to prevent deleting files and directories that are modified inside the .git directory in the working directory to prevent git from becoming corrupted.

## Specifying a local environment

Optionally, when running a stage locally, you can specify a local environment for the stage to run in. You might want to do this to ensure a stage with Debian Linux specific commands don't run on Red Hat Enterprise Linux, or Windows Powershell commands don't run on MacOS. If the operating system (or Linux distribution) don't match the current machine, build-magic will skip the stage.

```bash
> build-magic -r local -e debian --verbose echo hello world
```
