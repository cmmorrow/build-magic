# build-magic &#x1F528;&#x2728;

An un-opinionated, general purpose automation tool.

Build-magic is a command-line application for automating build, test, install, and deploy tasks. It's designed to be easy to use by both developers and DevOps engineers.

---

![build-magic](build-magic.gif)

Using build-magic can be as simple as:

    > build-magic echo hello world!

or can support complex build automation with multiple steps on the command-line or in a Config File.

=== "Command-line"

    ```bash
    > build-magic \
      --runner docker \
      --environment ubuntu:latest \
      --verbose \
      --cleanup \
      --command execute "./configure CC=c99 CFLAGS=-O2 LIBS=-lposix" \
      --command build "make" \
      --command test "make test" \
      --command execute "tar -czf myapp.tar.gz build/*" \
      --command release "jfrog rt upload myapp.tar.gz my-artifactory"
    ```

=== "Config File"

    ```bash
    > build-magic -C myapp.yaml
    > cat myapp.yaml
    ```
    ```yaml
    build-magic:
      - stage:
          name: release
          runner: docker
          environment: ubuntu:latest
          action: cleanup
          commands:
            - execute: ./configure CC=c99 CFLAGS=-O2 LIBS=-lposix
            - build: make
            - test: make test
            - execute: tar -czf myapp.tar.gz build/*
            - release: jfrog rt upload myapp.tar.gz my-artifactory
    ```

Build-magic can execute a batch of commands in a Config File with:

    > build-magic -C myapp.yaml

Or, if the Config File is named `build-magic.yaml`, can be run similar to a Makefile with:

    > build-magic release

---

## Common Use Cases

* Automate building, testing, and releasing new software versions.
* Build and deploy new machine learning models.
* Automate deploying software to staging or production cloud environments.
* Simplify onboarding new team members by automating development environment setup and installation.
* Automate launching an application for local testing with the same config file used for deploying in production.
* Execute regression, integration, and unit tests across multiple platforms and servers.
* Automate dry runs of critical commands that cannot be tested on a production system.

## Features

### Work the way you want to work

Developing for Linux from a Windows or MacOS laptop? Build-magic lets you build, test, and deploy your application within a Docker container, virtual machine, or on a remote machine. Build-magic will manage the environment differences for you so you can focus on the details that matter.

### Automate everything

If your terminal can do it, build-magic can automate it! Build-magic is a modern alternative to automating with Makefiles and shell scripts. Build-magic Config Files feature an easy to use YAML syntax for executing multiple stages (targets). Build-magic actions can also apply setup and teardown behaviors for preserving container or VM state, or clean up extra files generated as part of a build process. Build-magic also gives you control over how output is displayed by providing a TTY friendly format as well a log file friendly format.

### Simple but powerful

There are no looping mechanics or specialized conditional logic handlers beyond what can be done via the command-line. This might seem like a disadvantage but it makes build-magic jobs easier to debug, re-run, and replicate. What build-magic lacks in programming language-like features, it makes up for with easy of use and powerful actions. By using the cleanup action, build-magic jobs become idempotent. The persist action will preserve the state of a container or VM after execution of a job.

### Un-opinionated

As much as possible, build-magic strives to setup environments and execute commands the same way, whether commands are being executed locally, remotely, in a container, or in a VM. Also, unlike similar automation tools that have builtin directives, build-magic command directives don't impart any special meaning or track state -- they are simply descriptive. This keeps things simple, and what you see in a build-magic config file or in command-line arguments is exactly what's executed. Aside from the simple syntax, build-magic doesn't care how you run commands.

### Runtime variables

Build-magic config files support placeholders using a Jinja-like syntax. At runtime, dynamic values and secrets can be assigned and substituted for the placeholders, allowing for general-purpose, multi-user use cases. Simplify onboarding a new team member by automating project setup with a single build-magic config file.

### Cross platform

Build-magic runs on Windows, Mac OS, and Linux. For ultimate portability, build-magic supports executing commands on a remote server via SSH, in a Docker container, or in a virtual machine via Vagrant. Build-magic config files support variable substitution so dynamic values like version numbers and credentials can be supplied at runtime and substituted into commands.
