# build-magic :hammer::sparkles:

![PyPI](https://img.shields.io/pypi/v/build-magic)
![GitHub Workflow Status](https://img.shields.io/github/workflow/status/cmmorrow/build-magic/Python%20application)
![Codecov](https://img.shields.io/codecov/c/github/cmmorrow/build-magic)

An un-opinionated build automation tool.

## Introduction

Build-magic is a command-line application for automating build/test/install/package/deploy tasks. It aims to provide a common means for automating build tasks for developers and DevOps. Build-magic does this by abstracting away how and where the build tasks are executed. Developing a C++ application for a Linux container on Windows? Build-magic can build your project in a Linux container or virtual machine. Have a dedicated build server? Build-magic can SSH into the remote server and start the build.

There are four core principals behind build-magic:

* Work the way you want to work.
* Make building easier and portable.
* Not another CI or build tool.
* Enable developers to simplify DevOps.

## Installation

Build-magic requires Python 3.6+. You can install build-magic with the following command:

```bash
pip install build-magic
```

To use the Docker command runner, Docker must be installed. You can find out more about installing Docker [here](https://docs.docker.com/get-docker/).

To use the Vagrant command runner, Vagrant must be installed. You can find out more about installing Vagrant [here](https://www.vagrantup.com/docs/installation).

## Usage

Build-magic can execute arbitrary shell commands from it's command-line interface (CLI) or by specifying commands in a config file.

Here is a basic example of how to use build-magic from the command-line:

```bash
build-magic "echo hello world > hello.txt"
```

Multiple commands can be executed as a sequence by using the `--command` option:

```bash
build-magic \
--verbose \
--command execute "echo hello >file1.txt" \
--command execute "echo world >file2.txt" \
--command build "tar -czf myfiles.tar.gz file1.txt file2.txt" \
--command execute "rm file1.txt file2.txt" \
--command install "tar -xzf myfiles.tar.gz" \
--command test "cat file1.txt file2.txt"
```

When using the `--command` option, a directive that describes the command must be provided.The directive `execute` can be used as a catch-all for describing any command. The `--verbose` option will print anything written to stdout by an individual commands.

To run the commands in a Linux container, add the `--runner` and `--environment` options:

```bash
build-magic \
--runner docker \
--environment ubuntu:latest \
--verbose \
--command execute "echo hello > file1.txt" \
--command execute "echo world > file2.txt" \
--command build "tar -czf myfiles.tar.gz file1.txt file2.txt" \
--command execute "rm file1.txt file2.txt" \
--command install "tar -xzf myfiles.tar.gz" \
--command test "cat file1.txt file2.txt"
```

Run `build-magic --help` for a list of all the available command-line options.

Sequences of commands can be grouped into stages and executed from a config file written in YAML. The contents of the config file `config.yaml` will describes the same steps broken up into stages:

```yaml
build-magic:
  - stage:
        name: Setup
        commands:
          - execute: echo hello > file1.txt
          - execute: echo world > file2.txt
  - stage:
        name: Archive
        commands:
          - build: tar -czf myfiles.tar.gz file1.txt file2.txt
          - execute: rm file1.txt file2.txt
  - stage:
        name: Un-Archive
        commands:
          - install: tar -xzf myfiles.tar.gz
  - stage:
        name: Result
        commands:
          - test: cat file1.txt file2.txt
```