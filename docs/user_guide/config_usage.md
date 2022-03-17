# Defining build-magic Config Files

## Synopsis

Build-magic supports executing multiple stages as static, repeatable jobs with a Config File. A build-magic Config File is a YAML file with the following structure:

```yaml
author: Vision
maintainer: Vision
version: 1.2.3
created: 2021/12/05
modified: 2021/12/06
description: An example build-magic Config File.
prepare:
  - &myproject
    /home/myproject
build-magic:
  - stage:
      name: Build Project
      runner: docker
      environment: centos:7
      working directory: *myproject
      parameters:
        bind: *myproject
      environment variables:
        GOOS: linux
        GOARCH: amd64
      commands:
        - execute: configure
        - build: make
          label: Build the project
  - stage:
      name: Run tests
      description: Run integration tests against a test db
      runner: docker
      environment: centos:7
      working directory: *myproject
      parameters:
        bind: *myproject
      dotenv: mydb.env
      continue on fail: true
      commands: 
        - execute: service start mydb
          label: Start the test db
        - test: make test
          label: Run integration tests
        - execute: service stop mydb
          label: Shutdown the test db
  - stage:
      name: Package CentOS
      runner: docker
      environment: centos:7
      working directory: *myproject
      parameters:
        bind: *myproject
      commands:
        - build: make rpm
        - release: jfrog rt upload "build/RPMS/x86_64/(*).rpm" my-artifactory
          label: Upload the package to the artifactory
```

## Description

**build-magic** - The type of the **build-magic** property is an array of **stage** properties. The **build-magic** property must define at least one **stage**.

**stage** - Each **stage** is an object that defines the same properties as the CLI. The only property of **stage** that's required is **commands**.

**name** - Optional name to give the executing **stage**. If **name** isn't provided, the default stage name is 1, and each subsequent stage name is incremented by 1. The **name** can be used as the target if explicitly executing individual stages from the command-line.

**description** - Optional description of the stage to be displayed by the build-magic output. The **description** is typically longer than the stage **name**.

**runner** - The command runner to use for executing commands. The value must be one of *local*, *remote*, *vagrant* or *docker*. The default command runner is *local*.

**environment** - The environment to use for the specified command runner. If the **runner** property is defined and not equal to *local*, the **environment** property is required.

**action** The setup and teardown action to use. The value must be one of *default*, *cleanup*, or *persist*. The default action is *default*.

**continue on fail** - If *true*, build-magic will try to continue execution even if a command fails.

!!! Warning
    Depending on the commands being executed, using **continue** can lead to unstable behavior as failures can cascade to subsequent commands.

**copy from directory** - The path to copy artifacts from. If defined, build-magic will copy the array of items in **artifacts** to **working directory**.

**environment variables** - A list of key/value pairs where the key is the name of the environment variable and the value is the value of the environment variable. Each environment variable is set for the duration of the stage where it's provided.

**dotenv** - The path to a dotenv file of environment variables to set for the duration of the stage where it's provided.

**working directory** - The working directory the **stage** will operate from. If not specified, the default working directory is the current directory. In the case of the *local* and *remote* **runner**, the working directory is on the host machine. For the *vagrant* and *docker* **runner**, the working directory is on the guest machine, i.e. inside the virtual machine or running container.

**artifacts** - Files to be copied from the **copy from directory** to the **working directory**. Artifacts are ignored unless the **copy from directory** option is set. The artifacts must exist in **copy from directory** path to be copied to the working directory.

**parameters** - A list of key/value pairs of command runner specific configurations.

**commands** - A list of key/value pairs, where the key is a directive and the value is the command to execute.

**label** - An optional description for each command in **commands** that will be displayed by the build-magic output instead of the command.

## Metadata

As of build-magic 0.4.0, each Config File can optionally specify job-level metadata outside of the **build-magic** section that can be used to provide more context for the Config File.

**author** - The Config File author.

**maintainer** - The Config File maintainer or maintainers.

**version** - The version number of the Config File.

**created** - The date the Config File was created.

**modified** - The last date the Config File was modified.

**description** - A brief description of the job being executed in the Config File.

## Prepare

As of build-magic 0.4.0, a **prepare** section can optionally be provided as a list of defined YAML anchors and chunks. The anchors and associated config can be used to define repetitive commands or values to make better use of code reuse. You can of course use YAML anchors anywhere in a Config File, but the **prepare** section is a dedicated space for these anchors that will help keep the Config File clean and easier to read.
