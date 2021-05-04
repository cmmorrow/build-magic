# Basic Concepts

To get the most out of build-magic, you should become familiar with build-magic's core concepts:

- Commands
- Directives
- Command Runners
- Output Formats
- Working Directory
- Stages
- Config File
- Job
- Actions
- Parameters

Many of these terms will look familiar if you've used Jenkins or GitHub Actions, but the meaning of these terms can be quite different for build-magic.

## Commands

Build-magic's primary focus is executing Commands. A Command is a valid command-line interface command that can be executed in a single line. Commands are executed by build-magic using the default shell of the machine the Command is executing on. Each Command that build-magic executes returns stdout, stderr, and an exit code. If a Command returns an exit code other than 0, build-magic will by default stop execution and display any error message from stderr.

There are two ways to execute Commands with build-magic. The simplest way is to execute a single command as an argument to the `build-magic` command:

```text
> build-magic make
```

In this case, build-magic simply executes the `make` Command in the current directory.

!!! Note
    When using a command that has multiple arguments or makes use of shell operators such as redirection `>` or piping `|` It will be necessary to wrap the command in single quotes so that the shell doesn't try to interpret the operator.

Build-magic can also execute multiple commands with the `--command` option in the order they are provided:

```text
> build-magic \
--command execute 'tar -czf myfiles.tar.gz file1.txt file2.txt' \
--command execute 'rm file1.txt file2.txt'
```

Note that the word "execute" is used before the commands. This is a Directive and is described below. Each command is also surrounded in quotes, otherwise build-magic gets confused and thinks you are trying to pass additional arguments.

## Directives

Directives describe the type of Command being executed. All Commands that build-magic executes must have a Directive associated with them. Directives don't impart any special meaning to build-magic and are simply used to describe the command. Valid Directives that build-magic understands are:

- execute
- build
- test
- install
- release
- deploy

If only a single command is passed to build-magic without a Directive, the "execute" Directive is used by default.

## Command Runners

Build-magic can execute Commands on the local machine, in a container, in a virtual machine, or on a remote machine. You tell build-magic how you want to execute the Commands by specify a Command Runner with the `--runner` option. Valid Command Runners are:

- *local*
- *docker*
- *vagrant*
- *remote*

By default, the *local* Command Runner is used if the `--runner` option isn't provided.

All Commands Runners except for the *local* Command Runner must also provide the `--environment` option. The environment depends on the Command Runner being used:

- *docker*: The name of the Docker container - `ubuntu:latest`
- *vagrant*: The path to the Vagrantfile - `./Vagrantfile`
- *remote*: The username and hostname of the remote machine to connect to - `user@myhost`

Example:

```text
> build-magic --runner docker --environment ubuntu:latest make
```

## Output Formats

Build-magic reports it's progress and status to stdout on a terminal. There are three different output format based on your preference and use case:

- fancy
- plain
- quiet

## Working Directory

The Working Directory is the path that build-magic operates from. Non-absolute paths in commands that build-magic executes are relative to the Working Directory.

## Stages

A Stage is a collection of Commands. When you use build-magic from the command-line, all the Commands are gathered into a single stage and executed as a single collection. Build-magic can execute multiple Stages, but only by using a Config File.

## Config File

A build-magic Config File is a YAML file that describes the Stages and Commands to run, and how to run them.

## Job

A Job is a collection of all the Stages that build-magic is going to execute.

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
