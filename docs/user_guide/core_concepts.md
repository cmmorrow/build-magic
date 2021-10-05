# Core Concepts

To get the most out of build-magic, you should become familiar with build-magic's core concepts:

- [Commands](core_concepts.md#commands)
- [Directives](core_concepts.md#directives)
- [Command Runners](core_concepts.md#command-runners)
- [Output Formats](core_concepts.md#output-formats)
- [Working Directory](core_concepts.md#working-directory)
- [Stages](core_concepts.md#stages)
- [Config File](core_concepts.md#config-file)
- [Targets](core_concepts.md#targets)
- [Variables](core_concepts.md#variables)
- [Job](core_concepts.md#job)
- [Actions](core_concepts.md#actions)
- [Parameters](core_concepts.md#parameters)

Many of these terms will look familiar if you've used Ansible, Jenkins or GitHub Actions, but the meaning of these terms can be quite different for build-magic.

## Commands

Build-magic's primary focus is executing Commands. A Command is a valid command-line interface command that can be executed in a single line. Commands are executed by build-magic using the default shell of the machine the Command is executing on. Each Command that build-magic executes returns stdout, stderr, and an exit code. If a Command returns an exit code other than 0, build-magic will by default stop execution and display any error message from stderr.

There are two ways to execute Commands with build-magic. The simplest way is to execute a single command as an argument to the `build-magic` command:

```bash
> build-magic make clean
```

In this case, build-magic simply executes the `make clean` Command in the current directory.

!!! Note
    When using a command that has multiple arguments or makes use of shell operators such as redirection `>` or piping `|`, It will be necessary to wrap the command in single quotes so that the shell doesn't try to interpret the operator.

Build-magic can also execute multiple commands with the **--command** option in the order they are provided:

```bash
> build-magic \
--command execute 'tar -czf myfiles.tar.gz file1.txt file2.txt' \
--command execute 'rm file1.txt file2.txt'
```

Note that the word "execute" is used before the commands. This is a Directive and is described below. Each command is also surrounded in quotes, otherwise build-magic gets confused and thinks you are trying to pass additional arguments.

The build-magic Config File syntax is similar but does not require quotes around the command:

```yaml
commands:
  - execute: tar -czf myfiles.tar.gz file1.txt file2.txt
  - execute: rm file1.txt file2.txt
```

## Directives

Directives describe the type of Command being executed. All Commands that build-magic executes must have a Directive associated with them. Directives don't impart any special meaning to build-magic and are simply used to describe the command. Valid Directives that build-magic understands are:

- *execute*
- *build*
- *test*
- *install*
- *release*
- *deploy*

If only a single command is passed to build-magic on the command-line without a Directive, the *execute* Directive is used by default.

## Command Runners

Build-magic can execute Commands on the local machine, in a container, in a virtual machine, or on a remote machine. You tell build-magic how you want to execute the Commands by specify a Command Runner with the **--runner** option. Valid Command Runners are:

- *local*
- *docker*
- *vagrant*
- *remote*

By default, the *local* Command Runner is used if the **--runner** option isn't provided.

All Command Runners except for the *local* Command Runner must also provide the `--environment` option. The environment depends on the Command Runner being used:

- *docker*: The name of the Docker container - `ubuntu:latest`
- *vagrant*: The path to the Vagrantfile - `./Vagrantfile`
- *remote*: The username and hostname of the remote machine to connect to - `user@myhost`

Example:

=== "Command-line"

    ```bash
    > build-magic --runner docker --environment ubuntu:latest make
    ```

=== "Config File"

    ```yaml
    build-magic:
      - stage:
        runner: docker
        environment: ubuntu:latest
        commands:
          - execute: make
    ```

## Output Formats

Build-magic reports it's progress and status to stdout on a terminal. There are three different output format based on your preference and use case:

- *fancy*: Nicely formatted text output
- *plain*: Log friendly text output
- *quiet*: No output

The default Output Format is *fancy* which is useful when using build-magic from a TTY (terminal) application. The *plain* Output Format is useful if build-magic is being used from a CI/CD tool or piped to a log file where a log-like output is preferred.

Output Formats can only be set as a command-line option.

## Working Directory

The Working Directory is the path that build-magic operates from. Non-absolute paths in commands that build-magic executes are relative to the Working Directory. The default Working Directory is the current directory. The Working Directory can be set from the command-line with the `--wd /home/user` command or in a build-magic Config File with `working directory: /home/user`.

## Stages

A Stage is a collection of Commands. When you use build-magic from the command-line, all the Commands are gathered into a single stage and executed as a single collection. Build-magic can execute multiple Stages, but only by using a Config File.

## Config File

A build-magic Config File is a YAML file that describes the Stages and Commands to run, and how to run them. The Config File consists of a list of Stages to be executed in order. Multiple Config Files can be provided, in which case the Stages are executed in the order they are provided in each Config File. Specific stages to execute can be selected from the command line using Targets which are described below.

## Targets

A Target is a Stage name that can be used to run the corresponding Stage regardless of the Stage order in a Config file. Multiple Targets can be specified to reorder Stages at runtime. Targets can be used to filter the Stages to execute. For example, assume you have the Config File below named *build-magic.yaml*:

```yaml
build-magic:
  - stage:
      name: unittests
      commands:
        - test: pytest
  - stage:
      name: documentation
      action: cleanup
      commands:
        - build: mkdocs build
        - deploy: mkdocs gh-deploy
  - stage:
      name: package
      action: cleanup
      commands:
        - build: python setup.py sdist bdist_wheel --universal
        - release: twine upload dist/*
```

To only run the *unittests* stage in this Config File, use the below command:

```bash
> build-magic -t unittests
```

or if the stage name is a single word, the command can be shortened to:

```bash
> build-magic unittests
```

To run just the *unittests* and *documentation* stages, use:

```bash
> build-magic -t unittests -t documentation
```

or:

```bash
> build-magic unittests documentation
```

To swap the order of the *documentation* and *package* stages, use:

```bash
> build-magic unittests package documentation
```

All stages in the Config File can be run with:

```bash
build-magic all
```

## Variables

Variables are values that are substituted for placeholders in a Config File. Variables values and the corresponding placeholder name are specified at runtime as command-line arguments. The placeholders use a Jinja-like syntax of surrounding the placeholder name in `{{  }}`. The following Config File container placeholders intended for Variable substitution:

```yaml
build-magic:
  - stage:
      name: package
      runner: docker
      environment: ubuntu:latest
      commands:
        # Build the package
        - build: rpmbuild -bb $HOME/rpmbuild/SPECS/app{{ version }}.spec
        # Install and test the package
        - install: dnf install -y $HOME/rpmbuild/RPMS/noarch/app{{ version }}.rpm
        # Upload the package
        - release: scp app{{ version }}.rpm {{ user }}:{{ password }}@{{ host }}
```

This Config File can be re-used by different users to release new versions of the **app** RPM package. The Variables can be assigned at runtime with the following command as an example:

```bash
> build-magic -t package \
  --variable version 3.14.15 \
  --variable host myserver \
  --variable user myuser \
  --prompt password
```

The **--variable** option consists of the placeholder name followed by the value. The **--prompt** option will interactively prompt the user for input. This is the recommended way for providing secrets that shouldn't appear in the shell history.

!!! Note
    The **--prompt** option only works when using a TTY (terminal) interactively and will cause build-magic to hang if executed from a script.

## Job

A Job is a collection of all the Stages that build-magic is going to execute. If more than one Config File is provided, the Job consists of every Stage from each Config File.

## Actions

Actions can be used to modify build-magic's default behavior by adding setup and teardown behavior to a Stage. Build-magic's Actions are:

- default: Start up and destroy the virtual machine or container when the docker or vagrant Command Runner is used by the Stage. No setup or teardown is performed for the local or remote Command Runners.
- persist: Don't destroy the virtual machine or container used by the Stage. Useful for debugging.
- cleanup: Delete any files created by a Stage.

## Parameters

Parameters are optional configurations that are specific to a particular Command Runner.

| Command Runner | Parameter | Description |
| -------------- | --------- | ----------- |
| remote | keytype | The SSH key type (dsa, rsa, ecdsa, ed25519) |
| remote | keypath | The path to the SSH private key |
| remote | keypass | The private key passphrase if set |
| vagrant | hostwd | The working directory of the host (local machine) |
| vagrant | bind | The vm directory that is bound to the host |
| docker | hostwd | The working directory of the host (local machine) |
| docker | bind | A bind path on the container to the hostwd |
