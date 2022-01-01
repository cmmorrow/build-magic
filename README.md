# build-magic &#x1F528;&#x2728;

![PyPI](https://img.shields.io/pypi/v/build-magic)
![PyPI - Python Version](https://img.shields.io/pypi/pyversions/build-magic)
![GitHub Workflow Status](https://img.shields.io/github/workflow/status/cmmorrow/build-magic/Python%20application)
![Codecov](https://img.shields.io/codecov/c/github/cmmorrow/build-magic)
[![Downloads](https://pepy.tech/badge/build-magic)](https://pepy.tech/project/build-magic)

An un-opinionated build automation tool.

## Introduction

Build-magic is a command-line application for automating build/test/install/package/deploy tasks. It aims to provide a common means for automating tasks for developers and DevOps. Build-magic does this by abstracting away how and where the build tasks are executed. Simply tell build-magic what commands to run and where to run them.

Developing a C++ application for Linux on a Windows laptop? Build-magic can build your project in a Linux container or virtual machine. Have a dedicated build server? Build-magic can SSH into the remote server and start the build.

Build-magic allows you to specify commands and the environment from the command-line or from a Config File.

## Contributing

Build-magic is still under active development, with new features being added regularly.

Want to help make build-magic better? Pull Requests are welcome. Please review the [contributing guide](https://github.com/cmmorrow/build-magic/blob/main/CONTRIBUTING.md) on how you can contribute to build-magic.

## Examples

Archive two files on a local Linux or Mac OS machine:

```bash
> build-magic tar -czf myfiles.tar.gz file1.txt file2.txt
```

The following commands execute the same command on the local system, on a remote system, in a Docker container, and in a virtual machine:

```bash
> build-magic echo hello world

> build-magic --runner remote -e user@myhost echo hello world

> build-magic --runner docker -e alpine:latest echo hello world

> build-magic --runner vagrant -e Vagrantfile echo hello world
```

## Design

Building software is hard enough, and managing shell scripts, documentation, and environments across a project for multiple users and operating systems can become a pain. Build-magic was designed to be the automation tool that works for you. It aims to do for builds what Ansible has done for installs, and Docker has done for deployment. It's time to ditch the shell scripts and complex Makefiles.

These are the three features that distinguish build-magic:

### Un-opinionated

As much as possible, build-magic strives to setup environments and execute commands the same way, whether commands are being executed locally, remotely, in a container, or in a VM. Also, unlike similar automation tools that have builtin directives, build-magic command directives don't impart any special meaning or track state -- they are simply descriptive. This keeps things simple, and what you see in a build-magic config file or in command-line arguments is exactly what's executed. Aside from the simple syntax, build-magic doesn't care how you run commands.

### Declarative

Build-magic uses a simple syntax that lets you describe what commands to automate, the environment to use, and what files to include. There's no need for conditional statements that you might need when automating with a shell or batch script. Build-magic will take care of the details and execute the specified commands in the specified environment.

### Reproducible

Because build-magic lets you execute commands in a container or virtual machine, build-magic jobs are reproducible and portable across systems. This solves the *"Well it works on my machine"* problem.

## Installation

### MacOS

Build-magic can be installed with Homebrew using the following commands:

```bash
> brew tap cmmorrow/build-magic
> brew install build-magic
```

### Linux

You can find instructions for installing build-magic for Fedora based and Debian based distros from the build-magic Linux installation [instructions](https://cmmorrow.github.io/build-magic/getting_started/#linux).

### Python

If you have Python3 installed, the recommended way to install build-magic is into an isolated environment via [pipx](https://pypa.github.io/pipx/).

```bash
> pipx install build-magic
```

Alternatively, you can install build-magic from pypi into a virtual environment. Build-magic requires Python 3.6+. You can install build-magic with the following command:

```bash
> pip install build-magic
```

**Warning**: It isn't recommend to use `pip install build-magic` to install into a base Python environment. This is because build-magic uses pinned dependencies that might cause conflicts with package versions already installed in the base Python environment.

### Optional Installs

To use the Docker command runner, Docker must be installed. You can find out more about installing Docker [here](https://docs.docker.com/get-docker/).

To use the Vagrant command runner, Vagrant must be installed. You can find out more about installing Vagrant [here](https://www.vagrantup.com/docs/installation).

To use the Remote command runner, OpenSSH must be installed. If you are using Linux or MacOS, OpenSSH is likely already installed. If you are using Windows 10+ OpenSSH can be enabled following [these](https://docs.microsoft.com/en-us/windows-server/administration/openssh/openssh_install_firstuse) instructions.

## Documentation

You can view the documentation at [https://cmmorrow.github.io/build-magic/](https://cmmorrow.github.io/build-magic/).

## Usage

Build-magic can execute arbitrary shell commands from its command-line interface or by specifying commands in a Config File.

### Command-line

Here is a basic example of how to use build-magic from the command-line:

```bash
> build-magic "echo hello world > hello.txt"
```

Multiple commands can be executed as a sequence by using the `--command` option:

```bash
> build-magic \
--verbose \
--command execute "echo hello >file1.txt" \
--command execute "echo world >file2.txt" \
--command build "tar -czf myfiles.tar.gz file1.txt file2.txt" \
--command execute "rm file1.txt file2.txt" \
--command install "tar -xzf myfiles.tar.gz" \
--command test "cat file1.txt file2.txt" \
--command execute "rm file1.txt file2.txt" \
--command execute "rm myfiles.tar.gz"
```

When using the `--command` option, a directive that describes the command must be provided. The directive `execute` can be used as a catch-all for describing any command. The `--verbose` option will print anything written to stdout by an individual command.

To run the commands in a Linux container, add the `--runner` and `--environment` options:

```bash
> build-magic \
--runner docker \
--environment ubuntu:latest \
--verbose \
--command execute "echo hello > file1.txt" \
--command execute "echo world > file2.txt" \
--command build "tar -czf myfiles.tar.gz file1.txt file2.txt" \
--command execute "rm file1.txt file2.txt" \
--command install "tar -xzf myfiles.tar.gz" \
--command test "cat file1.txt file2.txt" \
--command execute "rm file1.txt file2.txt" \
--command execute "rm myfiles.tar.gz"
```

Run `build-magic --help` for a list of all the available command-line options.

### Config File

Sequences of commands can be grouped into stages and executed from a Config File written in YAML. The contents of the Config File `config.yaml` will describes the same steps broken up into stages:

```yaml
build-magic:
  - stage:
      name: Setup
      runner: docker
      environment: ubuntu:latest
      commands:
        - execute: echo hello > file1.txt
        - execute: echo world > file2.txt
  - stage:
      name: Archive
      runner: docker
      environment: ubuntu:latest
      commands:
        - build: tar -czf myfiles.tar.gz file1.txt file2.txt
          label: Archive the files as myfiles.tar.gz
        - execute: rm file1.txt file2.txt
          label: Delete the original files
  - stage:
      name: Un-Archive
      runner: docker
      environment: ubuntu:latest
      commands:
        - install: tar -xzf myfiles.tar.gz
          label: Extract the archive to the current directory
  - stage:
      name: Result
      runner: docker
      environment: ubuntu:latest
      commands:
        - test: cat file1.txt file2.txt
        - execute: rm file1.txt file2.txt
          label: Cleanup the files
        - execute: rm myfiles.tar.gz
          label: Cleanup the archive
```

Notice how optional labels can be added to each command that will be printed as part of the build-magic output instead of the corresponding command.

You can execute Config File `config.yaml` with:

```bash
> build-magic --config config.yaml --verbose
```

A single stage in a Config File can be run with:

```bash
> build-magic --config config.yaml --target Setup
```

Multiple stages can be executed this way, even in a different order:

```bash
> build-magic --config config.yaml --target Setup --target Result
```

### Code reuse with anchors

YAML anchors and aliases can be used to reuse repeated values. In the Config File above, the command `rm file1.txt file2.txt` is used more than once, and the same runner and environment is used for each stage. These values can be replaced with anchors and called with aliases. YAML anchors can be defined in a `prepare:` section of the Config File:

```yaml
prepare:
  - &delete_files
      rm file1.txt file2.txt
  - &runner
      docker
  - &environment
      ubuntu:latest
build-magic:
  - stage:
      name: Setup
      runner: *runner
      environment: *environment
      commands:
        - execute: echo hello > file1.txt
        - execute: echo world > file2.txt
  - stage:
      name: Archive
      runner: *runner
      environment: *environment
      commands:
        - build: tar -czf myfiles.tar.gz file1.txt file2.txt
          label: Archive the files as myfiles.tar.gz
        - execute: *delete_files
          label: Delete the original files
  - stage:
      name: Un-Archive
      runner: *runner
      environment: *environment
      commands:
        - install: tar -xzf myfiles.tar.gz
          label: Extract the archive to the current directory
  - stage:
      name: Result
      runner: *runner
      environment: *environment
      commands:
        - test: cat file1.txt file2.txt
        - execute: *delete_files
          label: Cleanup the files
        - execute: rm myfiles.tar.gz
          label: Cleanup the archive
```

The execution of this Config File is identical to the previous one.

### Environment Variables

Environment variables cannot be set by build-magic commands. However, they can be used by build-magic commands by using the `--env` option followed by the variable name and value:

```bash
> build-magic --env FOO hello --env BAR world echo '$FOO' '$BAR'
```

Environment variables can also be used in Config Files:

```yaml
build-magic:
  - stage:
      environment variables:
        FOO: hello
        BAR: world
      commands:
        - execute: echo $FOO $BAR
```

Alternatively, a dotenv file can be passed to set multiple environment variables at once:

```bash
> build-magic --dotenv hello.env echo '$FOO' '$BAR'
```

As well as in a Config File:

```yaml
build-magic:
  - stage:
      dotenv: hello.env
      commands:
        - execute: echo $FOO $BAR
```

### Runtime Variables

Build-magic supports variable substitution in Config Files that works similar to a Jinja template.

```yaml
build-magic:
  - stage:
      commands:
        - execute: >
          curl -u {{ user }}:{{ password }} 
          https://myrepo/myproject/{{ version }}
```

In the Config File above, the `user`, `password`, and `version` runtime variables are declared and can be substituted at runtime using the following command:

```bash
> build-magic -v user vision -v password wanda -v version 12 -C config.yaml
```

Since it isn't a good idea to provides secrets in clear text that can appear on screen or in command history, the `--prompt` option can be used to interactively prompt the user for the value of the variable without printing it to the screen.

```bash
> build-magic -v user vision --prompt password -v version 12 -C config.yaml
> password:
```

### Including Files

Files can be copied from another directory into the current working directory by passing the directory to copy from with the `--copy` option and providing the files to copy as arguments:

```bash
> build-magic \
--copy myproject/src \
-c execute "go build main.go" \
audio.go equalizer.go effects.go
```

Copying files is handled similarly in a Config File:

```yaml
build-magic:
  - stage:
      copy from directory: myproject/src
      artifacts:
        - audio.go
        - equalizer.go
        - effects.go
      commands:
        - execute: go build main.go
```
